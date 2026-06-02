"""
Platform publisher registry — the generic spine of create → approve → publish.

This is the scaffold's source of truth for *which platforms can actually post*.
A platform is only "built" when it has real, tested publishing code wired in.
Everything else returns an honest "publisher not built yet" — never a fabricated
success. (Zero-assumption rule: no fake post IDs, no pretend permalinks.)

A live *connection* (token verifies) is necessary but not sufficient to publish —
the posting code for that platform also has to exist. The Review pipeline uses
`is_built()` to decide whether the Publish button is live or shows "publisher pending".
"""
from __future__ import annotations

# Every platform AskGauravAI posts to. Order = display order in the pipeline.
ALL_PLATFORMS = ["instagram", "linkedin", "youtube", "twitter"]

# Platforms with a real publisher wired into the publish endpoint.
# instagram = carousel · linkedin/twitter = text · youtube = real video upload
# (youtube routes, but returns 'needs_video' until a real founder video is provided).
BUILT_PUBLISHERS = {"instagram", "linkedin", "twitter", "youtube"}


def is_built(platform: str) -> bool:
    return (platform or "").strip().lower() in BUILT_PUBLISHERS


def unbuilt_result(platform: str) -> dict:
    """The honest response for a platform whose connection is live but whose
    posting code hasn't been written yet."""
    return {
        "published": False,
        "mode": "unbuilt",
        "platform": platform,
        "error": f"{platform} publisher not built yet",
        "note": (
            "Connection can be live, but the posting code for this platform is "
            "the next build step. Nothing was sent."
        ),
    }
