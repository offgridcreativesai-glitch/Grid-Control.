// GRID CONTROL — API response types (FE contract)
// Canonical reference. Copy into the front-end project (e.g. src/types/api.ts).
// Mirrors docs/API_REFERENCE.md. Keep in sync with the backend handlers.

/** Standard envelope used by most /api/* endpoints. */
export interface ApiEnvelope<T> {
  success: boolean;
  data?: T;
  error?: string;
}

// ── Auth & Brands ────────────────────────────────────────────────────────────
export interface BrandRef {
  id: string;
  slug: string;
  name: string;
  role?: "admin" | "member" | string;
  profile?: Record<string, unknown>;
}

/** GET /api/auth/me — BARE shape (no envelope). */
export interface AuthMe {
  user: Record<string, unknown> | null;
  brands: BrandRef[];
}

/** GET /api/brands — BARE shape (no envelope). */
export interface BrandsList {
  brands: Pick<BrandRef, "slug" | "name">[];
}

// ── Command Center ───────────────────────────────────────────────────────────
export interface ActivityEvent {
  agent: string;
  status: "done" | "error" | "running" | string;
  icon: string;
  summary: string;
  timestamp: string; // ISO
}

/** GET /api/brand/summary → data */
export interface BrandSummary {
  brand_name: string;
  product: string;
  phase: string;
  platforms: string[];
  bottlenecks: string[];
  audience: string[];
  price_india: string;
  price_international: string;
  railway_url: string;
  instagram_handle: string;
  competitor_handles: string[];
  brand_face: string;
  tone_specifics: string;
  content_goal_90d: string;
  what_to_never_say: string;
  weekly_post_target: string;
  posts_scripted: number;
  agents_run: number;
  agents_approved: number;
  notion_pending: number;
  notion_approved: number;
  notion_rejected: number;
  completed_agents: string[];
  activity_feed: ActivityEvent[];
  keys: { anthropic: boolean; elevenlabs: boolean; notion: boolean; fal: boolean };
}

export interface NeedsYouItem {
  agent: string;
  filename: string;
  path: string;
  created_at: string; // ISO
}

/** GET /api/brands/:slug/needs-you → data */
export interface NeedsYouQueue {
  count: number;
  items: NeedsYouItem[];
  email_configured: boolean;
  notification_email: string; // masked, e.g. g***@gmail.com
}

// ── The Team / Agents ────────────────────────────────────────────────────────
export interface AgentEnriched {
  id: number;
  name: string;
  slug: string;
  role?: string;
  model?: string;
  [k: string]: unknown; // additional enrichment metadata
}

/** GET /api/agents/status → data[] */
export interface AgentStatus extends AgentEnriched {
  status: "idle" | "running" | "done" | "error" | string;
  lastRun: string | null;
  lastOutput: string | null;
}

// ── Insights / Cost ──────────────────────────────────────────────────────────
/** GET /api/brands/:slug/costs → data (shape from db.get_brand_monthly_costs) */
export interface CostBreakdown {
  total?: number;
  by_source?: Record<string, number>;
  by_agent?: Record<string, number>;
  [k: string]: unknown;
}

// ── Memory & Brain ───────────────────────────────────────────────────────────
export interface NarrativeEntry {
  agent: string;
  type: string;
  summary: string;
  refs?: Record<string, unknown>;
  created_at: string; // ISO
}

/** GET /api/brands/:slug/narrative → data */
export interface NarrativeResponse {
  entries: NarrativeEntry[];
  count: number;
}

// ── Connections ──────────────────────────────────────────────────────────────
export interface ConnectionStatus {
  connected: boolean;
  account: string;
}
/** GET /api/brands/:slug/connections → data (keyed by platform). Never includes tokens. */
export type ConnectionsResponse = Record<
  "instagram" | "linkedin" | "youtube" | "twitter" | string,
  ConnectionStatus
>;

// ── Concierge ────────────────────────────────────────────────────────────────
/** POST /api/concierge → data */
export interface ConciergeResponse {
  tier: "trivial" | "substantive";
  intent: string | null;
  llm_used: boolean;
  answer: string;
  items?: NeedsYouItem[];
  data_endpoint?: string;
  action_required?: boolean;
  endpoint?: string;
  forward_to?: string;
}
