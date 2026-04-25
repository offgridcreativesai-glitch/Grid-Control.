import { cn } from "@/lib/utils"
import { Play, Loader2, Clock, CheckCircle2, AlertCircle } from "lucide-react"
import type { Agent, AgentStatus } from "@/types"

const STATUS: Record<AgentStatus, { dot: string; label: string }> = {
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

interface CEOBrainCardProps {
  agent: Agent
  onRun: (agentName: string) => void
  isRunning: boolean
  runResult?: RunResult
}

export function CEOBrainCard({ agent, onRun, isRunning, runResult }: CEOBrainCardProps) {
  const s = STATUS[agent.status] ?? STATUS.idle

  return (
    <div
      className="gc-card flex items-center gap-5 p-4"
      style={{
        background: "linear-gradient(135deg, rgba(201,168,76,0.08) 0%, hsl(var(--gc-surface)) 100%)",
        borderColor: "rgba(201,168,76,0.2)",
      }}
    >
      {/* Icon */}
      <div
        className="flex items-center justify-center rounded-[10px] flex-shrink-0 text-2xl"
        style={{
          width: 48, height: 48,
          background: "rgba(201,168,76,0.12)",
          border: "1px solid rgba(201,168,76,0.25)",
        }}
      >
        🧠
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-3 mb-1">
          <span style={{ fontSize: 15, fontWeight: 700 }} className="text-[hsl(var(--foreground))]">{agent.name}</span>
          {/* Status dot + label */}
          <div className="flex items-center gap-1.5">
            <div className={`status-dot ${s.dot}`} />
            <span style={{ fontSize: 11, fontWeight: 600 }} className="text-[hsl(var(--gc-text-2))]">{s.label}</span>
          </div>
          {/* Model pill */}
          <span
            style={{ fontSize: 10, padding: "2px 8px", borderRadius: 4 }}
            className="text-[hsl(var(--gc-text-2))] bg-[hsl(var(--gc-surface2))] border border-[hsl(var(--border))]"
          >
            {agent.model}
          </span>
        </div>

        <p style={{ fontSize: 13 }} className="text-[hsl(var(--gc-text-2))]">
          {agent.role} — Orchestrates the full team. Routes tasks. Enforces approval gates.
        </p>

        {agent.lastRun && (
          <div className="flex items-center gap-1 mt-2 text-[hsl(var(--gc-text-3))]" style={{ fontSize: 11 }}>
            <Clock size={11} />
            Last run: {new Date(agent.lastRun).toLocaleString("en-IN", { dateStyle: "short", timeStyle: "short" })}
          </div>
        )}

        {runResult && (
          <div className={cn(
            "flex items-center gap-1.5 mt-2",
            runResult.type === "success" ? "text-[hsl(var(--gc-green))]" : "text-[hsl(var(--gc-red))]"
          )} style={{ fontSize: 12 }}>
            {runResult.type === "success"
              ? <CheckCircle2 size={12} className="flex-shrink-0" />
              : <AlertCircle  size={12} className="flex-shrink-0" />
            }
            {runResult.message}
          </div>
        )}
      </div>

      {/* Run button */}
      <button
        onClick={() => onRun(agent.name)}
        disabled={isRunning || agent.status === "running"}
        className="flex items-center gap-2 px-5 py-2 rounded-[6px] flex-shrink-0 transition-opacity disabled:opacity-40 disabled:cursor-not-allowed bg-[hsl(var(--gc-gold))] hover:opacity-85"
        style={{ fontSize: 11, fontWeight: 800, letterSpacing: 1, textTransform: "uppercase", color: "#000" }}
      >
        {isRunning
          ? <Loader2 size={12} className="animate-spin" />
          : <Play    size={12} />
        }
        {isRunning ? "Starting…" : "Run CEO Brain"}
      </button>
    </div>
  )
}
