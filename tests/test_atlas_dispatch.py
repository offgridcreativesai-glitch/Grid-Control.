"""Pins the two Atlas-dispatch bugs behind "nothing to review" (Jul 20), $0
(Anthropic mocked). A CLIENT (non-admin, i.e. Gaurav) must actually receive the
dispatch card:

  Bug 1 — brain_chat returned proposals=[] for clients, so even a REAL run_agent
          call was stripped before reaching the UI. No card ever appeared.
  Bug 2 — when Atlas narrated "queued and waiting" WITHOUT calling run_agent, the
          guard now forces one real dispatch so a card appears.

Fail-on-old: with the old `proposals if is_admin else []`, scenario A returns no
proposals — the test fails. Pass-on-fix: the client gets the agent card.

Run: `python3 -m pytest tests/test_atlas_dispatch.py -q`
"""
import sys
import types
from pathlib import Path

import pytest

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO))

import core  # noqa: E402
import routes.brain as brain  # noqa: E402
from dashboard_api import app  # noqa: E402


def _text(t):
    return types.SimpleNamespace(type="text", text=t)


def _tool(agent="Trend Researcher"):
    return types.SimpleNamespace(type="tool_use", id="tu1", name="run_agent",
                                 input={"agent_name": agent, "rationale": "put them on it"})


def _resp(content, stop):
    usage = types.SimpleNamespace(input_tokens=1, output_tokens=1,
                                  cache_creation_input_tokens=0, cache_read_input_tokens=0)
    return types.SimpleNamespace(content=content, stop_reason=stop, usage=usage)


class _FakeClient:
    def __init__(self, script):
        self._script = script
        self.calls = []
        self.messages = self

    def create(self, **kw):  # self.messages.create(...)
        self.calls.append(kw)
        forced = isinstance(kw.get("tool_choice"), dict)
        return self._script(len(self.calls), forced)


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    # require_auth lives in core and resolves _get_current_user in core's globals.
    monkeypatch.setattr(core, "_get_current_user", lambda: {"id": "u1", "email": "c@ci"})
    monkeypatch.setattr(brain, "_DB_AVAILABLE", False, raising=False)
    monkeypatch.setattr(brain, "_build_brain_brand_summary", lambda s: "", raising=False)
    monkeypatch.setattr(brain._roles, "is_offtopic", lambda t: False)
    monkeypatch.setattr(brain._roles, "over_token_budget", lambda *a, **k: False)
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def _install(monkeypatch, script):
    import anthropic
    monkeypatch.setattr(anthropic, "Anthropic", lambda **kw: _FakeClient(script))


def _post(client):
    return client.post("/api/brain/chat", json={
        "brand_slug": "third-gen-tribe",
        "messages": [{"role": "user", "content": "research streetwear trends and plan my comeback"}],
    })


def test_real_dispatch_reaches_the_client(client, monkeypatch):
    # Bug 1: Atlas calls run_agent for real → the client MUST get the card.
    def script(n, forced):
        if n == 1:
            return _resp([_tool("Trend Researcher")], "tool_use")
        return _resp([_text("I've put the Trend Researcher on it — approve below.")], "end_turn")
    _install(monkeypatch, script)
    j = _post(client).get_json()
    agents = [p for p in j["proposals"] if p.get("kind") == "agent"]
    assert len(agents) == 1
    assert agents[0]["payload"]["agent_name"] == "Trend Researcher"


def test_narration_without_tool_is_forced_into_a_real_dispatch(client, monkeypatch):
    # Bug 2: Atlas fabricates "queued and waiting" with NO tool call → guard forces one.
    def script(n, forced):
        if n == 1:
            return _resp([_text("Both are queued and waiting on your approval. Approve both in the queue.")], "end_turn")
        assert forced, "second call must force run_agent"
        return _resp([_tool("Strategy Agent")], "tool_use")
    _install(monkeypatch, script)
    j = _post(client).get_json()
    agents = [p for p in j["proposals"] if p.get("kind") == "agent"]
    assert len(agents) == 1 and agents[0]["payload"]["agent_name"] == "Strategy Agent"
    # the fabricated "queued and waiting" line must be gone, replaced with honest text
    assert "queued and waiting" not in j["response"].lower()
    assert "approve" in j["response"].lower()


def test_honest_answer_dispatches_nothing(client, monkeypatch):
    # A pure question → no dispatch claim → no card, no forced call.
    def script(n, forced):
        assert n == 1, "must not make a second (forced) call for an honest answer"
        return _resp([_text("Your positioning is streetwear-led and founder-driven.")], "end_turn")
    _install(monkeypatch, script)
    j = _post(client).get_json()
    assert [p for p in j["proposals"] if p.get("kind") == "agent"] == []


if __name__ == "__main__":
    print("run via pytest")
