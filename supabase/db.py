"""
supabase/db.py — GRID CONTROL Supabase Integration Layer

Two clients:
  _admin  — service_role key, bypasses RLS. Used by Flask backend for agent ops.
  _public — anon key + user JWT. Used for user-scoped queries from dashboard.

All functions return None on failure.
"""

import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv(
    dotenv_path=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"),
    override=True
)

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "").strip()
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be set in .env")

_public: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

_admin: Client | None = None
if SUPABASE_SERVICE_ROLE_KEY:
    _admin = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

def _svc() -> Client:
    """Return admin client (service_role, bypasses RLS). Falls back to public."""
    return _admin or _public


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Auth Helpers ─────────────────────────────────────────────────────────────

def verify_jwt(token: str) -> dict | None:
    """Verify a Supabase JWT and return the user object. None if invalid."""
    try:
        user = _public.auth.get_user(token)
        return {"id": user.user.id, "email": user.user.email} if user and user.user else None
    except Exception:
        return None


def get_user_brands(user_id: str) -> list[dict]:
    """Return all brands the user is a member of."""
    try:
        res = (
            _svc().table("brand_members")
            .select("brand_id, role, brands(id, slug, name, profile, created_at)")
            .eq("user_id", user_id)
            .execute()
        )
        return res.data or []
    except Exception as e:
        print(f"[db] get_user_brands error: {e}")
        return []


def check_brand_access(user_id: str, brand_id: str) -> str | None:
    """Return user's role for a brand, or None if no access."""
    try:
        res = (
            _svc().table("brand_members")
            .select("role")
            .eq("user_id", user_id)
            .eq("brand_id", brand_id)
            .single()
            .execute()
        )
        return res.data["role"] if res.data else None
    except Exception:
        return None


def create_brand_with_owner(slug: str, name: str, profile_dict: dict, owner_user_id: str) -> dict | None:
    """Create a brand and add the creator as admin. Returns the brand row."""
    try:
        brand = upsert_brand(slug, name, profile_dict)
        if not brand:
            return None
        _svc().table("brand_members").insert({
            "brand_id": brand["id"],
            "user_id": owner_user_id,
            "role": "admin",
        }).execute()
        return brand
    except Exception as e:
        print(f"[db] create_brand_with_owner error: {e}")
        return None


def add_brand_member(brand_id: str, user_email: str, role: str = "editor") -> dict | None:
    """Add a user to a brand by email. Returns the membership row."""
    try:
        user_res = _svc().table("profiles").select("id").eq("email", user_email).single().execute()
        if not user_res.data:
            return None
        res = _svc().table("brand_members").upsert({
            "brand_id": brand_id,
            "user_id": user_res.data["id"],
            "role": role,
        }, on_conflict="brand_id,user_id").execute()
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"[db] add_brand_member error: {e}")
        return None


def get_profile(user_id: str) -> dict | None:
    """Return user profile."""
    try:
        res = _svc().table("profiles").select("*").eq("id", user_id).single().execute()
        return res.data
    except Exception:
        return None


# ── Brands ────────────────────────────────────────────────────────────────────

def upsert_brand(slug: str, name: str, profile_dict: dict) -> dict | None:
    try:
        res = (
            _svc().table("brands")
            .upsert({"slug": slug, "name": name, "profile": profile_dict}, on_conflict="slug")
            .execute()
        )
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"[db] upsert_brand error: {e}")
        return None


def get_brand(slug: str) -> dict | None:
    try:
        res = _svc().table("brands").select("*").eq("slug", slug).single().execute()
        return res.data
    except Exception as e:
        print(f"[db] get_brand error: {e}")
        return None


# ── Agent Runs ────────────────────────────────────────────────────────────────

def get_agent_run(run_id: str) -> dict | None:
    try:
        res = _svc().table("agent_runs").select("*").eq("id", run_id).single().execute()
        return res.data
    except Exception as e:
        print(f"[db] get_agent_run error: {e}")
        return None


def save_agent_run(brand_id: str, agent_slug: str) -> dict | None:
    try:
        res = (
            _svc().table("agent_runs")
            .insert({"brand_id": brand_id, "agent_slug": agent_slug, "status": "running"})
            .execute()
        )
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"[db] save_agent_run error: {e}")
        return None


def update_agent_run_status(run_id: str, status: str, error: str | None = None) -> dict | None:
    try:
        payload: dict = {"status": status, "completed_at": _now()}
        if error:
            payload["error"] = error
        res = (
            _svc().table("agent_runs")
            .update(payload)
            .eq("id", run_id)
            .execute()
        )
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"[db] update_agent_run_status error: {e}")
        return None


# ── Agent Outputs ─────────────────────────────────────────────────────────────

def save_agent_output(
    brand_id: str,
    agent_run_id: str,
    agent_slug: str,
    output_type: str,
    raw_output: dict,
    formatted_output: dict | None = None,
    loop_header: dict | None = None,
) -> dict | None:
    try:
        payload = {
            "brand_id": brand_id,
            "agent_run_id": agent_run_id,
            "agent_slug": agent_slug,
            "output_type": output_type,
            "raw_output": raw_output,
            "formatted_output": formatted_output or {},
            "approval_status": "pending",
        }
        if loop_header:
            payload["formatted_output"]["loop_header"] = loop_header
        res = _svc().table("agent_outputs").insert(payload).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"[db] save_agent_output error: {e}")
        return None


def get_pending_outputs(brand_id: str) -> list[dict]:
    try:
        res = (
            _svc().table("agent_outputs")
            .select("*")
            .eq("brand_id", brand_id)
            .eq("approval_status", "pending")
            .order("created_at", desc=True)
            .execute()
        )
        return res.data or []
    except Exception as e:
        print(f"[db] get_pending_outputs error: {e}")
        return []


def approve_output(output_id: str) -> dict | None:
    try:
        res = (
            _svc().table("agent_outputs")
            .update({"approval_status": "approved", "approved_at": _now()})
            .eq("id", output_id)
            .execute()
        )
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"[db] approve_output error: {e}")
        return None


def reject_output(output_id: str) -> dict | None:
    try:
        res = (
            _svc().table("agent_outputs")
            .update({"approval_status": "rejected"})
            .eq("id", output_id)
            .execute()
        )
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"[db] reject_output error: {e}")
        return None


def get_output_history(brand_id: str, agent_slug: str) -> list[dict]:
    try:
        res = (
            _svc().table("agent_outputs")
            .select("id, created_at, approval_status, output_type")
            .eq("brand_id", brand_id)
            .eq("agent_slug", agent_slug)
            .order("created_at", desc=True)
            .execute()
        )
        return res.data or []
    except Exception as e:
        print(f"[db] get_output_history error: {e}")
        return []


def update_output_notion_id(output_id: str, notion_page_id: str) -> dict | None:
    try:
        res = _svc().table("agent_outputs").select("formatted_output").eq("id", output_id).single().execute()
        if not res.data:
            return None
        formatted = res.data.get("formatted_output") or {}
        formatted["notion_page_id"] = notion_page_id
        formatted["notion_url"] = f"https://notion.so/{notion_page_id.replace('-', '')}"
        res2 = (
            _svc().table("agent_outputs")
            .update({"formatted_output": formatted})
            .eq("id", output_id)
            .execute()
        )
        return res2.data[0] if res2.data else None
    except Exception as e:
        print(f"[db] update_output_notion_id error: {e}")
        return None


def get_outputs_by_agent(brand_id: str, agent_slug: str, approval_status: str | None = None) -> list[dict]:
    try:
        q = (
            _svc().table("agent_outputs")
            .select("*")
            .eq("brand_id", brand_id)
            .eq("agent_slug", agent_slug)
            .order("created_at", desc=True)
        )
        if approval_status:
            q = q.eq("approval_status", approval_status)
        res = q.execute()
        return res.data or []
    except Exception as e:
        print(f"[db] get_outputs_by_agent error: {e}")
        return []


# ── Session State ─────────────────────────────────────────────────────────────

def get_session_state(brand_id: str) -> dict:
    try:
        res = (
            _svc().table("session_state")
            .select("state")
            .eq("brand_id", brand_id)
            .execute()
        )
        if res.data:
            return res.data[0].get("state", {})
        return {}
    except Exception as e:
        print(f"[db] get_session_state error: {e}")
        return {}


def upsert_session_state(brand_id: str, state: dict) -> dict | None:
    try:
        existing = _svc().table("session_state").select("id").eq("brand_id", brand_id).execute()
        if existing.data:
            res = (
                _svc().table("session_state")
                .update({"state": state, "updated_at": _now()})
                .eq("brand_id", brand_id)
                .execute()
            )
        else:
            res = (
                _svc().table("session_state")
                .insert({"brand_id": brand_id, "state": state, "updated_at": _now()})
                .execute()
            )
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"[db] upsert_session_state error: {e}")
        return None


# ── Conversations ─────────────────────────────────────────────────────────────

def save_conversation(brand_id: str, agent_slug: str, messages_list: list) -> dict | None:
    try:
        existing = (
            _svc().table("conversations")
            .select("id")
            .eq("brand_id", brand_id)
            .eq("agent_slug", agent_slug)
            .execute()
        )
        if existing.data:
            row_id = existing.data[0]["id"]
            res = (
                _svc().table("conversations")
                .update({"messages": messages_list, "updated_at": _now()})
                .eq("id", row_id)
                .execute()
            )
        else:
            res = (
                _svc().table("conversations")
                .insert({
                    "brand_id": brand_id,
                    "agent_slug": agent_slug,
                    "messages": messages_list,
                    "updated_at": _now(),
                })
                .execute()
            )
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"[db] save_conversation error: {e}")
        return None


def get_conversation(brand_id: str, agent_slug: str) -> list:
    try:
        res = (
            _svc().table("conversations")
            .select("messages")
            .eq("brand_id", brand_id)
            .eq("agent_slug", agent_slug)
            .execute()
        )
        if res.data:
            return res.data[0].get("messages", [])
        return []
    except Exception as e:
        print(f"[db] get_conversation error: {e}")
        return []


# ── Cost Tracking ─────────────────────────────────────────────────────────────

_PRICING: dict[str, dict[str, float]] = {
    "claude-sonnet-4-6":        {"input": 3.00,  "output": 15.00},
    "claude-opus-4-6":          {"input": 15.00, "output": 75.00},
    "claude-haiku-4-5-20251001":{"input": 0.80,  "output": 4.00},
}
_DEFAULT_PRICING = {"input": 3.00, "output": 15.00}

FAL_COST_PER_IMAGE  = 0.008
APIFY_COST_PER_RUN  = 0.35


def calc_api_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    p = _PRICING.get(model, _DEFAULT_PRICING)
    return (input_tokens * p["input"] + output_tokens * p["output"]) / 1_000_000


def update_agent_run_costs(
    run_id: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    fal_generations: int = 0,
    apify_runs: int = 0,
) -> dict | None:
    try:
        api_cost   = calc_api_cost(model, input_tokens, output_tokens)
        fal_cost   = fal_generations * FAL_COST_PER_IMAGE
        apify_cost = apify_runs      * APIFY_COST_PER_RUN
        res = (
            _svc().table("agent_runs")
            .update({
                "model":           model,
                "input_tokens":    input_tokens,
                "output_tokens":   output_tokens,
                "api_cost_usd":    round(api_cost,   6),
                "fal_cost_usd":    round(fal_cost,   6),
                "apify_cost_usd":  round(apify_cost, 6),
                "fal_generations": fal_generations,
                "apify_runs":      apify_runs,
            })
            .eq("id", run_id)
            .execute()
        )
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"[db] update_agent_run_costs error: {e}")
        return None


def get_brand_monthly_costs(brand_id: str, year: int, month: int) -> dict:
    try:
        from_dt = f"{year:04d}-{month:02d}-01T00:00:00+00:00"
        import calendar
        last_day = calendar.monthrange(year, month)[1]
        to_dt    = f"{year:04d}-{month:02d}-{last_day:02d}T23:59:59+00:00"

        res = (
            _svc().table("agent_runs")
            .select(
                "agent_slug, model, input_tokens, output_tokens, "
                "api_cost_usd, fal_cost_usd, apify_cost_usd, "
                "fal_generations, apify_runs, status, created_at"
            )
            .eq("brand_id", brand_id)
            .eq("status", "done")
            .gte("created_at", from_dt)
            .lte("created_at", to_dt)
            .execute()
        )
        rows = res.data or []

        agents: dict[str, dict] = {}
        for r in rows:
            slug = r.get("agent_slug", "unknown")
            if slug not in agents:
                agents[slug] = {
                    "agent_slug": slug, "runs": 0,
                    "input_tokens": 0, "output_tokens": 0,
                    "api_cost_usd": 0.0, "fal_cost_usd": 0.0, "apify_cost_usd": 0.0,
                    "fal_generations": 0, "apify_runs": 0,
                }
            a = agents[slug]
            a["runs"]            += 1
            a["input_tokens"]    += r.get("input_tokens", 0) or 0
            a["output_tokens"]   += r.get("output_tokens", 0) or 0
            a["api_cost_usd"]    += float(r.get("api_cost_usd", 0) or 0)
            a["fal_cost_usd"]    += float(r.get("fal_cost_usd", 0) or 0)
            a["apify_cost_usd"]  += float(r.get("apify_cost_usd", 0) or 0)
            a["fal_generations"] += r.get("fal_generations", 0) or 0
            a["apify_runs"]      += r.get("apify_runs", 0) or 0

        agent_list = sorted(agents.values(), key=lambda x: x["api_cost_usd"], reverse=True)
        total_api   = sum(a["api_cost_usd"]   for a in agent_list)
        total_fal   = sum(a["fal_cost_usd"]   for a in agent_list)
        total_apify = sum(a["apify_cost_usd"] for a in agent_list)

        return {
            "year": year, "month": month,
            "agents": agent_list,
            "totals": {
                "api_cost_usd":   round(total_api,   4),
                "fal_cost_usd":   round(total_fal,   4),
                "apify_cost_usd": round(total_apify, 4),
                "total_usd":      round(total_api + total_fal + total_apify, 4),
                "total_runs":     len(rows),
            },
        }
    except Exception as e:
        print(f"[db] get_brand_monthly_costs error: {e}")
        return {"year": year, "month": month, "agents": [], "totals": {}}


# ── Brand Memory (pgvector) ────────────────────────────────────────────────────

def save_brand_memory(
    brand_id: str, agent_slug: str, memory_key: str, content: str,
    embedding: list[float] | None = None,
) -> dict | None:
    try:
        payload: dict = {
            "brand_id": brand_id, "agent_slug": agent_slug,
            "memory_key": memory_key, "content": content, "updated_at": _now(),
        }
        if embedding:
            payload["embedding"] = embedding
        res = (
            _svc().table("brand_memory")
            .upsert(payload, on_conflict="brand_id,agent_slug,memory_key")
            .execute()
        )
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"[db] save_brand_memory error: {e}")
        return None


def get_brand_memory(brand_id: str, agent_slug: str) -> list[dict]:
    try:
        res = (
            _svc().table("brand_memory")
            .select("memory_key, content, updated_at")
            .eq("brand_id", brand_id)
            .eq("agent_slug", agent_slug)
            .order("updated_at", desc=True)
            .execute()
        )
        return res.data or []
    except Exception as e:
        print(f"[db] get_brand_memory error: {e}")
        return []


def get_all_brand_memory(brand_id: str) -> list[dict]:
    try:
        res = (
            _svc().table("brand_memory")
            .select("agent_slug, memory_key, content, updated_at")
            .eq("brand_id", brand_id)
            .order("updated_at", desc=True)
            .execute()
        )
        return res.data or []
    except Exception as e:
        print(f"[db] get_all_brand_memory error: {e}")
        return []


# ── Audit Log ─────────────────────────────────────────────────────────────────

def log_audit(brand_id: str, action: str, actor: str = "system", payload: dict | None = None) -> dict | None:
    try:
        res = (
            _svc().table("audit_log")
            .insert({
                "brand_id": brand_id, "action": action,
                "actor": actor, "payload": payload or {},
            })
            .execute()
        )
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"[db] log_audit error: {e}")
        return None
