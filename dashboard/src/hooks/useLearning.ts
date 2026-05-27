/**
 * TanStack Query hooks for continuous learning.
 */
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"
import { useBrandStore } from "@/store/brandStore"

export interface LearningEntry {
  id: string
  brand_id: string
  agent_slug: string
  learning_type: string
  content: string
  source: string
  created_at: string
}

export interface LearningStats {
  total_learnings: number
  this_month: number
  by_agent: Record<string, number>
  by_type: Record<string, number>
}

export function useLearnings(limit = 20) {
  const { activeBrand } = useBrandStore()
  return useQuery<LearningEntry[]>({
    queryKey: ["learning", "list", activeBrand.slug, limit],
    queryFn: async () => {
      const res = await apiFetch(
        `/api/learning/list?brand_slug=${encodeURIComponent(activeBrand.slug)}&limit=${limit}`
      )
      const json = await res.json()
      return json.data ?? []
    },
    enabled: !!activeBrand.slug,
  })
}

export function useLearningStats() {
  const { activeBrand } = useBrandStore()
  return useQuery<LearningStats | null>({
    queryKey: ["learning", "stats", activeBrand.slug],
    queryFn: async () => {
      const res = await apiFetch(
        `/api/learning/stats?brand_slug=${encodeURIComponent(activeBrand.slug)}`
      )
      const json = await res.json()
      return json.data ?? null
    },
    enabled: !!activeBrand.slug,
  })
}

export function useCaptureLearning() {
  const qc = useQueryClient()
  const { activeBrand } = useBrandStore()
  return useMutation({
    mutationFn: async (payload: {
      agent_slug: string
      learning_type: string
      content: string
      source: string
    }) => {
      const res = await apiFetch("/api/learning/capture", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ brand_slug: activeBrand.slug, ...payload }),
      })
      const json = await res.json()
      if (!json.success) throw new Error(json.error)
      return json.data
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["learning"] }),
  })
}
