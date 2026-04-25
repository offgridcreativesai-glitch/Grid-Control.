"""
jarvis-skills/grid-control/skill.py
OpenJarvis skill — maps voice commands to Grid Control REST API.
"""

import os
import requests

SKILL_NAME = "Grid Control"
TRIGGERS   = [
    "run agent",
    "pipeline status",
    "how many pending",
    "pending approvals",
    "run daily pipeline",
    "what's next",
    "run today",
    "start pipeline",
]

GRID_API = os.getenv("GRID_API_URL", "http://localhost:5001")
SECRET   = os.getenv("DASHBOARD_SECRET", "")
HEADERS  = {"X-Dashboard-Secret": SECRET, "Content-Type": "application/json"} if SECRET else {"Content-Type": "application/json"}


def _get(path: str) -> dict:
    try:
        r = requests.get(f"{GRID_API}{path}", headers=HEADERS, timeout=10)
        return r.json() if r.ok else {}
    except Exception as e:
        return {"error": str(e)}


def _post(path: str, body: dict) -> dict:
    try:
        r = requests.post(f"{GRID_API}{path}", json=body, headers=HEADERS, timeout=15)
        return r.json() if r.ok else {}
    except Exception as e:
        return {"error": str(e)}


def _get_active_brand() -> str:
    """Get the first available brand slug."""
    resp = _get("/api/brands")
    brands = resp.get("data", []) if resp.get("success") else []
    return brands[0].get("slug", "") if brands else ""


def handle(query: str) -> str:
    """Route voice query to the appropriate Grid Control API call."""
    q = query.lower()

    # Pending approval count
    if any(kw in q for kw in ["pending", "how many", "approval"]):
        brand = _get_active_brand()
        if not brand:
            return "I couldn't find any brands in Grid Control."
        resp = _get(f"/api/outputs/pending?brand_slug={brand}")
        items = resp.get("data", []) if resp.get("success") else []
        return f"You have {len(items)} output{'s' if len(items) != 1 else ''} pending approval for {brand}."

    # Pipeline status
    elif any(kw in q for kw in ["status", "what's running", "agent status"]):
        brand = _get_active_brand()
        if not brand:
            return "No brands found in Grid Control."
        resp  = _get(f"/api/agents/status?brand_slug={brand}")
        agents = resp.get("data", []) if resp.get("success") else []
        running = [a["name"] for a in agents if a.get("status") == "running"]
        if running:
            return f"{', '.join(running)} {'is' if len(running) == 1 else 'are'} currently running."
        return "All agents are idle. No pipeline is running right now."

    # Daily pipeline run
    elif any(kw in q for kw in ["run today", "daily pipeline", "run daily", "start pipeline"]):
        brand = _get_active_brand()
        if not brand:
            return "No brands configured in Grid Control."
        resp = _post("/api/pipeline/daily-run", {"brand_slug": brand})
        if resp.get("success"):
            return f"Daily pipeline started for {brand}. Trend Researcher, Data Analyst, and Script Writer will run in sequence."
        return "I couldn't start the daily pipeline. Check the Flask API is running."

    # Fallback — send to Jarvis query endpoint
    else:
        brand = _get_active_brand()
        resp  = _post("/api/jarvis/query", {"query": query, "brand_slug": brand})
        return resp.get("response", "I couldn't process that request.")
