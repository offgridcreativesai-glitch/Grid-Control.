"""routes/connections.py — GRID CONTROL connections endpoints (blueprint). S2b split."""
from core import *  # noqa: F401,F403  (app, helpers, stdlib re-exports)
from flask import Blueprint, redirect as _redirect

import hmac as _hmac
import hashlib as _hashlib
import base64 as _b64
import time as _time
import secrets as _secrets
from urllib.parse import quote as _urlquote

bp = Blueprint("connections", __name__)


# ── Instagram Login OAuth (Instagram API with Instagram Login) ────────────────
# Modern path: an IG Professional account authorizes directly — no Facebook
# account or Page needed. Two endpoints:
#   GET /api/connections/instagram/authorize-url  (auth'd) → signed consent URL
#   GET /api/connections/instagram/callback       (public) → exchange + store
# The browser-facing callback can't carry our auth header, so it is protected by
# an HMAC-signed `state` instead.

def _oauth_secret() -> str:
    return (os.getenv("DASHBOARD_SECRET") or os.getenv("META_APP_SECRET") or "grid-oauth").strip()


def _ig_redirect_uri() -> str:
    """The exact callback Meta must have whitelisted. Driven by the HTTPS tunnel."""
    base = (os.getenv("OAUTH_PUBLIC_BASE_URL") or "").strip().rstrip("/")
    return f"{base}/api/connections/instagram/callback"


def _ig_return_url() -> str:
    """Where the browser lands in the dashboard after the round trip."""
    return (os.getenv("OAUTH_RETURN_URL") or "http://localhost:5280/connections").strip()


def _sign_state(brand_slug: str, extra: str = "") -> str:
    """Stateless CSRF token: base64(brand_slug|ts|extra).sig — survives the round trip.
    `extra` carries per-flow data (e.g. the X PKCE verifier) so we stay stateless."""
    payload = f"{brand_slug}|{int(_time.time())}|{extra}"
    sig = _hmac.new(_oauth_secret().encode(), payload.encode(), _hashlib.sha256).hexdigest()
    return _b64.urlsafe_b64encode(payload.encode()).decode().rstrip("=") + "." + sig


def _verify_state(state: str, max_age: int = 900):
    """Validate a signed state; return (brand_slug, extra) if valid + fresh, else None."""
    try:
        b64, sig = state.split(".", 1)
        payload = _b64.urlsafe_b64decode(b64 + "=" * (-len(b64) % 4)).decode()
        expect = _hmac.new(_oauth_secret().encode(), payload.encode(), _hashlib.sha256).hexdigest()
        if not _hmac.compare_digest(sig, expect):
            return None
        parts = payload.split("|")
        brand_slug, ts = parts[0], int(parts[1])
        extra = parts[2] if len(parts) > 2 else ""
        if _time.time() - ts > max_age:
            return None
        return (brand_slug, extra)
    except Exception:
        return None


@bp.route("/api/connections/instagram/authorize-url", methods=["GET"])
@require_auth
def instagram_authorize_url():
    """Return the Instagram consent URL for a brand (FE then navigates to it)."""
    from publishing.instagram_login import build_authorize_url, app_credentials

    brand_slug = (request.args.get("brand_slug") or "").strip()
    if not brand_slug:
        return jsonify({"success": False, "error": "brand_slug required"}), 400

    app_id, secret = app_credentials()
    if not app_id or not secret:
        return jsonify({"success": False,
                        "error": "INSTAGRAM_APP_ID / INSTAGRAM_APP_SECRET (or META_APP_ID / "
                                 "META_APP_SECRET) not set in .env"}), 500
    if not (os.getenv("OAUTH_PUBLIC_BASE_URL") or "").strip():
        return jsonify({"success": False,
                        "error": "OAUTH_PUBLIC_BASE_URL not set (the HTTPS tunnel base URL)"}), 500

    url = build_authorize_url(_ig_redirect_uri(), _sign_state(brand_slug))
    return jsonify({"success": True, "data": {"url": url, "redirect_uri": _ig_redirect_uri()}})


@bp.route("/api/connections/instagram/callback", methods=["GET"])
def instagram_callback():
    """Public OAuth landing: validate state, exchange code, store long-lived token."""
    from publishing.instagram_login import exchange_code, long_lived_token

    def _bounce(status: str, detail: str = "") -> object:
        sep = "&" if "?" in _ig_return_url() else "?"
        q = f"ig={status}"
        if detail:
            q += f"&ig_detail={_urlquote(detail)[:160]}"
        return _redirect(f"{_ig_return_url()}{sep}{q}")

    err = request.args.get("error_description") or request.args.get("error")
    if err:
        return _bounce("denied", err)

    code  = (request.args.get("code") or "").strip()
    state = (request.args.get("state") or "").strip()
    if not code or not state:
        return _bounce("error", "missing code/state")

    res = _verify_state(state)
    if not res:
        return _bounce("error", "invalid or expired state")
    brand_slug = res[0]

    try:
        short = exchange_code(code, _ig_redirect_uri())
        long  = long_lived_token(short["access_token"])
        token = long["access_token"]
        _write_brand_env_token(brand_slug, "META_GRAPH_API_TOKEN", token)
        if short.get("user_id"):
            _write_brand_env_token(brand_slug, "IG_USER_ID", short["user_id"])
    except Exception as exc:
        return _bounce("error", str(exc))

    status = _verify_social("instagram", token)
    if not status.get("connected"):
        return _bounce("error", status.get("account", "verify failed"))
    return _bounce("connected", status.get("account", ""))


# ── YouTube OAuth (Google web flow) ───────────────────────────────────────────
# Same shape as Instagram: authd authorize-url + public HMAC-state callback.
# Stores the durable refresh token (+ client id/secret) in brands/<slug>/.env so
# _verify_youtube_oauth() can mint access tokens later.

def _yt_redirect_uri() -> str:
    base = (os.getenv("OAUTH_PUBLIC_BASE_URL") or "").strip().rstrip("/")
    return f"{base}/api/connections/youtube/callback"


def _platform_bounce(platform_key: str, status: str, detail: str = "") -> object:
    """Redirect the browser back to the dashboard with ?<key>=<status>."""
    ret = _ig_return_url()
    sep = "&" if "?" in ret else "?"
    q = f"{platform_key}={status}"
    if detail:
        q += f"&{platform_key}_detail={_urlquote(detail)[:160]}"
    return _redirect(f"{ret}{sep}{q}")


@bp.route("/api/connections/youtube/authorize-url", methods=["GET"])
@require_auth
def youtube_authorize_url():
    """Return the Google consent URL for connecting a brand's YouTube channel."""
    from publishing.youtube_login import build_authorize_url, app_credentials

    brand_slug = (request.args.get("brand_slug") or "").strip()
    if not brand_slug:
        return jsonify({"success": False, "error": "brand_slug required"}), 400

    client_id, secret = app_credentials()
    if not client_id or not secret:
        return jsonify({"success": False,
                        "error": "YOUTUBE_CLIENT_ID / YOUTUBE_CLIENT_SECRET not set in .env"}), 500
    if not (os.getenv("OAUTH_PUBLIC_BASE_URL") or "").strip():
        return jsonify({"success": False,
                        "error": "OAUTH_PUBLIC_BASE_URL not set (the HTTPS tunnel base URL)"}), 500

    url = build_authorize_url(_yt_redirect_uri(), _sign_state(brand_slug))
    return jsonify({"success": True, "data": {"url": url, "redirect_uri": _yt_redirect_uri()}})


@bp.route("/api/connections/youtube/callback", methods=["GET"])
def youtube_callback():
    """Public OAuth landing: validate state, exchange code, store refresh token."""
    from publishing.youtube_login import exchange_code, app_credentials

    err = request.args.get("error_description") or request.args.get("error")
    if err:
        return _platform_bounce("yt", "denied", err)

    code  = (request.args.get("code") or "").strip()
    state = (request.args.get("state") or "").strip()
    if not code or not state:
        return _platform_bounce("yt", "error", "missing code/state")

    res = _verify_state(state)
    if not res:
        return _platform_bounce("yt", "error", "invalid or expired state")
    brand_slug = res[0]

    try:
        client_id, secret = app_credentials()
        result = exchange_code(code, _yt_redirect_uri())
        # Persist refresh token + the client creds the verifier needs (per-brand).
        _write_brand_env_token(brand_slug, "YOUTUBE_REFRESH_TOKEN", result["refresh_token"])
        _write_brand_env_token(brand_slug, "YOUTUBE_CLIENT_ID", client_id)
        _write_brand_env_token(brand_slug, "YOUTUBE_CLIENT_SECRET", secret)
    except Exception as exc:
        return _platform_bounce("yt", "error", str(exc))

    status = _verify_youtube_oauth(brand_env(brand_slug))
    if not status.get("connected"):
        return _platform_bounce("yt", "error", status.get("account", "verify failed"))
    return _platform_bounce("yt", "connected", status.get("account", ""))


# ── LinkedIn OAuth 2.0 ────────────────────────────────────────────────────────

def _li_redirect_uri() -> str:
    base = (os.getenv("OAUTH_PUBLIC_BASE_URL") or "").strip().rstrip("/")
    return f"{base}/api/connections/linkedin/callback"


@bp.route("/api/connections/linkedin/authorize-url", methods=["GET"])
@require_auth
def linkedin_authorize_url():
    from publishing.linkedin_login import build_authorize_url, app_credentials
    brand_slug = (request.args.get("brand_slug") or "").strip()
    if not brand_slug:
        return jsonify({"success": False, "error": "brand_slug required"}), 400
    client_id, secret = app_credentials()
    if not client_id or not secret:
        return jsonify({"success": False, "error": "LINKEDIN_CLIENT_ID / LINKEDIN_CLIENT_SECRET not set in .env"}), 500
    if not (os.getenv("OAUTH_PUBLIC_BASE_URL") or "").strip():
        return jsonify({"success": False, "error": "OAUTH_PUBLIC_BASE_URL not set (the HTTPS tunnel base URL)"}), 500
    url = build_authorize_url(_li_redirect_uri(), _sign_state(brand_slug))
    return jsonify({"success": True, "data": {"url": url, "redirect_uri": _li_redirect_uri()}})


@bp.route("/api/connections/linkedin/callback", methods=["GET"])
def linkedin_callback():
    from publishing.linkedin_login import exchange_code
    err = request.args.get("error_description") or request.args.get("error")
    if err:
        return _platform_bounce("li", "denied", err)
    code  = (request.args.get("code") or "").strip()
    state = (request.args.get("state") or "").strip()
    if not code or not state:
        return _platform_bounce("li", "error", "missing code/state")
    res = _verify_state(state)
    if not res:
        return _platform_bounce("li", "error", "invalid or expired state")
    brand_slug = res[0]
    try:
        out = exchange_code(code, _li_redirect_uri())
        _write_brand_env_token(brand_slug, "LINKEDIN_ACCESS_TOKEN", out["access_token"])
        if out.get("urn"):
            _write_brand_env_token(brand_slug, "LINKEDIN_URN", out["urn"])
    except Exception as exc:
        return _platform_bounce("li", "error", str(exc))
    status = _verify_social("linkedin", out["access_token"])
    if not status.get("connected"):
        return _platform_bounce("li", "error", status.get("account", "verify failed"))
    return _platform_bounce("li", "connected", status.get("account", ""))


# ── X (Twitter) OAuth 2.0 + PKCE (read-only; publishing stays manual) ─────────

def _tw_redirect_uri() -> str:
    base = (os.getenv("OAUTH_PUBLIC_BASE_URL") or "").strip().rstrip("/")
    return f"{base}/api/connections/twitter/callback"


@bp.route("/api/connections/twitter/authorize-url", methods=["GET"])
@require_auth
def twitter_authorize_url():
    from publishing.twitter_login import build_authorize_url, app_credentials
    brand_slug = (request.args.get("brand_slug") or "").strip()
    if not brand_slug:
        return jsonify({"success": False, "error": "brand_slug required"}), 400
    client_id, secret = app_credentials()
    if not client_id or not secret:
        return jsonify({"success": False, "error": "TWITTER_OAUTH_CLIENT_ID / TWITTER_OAUTH_CLIENT_SECRET not set in .env"}), 500
    if not (os.getenv("OAUTH_PUBLIC_BASE_URL") or "").strip():
        return jsonify({"success": False, "error": "OAUTH_PUBLIC_BASE_URL not set (the HTTPS tunnel base URL)"}), 500
    verifier = _secrets.token_urlsafe(48)  # PKCE (plain) — carried in signed state
    url = build_authorize_url(_tw_redirect_uri(), _sign_state(brand_slug, verifier), verifier)
    return jsonify({"success": True, "data": {"url": url, "redirect_uri": _tw_redirect_uri()}})


@bp.route("/api/connections/twitter/callback", methods=["GET"])
def twitter_callback():
    from publishing.twitter_login import exchange_code
    err = request.args.get("error_description") or request.args.get("error")
    if err:
        return _platform_bounce("tw", "denied", err)
    code  = (request.args.get("code") or "").strip()
    state = (request.args.get("state") or "").strip()
    if not code or not state:
        return _platform_bounce("tw", "error", "missing code/state")
    res = _verify_state(state)
    if not res:
        return _platform_bounce("tw", "error", "invalid or expired state")
    brand_slug, verifier = res
    try:
        out = exchange_code(code, _tw_redirect_uri(), verifier)
        _write_brand_env_token(brand_slug, "TWITTER_BEARER_TOKEN", out["access_token"])
        if out.get("refresh_token"):
            _write_brand_env_token(brand_slug, "TWITTER_OAUTH2_REFRESH", out["refresh_token"])
    except Exception as exc:
        return _platform_bounce("tw", "error", str(exc))
    status = _verify_social("twitter", out["access_token"])
    if not status.get("connected"):
        return _platform_bounce("tw", "error", status.get("account", "verify failed"))
    return _platform_bounce("tw", "connected", status.get("account", ""))



# ── VOICE PROFILE ENDPOINTS ───────────────────────────────────────────────────

@bp.route("/api/voice/extract-profile", methods=["POST"])
@require_auth
def voice_extract_profile():
    """
    Extract voice DNA from raw script samples.
    Calls Claude to analyze writing patterns, saves voice_profile.json.
    Body: {brand_slug, raw_scripts}
    """
    data        = request.get_json(silent=True) or {}
    brand_slug  = data.get("brand_slug", "").strip()
    raw_scripts = data.get("raw_scripts", "").strip()

    if not brand_slug:
        return jsonify({"success": False, "error": "brand_slug required"}), 400
    if not raw_scripts:
        return jsonify({"success": False, "error": "raw_scripts required"}), 400
    if not get_brand_dir(brand_slug):
        return jsonify({"success": False, "error": f"Brand '{brand_slug}' not found"}), 404

    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not anthropic_key:
        return jsonify({"success": False, "error": "ANTHROPIC_API_KEY not set"}), 500

    prompt = f"""Analyze the following brand scripts and extract a precise voice DNA profile.
Return valid JSON only. No markdown.

SCRIPTS TO ANALYZE:
{raw_scripts[:5000]}

Extract this exact schema:
{{
  "extracted_at": "ISO timestamp",
  "sentence_length": "short|medium|long|mixed",
  "avg_words_per_sentence": 0,
  "energy": "high|medium|calm|intense",
  "tone": "direct|conversational|educational|provocative|empathetic",
  "hinglish_pattern": "never|occasional|frequent",
  "vocabulary": {{
    "power_words": ["words used often for emphasis"],
    "never_use": ["words that break brand voice"],
    "signature_phrases": ["unique phrases this brand uses"]
  }},
  "structure": {{
    "typical_opening": "how scripts usually open",
    "typical_close": "how scripts usually close",
    "uses_questions": true,
    "uses_numbers": true
  }},
  "cta_style": "comment trigger|dm trigger|link in bio|save this",
  "platform_voice_delta": {{
    "instagram": "any adjustments for Instagram",
    "linkedin": "any adjustments for LinkedIn"
  }},
  "brand_personality": "3 adjectives that define this brand's voice"
}}"""

    try:
        import anthropic as _anthropic
        _client = _anthropic.Anthropic(api_key=anthropic_key)
        response = _client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = response.content[0].text.strip()

        # Strip markdown fences
        if "```" in raw:
            for part in raw.split("```"):
                part = part.strip()
                if part.startswith("json"):
                    part = part[4:].strip()
                if part.startswith("{"):
                    raw = part
                    break

        profile = json.loads(raw)
        profile["extracted_at"] = datetime.now().isoformat()

    except Exception as e:
        return jsonify({"success": False, "error": f"Voice extraction failed: {e}"}), 500

    # Save to brands/{slug}/voice_profile.json
    out_path = BRANDS_DIR / brand_slug / "voice_profile.json"
    _atomic_write_json(out_path, profile)

    return jsonify({"success": True, "data": profile})


@bp.route("/api/voice/profile", methods=["GET"])
@require_auth
def voice_get_profile():
    """Return voice_profile.json for a brand, or {exists: false} if not created yet."""
    brand_slug = request.args.get("brand_slug", "").strip()
    if not brand_slug:
        return jsonify({"success": False, "error": "brand_slug required"}), 400

    path = BRANDS_DIR / brand_slug / "voice_profile.json"
    if not path.exists():
        return jsonify({"success": True, "data": {"exists": False}})

    try:
        with open(path) as f:
            profile = json.load(f)
        return jsonify({"success": True, "data": {"exists": True, **profile}})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ── Notion Approval Cards ─────────────────────────────────────────────────────

@bp.route("/api/notion/cards", methods=["GET"])
@require_auth
def get_notion_cards():
    brand_slug = require_brand_slug()
    brand_dir = get_brand_dir(brand_slug)
    session_file = brand_dir / "session_state.json"
    if not session_file.exists():
        return jsonify({"success": True, "data": []})
    with open(session_file) as f:
        session = json.load(f)
    cards = session.get("notion_cards", [])
    return jsonify({"success": True, "data": cards})


@bp.route("/api/notion/approve", methods=["POST"])
@require_auth
def approve_notion_card():
    body = request.get_json() or {}
    page_id = body.get("page_id", "")
    brand_slug = require_brand_slug()

    if not page_id:
        return jsonify({"success": False, "error": "page_id required"}), 400

    try:
        from notion_integration.notion_pusher import update_notion_status
        update_notion_status(page_id, "Approved", approved=True)
    except Exception as e:
        print(f"[dashboard_api] Notion approve failed: {e}")

    _update_notion_card_status(brand_slug, page_id, "approved")
    return jsonify({"success": True, "data": {"message": "Approved in Notion"}})


@bp.route("/api/notion/reject", methods=["POST"])
@require_auth
def reject_notion_card():
    body = request.get_json() or {}
    page_id = body.get("page_id", "")
    brand_slug = require_brand_slug()

    if not page_id:
        return jsonify({"success": False, "error": "page_id required"}), 400

    try:
        from notion_integration.notion_pusher import update_notion_status
        update_notion_status(page_id, "Rejected", rejected=True)
    except Exception as e:
        print(f"[dashboard_api] Notion reject failed: {e}")

    _update_notion_card_status(brand_slug, page_id, "rejected")
    return jsonify({"success": True, "data": {"message": "Rejected in Notion"}})


@bp.route("/api/notion/sync", methods=["GET"])
@require_auth
def sync_notion_approvals():
    """
    Phase 3 Step 2 — Check Notion for approved pages, sync status back to Supabase.
    For each pending output with a notion_page_id, fetches its Notion status.
    If approved, calls db.approve_output() and _unlock_next_agent().
    """
    brand_slug = require_brand_slug()

    if not _NOTION_KEY:
        return jsonify({"success": False, "error": "NOTION_API_KEY not configured"}), 400

    if not _DB_AVAILABLE:
        return jsonify({"success": False, "error": "Supabase not available"}), 500

    brand_id = _get_brand_id(brand_slug)
    if not brand_id:
        return jsonify({"success": False, "error": "Brand not found"}), 404

    try:
        import requests as _req
        pending_rows = _db.get_pending_outputs(brand_id)
        synced = 0
        errors = []
        for row in pending_rows:
            formatted = row.get("formatted_output") or {}
            notion_page_id = formatted.get("notion_page_id", "")
            if not notion_page_id:
                continue
            try:
                resp = _req.get(
                    f"https://api.notion.com/v1/pages/{notion_page_id}",
                    headers={
                        "Authorization": f"Bearer {_NOTION_KEY}",
                        "Notion-Version": "2022-06-28",
                    },
                    timeout=5,
                )
                if resp.status_code != 200:
                    continue
                page_data = resp.json()
                props = page_data.get("properties", {})
                status_prop = props.get("Status", {})
                status_val = (status_prop.get("select") or {}).get("name", "")
                if status_val == "Approved":
                    _db.approve_output(row["id"])
                    agent_slug_key = row.get("agent_slug", "")
                    if agent_slug_key:
                        _unlock_next_agent(brand_id, agent_slug_key)
                    synced += 1
            except Exception as _row_err:
                errors.append(str(_row_err))
        return jsonify({"success": True, "data": {"synced": synced, "errors": errors}})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/api/connections/check", methods=["GET"])
@require_auth
def check_connections():
    """
    Phase 4 Step 1 — Live connection validator. Each check has a 5s timeout.
    Runs real API calls for Meta, Notion, Apify. Env-var check for Anthropic + ElevenLabs.
    """
    import requests as _req
    results: dict[str, dict] = {}

    # Anthropic — env var check only (no live call needed)
    ak = _ANTHROPIC_KEY
    results["anthropic"] = {"connected": bool(ak), "account": "API key set" if ak else "Not configured"}

    # ElevenLabs — env var check
    ek = _ELEVENLABS_KEY
    results["elevenlabs"] = {"connected": bool(ek), "account": "API key set" if ek else "Not configured"}

    # Notion — live call
    nk = _NOTION_KEY
    if nk:
        try:
            resp = _req.get(
                "https://api.notion.com/v1/users/me",
                headers={"Authorization": f"Bearer {nk}", "Notion-Version": "2022-06-28"},
                timeout=5,
            )
            if resp.status_code == 200:
                data = resp.json()
                name = data.get("name") or data.get("bot", {}).get("owner", {}).get("user", {}).get("name", "")
                results["notion"] = {"connected": True, "account": name or "Connected"}
            else:
                results["notion"] = {"connected": False, "account": f"Auth failed ({resp.status_code})"}
        except Exception as e:
            results["notion"] = {"connected": False, "account": f"Timeout: {e}"}
    else:
        results["notion"] = {"connected": False, "account": "NOTION_API_KEY not set"}

    # Apify — live call
    apify_key = os.getenv("APIFY_API_KEY", "").strip()
    if apify_key:
        try:
            resp = _req.get(
                f"https://api.apify.com/v2/users/me?token={apify_key}",
                timeout=5,
            )
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                username = data.get("username", "")
                results["apify"] = {"connected": True, "account": username or "Connected"}
            else:
                results["apify"] = {"connected": False, "account": f"Auth failed ({resp.status_code})"}
        except Exception as e:
            results["apify"] = {"connected": False, "account": f"Timeout: {e}"}
    else:
        results["apify"] = {"connected": False, "account": "APIFY_API_KEY not set"}

    # Meta (Instagram) — live call
    meta_token = os.getenv("META_GRAPH_API_TOKEN", "").strip() or os.getenv("META_ACCESS_TOKEN", "").strip()
    if meta_token:
        try:
            resp = _req.get(
                f"https://graph.facebook.com/me?access_token={meta_token}&fields=name",
                timeout=5,
            )
            if resp.status_code == 200:
                data = resp.json()
                name = data.get("name", "")
                results["meta"] = {"connected": True, "account": name or "Connected"}
            else:
                results["meta"] = {"connected": False, "account": f"Token invalid ({resp.status_code})"}
        except Exception as e:
            results["meta"] = {"connected": False, "account": f"Timeout: {e}"}
    else:
        results["meta"] = {"connected": False, "account": "META_GRAPH_API_TOKEN not set"}

    # LinkedIn — live call
    li_token = os.getenv("LINKEDIN_ACCESS_TOKEN", "").strip()
    if li_token:
        try:
            resp = _req.get(
                "https://api.linkedin.com/v2/me",
                headers={"Authorization": f"Bearer {li_token}"},
                timeout=5,
            )
            if resp.status_code == 200:
                data = resp.json()
                first = data.get("localizedFirstName", "")
                last  = data.get("localizedLastName", "")
                name  = f"{first} {last}".strip() or "Connected"
                results["linkedin"] = {"connected": True, "account": name}
            else:
                results["linkedin"] = {"connected": False, "account": f"Token invalid ({resp.status_code})"}
        except Exception as e:
            results["linkedin"] = {"connected": False, "account": f"Timeout: {e}"}
    else:
        results["linkedin"] = {"connected": False, "account": "LINKEDIN_ACCESS_TOKEN not set"}

    # YouTube — live call (validates API key via channels endpoint)
    yt_key = os.getenv("YOUTUBE_API_KEY", "").strip()
    if yt_key:
        try:
            resp = _req.get(
                f"https://www.googleapis.com/youtube/v3/channels?part=snippet&forHandle=AskGauravAI&key={yt_key}",
                timeout=5,
            )
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("items", [])
                title = items[0]["snippet"]["title"] if items else "Key valid"
                results["youtube"] = {"connected": True, "account": title}
            elif resp.status_code == 400:
                results["youtube"] = {"connected": False, "account": "API key invalid"}
            else:
                results["youtube"] = {"connected": False, "account": f"Error ({resp.status_code})"}
        except Exception as e:
            results["youtube"] = {"connected": False, "account": f"Timeout: {e}"}
    else:
        results["youtube"] = {"connected": False, "account": "YOUTUBE_API_KEY not set"}

    # Twitter / X — live call
    # Note: Free tier App-Only Bearer tokens get 403 on /2/users/me (OAuth user-context only).
    # We use Twitter via Apify actor anyway, so a 403 here is OK as long as the token is well-formed.
    tw_token = os.getenv("TWITTER_BEARER_TOKEN", "").strip()
    if tw_token:
        try:
            resp = _req.get(
                "https://api.twitter.com/2/users/me",
                headers={"Authorization": f"Bearer {tw_token}"},
                timeout=5,
            )
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                name = data.get("name", "") or data.get("username", "") or "Connected"
                results["twitter"] = {"connected": True, "account": f"@{data.get('username', name)}"}
            elif resp.status_code in (401,):
                # 401 = token actually invalid/revoked
                results["twitter"] = {"connected": False, "account": "Token invalid (401)"}
            elif resp.status_code in (403, 429):
                # 403 = Free tier restriction on /users/me (token still works via Apify)
                # 429 = rate limited (token still valid)
                results["twitter"] = {"connected": True, "account": "Token set (Free tier — read via Apify)"}
            else:
                results["twitter"] = {"connected": False, "account": f"Unexpected ({resp.status_code})"}
        except Exception as e:
            results["twitter"] = {"connected": False, "account": f"Timeout: {e}"}
    else:
        results["twitter"] = {"connected": False, "account": "TWITTER_BEARER_TOKEN not set"}

    # WhatsApp — env var check (Business API token)
    wa_token = os.getenv("WHATSAPP_ACCESS_TOKEN", "").strip()
    results["whatsapp"] = {
        "connected": bool(wa_token),
        "account": "Token set" if wa_token else "WHATSAPP_ACCESS_TOKEN not set",
    }

    return jsonify({"success": True, "data": results})


@bp.route("/api/connections/save-token", methods=["POST"])
@require_auth
def save_connection_token():
    """
    Persist a platform API token to a brand's private .env (brands/<slug>/.env).
    Body: { "brand_slug": "<slug>",
            "platform": "instagram"|"linkedin"|"youtube"|"twitter"|"tiktok"|"whatsapp",
            "token": "<token value>",
            "extra": { "IG_USER_ID": "...", "LINKEDIN_URN": "..." }  # optional secondary keys
    }
    Falls back to global .env when no brand_slug is given (back-compat).
    """
    body       = request.get_json() or {}
    brand_slug = (body.get("brand_slug") or "").strip()
    platform   = (body.get("platform") or "").strip().lower()
    token      = (body.get("token")    or "").strip()
    extra      = body.get("extra") or {}

    if not platform:
        return jsonify({"success": False, "error": "platform is required"}), 400
    if platform not in _PLATFORM_ENV_MAP:
        return jsonify({"success": False, "error": f"Unknown platform '{platform}'"}), 400
    if not token:
        return jsonify({"success": False, "error": "token is required"}), 400

    env_key = _PLATFORM_ENV_MAP[platform]
    try:
        if brand_slug:
            _write_brand_env_token(brand_slug, env_key, token)
            for k, v in extra.items():
                if isinstance(v, str) and v.strip():
                    _write_brand_env_token(brand_slug, str(k).strip(), v.strip())
            target = f"brands/{brand_slug}/.env"
        else:
            _write_env_token(env_key, token)
            target = ".env"
    except Exception as exc:
        return jsonify({"success": False, "error": f"Failed to write {env_key}: {exc}"}), 500

    # Live-verify what we just stored (never echo the token back)
    status = _verify_social(platform, token)
    return jsonify({
        "success": True,
        "data": {
            "platform":  platform,
            "env_key":   env_key,
            "target":    target,
            "connected": status["connected"],
            "account":   status["account"],
            "message":   f"{env_key} saved to {target}",
        },
    })
