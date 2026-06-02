/**
 * TanStack Query hooks for the GRID CONTROL Flask API.
 * All hooks are brand-scoped via the activeBrand from brandStore.
 */
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"
import { useBrandStore } from "@/store/brandStore"

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
  return useQuery({
    queryKey: ["agents", "status"],
    queryFn: () => getJson<{ agents: AgentStatus[] }>("/api/agents/status"),
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

  const liveBySlug = new Map(data.agents.map((a) => [a.slug, a]))
  return AGENTS.map((a) => {
    const live = liveBySlug.get(a.slug)
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
      postJson("/api/outputs/approve", { brand_slug: activeBrand.slug, filename }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["outputs", "pending"] }),
  })
}

export function useRejectOutput() {
  const qc = useQueryClient()
  const { activeBrand } = useBrandStore()
  return useMutation({
    mutationFn: (filename: string) =>
      postJson("/api/outputs/reject", { brand_slug: activeBrand.slug, filename }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["outputs", "pending"] }),
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
    queryFn: () =>
      getJson<{ history: any }>(
        `/api/performance/history?brand_slug=${encodeURIComponent(activeBrand.slug)}`,
      ),
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
    queryFn: () =>
      getJson<{ success: boolean; data: PublishedPost[] }>(
        `/api/published?brand_slug=${encodeURIComponent(activeBrand.slug)}`,
      ),
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
    queryFn: () =>
      getJson<{ success: boolean; data: DigestData }>(
        `/api/digest?brand_slug=${encodeURIComponent(activeBrand.slug)}`,
      ).then((r) => r.data),
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
    mutationFn: ({ platform, filename }: { platform: string; filename: string }) =>
      postJson<{ success: boolean; data?: PublishResult; error?: string }>("/api/publish", {
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
