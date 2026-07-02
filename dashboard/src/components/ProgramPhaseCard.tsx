/**
 * ProgramPhaseCard — Stage 1 of the proactive weekly operating program
 * (GRIDLOCK-PROGRAM-01JUL). Replaces FirstTaskCard as the post-brand-book
 * handoff: instead of 3 generic buttons, the brand lands on a named phase
 * (foundation/launch/growth/scale) with a phase-appropriate plan.
 *
 * "Start my weekly program" sends a chat prompt (same handoff pattern as the
 * old FirstTaskCard) — Stage 2/3 wire the real automated weekly review/build
 * chains; today Atlas answers from context.
 *
 * Self-gates on status==="approved" + a per-brand "done" flag so it doesn't nag.
 */
import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { Sparkles, ArrowRight, X } from "lucide-react"
import { apiFetch } from "@/lib/api"
import { useBrandStore } from "@/store/brandStore"

type PhasePlan = {
  label: string
  monthly_rev_range: string
  goal: string
  content_ads_ratio: string | null
  weekly_volume: { long_form: number; social: number; creator_seeds: number }
  active_agents: string[]
}

export function ProgramPhaseCard({ onStartTask }: { onStartTask: (text: string) => void }) {
  const { activeBrand } = useBrandStore()
  const slug = activeBrand.slug
  const flagKey = `gc_program_phase_done_${slug}`
  const [dismissed, setDismissed] = useState<boolean>(() => {
    try { return localStorage.getItem(flagKey) === "1" } catch { return false }
  })

  const { data: bb } = useQuery({
    queryKey: ["brand-book", slug],
    enabled: !!slug,
    queryFn: async () => (await (await apiFetch(`/api/brands/${slug}/brand-book`)).json()),
  })
  const status: string = bb?.data?.status ?? "none"

  const { data: summary } = useQuery({
    queryKey: ["brand-summary-phase", slug],
    enabled: !!slug && status === "approved",
    queryFn: async () => (await (await apiFetch(`/api/brand/summary?brand_slug=${slug}`)).json()),
  })
  const phase: string = summary?.data?.program_phase ?? "launch"
  const plan: PhasePlan | undefined = summary?.data?.program_phase_plan

  if (!slug || status !== "approved" || dismissed) return null

  const done = () => { try { localStorage.setItem(flagKey, "1") } catch { /* ignore */ }; setDismissed(true) }
  const start = () => {
    onStartTask(
      `Start my weekly program. I'm in the ${plan?.label ?? phase} phase — walk me through what happens each week.`
    )
    done()
  }

  return (
    <div className="glass-panel mt-7 overflow-hidden rounded-2xl border border-emerald/40">
      <div className="flex items-center justify-between gap-2 border-b border-border px-4 py-3">
        <span className="flex items-center gap-2">
          <Sparkles size={16} className="text-emerald" />
          <span className="text-[13.5px] font-semibold text-foreground">
            You&rsquo;re on the {plan?.label ?? "Launch"} phase
          </span>
        </span>
        <button onClick={done} className="text-muted-foreground transition-colors hover:text-foreground" aria-label="Dismiss">
          <X size={15} />
        </button>
      </div>
      <div className="p-4">
        <p className="text-[13px] leading-relaxed text-muted-foreground">
          {plan?.goal ?? "Organic traction + social proof."}
          {plan?.content_ads_ratio && (
            <> Content : ads mix for this phase is <span className="text-foreground">{plan.content_ads_ratio}</span>.</>
          )}
        </p>
        {plan?.weekly_volume && (
          <div className="mt-3 flex flex-wrap gap-2 text-[11.5px] text-muted-foreground">
            <span className="rounded-full border border-border px-2.5 py-1">{plan.weekly_volume.long_form}/wk long-form</span>
            <span className="rounded-full border border-border px-2.5 py-1">{plan.weekly_volume.social}/wk social</span>
            {plan.weekly_volume.creator_seeds > 0 && (
              <span className="rounded-full border border-border px-2.5 py-1">{plan.weekly_volume.creator_seeds}/mo creator seeds</span>
            )}
          </div>
        )}
        <button
          onClick={start}
          className="group mt-4 flex w-full items-center justify-between gap-3 rounded-xl border border-border bg-white/[0.02] px-4 py-3 text-left transition-colors hover:border-primary/50 hover:bg-white/[0.04]"
        >
          <span className="text-[13.5px] font-medium text-foreground">Start my weekly program</span>
          <ArrowRight size={15} className="shrink-0 text-muted-foreground transition-transform group-hover:translate-x-0.5 group-hover:text-primary" />
        </button>
        <button onClick={done} className="mt-3 text-[12px] text-muted-foreground underline-offset-2 hover:text-foreground hover:underline">
          I&rsquo;ll explore on my own
        </button>
      </div>
    </div>
  )
}
