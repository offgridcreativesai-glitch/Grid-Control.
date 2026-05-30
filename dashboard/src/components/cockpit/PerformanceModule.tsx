/**
 * Performance Snapshot — ported from performance.jsx, wired to real data.
 *
 * Real data only (Rule 1): NO fabricated metrics. If Meta isn't connected we show the
 * connect card. If connected but no posts tracked yet, a calm syncing strip. Once posts
 * exist we surface real integer counts (posts tracked, winning/dead patterns). Rich
 * reach/engagement tiles light up when META_GRAPH_API_TOKEN lands (documented pending item).
 */
import { useNavigate } from "react-router-dom"
import { Link2, Check } from "lucide-react"
import { usePerformanceHistory, useConnections } from "@/hooks/useGridApi"
import { Card, ModuleHeader, PrimaryButton, STATUS } from "./primitives"

function StatTile({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-xl border border-white/[0.06] bg-white/[0.015] p-4">
      <span className="font-mono text-[10.5px] uppercase tracking-[0.14em] text-zinc-500">
        {label}
      </span>
      <div className="mt-3 flex items-baseline gap-2">
        <span className="text-[22px] font-semibold tracking-tight text-zinc-100 tabular-nums">
          {value}
        </span>
      </div>
    </div>
  )
}

export function PerformanceModule() {
  const navigate = useNavigate()
  const { data: perf } = usePerformanceHistory()
  const { data: conn } = useConnections()

  const metaConnected = !!conn?.data?.meta?.connected
  const history: any = perf as any
  const posts: any[] = history?.posts ?? []
  const winning = Object.keys(history?.winning_patterns ?? {}).length
  const dead = (history?.dead_patterns ?? []).length
  const hasTracked = posts.length > 0

  return (
    <Card className="flex h-full flex-col p-6">
      <ModuleHeader title="Performance Snapshot" sub="Live account metrics" />

      <div className="mt-5 flex-1">
        {!metaConnected ? (
          <div className="flex h-full flex-col items-center justify-center rounded-xl border border-dashed border-white/[0.1] bg-white/[0.012] px-6 py-10 text-center">
            <div className="grid h-10 w-10 place-items-center rounded-full border border-white/[0.08] bg-white/[0.02] text-zinc-500">
              <Link2 size={18} />
            </div>
            <p className="mt-3.5 text-[13.5px] font-medium text-zinc-200">
              Connect Meta to see live performance
            </p>
            <p className="mt-1 text-[12px] text-zinc-500">
              Reach, engagement and saves will appear here once linked.
            </p>
            <div className="mt-4">
              <PrimaryButton icon={Link2} onClick={() => navigate("/onboarding")}>
                Connect Meta
              </PrimaryButton>
            </div>
          </div>
        ) : !hasTracked ? (
          <div
            className="flex items-center gap-2.5 rounded-xl border px-4 py-3.5"
            style={{ borderColor: STATUS.green.bd, background: STATUS.green.bg }}
          >
            <Check size={16} style={{ color: STATUS.green.fg }} />
            <span className="text-[13px] font-medium" style={{ color: STATUS.green.fg }}>
              Meta connected — no posts tracked yet. Metrics appear after your first published post.
            </span>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-3 gap-3">
              <StatTile label="Posts tracked" value={posts.length} />
              <StatTile label="Winning patterns" value={winning} />
              <StatTile label="Dead patterns" value={dead} />
            </div>
            <p className="mt-4 text-[12px] leading-relaxed text-zinc-500">
              Reach / engagement / saves tiles populate from the Meta Graph API once the access
              token is configured.
            </p>
          </>
        )}
      </div>
    </Card>
  )
}
