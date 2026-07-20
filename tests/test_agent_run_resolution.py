"""Pins the empty-agent-name bug (Jul 20): Atlas's Approve button POSTs
{agent_name: "Trend Researcher"} but /api/agents/run read only body["agentName"]
(camelCase) → empty → "No script built yet for ''", so approving a dispatch ran
nothing. Fail-on-old: resolving {"agent_name": ...} returned "". Fixed:
_resolve_agent_name accepts agentName / agent_name / agent_slug.

Run: `python3 -m pytest tests/test_agent_run_resolution.py -q`
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from routes.agents import _resolve_agent_name
from core import AGENT_SCRIPTS, _agent_name_to_slug


def test_snake_case_agent_name_resolves():
    # THE bug: this is exactly what Atlas's approve button sends.
    assert _resolve_agent_name({"agent_name": "Trend Researcher"}) == "Trend Researcher"


def test_legacy_camelcase_still_works():
    assert _resolve_agent_name({"agentName": "Strategy Agent"}) == "Strategy Agent"


def test_kebab_slug_resolves_to_name():
    # Pick a real dispatchable agent and round-trip its slug.
    name = "Trend Researcher"
    slug = _agent_name_to_slug(name)
    assert _resolve_agent_name({"agent_slug": slug}) == name


def test_empty_body_resolves_empty():
    assert _resolve_agent_name({}) == ""
    assert _resolve_agent_name({"agent_name": "   "}) == ""


def test_resolved_name_maps_to_a_real_script():
    # Whole point: after resolution the name must actually find a runnable script,
    # not fall into the "No script built yet" branch.
    name = _resolve_agent_name({"agent_name": "Trend Researcher"})
    assert AGENT_SCRIPTS.get(name), f"{name!r} has no script — dispatch would no-op"


if __name__ == "__main__":
    test_snake_case_agent_name_resolves()
    test_legacy_camelcase_still_works()
    test_kebab_slug_resolves_to_name()
    test_empty_body_resolves_empty()
    test_resolved_name_maps_to_a_real_script()
    print("agent-run resolution tests passed")
