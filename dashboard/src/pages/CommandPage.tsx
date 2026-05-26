import { useMemo } from "react"
import { AlertTriangle } from "lucide-react"
import { getGreeting, formatTimeAgo, formatTime, formatNumber, formatDelta } from "@/lib/utils"
import { cn } from "@/lib/utils"
import { StatusDot } from "@/components/ui/status-dot"
import { PlatformIcon } from "@/components/ui/platform-icon"
import {
  useAgentStatus,
  usePendingOutputs,
  usePerformanceHistory,
  useLiveAgents,
} from "@/hooks/useGridApi"
import type { Platform } from "@/store/appStore"

function inferPlatform(filename: string, agent: string): Platform {
  const hay = `${filename} ${agent}`.toLowerCase()
  if (hay.includes("instagram") || hay.includes("ig")) return "instagram"
  if (hay.includes("linkedin") || hay.includes("li_") || hay.includes("li.")) return "linkedin"
  if (hay.includes("tiktok") || hay.includes("tt_") || hay.includes("tt.")) return "tiktok"
  if (hay.includes("youtube") || hay.includes("yt_") || hay.includes("yt.")) return "youtube"
  return "x"
}

export function CommandPage() {
  const { data: agentStatus } = useAgentStatus()
  const { data: pending } = usePendingOutputs()
  const { data: perf } = usePerformanceHistory()
  const liveAgents = useLiveAgents()

  const today = new Date()
  const formattedDate = new Intl.DateTimeFormat("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
    year: "numeric",
  }).format(today)

  // ── KPIs ───────────────────────────────────────────────────────────────────
  const pendingCount = pending?.outputs?.length ?? 0
  const runningAgents = agentStatus?.agents?.filter((a) => a.status === "running").length ?? 0

  const perfHistory: any = perf?.history ?? {}
  const impressions = Number(perfHistory.impressions_7d ?? perfHistory.impressions ?? 0)
  const followers = Number(perfHistory.followers_7d ?? perfHistory.new_followers ?? 0)
  const postsShipped = Number(perfHistory.posts_shipped_7d ?? 0)

  const kpis = [
    { label: "Posts shipped 7d", value: postsShipped, delta: Number(perfHistory.posts_delta ?? 0) },
    { label: "Pending approvals", value: pendingCount, delta: 0 },
    { label: "Impressions 7d", value: impressions, delta: Number(perfHistory.impressions_delta ?? 0) },
    { label: "New followers 7d", value: followers, delta: Number(perfHistory.followers_delta ?? 0) },
  ]

  // ── Activity timeline (derived from agent status) ──────────────────────────
  const activityEvents = useMemo(() => {
    return liveAgents
      .filter((a) => a.lastRun)
      .map((a) => ({
        id: a.slug,
        agentName: a.name,
        action:
          a.status === "running"
            ? "is running now"
            : a.status === "error"
              ? "errored on last run"
              : a.status === "queued"
                ? "is queued"
                : "completed last run",
        status: a.status,
        timestamp: a.lastRun!,
      }))
      .sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime())
      .slice(0, 12)
  }, [liveAgents])

  // ── Up next (scheduled pending outputs) ────────────────────────────────────
  const upNext = useMemo(() => {
    const items = pending?.outputs ?? []
    return items
      .filter((o) => !!o.scheduled_for)
      .map((o) => ({
        id: o.filename,
        platform: inferPlatform(o.filename, o.agent_slug),
        scheduledTime: new Date(o.scheduled_for!),
        caption: o.caption || o.preview || "(no caption)",
        status: "queued" as const,
      }))
      .sort((a, b) => a.scheduledTime.getTime() - b.scheduledTime.getTime())
      .slice(0, 5)
  }, [pending])

  // ── Failures ───────────────────────────────────────────────────────────────
  const failedEvents = activityEvents.filter((e) => e.status === "error")

  return (
    <div className="p-6 space-y-6">
      {/* Greeting */}
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">
          {getGreeting()}, Gaurav.
        </h1>
        <p className="font-mono text-sm text-muted-foreground">
          {formattedDate}
          {runningAgents > 0 && (
            <span className="ml-2">· {runningAgents} agents running</span>
          )}
        </p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-4 gap-4">
        {kpis.map((kpi) => (
          <div
            key={kpi.label}
            className="rounded-lg border border-border bg-card p-4"
          >
            <p className="text-xs text-muted-foreground mb-1">{kpi.label}</p>
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-semibold font-mono">
                {formatNumber(kpi.value)}
              </span>
              {kpi.delta !== 0 && (
                <span
                  className={cn(
                    "text-xs font-mono",
                    kpi.delta >= 0 ? "text-primary" : "text-destructive",
                  )}
                >
                  {formatDelta(kpi.delta)}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Today's Agent Activity */}
        <div className="space-y-3">
          <h2 className="text-sm font-medium text-muted-foreground">
            Today&apos;s agent activity
          </h2>
          <div className="rounded-lg border border-border bg-card">
            {activityEvents.length === 0 ? (
              <div className="px-4 py-8 text-center text-sm text-muted-foreground">
                No agents have run yet. Trigger one from the Agents page.
              </div>
            ) : (
              <div className="divide-y divide-border">
                {activityEvents.map((event) => (
                  <div
                    key={event.id}
                    className="flex items-start gap-3 px-4 py-3 hover:bg-secondary/50 transition-colors"
                  >
                    <StatusDot status={event.status} className="mt-1.5" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm">
                        <span className="font-medium">{event.agentName}</span>{" "}
                        <span className="text-muted-foreground">{event.action}</span>
                      </p>
                    </div>
                    <span className="text-xs font-mono text-muted-foreground whitespace-nowrap">
                      {formatTimeAgo(event.timestamp)}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Up Next */}
        <div className="space-y-3">
          <h2 className="text-sm font-medium text-muted-foreground">Up next</h2>
          {upNext.length === 0 ? (
            <div className="rounded-lg border border-border bg-card px-4 py-8 text-center text-sm text-muted-foreground">
              No scheduled posts. Run Content Planner to populate.
            </div>
          ) : (
            <div className="flex gap-3 overflow-x-auto pb-2 hide-scrollbar">
              {upNext.map((post) => (
                <div
                  key={post.id}
                  className="flex-shrink-0 w-56 rounded-lg border border-border bg-card p-3 hover:bg-secondary/50 transition-colors"
                >
                  <div className="flex items-center gap-2 mb-2">
                    <PlatformIcon platform={post.platform} className="h-4 w-4" />
                    <span className="text-xs font-mono text-muted-foreground">
                      {formatTime(post.scheduledTime)}
                    </span>
                    <StatusDot status={post.status} className="ml-auto" />
                  </div>
                  <p className="text-sm line-clamp-2">{post.caption}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Failures Alert */}
      {failedEvents.length > 0 && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <AlertTriangle className="h-4 w-4 text-destructive" />
              <p className="text-sm">
                <span className="font-medium">
                  {failedEvents.length} agent failure{failedEvents.length > 1 ? "s" : ""}
                </span>
                <span className="text-muted-foreground"> in the last 24 hours</span>
              </p>
            </div>
            <button className="text-xs font-medium text-primary hover:underline">
              Investigate
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
