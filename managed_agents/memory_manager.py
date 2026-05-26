"""
managed_agents/memory_manager.py

Creates and seeds 3 memory stores per brand:
  1. brand_context   — brand_profile.json content, tone, goals, handles
  2. agent_learnings — what each agent has learned across sessions
  3. market_data     — trends_live.json + competitors_db.json snapshots

Memory store IDs are saved to brands/{slug}/memory_stores.json.
Runs automatically when a new brand is onboarded via dashboard_api.py.

CLI usage:
    python3 managed_agents/memory_manager.py --brand dropvolt
    python3 managed_agents/memory_manager.py --brand dropvolt --reseed  # reseed existing stores
    python3 managed_agents/memory_manager.py --list  # show all brands + store IDs
"""

import os
import sys
import json
import argparse
import pathlib

ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import anthropic

BRANDS_DIR    = ROOT / "brands"
# anthropic-beta header is no longer required for memory_stores in SDK 0.100+ — it's
# auto-injected by the SDK. Keep an empty kwarg so call-sites don't break.
BETA_HEADER   = {}
STORES_FILE   = "memory_stores.json"  # written inside brands/{slug}/


# ── HELPERS ───────────────────────────────────────────────────────────────────

def get_client() -> anthropic.Anthropic:
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        print("[memory_manager] ERROR: ANTHROPIC_API_KEY not set")
        sys.exit(1)
    return anthropic.Anthropic(api_key=key)


def load_json(path: pathlib.Path) -> dict:
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def load_stores(brand_slug: str) -> dict:
    path = BRANDS_DIR / brand_slug / STORES_FILE
    return load_json(path)


def save_stores(brand_slug: str, stores: dict) -> None:
    path = BRANDS_DIR / brand_slug / STORES_FILE
    with open(path, "w") as f:
        json.dump(stores, f, indent=2)


# ── STORE CREATION ────────────────────────────────────────────────────────────

def create_store(client: anthropic.Anthropic, name: str) -> str:
    """Create a memory store and return its ID."""
    store = client.beta.memory_stores.create(name=name)
    return store.id


def ensure_stores(client: anthropic.Anthropic, brand_slug: str) -> dict:
    """
    Create 3 memory stores for a brand if they don't exist.
    Returns dict: {brand_context, agent_learnings, market_data}
    """
    existing = load_stores(brand_slug)

    stores = {}
    store_defs = {
        "brand_context":   f"Brand Context — {brand_slug}",
        "agent_learnings": f"Agent Learnings — {brand_slug}",
        "market_data":     f"Market Data — {brand_slug}",
    }

    for key, store_name in store_defs.items():
        if existing.get(key):
            # Verify it still exists
            try:
                client.beta.memory_stores.retrieve(existing[key])
                stores[key] = existing[key]
                print(f"  [skip]   {key} — {existing[key]}")
                continue
            except Exception:
                print(f"  [recreate] {key} — old ID invalid")

        store_id = create_store(client, store_name)
        stores[key] = store_id
        print(f"  [created] {key} — {store_id}")

    save_stores(brand_slug, stores)
    return stores


# ── MEMORY SEEDING ────────────────────────────────────────────────────────────

def seed_brand_context(client: anthropic.Anthropic, store_id: str, brand_slug: str) -> None:
    """Seed brand_context store with brand_profile.json content."""
    profile = load_json(BRANDS_DIR / brand_slug / "brand_profile.json")
    if not profile:
        print(f"  [warn] No brand_profile.json found for {brand_slug} — skipping seed")
        return

    content = f"""BRAND PROFILE — {brand_slug}

Name: {profile.get('name', '?')}
Niche: {profile.get('niche', '?')}
Product: {profile.get('product_description', '?')}
Target audience: {profile.get('target_audience', '?')}
Tone: {profile.get('tone', '?')}
Platforms: {', '.join(profile.get('platforms', []))}
Competitors: {', '.join(profile.get('competitors', []))}
Goals: {', '.join(profile.get('goals', []))}
Bottlenecks: {', '.join(profile.get('bottlenecks', []))}
Pricing: {json.dumps(profile.get('pricing', {}))}
Social handles: {json.dumps(profile.get('social_handles', {}))}

Full profile JSON:
{json.dumps(profile, indent=2)}
"""

    client.beta.memory_stores.memories.create(
        memory_store_id=store_id,
        content=content,
        path=f"/brand_profile.md",
    )
    print(f"  [seeded] brand_context with brand_profile.json")


def seed_market_data(client: anthropic.Anthropic, store_id: str, brand_slug: str) -> None:
    """Seed market_data store with trends_live.json + competitors_db.json."""
    brand_dir = BRANDS_DIR / brand_slug

    trends      = load_json(brand_dir / "trends_live.json")
    competitors = load_json(brand_dir / "competitors_db.json")

    seeded = False

    if trends:
        ts = trends.get('scraped_at', 'unknown').replace(':', '').replace(' ', '_')[:30]
        client.beta.memory_stores.memories.create(
            memory_store_id=store_id,
            content=json.dumps(trends, indent=2),
            path=f"/trends_{ts}.md",
        )
        print(f"  [seeded] market_data with trends_live.json")
        seeded = True

    if competitors:
        client.beta.memory_stores.memories.create(
            memory_store_id=store_id,
            content=json.dumps(competitors, indent=2),
            path=f"/competitors_db.md",
        )
        print(f"  [seeded] market_data with competitors_db.json")
        seeded = True

    if not seeded:
        print(f"  [skip]   market_data — no trends or competitor data yet")


def seed_agent_learnings(client: anthropic.Anthropic, store_id: str, brand_slug: str) -> None:
    """Seed agent_learnings with a placeholder — grows across sessions."""
    client.beta.memory_stores.memories.create(
        memory_store_id=store_id,
        content=f"Agent learnings for {brand_slug}.\nThis store grows as agents complete sessions and record insights.\nInitialised: empty.",
        path=f"/_init.md",
    )
    print(f"  [seeded] agent_learnings with placeholder")


# ── PUBLIC API ────────────────────────────────────────────────────────────────

def setup_brand_memory(brand_slug: str, reseed: bool = False) -> dict:
    """
    Full setup for a brand: create stores + seed them.
    Called from dashboard_api.py on brand creation.
    Returns the stores dict: {brand_context, agent_learnings, market_data}
    """
    client = get_client()

    print(f"\n[memory_manager] Setting up memory stores for brand: {brand_slug}")
    print("Creating stores:")
    stores = ensure_stores(client, brand_slug)

    print("Seeding stores:")
    seed_brand_context(client,   stores["brand_context"],   brand_slug)
    seed_market_data(client,     stores["market_data"],     brand_slug)
    seed_agent_learnings(client, stores["agent_learnings"], brand_slug)

    print(f"[memory_manager] Done. Stores saved to brands/{brand_slug}/memory_stores.json\n")
    return stores


def update_market_data(brand_slug: str) -> None:
    """
    Called after Trend Researcher or Strategy Agent completes —
    adds a fresh document to the market_data store.
    """
    client = get_client()
    stores = load_stores(brand_slug)
    if not stores.get("market_data"):
        print(f"[memory_manager] No market_data store found for {brand_slug} — run setup first")
        return

    seed_market_data(client, stores["market_data"], brand_slug)


def record_agent_learning(brand_slug: str, agent_name: str, learning: str) -> None:
    """
    Called at the end of any agent session to persist a key insight.
    Agents call this by appending to agent_learnings store.
    """
    client = get_client()
    stores = load_stores(brand_slug)
    if not stores.get("agent_learnings"):
        return

    import time as _t
    safe_agent = agent_name.lower().replace(" ", "-").replace("+", "-")
    client.beta.memory_stores.memories.create(
        memory_store_id=stores["agent_learnings"],
        content=learning,
        path=f"/{safe_agent}_{int(_t.time())}.md",
    )


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="OffGrid Marketing OS — Memory Manager")
    group  = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--brand",  help="Brand slug to set up memory stores for")
    group.add_argument("--list",   action="store_true", help="List all brands and their memory store IDs")
    parser.add_argument("--reseed", action="store_true", help="Reseed existing stores (adds new documents)")
    args = parser.parse_args()

    if args.list:
        for brand_dir in sorted(BRANDS_DIR.iterdir()):
            if brand_dir.is_dir():
                stores = load_stores(brand_dir.name)
                print(f"\n{brand_dir.name}:")
                if stores:
                    for k, v in stores.items():
                        print(f"  {k}: {v or '(not created)'}")
                else:
                    print("  (no memory stores)")
        return

    setup_brand_memory(args.brand, reseed=args.reseed)


if __name__ == "__main__":
    main()
