import { useState } from "react"
import { Check, CreditCard, Zap, Building2, ArrowRight, Loader2, AlertCircle } from "lucide-react"
import { cn } from "@/lib/utils"
import {
  useBillingPlans,
  useSubscription,
  useUsage,
  usePayments,
  useSubscribe,
  useCancelSubscription,
  type BillingPlan,
} from "@/hooks/useBilling"

function formatINR(paise: number) {
  return `₹${(paise / 100).toLocaleString("en-IN")}`
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    active: "bg-green-500/20 text-green-400",
    authenticated: "bg-yellow-500/20 text-yellow-400",
    created: "bg-blue-500/20 text-blue-400",
    cancelled: "bg-red-500/20 text-red-400",
    expired: "bg-neutral-500/20 text-neutral-400",
    paused: "bg-orange-500/20 text-orange-400",
  }
  return (
    <span className={cn("rounded-full px-2.5 py-0.5 text-xs font-medium", colors[status] ?? colors.created)}>
      {status}
    </span>
  )
}

const planIcons: Record<string, typeof Zap> = {
  starter: Zap,
  growth: CreditCard,
  agency: Building2,
}

function PlanCard({
  plan,
  isActive,
  onSelect,
  loading,
}: {
  plan: BillingPlan
  isActive: boolean
  onSelect: () => void
  loading: boolean
}) {
  const Icon = planIcons[plan.slug] ?? Zap
  const isGrowth = plan.slug === "growth"

  return (
    <div
      className={cn(
        "relative flex flex-col rounded-xl border p-6 transition-all",
        isActive
          ? "border-primary bg-primary/5"
          : isGrowth
          ? "border-primary/50 bg-card shadow-lg shadow-primary/5"
          : "border-border bg-card hover:border-primary/30"
      )}
    >
      {isGrowth && !isActive && (
        <div className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-primary px-3 py-0.5 text-xs font-semibold text-primary-foreground">
          Most Popular
        </div>
      )}

      <div className="mb-4 flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
          <Icon className="h-5 w-5 text-primary" />
        </div>
        <div>
          <h3 className="font-semibold text-foreground">{plan.name}</h3>
          <p className="text-xs text-muted-foreground">{plan.description}</p>
        </div>
      </div>

      <div className="mb-4">
        <span className="text-3xl font-bold text-foreground">{formatINR(plan.amount_paise)}</span>
        <span className="text-sm text-muted-foreground">/{plan.interval === "monthly" ? "mo" : "yr"}</span>
      </div>

      <ul className="mb-6 flex-1 space-y-2">
        {plan.features.map((f, i) => (
          <li key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
            <Check className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
            {f}
          </li>
        ))}
        <li className="flex items-start gap-2 text-sm text-muted-foreground">
          <Check className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
          {plan.max_agent_runs_per_month} agent runs/month
        </li>
        <li className="flex items-start gap-2 text-sm text-muted-foreground">
          <Check className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
          {plan.max_brands} brand{plan.max_brands > 1 ? "s" : ""}
        </li>
      </ul>

      {isActive ? (
        <div className="rounded-lg bg-primary/10 py-2 text-center text-sm font-medium text-primary">
          Current Plan
        </div>
      ) : (
        <button
          onClick={onSelect}
          disabled={loading}
          className={cn(
            "flex items-center justify-center gap-2 rounded-lg py-2.5 text-sm font-medium transition-colors",
            isGrowth
              ? "bg-primary text-primary-foreground hover:bg-primary/90"
              : "bg-secondary text-foreground hover:bg-secondary/80"
          )}
        >
          {loading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <>
              Get Started <ArrowRight className="h-4 w-4" />
            </>
          )}
        </button>
      )}
    </div>
  )
}

export function BillingPage() {
  const { data: plans, isLoading: plansLoading } = useBillingPlans()
  const { data: subscription } = useSubscription()
  const { data: usage } = useUsage()
  const { data: payments } = usePayments()
  const subscribeMut = useSubscribe()
  const cancelMut = useCancelSubscription()
  const [selectedPlan, setSelectedPlan] = useState<string | null>(null)

  const handleSubscribe = (slug: string) => {
    setSelectedPlan(slug)
    subscribeMut.mutate(slug, {
      onSuccess: (data) => {
        // Razorpay returns a short_url for checkout
        if (data?.short_url) {
          window.open(data.short_url, "_blank")
        }
        setSelectedPlan(null)
      },
      onError: () => setSelectedPlan(null),
    })
  }

  const activePlanSlug = subscription?.billing_plans?.slug

  return (
    <div className="mx-auto max-w-5xl space-y-8 p-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-foreground">Billing</h1>
        <p className="text-sm text-muted-foreground">
          Manage your subscription, usage, and payments.
        </p>
      </div>

      {/* Active Subscription Banner */}
      {subscription && subscription.status !== "cancelled" && (
        <div className="flex items-center justify-between rounded-xl border border-primary/20 bg-primary/5 p-4">
          <div className="flex items-center gap-3">
            <CreditCard className="h-5 w-5 text-primary" />
            <div>
              <p className="text-sm font-medium text-foreground">
                {subscription.billing_plans?.name ?? "Active"} Plan
              </p>
              <p className="text-xs text-muted-foreground">
                {subscription.current_period_end
                  ? `Renews ${new Date(subscription.current_period_end).toLocaleDateString()}`
                  : "Subscription active"}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <StatusBadge status={subscription.status} />
            {subscription.status === "active" && (
              <button
                onClick={() => cancelMut.mutate()}
                disabled={cancelMut.isPending}
                className="text-xs text-muted-foreground hover:text-red-400 transition-colors"
              >
                Cancel
              </button>
            )}
          </div>
        </div>
      )}

      {/* Plans */}
      <div>
        <h2 className="mb-4 text-lg font-semibold text-foreground">Plans</h2>
        {plansLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-3">
            {(plans ?? []).map((plan) => (
              <PlanCard
                key={plan.slug}
                plan={plan}
                isActive={activePlanSlug === plan.slug}
                onSelect={() => handleSubscribe(plan.slug)}
                loading={selectedPlan === plan.slug && subscribeMut.isPending}
              />
            ))}
          </div>
        )}
      </div>

      {/* Usage This Month */}
      {usage && (
        <div>
          <h2 className="mb-4 text-lg font-semibold text-foreground">Usage This Month</h2>
          <div className="grid gap-4 sm:grid-cols-4">
            <div className="rounded-xl border border-border bg-card p-4">
              <p className="text-xs text-muted-foreground">Agent Runs</p>
              <p className="text-2xl font-bold text-foreground">{usage.total_runs}</p>
            </div>
            <div className="rounded-xl border border-border bg-card p-4">
              <p className="text-xs text-muted-foreground">Est. Cost</p>
              <p className="text-2xl font-bold text-foreground">${usage.total_cost_usd.toFixed(2)}</p>
            </div>
            <div className="rounded-xl border border-border bg-card p-4">
              <p className="text-xs text-muted-foreground">Input Tokens</p>
              <p className="text-2xl font-bold text-foreground">
                {(usage.total_input_tokens / 1000).toFixed(0)}K
              </p>
            </div>
            <div className="rounded-xl border border-border bg-card p-4">
              <p className="text-xs text-muted-foreground">Output Tokens</p>
              <p className="text-2xl font-bold text-foreground">
                {(usage.total_output_tokens / 1000).toFixed(0)}K
              </p>
            </div>
          </div>

          {/* Per-agent breakdown */}
          {Object.keys(usage.by_agent).length > 0 && (
            <div className="mt-4 rounded-xl border border-border bg-card">
              <div className="border-b border-border px-4 py-2">
                <p className="text-xs font-medium text-muted-foreground">By Agent</p>
              </div>
              <div className="divide-y divide-border">
                {Object.entries(usage.by_agent)
                  .sort(([, a], [, b]) => b.runs - a.runs)
                  .map(([slug, data]) => (
                    <div key={slug} className="flex items-center justify-between px-4 py-2.5">
                      <span className="text-sm text-foreground">{slug}</span>
                      <div className="flex items-center gap-4">
                        <span className="text-xs text-muted-foreground">{data.runs} runs</span>
                        <span className="text-xs text-muted-foreground">
                          ${data.cost_usd.toFixed(4)}
                        </span>
                      </div>
                    </div>
                  ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Payment History */}
      {payments && payments.length > 0 && (
        <div>
          <h2 className="mb-4 text-lg font-semibold text-foreground">Payment History</h2>
          <div className="rounded-xl border border-border bg-card">
            <div className="grid grid-cols-4 border-b border-border px-4 py-2 text-xs font-medium text-muted-foreground">
              <span>Date</span>
              <span>Amount</span>
              <span>Method</span>
              <span>Status</span>
            </div>
            <div className="divide-y divide-border">
              {payments.map((p) => (
                <div key={p.id} className="grid grid-cols-4 px-4 py-2.5 text-sm">
                  <span className="text-foreground">
                    {new Date(p.created_at).toLocaleDateString()}
                  </span>
                  <span className="text-foreground">{formatINR(p.amount_paise)}</span>
                  <span className="text-muted-foreground capitalize">{p.method || "—"}</span>
                  <StatusBadge status={p.status} />
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Error Display */}
      {subscribeMut.isError && (
        <div className="flex items-center gap-2 rounded-lg border border-red-500/20 bg-red-500/5 p-3 text-sm text-red-400">
          <AlertCircle className="h-4 w-4" />
          {subscribeMut.error?.message || "Something went wrong"}
        </div>
      )}
    </div>
  )
}
