"""
NotionPusher — OffGrid Marketing OS
Pushes all agent outputs to Notion for human approval.
Rule 3: Nothing executes without approval.
Rule 9: Every output carries a Loop Header.
"""

import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_PAGE_ID = os.getenv("NOTION_PAGE_ID")
NOTION_VERSION = "2022-06-28"

HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": NOTION_VERSION
}


class NotionAuthError(Exception):
    """Raised when Notion API returns 401 unauthorized — token invalid/expired."""
    pass


def _get_or_create_database() -> str:
    """
    Check if OffGrid Approvals database exists under the page.
    If not, create it. Return the database ID.

    Raises NotionAuthError(401) with a clear message if token is bad —
    so callers can distinguish "token expired" from "transient API error".
    """
    # Search for existing database
    search_url = "https://api.notion.com/v1/search"
    payload = {
        "query": "OffGrid Agent Approvals",
        "filter": {"value": "database", "property": "object"}
    }
    response = requests.post(search_url, headers=HEADERS, json=payload, timeout=10)

    # HARD ERROR CHECK — fail loud, not silent
    if response.status_code == 401:
        raise NotionAuthError(
            "Notion API token is INVALID or EXPIRED (401). "
            "Fix: go to https://notion.so/my-integrations, regenerate the token for the 'Social media Agents' integration, "
            "and paste the new token into .env as NOTION_API_KEY=..."
        )
    if response.status_code != 200:
        raise Exception(f"Notion search failed ({response.status_code}): {response.json().get('message', 'unknown')}")

    results = response.json().get("results", [])

    if results:
        db_id = results[0]["id"]
        print(f"[NotionPusher] Found existing database: {db_id}")
        return db_id

    # Create database if not found
    create_url = "https://api.notion.com/v1/databases"
    db_payload = {
        "parent": {"type": "page_id", "page_id": NOTION_PAGE_ID},
        "title": [{"type": "text", "text": {"content": "OffGrid Agent Approvals"}}],
        "properties": {
            "Output Title": {"title": {}},
            "Agent": {"select": {
                "options": [
                    {"name": "Trend Researcher", "color": "blue"},
                    {"name": "Strategy Agent", "color": "purple"},
                    {"name": "Content Planner", "color": "green"},
                    {"name": "Script Writer", "color": "yellow"},
                    {"name": "Creative Director", "color": "orange"},
                    {"name": "Ad Strategist", "color": "red"},
                    {"name": "Data Analyst", "color": "gray"},
                    {"name": "Funnel Specialist", "color": "pink"},
                    {"name": "Website Agent", "color": "brown"}
                ]
            }},
            "Brand": {"rich_text": {}},
            "Status": {"select": {
                "options": [
                    {"name": "Pending Approval", "color": "yellow"},
                    {"name": "Approved", "color": "green"},
                    {"name": "Rejected", "color": "red"}
                ]
            }},
            "Output Type": {"rich_text": {}},
            "Loop Goal": {"rich_text": {}},
            "Loop Metric": {"rich_text": {}},
            "Variants Tested": {"number": {}},
            "Winner Reason": {"rich_text": {}},
            "Timestamp": {"date": {}},
            "Approved": {"checkbox": {}},
            "Rejected": {"checkbox": {}}
        }
    }

    create_response = requests.post(create_url, headers=HEADERS, json=db_payload, timeout=10)
    if create_response.status_code == 401:
        raise NotionAuthError(
            "Notion API token is INVALID or EXPIRED (401). "
            "Fix: regenerate at https://notion.so/my-integrations and update NOTION_API_KEY in .env."
        )
    create_data = create_response.json()
    if "id" not in create_data:
        raise Exception(
            f"Notion database create failed ({create_response.status_code}): {create_data.get('message', create_data)}"
        )
    db_id = create_data["id"]
    print(f"[NotionPusher] Created new database: {db_id}")
    return db_id


def push_to_notion(
    agent_name: str,
    brand: str,
    output_type: str,
    loop_header: dict,
    content,
) -> dict:
    # Convert any dict/JSON output to human-readable markdown before pushing to Notion
    try:
        from utils.output_formatter import format_for_notion
        import json as _json
        if isinstance(content, dict):
            content = format_for_notion(agent_name, content)
        elif isinstance(content, str) and (content.strip().startswith("{") or content.strip().startswith("[")):
            try:
                parsed = _json.loads(content)
                content = format_for_notion(agent_name, parsed)
            except Exception:
                pass
    except Exception:
        pass
    """
    Push a single agent output to the Notion approvals database.

    Args:
        agent_name: Name of the agent that produced the output
        brand: Brand slug (e.g. offgrid-creatives-ai)
        output_type: What kind of output (e.g. Hook, Trend Report, Strategy)
        loop_header: Dict with keys — goal, metric, variants_tested, winner
        content: The actual output content as a string

    Returns:
        dict with success status and Notion page URL
    """

    if not NOTION_API_KEY or not NOTION_PAGE_ID:
        return {
            "success": False,
            "error": "NOTION_API_KEY or NOTION_PAGE_ID missing from .env"
        }

    try:
        db_id = _get_or_create_database()
        timestamp = datetime.utcnow().isoformat()

        # Truncate content for Notion block limit (2000 chars per block)
        content_chunks = [content[i:i+1900] for i in range(0, len(content), 1900)]

        page_payload = {
            "parent": {"database_id": db_id},
            "properties": {
                "Output Title": {
                    "title": [{"text": {"content": f"{agent_name} — {output_type}"}}]
                },
                "Agent": {
                    "select": {"name": agent_name}
                },
                "Brand": {
                    "rich_text": [{"text": {"content": brand}}]
                },
                "Status": {
                    "select": {"name": "Pending Approval"}
                },
                "Output Type": {
                    "rich_text": [{"text": {"content": output_type}}]
                },
                "Loop Goal": {
                    "rich_text": [{"text": {"content": loop_header.get("goal", "")}}]
                },
                "Loop Metric": {
                    "rich_text": [{"text": {"content": loop_header.get("metric", "")}}]
                },
                "Variants Tested": {
                    "number": loop_header.get("variants_tested", 3)
                },
                "Winner Reason": {
                    "rich_text": [{"text": {"content": loop_header.get("winner", "")}}]
                },
                "Timestamp": {
                    "date": {"start": timestamp}
                },
                "Approved": {"checkbox": False},
                "Rejected": {"checkbox": False}
            },
            "children": [
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"text": {"content": "Loop Header"}}]
                    }
                },
                {
                    "object": "block",
                    "type": "code",
                    "code": {
                        "language": "plain text",
                        "rich_text": [{"text": {"content": 
                            f"LOOP: {agent_name} — {output_type}\n"
                            f"GOAL: {loop_header.get('goal', '')}\n"
                            f"METRIC: better = {loop_header.get('metric', '')}\n"
                            f"VARIANTS TESTED: {loop_header.get('variants_tested', 3)}\n"
                            f"WINNER: {loop_header.get('winner', '')}"
                        }}]
                    }
                },
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"text": {"content": "Output"}}]
                    }
                }
            ] + [
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"text": {"content": chunk}}]
                    }
                }
                for chunk in content_chunks
            ]
        }

        create_url = "https://api.notion.com/v1/pages"
        response = requests.post(create_url, headers=HEADERS, json=page_payload, timeout=15)
        result = response.json()

        if response.status_code == 200:
            return {
                "success": True,
                "notion_url": result.get("url", ""),
                "page_id": result.get("id", ""),
                "agent": agent_name,
                "brand": brand,
                "timestamp": timestamp
            }
        else:
            return {
                "success": False,
                "error": result.get("message", "Unknown Notion API error"),
                "status_code": response.status_code
            }

    except NotionAuthError as e:
        return {
            "success": False,
            "error": f"NOTION_AUTH_ERROR: {e}",
            "auth_error": True,
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"NOTION_PUSH_FAILED: {type(e).__name__}: {e}"
        }


def update_notion_status(page_id: str, status: str, approved: bool = False, rejected: bool = False) -> dict:
    """
    Update the Status field and approval checkboxes on an existing Notion page.

    Args:
        page_id: Notion page UUID
        status: One of "Pending Approval", "Approved", "Rejected"
        approved: Set Approved checkbox
        rejected: Set Rejected checkbox

    Returns:
        dict with success bool
    """
    if not NOTION_API_KEY:
        return {"success": False, "error": "NOTION_API_KEY missing"}

    url = f"https://api.notion.com/v1/pages/{page_id}"
    payload = {
        "properties": {
            "Status": {"select": {"name": status}},
            "Approved": {"checkbox": approved},
            "Rejected": {"checkbox": rejected}
        }
    }
    response = requests.patch(url, headers=HEADERS, json=payload, timeout=10)
    if response.status_code == 200:
        return {"success": True}
    else:
        return {
            "success": False,
            "error": response.json().get("message", "Notion API error"),
            "status_code": response.status_code
        }


def test_notion_connection() -> bool:
    """
    Quick connection test. Call this from main.py on startup.
    Returns True if Notion is reachable and credentials are valid.
    """
    test_url = f"https://api.notion.com/v1/pages/{NOTION_PAGE_ID}"
    response = requests.get(test_url, headers=HEADERS, timeout=10)

    if response.status_code == 200:
        print("[NotionPusher] ✅ Notion connection verified")
        return True
    else:
        print(f"[NotionPusher] ❌ Notion connection failed: {response.status_code}")
        print(f"[NotionPusher] Make sure the Social Media Agents integration is added to the page")
        return False
