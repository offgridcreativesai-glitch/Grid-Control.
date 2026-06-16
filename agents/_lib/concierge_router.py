"""Phase J — Concierge (Chief of Staff) deterministic intent router.

The client talks to ONE agent (the Chief of Staff), never the 6 roles directly.
This module is the TRIVIAL tier: it classifies a message with pure regex — NO LLM
spin-up — so deterministic asks ("what needs approval?", "team status", "pause the
DM hunter") never cost a token.

Tiers returned by `classify()`:
  - "trivial" + safe_execute=True   → a READ-ONLY ask the caller answers from local
                                       state with no LLM and no side effects.
  - "trivial" + safe_execute=False  → a recognised STATE-CHANGING ask (approve / reject
                                       / pause). We DO NOT execute it here — the caller
                                       routes the user to the existing explicit endpoint
                                       (approval-everywhere law, Phase K1). A loose regex
                                       must never auto-publish.
  - "substantive"                   → re-plan / new angle / inject a trend. The caller
                                       dispatches the Brain LLM + the right specialist,
                                       result lands in the approval dashboard.

Pure functions, $0, unit-testable. No imports beyond `re`.
"""
from __future__ import annotations

import re

# READ-ONLY intents — safe to answer with no LLM and no side effects.
# Each maps to (patterns, GET data source the caller reads from).
_READ_PATTERNS: dict[str, tuple[list[str], str | None]] = {
    "list_pending": ([
        r"what'?s? (is |are )?(in the )?(queue|pending|waiting)",
        r"needs? (my )?approv",
        r"\bpending\b",
        r"anything (for me|to approve|need)",
    ], None),  # answered inline from local state (no HTTP needed)
    "team_status": ([
        r"\b(team|agent)s? status\b",
        r"what'?s? (the team|everyone|the agents?) (working|doing|up to)",
        r"who'?s? (working|running|busy)",
        r"\bstatus\b",
    ], "/api/agents/status"),
    "cost_status": ([
        r"\b(cost|spend|spent|tokens?)\b.*\b(today|so far|this week|this month)\b",
        r"how much (have we|did we|has it) (spent|cost)",
        r"what'?s? (the|our) (spend|cost|token)",
    ], "/api/billing/usage"),
}

# STATE-CHANGING intents — recognised but NOT executed here. Routed to the
# dedicated, already-gated endpoint so the approval law is never bypassed.
# Only intents whose endpoint EXISTS today are listed; pause/resume-agent are
# deferred until those endpoints are built (else we'd point the client at a 404).
_ACTION_PATTERNS: dict[str, tuple[list[str], str]] = {
    # intent: (patterns, endpoint the caller should send the user to)
    "approve":      ([r"\bapprove\b", r"\bship it\b", r"\bgo ahead and post\b"], "/api/outputs/approve"),
    "reject":       ([r"\breject\b", r"\bkill (the|that|this)\b", r"\bdiscard\b"], "/api/outputs/reject"),
    "request_change": ([r"\b(change|revise|tweak|edit)\b.*\b(this|that|the post|the carousel|the reel|caption)\b"], "/api/outputs/revise"),
}


def _matches(text: str, patterns: list[str]) -> bool:
    return any(re.search(p, text) for p in patterns)


def classify(message: str) -> dict:
    """Classify a concierge message into a tier + intent. Pure, no side effects.

    Returns: { tier, intent, safe_execute, endpoint }
      tier ∈ {"trivial", "substantive"}; intent is None for substantive.
    """
    m = (message or "").strip().lower()
    if not m:
        return {"tier": "substantive", "intent": None, "safe_execute": False, "endpoint": None}

    # READ-ONLY first — these are the only intents safe to auto-answer.
    for intent, (pats, data_endpoint) in _READ_PATTERNS.items():
        if _matches(m, pats):
            return {"tier": "trivial", "intent": intent, "safe_execute": True, "endpoint": data_endpoint}

    # STATE-CHANGING — recognised, routed to the gated endpoint, never executed here.
    for intent, (pats, endpoint) in _ACTION_PATTERNS.items():
        if _matches(m, pats):
            return {"tier": "trivial", "intent": intent, "safe_execute": False, "endpoint": endpoint}

    # Everything else needs reasoning → the Brain LLM + a specialist.
    return {"tier": "substantive", "intent": None, "safe_execute": False, "endpoint": None}
