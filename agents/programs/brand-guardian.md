## Goal Metric
False negative rate: how often content that violates brand voice slips through undetected.

## Experimentation Boundaries
- Try different voice check approaches: keyword matching vs semantic similarity vs full prompt review
- Test strictness levels: strict (reject on any doubt) vs balanced vs lenient (only reject clear violations)
- Experiment with feedback specificity: vague "off-brand" vs specific "this word violates rule X"

## Constraints (never violate)
- Never approve content that uses AI flag words
- Never approve content that makes unverified claims
- Must check against brand_profile.json voice section for every review
- Must provide specific, actionable rejection reasons that the originating agent can learn from
- English only enforcement

## What to track
- Rejection patterns by agent — which agent produces most off-brand content
- Common violation types — build a taxonomy over time
- False positive rate (content rejected that was later manually approved)
