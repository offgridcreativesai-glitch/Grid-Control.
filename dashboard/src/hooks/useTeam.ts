/**
 * TanStack Query hooks for team management.
 */
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"
import { useBrandStore } from "@/store/brandStore"

export interface TeamMember {
  id: string
  user_id: string
  brand_id: string
  role: "admin" | "editor" | "viewer"
  created_at: string
  profiles?: {
    email: string
    display_name: string | null
  }
}

export function useTeamMembers() {
  const { activeBrand } = useBrandStore()
  return useQuery<TeamMember[]>({
    queryKey: ["team", "members", activeBrand.slug],
    queryFn: async () => {
      const res = await apiFetch(
        `/api/team/members?brand_slug=${encodeURIComponent(activeBrand.slug)}`
      )
      const json = await res.json()
      return json.data ?? []
    },
    enabled: !!activeBrand.slug,
  })
}

export function useInviteMember() {
  const qc = useQueryClient()
  const { activeBrand } = useBrandStore()
  return useMutation({
    mutationFn: async ({ email, role }: { email: string; role: string }) => {
      const res = await apiFetch("/api/team/invite", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ brand_slug: activeBrand.slug, email, role }),
      })
      const json = await res.json()
      if (!json.success) throw new Error(json.error)
      return json.data
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["team"] }),
  })
}

export function useUpdateRole() {
  const qc = useQueryClient()
  const { activeBrand } = useBrandStore()
  return useMutation({
    mutationFn: async ({ userId, role }: { userId: string; role: string }) => {
      const res = await apiFetch("/api/team/update-role", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ brand_slug: activeBrand.slug, user_id: userId, role }),
      })
      const json = await res.json()
      if (!json.success) throw new Error(json.error)
      return json.data
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["team"] }),
  })
}

export function useRemoveMember() {
  const qc = useQueryClient()
  const { activeBrand } = useBrandStore()
  return useMutation({
    mutationFn: async (userId: string) => {
      const res = await apiFetch("/api/team/remove", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ brand_slug: activeBrand.slug, user_id: userId }),
      })
      const json = await res.json()
      if (!json.success) throw new Error(json.error)
      return json.data
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["team"] }),
  })
}
