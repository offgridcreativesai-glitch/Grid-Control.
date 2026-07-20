"""Atlas anti-fabrication guard.

Atlas (the client Brain) is the ORCHESTRATOR: when the user wants work done it
MUST call run_agent (a real, gated dispatch → a card the user approves). The
model instead sometimes NARRATES a dispatch in prose ("two specialists are
queued and waiting on your approval") without emitting the tool call — so no
card appears and there is nothing to review. That's a fabrication and the exact
trust-breaking bug (Jul 20, and the standing [[project_atlas_dispatches_agents]]
rule regressing).

This module is the mechanism that makes the claim provable: if Atlas's reply
talks like it dispatched a specialist but no agent proposal was actually
produced, the caller forces a real run_agent so the words become true. Pure +
tested so the decision can't silently rot.
"""
import re

# Phrases that assert a specialist is being/has been put to work THIS reply.
# Tight on purpose: matches "I just started the team", not generic mentions.
_DISPATCH_CLAIM = re.compile(
    r"(queued|dispatch(ed|ing)?|"
    r"scraping|pulling (live|real|the)|analy[sz]ing (live|real|your)|"
    r"\bon it\b|working on (it|that)|put (the )?(team|specialist|\w+ (researcher|agent|analyst|planner|writer))|"
    r"running (now|it right now)|waiting (on|for) your approval|"
    r"approve (both|them|it|the two|these)\b[^.]*\b(queue|run|start))",
    re.I,
)


def claims_dispatch(text: str) -> bool:
    """True if the reply talks as though a specialist was just dispatched."""
    return bool(_DISPATCH_CLAIM.search(text or ""))


def needs_forced_dispatch(text: str, has_agent_proposal: bool) -> bool:
    """The fabrication test: reply CLAIMS a dispatch but none was actually made.
    When True, the caller must force a real run_agent so a card appears (gated —
    nothing runs without the user's approval, so a spurious force is harmless)."""
    return claims_dispatch(text) and not has_agent_proposal


if __name__ == "__main__":  # smallest runnable check
    fabricated = ("Both are queued and waiting on your approval. Approve both in "
                  "the queue and they run.")
    assert needs_forced_dispatch(fabricated, has_agent_proposal=False)
    assert not needs_forced_dispatch(fabricated, has_agent_proposal=True)  # real card exists
    assert not needs_forced_dispatch("Your positioning is streetwear-led, founder-driven.", False)
    assert not needs_forced_dispatch("", False)
    print("atlas_guard self-check passed")
