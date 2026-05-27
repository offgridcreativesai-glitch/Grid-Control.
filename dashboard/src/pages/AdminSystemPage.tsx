import { Loader2, Cpu, AlertTriangle, CheckCircle2, Play, Zap } from "lucide-react"
import { cn } from "@/lib/utils"
import { useAdminSystem } from "@/hooks/useAdmin"

function StatCard({
  label,
  value,
  sub,
  icon: Icon,
  color = "text-primary",
}: {
  label: string
  value: string | number
  sub?: string
  icon: typeof Cpu
  color?: string
}) {
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <div className="flex items-center gap-2 mb-2">
        <Icon className={cn("h-4 w-4", color)} />
        <p className="text-xs text-muted-foreground">{label}</p>
      </div>
      <p className="text-xl font-semibold font-mono">{value}</p>
      {sub && <p className="text-[10px] text-muted-foreground mt-1">{sub}</p>}
    </div>
  )
}

export function AdminSystemPage() {
  const { data, isLoading, isError } = useAdminSystem()

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
        <p className="text-sm text-destructive">Failed to load system data</p>
      </div>
    )
  }

  const modelEntries = Object.entries(data.cost_by_model)
    .sort((a, b) => b[1].cost_usd - a[1].cost_usd)

  return (
    <div className="p-6 space-y-6 overflow-auto h-full">
      <div>
        <h1 className="text-lg font-semibold">Admin — System Health</h1>
        <p className="text-xs text-muted-foreground mt-1">Agent runs, error rates, API cost breakdown</p>
      </div>

      {/* Health KPIs */}
      <div className="grid grid-cols-5 gap-4">
        <StatCard label="Total Runs" value={data.total_runs} icon={Cpu} />
        <StatCard label="Successes" value={data.successes} icon={CheckCircle2} color="text-green-400" />
        <StatCard label="Errors" value={data.errors} icon={AlertTriangle} color="text-destructive" />
        <StatCard label="Running" value={data.running} icon={Play} color="text-blue-400" />
        <StatCard
          label="Error Rate"
          value={`${data.error_rate_pct}%`}
          icon={Zap}
          color={data.error_rate_pct > 10 ? "text-destructive" : "text-green-400"}
        />
      </div>

      {/* Cost Breakdown */}
      <div className="grid grid-cols-2 gap-6">
        {/* By Model */}
        <div className="rounded-lg border border-border bg-card p-4">
          <h3 className="text-sm font-medium mb-3">Cost by Model</h3>
          <div className="space-y-3">
            {modelEntries.map(([model, stats]) => {
              const pct = data.total_cost_usd > 0
                ? (stats.cost_usd / data.total_cost_usd) * 100
                : 0
              return (
                <div key={model}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-mono text-muted-foreground">{model}</span>
                    <span className="text-xs font-mono">${stats.cost_usd.toFixed(4)}</span>
                  </div>
                  <div className="h-1.5 rounded-full bg-secondary overflow-hidden">
                    <div
                      className="h-full rounded-full bg-primary transition-all"
                      style={{ width: `${Math.min(pct, 100)}%` }}
                    />
                  </div>
                  <p className="text-[10px] text-muted-foreground mt-0.5">
                    {stats.runs} runs · {pct.toFixed(1)}% of total
                  </p>
                </div>
              )
            })}
          </div>
        </div>

        {/* Cost Summary */}
        <div className="rounded-lg border border-border bg-card p-4">
          <h3 className="text-sm font-medium mb-3">Cost Summary</h3>
          <div className="space-y-3">
            <div className="flex items-center justify-between py-2 border-b border-border">
              <span className="text-sm text-muted-foreground">Anthropic API</span>
              <span className="text-sm font-mono">${data.total_api_cost_usd.toFixed(4)}</span>
            </div>
            <div className="flex items-center justify-between py-2 border-b border-border">
              <span className="text-sm text-muted-foreground">FAL.ai (images)</span>
              <span className="text-sm font-mono">${data.total_fal_cost_usd.toFixed(4)}</span>
            </div>
            <div className="flex items-center justify-between py-2 border-b border-border">
              <span className="text-sm text-muted-foreground">Apify (scraping)</span>
              <span className="text-sm font-mono">${data.total_apify_cost_usd.toFixed(4)}</span>
            </div>
            <div className="flex items-center justify-between py-2 font-medium">
              <span className="text-sm">Total</span>
              <span className="text-sm font-mono text-primary">${data.total_cost_usd.toFixed(4)}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Errors */}
      <div className="rounded-lg border border-border bg-card p-4">
        <h3 className="text-sm font-medium mb-3">Recent Errors</h3>
        {data.recent_errors.length === 0 ? (
          <p className="text-xs text-muted-foreground italic">No errors — all systems green</p>
        ) : (
          <div className="space-y-2">
            {data.recent_errors.map((err, i) => (
              <div key={i} className="flex items-start gap-3 py-2 border-b border-border last:border-0">
                <AlertTriangle className="h-3.5 w-3.5 text-destructive mt-0.5 shrink-0" />
                <div className="min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="text-xs font-mono font-medium">{err.agent}</span>
                    {err.brand && (
                      <span className="text-[10px] text-muted-foreground">· {err.brand}</span>
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground truncate">{err.error}</p>
                  {err.at && (
                    <p className="text-[10px] text-muted-foreground mt-0.5">
                      {new Date(err.at).toLocaleString()}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
