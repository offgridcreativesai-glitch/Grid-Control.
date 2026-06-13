"""
Rule 10 — Source Citation Enforcement
Shared utility for generation agents (Strategy Agent, Content Planner, Script Writer, etc.)

Two responsibilities:
1. build_source_index(source_files) — flatten every input JSON into a lookup dict
   {f"{file_basename}#{key_path}": value} where key_path uses dot.notation + [N] indexing
2. validate_citations(output, source_index) — checks every entry in output["data_provenance"]
   actually traces back to a real source value (fuzzy token-overlap, allows paraphrasing)

Hard rule:
  Every Claude-generated claim/recommendation/number must appear in data_provenance with
  source_file + source_path + source_value. If validate_citations() fails, the agent
  re-prompts Claude up to MAX_RERUN_ATTEMPTS times with the violation list.
  If still invalid, output is saved with provenance_validation_failed: true for manual review.
"""

import os
import re
import json
from pathlib import Path

MAX_RERUN_ATTEMPTS = 2

# Fuzzy match threshold: source_value tokens must overlap with claim tokens by ≥ this Jaccard
# (allows Claude to paraphrase a long source quote into a shorter claim)
CITATION_FUZZY_MATCH_MIN = 0.30

# Common stopwords (English) — same set used in trend_sentinel.py
_STOPWORDS = {
    "a","an","the","and","or","but","is","are","was","were","be","been","being",
    "in","on","at","to","for","with","by","of","from","as","into","about","this",
    "that","these","those","it","its","you","your","i","we","our","they","their",
    "what","which","who","whom","when","where","why","how","not","no","do","does",
    "did","done","doing","have","has","had","having","will","would","should","could",
    "can","may","might","must","shall","ought","need","one","two","three","first",
    "next","last","more","most","less","least","very","just","than","then","also",
    "if","else","only","own","same","so","such","too","s","t","ll","re","ve","m","d",
}


def _tokenize(text: str) -> set:
    """Lowercase, split on non-word, drop stopwords + tokens < 3 chars. Pure deterministic."""
    if not text:
        return set()
    text = str(text)
    tokens = re.split(r"[^a-z0-9]+", text.lower())
    return {t for t in tokens if len(t) >= 3 and t not in _STOPWORDS}


def _jaccard(a: set, b: set) -> float:
    """Jaccard similarity = |intersection| / |union|."""
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def _flatten(obj, path: str, out: dict):
    """
    Recursively flatten a JSON object into out[key_path] = value (string).
    Lists indexed as [0], [1], ... — paths use dot.notation.
    Only leaf values (str, int, float, bool) are stored.
    """
    if isinstance(obj, dict):
        for k, v in obj.items():
            new_path = f"{path}.{k}" if path else k
            _flatten(v, new_path, out)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            new_path = f"{path}[{i}]"
            _flatten(item, new_path, out)
    else:
        # leaf — coerce to string for matching
        if obj is not None and obj != "":
            out[path] = str(obj)


def build_source_index(source_files: list, virtual_sources: dict | None = None) -> dict:
    """
    Read every JSON file in source_files and build a flat lookup:
      { "trends_live.json#competitor_intel.gaps_identified[1].opportunity_for_brand": "ASKGauravAI can..." }

    source_files: list of paths (str or Path) to JSON files
    virtual_sources: optional dict {virtual_filename: dict_object} for in-memory data
                     (e.g. Trend Researcher's scraped_data before it's saved to disk)

    Skips files that don't exist or fail to parse.
    Returns the index dict.
    """
    index: dict[str, str] = {}

    # Load files from disk
    for fpath in source_files:
        p = Path(fpath)
        if not p.exists():
            continue
        try:
            with open(p) as f:
                data = json.load(f)
        except Exception:
            continue
        leaves: dict[str, str] = {}
        _flatten(data, "", leaves)
        for k, v in leaves.items():
            index[f"{p.name}#{k}"] = v

    # Add virtual in-memory sources
    if virtual_sources:
        for virtual_name, data_obj in virtual_sources.items():
            if not isinstance(data_obj, (dict, list)):
                continue
            leaves = {}
            _flatten(data_obj, "", leaves)
            for k, v in leaves.items():
                index[f"{virtual_name}#{k}"] = v

    return index


def validate_citations(output: dict, source_index: dict) -> tuple[bool, list[dict], dict]:
    """
    Validate every entry in output["data_provenance"] against source_index.

    Each provenance entry must have: claim, source_file, source_path, source_value.
    Validation steps per entry:
      1. source_file + source_path must combine to a key that EXISTS in source_index
      2. source_value tokens must overlap with the actual indexed value tokens by ≥ CITATION_FUZZY_MATCH_MIN
         (this allows paraphrasing while preventing Claude from inventing source content)
      3. claim tokens must overlap with source_value tokens by ≥ CITATION_FUZZY_MATCH_MIN
         (the claim must actually reflect the source, not just cite a random key)

    Returns:
      (is_valid, missing[], report)
        is_valid: True only if every entry passes ALL checks
        missing[]: list of {entry_index, claim, error, key_attempted}
        report: dict for the provenance_validation block in output
    """
    provenance = output.get("data_provenance", [])
    if not isinstance(provenance, list):
        return False, [{"entry_index": -1, "error": "data_provenance is not a list"}], {
            "engine": "rule_10_v1",
            "passed": False,
            "claims_total": 0,
            "claims_validated": 0,
            "missing_citations": ["data_provenance field missing or malformed"],
        }

    missing: list[dict] = []
    validated = 0

    for i, entry in enumerate(provenance):
        if not isinstance(entry, dict):
            missing.append({"entry_index": i, "error": "entry is not a dict"})
            continue

        claim       = entry.get("claim", "")
        source_file = entry.get("source_file", "")
        source_path = entry.get("source_path", "")
        source_val  = entry.get("source_value", "")

        if not all([claim, source_file, source_path, source_val]):
            missing.append({
                "entry_index": i,
                "claim": claim[:100],
                "error": "missing required field (claim/source_file/source_path/source_value)",
                "key_attempted": f"{source_file}#{source_path}",
            })
            continue

        # CHECK 1: key exists in source_index
        key = f"{source_file}#{source_path}"
        actual_value = source_index.get(key)
        if actual_value is None:
            # Try without [0] indices in case Claude omitted them or used different notation
            # Also try with leading dot stripped
            normalized_path = source_path.lstrip(".")
            alt_key = f"{source_file}#{normalized_path}"
            actual_value = source_index.get(alt_key)
            if actual_value is None:
                missing.append({
                    "entry_index": i,
                    "claim": claim[:100],
                    "error": "source_path does not exist in source_index",
                    "key_attempted": key,
                })
                continue

        # CHECK 2: source_value tokens overlap with actual indexed value
        actual_tokens = _tokenize(actual_value)
        cited_tokens  = _tokenize(source_val)
        overlap_actual = _jaccard(cited_tokens, actual_tokens)
        if overlap_actual < CITATION_FUZZY_MATCH_MIN:
            missing.append({
                "entry_index": i,
                "claim": claim[:100],
                "error": f"source_value doesn't match actual indexed value (jaccard={overlap_actual:.2f} < {CITATION_FUZZY_MATCH_MIN})",
                "key_attempted": key,
                "expected_snippet": actual_value[:150],
                "got_snippet": source_val[:150],
            })
            continue

        # CHECK 3: claim tokens overlap with source_value tokens
        claim_tokens = _tokenize(claim)
        overlap_claim = _jaccard(claim_tokens, cited_tokens)
        if overlap_claim < CITATION_FUZZY_MATCH_MIN:
            missing.append({
                "entry_index": i,
                "claim": claim[:100],
                "error": f"claim doesn't reflect source_value (jaccard={overlap_claim:.2f} < {CITATION_FUZZY_MATCH_MIN})",
                "key_attempted": key,
            })
            continue

        validated += 1

    is_valid = len(missing) == 0 and len(provenance) > 0
    report = {
        "engine": "rule_10_v1",
        "fuzzy_match_threshold": CITATION_FUZZY_MATCH_MIN,
        "passed": is_valid,
        "claims_total": len(provenance),
        "claims_validated": validated,
        "missing_citations": missing,
    }

    return is_valid, missing, report


def build_violation_message(missing: list[dict]) -> str:
    """
    Build a human-readable violation message to feed back into the next Claude call.
    The agent uses this to re-prompt Claude with "fix these citations or remove these claims."
    """
    if not missing:
        return ""
    lines = ["The following data_provenance entries failed validation. You must either fix the citation OR remove the corresponding claim from your output:"]
    for m in missing[:10]:  # cap at 10 to keep prompt size manageable
        lines.append(
            f"  - Entry {m.get('entry_index', '?')}: {m.get('error', 'unknown error')}"
        )
        if m.get("key_attempted"):
            lines.append(f"    Key attempted: {m['key_attempted']}")
        if m.get("expected_snippet") and m.get("got_snippet"):
            lines.append(f"    Source actually says: {m['expected_snippet']}")
            lines.append(f"    You cited:           {m['got_snippet']}")
        if m.get("claim"):
            lines.append(f"    Claim: {m['claim']}")
    if len(missing) > 10:
        lines.append(f"  ... and {len(missing) - 10} more violations.")
    return "\n".join(lines)
