/**
 * TanStack Query hooks for the GRID CONTROL Flask API.
 * All hooks are brand-scoped via the activeBrand from brandStore.
 */
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"
import { useBrandStore } from "@/store/brandStore"
import { isDemo, DEMO_PENDING, DEMO_AGENT_STATUS, DEMO_DIGEST, DEMO_PERF_HISTORY, DEMO_PUBLISHED, DEMO_WEEK, DEMO_PUBLISH_POLICY, DEMO_COST_CAP } from "@/lib/demo"

// ── Types ─────────────────────────────────────────────────────────────────────

export interface AgentStatus {
  slug: string
  name: string
  number?: number
  role?: string
  status: "idle" | "running" | "error" | "success" | "queued" | "blocked"
  last_run?: string | null
}

export interface PendingOutput {
  filename: string
  agent_slug: string       // mapped from API.agentName
  agent_name: string       // human-readable
  created_at: string       // mapped from API.timestamp
  filepath?: string
  contentType?: string
  preview?: string
  // Enriched fields from backend _extract_output_meta
  title?: string | null
  platform?: string | null
  caption?: string | null
  body_text?: string | null
  slide_images?: string[]
  hashtags?: string[]
  scheduled_for?: string | null
  raw?: any
}

export interface BrandProfile {
  brand_name?: string
  handle?: string
  voice_profile?: string
  audience?: string
  do_not_post?: string[]
  working_hours?: { start: string; end: string; tz?: string }
  [k: string]: any
}

export interface AgentDef {
  slug: string
  name: string
  number: number
  role: string
}

// ── Helpers ───────────────────────────────────────────────────────────────────

async function getJson<T>(path: string): Promise<T> {
  const r = await apiFetch(path)
  if (!r.ok) throw new Error(`${r.status} ${r.statusText} on ${path}`)
  return (await r.json()) as T
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const r = await apiFetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
  if (!r.ok) throw new Error(`${r.status} ${r.statusText} on ${path}`)
  return (await r.json()) as T
}

// ── Brand list ────────────────────────────────────────────────────────────────

export function useBrands() {
  return useQuery({
    queryKey: ["brands"],
    queryFn: () => getJson<{ brands: { slug: string; name: string; handle?: string }[] }>("/api/brands"),
    staleTime: 60_000,
  })
}

// ── Agents ────────────────────────────────────────────────────────────────────

export function useAgents() {
  return useQuery({
    queryKey: ["agents"],
    queryFn: () => getJson<{ agents: AgentDef[] }>("/api/agents"),
    staleTime: 5 * 60_000,
  })
}

export function useAgentStatus() {
  const { activeBrand } = useBrandStore()
  return useQuery({
    queryKey: ["agents", "status", activeBrand.slug],
    enabled: !!activeBrand.slug,
    queryFn: async () => {
      if (isDemo()) return { agents: DEMO_AGENT_STATUS }
      // Endpoint returns { success, data: [...] } with camelCase `lastRun` and
      // session status "running"/"done"/"idle". Normalize to AgentStatus shape.
      const resp = await getJson<{ success: boolean; data: Array<Record<string, unknown>> }>(
        `/api/agents/status?brand_slug=${encodeURIComponent(activeBrand.slug)}`,
      )
      const agents: AgentStatus[] = (resp.data ?? []).map((a) => {
        const raw = (a.status as string) ?? "idle"
        const status = (raw === "done" ? "success" : raw) as AgentStatus["status"]
        return {
          slug: (a.slug as string) ?? "",
          name: (a.name as string) ?? "",
          status,
          last_run: (a.lastRun as string) ?? (a.last_run as string) ?? null,
        }
      })
      return { agents }
    },
    refetchInterval: 10_000,
  })
}

export function useRunAgent() {
  const qc = useQueryClient()
  const { activeBrand } = useBrandStore()
  return useMutation({
    mutationFn: (agentSlug: string) =>
      postJson("/api/agents/run", { agent_slug: agentSlug, brand_slug: activeBrand.slug }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["agents", "status"] })
    },
  })
}

// ── Live agent roster (merge canonical list + live status) ───────────────────

import { AGENTS, type Agent } from "@/data/agents"

export function useLiveAgents(): Agent[] {
  const { data } = useAgentStatus()
  if (!data?.agents) return AGENTS

  // Match by name — present on both the static roster and the endpoint payload
  // (backend items don't reliably carry a slug).
  const liveByName = new Map(data.agents.map((a) => [a.name, a]))
  return AGENTS.map((a) => {
    const live = liveByName.get(a.name)
    if (!live) return a
    return {
      ...a,
      status: (live.status ?? a.status) as Agent["status"],
      lastRun: live.last_run ? new Date(live.last_run) : a.lastRun,
    }
  })
}

// ── Pending approvals ─────────────────────────────────────────────────────────

export function usePendingOutputs() {
  const { activeBrand } = useBrandStore()
  return useQuery({
    queryKey: ["outputs", "pending", activeBrand.slug],
    queryFn: async () => {
      if (isDemo()) return { outputs: DEMO_PENDING }
      // API returns { success, data: [{agentName, filename, timestamp, preview, ...}] }
      // Adapt to our PendingOutput shape so consumers don't need to know.
      const raw = await getJson<{ success: boolean; data: any[] }>(
        `/api/outputs/pending?brand_slug=${encodeURIComponent(activeBrand.slug)}`,
      )
      const items: PendingOutput[] = (raw.data || [])
        .filter((it) => it.filename && !it.filename.startsWith(".") && !it.filename.endsWith(".DS_Store"))
        .map((it) => ({
          filename: it.filename,
          agent_slug: it.agentName || "",
          agent_name: (it.agentName || "").replace(/-/g, " ").replace(/\b\w/g, (c: string) => c.toUpperCase()),
          created_at: it.timestamp || "",
          filepath: it.filepath,
          contentType: it.contentType,
          preview: it.preview,
          title: it.title ?? null,
          platform: it.platform ?? null,
          caption: it.caption ?? null,
          body_text: it.body_text ?? null,
          slide_images: it.slide_images ?? [],
          hashtags: it.hashtags ?? [],
          scheduled_for: it.scheduled_for ?? null,
        }))
        // Sort newest first
        .sort((a, b) => (b.created_at || "").localeCompare(a.created_at || ""))
      return { outputs: items }
    },
    enabled: !!activeBrand.slug,
    refetchInterval: 15_000,
  })
}

export function useApproveOutput() {
  const qc = useQueryClient()
  const { activeBrand } = useBrandStore()
  return useMutation({
    mutationFn: (filename: string) =>
      isDemo()
        ? Promise.resolve({ success: true })
        : postJson("/api/outputs/approve", { brand_slug: activeBrand.slug, filename }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["outputs", "pending"] }),
  })
}

export function useRejectOutput() {
  const qc = useQueryClient()
  const { activeBrand } = useBrandStore()
  return useMutation({
    mutationFn: ({ filename, reason }: { filename: string; reason?: string }) =>
      isDemo()
        ? Promise.resolve({ success: true })
        : postJson("/api/outputs/reject", { brand_slug: activeBrand.slug, filename, reason: reason || "" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["outputs", "pending"] }),
  })
}

// ── Week view (operating rhythm · Fable 5 UX pass) ────────────────────────────

export interface WeekRun {
  agent_slug: string
  status: string
  started_at: string
  completed_at?: string | null
}

export interface WeekData {
  ran: WeekRun[]
  waiting: { count: number; by_agent: Record<string, number> }
  next: { pipeline: string; day_of_week?: string | null; hour?: number | null; minute?: number | null }[]
}

export function useWeek() {
  const { activeBrand } = useBrandStore()
  return useQuery({
    queryKey: ["week", activeBrand.slug],
    queryFn: async () => {
      if (isDemo()) return DEMO_WEEK
      const raw = await getJson<{ success: boolean; data: WeekData }>(
        `/api/week?brand_slug=${encodeURIComponent(activeBrand.slug)}`,
      )
      return raw.data
    },
    enabled: !!activeBrand.slug,
    refetchInterval: 60_000,
  })
}

// ── Trust dial (GRIDLOCK-PROGRAM-01JUL Stage 5) ────────────────────────────────

export type TrustLevel = "consult" | "automate" | "direct"

export interface TrustDialData {
  levels: TrustLevel[]
  default_level: TrustLevel
  settings: Record<string, TrustLevel>   // agent_slug -> level; missing key = default
}

export function useTrustDial() {
  const { activeBrand } = useBrandStore()
  return useQuery({
    queryKey: ["trust-dial", activeBrand.slug],
    queryFn: () => getJson<{ success: boolean; data: TrustDialData }>(
      `/api/brands/${encodeURIComponent(activeBrand.slug)}/trust-dial`,
    ).then((r) => r.data),
    enabled: !!activeBrand.slug,
    staleTime: 30_000,
  })
}

export function useSetTrustDial() {
  const qc = useQueryClient()
  const { activeBrand } = useBrandStore()
  return useMutation({
    mutationFn: (vars: { agent_slug: string; level: TrustLevel }) =>
      postJson(`/api/brands/${encodeURIComponent(activeBrand.slug)}/trust-dial`, vars),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["trust-dial", activeBrand.slug] }),
  })
}

// ── Publish policy — per-platform manual/assisted, owner-facing ────────────────

export type PublishLevel = "manual" | "assisted"

export interface PublishPolicyData {
  levels: PublishLevel[]
  default_level: PublishLevel
  locked_manual: string[]                    // platforms that can't be changed (e.g. "twitter")
  settings: Record<string, PublishLevel>     // platform -> level; missing key = default (manual)
}

export function usePublishPolicy() {
  const { activeBrand } = useBrandStore()
  return useQuery({
    queryKey: ["publish-policy", activeBrand.slug],
    queryFn: () =>
      isDemo()
        ? Promise.resolve(DEMO_PUBLISH_POLICY as PublishPolicyData)
        : getJson<{ success: boolean; data: PublishPolicyData }>(
            `/api/brands/${encodeURIComponent(activeBrand.slug)}/publish-policy`,
          ).then((r) => r.data),
    enabled: !!activeBrand.slug,
    staleTime: 30_000,
  })
}

export function useSetPublishPolicy() {
  const qc = useQueryClient()
  const { activeBrand } = useBrandStore()
  return useMutation({
    mutationFn: (vars: { platform: string; level: PublishLevel }) =>
      isDemo()
        ? Promise.resolve({ success: true })
        : postJson(`/api/brands/${encodeURIComponent(activeBrand.slug)}/publish-policy`, vars),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["publish-policy", activeBrand.slug] }),
  })
}

// ── Cost cap — per-brand daily spend cap, owner-facing ──────────────────────────

export interface CostCapData {
  enabled: boolean
  spent_today_usd: number
  daily_cap_usd: number
  remaining_usd: number
  date: string
  is_override: boolean   // false = showing the global default, not a brand-specific cap
}

export function useCostCap() {
  const { activeBrand } = useBrandStore()
  return useQuery({
    queryKey: ["cost-cap", activeBrand.slug],
    queryFn: () =>
      isDemo()
        ? Promise.resolve(DEMO_COST_CAP as CostCapData)
        : getJson<{ success: boolean; data: CostCapData }>(
            `/api/brands/${encodeURIComponent(activeBrand.slug)}/cost-cap`,
          ).then((r) => r.data),
    enabled: !!activeBrand.slug,
    staleTime: 15_000,
  })
}

export function useSetCostCap() {
  const qc = useQueryClient()
  const { activeBrand } = useBrandStore()
  return useMutation({
    mutationFn: (vars: { daily_usd_cap: number }) =>
      isDemo()
        ? Promise.resolve({ success: true })
        : postJson(`/api/brands/${encodeURIComponent(activeBrand.slug)}/cost-cap`, vars),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["cost-cap", activeBrand.slug] }),
  })
}

// ── Brand dashboard (profile + trends + session) ──────────────────────────────

export function useBrandDashboard() {
  const { activeBrand } = useBrandStore()
  return useQuery({
    queryKey: ["brand", "dashboard", activeBrand.slug],
    queryFn: () =>
      getJson<{ profile: BrandProfile; session_state: any; trends_live: any }>(
        `/api/brand/dashboard?brand_slug=${encodeURIComponent(activeBrand.slug)}`,
      ),
    enabled: !!activeBrand.slug,
    staleTime: 60_000,
  })
}

// ── Performance history ───────────────────────────────────────────────────────

export function usePerformanceHistory() {
  const { activeBrand } = useBrandStore()
  return useQuery({
    queryKey: ["performance", "history", activeBrand.slug],
    queryFn: async () => {
      if (isDemo()) return { history: DEMO_PERF_HISTORY }
      return getJson<{ history: any }>(
        `/api/performance/history?brand_slug=${encodeURIComponent(activeBrand.slug)}`,
      )
    },
    enabled: !!activeBrand.slug,
    staleTime: 30_000,
  })
}

// ── Published posts (approved + scheduled + published with engagement) ──────

export interface PublishedPost {
  id: string
  post_id: string
  platform: string | null
  title: string | null
  caption: string | null
  body_text?: string | null
  slide_images: string[]
  hashtags: string[]
  scheduled_for: string | null
  approved_at: string
  posted_at: string | null
  status: "scheduled" | "published"
  engagement: {
    likes: number
    comments: number
    shares: number
    impressions: number
    saves: number
  } | null
  agent_slug: string
  filepath: string
}

export function usePublishedPosts() {
  const { activeBrand } = useBrandStore()
  return useQuery({
    queryKey: ["published", activeBrand.slug],
    queryFn: async () => {
      if (isDemo()) return { success: true, data: DEMO_PUBLISHED }
      return getJson<{ success: boolean; data: PublishedPost[] }>(
        `/api/published?brand_slug=${encodeURIComponent(activeBrand.slug)}`,
      )
    },
    enabled: !!activeBrand.slug,
    refetchInterval: 30_000,
  })
}

// ── Connection status ─────────────────────────────────────────────────────────

export function useConnections() {
  return useQuery({
    queryKey: ["connections"],
    queryFn: () => getJson<{ data: Record<string, { connected: boolean; account: string }> }>("/api/connections/check"),
    staleTime: 60_000,
  })
}

// ── Daily Intelligence Digest (cockpit hero) ──────────────────────────────────

export interface DigestTrend {
  title: string
  relevance?: number | null
  classification?: string
}

export interface DigestData {
  brand_slug: string
  verdict: "PIVOT" | "TRACK" | "STAY" | null
  verdict_reason: string
  verdict_at: string
  sentinel: { signals: { label: string; day_count: number; reason: string }[]; tracked_count: number }
  trends: DigestTrend[]
  contradictions: {
    counts: Record<string, number>
    findings: any[]
    blocking: boolean
  }
  last_pipeline_run: string
  has_data: boolean
}

export function useDigest() {
  const { activeBrand } = useBrandStore()
  return useQuery({
    queryKey: ["digest", activeBrand.slug],
    queryFn: async () => {
      if (isDemo()) return DEMO_DIGEST
      const r = await getJson<{ success: boolean; data: DigestData }>(
        `/api/digest?brand_slug=${encodeURIComponent(activeBrand.slug)}`,
      )
      return r.data
    },
    enabled: !!activeBrand.slug,
    staleTime: 30_000,
  })
}

// ── Operator mode (super-admin only — unlocks Brain edit/run, never relaxes approvals) ──

export function useOperatorMode(enabled = true) {
  return useQuery({
    queryKey: ["operator-mode"],
    queryFn: () => getJson<{ success: boolean; data: { on: boolean } }>("/api/operator-mode"),
    // 403 for non-operators is expected — don't spam retries. Gate with `enabled`
    // (pass isSuperAdmin) so non-operators never fire the request at all.
    enabled,
    retry: false,
    staleTime: 60_000,
  })
}

export function useSetOperatorMode() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (on: boolean) =>
      postJson<{ success: boolean; data: { on: boolean } }>("/api/operator-mode", { on }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["operator-mode"] }),
  })
}

// ── Instagram publishing (the "agents post it" step) ────────────────────────────

export interface PublishResult {
  mode: "published" | "prepared" | "unbuilt" | "needs_video"
  platform?: string
  media_id?: string
  permalink?: string
  post_id?: string
  reason?: string
  slide_urls?: string[]
  caption?: string
  note?: string
  error?: string
}

export function usePublishCheck() {
  return useQuery({
    queryKey: ["publish-check"],
    queryFn: () =>
      getJson<{ success: boolean; data: { live: boolean; username?: string; account_type?: string; reason?: string } }>(
        "/api/publish/check",
      ).then((r) => r.data),
    staleTime: 60_000,
    retry: false,
  })
}

export function usePublishInstagram() {
  const qc = useQueryClient()
  const { activeBrand } = useBrandStore()
  return useMutation({
    mutationFn: (filename: string) =>
      postJson<{ success: boolean; data?: PublishResult; error?: string }>("/api/publish/instagram", {
        brand_slug: activeBrand.slug,
        filename,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["published"] })
    },
  })
}

/**
 * Generic publish — routes through the platform registry on the backend.
 * instagram publishes for real; linkedin/youtube/twitter return mode "unbuilt"
 * (honest "publisher not built yet" — nothing is sent).
 */
export function usePublish() {
  const qc = useQueryClient()
  const { activeBrand } = useBrandStore()
  return useMutation({
    mutationFn: ({ platform, filename }: { platform: string; filename: string }): Promise<{ success: boolean; data?: PublishResult; error?: string }> =>
      isDemo()
        ? Promise.resolve({
            success: true,
            data: { mode: "prepared", platform, reason: "Demo mode — nothing actually publishes." },
          })
        : postJson<{ success: boolean; data?: PublishResult; error?: string }>("/api/publish", {
            brand_slug: activeBrand.slug,
            platform,
            filename,
          }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["published"] })
    },
  })
}

// ── Generate a carousel (synchronous ~30-60s → lands in pending_approval) ────────

export function useGenerateCarousel() {
  const qc = useQueryClient()
  const { activeBrand } = useBrandStore()
  return useMutation({
    mutationFn: (opts: { topic?: string; post_id?: string; slides?: number; platform?: string }) =>
      postJson<{ success: boolean; data?: any; error?: string }>("/api/carousel/generate", {
        brand_slug: activeBrand.slug,
        topic: opts.topic,
        post_id: opts.post_id,
        slides: opts.slides ?? 7,
        platform: opts.platform ?? "instagram",
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["outputs", "pending"] })
      qc.invalidateQueries({ queryKey: ["agents", "status"] })
    },
  })
}

// ── Run the daily pipeline (Trend Researcher → Sentinel → Data Analyst) ──────────

export function useRunDailyPipeline() {
  const qc = useQueryClient()
  const { activeBrand } = useBrandStore()
  return useMutation({
    mutationFn: () =>
      postJson<{ success: boolean; pipeline_run_id?: string }>("/api/pipeline/daily-run", {
        brand_slug: activeBrand.slug,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["agents", "status"] })
      qc.invalidateQueries({ queryKey: ["digest"] })
    },
  })
}

// ── Creative Library (gap #3 — unified, tagged, versioned creative assets) ───────

export interface CreativeAsset {
  id: string
  brand_slug: string
  filename: string
  kind: "image" | "video" | "audio"
  ext: string
  source_agent: string
  approval_state: "pending" | "approved" | "generated"
  post_id: string | null
  group_key: string
  size_bytes: number
  created: string
  media_url: string
  path: string
  tags: string[]
}

export interface CreativeFacets {
  total: number
  kind: Record<string, number>
  source_agent: Record<string, number>
  approval_state: Record<string, number>
  tags: Record<string, number>
}

export interface CreativeFilters {
  kind?: string
  source_agent?: string
  approval_state?: string
  tag?: string
  q?: string
}

export function useCreativeLibrary(filters: CreativeFilters = {}) {
  const { activeBrand } = useBrandStore()
  return useQuery({
    queryKey: ["creative-library", activeBrand.slug, filters],
    enabled: !!activeBrand.slug,
    queryFn: () => {
      const p = new URLSearchParams({ brand_slug: activeBrand.slug })
      for (const [k, v] of Object.entries(filters)) if (v) p.set(k, v)
      return getJson<{ success: boolean; data: { assets: CreativeAsset[]; facets: CreativeFacets } }>(
        `/api/creative-library?${p.toString()}`,
      ).then((r) => r.data)
    },
    staleTime: 15_000,
  })
}

export function useSetAssetTags() {
  const qc = useQueryClient()
  const { activeBrand } = useBrandStore()
  return useMutation({
    mutationFn: (vars: { asset_id: string; tags: string[] }) =>
      postJson<{ success: boolean; data: CreativeAsset }>("/api/creative-library/tags", {
        brand_slug: activeBrand.slug,
        ...vars,
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["creative-library", activeBrand.slug] }),
  })
}

// ── Latest analysis (the Data Analyst's conclusion, not just raw metrics) ────────

export interface AnalysisAction {
  action: string
  reason?: string
  expected_outcome?: string
  priority?: number
}

export interface LatestAnalysis {
  exists: boolean
  report_week?: string
  generated_at?: string
  lead_insight?: string
  confidence?: "high" | "medium" | "low" | ""
  next_actions?: AnalysisAction[]
  anomalies?: string[]
  repurposing?: string[]
  data_quality_note?: string
}

export function useLatestAnalysis() {
  const { activeBrand } = useBrandStore()
  return useQuery({
    queryKey: ["analysis", "latest", activeBrand.slug],
    enabled: !!activeBrand.slug,
    queryFn: () =>
      getJson<{ success: boolean; data: LatestAnalysis }>(
        `/api/analysis/latest?brand_slug=${encodeURIComponent(activeBrand.slug)}`,
      ).then((r) => r.data),
    staleTime: 30_000,
  })
}

// ── Social listening (gap #4 — what the internet is saying about the brand) ──────

export interface Mention {
  title: string
  link: string
  snippet: string
  source: string
  source_type: "social" | "forum" | "review" | "news" | "web" | "own"
  sentiment: "positive" | "neutral" | "negative"
}

export interface SocialListening {
  status: "ok" | "none" | "blocked" | "no_provider" | "no_brand_identity" | "not_run"
  note?: string
  collected_at?: string
  total_mentions?: number
  by_sentiment?: { positive: number; neutral: number; negative: number }
  by_source_type?: Record<string, number>
  mentions?: Mention[]
}

export function useListening() {
  const { activeBrand } = useBrandStore()
  return useQuery({
    queryKey: ["listening", activeBrand.slug],
    enabled: !!activeBrand.slug,
    queryFn: () =>
      getJson<{ success: boolean; data: SocialListening }>(
        `/api/listening?brand_slug=${encodeURIComponent(activeBrand.slug)}`,
      ).then((r) => r.data),
    staleTime: 60_000,
  })
}

export function useRunListening() {
  const qc = useQueryClient()
  const { activeBrand } = useBrandStore()
  return useMutation({
    mutationFn: () =>
      postJson<{ success: boolean; data: SocialListening }>("/api/listening/run", {
        brand_slug: activeBrand.slug,
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["listening", activeBrand.slug] }),
  })
}

// ── Reputation engine (gap #5) ────────────────────────────────────────────────

export interface ReviewPlatform {
  platform: string
  domain: string
  url: string
  rating: number | null
  reviews: number | null
  sentiment: "positive" | "neutral" | "negative"
  title: string
  snippet: string
}

export interface Reputation {
  status: "ok" | "none" | "blocked" | "no_provider" | "no_brand_identity" | "not_run"
  note?: string
  collected_at?: string
  overall_rating?: number | null
  platforms_found?: number
  total_reviews?: number
  platforms?: ReviewPlatform[]
  needs_response?: ReviewPlatform[]
}

export function useReputation() {
  const { activeBrand } = useBrandStore()
  return useQuery({
    queryKey: ["reputation", activeBrand.slug],
    enabled: !!activeBrand.slug,
    queryFn: () =>
      getJson<{ success: boolean; data: Reputation }>(
        `/api/reputation?brand_slug=${encodeURIComponent(activeBrand.slug)}`,
      ).then((r) => r.data),
    staleTime: 60_000,
  })
}

export function useRunReputation() {
  const qc = useQueryClient()
  const { activeBrand } = useBrandStore()
  return useMutation({
    mutationFn: () =>
      postJson<{ success: boolean; data: Reputation }>("/api/reputation/run", {
        brand_slug: activeBrand.slug,
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["reputation", activeBrand.slug] }),
  })
}

// ── White-label branding (gap #4) ─────────────────────────────────────────────

export interface WhiteLabel {
  brand_name?: string
  logo_url?: string
  accent?: string
  support_email?: string
  custom_domain?: string
}

export function useWhiteLabel() {
  const { activeBrand } = useBrandStore()
  return useQuery({
    queryKey: ["white-label", activeBrand.slug],
    enabled: !!activeBrand.slug,
    queryFn: () =>
      getJson<{ success: boolean; data: WhiteLabel }>(
        `/api/brands/${encodeURIComponent(activeBrand.slug)}/white-label`,
      ).then((r) => r.data),
    staleTime: 30_000,
  })
}

export function useSetWhiteLabel() {
  const qc = useQueryClient()
  const { activeBrand } = useBrandStore()
  return useMutation({
    mutationFn: (patch: WhiteLabel) =>
      postJson<{ success: boolean; data: WhiteLabel }>(
        `/api/brands/${encodeURIComponent(activeBrand.slug)}/white-label`,
        patch,
      ),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["white-label", activeBrand.slug] }),
  })
}
