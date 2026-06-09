"""
Agent run tracing & cost tracking.
Logs every agent run to Supabase usage_logs.
Optionally forwards to Langfuse when LANGFUSE_* env vars are set.
"""
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

# ── Cost table — single source of truth in utils/pricing.py ──
import sys
from pathlib import Path as _Path
sys.path.insert(0, str(_Path(__file__).resolve().parent.parent))
from utils.pricing import MODEL_COSTS, estimate_cost  # noqa: E402, F401


# ── Langfuse (optional) ─────────────────────────────────────
_langfuse = None
_langfuse_ok = False

def _init_langfuse():
    global _langfuse, _langfuse_ok
    pk = os.getenv("LANGFUSE_PUBLIC_KEY")
    sk = os.getenv("LANGFUSE_SECRET_KEY")
    host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
    if pk and sk:
        try:
            from langfuse import Langfuse
            _langfuse = Langfuse(public_key=pk, secret_key=sk, host=host)
            _langfuse_ok = True
        except Exception:
            _langfuse_ok = False

_init_langfuse()


# ── Supabase logger ─────────────────────────────────────────
def _get_db():
    """Lazy import to avoid circular deps."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "supabase"))
    import db as _db
    return _db._client


class AgentTrace:
    """Context manager for tracing a single agent run."""

    def __init__(self, agent_slug: str, brand_id: str, model: str = "sonnet-4-6",
                 run_id: Optional[str] = None, metadata: Optional[dict] = None):
        self.agent_slug = agent_slug
        self.brand_id = brand_id
        self.model = model
        # B2 fix: prefer GRID_RUN_ID from env so usage_logs links back to the
        # agent_runs row created by dashboard_api. Fall back to new UUID for
        # direct/pipeline runs that have no dashboard-created row.
        env_run_id = os.getenv("GRID_RUN_ID", "").strip()
        self.run_id = run_id or env_run_id or str(uuid.uuid4())
        self._is_dashboard_run = bool(env_run_id)  # True when invoked via dashboard
        self.metadata = metadata or {}
        self.input_tokens = 0
        self.output_tokens = 0
        self.start_time = None
        self.end_time = None
        self.status = "running"
        self.error = None
        self._langfuse_trace = None

    def __enter__(self):
        self.start_time = time.time()
        # Start Langfuse trace if available
        if _langfuse_ok and _langfuse:
            try:
                self._langfuse_trace = _langfuse.trace(
                    name=f"{self.agent_slug}",
                    id=self.run_id,
                    metadata={
                        "brand_id": self.brand_id,
                        "model": self.model,
                        **self.metadata,
                    },
                )
            except Exception:
                pass
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        if exc_type:
            self.status = "error"
            self.error = str(exc_val)
        else:
            self.status = "success"

        # Log to Supabase
        self._log_to_supabase()

        # Finalize Langfuse
        if self._langfuse_trace:
            try:
                self._langfuse_trace.update(
                    output={"status": self.status, "error": self.error},
                    metadata={
                        "input_tokens": self.input_tokens,
                        "output_tokens": self.output_tokens,
                        "cost_usd": self.cost_usd,
                        "duration_s": self.duration_s,
                    },
                )
                _langfuse.flush()
            except Exception:
                pass

        return False  # don't suppress exceptions

    def add_tokens(self, input_tokens: int = 0, output_tokens: int = 0):
        """Accumulate token usage during the run."""
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens

    def add_generation(self, name: str, input_tokens: int, output_tokens: int,
                       model: Optional[str] = None):
        """Log a single LLM generation within this run."""
        self.add_tokens(input_tokens, output_tokens)
        if self._langfuse_trace:
            try:
                self._langfuse_trace.generation(
                    name=name,
                    model=model or self.model,
                    usage={"input": input_tokens, "output": output_tokens},
                )
            except Exception:
                pass

    @property
    def cost_usd(self) -> float:
        return estimate_cost(self.model, self.input_tokens, self.output_tokens)

    @property
    def duration_s(self) -> float:
        if self.start_time and self.end_time:
            return round(self.end_time - self.start_time, 2)
        return 0.0

    def _log_to_supabase(self):
        """Write usage record to usage_logs and update agent_runs cost columns."""
        try:
            db = _get_db()
            payload: dict = {
                "brand_id": self.brand_id,
                "agent_slug": self.agent_slug,
                "model_used": self.model,
                "input_tokens": self.input_tokens,
                "output_tokens": self.output_tokens,
                "estimated_cost_usd": self.cost_usd,
            }
            # B2 fix: link to the dashboard-created agent_runs row via GRID_RUN_ID.
            if self._is_dashboard_run:
                payload["agent_run_id"] = self.run_id

            db.table("usage_logs").insert(payload).execute()

            # B2 fix: also update agent_runs.api_cost_usd so the cost widget
            # (which reads agent_runs, not usage_logs) shows a non-zero value.
            if self._is_dashboard_run and self.input_tokens > 0:
                from pathlib import Path as _P
                import importlib.util as _ilu
                _db_path = str(_P(__file__).resolve().parent.parent / "supabase" / "db.py")
                _spec = _ilu.spec_from_file_location("_grid_db_t", _db_path)
                _mod = _ilu.module_from_spec(_spec)
                _spec.loader.exec_module(_mod)
                _mod.update_agent_run_costs(
                    self.run_id, self.model,
                    self.input_tokens, self.output_tokens,
                )
        except Exception as e:
            print(f"[tracing] Failed to log usage: {e}")


def trace_agent(agent_slug: str, brand_id: str, model: str = "sonnet-4-6",
                metadata: Optional[dict] = None) -> AgentTrace:
    """Create an agent trace context manager."""
    return AgentTrace(agent_slug=agent_slug, brand_id=brand_id, model=model, metadata=metadata)
