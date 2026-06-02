---
type: community
cohesion: 1.00
members: 2
---

# scripts_scrape_carousel_competitors_py

**Cohesion:** 1.00 - tightly connected
**Members:** 2 nodes

## Members
- [[One-off scrape pull recent carousel posts from carousel-style competitors to st]] - rationale - scripts/scrape_carousel_competitors.py
- [[scrape_carousel_competitors.py]] - code - scripts/scrape_carousel_competitors.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/scripts_scrape_carousel_competitors_py
SORT file.name ASC
```
