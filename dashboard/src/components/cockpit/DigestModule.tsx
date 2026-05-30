/**
 * Daily Intelligence Digest — the cockpit hero.
 * Ported from digest.jsx, wired to the real /api/digest endpoint.
 *
 * Real data only (Rule 1): the verdict badge renders ONLY when Trend Sentinel has
 * written a real PIVOT/TRACK/STAY decision. No verdict → calm pending state.
 * Flags come from contradictions.json findings, rendered human-readable — never raw JSON.
 */
import { Compass, RefreshCw, TriangleAlert } from "lucide-react"
import { useDigest, useRunDailyPipeline, type DigestData } from "@/hooks/useGridApi"
import { Card, Eyebrow, ModuleHeader, STATUS, VERDICT_TONE } from "./primitives"
import { relativeTime } from "@/lib/cockpitFormat"

function VerdictBadge({ verdict, reason }: { verdict: "PIVOT" | "TRACK" | "STAY"; reason: string }) {
  const s = STATUS[VERDICT_TONE[verdict]]
  return (
    <div className="rounded-xl border p-4" style={{ borderColor: s.bd, background: s.bg }}>
      <div className="flex items-center gap-3">
        <span
          className="font-mono text-[26px] font-semibold leading-none tracking-tight"
          style={{ color: s.fg }}
        >
          {verdict}
        </span>
        <span className="font-mono text-[10.5px] uppercase tracking-[0.16em] text-zinc-500">
          today&rsquo;s verdict
        </span>
      </div>
      {reason && <p className="mt-2.5 text-[13.5px] leading-relaxed text-zinc-300">{reason}</p>}
    </div>
  )
}

function ScoreChip({ score }: { score: number }) {
  const strong = score >= 0.8
  return (
    <span
      className="shrink-0 rounded-md px-1.5 py-0.5 font-mono text-[11px] tabular-nums"
      style={{
        color: strong ? "#cdd3da" : "#9aa0a8",
        background: "rgba(255,255,255,0.05)",
        border: "1px solid rgba(255,255,255,0.07)",
      }}
    >
      {score.toFixed(2)}
    </span>
  )
}

/** Render a contradiction finding as one human-readable line (never raw JSON). */
function flagText(f: any): string {
  if (typeof f === "string") return f
  if (!f || typeof f !== "object") return ""
  return f.evidence || f.proposed_fix || f.message || f.summary || f.rule_id || "Flagged finding"
}

export function DigestModule() {
  const { data, isLoading, isError } = useDigest()
  const runPipeline = useRunDailyPipeline()
  const running = runPipeline.isPending

  const RunButton = ({ subtle = false }: { subtle?: boolean }) => (
    <button
      onClick={() => runPipeline.mutate()}
      disabled={running}
      className={
        "inline-flex items-center gap-1.5 text-[12.5px] font-medium transition-colors disabled:opacity-50 " +
        (subtle ? "text-zinc-300 hover:text-white" : "text-zinc-400 hover:text-zinc-100")
      }
    >
      <RefreshCw size={14} className={running ? "animate-spin" : ""} />
      {running ? "Running pipeline…" : "Run daily pipeline"}
    </button>
  )

  const d: DigestData | undefined = data
  const dateline = d?.last_pipeline_run
    ? `Updated ${relativeTime(d.last_pipeline_run)}`
    : "No pipeline run yet"

  const trends = (d?.trends ?? []).filter((t) => t.title)
  const findings = d?.contradictions?.findings ?? []
  const empty = !isLoading && !isError && d && !d.has_data && !d.verdict

  return (
    <Card className="flex h-full flex-col p-6">
      <ModuleHeader
        title="Daily Intelligence Digest"
        sub={dateline}
        right={<Eyebrow className="mt-1">hero</Eyebrow>}
      />

      {isLoading ? (
        <div className="flex flex-1 items-center justify-center py-14 text-[13px] text-zinc-500">
          Loading intelligence…
        </div>
      ) : isError ? (
        <div className="flex flex-1 flex-col items-center justify-center py-14 text-center">
          <p className="max-w-[34ch] text-[13.5px] leading-relaxed text-zinc-400">
            Couldn&rsquo;t load the digest. Check the API connection.
          </p>
        </div>
      ) : empty ? (
        <div className="flex flex-1 flex-col items-center justify-center py-14 text-center">
          <div className="flex h-11 w-11 items-center justify-center rounded-full border border-white/[0.08] bg-white/[0.02] text-zinc-500">
            <Compass size={20} />
          </div>
          <p className="mt-4 max-w-[34ch] text-[13.5px] leading-relaxed text-zinc-400">
            No new intelligence yet — run the daily pipeline to populate.
          </p>
          <div className="mt-4">
            <RunButton subtle />
          </div>
        </div>
      ) : (
        <>
          <div className="mt-5">
            {d?.verdict ? (
              <VerdictBadge verdict={d.verdict} reason={d.verdict_reason} />
            ) : (
              <div className="rounded-xl border border-white/[0.07] bg-white/[0.015] p-4">
                <span className="font-mono text-[10.5px] uppercase tracking-[0.16em] text-zinc-500">
                  verdict pending
                </span>
                <p className="mt-2 text-[13px] leading-relaxed text-zinc-400">
                  Trend Sentinel hasn&rsquo;t issued a STAY/TRACK/PIVOT call yet. Run the daily
                  pipeline to generate one.
                </p>
              </div>
            )}
          </div>

          {trends.length > 0 && (
            <div className="mt-6">
              <Eyebrow>New trends</Eyebrow>
              <ul className="mt-3 space-y-px">
                {trends.map((t, i) => (
                  <li
                    key={i}
                    className="flex items-center justify-between gap-4 rounded-lg px-2 py-2 transition-colors hover:bg-white/[0.03]"
                  >
                    <span className="truncate text-[13px] text-zinc-300">{t.title}</span>
                    {typeof t.relevance === "number" && <ScoreChip score={t.relevance} />}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {findings.length > 0 && (
            <div className="mt-6">
              <Eyebrow>Flags</Eyebrow>
              <ul className="mt-3 space-y-2">
                {findings.map((f, i) => (
                  <li key={i} className="flex items-start gap-2.5">
                    <TriangleAlert
                      size={14}
                      className="mt-[2px] shrink-0"
                      style={{ color: STATUS.red.fg }}
                    />
                    <span className="text-[12.5px] leading-relaxed text-zinc-400">
                      {flagText(f)}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="mt-auto flex items-center justify-end border-t border-white/[0.06] pt-4">
            <RunButton />
          </div>
        </>
      )}
    </Card>
  )
}
