"""Pins the Atlas-fabricates-a-dispatch bug (Jul 20). Gaurav's real transcript:
Atlas said "Both are queued and waiting on your approval. Approve both in the
queue and they run." — but nothing was dispatched, no card appeared, nothing to
review. Fail-on-old: that text with no agent proposal used to pass straight
through. Fixed: needs_forced_dispatch flags it so a real dispatch is forced.

Run: `python3 -m pytest tests/test_atlas_guard.py -q`
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.atlas_guard import claims_dispatch, needs_forced_dispatch


# Gaurav's actual Atlas replies from the broken session.
FABRICATED = [
    "Both are queued and waiting on your approval. Approve both in the queue and they run.",
    "Two specialists are queued and waiting on your approval: Trend Researcher — scraping "
    "live fashion trends on Instagram right now.",
    "I've put the Trend Researcher on it — pulling live streetwear data now.",
    "On it — the strategy agent is running now.",
]

# Legitimate replies that must NOT trigger a forced dispatch.
HONEST_NO_DISPATCH = [
    "Your positioning is streetwear-led and founder-driven — that's your edge.",
    "Do you sell streetwear, modest fashion, or broader lifestyle? That tightens the plan.",
    "You're on the Launch phase: organic traction plus social proof, 75:25 content-to-ads.",
    "",
]


def test_fabricated_dispatch_without_proposal_is_flagged():
    for text in FABRICATED:
        assert claims_dispatch(text), text
        # THE bug: claimed a dispatch, produced no agent card.
        assert needs_forced_dispatch(text, has_agent_proposal=False), text


def test_real_dispatch_with_a_proposal_is_fine():
    # Same words, but a real run_agent card WAS produced → honest, no force.
    for text in FABRICATED:
        assert not needs_forced_dispatch(text, has_agent_proposal=True), text


def test_honest_answers_never_forced():
    for text in HONEST_NO_DISPATCH:
        assert not claims_dispatch(text), text
        assert not needs_forced_dispatch(text, has_agent_proposal=False), text


if __name__ == "__main__":
    test_fabricated_dispatch_without_proposal_is_flagged()
    test_real_dispatch_with_a_proposal_is_fine()
    test_honest_answers_never_forced()
    print("atlas-guard tests passed")
