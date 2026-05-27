import { Loader2, Building2, Users, CreditCard, Cpu, TrendingUp, DollarSign, Activity } from "lucide-react"
import { cn } from "@/lib/utils"
import { useAdminOverview } from "@/hooks/useAdmin"

function KpiCard({
  label,
  value,
  sub,
  icon: Icon,
  color = "text-primary",
}: {
  label: string
  value: string
  sub?: string
  icon: typeof Building2
  color?: string
}) {
  return (
    <div className="rounded-lg border border-border bg-card p-5">
      <div className="flex items-center justify-between mb-3">
        <p className="text-xs text-muted-foreground">{label}</p>
        <Icon className={cn("h-4 w-4", color)} />
      </div>
      <p className="text-2xl font-semibold font-mono">{value}</p>
      {sub && <p className="text-xs text-muted-foreground mt-1">{sub}</p>}
    </div>
  )
}

export function AdminOverviewPage() {
  const { data, isLoading, isError } = useAdminOverview()

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (isError || !data) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-sm text-destructive">Failed to load admin data</p>
      </div>
    )
  }

  const agentEntries = Object.entries(data.agent_breakdown)
    .sort((a, b) => b[1].cost_usd - a[1].cost_usd)

  const brandEntries = Object.entries(data.brand_costs)
    .sort((a, b) => b[1].cost_usd - a[1].cost_usd)

  return (
    <div className="p-6 space-y-6 overflow-auto h-full">
      <div>
        <h1 className="text-lg font-semibold">Admin — Business Overview</h1>
        <p className="text-xs text-muted-foreground mt-1">Grid Control owner dashboard</p>
      </div>

      {/* KPI Grid */}
      <div className="grid grid-cols-4 gap-4">
        <KpiCard
          label="Total Brands"
          value={String(data.total_brands)}
          icon={Building2}
        />
        <KpiCard
          label="Active Subscriptions"
          value={String(data.active_subscriptions)}
          icon={Users}
          color="text-blue-400"
        />
        <KpiCard
          label="MRR"
          value={`₹${data.mrr_inr.toLocaleString("en-IN")}`}
          icon={CreditCard}
          color="text-green-400"
        />
        <KpiCard
          label="Agent Cost (this month)"
          value={`$${data.total_cost_usd.toFixed(2)}`}
          sub={`${data.total_runs_this_month} runs`}
          icon={DollarSign}
          color="text-orange-400"
        />
      </div>

      {/* Revenue vs Cost */}
      <div className="grid grid-cols-3 gap-4">
        <div className="rounded-lg border border-border bg-card p-5">
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp className="h-4 w-4 text-green-400" />
            <p className="text-xs text-muted-foreground">Month Revenue</p>
          </div>
          <p className="text-xl font-semibold font-mono">₹{data.month_revenue_inr.toLocaleString("en-IN")}</p>
        </div>
        <div className="rounded-lg border border-border bg-card p-5">
          <div className="flex items-center gap-2 mb-2">
            <Cpu className="h-4 w-4 text-orange-400" />
            <p className="text-xs text-muted-foreground">Month API Spend</p>
          </div>
          <p className="text-xl font-semibold font-mono">${data.total_cost_usd.toFixed(2)}</p>
        </div>
        <div className="rounded-lg border border-border bg-card p-5">
          <div className="flex items-center gap-2 mb-2">
            <Activity className="h-4 w-4 text-primary" />
            <p className="text-xs text-muted-foreground">Profit Margin</p>
          </div>
          <p className={cn(
            "text-xl font-semibold font-mono",
            data.profit_margin_pct >= 0 ? "text-green-400" : "text-destructive"
          )}>
            {data.profit_margin_pct > 0 ? "+" : ""}{data.profit_margin_pct}%
          </p>
        </div>
      </div>

      {/* Cost Breakdowns */}
      <div className="grid grid-cols-2 gap-6">
        {/* By Agent */}
        <div className="rounded-lg border border-border bg-card p-4">
          <h3 className="text-sm font-medium mb-3">Cost by Agent</h3>
          {agentEntries.length === 0 ? (
            <p className="text-xs text-muted-foreground italic">No agent runs yet</p>
          ) : (
            <div className="space-y-2">
              {agentEntries.map(([slug, stats]) => (
                <div key={slug} className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono text-muted-foreground">{slug}</span>
                  </div>
                  <div className="flex items-center gap-4 text-xs font-mono">
                    <span className="text-muted-foreground">{stats.runs} runs</span>
                    <span className="text-foreground">${stats.cost_usd.toFixed(4)}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* By Brand */}
        <div className="rounded-lg border border-border bg-card p-4">
          <h3 className="text-sm font-medium mb-3">Cost by Brand</h3>
          {brandEntries.length === 0 ? (
            <p className="text-xs text-muted-foreground italic">No usage yet</p>
          ) : (
            <div className="space-y-2">
              {brandEntries.map(([name, stats]) => (
                <div key={name} className="flex items-center justify-between">
                  <span className="text-xs font-mono text-muted-foreground">{name}</span>
                  <div className="flex items-center gap-4 text-xs font-mono">
                    <span className="text-muted-foreground">{stats.runs} runs</span>
                    <span className="text-foreground">${stats.cost_usd.toFixed(4)}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
