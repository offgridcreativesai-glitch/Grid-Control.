"""Pins the brand-book vault-dump bug (Jul 14): brand-book output must render the
human `narrative`, never a raw key dump of meta/brand/scores. Runnable with pytest
(once backend CI exists) or directly: `python3 utils/test_output_formatter.py`.
"""
from utils.output_formatter import format_for_notion

_BRAND_BOOK = {
    "meta": {"brand": "Third Gen Tribe", "slug": "third-gen-tribe", "version": "v7"},
    "brand": {"brand_slug": "third-gen-tribe", "instagram": {"username": "thirdgentribe", "followers": 418}},
    "scores": {"tiers": {"x": 1}},
    "narrative": {
        "headline": "Turn your Reels into a working sales door",
        "subhead": "Put the comment-to-DM ask on every Reel.",
        "exec_summary": ["You're at 418 followers — early runway, not failure."],
        "where_you_stand": "Engagement is 10.6; the niche middle is 3,341.",
        "white_space": "LinkedIn and X are empty lanes.",
        "your_playbook": ["Add 'comment a keyword -> I DM you the link' to every Reel."],
        "roadmap": {"month_1": {"title": "Wake up the account", "goal": "Do the two things the niche does."}},
    },
}


def test_brand_book_renders_narrative_not_raw_dump():
    out = format_for_notion("brand-book", _BRAND_BOOK)
    # Human narrative is present
    assert "Turn your Reels into a working sales door" in out
    assert "Executive Summary" in out
    assert "Your Playbook" in out
    assert "Wake up the account" in out
    # THE bug: raw structural keys must NOT leak into the client view
    assert "Slug:" not in out
    assert "Brand Slug:" not in out
    assert "Followers:" not in out
    assert "Tiers:" not in out


def test_brand_book_without_narrative_is_graceful():
    out = format_for_notion("brand-book", {"meta": {"slug": "x"}})
    assert "open the pdf" in out.lower()
    assert "Slug:" not in out


if __name__ == "__main__":
    test_brand_book_renders_narrative_not_raw_dump()
    test_brand_book_without_narrative_is_graceful()
    print("output_formatter brand-book tests passed")
