import { cn } from "@/lib/utils"
import { Play, Loader2, Clock, CheckCircle2, AlertCircle, Lock } from "lucide-react"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import type { Agent, AgentStatus } from "@/types"

interface AgentWithFlags extends Agent {
  coming_soon?: boolean
}

// Status dot class + label
const STATUS: Record<AgentStatus | "coming_soon", { dot: string; label: string }> = {
  idle:        { dot: "idle",    label: "Idle" },
  running:     { dot: "running", label: "Running" },
  done:        { dot: "online",  label: "Done" },
  error:       { dot: "idle",    label: "Error" },
  coming_soon: { dot: "idle",    label: "Coming Soon" },
}

interface RunResult {
  type: "success" | "error"
  message: string
}

interface AgentCardProps {
  agent: AgentWithFlags
  onRun: (agentName: string) => void
  isRunning: boolean
  runResult?: RunResult
}

// Agent emoji map — keeps parity with mockup
const AGENT_EMOJI: Record<string, string> = {
  "Trend Researcher":  "📡",
  "Strategy Agent":    "🗺️",
  "Content Planner":   "📅",
  "Script Writer":     "✍️",
  "Creative Director": "🎬",
  "Data Analyst":      "📊",
  "Funnel Specialist": "🔧",
  "Ad Strategist":     "🎯",
  "Website Agent":     "🌐",
}

export function AgentCard({ agent, onRun, isRunning, runResult }: AgentCardProps) {
  const isComingSoon = agent.coming_soon === true
  const s = STATUS[isComingSoon ? "coming_soon" : (agent.status ?? "idle")]
  const emoji = AGENT_EMOJI[agent.name] ?? "🤖"
  const isError = agent.status === "error"

  if (isComingSoon) {
    return (
      <Tooltip delayDuration={0}>
        <TooltipTrigger asChild>
          <div className="gc-card p-3 flex items-center gap-3 opacity-35 cursor-not-allowed select-none">
            <div
              className="flex items-center justify-center rounded-[8px] flex-shrink-0"
              style={{ width: 32, height: 32, background: "hsl(var(--gc-surface2))", border: "1px solid hsl(var(--border))", fontSize: 15 }}
            >
              {emoji}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-1.5">
                <span style={{ fontSize: 13, fontWeight: 600 }} className="text-[hsl(var(--foreground))] truncate">{agent.name}</span>
                <Lock size={10} className="text-[hsl(var(--gc-text-3))] flex-shrink-0" />
              </div>
              <div style={{ fontSize: 11 }} className="text-[hsl(var(--gc-text-2))] truncate mt-0.5">{agent.role}</div>
            </div>
            <div className={`status-dot ${s.dot}`} />
          </div>
        </TooltipTrigger>
        <TooltipContent side="top" className="bg-[hsl(var(--gc-surface))] border-[hsl(var(--border))]">
          Script being built — coming soon
        </TooltipContent>
      </Tooltip>
    )
  }

  return (
    <div className={cn(
      "gc-card gc-card-hover p-3 flex flex-col gap-2",
      agent.status === "running" && "border-[rgba(240,165,0,0.3)]",
      isError && "border-[rgba(231,76,60,0.3)]",
    )}>
      {/* Row 1: icon + name + dot */}
      <div className="flex items-center gap-3">
        <div
          className={cn(
            "flex items-center justify-center rounded-[8px] flex-shrink-0",
            agent.status === "running" && "border-[rgba(240,165,0,0.3)] bg-[rgba(240,165,0,0.08)]"
          )}
          style={{
            width: 32, height: 32, fontSize: 15,
            background: agent.status === "running" ? undefined : "hsl(var(--gc-surface2))",
            border: agent.status === "running" ? undefined : "1px solid hsl(var(--border))",
          }}
        >
          {emoji}
        </div>
        <div className="flex-1 min-w-0">
          <div style={{ fontSize: 13, fontWeight: 600 }} className="text-[hsl(var(--foreground))] truncate">{agent.name}</div>
          <div style={{ fontSize: 11 }} className="text-[hsl(var(--gc-text-2))] truncate mt-0.5">{agent.role}</div>
        </div>
        <div className={`status-dot ${s.dot} flex-shrink-0`} />
      </div>

      {/* Run result feedback */}
      {runResult && (
        <div className={cn(
          "flex items-start gap-1.5 rounded-[6px] p-2",
          runResult.type === "success"
            ? "bg-[rgba(46,204,113,0.07)] border border-[rgba(46,204,113,0.18)]"
            : "bg-[rgba(231,76,60,0.07)] border border-[rgba(231,76,60,0.18)]"
        )}>
          {runResult.type === "success"
            ? <CheckCircle2 size={11} className="text-[hsl(var(--gc-green))] mt-0.5 flex-shrink-0" />
            : <AlertCircle  size={11} className="text-[hsl(var(--gc-red))]   mt-0.5 flex-shrink-0" />
          }
          <span style={{ fontSize: 11 }} className={runResult.type === "success" ? "text-[hsl(var(--gc-green))]" : "text-[hsl(var(--gc-red))]"}>
            {runResult.message}
          </span>
        </div>
      )}

      {/* Footer: last run + Run button */}
      <div className="flex items-center justify-between mt-1">
        <div className="flex items-center gap-1 text-[hsl(var(--gc-text-3))]" style={{ fontSize: 10 }}>
          <Clock size={10} />
          {agent.lastRun
            ? new Date(agent.lastRun).toLocaleString("en-IN", { dateStyle: "short", timeStyle: "short" })
            : "Never"
          }
        </div>
        <button
          onClick={() => onRun(agent.name)}
          disabled={isRunning || agent.status === "running"}
          className={cn(
            "flex items-center gap-1 px-3 py-1 rounded-[5px] transition-opacity",
            "disabled:opacity-40 disabled:cursor-not-allowed",
            agent.status === "running"
              ? "bg-[rgba(240,165,0,0.1)] border border-[rgba(240,165,0,0.3)] text-[hsl(var(--gc-amber))]"
              : "bg-[rgba(201,168,76,0.1)] border border-[rgba(201,168,76,0.25)] text-[hsl(var(--gc-gold))] hover:bg-[rgba(201,168,76,0.18)]"
          )}
          style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.3px" }}
        >
          {isRunning
            ? <Loader2 size={10} className="animate-spin" />
            : <Play    size={10} />
          }
          {isRunning ? "Starting" : agent.status === "running" ? "Running" : "Run"}
        </button>
      </div>
    </div>
  )
}
