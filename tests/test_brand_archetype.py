"""Tests for the STEP-0 brand archetype reasoning layer (Fable 5 rebuild)."""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents._lib import brand_archetype as ba


def test_product_classification():
    r = ba.classify_brand("t", {"product": "graphic t-shirts", "category": "apparel",
                                "shop_link": "x"}, brands_dir=tempfile.mkdtemp())
    assert r["archetype"] == "product"


def test_service_classification():
    r = ba.classify_brand("s", {"product": "AI reports", "category": "b2b saas service",
                                "pricing": "custom quote"}, brands_dir=tempfile.mkdtemp())
    assert r["archetype"] == "service"


def test_personal_classification():
    r = ba.classify_brand("p", {"founder_identity": "G", "lived_history_sources": ["x"],
                                "brand_type": "personal brand"}, brands_dir=tempfile.mkdtemp())
    assert r["archetype"] == "personal"


def test_no_signal_refuses_to_guess():
    r = ba.classify_brand("e", {}, brands_dir=tempfile.mkdtemp())
    assert r["archetype"] == "unknown" and r["confidence"] == 0.0


def test_declared_archetype_wins():
    r = ba.classify_brand("d", {"business_model_archetype": "product",
                                "brand_type": "personal brand"}, brands_dir=tempfile.mkdtemp())
    assert r["archetype"] == "product"


def test_human_pin_survives_reclassification():
    tmp = tempfile.mkdtemp()
    os.makedirs(os.path.join(tmp, "b"))
    with open(os.path.join(tmp, "b", "brand_archetype.json"), "w") as f:
        json.dump({"archetype": "personal", "source": "human", "confidence": 1.0}, f)
    r = ba.classify_brand("b", {"category": "apparel", "shop_link": "x"}, brands_dir=tmp)
    assert r["archetype"] == "personal"


def test_directive_blocks_differ_per_archetype():
    blocks = {a: ba.directive_block({"archetype": a, "source": "t", "confidence": 1.0})
              for a in ba.ARCHETYPES}
    assert "SHORT" in blocks["product"] and "LONG" in blocks["service"]
    assert "RELATIONSHIP" in blocks["personal"]
    assert len({b for b in blocks.values()}) == 3
    assert "UNRESOLVED" in ba.directive_block({"archetype": "unknown"})


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"{name} PASS")
