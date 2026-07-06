"""
Brand Archetype Reasoning Layer — Fable 5 rebuild (Jul 3 2026).

THE fix for the "one psychology fits all brands" gap: every content agent must
classify WHAT KIND of brand it is writing for as an explicit reasoning step
BEFORE generating, and that classification changes which psychological levers
get used — not just which variables get substituted.

Three archetypes (from the review brief, section 3):

  • product   — impulse-driven, visual-first. STEPPS Public + Practical Value.
                Hooks lean Aspirational/Exclusivity. CTA is SHORT-distance
                (shop link, same session).
  • service   — trust-driven, long consideration cycle. STEPPS Social Currency
                + Stories. Hooks lean Authority/Specificity. CTA is LONG-distance
                (book a call, DM to qualify — never a hard sell early).
  • personal  — parasocial. STEPPS Emotion + Identity. Hooks lean Pain Point /
                Identity. CTA is about relationship and reply, not conversion.

Design rules:
  1. Classification is DETERMINISTIC-first: an explicit
     brand_profile["business_model_archetype"] always wins (human override).
     Otherwise a keyword/field heuristic over the brand profile decides —
     no LLM call, zero cost, and every signal cites the profile field it
     came from (Rule 10 compatible).
  2. The result is PERSISTED to brands/{slug}/brand_archetype.json so it is
     human-inspectable, stable across runs, and editable like any other
     brand-memory file. Delete the file to force re-classification.
  3. Agents consume it via directive_block(), a labeled "STEP 0" prompt
     section that rewires variant frames, hook-pattern priority, STEPPS
     lever priority, and CTA distance per archetype. The strategy TABLE is
     data, not if-branches inside agent prompts.

Public API:
    from agents._lib.brand_archetype import classify_brand, directive_block
    record = classify_brand(brand_slug, brand_profile)   # dict, persisted
    block  = directive_block(record, agent="script-writer")  # prompt text
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BRANDS_DIR = os.environ.get("BRANDS_DIR", os.path.join(_PROJECT_ROOT, "brands"))

ARCHETYPES = ("product", "service", "personal")

# ── The strategy table: archetype → psychology. Data, not code branches. ──────

STRATEGY = {
    "product": {
        "label": "Product brand (physical/impulse purchase)",
        "buying_psychology": (
            "Impulse-driven, visual-first. The buyer decides in seconds based on how the "
            "product looks and what owning it says about them. Desire precedes justification."
        ),
        "stepps_priority": ["Public", "Practical Value", "Triggers"],
        "stepps_avoid": "Do not force founder Stories — the product IS the story.",
        "hook_patterns": [
            "Aspirational", "Exclusivity", "Impossible Claim",
            "Contrast Principle", "Curiosity Gap",
        ],
        "cta_distance": "SHORT",
        "cta_rule": (
            "CTA closes in the same session: shop link, drop notification, 'link in bio'. "
            "Never ask for a call or a DM-to-qualify — friction kills impulse."
        ),
        "proof_style": "Visual social proof: on-body/in-use shots, UGC, 'seen on' — not case studies.",
        "consideration_cycle": "Seconds to hours. Optimize for scroll-stop and same-session action.",
        "variant_frames": [
            ("DESIRE-FIRST", "Open on the transformation of look/lifestyle the product creates. Make them want it before they understand it."),
            ("DROP/SCARCITY", "Open on newness, limited availability, or insider access. Urgency is the engine."),
            ("IDENTITY-OF-THE-WEARER", "Open on who uses/wears this and what it signals publicly. Belonging is the hook."),
        ],
    },
    "service": {
        "label": "Service brand (trust purchase, long consideration)",
        "buying_psychology": (
            "Trust-driven, long consideration cycle. The buyer is evaluating competence and "
            "risk over weeks. Every piece of content is a deposit in a trust account — a hard "
            "sell early withdraws everything."
        ),
        "stepps_priority": ["Social Currency", "Stories", "Practical Value"],
        "stepps_avoid": "Do not lean on Public visibility — nobody 'shows off' hiring a service.",
        "hook_patterns": [
            "Specificity", "Time/Money Claim", "Contrarian Truth",
            "Pain Point", "Curiosity Gap",
        ],
        "cta_distance": "LONG",
        "cta_rule": (
            "CTA moves ONE step down a long funnel: save this, DM a question, book a call "
            "(late-funnel only). NEVER a hard sell or price push in cold content."
        ),
        "proof_style": "Authority proof: specific numbers, case stories, before/after with real data.",
        "consideration_cycle": "Weeks to months. Optimize for saves, profile visits, and inbound DMs.",
        "variant_frames": [
            ("PAIN-FIRST", "Open with the specific business pain the audience feels right now. Make them feel seen, then show the path."),
            ("PROOF-FIRST", "Open with a specific, quantified client/self result. Lead with the number, then the method."),
            ("CONTRARIAN-AUTHORITY", "Open by arguing against the popular advice in the niche, backed by lived experience."),
        ],
    },
    "personal": {
        "label": "Personal/influencer brand (parasocial relationship)",
        "buying_psychology": (
            "Parasocial. The audience is building a one-sided relationship with a person. "
            "They buy (attention, then products) because of who the person is and how the "
            "content makes them feel about themselves."
        ),
        "stepps_priority": ["Emotion", "Identity", "Social Currency"],
        "stepps_avoid": "Do not optimize for Practical Value alone — tips without a person attached are commodity content.",
        "hook_patterns": [
            "Pain Point", "Identity", "Contrarian Truth",
            "Fear/Loss", "Curiosity Gap",
        ],
        "cta_distance": "RELATIONSHIP",
        "cta_rule": (
            "CTA is about reply and relationship: answer a question, share your take, follow "
            "the journey. Immediate conversion CTAs are banned in cold content."
        ),
        "proof_style": "Lived-history proof: real moments, real failures, receipts from the person's own journey.",
        "consideration_cycle": "Months. Optimize for reply rate, shares, and returning viewers.",
        "variant_frames": [
            ("STORY-FIRST", "Open inside a real lived moment (from approved lived-history sources only). Specific scene, then the lesson."),
            ("BELIEF-FIRST", "Open with a strongly-held contrarian belief the person actually holds. Take a side."),
            ("IDENTITY-MIRROR", "Open by describing the viewer to themselves ('you're the founder who...'). Recognition is the hook."),
        ],
    },
}

# ── Classification heuristics (field, keywords, archetype, weight) ────────────

_SERVICE_KW = (
    "agency", "consult", "coaching", "done-for-you", "service", "retainer",
    "b2b", "saas", "software", "audit", "report", "freelanc", "studio",
)
_PRODUCT_KW = (
    "apparel", "clothing", "t-shirt", "tee", "fashion", "skincare", "cosmetic",
    "d2c product", "ecommerce", "e-commerce", "merch", "accessor", "footwear",
    "drop", "collection", "sku", "shopify",
)
_PERSONAL_KW = (
    "personal brand", "influencer", "creator", "founder brand", "thought leader",
    "on camera", "face of", "storytell",
)


def _profile_text(profile: dict, fields: tuple[str, ...]) -> str:
    parts = []
    for f in fields:
        v = profile.get(f)
        if v:
            parts.append(json.dumps(v) if not isinstance(v, str) else v)
    return " ".join(parts).lower()


def _heuristic_scores(profile: dict) -> tuple[dict, list[str]]:
    """Score each archetype from brand_profile fields. Returns (scores, signals)
    where every signal names the profile field it came from (provenance)."""
    scores = {a: 0.0 for a in ARCHETYPES}
    signals: list[str] = []

    txt_fields = ("brand_type", "business_model", "category", "product",
                  "product_name", "positioning", "brand_name", "what_we_sell",
                  "offer", "description", "unique_tension")
    txt = _profile_text(profile, txt_fields)

    for kw in _PRODUCT_KW:
        if kw in txt:
            scores["product"] += 2
            signals.append(f"keyword '{kw}' in profile text fields → product")
    for kw in _SERVICE_KW:
        if kw in txt:
            scores["service"] += 2
            signals.append(f"keyword '{kw}' in profile text fields → service")
    for kw in _PERSONAL_KW:
        if kw in txt:
            scores["personal"] += 2
            signals.append(f"keyword '{kw}' in profile text fields → personal")

    # Structural signals
    if profile.get("founder_identity") and profile.get("lived_history_sources"):
        scores["personal"] += 3
        signals.append("founder_identity + lived_history_sources present → personal")
    if profile.get("price_point") or profile.get("pricing"):
        p = str(profile.get("price_point") or profile.get("pricing")).lower()
        if any(t in p for t in ("call", "custom", "retainer", "quote")):
            scores["service"] += 2
            signals.append("pricing requires call/custom quote → service")
    if profile.get("shop_link") or profile.get("store_url") or profile.get("catalog"):
        scores["product"] += 3
        signals.append("shop_link/store_url/catalog present → product")
    if profile.get("hire_signal_rule"):
        scores["personal"] += 1
        signals.append("hire_signal_rule present (person, not shop) → personal")

    return scores, signals


def classify_brand(brand_slug: str, brand_profile: dict, brands_dir: str | None = None) -> dict:
    """Explicit STEP-0 classification. Order of authority:
      1. persisted brands/{slug}/brand_archetype.json with source='human' (never overwritten)
      2. explicit brand_profile['business_model_archetype'] (human declaration)
      3. field/keyword heuristics over the profile (each signal cites its field)
    Persists the result; returns the full record."""
    bdir = os.path.join(brands_dir or BRANDS_DIR, brand_slug)
    path = os.path.join(bdir, "brand_archetype.json")

    # 1. existing human-pinned record wins
    try:
        with open(path) as f:
            existing = json.load(f)
        if existing.get("archetype") in ARCHETYPES and existing.get("source") == "human":
            return existing
    except Exception:
        existing = None

    # 2. explicit profile declaration
    declared = str(brand_profile.get("business_model_archetype", "")).strip().lower()
    if declared in ARCHETYPES:
        record = {
            "archetype": declared,
            "source": "brand_profile.business_model_archetype",
            "confidence": 1.0,
            "signals": ["declared in brand_profile.business_model_archetype"],
            "secondary": None,
            "classified_at": datetime.now(timezone.utc).isoformat(),
        }
        _persist(path, record)
        return record

    # 3. heuristic
    scores, signals = _heuristic_scores(brand_profile)
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    top, top_score = ranked[0]
    second, second_score = ranked[1]
    total = sum(scores.values()) or 1.0

    if top_score == 0:
        # No signal at all — refuse to guess (zero-fabrication). Personal is NOT
        # a safe default; mark unknown and tell the agent to ask.
        record = {
            "archetype": "unknown",
            "source": "heuristic",
            "confidence": 0.0,
            "signals": ["no classifiable signals in brand_profile — ask the brand owner"],
            "secondary": None,
            "classified_at": datetime.now(timezone.utc).isoformat(),
        }
    else:
        record = {
            "archetype": top,
            "source": "heuristic",
            "confidence": round(top_score / total, 2),
            "signals": signals,
            "secondary": second if second_score >= top_score * 0.6 and second_score > 0 else None,
            "classified_at": datetime.now(timezone.utc).isoformat(),
        }
    _persist(path, record)
    return record


def _persist(path: str, record: dict) -> None:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(record, f, indent=2)
    except Exception as e:
        print(f"[brand_archetype] persist skipped: {e}")


# ── Prompt directive ──────────────────────────────────────────────────────────

def directive_block(record: dict, agent: str = "") -> str:
    """Returns the STEP 0 prompt section. Empty-ish safe block when unknown."""
    arch = record.get("archetype")
    if arch not in STRATEGY:
        return (
            "\n═══ STEP 0 — BRAND ARCHETYPE (UNRESOLVED) ═══\n"
            "The brand's business-model archetype could not be classified from the profile.\n"
            "Do NOT assume a psychology. Flag in your output that the brand owner must "
            "declare business_model_archetype (product | service | personal) in brand_profile.json, "
            "and write conservatively: no hard CTAs, no founder-story fabrication.\n"
        )

    s = STRATEGY[arch]
    secondary_note = ""
    sec = record.get("secondary")
    if sec and sec in STRATEGY:
        secondary_note = (
            f"\nSECONDARY ARCHETYPE: {sec} — blend in its levers only where the primary "
            f"psychology is not weakened (e.g. a personal brand selling a product may use "
            f"one SHORT-distance CTA per week, never in cold content)."
        )

    frames = "\n".join(
        f"  VARIANT {chr(65 + i)} — {name}: {desc}"
        for i, (name, desc) in enumerate(s["variant_frames"])
    )

    return f"""
═══ STEP 0 — BRAND ARCHETYPE REASONING (do this BEFORE anything else) ═══
CLASSIFICATION: {arch.upper()} — {s['label']}
  (source: {record.get('source')}, confidence: {record.get('confidence')})

BUYING PSYCHOLOGY: {s['buying_psychology']}

THIS CLASSIFICATION CHANGES HOW YOU REASON — not just what words you fill in:
• STEPPS LEVERS (priority order): {', '.join(s['stepps_priority'])}. {s['stepps_avoid']}
• HOOK PATTERNS (draw your hooks from these FIRST): {', '.join(s['hook_patterns'])}
• CTA DISTANCE: {s['cta_distance']} — {s['cta_rule']}
• PROOF STYLE: {s['proof_style']}
• CONSIDERATION CYCLE: {s['consideration_cycle']}

VARIANT FRAMES FOR THIS ARCHETYPE (use these as your AutoResearch variants):
{frames}
{secondary_note}
In your output, echo the archetype you reasoned with as "brand_archetype": "{arch}".
═══ END STEP 0 ═══
"""
