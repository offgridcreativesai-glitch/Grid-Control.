/**
 * All Brands — the owner-only control tower (route "/brands", super-admin gated).
 * Sits ABOVE the per-brand cockpits. Lists every brand the operator runs; clicking a
 * card selects that brand and drills into its cockpit ("/").
 *
 * Real data only: each card reads that brand's real /api/digest (verdict, trend count,
 * last run) and pending count. System health shows the real API status; deeper system
 * instrumentation lives on /admin/system (no fabricated deploy/error tiles here).
 */
import { useNavigate } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { ListChecks, ArrowRight, Activity } from "lucide-react"
import { apiFetch } from "@/lib/api"
import { useBrandStore, type Brand } from "@/store/brandStore"
import { useBrands, useAgentStatus, type DigestData } from "@/hooks/useGridApi"
import {
  CockpitRoot,
  Card,
  Eyebrow,
  STATUS,
  VerdictPill,
  StatusDot,
} from "@/components/cockpit/primitives"
import { relativeTime, brandMark } from "@/lib/cockpitFormat"

interface BrandSummary {
  digest?: DigestData
  pending: number
}

function useBrandSummary(slug: string) {
  return useQuery({
    queryKey: ["brand-summary", slug],
    queryFn: async (): Promise<BrandSummary> => {
      const [dRes, pRes] = await Promise.all([
        apiFetch(`/api/digest?brand_slug=${encodeURIComponent(slug)}`).then((r) => r.json()),
        apiFetch(`/api/outputs/pending?brand_slug=${encodeURIComponent(slug)}`).then((r) => r.json()),
      ])
      const pendingRaw: any[] = pRes?.data || []
      const pending = pendingRaw.filter(
        (it) => it.filename && !it.filename.startsWith(".") && !it.filename.endsWith(".DS_Store"),
      ).length
      return { digest: dRes?.data, pending }
    },
    staleTime: 30_000,
  })
}

function ApiHealth() {
  const { data } = useQuery({
    queryKey: ["api-health"],
    queryFn: () => apiFetch("/api/health").then((r) => r.json()).catch(() => null),
    staleTime: 30_000,
    retry: false,
  })
  const ok = data?.success === true
  const s = ok ? STATUS.green : STATUS.red
  return (
    <div className="mb-7 flex items-center justify-between border-b border-white/[0.06] pb-7">
      <div className="flex items-center gap-2">
        <Eyebrow>System health</Eyebrow>
        <span className="font-mono text-[10px] text-zinc-700">· read-only</span>
      </div>
      <div className="flex items-center gap-3">
        <div
          className="flex items-center gap-2.5 rounded-xl border px-3.5 py-2"
          style={{ borderColor: s.bd, background: s.bg }}
        >
          <Activity size={14} style={{ color: s.fg }} />
          <span className="text-[12.5px] font-medium" style={{ color: s.fg }}>
            API {ok ? "operational" : "unreachable"}
          </span>
        </div>
        <a
          href="/admin/system"
          className="font-mono text-[11px] text-zinc-500 transition-colors hover:text-zinc-300"
        >
          Full system status →
        </a>
      </div>
    </div>
  )
}

function BrandCard({ brand, onOpen }: { brand: Brand; onOpen: () => void }) {
  const { data } = useBrandSummary(brand.slug)
  const verdict = data?.digest?.verdict ?? null
  const trends = data?.digest?.trends?.length ?? 0
  const lastRun = data?.digest?.last_pipeline_run
  const blocked = !!data?.digest?.contradictions?.blocking
  const pending = data?.pending ?? 0

  const tone: keyof typeof STATUS = blocked ? "red" : pending >= 5 ? "amber" : "green"
  const healthLabel = blocked ? "Blocked" : pending >= 5 ? "Attention" : "Healthy"

  return (
    <button
      onClick={onOpen}
      className="group flex flex-col rounded-2xl border border-white/[0.07] bg-[#141518] p-5 text-left transition-colors hover:border-white/[0.16] hover:bg-[#17181c]"
      style={{ boxShadow: "0 8px 24px -16px rgba(0,0,0,0.6)" }}
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <span
            className="grid h-9 w-9 place-items-center rounded-lg text-[14px] font-semibold text-zinc-100"
            style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.08)" }}
          >
            {brandMark(brand.name)}
          </span>
          <div>
            <div className="text-[14.5px] font-semibold tracking-tight text-zinc-100">
              {brand.name}
            </div>
            <div className="mt-1 inline-flex items-center gap-2">
              <StatusDot tone={tone} pulse={tone === "red"} />
              <span className="text-[12.5px] font-medium" style={{ color: STATUS[tone].fg }}>
                {healthLabel}
              </span>
            </div>
          </div>
        </div>
        {verdict && <VerdictPill verdict={verdict} />}
      </div>

      <div className="mt-5 grid grid-cols-3 gap-3 border-t border-white/[0.06] pt-4">
        <MiniStat label="Pending" value={pending} strong={pending >= 5} />
        <MiniStat label="Trends" value={`${trends} new`} />
        <MiniStat label="Last run" value={lastRun ? relativeTime(lastRun) : "—"} />
      </div>

      <div className="mt-5 flex items-center gap-1.5 text-[12.5px] font-medium text-zinc-500 transition-colors group-hover:text-zinc-200">
        Open cockpit
        <ArrowRight size={14} className="transition-transform group-hover:translate-x-0.5" />
      </div>
    </button>
  )
}

function MiniStat({ label, value, strong }: { label: string; value: string | number; strong?: boolean }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-zinc-600">{label}</span>
      <span
        className={
          "text-[13px] tabular-nums " +
          (strong ? "font-semibold text-zinc-100" : "font-medium text-zinc-300")
        }
      >
        {value}
      </span>
    </div>
  )
}

function SummaryItem({
  icon: I,
  value,
  label,
  tone,
}: {
  icon: typeof ListChecks
  value: number
  label: string
  tone?: keyof typeof STATUS
}) {
  const s = tone ? STATUS[tone] : null
  return (
    <div className="flex items-center gap-2.5">
      <span
        className="grid h-8 w-8 place-items-center rounded-lg"
        style={{
          background: s ? s.bg : "rgba(255,255,255,0.04)",
          border: "1px solid " + (s ? s.bd : "rgba(255,255,255,0.07)"),
        }}
      >
        <I size={15} style={{ color: s ? s.fg : "#9aa0a8" }} />
      </span>
      <div className="leading-tight">
        <div className="text-[15px] font-semibold tabular-nums" style={{ color: s ? s.fg : "#e4e4e7" }}>
          {value}
        </div>
        <div className="font-mono text-[10.5px] uppercase tracking-[0.12em] text-zinc-600">
          {label}
        </div>
      </div>
    </div>
  )
}

export function AllBrandsPage() {
  const navigate = useNavigate()
  const { data } = useBrands()
  const { setActiveBrand } = useBrandStore()
  const { data: agentStatus } = useAgentStatus()

  const brands: Brand[] = (data?.brands ?? []).map((b) => ({
    slug: b.slug,
    name: b.name,
    handle: b.handle,
  }))
  const runningAgents = agentStatus?.agents?.filter((a) => a.status === "running").length ?? 0

  const open = (b: Brand) => {
    setActiveBrand(b)
    navigate("/")
  }

  return (
    <CockpitRoot>
      <div className="mx-auto max-w-[1240px] px-6 pb-20 pt-8">
        <ApiHealth />

        <div className="flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h1 className="text-[26px] font-semibold tracking-tight text-zinc-100">All Brands</h1>
            <p className="mt-1.5 font-mono text-[11.5px] text-zinc-500">
              Control tower · zoomed out across every brand you operate
            </p>
          </div>
          <div className="flex items-center gap-6 rounded-2xl border border-white/[0.07] bg-[#141518] px-5 py-3">
            <SummaryItem icon={ListChecks} value={brands.length} label="Brands" />
            <div className="h-9 w-px bg-white/[0.06]" />
            <SummaryItem icon={Activity} value={runningAgents} label="Agents running" tone="blue" />
          </div>
        </div>

        {brands.length === 0 ? (
          <Card className="mt-8 p-10 text-center">
            <p className="text-[13.5px] text-zinc-400">
              No brands yet. Onboard your first brand to populate the control tower.
            </p>
          </Card>
        ) : (
          <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {brands.map((b) => (
              <BrandCard key={b.slug} brand={b} onOpen={() => open(b)} />
            ))}
          </div>
        )}
      </div>
    </CockpitRoot>
  )
}
