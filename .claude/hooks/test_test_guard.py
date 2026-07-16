"""Pins the test-guard's decision logic (the hook that enforces
"every fix ships with a test"). Pure-function tests, no git needed.

Run: `python3 .claude/hooks/test_test_guard.py` or pytest.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from test_guard import broad_add, decide, is_test, paths_from_command


def test_app_code_without_test_blocks():
    block, app = decide(["routes/content.py"])
    assert block and app == ["routes/content.py"]
    block, _ = decide(["dashboard/src/pages/CommandCenterPage.tsx"])
    assert block
    block, _ = decide(["core.py", "docs/notes.md"])
    assert block


def test_app_code_with_test_passes():
    block, _ = decide(["routes/content.py", "test_reject_resolution.py"])
    assert not block
    block, _ = decide(["dashboard/src/lib/demo.ts", "dashboard/src/lib/demo.test.ts"])
    assert not block
    block, _ = decide(["utils/output_formatter.py", "utils/test_output_formatter.py"])
    assert not block
    block, _ = decide(["core.py", "tests/test_critical_path.py"])
    assert not block


def test_non_app_commits_pass():
    for staged in (
        ["docs/POST_ONBOARDING_CHAT_FLOW.md"],
        [".claude/hooks/ground_rules.md", ".claude/settings.json"],
        [".github/workflows/ci.yml"],
        [],
    ):
        block, _ = decide(staged)
        assert not block, staged


def test_test_only_commits_pass():
    block, _ = decide(["utils/test_formatter_coverage.py"])
    assert not block


def test_test_files_are_not_counted_as_app_code():
    # utils/test_*.py matches the utils/ app pattern but is a test — must not block
    assert is_test("utils/test_output_formatter.py")
    assert is_test("dashboard/src/lib/demo.test.ts")
    assert is_test("tests/test_paid_ops.py")
    assert not is_test("utils/output_formatter.py")


def test_add_and_commit_in_one_command_is_seen():
    # Pinned live escape (Jul 15): `git add X && git commit` stages AFTER the
    # PreToolUse hook runs, so the index alone saw nothing and the commit passed.
    cmd = 'git add routes/content.py utils/output_formatter.py && git commit -m "fix"'
    paths = paths_from_command(cmd)
    assert "routes/content.py" in paths and "utils/output_formatter.py" in paths
    block, _ = decide(paths)
    assert block
    # and with a test named in the same command, it passes
    ok_cmd = 'git add routes/content.py tests/test_critical_path.py && git commit -m "fix"'
    block, _ = decide(paths_from_command(ok_cmd))
    assert not block


def test_broad_add_detected():
    assert broad_add("git add -A && git commit -m x")
    assert broad_add("git add . && git commit -m x")
    assert not broad_add("git add routes/content.py && git commit -m x")


if __name__ == "__main__":
    test_app_code_without_test_blocks()
    test_app_code_with_test_passes()
    test_non_app_commits_pass()
    test_test_only_commits_pass()
    test_test_files_are_not_counted_as_app_code()
    test_add_and_commit_in_one_command_is_seen()
    test_broad_add_detected()
    print("test-guard tests passed")
