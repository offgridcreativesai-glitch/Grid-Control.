/**
 * Your Team — the 8-strong client-facing cast (route "/team").
 *
 * THE SECRET: the owner sees eight named specialists, never the 18-agent backend.
 * Live status maps every running backend agent onto its persona (deduped).
 * No slugs / models / cost / tokens.
 */
import { useMemo } from "react"
import { useNavigate } from "react-router-dom"
import { ArrowRight } from "lucide-react"
import { AgentCharacter, AGENTS as AGENT_INFO, type AgentKey } from "@/components/AgentCharacter"
import { CAST, personaForSlug } from "@/lib/agentPersona"
import { useLiveAgents } from "@/hooks/useGridApi"
import { relativeTime } from "@/lib/cockpitFormat"

export function CrewPage() {
  const navigate = useNavigate()
  const live = useLiveAgents()

  // Roll the 18-agent live status up onto the 8 personas.
  const { running, lastRun } = useMemo(() => {
    const running = new Set<AgentKey>()
    const lastRun = new Map<AgentKey, Date>()
    for (const a of live) {
      const key = personaForSlug(a.slug).key
      if (a.status === "running") running.add(key)
      if (a.lastRun) {
        const cur = lastRun.get(key)
        if (!cur || a.lastRun > cur) lastRun.set(key, a.lastRun)
      }
    }
    return { running, lastRun }
  }, [live])

  const workingCount = running.size

  return (
    <div className="min-h-full bg-background/60">
      <div className="mx-auto max-w-[1100px] px-6 pb-20 pt-10">
        {/* Header */}
        <div className="flex items-end justify-between gap-6">
          <div>
            <h1 className="font-display text-[26px] font-semibold tracking-tight text-foreground">Your team</h1>
            <p className="mt-1.5 text-[14px] text-muted-foreground">
              Eight specialists. Atlas runs the room and keeps every move on plan.
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-2 rounded-full border border-border bg-white/[0.02] px-3.5 py-2">
            <span
              className="h-2 w-2 rounded-full"
              style={{ background: workingCount > 0 ? "var(--emerald)" : "var(--status-blocked)" }}
            />
            <span className="text-[12px] font-medium text-foreground/80">
              {workingCount > 0 ? `${workingCount} working now` : "All standing by"}
            </span>
          </div>
        </div>

        {/* Cast grid */}
        <div className="mt-9 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {CAST.map((p) => {
            const info = AGENT_INFO[p.key]
            const isWorking = running.has(p.key)
            const seen = lastRun.get(p.key)
            return (
              <div
                key={p.key}
                className="glass-panel relative flex flex-col items-center rounded-2xl px-5 pb-5 pt-7 text-center"
                style={info.lead ? { borderColor: "rgba(255,77,0,0.32)" } : undefined}
              >
                {info.lead && (
                  <span className="absolute right-3 top-3 rounded-full border border-primary/40 bg-primary/[0.08] px-2 py-0.5 text-[9.5px] font-semibold uppercase tracking-[0.14em] text-primary">
                    Lead
                  </span>
                )}

                <AgentCharacter agent={p.key} size="md" parallax isActive={isWorking} showGlow={info.lead} />

                <p className="mt-3 font-display text-[16px] font-semibold tracking-tight text-foreground">{p.name}</p>
                <p className="text-[12px] font-medium text-emerald">{p.role}</p>
                <p className="mt-2 text-[12.5px] leading-relaxed text-muted-foreground">{info.blurb}</p>

                <div className="mt-3 flex items-center gap-1.5">
                  <span
                    className="h-1.5 w-1.5 rounded-full"
                    style={{ background: isWorking ? "var(--emerald)" : "var(--status-blocked)" }}
                  />
                  <span className="text-[11px] text-foreground/70">
                    {isWorking
                      ? p.action.replace(/^is /, "Working — ")
                      : seen
                        ? `Last active ${relativeTime(seen.getTime())}`
                        : "Standing by"}
                  </span>
                </div>
              </div>
            )
          })}
        </div>

        {/* Footer CTA — the owner directs the team through Atlas, not 1:1 */}
        <div className="mt-9 flex items-center justify-between rounded-2xl border border-border bg-white/[0.02] px-6 py-5">
          <div>
            <p className="text-[14px] font-semibold text-foreground">Want to put the team on something?</p>
            <p className="mt-0.5 text-[12.5px] text-muted-foreground">
              Tell Atlas what you need — he briefs the right specialists.
            </p>
          </div>
          <button
            onClick={() => navigate("/command")}
            className="inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-[13px] font-semibold text-primary-foreground transition-[filter] hover:brightness-110"
          >
            Talk to Atlas <ArrowRight size={15} />
          </button>
        </div>
      </div>
    </div>
  )
}
