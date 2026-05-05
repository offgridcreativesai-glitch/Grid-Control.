"""
NotionContentCalendar — OffGrid Marketing OS
Pushes generated carousels (and future content units) to a SEPARATE Notion DB
that tracks publish lifecycle: Draft → Ready → Published.

Distinct from notion_pusher.py which pushes ALL agent outputs to the approval DB.
This is the publishing-side calendar — entries here are visual/copy-ready.

Setup once:
  1. The integration auto-creates a "OffGrid Content Calendar" DB on first push,
     under the same page as the approval DB.
  2. Optionally set NOTION_CONTENT_CALENDAR_DB_ID in .env to point to an existing DB.

Properties:
  - Title (Title): brand · platform · post_id|topic
  - Brand (rich_text)
  - Platform (select): instagram | linkedin | square
  - Post ID (rich_text)
  - Status (select): Draft | Ready | Published | Archived
  - Slide Count (number)
  - Hook (rich_text)
  - Caption (rich_text)
  - Spec Path (url) — local file path to slides.json
  - Tags (multi_select)
  - Generated At (date)
"""

import os
import re
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


def _normalize_notion_id(raw: str) -> str:
    """Notion accepts the bare 32-char hex or dashed UUID. Strip URLs and re-dash."""
    if not raw:
        return ""
    # Pull a 32-char hex chunk from anywhere in the string (URLs, dashed UUIDs, bare hex)
    cleaned = raw.strip().rstrip("/")
    m = re.search(r"([0-9a-fA-F]{32})", cleaned.replace("-", ""))
    if not m:
        # Maybe it's already a dashed UUID
        m2 = re.search(r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})", cleaned)
        if m2:
            return m2.group(1)
        return ""
    h = m.group(1)
    return f"{h[0:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"


NOTION_API_KEY = os.getenv("NOTION_API_KEY", "").strip()
NOTION_PAGE_ID = _normalize_notion_id(os.getenv("NOTION_PAGE_ID", ""))
NOTION_CONTENT_CALENDAR_DB_ID = _normalize_notion_id(os.getenv("NOTION_CONTENT_CALENDAR_DB_ID", ""))
NOTION_VERSION = "2022-06-28"

HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": NOTION_VERSION,
}

CALENDAR_DB_NAME = "OffGrid Content Calendar"


def _get_or_create_calendar_db() -> str:
    """Find or create the Content Calendar DB. Returns DB ID."""
    if NOTION_CONTENT_CALENDAR_DB_ID:
        return NOTION_CONTENT_CALENDAR_DB_ID

    if not NOTION_API_KEY or not NOTION_PAGE_ID:
        raise Exception("NOTION_API_KEY or NOTION_PAGE_ID missing — cannot push to calendar")

    # Search for existing
    search_url = "https://api.notion.com/v1/search"
    payload = {"query": CALENDAR_DB_NAME, "filter": {"value": "database", "property": "object"}}
    r = requests.post(search_url, headers=HEADERS, json=payload, timeout=10)
    if r.status_code == 401:
        raise Exception("Notion 401 — regenerate NOTION_API_KEY at notion.so/my-integrations")
    r.raise_for_status()

    results = r.json().get("results", [])
    for db in results:
        title_text = "".join(t.get("plain_text", "") for t in db.get("title", []))
        if title_text.strip() == CALENDAR_DB_NAME:
            return db["id"]

    # Create new
    create_url = "https://api.notion.com/v1/databases"
    db_payload = {
        "parent": {"type": "page_id", "page_id": NOTION_PAGE_ID},
        "title": [{"type": "text", "text": {"content": CALENDAR_DB_NAME}}],
        "properties": {
            "Title": {"title": {}},
            "Brand": {"rich_text": {}},
            "Platform": {"select": {"options": [
                {"name": "instagram", "color": "purple"},
                {"name": "linkedin", "color": "blue"},
                {"name": "square", "color": "gray"},
            ]}},
            "Post ID": {"rich_text": {}},
            "Status": {"select": {"options": [
                {"name": "Draft", "color": "yellow"},
                {"name": "Ready", "color": "blue"},
                {"name": "Published", "color": "green"},
                {"name": "Archived", "color": "gray"},
            ]}},
            "Slide Count": {"number": {}},
            "Hook": {"rich_text": {}},
            "Caption": {"rich_text": {}},
            "Spec Path": {"url": {}},
            "Tags": {"multi_select": {"options": []}},
            "Generated At": {"date": {}},
        },
    }
    cr = requests.post(create_url, headers=HEADERS, json=db_payload, timeout=15)
    if cr.status_code != 200:
        raise Exception(f"Calendar DB create failed ({cr.status_code}): {cr.text[:400]}")
    db_id = cr.json()["id"]
    print(f"[ContentCalendar] Created new DB: {db_id}")
    return db_id


def _hashtag_tags(caption: str) -> list[dict]:
    if not caption:
        return []
    tags = []
    for word in caption.split():
        w = word.strip(",.!?;:")
        if w.startswith("#") and len(w) > 1:
            name = w.lstrip("#")[:90]
            tags.append({"name": name})
    # Dedup, max 10
    seen, out = set(), []
    for t in tags:
        if t["name"].lower() not in seen:
            seen.add(t["name"].lower())
            out.append(t)
        if len(out) >= 10:
            break
    return out


def push_carousel_to_calendar(
    brand: str,
    post_id: str | None,
    topic: str,
    platform: str,
    slide_count: int,
    hook: str,
    caption: str,
    spec_path: str,
    status: str = "Draft",
) -> dict:
    """
    Push a carousel entry to the Content Calendar DB.
    Returns {success, page_id, page_url, error?}.
    """
    if not NOTION_API_KEY or not NOTION_PAGE_ID:
        return {"success": False, "error": "Notion env vars missing — calendar push skipped"}

    try:
        db_id = _get_or_create_calendar_db()
    except Exception as e:
        return {"success": False, "error": str(e)}

    title = f"{brand} · {platform} · {post_id or topic[:60]}"
    tags = _hashtag_tags(caption)

    page_payload = {
        "parent": {"database_id": db_id},
        "properties": {
            "Title": {"title": [{"text": {"content": title[:100]}}]},
            "Brand": {"rich_text": [{"text": {"content": brand}}]},
            "Platform": {"select": {"name": platform}},
            "Post ID": {"rich_text": [{"text": {"content": (post_id or "")[:100]}}]},
            "Status": {"select": {"name": status}},
            "Slide Count": {"number": int(slide_count)},
            "Hook": {"rich_text": [{"text": {"content": hook[:1900]}}]},
            "Caption": {"rich_text": [{"text": {"content": caption[:1900]}}]},
            "Spec Path": {"url": f"file://{spec_path}" if spec_path else None},
            "Tags": {"multi_select": tags},
            "Generated At": {"date": {"start": datetime.utcnow().isoformat()}},
        },
    }
    # Drop None URL if absent
    if page_payload["properties"]["Spec Path"]["url"] is None:
        del page_payload["properties"]["Spec Path"]

    create_url = "https://api.notion.com/v1/pages"
    r = requests.post(create_url, headers=HEADERS, json=page_payload, timeout=15)
    if r.status_code != 200:
        return {"success": False, "error": f"Notion page create failed ({r.status_code}): {r.text[:400]}"}

    body = r.json()
    page_id = body["id"]
    page_url = body.get("url", "")
    return {"success": True, "page_id": page_id, "page_url": page_url}
