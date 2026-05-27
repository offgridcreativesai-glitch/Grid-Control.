/**
 * TanStack Query hooks for billing / Razorpay subscriptions.
 */
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"
import { useBrandStore } from "@/store/brandStore"

// ── Types ────────────────────────────────────────────────────

export interface BillingPlan {
  id: string
  name: string
  slug: string
  description: string
  amount_paise: number
  currency: string
  interval: string
  razorpay_plan_id: string | null
  features: string[]
  max_brands: number
  max_agent_runs_per_month: number
  is_active: boolean
}

export interface Subscription {
  id: string
  brand_id: string
  plan_id: string
  razorpay_subscription_id: string | null
  razorpay_customer_id: string | null
  status: string
  current_period_start: string | null
  current_period_end: string | null
  trial_end: string | null
  cancelled_at: string | null
  metadata: Record<string, any>
  billing_plans?: BillingPlan
}

export interface UsageData {
  total_runs: number
  total_cost_usd: number
  total_input_tokens: number
  total_output_tokens: number
  by_agent: Record<string, { runs: number; cost_usd: number }>
  period_start: string
}

export interface Payment {
  id: string
  razorpay_payment_id: string
  amount_paise: number
  currency: string
  status: string
  method: string
  created_at: string
}

// ── Hooks ────────────────────────────────────────────────────

export function useBillingPlans() {
  return useQuery<BillingPlan[]>({
    queryKey: ["billing", "plans"],
    queryFn: async () => {
      const res = await apiFetch("/api/billing/plans")
      const json = await res.json()
      return json.data ?? []
    },
    staleTime: 5 * 60 * 1000,
  })
}

export function useSubscription() {
  const { activeBrand } = useBrandStore()
  return useQuery<Subscription | null>({
    queryKey: ["billing", "subscription", activeBrand.slug],
    queryFn: async () => {
      const res = await apiFetch(
        `/api/billing/subscription?brand_slug=${encodeURIComponent(activeBrand.slug)}`
      )
      const json = await res.json()
      return json.data ?? null
    },
    enabled: !!activeBrand.slug,
  })
}

export function useUsage() {
  const { activeBrand } = useBrandStore()
  return useQuery<UsageData | null>({
    queryKey: ["billing", "usage", activeBrand.slug],
    queryFn: async () => {
      const res = await apiFetch(
        `/api/billing/usage?brand_slug=${encodeURIComponent(activeBrand.slug)}`
      )
      const json = await res.json()
      return json.data ?? null
    },
    enabled: !!activeBrand.slug,
  })
}

export function usePayments() {
  const { activeBrand } = useBrandStore()
  return useQuery<Payment[]>({
    queryKey: ["billing", "payments", activeBrand.slug],
    queryFn: async () => {
      const res = await apiFetch(
        `/api/billing/payments?brand_slug=${encodeURIComponent(activeBrand.slug)}`
      )
      const json = await res.json()
      return json.data ?? []
    },
    enabled: !!activeBrand.slug,
  })
}

export function useSubscribe() {
  const qc = useQueryClient()
  const { activeBrand } = useBrandStore()
  return useMutation({
    mutationFn: async (planSlug: string) => {
      const res = await apiFetch("/api/billing/subscribe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          brand_slug: activeBrand.slug,
          plan_slug: planSlug,
          name: activeBrand.name,
        }),
      })
      const json = await res.json()
      if (!json.success) throw new Error(json.error)
      return json.data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["billing"] })
    },
  })
}

export function useCancelSubscription() {
  const qc = useQueryClient()
  const { activeBrand } = useBrandStore()
  return useMutation({
    mutationFn: async () => {
      const res = await apiFetch("/api/billing/cancel", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ brand_slug: activeBrand.slug }),
      })
      const json = await res.json()
      if (!json.success) throw new Error(json.error)
      return json.data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["billing"] })
    },
  })
}
