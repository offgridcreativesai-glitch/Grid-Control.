import { Loader2, Building2, ExternalLink } from "lucide-react"
import { cn } from "@/lib/utils"
import { useAdminClients } from "@/hooks/useAdmin"

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    active: "bg-green-500/20 text-green-400",
    authenticated: "bg-yellow-500/20 text-yellow-400",
    created: "bg-blue-500/20 text-blue-400",
    cancelled: "bg-red-500/20 text-red-400",
    expired: "bg-neutral-500/20 text-neutral-400",
    none: "bg-neutral-500/20 text-neutral-500",
  }
  return (
    <span className={cn("rounded-full px-2 py-0.5 text-[10px] font-medium", colors[status] ?? colors.none)}>
      {status}
    </span>
  )
}

export function AdminClientsPage() {
  const { data: clients, isLoading, isError } = useAdminClients()

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (isError) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-sm text-destructive">Failed to load clients</p>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6 overflow-auto h-full">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold">Admin — Clients</h1>
          <p className="text-xs text-muted-foreground mt-1">{clients?.length ?? 0} brands across all clients</p>
        </div>
      </div>

      <div className="rounded-lg border border-border bg-card overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-border bg-secondary/30">
              <th className="px-4 py-2.5 text-left text-xs font-medium text-muted-foreground">Brand</th>
              <th className="px-4 py-2.5 text-left text-xs font-medium text-muted-foreground">Owner</th>
              <th className="px-4 py-2.5 text-left text-xs font-medium text-muted-foreground">Plan</th>
              <th className="px-4 py-2.5 text-center text-xs font-medium text-muted-foreground">Status</th>
              <th className="px-4 py-2.5 text-right text-xs font-medium text-muted-foreground">Cost (month)</th>
              <th className="px-4 py-2.5 text-right text-xs font-medium text-muted-foreground">Created</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {(clients ?? []).map((c) => (
              <tr key={c.id} className="hover:bg-secondary/30 transition-colors">
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary/10">
                      <Building2 className="h-3.5 w-3.5 text-primary" />
                    </div>
                    <div>
                      <p className="text-sm font-medium">{c.name}</p>
                      <p className="text-[10px] text-muted-foreground font-mono">{c.slug}</p>
                    </div>
                  </div>
                </td>
                <td className="px-4 py-3">
                  <p className="text-sm">{c.owner_name}</p>
                  <p className="text-[10px] text-muted-foreground">{c.owner_email}</p>
                </td>
                <td className="px-4 py-3">
                  <p className="text-sm">{c.plan}</p>
                  {c.plan_amount_paise > 0 && (
                    <p className="text-[10px] text-muted-foreground">
                      ₹{(c.plan_amount_paise / 100).toLocaleString("en-IN")}/mo
                    </p>
                  )}
                </td>
                <td className="px-4 py-3 text-center">
                  <StatusBadge status={c.subscription_status} />
                </td>
                <td className="px-4 py-3 text-right text-sm font-mono text-muted-foreground">
                  ${c.cost_usd_this_month.toFixed(2)}
                </td>
                <td className="px-4 py-3 text-right text-xs text-muted-foreground">
                  {new Date(c.created_at).toLocaleDateString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
