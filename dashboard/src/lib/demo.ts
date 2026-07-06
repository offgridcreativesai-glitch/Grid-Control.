/**
 * DEV-only demo mode. Lets someone walk the whole product (landing → Vault) with
 * believable seeded data and NO real account. Gated on import.meta.env.DEV +
 * localStorage "gc_demo" — it can never activate in a production build.
 *
 * The demo brand ("Aurora Skincare") is fictional — not a real client.
 */
import type { PendingOutput, PublishedPost, AgentStatus, DigestData } from "@/hooks/useGridApi"
import type { ActivityEvent } from "@/store/appStore"
import type { Brand } from "@/store/brandStore"
import { useBrandStore } from "@/store/brandStore"
import { useAppStore } from "@/store/appStore"
import { useAuthStore } from "@/store/authStore"

export const DEMO_EMAIL = "demo@gridcontrol.app"

export function isDemo(): boolean {
  return (
    import.meta.env.DEV &&
    typeof window !== "undefined" &&
    localStorage.getItem("gc_demo") === "1"
  )
}

export const DEMO_BRAND: Brand = { slug: "demo", name: "Aurora Skincare", handle: "aurora.skin", primary: true }

const now = Date.now()
const iso = (msAgo: number) => new Date(now - msAgo).toISOString()
const isoIn = (msAhead: number) => new Date(now + msAhead).toISOString()
const DAY = 86_400_000

// ── Pending drafts (Command inline cards · Vault drafts · Calendar scheduled) ──
export const DEMO_PENDING: PendingOutput[] = [
  {
    filename: "demo_ig_retinol_myths.json",
    agent_slug: "carousel-designer",
    agent_name: "Carousel Designer",
    created_at: iso(2 * 3600_000),
    platform: "instagram",
    title: "5 retinol myths that are wrecking your skin",
    caption:
      "Everyone gets retinol wrong.\n\nHere are 5 myths we hear every week — and what actually works instead. Save this before your next routine. 👇",
    body_text: "",
    hashtags: ["skincare", "retinol", "skintok", "dermatology"],
    slide_images: [],
    scheduled_for: isoIn(2 * DAY + 5 * 3600_000),
  },
  {
    filename: "demo_li_founder_pov.json",
    agent_slug: "script-writer",
    agent_name: "Script Writer",
    created_at: iso(5 * 3600_000),
    platform: "linkedin",
    title: "Why we stopped chasing virality",
    caption:
      "We grew faster the month we posted less.\n\nHere's the counter-intuitive play that doubled our saves without doubling output — a founder's honest take.",
    body_text: "",
    hashtags: ["founder", "marketing", "brandbuilding"],
    slide_images: [],
    scheduled_for: isoIn(5 * DAY + 3 * 3600_000),
  },
  {
    filename: "demo_x_hot_take.json",
    agent_slug: "script-writer",
    agent_name: "Script Writer",
    created_at: iso(40 * 60_000),
    platform: "x",
    title: null,
    caption:
      "Hot take: your skincare brand doesn't have a content problem.\n\nIt has a 'sounding like everyone else' problem. Fix the voice, the reach follows.",
    body_text: "",
    hashtags: [],
    slide_images: [],
    scheduled_for: null,
  },
  // Plan-level item — renders in the Vault's "Big decisions" lane so the demo
  // shows decision-weight separation (strategy ≠ single caption).
  {
    filename: "demo_week3_calendar.json",
    agent_slug: "content-planner",
    agent_name: "Content Planner",
    created_at: iso(7 * 3600_000),
    platform: null,
    title: "Week 3 content plan — barrier-repair education arc",
    caption:
      "Next week doubles down on what's working: 3 education carousels on barrier repair (your top saver), 1 founder POV, 1 community reply-bait. Posting shifts to 9am after last week's morning spike.",
    body_text: "",
    hashtags: [],
    slide_images: [],
    scheduled_for: null,
  },
]

// ── Live agent status (names must match the canonical roster) ──
export const DEMO_AGENT_STATUS: AgentStatus[] = [
  { slug: "script-writer", name: "Script Writer", status: "running", last_run: iso(60_000) },
  { slug: "creative-director", name: "Creative Director", status: "running", last_run: iso(120_000) },
  { slug: "trend-researcher", name: "Trend Researcher", status: "running", last_run: iso(8 * 60_000) },
  { slug: "content-planner", name: "Content Planner", status: "success", last_run: iso(40 * 60_000) },
  { slug: "data-analyst", name: "Data Analyst", status: "success", last_run: iso(3 * 3600_000) },
]

// ── Live Work Feed stream ──
export const DEMO_ACTIVITY: ActivityEvent[] = [
  { agent: "creative-director", status: "running", brand: "demo", timestamp: iso(90_000) },
  { agent: "script-writer", status: "running", brand: "demo", timestamp: iso(3 * 60_000) },
  { agent: "trend-researcher", status: "running", brand: "demo", timestamp: iso(9 * 60_000) },
  { agent: "carousel-designer", status: "success", brand: "demo", timestamp: iso(26 * 60_000) },
  { agent: "content-planner", status: "success", brand: "demo", timestamp: iso(52 * 60_000) },
  { agent: "data-analyst", status: "success", brand: "demo", timestamp: iso(3 * 3600_000) },
]

// ── Daily digest (Intelligence verdict hero) ──
export const DEMO_DIGEST: DigestData = {
  brand_slug: "demo",
  verdict: "TRACK",
  verdict_reason:
    "Founder-POV carousels are driving a steady climb in saves. Lean in — but reach on Reels dipped 12% this week, so keep an eye on format mix.",
  verdict_at: iso(3 * 3600_000),
  sentinel: {
    signals: [
      { label: "Saves trending up", day_count: 6, reason: "Save rate up 6 days running on carousels." },
      { label: "Reel reach softening", day_count: 3, reason: "Reel reach down 3 days — fatigue on talking-head format." },
    ],
    tracked_count: 9,
  },
  trends: [
    { title: "‘Skin barrier’ search interest spiking", relevance: 0.86, classification: "Micro-trend" },
    { title: "Founder-on-camera reels outperforming polished ads", relevance: 0.79, classification: "Structural Shift" },
  ],
  contradictions: { counts: {}, findings: [], blocking: false },
  last_pipeline_run: iso(3 * 3600_000),
  has_data: true,
}

// ── Performance history (Intelligence charts / KPIs / patterns) ──
type PerfHistory = {
  posts: Array<{ id: string; platform: string; caption: string; impressions: number; engagements: number; saves: number; posted_at: string }>
  followers_total: number
  followers_delta: number
  winning_patterns: Record<string, string[]>
  dead_patterns: string[]
}

export const DEMO_PERF_HISTORY: PerfHistory = {
  posts: [
    { id: "p1", platform: "instagram", caption: "5 retinol myths, busted", impressions: 18420, engagements: 2140, saves: 612, posted_at: iso(3 * DAY) },
    { id: "p2", platform: "instagram", caption: "The 3-step barrier routine", impressions: 14100, engagements: 1680, saves: 540, posted_at: iso(6 * DAY) },
    { id: "p3", platform: "linkedin", caption: "Why we posted less and grew more", impressions: 9200, engagements: 870, saves: 120, posted_at: iso(8 * DAY) },
    { id: "p4", platform: "x", caption: "Hot take on skincare content", impressions: 6400, engagements: 410, saves: 38, posted_at: iso(10 * DAY) },
    { id: "p5", platform: "instagram", caption: "Founder POV: our biggest mistake", impressions: 21300, engagements: 2760, saves: 781, posted_at: iso(12 * DAY) },
    { id: "p6", platform: "youtube", caption: "How we build a week of content", impressions: 5200, engagements: 520, saves: 96, posted_at: iso(15 * DAY) },
  ],
  followers_total: 48230,
  followers_delta: 1284,
  winning_patterns: {
    hook_patterns_top_3: ["Bold contrarian hook in line 1", "Founder-POV confession open", "Numbered myth-buster"],
    formats_top_3: ["Carousel", "Talking-head Reel"],
  },
  dead_patterns: ["Generic tips listicles", "Over-polished stock visuals"],
}

// ── Published / scheduled (Vault Ready + Published) ──
export const DEMO_PUBLISHED: PublishedPost[] = [
  {
    id: "demo_pub_ig_barrier.json",
    post_id: "ig_barrier",
    platform: "instagram",
    title: "The 3-step barrier routine",
    caption: "Your skin barrier is the whole game. Here's the 3-step routine we swear by.",
    body_text: "",
    slide_images: [],
    hashtags: ["skincare", "skinbarrier"],
    scheduled_for: null,
    approved_at: iso(6 * DAY),
    posted_at: iso(6 * DAY),
    status: "published",
    engagement: { likes: 1420, comments: 96, shares: 54, impressions: 14100, saves: 540 },
    agent_slug: "carousel-designer",
    filepath: "",
  },
  {
    id: "demo_sched_li_hiring.json",
    post_id: "li_hiring",
    platform: "linkedin",
    title: "We're hiring a content lead",
    caption: "We're looking for a content lead who gets founder-led brands. Here's what the role looks like.",
    body_text: "",
    slide_images: [],
    hashtags: ["hiring"],
    scheduled_for: isoIn(3 * DAY),
    approved_at: iso(60 * 60_000),
    posted_at: null,
    status: "scheduled",
    engagement: null,
    agent_slug: "script-writer",
    filepath: "",
  },
]

// ── Memory page — structured, editable brand memory (Noimos-style) ──
export interface MemoryListItem { id: string; text: string }
export interface MemoryService { id: string; name: string; description: string }
export interface MemoryAccount { id: string; handle: string; platform: string }

export interface MemoryDoc {
  workspace: {
    brandOverview: string
    services: MemoryService[]
    goals: MemoryListItem[]
    keyMetrics: MemoryListItem[]
  }
  personal: {
    overview: string
    voiceKeywords: MemoryListItem[]
    voiceExamples: MemoryListItem[]
    contentPillars: MemoryListItem[]
    contentAudience: string
    effectivePatterns: MemoryListItem[]
    pitfalls: MemoryListItem[]
    rules: MemoryListItem[]
  }
  account: {
    accounts: MemoryAccount[]
    selectedId: string
    overview: string
    voiceKeywords: MemoryListItem[]
  }
}

const li = (...texts: string[]): MemoryListItem[] => texts.map((t, i) => ({ id: `li_${i}_${t.slice(0, 6)}`, text: t }))

export const EMPTY_MEMORY_DOC: MemoryDoc = {
  workspace: { brandOverview: "", services: [], goals: [], keyMetrics: [] },
  personal: { overview: "", voiceKeywords: [], voiceExamples: [], contentPillars: [], contentAudience: "", effectivePatterns: [], pitfalls: [], rules: [] },
  account: { accounts: [], selectedId: "", overview: "", voiceKeywords: [] },
}

export const DEMO_MEMORY_DOC: MemoryDoc = {
  workspace: {
    brandOverview:
      "Aurora Skincare is a clean-science skincare brand for people tired of being talked down to. We translate dermatology into plain, myth-busting guidance and ship products that respect the skin barrier — proving honest education outsells hype.",
    services: [
      { id: "s1", name: "Barrier Repair Serum", description: "A daily ceramide + niacinamide serum that rebuilds a compromised moisture barrier." },
      { id: "s2", name: "Gentle Retinol 0.2%", description: "A beginner-friendly encapsulated retinol that delivers results without wrecking the skin." },
    ],
    goals: li(
      "Hit ₹50L in monthly recurring revenue within 6 months.",
      "Build a loyal community of 100k skincare-curious followers.",
      "Land one dermatologist-creator partnership each quarter.",
    ),
    keyMetrics: li("Save rate on educational carousels", "Repeat purchase rate within 60 days", "Cost per acquired email subscriber"),
  },
  personal: {
    overview:
      "The founder is a chemist-turned-builder who speaks founder-to-founder. Confident and myth-busting, never preachy — happy to show the mistakes as much as the wins.",
    voiceKeywords: li("Confident", "Myth-busting", "Warm", "Plain-spoken", "Evidence-led", "Founder-POV", "Anti-hype"),
    voiceExamples: li(
      "Everyone gets retinol wrong. It's not about strength — it's about a consistency your barrier can survive.",
      "We grew faster the month we posted less. Fewer, truer posts beat a feed full of noise.",
      "Building in public means showing the flops too. Here's a launch that under-delivered, and what we changed.",
    ),
    contentPillars: li("Myth-busting skincare science", "Founder build-in-public", "Ingredient deep-dives", "Routine teardowns", "Behind-the-brand"),
    contentAudience:
      "Skincare-curious women 25–40 who want honest, science-led guidance without the gatekeeping or the hype.",
    effectivePatterns: li(
      "Open with a bold, contrarian one-liner in the first line.",
      "Use numbered myth-busters — they save and share best.",
      "Show the founder's face; real beats polished stock.",
    ),
    pitfalls: li("Claiming medical or dermatology results.", "Over-polished stock visuals that feel like an ad.", "Generic tips listicles with no point of view."),
    rules: li(
      "Never make medical claims — keep guidance educational.",
      "Preserve product names exactly: Barrier Repair Serum, Gentle Retinol 0.2%.",
      "Always lead with the 'why', not the ingredient list.",
    ),
  },
  account: {
    accounts: [
      { id: "x", handle: "@aurora.skin", platform: "X" },
      { id: "ig", handle: "@aurora.skin", platform: "Instagram" },
    ],
    selectedId: "x",
    overview:
      "On X, Aurora Skincare is the myth-busting friend who explains skin science in plain English and isn't afraid to call out industry hype.",
    voiceKeywords: li("Direct", "No-nonsense", "Helpful", "Witty", "Evidence-led"),
  },
}

// ── Connections page ──
export const DEMO_CONNECTIONS = [
  { platform: "instagram", handle: "@aurora.skin", env_key: "IG", has_token: true, connected: true, account: "Aurora Skincare" },
  { platform: "linkedin", handle: "Aurora Skincare", env_key: "LI", has_token: true, connected: true, account: "Aurora Skincare" },
  { platform: "youtube", handle: "Aurora Skincare", env_key: "YT", has_token: true, connected: false, account: "Token needs refresh" },
  { platform: "twitter", handle: "@aurora_skin", env_key: "TW", has_token: false, connected: false, account: "" },
  { platform: "tiktok", handle: "", env_key: "TT", has_token: false, connected: false, account: "" },
]

// ── Settings page: publish policy + cost cap ──
export const DEMO_PUBLISH_POLICY = {
  levels: ["manual", "assisted"] as ("manual" | "assisted")[],
  default_level: "manual" as const,
  locked_manual: ["twitter"],
  settings: { instagram: "manual", linkedin: "manual" } as Record<string, "manual" | "assisted">,
}

export const DEMO_COST_CAP = {
  enabled: true,
  spent_today_usd: 2.4,
  daily_cap_usd: 15,
  remaining_usd: 12.6,
  date: new Date(now).toISOString().slice(0, 10),
  is_override: false,
}

// ── Week view (operating rhythm) ──
export const DEMO_WEEK = {
  ran: [
    { agent_slug: "trend-researcher", status: "success", started_at: iso(6 * 3600_000), completed_at: iso(5 * 3600_000) },
    { agent_slug: "script-writer", status: "running", started_at: iso(1 * 3600_000), completed_at: null },
    { agent_slug: "carousel-designer", status: "success", started_at: iso(DAY + 2 * 3600_000), completed_at: iso(DAY + 3600_000) },
    { agent_slug: "content-planner", status: "success", started_at: iso(2 * DAY), completed_at: iso(2 * DAY - 3600_000) },
    { agent_slug: "data-analyst", status: "success", started_at: iso(3 * DAY), completed_at: iso(3 * DAY - 3600_000) },
    { agent_slug: "weekly-review-composer", status: "success", started_at: iso(5 * DAY), completed_at: iso(5 * DAY - 1800_000) },
  ],
  waiting: { count: 3, by_agent: { "carousel-designer": 1, "script-writer": 2 } },
  next: [
    { pipeline: "daily", day_of_week: null, hour: 7, minute: 30 },
    { pipeline: "weekly", day_of_week: "fri", hour: 18, minute: 0 },
    { pipeline: "monthly", day_of_week: "mon", hour: 10, minute: 0 },
  ],
}

/** Seed the stores so demo pages render alive. Idempotent. */
export function seedDemo() {
  const bs = useBrandStore.getState()
  bs.setBrands([DEMO_BRAND])
  if (bs.activeBrand.slug !== DEMO_BRAND.slug) bs.setActiveBrand(DEMO_BRAND)
  useAppStore.setState({ activity: DEMO_ACTIVITY })
}

/** Full demo entry from the Sign In page — flips the flag, fakes the session, seeds. */
export function enterDemo() {
  localStorage.setItem("gc_demo", "1")
  useAuthStore.setState({
    user: { id: "demo", email: DEMO_EMAIL } as never,
    loading: false,
    isSuperAdmin: false,
    viewMode: "client",
  })
  seedDemo()
}
