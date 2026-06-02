# Agent System — Ui, Trend

> 19 nodes · cohesion 0.15

## Key Concepts

- **validate_citations()** (11 connections) — `agents/_provenance.py`
- **build_source_index()** (9 connections) — `agents/_provenance.py`
- **build_violation_message()** (9 connections) — `agents/_provenance.py`
- **.run_autoresearch_loop()** (8 connections) — `agents/trend_researcher.py`
- **_provenance.py** (7 connections) — `agents/_provenance.py`
- **_flatten()** (4 connections) — `agents/_provenance.py`
- **_jaccard()** (4 connections) — `agents/_provenance.py`
- **_tokenize()** (4 connections) — `agents/_provenance.py`
- **str** (3 connections) — `agents/_provenance.py`
- **Jaccard similarity = |intersection| / |union|.** (2 connections) — `agents/_provenance.py`
- **bool** (1 connections) — `agents/_provenance.py`
- **float** (1 connections) — `agents/_provenance.py`
- **Rule 10 — Source Citation Enforcement Shared utility for generation agents (Stra** (1 connections) — `agents/_provenance.py`
- **Validate every entry in output["data_provenance"] against source_index.      Eac** (1 connections) — `agents/_provenance.py`
- **Build a human-readable violation message to feed back into the next Claude call.** (1 connections) — `agents/_provenance.py`
- **Lowercase, split on non-word, drop stopwords + tokens < 3 chars. Pure determinis** (1 connections) — `agents/_provenance.py`
- **Recursively flatten a JSON object into out[key_path] = value (string).     Lists** (1 connections) — `agents/_provenance.py`
- **Read every JSON file in source_files and build a flat lookup:       { "trends_li** (1 connections) — `agents/_provenance.py`
- **Rule 9 — AutoResearch Loop.          Runs 3 internal variants through Claude:** (1 connections) — `agents/trend_researcher.py`

## Relationships

- [[Agent System — Creative, Brand]] (3 shared connections)
- [[Agent System — Brand]] (3 shared connections)
- [[Agent System — Content, Calendar]] (3 shared connections)
- [[Agent System — Script, Review]] (3 shared connections)
- [[Agent System — Strategy, Trend]] (3 shared connections)
- [[Agent System — Trend, Api]] (3 shared connections)
- [[Agent System — Trend, Calendar]] (1 shared connections)
- [[Agent System — Trend, Ui]] (1 shared connections)

## Source Files

- `agents/_provenance.py`
- `agents/trend_researcher.py`

## Audit Trail

- EXTRACTED: 49 (70%)
- INFERRED: 21 (30%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*