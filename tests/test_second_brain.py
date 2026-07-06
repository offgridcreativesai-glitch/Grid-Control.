"""Tests for the per-brand second-brain vault (Fable 5 rebuild)."""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents._lib.second_brain import SecondBrain


def _brand(tmp, slug="testbrand"):
    bdir = os.path.join(tmp, slug)
    os.makedirs(bdir, exist_ok=True)
    return bdir


def test_note_write_and_index():
    tmp = tempfile.mkdtemp()
    _brand(tmp)
    sb = SecondBrain("testbrand", brands_dir=tmp)
    name = sb.note("script-writer", "Pain hooks beat curiosity", "ER 4.2% vs 1.1%",
                   kind="insight", source="performance_history.json")
    assert name == "pain-hooks-beat-curiosity"
    assert "[[pain-hooks-beat-curiosity]]" in sb.read_index()


def test_sourceless_insight_refused():
    tmp = tempfile.mkdtemp()
    _brand(tmp)
    sb = SecondBrain("testbrand", brands_dir=tmp)
    assert sb.note("x", "vibes only", "no source") is None
    assert sb.note("human", "we pivot to english", "decision", kind="decision") is not None


def test_sync_renders_profile_archetype_learnings():
    tmp = tempfile.mkdtemp()
    bdir = _brand(tmp)
    json.dump({"brand_name": "T", "product": "tees", "platforms": ["ig"]},
              open(os.path.join(bdir, "brand_profile.json"), "w"))
    json.dump({"archetype": "product", "source": "heuristic", "confidence": 0.9,
               "signals": ["keyword 'tee'"]},
              open(os.path.join(bdir, "brand_archetype.json"), "w"))
    with open(os.path.join(bdir, "agent_learnings.jsonl"), "w") as f:
        f.write(json.dumps({"agent": "script-writer", "text": "carousels outperform reels", "ts": "2026-07-01T00:00:00"}) + "\n")
    sb = SecondBrain("testbrand", brands_dir=tmp)
    counts = sb.sync()
    assert counts["profile"] == 1 and counts["archetype"] == 1 and counts["learnings"] == 1


def test_context_block_traverses_links():
    tmp = tempfile.mkdtemp()
    bdir = _brand(tmp)
    json.dump({"brand_name": "T", "product": "tees"},
              open(os.path.join(bdir, "brand_profile.json"), "w"))
    sb = SecondBrain("testbrand", brands_dir=tmp)
    sb.sync()
    sb.note("script-writer", "drop hooks win", "scarcity framing +2x CTR",
            kind="insight", source="performance_history.json", links=["brand profile"])
    block = sb.context_block(agent="script-writer", query="which hooks win")
    assert "drop hooks win" in block and "Second Brain" in block
    # linked note pulled in via 1-hop traversal
    assert "brand profile" in block or "brand-profile" in block


def test_isolation_between_brands():
    tmp = tempfile.mkdtemp()
    _brand(tmp, "a"); _brand(tmp, "b")
    sa = SecondBrain("a", brands_dir=tmp)
    sa.note("x", "a secret", "text", kind="decision")
    sb = SecondBrain("b", brands_dir=tmp)
    assert sb.read_index() == "" and sb.context_block() == ""


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"{name} PASS")
