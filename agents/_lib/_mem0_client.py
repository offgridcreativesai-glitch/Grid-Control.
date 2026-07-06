"""
Semantic memory client — Phase 1a (Jun 18 2026).

2 scopes, no mixing:
  • "grid_control"  → Gaurav's account, cross-brand
  • "brand:<slug>"  → per-brand, isolated

Backend: Voyage voyage-3-lite embeddings (512-dim) + Supabase pgvector.
Lives alongside (NOT replacing) the KV brand_memory table.

Public API:
    sem = SemanticMemory()
    sem.remember(scope="brand", brand_slug="askgauravai",
                 agent="strategy-agent",
                 content="Manthan is the closest competitor by ER")
    hits = sem.recall(scope="brand", brand_slug="askgauravai",
                      agent="strategy-agent",
                      query="who do we compete with?", k=5)
"""
import os
import sys
from typing import Optional
from dotenv import load_dotenv

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_SUPA_DIR = os.path.join(_PROJECT_ROOT, "supabase")
if _SUPA_DIR not in sys.path:
    sys.path.insert(0, _SUPA_DIR)
load_dotenv(os.path.join(_PROJECT_ROOT, ".env"))


class SemanticMemory:
    """Thin embed→store→search layer. Silent no-op when keys/DB missing."""

    EMBED_MODEL = "voyage-3-lite"
    EMBED_DIM = 512

    def __init__(self):
        self._ok = False
        self._voyage = None
        self._db = None
        try:
            import voyageai
            key = os.getenv("VOYAGE_API_KEY")
            if not key:
                return
            self._voyage = voyageai.Client(api_key=key)
            import db as _db
            self._db = _db
            self._ok = True
        except Exception as e:
            print(f"[mem0] init skipped: {e}")

    # ── public API ───────────────────────────────────────────

    def remember(
        self,
        scope: str,
        agent: str,
        content: str,
        brand_slug: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> Optional[str]:
        """Store one fact in the chosen scope. Returns row id or None."""
        if not self._ok or not content:
            return None
        emb = self._embed(content)
        if emb is None:
            return None
        if scope == "grid_control":
            return self._insert_grid_control(agent, content, emb, metadata or {})
        if scope == "brand":
            if not brand_slug:
                return None
            brand_id = self._brand_id(brand_slug)
            if not brand_id:
                return None
            return self._insert_brand(brand_id, agent, content, emb, metadata or {})
        return None

    def recall(
        self,
        scope: str,
        agent: str,
        query: str,
        brand_slug: Optional[str] = None,
        k: int = 5,
    ) -> list[dict]:
        """Semantic search: returns top-k matches scoped by agent."""
        if not self._ok or not query:
            return []
        emb = self._embed(query)
        if emb is None:
            return []
        if scope == "grid_control":
            return self._search_grid_control(agent, emb, k)
        if scope == "brand":
            if not brand_slug:
                return []
            brand_id = self._brand_id(brand_slug)
            if not brand_id:
                return []
            return self._search_brand(brand_id, agent, emb, k)
        return []

    def recall_as_text(self, **kwargs) -> str:
        """Same args as recall(); returns markdown block for prompt injection."""
        hits = self.recall(**kwargs)
        if not hits:
            return ""
        lines = [f"- {h['content']}" for h in hits]
        scope = kwargs.get("scope", "?")
        return f"\n## Semantic Memory ({scope})\n" + "\n".join(lines) + "\n"

    # ── internals ────────────────────────────────────────────

    def _embed(self, text: str) -> Optional[list[float]]:
        try:
            r = self._voyage.embed([text], model=self.EMBED_MODEL, input_type="document")
            return r.embeddings[0]
        except Exception as e:
            print(f"[mem0] embed failed: {e}")
            return None

    def _brand_id(self, slug: str) -> Optional[str]:
        try:
            row = self._db.get_brand(slug)
            return row["id"] if row else None
        except Exception:
            return None

    def _svc(self):
        return self._db._svc()

    def _insert_grid_control(self, agent, content, emb, metadata):
        try:
            r = (self._svc().table("grid_control_memory_vec")
                 .insert({"agent_slug": agent, "content": content,
                          "embedding": emb, "metadata": metadata})
                 .execute())
            return r.data[0]["id"] if r.data else None
        except Exception as e:
            print(f"[mem0] gc insert failed: {e}")
            return None

    def _insert_brand(self, brand_id, agent, content, emb, metadata):
        try:
            r = (self._svc().table("brand_memory_vec")
                 .insert({"brand_id": brand_id, "agent_slug": agent,
                          "content": content, "embedding": emb,
                          "metadata": metadata})
                 .execute())
            return r.data[0]["id"] if r.data else None
        except Exception as e:
            print(f"[mem0] brand insert failed: {e}")
            return None

    def _search_grid_control(self, agent, emb, k):
        try:
            r = self._svc().rpc("mem_search_grid_control",
                                {"q_embedding": emb, "q_agent": agent, "k": k}).execute()
            return r.data or []
        except Exception as e:
            print(f"[mem0] gc search failed: {e}")
            return []

    def _search_brand(self, brand_id, agent, emb, k):
        try:
            r = self._svc().rpc("mem_search_brand",
                                {"q_embedding": emb, "q_brand": brand_id,
                                 "q_agent": agent, "k": k}).execute()
            return r.data or []
        except Exception as e:
            print(f"[mem0] brand search failed: {e}")
            return []


# Singleton for cheap reuse across agents in one process
_singleton: Optional[SemanticMemory] = None

def get_semantic_memory() -> SemanticMemory:
    global _singleton
    if _singleton is None:
        _singleton = SemanticMemory()
    return _singleton
