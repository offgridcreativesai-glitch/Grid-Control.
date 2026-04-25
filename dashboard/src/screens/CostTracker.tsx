/**
 * CostTracker — GRID CONTROL
 * Screen 10 — Monthly spend dashboard per brand.
 * Shows Anthropic API cost, FAL.ai image cost, Apify scraping cost, total.
 */

import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { useBrandStore } from "@/store/brandStore"
import { apiFetch } from "@/lib/api"
import {
  DollarSign,
  Cpu,
  Image,
  Globe,
  TrendingUp,
  ChevronLeft,
  ChevronRight,
  RefreshCw,
  Play,
  AlertCircle,
} from "lucide-react"

const API = "http://localhost:5001"

// 1 USD = 85 INR (approximate — update periodically)
const USD_TO_INR = 85

// Fixed monthly subscriptions — update if plans change
const FIXED_COSTS = [
  { name: "Apify",      plan: "Starter",  usd: 29 },
  { name: "Make.com",   plan: "Core",     usd: 11 },
  { name: "Claude Pro", plan: "Pro",      usd: 20 },
]
const FIXED_TOTAL_USD = FIXED_COSTS.reduce((s, c) => s + c.usd, 0) // 60

// ── helpers ────────────────────────────────────────────────────────────────────

const MONTH_NAMES = [
  "Jan","Feb","Mar","Apr","May","Jun",
  "Jul","Aug","Sep","Oct","Nov","Dec",
]

function inr(usd: number) {
  const val = usd * USD_TO_INR
  if (val >= 1000) return `₹${val.toFixed(0)}`
  if (val >= 1)    return `₹${val.toFixed(2)}`
  return `₹${val.toFixed(4)}`
}

function fmtTokens(n: number) {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`
  if (n >= 1_000)     return `${(n / 1_000).toFixed(1)}K`
  return String(n)
}

// ── types ──────────────────────────────────────────────────────────────────────

interface AgentCost {
  agent_slug:      string
  runs:            number
  input_tokens:    number
  output_tokens:   number
  api_cost_usd:    number
  fal_cost_usd:    number
  apify_cost_usd:  number
  fal_generations: number
  apify_runs:      number
}

interface Totals {
  api_cost_usd:   number
  fal_cost_usd:   number
  apify_cost_usd: number
  total_usd:      number
  total_runs:     number
}

interface CostData {
  year:    number
  month:   number
  agents:  AgentCost[]
  totals:  Totals
}

// ── stat card ──────────────────────────────────────────────────────────────────

function StatCard({
  icon,
  label,
  value,
  sub,
}: {
  icon: React.ReactNode
  label: string
  value: string
  sub?: string
}) {
  return (
    <div className="gc-card p-4 space-y-3">
      <div className="flex items-center gap-2">
        <div className="w-7 h-7 rounded-lg gc-gold-bg border gc-gold-border flex items-center justify-center">
          {icon}
        </div>
        <span className="gc-label" style={{ fontSize: "10px" }}>{label}</span>
      </div>
      <p className="text-xl font-bold text-[hsl(var(--foreground))]">{value}</p>
      {sub && <p className="text-xs gc-muted">{sub}</p>}
    </div>
  )
}

// ── agent row ──────────────────────────────────────────────────────────────────

function AgentRow({ agent, totalUsd }: { agent: AgentCost; totalUsd: number }) {
  const total = agent.api_cost_usd + agent.fal_cost_usd + agent.apify_cost_usd
  const pct   = totalUsd > 0 ? (total / totalUsd) * 100 : 0
  const label = agent.agent_slug.replace(/-/g, " ").replace(/\b\w/g, c => c.toUpperCase())

  return (
    <div className="gc-card p-4 space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-semibold text-[hsl(var(--foreground))]">{label}</p>
          <p className="text-xs gc-muted">{agent.runs} run{agent.runs !== 1 ? "s" : ""} this month</p>
        </div>
        <div className="text-right">
          <p className="text-sm font-bold gc-gold">{inr(total)}</p>
          <p className="text-xs gc-muted">{pct.toFixed(1)}% of total</p>
        </div>
      </div>

      {/* Progress bar */}
      <div className="w-full h-1 rounded-full bg-[hsl(var(--gc-surface2))]">
        <div
          className="h-1 rounded-full bg-[hsl(var(--gc-gold))]"
          style={{ width: `${Math.min(pct, 100)}%` }}
        />
      </div>

      {/* Cost breakdown */}
      <div className="grid grid-cols-3 gap-2 text-xs">
        <div className="space-y-0.5">
          <p className="gc-muted">Claude API</p>
          <p className="text-[hsl(var(--foreground))] font-medium">{inr(agent.api_cost_usd)}</p>
          <p className="gc-dimmed">
            {fmtTokens(agent.input_tokens)} in / {fmtTokens(agent.output_tokens)} out
          </p>
        </div>
        <div className="space-y-0.5">
          <p className="gc-muted">FAL.ai</p>
          <p className="text-[hsl(var(--foreground))] font-medium">{inr(agent.fal_cost_usd)}</p>
          <p className="gc-dimmed">{agent.fal_generations} image{agent.fal_generations !== 1 ? "s" : ""}</p>
        </div>
        <div className="space-y-0.5">
          <p className="gc-muted">Apify</p>
          <p className="text-[hsl(var(--foreground))] font-medium">{inr(agent.apify_cost_usd)}</p>
          <p className="gc-dimmed">{agent.apify_runs} run{agent.apify_runs !== 1 ? "s" : ""}</p>
        </div>
      </div>
    </div>
  )
}

// ── main component ─────────────────────────────────────────────────────────────

export function CostTracker() {
  const { activeBrand } = useBrandStore()
  const now = new Date()
  const [year,  setYear]  = useState(now.getFullYear())
  const [month, setMonth] = useState(now.getMonth() + 1) // 1-indexed
  const [running, setRunning] = useState(false)
  const [runMsg,  setRunMsg]  = useState("")

  const { data, isLoading, isError, refetch } = useQuery<CostData>({
    queryKey: ["brand-costs", activeBrand.slug, year, month],
    queryFn:  async () => {
      const res = await apiFetch(
        `${API}/api/brands/${activeBrand.slug}/costs?year=${year}&month=${month}`
      )
      const json = await res.json()
      if (!json.success) throw new Error(json.error)
      return json.data
    },
    enabled: !!activeBrand.slug,
  })

  // Month navigation
  function prevMonth() {
    if (month === 1) { setMonth(12); setYear(y => y - 1) }
    else setMonth(m => m - 1)
  }
  function nextMonth() {
    const isCurrentMonth = year === now.getFullYear() && month === now.getMonth() + 1
    if (isCurrentMonth) return
    if (month === 12) { setMonth(1); setYear(y => y + 1) }
    else setMonth(m => m + 1)
  }
  const isCurrentMonth = year === now.getFullYear() && month === now.getMonth() + 1

  // Run cost tracker agent
  async function runCostTracker() {
    setRunning(true)
    setRunMsg("Running Cost Tracker agent...")
    try {
      const res = await apiFetch(`${API}/api/agents/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ agentName: "Cost Tracker", brand_slug: activeBrand.slug }),
      })
      const json = await res.json()
      if (json.success) {
        setRunMsg("Cost Tracker running — refresh in 30 seconds")
        setTimeout(() => { refetch(); setRunMsg("") }, 30000)
      } else {
        setRunMsg(`Error: ${json.error}`)
      }
    } catch (e) {
      setRunMsg("Failed to start agent")
    } finally {
      setRunning(false)
    }
  }

  const totals   = data?.totals
  const agents   = data?.agents ?? []
  const totalUsd = totals?.total_usd ?? 0

  return (
    <div className="h-full flex flex-col bg-[hsl(var(--background))]">

      {/* Topbar */}
      <div className="h-[52px] shrink-0 flex items-center justify-between px-6 border-b border-[hsl(var(--border))]">
        <div className="flex items-center gap-2 text-sm">
          <span className="gc-muted">GRID CONTROL</span>
          <span className="gc-dimmed">/</span>
          <span className="text-[hsl(var(--foreground))] font-medium">Cost Tracker</span>
          {activeBrand.name && (
            <>
              <span className="gc-dimmed">/</span>
              <span className="gc-muted">{activeBrand.name}</span>
            </>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={runCostTracker}
            disabled={running}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold bg-[hsl(var(--gc-gold))] text-black disabled:opacity-50 transition-opacity"
          >
            <Play size={12} />
            {running ? "Running..." : "Run Cost Tracker"}
          </button>
          <button
            onClick={() => refetch()}
            className="p-2 rounded-lg border border-[hsl(var(--border))] gc-muted hover:text-[hsl(var(--foreground))] transition-colors"
          >
            <RefreshCw size={14} />
          </button>
        </div>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto">
        <div className="p-6 space-y-5">

          {/* Run message */}
          {runMsg && (
            <div className="flex items-center gap-2 px-4 py-3 rounded-lg border gc-gold-border gc-gold-bg text-sm gc-gold">
              <AlertCircle size={14} />
              {runMsg}
            </div>
          )}

          {/* Month selector */}
          <div className="flex items-center gap-3">
            <button
              onClick={prevMonth}
              className="p-1.5 rounded-lg border border-[hsl(var(--border))] gc-muted hover:text-[hsl(var(--foreground))] transition-colors"
            >
              <ChevronLeft size={15} />
            </button>
            <span className="text-sm font-semibold text-[hsl(var(--foreground))] min-w-[110px] text-center">
              {MONTH_NAMES[month - 1]} {year}
            </span>
            <button
              onClick={nextMonth}
              disabled={isCurrentMonth}
              className="p-1.5 rounded-lg border border-[hsl(var(--border))] gc-muted hover:text-[hsl(var(--foreground))] disabled:opacity-30 transition-colors"
            >
              <ChevronRight size={15} />
            </button>
            {isCurrentMonth && (
              <span className="px-2 py-0.5 rounded text-[10px] font-bold gc-gold gc-gold-bg border gc-gold-border tracking-wider">
                CURRENT
              </span>
            )}
          </div>

          {/* Fixed monthly overhead — always visible */}
          <div className="gc-card p-4 space-y-3">
            <div className="flex items-center justify-between">
              <p className="gc-label" style={{ fontSize: "10px" }}>Fixed Monthly Overhead</p>
              <p className="text-[10px] gc-muted">Always incurred · independent of agent runs</p>
            </div>
            <div className="grid grid-cols-3 gap-3">
              {FIXED_COSTS.map(c => (
                <div key={c.name} className="space-y-0.5">
                  <p className="text-xs font-semibold text-[hsl(var(--foreground))]">{c.name}</p>
                  <p className="text-[10px] gc-muted">{c.plan} plan</p>
                  <p className="text-sm font-bold gc-gold">{inr(c.usd)}</p>
                  <p className="text-[10px] gc-dimmed">${c.usd}/mo</p>
                </div>
              ))}
            </div>
            <div className="pt-2 border-t border-[hsl(var(--border))] flex items-center justify-between">
              <span className="text-xs gc-muted">Fixed Total</span>
              <span className="text-sm font-bold gc-gold">{inr(FIXED_TOTAL_USD)}</span>
            </div>
          </div>

          {/* Loading / error */}
          {isLoading && (
            <div className="flex items-center justify-center h-40 gc-muted text-sm">
              Loading cost data...
            </div>
          )}
          {isError && (
            <div className="flex items-center justify-center h-40 text-[hsl(var(--gc-red))] text-sm">
              Failed to load costs. Make sure the API is running.
            </div>
          )}

          {data && (
            <>
              {/* Stat cards */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                <StatCard
                  icon={<DollarSign size={14} className="gc-gold" />}
                  label="Total Spend"
                  value={inr(totalUsd)}
                  sub={`${totals?.total_runs ?? 0} agent runs this month`}
                />
                <StatCard
                  icon={<Cpu size={14} className="gc-gold" />}
                  label="Claude API"
                  value={inr(totals?.api_cost_usd ?? 0)}
                  sub="Anthropic tokens"
                />
                <StatCard
                  icon={<Image size={14} className="gc-gold" />}
                  label="FAL.ai"
                  value={inr(totals?.fal_cost_usd ?? 0)}
                  sub="Image / video generations"
                />
                <StatCard
                  icon={<Globe size={14} className="gc-gold" />}
                  label="Apify"
                  value={inr(totals?.apify_cost_usd ?? 0)}
                  sub="Instagram scraping"
                />
              </div>

              {/* Grand total — fixed + variable */}
              <div className="rounded-lg gc-gold-bg border gc-gold-border px-4 py-3 flex items-center justify-between">
                <div>
                  <p className="gc-label" style={{ fontSize: "10px" }}>Grand Total This Month</p>
                  <p className="text-[10px] gc-muted mt-0.5">
                    Fixed {inr(FIXED_TOTAL_USD)} + Variable {inr(totalUsd)}
                  </p>
                </div>
                <p className="text-2xl font-bold gc-gold">{inr(FIXED_TOTAL_USD + totalUsd)}</p>
              </div>

              {/* Pricing reference */}
              <div className="gc-card p-4">
                <p className="gc-label mb-3" style={{ fontSize: "10px" }}>Pricing Reference</p>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                  <div>
                    <p className="text-[hsl(var(--foreground))] font-medium">Claude Sonnet 4-6</p>
                    <p className="gc-muted">₹255 / 1M in · ₹1,275 / 1M out</p>
                  </div>
                  <div>
                    <p className="text-[hsl(var(--foreground))] font-medium">Claude Opus 4-6</p>
                    <p className="gc-muted">₹1,275 / 1M in · ₹6,375 / 1M out</p>
                  </div>
                  <div>
                    <p className="text-[hsl(var(--foreground))] font-medium">FAL.ai</p>
                    <p className="gc-muted">~₹0.68 / image</p>
                  </div>
                  <div>
                    <p className="text-[hsl(var(--foreground))] font-medium">Apify</p>
                    <p className="gc-muted">~₹29.75 / actor run</p>
                  </div>
                </div>
              </div>

              {/* Per-agent breakdown */}
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <TrendingUp size={14} className="gc-gold" />
                  <p className="gc-label" style={{ fontSize: "11px" }}>Per-Agent Breakdown</p>
                </div>

                {agents.length === 0 ? (
                  <div className="gc-card p-8 text-center space-y-2">
                    <DollarSign size={28} className="mx-auto gc-muted" />
                    <p className="text-sm gc-muted">
                      No agent runs with cost data recorded for {MONTH_NAMES[month - 1]} {year}.
                    </p>
                    <p className="text-xs gc-dimmed">
                      Cost data is recorded automatically after each agent run. Run an agent to start tracking.
                    </p>
                  </div>
                ) : (
                  <div className="grid gap-3 md:grid-cols-2">
                    {agents.map(agent => (
                      <AgentRow key={agent.agent_slug} agent={agent} totalUsd={totalUsd} />
                    ))}
                  </div>
                )}
              </div>

              {/* n8n automation note */}
              <div className="gc-card p-4 space-y-1">
                <p className="text-xs font-semibold text-[hsl(var(--foreground))] uppercase tracking-widest">n8n Automation</p>
                <p className="text-xs gc-muted">
                  Trigger any agent automatically from n8n:
                  <code className="ml-1 px-1.5 py-0.5 rounded bg-[hsl(var(--gc-surface2))] gc-gold font-mono">
                    POST /api/webhooks/n8n
                  </code>
                  {" "}with body{" "}
                  <code className="px-1.5 py-0.5 rounded bg-[hsl(var(--gc-surface2))] gc-gold font-mono">
                    {`{ brand_slug, agent_name }`}
                  </code>
                </p>
              </div>
            </>
          )}

        </div>
      </div>
    </div>
  )
}
