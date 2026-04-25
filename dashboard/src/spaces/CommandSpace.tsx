/**
 * CommandSpace — Space 1
 * Home screen: pipeline progress, next action, attention items, activity feed.
 * Notion/Linear aesthetic: large text, generous padding, status-first.
 */

import { useEffect, useRef, useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import {
  CheckCircle2, Circle, Loader2, ArrowRight,
  Inbox, Activity, Play, RefreshCw, Mic, X, Zap,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { apiFetch } from "@/lib/api"
import { useBrandStore } from "@/store/brandStore"
import type { Agent, BrandSummary, ApiResponse } from "@/types"

// ── Pipeline definition ────────────────────────────────────────────────────────

const PIPELINE: { name: string; label: string }[] = [
  { name: "Trend Researcher",  label: "Trends"   },
  { name: "Strategy Agent",    label: "Strategy" },
  { name: "Content Planner",   label: "Content"  },
  { name: "Script Writer",     label: "Scripts"  },
  { name: "Creative Director", label: "Creative" },
]

// ── API helpers ────────────────────────────────────────────────────────────────

async function fetchAgentStatus(slug: string): Promise<Agent[]> {
  const res  = await apiFetch(`/api/agents/status?brand_slug=${slug}`)
  const json: ApiResponse<Agent[]> = await res.json()
  if (!json.success) throw new Error(json.error)
  return json.data
}

async function fetchBrandSummary(slug: string): Promise<BrandSummary> {
  const res  = await apiFetch(`/api/brand/summary?brand_slug=${slug}`)
  const json: ApiResponse<BrandSummary> = await res.json()
  if (!json.success) throw new Error(json.error)
  return json.data
}

async function runAgent(agentName: string, brandSlug: string): Promise<{ message: string; agent: string }> {
  const res  = await apiFetch("/api/agents/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ agentName, brand_slug: brandSlug }),
  })
  const json: ApiResponse<{ message: string; agent: string }> = await res.json()
  if (!json.success) throw new Error(json.error ?? "Agent run failed")
  return json.data
}

async function runDailyPipeline(brandSlug: string): Promise<{ pipeline_run_id: string }> {
  const res  = await apiFetch("/api/pipeline/daily-run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ brand_slug: brandSlug }),
  })
  const json: ApiResponse<{ pipeline_run_id: string }> = await res.json()
  if (!json.success) throw new Error(json.error ?? "Daily pipeline failed to start")
  return json.data
}

async function askJarvis(query: string, brandSlug: string): Promise<{ response: string; audio_b64: string | null }> {
  const res  = await apiFetch("/api/jarvis/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, brand_slug: brandSlug }),
  })
  const json = await res.json()
  if (!json.success) throw new Error(json.error ?? "Jarvis query failed")
  return { response: json.response as string, audio_b64: json.audio_b64 as string | null }
}

// ── Pipeline Step ──────────────────────────────────────────────────────────────

function PipelineStep({
  label, status, isLast,
}: {
  label: string
  status: "done" | "running" | "error" | "idle"
  isLast: boolean
}) {
  const isDone    = status === "done"
  const isRunning = status === "running"
  const isError   = status === "error"

  return (
    <div className="flex items-center gap-2">
      <div className="flex flex-col items-center gap-1">
        <div
          className={cn(
            "w-8 h-8 rounded-full flex items-center justify-center border-2 transition-colors",
            isDone    && "border-[hsl(var(--gc-green))]  bg-[rgba(46,204,113,0.12)]",
            isRunning && "border-[hsl(var(--gc-amber))]  bg-[rgba(240,165,0,0.12)] animate-pulse",
            isError   && "border-[hsl(var(--gc-red))]    bg-[rgba(231,76,60,0.12)]",
            !isDone && !isRunning && !isError && "border-[hsl(var(--border))] bg-[hsl(var(--gc-surface2))]",
          )}
        >
          {isDone    && <CheckCircle2 size={14} className="text-[hsl(var(--gc-green))]" />}
          {isRunning && <Loader2      size={14} className="text-[hsl(var(--gc-amber))] animate-spin" />}
          {isError   && <span style={{ fontSize: 12 }}>!</span>}
          {!isDone && !isRunning && !isError && <Circle size={10} className="text-[hsl(var(--gc-text-3))]" />}
        </div>
        <span
          style={{ fontSize: 12, fontWeight: isDone ? 600 : 500, whiteSpace: "nowrap" }}
          className={cn(
            isDone    ? "text-[hsl(var(--gc-green))]"   :
            isRunning ? "text-[hsl(var(--gc-amber))]"   :
            isError   ? "text-[hsl(var(--gc-red))]"     :
            "text-[hsl(var(--gc-text-2))]"
          )}
        >
          {label}
        </span>
      </div>
      {!isLast && (
        <div
          className={cn("h-0.5 w-10 flex-shrink-0 -mt-4", isDone ? "bg-[hsl(var(--gc-green))]" : "bg-[hsl(var(--border))]")}
        />
      )}
    </div>
  )
}

// ── Main ───────────────────────────────────────────────────────────────────────

export function CommandSpace() {
  const { activeBrand, navigate } = useBrandStore()
  const queryClient               = useQueryClient()
  const prevStatusesRef           = useRef<Record<string, string>>({})

  const { data: agents = [], isLoading: agentsLoading } = useQuery({
    queryKey:        ["agents-status", activeBrand.slug],
    queryFn:         () => fetchAgentStatus(activeBrand.slug),
    refetchInterval: 10000,
    enabled:         !!activeBrand.slug,
  })

  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey:        ["brand-summary", activeBrand.slug],
    queryFn:         () => fetchBrandSummary(activeBrand.slug),
    refetchInterval: 15000,
    enabled:         !!activeBrand.slug,
  })

  useEffect(() => {
    const prev = prevStatusesRef.current
    let anyCompleted = false
    for (const agent of agents) {
      if (prev[agent.name] === "running" && agent.status === "done") anyCompleted = true
      prev[agent.name] = agent.status
    }
    if (anyCompleted) {
      queryClient.invalidateQueries({ queryKey: ["brand-summary", activeBrand.slug] })
    }
  }, [agents, activeBrand.slug, queryClient])

  const mutation = useMutation({
    mutationFn: ({ name }: { name: string }) => runAgent(name, activeBrand.slug),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["agents-status", activeBrand.slug] })
    },
  })

  const dailyMutation = useMutation({
    mutationFn: () => runDailyPipeline(activeBrand.slug),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["agents-status", activeBrand.slug] })
    },
  })

  const [showJarvis,     setShowJarvis]     = useState(false)
  const [micText,        setMicText]        = useState("")
  const [jarvisResponse, setJarvisResponse] = useState("")
  const [jarvisLoading,  setJarvisLoading]  = useState(false)

  const handleAskJarvis = async () => {
    if (!micText.trim()) return
    setJarvisLoading(true)
    setJarvisResponse("")
    try {
      const result = await askJarvis(micText, activeBrand.slug)
      setJarvisResponse(result.response)
      if (result.audio_b64) {
        const audio = new Audio(`data:audio/mp3;base64,${result.audio_b64}`)
        audio.play().catch(() => {/* ignore autoplay restrictions */})
      }
    } catch {
      setJarvisResponse("Jarvis is offline. Check Flask API.")
    } finally {
      setJarvisLoading(false)
    }
  }

  // Derive pipeline statuses
  const pipelineSteps = PIPELINE.map(step => {
    const agent = agents.find(a => a.name === step.name)
    return { ...step, status: (agent?.status ?? "idle") as "done" | "running" | "error" | "idle" }
  })

  // Next action = first pipeline step that isn't done
  const nextStep = pipelineSteps.find(s => s.status !== "done")

  const pendingCount = summary?.notion_pending ?? 0
  const isRunningAny = agents.some(a => a.status === "running")
  const isLoading    = agentsLoading || summaryLoading

  if (!activeBrand.slug) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-6 text-center px-8">
        <div className="w-16 h-16 rounded-full gc-card flex items-center justify-center text-3xl">🏢</div>
        <div>
          <h2 className="text-white font-bold" style={{ fontSize: 22 }}>No brand selected</h2>
          <p className="text-[hsl(var(--gc-text-2))] mt-2" style={{ fontSize: 15 }}>
            Use the brand switcher in the sidebar to select or create a brand.
          </p>
        </div>
        <button
          onClick={() => navigate(4)}
          className="px-6 py-3 rounded-lg bg-[hsl(var(--gc-gold))] text-black font-bold hover:opacity-85 transition-opacity"
          style={{ fontSize: 14 }}
        >
          + Add Brand
        </button>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Top bar */}
      <div
        style={{ height: 52, flexShrink: 0 }}
        className="flex items-center justify-between px-8 border-b border-[hsl(var(--border))]"
      >
        <div className="flex items-center gap-2">
          <span className="text-[hsl(var(--gc-text-2))]" style={{ fontSize: 13 }}>Command</span>
          <span className="text-[hsl(var(--gc-text-3))]" style={{ fontSize: 13 }}>/</span>
          <span className="text-white font-semibold" style={{ fontSize: 14 }}>Overview</span>
        </div>
        <div className="flex items-center gap-3">
          {isRunningAny && (
            <div className="flex items-center gap-2 px-3 py-1 rounded border"
              style={{ fontSize: 12, fontWeight: 600, color: "hsl(var(--gc-amber))", background: "rgba(245,166,35,0.08)", borderColor: "rgba(245,166,35,0.28)" }}>
              <div className="w-1.5 h-1.5 rounded-full bg-[hsl(var(--gc-amber))] animate-pulse" />
              Agent Running
            </div>
          )}
          <button
            onClick={() => { setShowJarvis(true); setJarvisResponse(""); setMicText("") }}
            className="w-8 h-8 rounded-full flex items-center justify-center hover:bg-[hsl(var(--gc-surface2))] transition-colors border border-[hsl(var(--border))]"
            title="Ask Jarvis"
          >
            <Mic size={13} className="text-[hsl(var(--gc-gold))]" />
          </button>
          {!isLoading && (
            <button
              onClick={() => {
                queryClient.invalidateQueries({ queryKey: ["agents-status", activeBrand.slug] })
                queryClient.invalidateQueries({ queryKey: ["brand-summary", activeBrand.slug] })
              }}
              className="flex items-center gap-1.5 text-[hsl(var(--gc-text-2))] hover:text-white transition-colors"
              style={{ fontSize: 13 }}
            >
              <RefreshCw size={12} />
              Refresh
            </button>
          )}
        </div>
      </div>

      {/* Scrollable body */}
      <div className="flex-1 overflow-y-auto">
        <div className="px-8 pt-8 pb-12 space-y-10" style={{ maxWidth: 860 }}>

          {/* Brand hero */}
          <div>
            <p className="text-[hsl(var(--gc-text-2))] font-semibold uppercase tracking-widest" style={{ fontSize: 11 }}>
              Active Brand
            </p>
            <h1 style={{ fontSize: 32, fontWeight: 800, letterSpacing: -0.5, lineHeight: 1.2, marginTop: 6 }}
              className="text-[hsl(var(--gc-gold))]">
              {summary?.brand_name ?? activeBrand.name}
            </h1>
            {summary?.phase && (
              <span
                className="inline-flex items-center px-3 py-1 rounded border mt-3"
                style={{ fontSize: 11, fontWeight: 700, letterSpacing: 1, textTransform: "uppercase",
                  color: "hsl(var(--gc-gold))", background: "rgba(201,168,76,0.1)", borderColor: "rgba(201,168,76,0.25)" }}>
                {summary.phase}
              </span>
            )}
          </div>

          {/* Pipeline bar */}
          <div>
            <p className="text-[hsl(var(--gc-text-2))] font-semibold uppercase tracking-widest mb-5" style={{ fontSize: 11 }}>
              Weekly Pipeline
            </p>
            {isLoading ? (
              <div className="h-16 gc-card animate-pulse rounded-xl" />
            ) : (
              <div className="gc-card rounded-xl px-6 py-5">
                <div className="flex items-start gap-0">
                  {pipelineSteps.map((step, i) => (
                    <PipelineStep
                      key={step.name}
                      label={step.label}
                      status={step.status}
                      isLast={i === pipelineSteps.length - 1}
                    />
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Next action + Attention — 2 col */}
          <div className="grid grid-cols-2 gap-5">
            {/* Next Action */}
            <div className="gc-card rounded-xl p-6 space-y-4">
              <p className="text-[hsl(var(--gc-text-2))] font-semibold uppercase tracking-widest" style={{ fontSize: 11 }}>
                Next Action
              </p>
              {nextStep ? (
                <>
                  <div>
                    <p className="text-white font-bold" style={{ fontSize: 20 }}>
                      Run {nextStep.label}
                    </p>
                    <p className="text-[hsl(var(--gc-text-2))] mt-1" style={{ fontSize: 14 }}>
                      {nextStep.name}
                    </p>
                  </div>
                  <button
                    onClick={() => mutation.mutate({ name: nextStep.name })}
                    disabled={mutation.isPending || isRunningAny}
                    className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-[hsl(var(--gc-gold))] text-black font-bold hover:opacity-85 transition-opacity disabled:opacity-40"
                    style={{ fontSize: 13 }}
                  >
                    {mutation.isPending
                      ? <Loader2 size={14} className="animate-spin" />
                      : <Play size={14} />
                    }
                    Run Now
                  </button>
                  <button
                    onClick={() => dailyMutation.mutate()}
                    disabled={dailyMutation.isPending || isRunningAny}
                    className="flex items-center gap-2 px-5 py-2.5 rounded-lg font-bold hover:opacity-85 transition-opacity disabled:opacity-40"
                    style={{ fontSize: 13, border: "1px solid hsl(var(--gc-gold))", color: "hsl(var(--gc-gold))", background: "transparent" }}
                    title="Run Trends → Data Analyst → Scripts in sequence"
                  >
                    {dailyMutation.isPending
                      ? <Loader2 size={14} className="animate-spin" />
                      : <Zap size={14} />
                    }
                    Run Today
                  </button>
                </>
              ) : (
                <div>
                  <p className="text-[hsl(var(--gc-green))] font-bold" style={{ fontSize: 18 }}>
                    Pipeline complete ✓
                  </p>
                  <p className="text-[hsl(var(--gc-text-2))] mt-1" style={{ fontSize: 14 }}>
                    All 5 pipeline steps done this week.
                  </p>
                </div>
              )}
            </div>

            {/* Needs Attention */}
            <div className="gc-card rounded-xl p-6 space-y-4">
              <p className="text-[hsl(var(--gc-text-2))] font-semibold uppercase tracking-widest" style={{ fontSize: 11 }}>
                Needs Your Eyes
              </p>
              {pendingCount > 0 ? (
                <>
                  <div>
                    <p className="text-[hsl(var(--gc-amber))] font-bold" style={{ fontSize: 28, lineHeight: 1 }}>
                      {pendingCount}
                    </p>
                    <p className="text-white font-semibold mt-1" style={{ fontSize: 15 }}>
                      {pendingCount === 1 ? "output" : "outputs"} pending review
                    </p>
                  </div>
                  <button
                    onClick={() => navigate(2)}
                    className="flex items-center gap-2 text-[hsl(var(--gc-gold))] hover:opacity-75 transition-opacity font-semibold"
                    style={{ fontSize: 14 }}
                  >
                    Go to Review <ArrowRight size={14} />
                  </button>
                </>
              ) : (
                <div>
                  <p className="text-[hsl(var(--gc-green))] font-bold" style={{ fontSize: 18 }}>
                    All clear ✓
                  </p>
                  <p className="text-[hsl(var(--gc-text-2))] mt-1" style={{ fontSize: 14 }}>
                    Nothing pending approval.
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Stats row */}
          {summary && (
            <div className="grid grid-cols-3 gap-4">
              {[
                { label: "Posts Scripted",   value: summary.posts_scripted,  color: "text-white" },
                { label: "Agents Run",       value: summary.agents_run,      color: "text-white" },
                { label: "Approved Outputs", value: summary.notion_approved, color: "text-[hsl(var(--gc-green))]" },
              ].map(({ label, value, color }) => (
                <div key={label} className="gc-card rounded-xl p-5">
                  <p className={cn("font-bold", color)} style={{ fontSize: 28, lineHeight: 1 }}>{value}</p>
                  <p className="text-[hsl(var(--gc-text-2))] mt-1.5" style={{ fontSize: 13 }}>{label}</p>
                </div>
              ))}
            </div>
          )}

          {/* Activity feed */}
          {(summary?.activity_feed ?? []).length > 0 && (
            <div>
              <div className="flex items-center gap-2 mb-4">
                <Activity size={14} className="text-[hsl(var(--gc-text-3))]" />
                <p className="text-[hsl(var(--gc-text-2))] font-semibold uppercase tracking-widest" style={{ fontSize: 11 }}>
                  Recent Activity
                </p>
              </div>
              <div className="gc-card rounded-xl divide-y divide-[hsl(var(--border))]">
                {summary!.activity_feed.slice(0, 8).map((item, i) => (
                  <div key={i} className="flex items-center gap-4 px-5 py-4">
                    <span style={{ fontSize: 18, flexShrink: 0 }}>{item.icon}</span>
                    <div className="flex-1 min-w-0">
                      <p className="text-white font-semibold truncate" style={{ fontSize: 14 }}>{item.agent}</p>
                      {item.summary && (
                        <p className="text-[hsl(var(--gc-text-2))] truncate mt-0.5" style={{ fontSize: 13 }}>{item.summary}</p>
                      )}
                    </div>
                    <div className="flex items-center gap-3 shrink-0">
                      <span
                        className="px-2 py-0.5 rounded border font-mono"
                        style={{
                          fontSize: 11,
                          color:   item.status === "done"    ? "hsl(var(--gc-green))"  :
                                   item.status === "running" ? "hsl(var(--gc-amber))"  :
                                   item.status === "error"   ? "hsl(var(--gc-red))"    :
                                   "hsl(var(--gc-text-2))",
                          background: item.status === "done"    ? "rgba(46,204,113,0.07)"  :
                                      item.status === "running" ? "rgba(240,165,0,0.07)"   :
                                      item.status === "error"   ? "rgba(231,76,60,0.07)"   :
                                      "hsl(var(--gc-surface2))",
                          borderColor: item.status === "done"    ? "rgba(46,204,113,0.2)"  :
                                       item.status === "running" ? "rgba(240,165,0,0.2)"   :
                                       item.status === "error"   ? "rgba(231,76,60,0.2)"   :
                                       "hsl(var(--border))",
                        }}
                      >
                        {item.status}
                      </span>
                      {item.timestamp && (
                        <span className="text-[hsl(var(--gc-text-3))]" style={{ fontSize: 12 }}>
                          {new Date(item.timestamp).toLocaleString("en-IN", { dateStyle: "short", timeStyle: "short" })}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Empty state when no activity */}
          {!isLoading && (summary?.activity_feed ?? []).length === 0 && (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <div className="w-16 h-16 rounded-full gc-card flex items-center justify-center mb-5">
                <Inbox size={28} className="text-[hsl(var(--gc-text-2))]" />
              </div>
              <p className="text-white font-semibold" style={{ fontSize: 16 }}>No activity yet</p>
              <p className="text-[hsl(var(--gc-text-2))] mt-1.5" style={{ fontSize: 14 }}>
                Run your first agent to get started
              </p>
              <button
                onClick={() => navigate(3)}
                className="mt-6 flex items-center gap-2 px-5 py-2.5 rounded-lg bg-[hsl(var(--gc-gold))] text-black font-bold hover:opacity-85 transition-opacity"
                style={{ fontSize: 13 }}
              >
                Go to Agents <ArrowRight size={14} />
              </button>
            </div>
          )}

        </div>
      </div>

      {/* Jarvis Voice Modal */}
      {showJarvis && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center"
          style={{ background: "rgba(0,0,0,0.75)" }}
          onClick={(e) => { if (e.target === e.currentTarget) setShowJarvis(false) }}
        >
          <div className="gc-card rounded-2xl p-6 w-full space-y-4" style={{ maxWidth: 480 }}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-full flex items-center justify-center"
                  style={{ background: "rgba(201,168,76,0.15)", border: "1px solid rgba(201,168,76,0.3)" }}>
                  <Mic size={14} className="text-[hsl(var(--gc-gold))]" />
                </div>
                <span className="text-white font-bold" style={{ fontSize: 16 }}>Ask Jarvis</span>
              </div>
              <button onClick={() => setShowJarvis(false)}
                className="text-[hsl(var(--gc-text-3))] hover:text-white transition-colors">
                <X size={16} />
              </button>
            </div>

            <textarea
              value={micText}
              onChange={e => setMicText(e.target.value)}
              onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleAskJarvis() } }}
              placeholder="Ask anything about your pipeline… (Enter to send)"
              rows={3}
              className="w-full rounded-xl px-4 py-3 text-white placeholder:text-[hsl(var(--gc-text-3))] focus:outline-none resize-none"
              style={{ background: "hsl(var(--gc-surface2))", border: "1px solid hsl(var(--border))", fontSize: 14, lineHeight: 1.6 }}
              autoFocus
            />

            <button
              onClick={handleAskJarvis}
              disabled={jarvisLoading || !micText.trim()}
              className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl font-bold transition-opacity hover:opacity-85 disabled:opacity-40"
              style={{ background: "hsl(var(--gc-gold))", color: "#000", fontSize: 14 }}
            >
              {jarvisLoading ? <Loader2 size={14} className="animate-spin" /> : <Mic size={14} />}
              {jarvisLoading ? "Thinking…" : "Ask"}
            </button>

            {jarvisResponse && (
              <div className="rounded-xl px-4 py-3"
                style={{ background: "rgba(201,168,76,0.07)", border: "1px solid rgba(201,168,76,0.2)" }}>
                <p className="text-white leading-relaxed" style={{ fontSize: 14, lineHeight: 1.7 }}>{jarvisResponse}</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
