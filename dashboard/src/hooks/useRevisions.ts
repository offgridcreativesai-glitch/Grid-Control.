/**
 * TanStack Query hooks for the revision loop.
 */
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"
import { useBrandStore } from "@/store/brandStore"

export interface Revision {
  id: string
  output_id: string
  brand_id: string
  agent_slug: string
  revision_number: number
  feedback: string
  status: string
  created_at: string
}

export function useRevisions(outputId: string) {
  const { activeBrand } = useBrandStore()
  return useQuery<Revision[]>({
    queryKey: ["revisions", outputId, activeBrand.slug],
    queryFn: async () => {
      const res = await apiFetch(
        `/api/outputs/revisions?brand_slug=${encodeURIComponent(activeBrand.slug)}&output_id=${encodeURIComponent(outputId)}`
      )
      const json = await res.json()
      return json.data ?? []
    },
    enabled: !!activeBrand.slug && !!outputId,
  })
}

export function useRequestRevision() {
  const qc = useQueryClient()
  const { activeBrand } = useBrandStore()
  return useMutation({
    mutationFn: async (payload: { output_id: string; feedback: string }) => {
      const res = await apiFetch("/api/outputs/revise", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ brand_slug: activeBrand.slug, ...payload }),
      })
      const json = await res.json()
      if (!json.success) throw new Error(json.error)
      return json.data
    },
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ["revisions", vars.output_id] })
      qc.invalidateQueries({ queryKey: ["outputs"] })
    },
  })
}
