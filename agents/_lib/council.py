"""
Council Pattern for AutoResearch (Phase 7)

Inspired by Karpathy's LLM Council: generate variants → blind cross-review → synthesize.

Usage:
    from agents._lib.council import Council

    council = Council(agent_name="script-writer")
    result = council.evaluate(
        variants=[variant_1, variant_2, variant_3],
        criteria=Council.SCRIPT_CRITERIA,
        brand_slug="askgauravai",
    )
    # result.winner — the best variant
    # result.scores — per-variant scores with reasoning
    # result.synthesis — combined recommendation
"""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class VariantScore:
    variant_index: int
    criterion: str
    score: float  # 0-10
    reasoning: str


@dataclass
class CouncilResult:
    winner_index: int
    winner: str
    scores: list[VariantScore]
    synthesis: str
    eval_trace: dict


# Pre-defined scoring criteria per agent type
SCRIPT_CRITERIA = [
    {"name": "hook_strength", "weight": 0.35, "description": "Does the hook stop the scroll in under 3 seconds? Is it specific, not generic?"},
    {"name": "brand_voice", "weight": 0.30, "description": "Does it match the brand's voice profile? No AI-sounding language. No corporate speak."},
    {"name": "cta_clarity", "weight": 0.20, "description": "Is the call-to-action clear, specific, and actionable?"},
    {"name": "platform_fit", "weight": 0.15, "description": "Is the format optimized for the target platform?"},
]

STRATEGY_CRITERIA = [
    {"name": "data_backing", "weight": 0.30, "description": "Are claims backed by real data with cited sources?"},
    {"name": "feasibility", "weight": 0.25, "description": "Can this be executed with available resources in the given timeframe?"},
    {"name": "differentiation", "weight": 0.25, "description": "Does this create meaningful differentiation from competitors?"},
    {"name": "actionability", "weight": 0.20, "description": "Are the next steps clear and specific enough to execute immediately?"},
]

CONTENT_PLAN_CRITERIA = [
    {"name": "narrative_arc", "weight": 0.30, "description": "Does the plan tell a story across the month? Are there callbacks?"},
    {"name": "fatigue_management", "weight": 0.25, "description": "Is there enough variety to prevent audience fatigue?"},
    {"name": "funnel_coverage", "weight": 0.25, "description": "Does it cover awareness, consideration, and conversion stages?"},
    {"name": "brand_alignment", "weight": 0.20, "description": "Does every post reinforce the brand's core message?"},
]


class Council:
    SCRIPT_CRITERIA = SCRIPT_CRITERIA
    STRATEGY_CRITERIA = STRATEGY_CRITERIA
    CONTENT_PLAN_CRITERIA = CONTENT_PLAN_CRITERIA

    def __init__(self, agent_name: str):
        self.agent_name = agent_name

    def build_review_prompt(
        self,
        variants: list[str],
        criteria: list[dict],
    ) -> str:
        """Build the blind cross-review prompt. Variants are labeled A, B, C...
        to eliminate bias from knowing which agent/prompt generated them."""
        labels = [chr(65 + i) for i in range(len(variants))]

        criteria_block = "\n".join(
            f"- **{c['name']}** (weight: {c['weight']}): {c['description']}"
            for c in criteria
        )

        variants_block = "\n\n".join(
            f"### Variant {labels[i]}\n```\n{v}\n```"
            for i, v in enumerate(variants)
        )

        return f"""You are an expert content evaluator. Score each variant BLINDLY against the criteria below.
You do NOT know which prompt, agent, or approach generated each variant. Judge purely on output quality.

## Scoring Criteria
{criteria_block}

## Variants to Evaluate
{variants_block}

## Instructions
For each variant, score each criterion from 0-10. Then compute weighted totals.
Return ONLY valid JSON in this exact format:
{{
  "scores": [
    {{
      "variant": "A",
      "criteria_scores": {{"criterion_name": {{"score": 8, "reasoning": "..."}}}},
      "weighted_total": 7.5
    }}
  ],
  "winner": "A",
  "synthesis": "One-paragraph explanation of why the winner is best and what elements from other variants could improve it."
}}"""

    def parse_review(self, raw_response: str, variants: list[str]) -> CouncilResult:
        """Parse the LLM's review response into a structured CouncilResult."""
        try:
            cleaned = raw_response.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            return CouncilResult(
                winner_index=0,
                winner=variants[0],
                scores=[],
                synthesis="Failed to parse council review — defaulting to first variant.",
                eval_trace={"error": "JSON parse failed", "raw": raw_response[:500]},
            )

        scores_list: list[VariantScore] = []
        for entry in data.get("scores", []):
            variant_label = entry.get("variant", "A")
            idx = ord(variant_label) - 65
            for crit_name, crit_data in entry.get("criteria_scores", {}).items():
                scores_list.append(VariantScore(
                    variant_index=idx,
                    criterion=crit_name,
                    score=float(crit_data.get("score", 0)),
                    reasoning=crit_data.get("reasoning", ""),
                ))

        winner_label = data.get("winner", "A")
        winner_idx = min(ord(winner_label) - 65, len(variants) - 1)
        winner_idx = max(0, winner_idx)

        return CouncilResult(
            winner_index=winner_idx,
            winner=variants[winner_idx],
            scores=scores_list,
            synthesis=data.get("synthesis", ""),
            eval_trace={
                "raw_scores": data.get("scores", []),
                "timestamp": datetime.now().isoformat(),
                "agent": self.agent_name,
                "variant_count": len(variants),
            },
        )

    def evaluate(
        self,
        variants: list[str],
        criteria: list[dict],
        brand_slug: str,
        output_type: str = "script",
    ) -> CouncilResult:
        """Full council evaluation: build prompt → call Claude → parse → save trace."""
        import anthropic

        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key or len(variants) < 2:
            return CouncilResult(
                winner_index=0,
                winner=variants[0] if variants else "",
                scores=[],
                synthesis="Council skipped — insufficient variants or no API key.",
                eval_trace={"skipped": True},
            )

        prompt = self.build_review_prompt(variants, criteria)
        client = anthropic.Anthropic(api_key=api_key)

        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}],
                timeout=120.0,
            )
            raw_text = "".join(b.text for b in response.content if hasattr(b, "text"))
        except Exception as e:
            return CouncilResult(
                winner_index=0,
                winner=variants[0],
                scores=[],
                synthesis=f"Council call failed: {e}",
                eval_trace={"error": str(e)},
            )

        result = self.parse_review(raw_text, variants)
        self.save_eval_trace(brand_slug, result, output_type)
        return result

    def save_eval_trace(
        self,
        brand_slug: str,
        result: CouncilResult,
        output_type: str,
    ) -> Path:
        """Save the cross-review scores for auditability."""
        trace_dir = Path(f"brands/{brand_slug}/eval_traces/{self.agent_name}")
        trace_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = trace_dir / f"{output_type}_{timestamp}.json"

        trace = {
            "output_type": output_type,
            "winner_index": result.winner_index,
            "synthesis": result.synthesis,
            "scores": [
                {
                    "variant_index": s.variant_index,
                    "criterion": s.criterion,
                    "score": s.score,
                    "reasoning": s.reasoning,
                }
                for s in result.scores
            ],
            **result.eval_trace,
        }

        path.write_text(json.dumps(trace, indent=2), encoding="utf-8")
        return path
