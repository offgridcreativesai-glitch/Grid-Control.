"""Phase 1 — Role model, Brain guardrails, cost governance, per-brand agent config.

Isolated pure-ish helpers so dashboard_api.py edits stay surgical and this logic is
unit-testable on its own. No Flask imports here.

Role taxonomy (D8/D9):
  operator        — Gaurav. Full control. Brain edit/bash ONLY when operator-mode ON.
  subscriber      — self-serve brand, full per-brand cockpit, NO operator tools.
  managed-client  — approve/reject + insights only, NO triggering, NO operator tools.
  agency-owner    — reserved for Mode 3 (white-label). Not built yet.

Capability rule (Layer-1 hard wall): only an OPERATOR with operator-mode toggled ON
may load propose_edit / propose_bash. Everyone else gets read-only/trigger-only Brain.
"""
from __future__ import annotations

import json
import re
import threading
import time
from pathlib import Path

OPERATOR = "operator"
SUBSCRIBER = "subscriber"
MANAGED_CLIENT = "managed-client"
AGENCY = "agency-owner"  # reserved (Mode 3)

# brand_members.role (DB) → grid role, for non-super-admin users.
_BRAND_ROLE_MAP = {
    "admin": SUBSCRIBER,
    "owner": SUBSCRIBER,
    "editor": SUBSCRIBER,
    "subscriber": SUBSCRIBER,
    "client": MANAGED_CLIENT,
    "viewer": MANAGED_CLIENT,
    "managed-client": MANAGED_CLIENT,
    "managed_client": MANAGED_CLIENT,
}


def resolve_grid_role(is_super_admin: bool, brand_role: str | None) -> str:
    """Map (super-admin flag, per-brand membership role) → grid role.
    Deny-by-default: unknown/None brand role for a non-admin → managed-client (most locked)."""
    if is_super_admin:
        return OPERATOR
    return _BRAND_ROLE_MAP.get((brand_role or "").strip().lower(), MANAGED_CLIENT)


# ── Operator-mode toggle (locked by default; every flip audit-logged by caller) ──
_operator_mode: dict[str, dict] = {}  # user_id -> {"on": bool, "since": float}
_op_lock = threading.Lock()


def set_operator_mode(user_id: str, on: bool) -> dict:
    with _op_lock:
        _operator_mode[user_id] = {"on": bool(on), "since": time.time()}
        return dict(_operator_mode[user_id])


def operator_mode_on(user_id: str | None) -> bool:
    if not user_id:
        return False
    with _op_lock:
        return bool(_operator_mode.get(user_id, {}).get("on"))


def brain_full_tools_allowed(is_super_admin: bool, user_id: str | None) -> bool:
    """Layer-1: edit/bash tools only for an operator who has explicitly enabled operator mode."""
    return bool(is_super_admin and operator_mode_on(user_id))


# ── Layer-2 topical / jailbreak pre-check (cheap heuristic, no model call) ────────
# Fires only for NON-operator-active sessions. Catches the obvious off-topic and
# prompt-injection attempts before the paid model runs.
_OFFTOPIC_PATTERNS = [
    r"\bwrite\s+(me\s+)?(a\s+|some\s+)?(python|javascript|typescript|java|c\+\+|c#|rust|golang|go|sql|php|ruby|bash|shell)\b",
    r"\bwrite\s+(me\s+)?(a\s+|some\s+)?(code|function|program|algorithm|regex)\b",
    r"\bbuild\s+(me\s+)?(an?\s+)?(app|application|website|web\s*site|game|api|bot|saas|platform|software)\b",
    r"\b(create|make|develop)\s+(an?\s+)?(app|application|website|game|mobile app|chatbot)\b",
    r"\bdebug\s+(this|my|the)\s+(code|program|function)\b",
    r"\bfix\s+(this|my)\s+(code|bug|error)\b",
    r"\b(solve|calculate|compute)\b.*\b(equation|integral|derivative|matrix|math problem|homework)\b",
    r"\b(recipe|how to cook|how to bake)\b",
    r"\b(essay|homework|poem|novel)\b",
    r"\b(invest|stock|crypto|trading|portfolio)\s+(advice|tip|recommendation)\b",
    # prompt-injection / exfiltration
    r"\bignore\s+(all\s+|your\s+|the\s+|any\s+)?(previous|above|prior)?\s*(instructions|rules|prompt)\b",
    r"\b(reveal|show|print|tell me)\s+(your\s+)?(system\s+prompt|instructions|api\s*key|env|\.env|secret|token)\b",
    r"\bdeveloper mode\b|\bjailbreak\b|\bDAN mode\b",
    r"\b(act|pretend|roleplay)\s+as\s+(a|an)\b.*\b(hacker|unrestricted|uncensored)\b",
]
_OFFTOPIC_RE = [re.compile(p, re.IGNORECASE) for p in _OFFTOPIC_PATTERNS]


def is_offtopic(text: str | None) -> bool:
    """True if the message clearly asks for non-marketing work or tries to jailbreak."""
    if not text:
        return False
    return any(rx.search(text) for rx in _OFFTOPIC_RE)


def offtopic_refusal(brand_name: str | None) -> str:
    label = brand_name or "your brand"
    return (
        f"I'm the marketing Brain for {label}. I can help with content strategy, "
        "performance insights, trends, competitors, and approvals — but not with "
        "coding, app-building, or general off-topic requests. What would you like to "
        "do for your brand?"
    )


# ── Brain cost governance — per-role daily token budgets ─────────────────────────
# 0 == unlimited. Operator is unlimited; clients/subscribers are capped to bound spend.
DAILY_TOKEN_BUDGET = {
    OPERATOR: 0,
    SUBSCRIBER: 300_000,
    MANAGED_CLIENT: 60_000,
    AGENCY: 0,
}


def over_token_budget(role: str, tokens_used_today: int) -> bool:
    budget = DAILY_TOKEN_BUDGET.get(role, 60_000)
    return budget > 0 and tokens_used_today >= budget


# ── Per-brand agent config (which of the 18 agents are on, + tuning) ─────────────
# Stored at brands/{slug}/agent_config.json. Absent file == every agent default-ON.
def agent_config_path(base_dir: str | Path, slug: str) -> Path:
    return Path(base_dir) / "brands" / slug / "agent_config.json"


def load_agent_config(base_dir: str | Path, slug: str) -> dict:
    p = agent_config_path(base_dir, slug)
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            pass
    return {"agents": {}, "updated_at": None, "_default": "all agents enabled"}


def agent_enabled(base_dir: str | Path, slug: str, agent_slug: str) -> bool:
    """An agent is enabled unless explicitly turned off in agent_config.json."""
    cfg = load_agent_config(base_dir, slug)
    entry = (cfg.get("agents") or {}).get(agent_slug)
    if isinstance(entry, dict):
        return bool(entry.get("enabled", True))
    if isinstance(entry, bool):
        return entry
    return True


def save_agent_config(base_dir: str | Path, slug: str, agents: dict) -> dict:
    """agents: { '<agent-slug>': {'enabled': bool, ...tuning} | bool }."""
    p = agent_config_path(base_dir, slug)
    p.parent.mkdir(parents=True, exist_ok=True)
    cfg = {"agents": agents or {}, "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    p.write_text(json.dumps(cfg, indent=2))
    return cfg
