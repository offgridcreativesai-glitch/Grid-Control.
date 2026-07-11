/**
 * Intelligence — how the brand is performing + what we're doing about it (route "/insights").
 * Real data only (performance history + daily digest). Client-safe: no models / slugs / tokens.
 */
import { useState, useMemo, type ReactNode } from "react"
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts"
import { cn, formatNumber, formatDelta, formatTimeAgo } from "@/lib/utils"
import type { Platform } from "@/store/appStore"
import { StatusDot } from "@/components/ui/status-dot"
import { PlatformIcon } from "@/components/ui/platform-icon"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { usePerformanceHistory, useDigest, useLatestAnalysis, useListening, useRunListening } from "@/hooks/useGridApi"
import { useBrandStore } from "@/store/brandStore"

const PLATFORMS: (Platform | "all")[] = ["all", "x", "instagram", "linkedin", "tiktok", "youtube"]

interface PerfPost {
  id?: string
  post_id?: string
  platform?: string
  caption?: string
  impressions?: number
  engagements?: number
  saves?: number
  posted_at?: string
}

function inferPlat(p?: string): Platform {
  if (!p) return "x"
  const v = p.toLowerCase()
  if (v.includes("instagram") || v === "ig") return "instagram"
  if (v.includes("linkedin") || v === "li") return "linkedin"
  if (v.includes("tiktok") || v === "tt") return "tiktok"
  if (v.includes("youtube") || v === "yt") return "youtube"
  return "x"
}

// Internal verdict → plain-English headline (no jargon leaks to the client).
const VERDICT: Record<"PIVOT" | "TRACK" | "STAY", { title: string; tone: string; tint: string }> = {
  STAY: { title: "Stay the course", tone: "var(--emerald)", tint: "rgba(22,160,126,0.10)" },
  TRACK: { title: "Watch closely", tone: "var(--blue)", tint: "rgba(46,107,255,0.10)" },
  PIVOT: { title: "Time to adjust", tone: "var(--status-queued)", tint: "rgba(240,160,48,0.10)" },
}

function Panel({ className = "", children }: { className?: string; children: ReactNode }) {
  return <div className={"glass-panel rounded-2xl " + className}>{children}</div>
}

function SentPill({ tone, bg, label, n }: { tone: string; bg: string; label: string; n: number }) {
  return (
    <span className="flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[12px]" style={{ background: bg, color: tone }}>
      <span className="h-1.5 w-1.5 rounded-full" style={{ background: tone }} />
      {label} {n}
    </span>
  )
}

export function InsightsPage() {
  const { activeBrand } = useBrandStore()
  const [selectedPlatform, setSelectedPlatform] = useState<Platform | "all">("all")
  const [sortBy, setSortBy] = useState<"impressions" | "engagements" | "saves">("impressions")

  const { data: perfData } = usePerformanceHistory()
  const { data: digest } = useDigest()
  const { data: analysis } = useLatestAnalysis()
  const { data: listening } = useListening()
  const runListening = useRunListening()
  const history = (perfData?.history ?? {}) as Record<string, unknown>

  const posts: PerfPost[] = Array.isArray(history.posts) ? (history.posts as PerfPost[]) : []

  const winningPatterns: string[] = useMemo(() => {
    const wp = (history.winning_patterns ?? {}) as Record<string, unknown>
    const out: string[] = []
    for (const arr of [wp.hook_patterns_top_3, wp.topic_clusters_top_3, wp.formats_top_3]) {
      if (Array.isArray(arr)) {
        for (const item of arr) {
          if (typeof item === "string") out.push(item)
          else if (item?.label) out.push(item.label)
          else if (item?.name) out.push(item.name)
          else if (item?.pattern) out.push(item.pattern)
        }
      }
    }
    return out
  }, [history])

  const deadPatterns: string[] = useMemo(() => {
    const dp = history.dead_patterns ?? []
    if (!Array.isArray(dp)) return []
    return dp
      .map((d: unknown) =>
        typeof d === "string" ? d : (d as Record<string, string>)?.label || (d as Record<string, string>)?.name || (d as Record<string, string>)?.pattern || "",
      )
      .filter(Boolean)
  }, [history])

  const totalImpressions = posts.reduce((s, p) => s + (p.impressions ?? 0), 0)
  const totalEngagements = posts.reduce((s, p) => s + (p.engagements ?? 0), 0)
  const totalSaves = posts.reduce((s, p) => s + (p.saves ?? 0), 0)
  const saveRate = totalImpressions > 0 ? (totalSaves / totalImpressions) * 100 : 0

  const kpis = [
    { label: "Reach", value: totalImpressions, unit: "", delta: 0 },
    { label: "Engagements", value: totalEngagements, unit: "", delta: 0 },
    { label: "Followers", value: Number(history.followers_total ?? 0), unit: "", delta: Number(history.followers_delta ?? 0) },
    { label: "Save rate", value: saveRate, unit: "%", delta: 0 },
  ]

  const reachData = useMemo(
    () =>
      posts
        .filter((p) => p.posted_at)
        .map((p) => ({ date: p.posted_at!, value: p.impressions ?? 0 }))
        .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime()),
    [posts],
  )

  const engagementData = useMemo(
    () =>
      posts
        .filter((p) => p.posted_at && p.impressions)
        .map((p) => ({ date: p.posted_at!, value: ((p.engagements ?? 0) / (p.impressions || 1)) * 100 }))
        .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime()),
    [posts],
  )

  const filteredPosts = posts
    .filter((post) => selectedPlatform === "all" || inferPlat(post.platform) === selectedPlatform)
    .map((p) => ({
      id: p.id ?? p.post_id ?? Math.random().toString(),
      platform: inferPlat(p.platform),
      caption: p.caption ?? "(no caption)",
      impressions: p.impressions ?? 0,
      engagements: p.engagements ?? 0,
      saves: p.saves ?? 0,
      postedAt: p.posted_at ? new Date(p.posted_at) : new Date(),
    }))
    .sort((a, b) => (b[sortBy] as number) - (a[sortBy] as number))

  const hasData = posts.length > 0
  const verdict = digest?.verdict ? VERDICT[digest.verdict] : null

  return (
    <div className="min-h-full bg-background/60">
      <div className="mx-auto max-w-[1100px] space-y-6 px-6 pb-20 pt-10">
        {/* Header */}
        <div>
          <h1 className="font-display text-[26px] font-semibold tracking-tight text-foreground">Intelligence</h1>
          <p className="mt-1.5 text-[14px] text-muted-foreground">
            How <span className="text-foreground">{activeBrand.name}</span> is performing — and what the team is doing about it.
          </p>
        </div>

        {/* Verdict hero */}
        {verdict && (
          <Panel className="flex items-start gap-4 p-5" >
            <span
              className="mt-1 grid h-10 w-10 shrink-0 place-items-center rounded-xl"
              style={{ background: verdict.tint }}
            >
              <span className="h-2.5 w-2.5 rounded-full" style={{ background: verdict.tone }} />
            </span>
            <div>
              <p className="text-[16px] font-semibold tracking-tight" style={{ color: verdict.tone }}>
                {verdict.title}
              </p>
              <p className="mt-1 text-[13.5px] leading-relaxed text-foreground/85">
                {digest?.verdict_reason || "Your team's current read on the brand."}
              </p>
            </div>
          </Panel>
        )}

        {/* Analyst's conclusion — what the numbers MEAN + what to do (not just charts) */}
        {analysis?.exists && analysis.lead_insight && (
          <Panel className="p-5">
            <div className="mb-2 flex items-center gap-2">
              <h3 className="text-[14px] font-semibold text-foreground">What your analyst concluded</h3>
              {analysis.confidence && (
                <span
                  className="rounded-full px-2 py-0.5 text-[10.5px] font-medium capitalize"
                  style={{
                    background:
                      analysis.confidence === "high" ? "rgba(22,160,126,0.12)"
                      : analysis.confidence === "low" ? "rgba(240,160,48,0.12)"
                      : "rgba(46,107,255,0.12)",
                    color:
                      analysis.confidence === "high" ? "var(--emerald)"
                      : analysis.confidence === "low" ? "var(--status-queued)"
                      : "var(--blue)",
                  }}
                >
                  {analysis.confidence} confidence
                </span>
              )}
            </div>
            <p className="text-[14px] leading-relaxed text-foreground/90">{analysis.lead_insight}</p>
            {(analysis.next_actions?.length ?? 0) > 0 && (
              <div className="mt-4 space-y-2.5">
                <p className="text-[11px] uppercase tracking-[0.14em] text-muted-foreground">Do next</p>
                {analysis.next_actions!.map((a, i) => (
                  <div key={i} className="flex gap-3">
                    <span className="mt-0.5 grid h-5 w-5 shrink-0 place-items-center rounded-full bg-secondary text-[11px] font-semibold text-foreground">
                      {a.priority ?? i + 1}
                    </span>
                    <div>
                      <p className="text-[13.5px] text-foreground/90">{a.action}</p>
                      {a.reason && <p className="text-[12.5px] text-muted-foreground">{a.reason}</p>}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Panel>
        )}

        {/* What people are saying — social listening (real web mentions + sentiment) */}
        <Panel className="p-5">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-[14px] font-semibold text-foreground">What people are saying</h3>
            <button
              onClick={() => runListening.mutate()}
              disabled={runListening.isPending}
              className="rounded-full border border-border px-3 py-1 text-[12px] text-muted-foreground transition-colors hover:text-foreground disabled:opacity-50"
            >
              {runListening.isPending ? "Listening…" : "Refresh"}
            </button>
          </div>
          {listening?.status === "ok" && (listening.total_mentions ?? 0) > 0 ? (
            <>
              <div className="mb-4 flex flex-wrap items-center gap-2">
                <SentPill tone="var(--emerald)" bg="rgba(22,160,126,0.12)" label="Positive" n={listening.by_sentiment?.positive ?? 0} />
                <SentPill tone="var(--muted-foreground)" bg="rgba(120,120,120,0.12)" label="Neutral" n={listening.by_sentiment?.neutral ?? 0} />
                <SentPill tone="var(--destructive)" bg="rgba(220,60,60,0.12)" label="Negative" n={listening.by_sentiment?.negative ?? 0} />
                <span className="ml-auto text-[11px] text-muted-foreground">
                  {listening.total_mentions} mentions · {Object.entries(listening.by_source_type ?? {}).map(([k, v]) => `${v} ${k}`).join(" · ")}
                </span>
              </div>
              <ul className="divide-y divide-border">
                {(listening.mentions ?? []).slice(0, 8).map((m, i) => (
                  <li key={i} className="flex items-start gap-3 py-2.5">
                    <span
                      className="mt-1.5 h-2 w-2 shrink-0 rounded-full"
                      style={{ background: m.sentiment === "positive" ? "var(--emerald)" : m.sentiment === "negative" ? "var(--destructive)" : "var(--muted-foreground)" }}
                    />
                    <div className="min-w-0">
                      <a href={m.link} target="_blank" rel="noreferrer" className="line-clamp-1 text-[13px] text-foreground/90 hover:text-primary">
                        {m.title || m.link}
                      </a>
                      <p className="text-[11.5px] text-muted-foreground capitalize">{m.source} · {m.source_type}</p>
                    </div>
                  </li>
                ))}
              </ul>
            </>
          ) : (
            <p className="text-[12.5px] text-muted-foreground">
              {runListening.data?.data?.note ||
                "No listening data yet. Hit Refresh to scan the web for what people are saying about your brand."}
            </p>
          )}
        </Panel>

        {/* Platform filter */}
        <Tabs value={selectedPlatform} onValueChange={(v) => setSelectedPlatform(v as Platform | "all")}>
          <TabsList>
            {PLATFORMS.map((platform) => (
              <TabsTrigger key={platform} value={platform} className="capitalize">
                {platform === "all" ? (
                  "All"
                ) : (
                  <span className="flex items-center gap-1.5">
                    <PlatformIcon platform={platform} className="h-3.5 w-3.5" />
                    {platform}
                  </span>
                )}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>

        {/* KPIs */}
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          {kpis.map((kpi) => (
            <Panel key={kpi.label} className="p-4">
              <p className="text-[11px] uppercase tracking-[0.14em] text-muted-foreground">{kpi.label}</p>
              <div className="mt-1.5 flex items-baseline gap-2">
                <span className="font-display text-[26px] font-semibold text-foreground">
                  {kpi.unit ? kpi.value.toFixed(1) + kpi.unit : formatNumber(kpi.value)}
                </span>
                {kpi.delta !== 0 && (
                  <span className={cn("text-[12px]", kpi.delta >= 0 ? "text-emerald" : "text-destructive")}>
                    {formatDelta(kpi.delta)} 30d
                  </span>
                )}
              </div>
            </Panel>
          ))}
        </div>

        {!hasData ? (
          <Panel className="p-10 text-center">
            <p className="text-[14px] text-muted-foreground">
              No performance data yet. Once your posts are live, the numbers and trends show up here.
            </p>
          </Panel>
        ) : (
          <>
            {/* Charts */}
            <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
              <Panel className="p-5">
                <h3 className="mb-4 text-[14px] font-semibold text-foreground">Reach over time</h3>
                <ResponsiveContainer width="100%" height={200}>
                  <LineChart data={reachData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                    <XAxis dataKey="date" tick={{ fontSize: 10, fill: "var(--muted-foreground)" }} tickFormatter={(v) => new Date(v).getDate().toString()} stroke="var(--border)" />
                    <YAxis tick={{ fontSize: 10, fill: "var(--muted-foreground)" }} tickFormatter={(v) => formatNumber(v)} stroke="var(--border)" />
                    <Tooltip contentStyle={{ backgroundColor: "var(--popover)", border: "1px solid var(--border)", borderRadius: "10px", fontSize: "12px" }} labelStyle={{ color: "var(--muted-foreground)" }} />
                    <Line type="monotone" dataKey="value" stroke="var(--primary)" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </Panel>

              <Panel className="p-5">
                <h3 className="mb-4 text-[14px] font-semibold text-foreground">Engagement rate</h3>
                <ResponsiveContainer width="100%" height={200}>
                  <LineChart data={engagementData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                    <XAxis dataKey="date" tick={{ fontSize: 10, fill: "var(--muted-foreground)" }} tickFormatter={(v) => new Date(v).getDate().toString()} stroke="var(--border)" />
                    <YAxis tick={{ fontSize: 10, fill: "var(--muted-foreground)" }} tickFormatter={(v) => v.toFixed(1) + "%"} stroke="var(--border)" />
                    <Tooltip contentStyle={{ backgroundColor: "var(--popover)", border: "1px solid var(--border)", borderRadius: "10px", fontSize: "12px" }} formatter={(value: unknown) => [Number(value).toFixed(2) + "%", "Rate"]} labelStyle={{ color: "var(--muted-foreground)" }} />
                    <Line type="monotone" dataKey="value" stroke="var(--blue)" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </Panel>
            </div>

            {/* Top posts */}
            <div>
              <div className="mb-3 flex items-center justify-between">
                <h3 className="text-[14px] font-semibold text-foreground">Top posts</h3>
                <div className="flex items-center gap-3">
                  <span className="text-[11px] text-muted-foreground">Sort by</span>
                  {(["impressions", "engagements", "saves"] as const).map((sort) => (
                    <button
                      key={sort}
                      onClick={() => setSortBy(sort)}
                      className={cn(
                        "text-[12px] capitalize transition-colors",
                        sortBy === sort ? "font-semibold text-foreground" : "text-muted-foreground hover:text-foreground",
                      )}
                    >
                      {sort === "impressions" ? "reach" : sort}
                    </button>
                  ))}
                </div>
              </div>

              <Panel className="overflow-hidden">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-border">
                      <th className="px-4 py-2.5 text-left text-[11px] font-medium uppercase tracking-[0.1em] text-muted-foreground">Post</th>
                      <th className="px-4 py-2.5 text-right text-[11px] font-medium uppercase tracking-[0.1em] text-muted-foreground">Reach</th>
                      <th className="px-4 py-2.5 text-right text-[11px] font-medium uppercase tracking-[0.1em] text-muted-foreground">Engagements</th>
                      <th className="px-4 py-2.5 text-right text-[11px] font-medium uppercase tracking-[0.1em] text-muted-foreground">Saves</th>
                      <th className="px-4 py-2.5 text-right text-[11px] font-medium uppercase tracking-[0.1em] text-muted-foreground">Posted</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {filteredPosts.map((post) => (
                      <tr key={post.id} className="transition-colors hover:bg-white/[0.02]">
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2">
                            <PlatformIcon platform={post.platform} className="h-4 w-4" />
                            <span className="line-clamp-1 text-[13px] text-foreground/90">{post.caption}</span>
                          </div>
                        </td>
                        <td className="px-4 py-3 text-right text-[13px] text-muted-foreground">{formatNumber(post.impressions)}</td>
                        <td className="px-4 py-3 text-right text-[13px] text-muted-foreground">{formatNumber(post.engagements)}</td>
                        <td className="px-4 py-3 text-right text-[13px] text-muted-foreground">{formatNumber(post.saves)}</td>
                        <td className="px-4 py-3 text-right text-[13px] text-muted-foreground">{formatTimeAgo(post.postedAt)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Panel>
            </div>
          </>
        )}

        {/* What's working / what to retire */}
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
          <Panel className="p-5">
            <h3 className="mb-3 text-[14px] font-semibold text-foreground">What&rsquo;s working</h3>
            {winningPatterns.length === 0 ? (
              <p className="text-[12.5px] italic text-muted-foreground">
                We&rsquo;ll surface winning patterns once a handful of posts are live.
              </p>
            ) : (
              <ul className="space-y-2.5">
                {winningPatterns.map((pattern, i) => (
                  <li key={i} className="flex items-start gap-2.5">
                    <StatusDot status="success" className="mt-1.5" />
                    <span className="text-[13px] leading-relaxed text-foreground/85">{pattern}</span>
                  </li>
                ))}
              </ul>
            )}
          </Panel>

          <Panel className="p-5">
            <h3 className="mb-3 text-[14px] font-semibold text-foreground">What to retire</h3>
            {deadPatterns.length === 0 ? (
              <p className="text-[12.5px] italic text-muted-foreground">Nothing to retire yet.</p>
            ) : (
              <ul className="space-y-2.5">
                {deadPatterns.map((pattern, i) => (
                  <li key={i} className="flex items-start gap-2.5">
                    <StatusDot status="error" className="mt-1.5" />
                    <span className="text-[13px] leading-relaxed text-muted-foreground line-through">{pattern}</span>
                  </li>
                ))}
              </ul>
            )}
          </Panel>
        </div>
      </div>
    </div>
  )
}
