/**
 * THE SECRET — client-facing persona layer.
 *
 * The backend runs an 18-agent roster with internal slugs/roles. The client never
 * sees those. Every backend slug maps to ONE of the 8 friendly team characters
 * (atlas/riveter/aegis/exactor/spark/lumen/nexus/forge). The UI shows only the
 * persona name + avatar + a plain-English phrase — never a slug, model, or status code.
 */
import type { AgentKey } from "@/components/AgentCharacter"

export interface Persona {
  key: AgentKey
  name: string
  role: string
  /** present-tense action shown while this persona is working */
  action: string
}

const PERSONAS: Record<AgentKey, Persona> = {
  atlas: { key: "atlas", name: "Atlas", role: "Chief of Staff", action: "is coordinating the team" },
  riveter: { key: "riveter", name: "Riveter", role: "Content Architect", action: "is drafting content" },
  aegis: { key: "aegis", name: "Aegis", role: "Brand Guardian", action: "is checking brand fit" },
  exactor: { key: "exactor", name: "Exactor", role: "Performance Analyst", action: "is reviewing performance" },
  spark: { key: "spark", name: "Spark", role: "Trend Researcher", action: "is researching trends" },
  lumen: { key: "lumen", name: "Lumen", role: "Creative Director", action: "is designing visuals" },
  nexus: { key: "nexus", name: "Nexus", role: "Community Manager", action: "is handling conversations" },
  forge: { key: "forge", name: "Forge", role: "Builder", action: "is building" },
  beacon: { key: "beacon", name: "Beacon", role: "Search & Discovery", action: "is tuning search visibility" },
}

// 18 backend slugs → 8 client personas. Anything unknown falls back to Atlas.
const SLUG_TO_KEY: Record<string, AgentKey> = {
  "ceo-brain": "atlas",
  "strategy-agent": "atlas",
  "content-planner": "riveter",
  "script-writer": "riveter",
  "creative-director": "lumen",
  "carousel-designer": "lumen",
  "ad-strategist": "forge",
  "data-analyst": "exactor",
  "performance-tracker": "exactor",
  "funnel-specialist": "forge",
  "trend-researcher": "spark",
  "trend-sentinel": "spark",
  "website-agent": "forge",
  "brand-guardian": "aegis",
  "seo-aeo-agent": "beacon",
  "email-marketing-agent": "forge",
  "community-manager": "nexus",
  "dm-customer-hunter": "nexus",
  // Proactive weekly program (GRIDLOCK-PROGRAM-01JUL) — Atlas is chief of staff,
  // presents the system's own review/build cadence, not a specific content agent.
  "weekly-program": "atlas",
  "weekly-review-composer": "atlas",
}

/** The 8-strong client-facing cast, in display order (Atlas leads). */
export const CAST: Persona[] = (
  ["atlas", "riveter", "lumen", "spark", "exactor", "aegis", "nexus", "forge", "beacon"] as AgentKey[]
).map((k) => PERSONAS[k])

export function personaForSlug(slug?: string | null): Persona {
  if (slug) {
    if (SLUG_TO_KEY[slug]) return PERSONAS[SLUG_TO_KEY[slug]]
    if ((slug as AgentKey) in PERSONAS) return PERSONAS[slug as AgentKey] // tolerate a friendly key
  }
  return PERSONAS.atlas
}

/** Plain-English line for the Live Work Feed. Never leaks a status code. */
export function activityPhrase(slug: string | undefined, status: string | undefined): string {
  const p = personaForSlug(slug)
  switch ((status || "").toLowerCase()) {
    case "running":
      return `${p.name} ${p.action}`
    case "success":
    case "done":
      return `${p.name} finished`
    case "queued":
      return `${p.name} is lined up`
    case "blocked":
      return `${p.name} is waiting on you`
    case "error":
      return `${p.name} needs a hand`
    default:
      return `${p.name} is standing by`
  }
}
