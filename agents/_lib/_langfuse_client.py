"""
Langfuse observability client — Phase 1b (Jun 18 2026).

Follows the langfuse/skills instrumentation guide:
  • Use @observe decorator for agent functions (nested spans for multi-step ops).
  • Call update_current_generation(model, usage_details) on LLM calls so Langfuse
    auto-calculates cost — retires our hand-rolled `cost_reporter.calc_api_cost`.
  • Always flush() before script exits.

Public API:
    lf = get_langfuse()
    @lf.observe(name="strategy-agent.run")
    def run(): ...
    lf.record_llm(model="claude-sonnet-4-6", in_tokens=1200, out_tokens=800)
    lf.flush()

Silent no-op when keys missing (so dev/CI without keys keeps running).
"""
import os
import sys
from contextlib import contextmanager
from typing import Optional
from dotenv import load_dotenv

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(_PROJECT_ROOT, ".env"))


def _resolve_host() -> Optional[str]:
    """Skill canon is LANGFUSE_BASE_URL; SDK reads LANGFUSE_HOST. Accept either."""
    return os.getenv("LANGFUSE_HOST") or os.getenv("LANGFUSE_BASE_URL")


class LangfuseClient:
    """Thin wrapper over the langfuse Python SDK. Silent no-op without keys."""

    def __init__(self):
        self._ok = False
        self._lf = None
        try:
            pk = os.getenv("LANGFUSE_PUBLIC_KEY")
            sk = os.getenv("LANGFUSE_SECRET_KEY")
            if not (pk and sk):
                return
            from langfuse import Langfuse, get_client
            host = _resolve_host()
            if host:
                os.environ.setdefault("LANGFUSE_HOST", host)
            self._lf = Langfuse(public_key=pk, secret_key=sk, host=host)
            if not self._lf.auth_check():
                print("[langfuse] auth_check failed — disabling")
                return
            self._ok = True
            self._get_client = get_client
        except Exception as e:
            print(f"[langfuse] init skipped: {e}")

    @property
    def enabled(self) -> bool:
        return self._ok

    # ── decorator pass-through ─────────────────────────────────
    def observe(self, **kwargs):
        """@lf.observe(name='strategy-agent.run')  — wraps agent functions in a span."""
        if not self._ok:
            def _noop(fn):
                return fn
            return _noop
        from langfuse import observe
        return observe(**kwargs)

    # ── span-level helpers (call inside an @observe scope) ─────
    def set_trace_meta(
        self,
        agent: str,
        brand_slug: Optional[str] = None,
        run_id: Optional[str] = None,
        tags: Optional[list[str]] = None,
        input: Optional[dict] = None,
    ):
        """Stamp metadata on the current (root) span. In v4 this bubbles to the
        trace because the @observe-decorated function is the trace root."""
        if not self._ok:
            return
        try:
            lf = self._get_client()
            lf.update_current_span(
                metadata={
                    "agent": agent,
                    "brand_slug": brand_slug,
                    "run_id": run_id,
                    "tags": tags or [],
                },
                input=input,
            )
        except Exception as e:
            print(f"[langfuse] set_trace_meta failed: {e}")

    @contextmanager
    def start_generation(
        self,
        name: str,
        model: Optional[str] = None,
        input=None,
    ):
        """Open a Langfuse GENERATION as the current observation for the duration
        of the `with` block. Wrap the actual LLM call (e.g. client.messages.stream)
        in this so the generation exists in context when record_llm() stamps usage
        — otherwise usage/cost attaches to the span root and shows $0.00.

        No-op (yields None) when keys are missing.
        """
        if not self._ok:
            yield None
            return
        try:
            lf = self._get_client()
            with lf.start_as_current_observation(
                name=name, as_type="generation", model=model, input=input
            ) as gen:
                yield gen
        except Exception as e:
            print(f"[langfuse] start_generation failed: {e}")
            yield None

    def record_llm(
        self,
        model: str,
        in_tokens: int,
        out_tokens: int,
        cached_tokens: int = 0,
    ):
        """Stamp the current generation with model + token usage so Langfuse
        auto-calculates cost from its model registry. Call right after the LLM call,
        inside a start_generation() block."""
        if not self._ok:
            return
        try:
            lf = self._get_client()
            lf.update_current_generation(
                model=model,
                usage_details={
                    "input": in_tokens,
                    "output": out_tokens,
                    "cache_read_input_tokens": cached_tokens,
                },
            )
        except Exception as e:
            print(f"[langfuse] record_llm failed: {e}")

    def set_output(self, output):
        """Record a meaningful trace output (e.g. winning variant id)."""
        if not self._ok:
            return
        try:
            self._get_client().update_current_span(output=output)
        except Exception as e:
            print(f"[langfuse] set_output failed: {e}")

    def flush(self):
        """ALWAYS call before script exit. Skill calls this the #1 mistake."""
        if not self._ok:
            return
        try:
            self._lf.flush()
        except Exception as e:
            print(f"[langfuse] flush failed: {e}")


_singleton: Optional[LangfuseClient] = None


def get_langfuse() -> LangfuseClient:
    global _singleton
    if _singleton is None:
        _singleton = LangfuseClient()
    return _singleton
