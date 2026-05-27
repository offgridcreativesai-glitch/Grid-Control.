import { Loader2, TrendingUp, CreditCard, ArrowUpRight } from "lucide-react"
import { cn } from "@/lib/utils"
import { useAdminRevenue } from "@/hooks/useAdmin"

function formatINR(paise: number) {
  return `₹${(paise / 100).toLocaleString("en-IN")}`
}

function PaymentStatus({ status }: { status: string }) {
  const colors: Record<string, string> = {
    captured: "bg-green-500/20 text-green-400",
    authorized: "bg-yellow-500/20 text-yellow-400",
    failed: "bg-red-500/20 text-red-400",
    refunded: "bg-orange-500/20 text-orange-400",
  }
  return (
    <span className={cn("rounded-full px-2 py-0.5 text-[10px] font-medium", colors[status] ?? "bg-muted text-muted-foreground")}>
      {status}
    </span>
  )
}

export function AdminRevenuePage() {
  const { data, isLoading, isError } = useAdminRevenue()

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
        <p className="text-sm text-destructive">Failed to load revenue data</p>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6 overflow-auto h-full">
      <div>
        <h1 className="text-lg font-semibold">Admin — Revenue</h1>
        <p className="text-xs text-muted-foreground mt-1">Subscriptions, payments, MRR tracking</p>
      </div>

      {/* Revenue KPIs */}
      <div className="grid grid-cols-3 gap-4">
        <div className="rounded-lg border border-border bg-card p-5">
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp className="h-4 w-4 text-green-400" />
            <p className="text-xs text-muted-foreground">MRR</p>
          </div>
          <p className="text-2xl font-semibold font-mono">
            ₹{data.mrr_inr.toLocaleString("en-IN")}
          </p>
        </div>
        <div className="rounded-lg border border-border bg-card p-5">
          <div className="flex items-center gap-2 mb-2">
            <CreditCard className="h-4 w-4 text-blue-400" />
            <p className="text-xs text-muted-foreground">Active Subs</p>
          </div>
          <p className="text-2xl font-semibold font-mono">
            {data.active_subscriptions}
          </p>
          <p className="text-xs text-muted-foreground mt-1">
            of {data.total_subscriptions} total
          </p>
        </div>
        <div className="rounded-lg border border-border bg-card p-5">
          <div className="flex items-center gap-2 mb-2">
            <ArrowUpRight className="h-4 w-4 text-primary" />
            <p className="text-xs text-muted-foreground">ARR (projected)</p>
          </div>
          <p className="text-2xl font-semibold font-mono">
            ₹{(data.mrr_inr * 12).toLocaleString("en-IN")}
          </p>
        </div>
      </div>

      {/* Payment History */}
      <div>
        <h3 className="text-sm font-medium mb-3">Recent Payments</h3>
        <div className="rounded-lg border border-border bg-card overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border bg-secondary/30">
                <th className="px-4 py-2.5 text-left text-xs font-medium text-muted-foreground">Brand</th>
                <th className="px-4 py-2.5 text-right text-xs font-medium text-muted-foreground">Amount</th>
                <th className="px-4 py-2.5 text-center text-xs font-medium text-muted-foreground">Method</th>
                <th className="px-4 py-2.5 text-center text-xs font-medium text-muted-foreground">Status</th>
                <th className="px-4 py-2.5 text-right text-xs font-medium text-muted-foreground">Date</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {data.recent_payments.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-sm text-muted-foreground">
                    No payments recorded yet
                  </td>
                </tr>
              ) : (
                data.recent_payments.map((p) => (
                  <tr key={p.id} className="hover:bg-secondary/30 transition-colors">
                    <td className="px-4 py-3 text-sm">
                      {p.brands?.name ?? "—"}
                    </td>
                    <td className="px-4 py-3 text-right text-sm font-mono">
                      {formatINR(p.amount_paise)}
                    </td>
                    <td className="px-4 py-3 text-center text-xs text-muted-foreground capitalize">
                      {p.method || "—"}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <PaymentStatus status={p.status} />
                    </td>
                    <td className="px-4 py-3 text-right text-xs text-muted-foreground">
                      {new Date(p.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
