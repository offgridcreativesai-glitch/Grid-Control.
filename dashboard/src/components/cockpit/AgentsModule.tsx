/**
 * Agent Activity — ported from agents.jsx, wired to real agent status + pending count.
 * Shows the live roster (status dots), an "N awaiting review" alert that routes to /review,
 * and quiet run buttons for the two most common manual kicks.
 */
import { useNavigate } from "react-router-dom"
import { TriangleAlert, ArrowRight, Compass, ListChecks } from "lucide-react"
import { useLiveAgents, usePendingOutputs, useRunAgent } from "@/hooks/useGridApi"
import { Card, ModuleHeader, SoftButton, StatusDot, STATUS } from "./primitives"
import { relativeTime } from "@/lib/cockpitFormat"

// The handful of agents the cockpit surfaces by default (the rest live on /agents).
const COCKPIT_AGENTS = [
  "trend-researcher",
  "content-planner",
  "script-writer",
  "creative-director",
  "data-analyst",
  "brand-guardian",
]

type Tone = "blue" | "gray" | "red"
function toneFor(status: string): { tone: Tone; pulse: boolean; label: string } {
  if (status === "running" || status === "queued") return { tone: "blue", pulse: true, label: "running" }
  if (status === "blocked" || status === "error") return { tone: "red", pulse: false, label: "blocked" }
  return { tone: "gray", pulse: false, label: "idle" }
}

export function AgentsModule() {
  const navigate = useNavigate()
  const agents = useLiveAgents()
  const { data: pending } = usePendingOutputs()
  const runAgent = useRunAgent()

  const shown = COCKPIT_AGENTS.map((slug) => agents.find((a) => a.slug === slug)).filter(
    Boolean,
  ) as typeof agents

  const runningCount = shown.filter((a) => a.status === "running" || a.status === "queued").length
  const pendingCount = pending?.outputs?.length ?? 0

  return (
    <Card className="flex h-full flex-col p-6">
      <ModuleHeader
        title="Agent Activity"
        sub={`${shown.length} agents · ${runningCount} running`}
      />

      {pendingCount > 0 && (
        <button
          onClick={() => navigate("/review")}
          className="group mt-5 flex w-full items-center justify-between rounded-xl border px-3.5 py-2.5 text-left transition-colors"
          style={{ borderColor: STATUS.amber.bd, background: STATUS.amber.bg }}
        >
          <span
            className="flex items-center gap-2 text-[12.5px] font-medium"
            style={{ color: STATUS.amber.fg }}
          >
            <TriangleAlert size={14} /> {pendingCount} awaiting review
          </span>
          <ArrowRight
            size={15}
            style={{ color: STATUS.amber.fg }}
            className="transition-transform group-hover:translate-x-0.5"
          />
        </button>
      )}

      <ul className="mt-4 flex-1 divide-y divide-white/[0.05]">
        {shown.map((a) => {
          const t = toneFor(a.status)
          return (
            <li key={a.slug} className="flex items-center gap-3 py-2.5">
              <StatusDot tone={t.tone} pulse={t.pulse} title={t.label} />
              <div className="min-w-0 flex-1">
                <div className="flex items-baseline justify-between gap-3">
                  <span className="text-[13px] font-medium text-zinc-200">{a.name}</span>
                  <span className="shrink-0 font-mono text-[10.5px] text-zinc-600">
                    {a.lastRun ? relativeTime(a.lastRun.getTime()) : "—"}
                  </span>
                </div>
                <div className="truncate text-[12px] text-zinc-500">{a.role}</div>
              </div>
            </li>
          )
        })}
      </ul>

      <div className="mt-4 flex items-center gap-2 border-t border-white/[0.06] pt-4">
        <SoftButton
          icon={Compass}
          disabled={runAgent.isPending}
          onClick={() => runAgent.mutate("trend-researcher")}
        >
          Run Trend Research
        </SoftButton>
        <SoftButton
          icon={ListChecks}
          disabled={runAgent.isPending}
          onClick={() => runAgent.mutate("script-writer")}
        >
          Generate scripts
        </SoftButton>
      </div>
    </Card>
  )
}
