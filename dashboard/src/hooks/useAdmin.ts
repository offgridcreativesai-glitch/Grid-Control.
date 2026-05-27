/**
 * TanStack Query hooks for Super Admin endpoints.
 * Only callable by super_admin users — API returns 403 for everyone else.
 */
import { useQuery } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"

// ── Types ────────────────────────────────────────────────────────────────────

export interface AdminOverview {
  total_brands: number
  active_subscriptions: number
  mrr_paise: number
  mrr_inr: number
  month_revenue_paise: number
  month_revenue_inr: number
  total_cost_usd: number
  total_runs_this_month: number
  agent_breakdown: Record<string, { runs: number; cost_usd: number }>
  brand_costs: Record<string, { runs: number; cost_usd: number }>
  profit_margin_pct: number
}

export interface AdminClient {
  id: string
  slug: string
  name: string
  created_at: string
  owner_name: string
  owner_email: string
  plan: string
  plan_amount_paise: number
  subscription_status: string
  cost_usd_this_month: number
}

export interface AdminRevenue {
  mrr_paise: number
  mrr_inr: number
  active_subscriptions: number
  total_subscriptions: number
  recent_payments: Array<{
    id: string
    brand_id: string
    amount_paise: number
    currency: string
    status: string
    method: string
    created_at: string
    brands?: { slug: string; name: string }
  }>
}

export interface AdminSystem {
  total_runs: number
  successes: number
  errors: number
  running: number
  error_rate_pct: number
  cost_by_model: Record<string, { runs: number; cost_usd: number }>
  total_api_cost_usd: number
  total_fal_cost_usd: number
  total_apify_cost_usd: number
  total_cost_usd: number
  recent_errors: Array<{
    agent: string
    brand: string
    error: string
    at: string
  }>
}

// ── Hooks ────────────────────────────────────────────────────────────────────

export function useAdminOverview() {
  return useQuery<AdminOverview>({
    queryKey: ["admin", "overview"],
    queryFn: async () => {
      const res = await apiFetch("/api/admin/overview")
      const json = await res.json()
      if (!json.success) throw new Error(json.error)
      return json.data
    },
    refetchInterval: 30000,
  })
}

export function useAdminClients() {
  return useQuery<AdminClient[]>({
    queryKey: ["admin", "clients"],
    queryFn: async () => {
      const res = await apiFetch("/api/admin/clients")
      const json = await res.json()
      if (!json.success) throw new Error(json.error)
      return json.data
    },
    refetchInterval: 30000,
  })
}

export function useAdminRevenue() {
  return useQuery<AdminRevenue>({
    queryKey: ["admin", "revenue"],
    queryFn: async () => {
      const res = await apiFetch("/api/admin/revenue")
      const json = await res.json()
      if (!json.success) throw new Error(json.error)
      return json.data
    },
    refetchInterval: 30000,
  })
}

export function useAdminSystem() {
  return useQuery<AdminSystem>({
    queryKey: ["admin", "system"],
    queryFn: async () => {
      const res = await apiFetch("/api/admin/system")
      const json = await res.json()
      if (!json.success) throw new Error(json.error)
      return json.data
    },
    refetchInterval: 15000,
  })
}
