import { create } from "zustand"
import { supabase } from "@/lib/supabase"
import { apiFetch } from "@/lib/api"
import type { User, Session } from "@supabase/supabase-js"

export type ViewMode = "admin" | "client"

interface AuthState {
  user: User | null
  session: Session | null
  loading: boolean
  isSuperAdmin: boolean
  viewMode: ViewMode
  setViewMode: (mode: ViewMode) => void
  init: () => Promise<void>
  signIn: (email: string, password: string) => Promise<{ error: string | null }>
  signUp: (email: string, password: string, fullName: string) => Promise<{ error: string | null }>
  signOut: () => Promise<void>
}

async function checkSuperAdmin(): Promise<boolean> {
  try {
    const res = await apiFetch("/api/admin/check")
    if (!res.ok) return false
    const json = await res.json()
    return json?.data?.is_admin === true
  } catch {
    return false
  }
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  session: null,
  loading: true,
  isSuperAdmin: false,
  viewMode: "client" as ViewMode,
  setViewMode: (mode) => set({ viewMode: mode }),

  init: async () => {
    const { data } = await supabase.auth.getSession()
    const user = data.session?.user ?? null

    let isAdmin = false
    if (user) {
      isAdmin = await checkSuperAdmin()
    }

    set({
      session: data.session,
      user,
      loading: false,
      isSuperAdmin: isAdmin,
      viewMode: isAdmin ? "admin" : "client",
    })

    supabase.auth.onAuthStateChange(async (_event, session) => {
      const newUser = session?.user ?? null
      set({ session, user: newUser })
      if (newUser) {
        const isAdmin = await checkSuperAdmin()
        set({ isSuperAdmin: isAdmin, viewMode: isAdmin ? "admin" : "client" })
      } else {
        set({ isSuperAdmin: false, viewMode: "client" })
      }
    })
  },

  signIn: async (email, password) => {
    const { error } = await supabase.auth.signInWithPassword({ email, password })
    return { error: error?.message ?? null }
  },

  signUp: async (email, password, fullName) => {
    const { error } = await supabase.auth.signUp({
      email,
      password,
      options: { data: { full_name: fullName } },
    })
    return { error: error?.message ?? null }
  },

  signOut: async () => {
    await supabase.auth.signOut()
    set({ user: null, session: null, isSuperAdmin: false })
  },
}))
