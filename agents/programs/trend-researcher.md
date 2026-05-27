## Goal Metric
Trend relevance score: percentage of identified trends that get used in actual content within 7 days.

## Experimentation Boundaries
- Try different source mixes: social-heavy vs news-heavy vs Reddit-heavy vs podcast-heavy
- Test trend classification accuracy: Fad vs Micro-trend vs Structural Shift
- Experiment with relevance scoring: keyword overlap vs semantic brand alignment vs audience overlap
- Try different update frequencies: daily vs every-3-days vs weekly deep-dive

## Constraints (never violate)
- Every trend must have a real source URL and timestamp
- Classification must be one of: Fad, Micro-trend, Structural Shift
- Relevance score must be mapped to brand profile
- ACTIVE_BRAND env var must be set before any scrape
- Never assume trend data — if scrape fails, report the failure

## What to track
- Which sources produce highest-relevance trends for each brand
- Trend-to-content conversion time
- Classification accuracy over time (were Fads actually Fads?)
