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
  sendMagicLink: (email: string) => Promise<{ error: string | null }>
  signInWithGoogle: () => Promise<{ error: string | null }>
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
    // A throwing auth boot (e.g. AuthApiError: Invalid Refresh Token from a
    // stale stored session) must resolve to SIGNED OUT — never leave
    // loading:true, which renders as a permanently blank screen (Jul 16 bug,
    // deployed /command after login).
    let session: Session | null = null
    let user: User | null = null
    let isAdmin = false
    try {
      const { data, error } = await supabase.auth.getSession()
      if (!error) {
        session = data.session
        user = session?.user ?? null
      }
      if (user) {
        isAdmin = await checkSuperAdmin()
      }
    } catch {
      session = null
      user = null
      isAdmin = false
    } finally {
      set({
        session,
        user,
        loading: false,
        isSuperAdmin: isAdmin,
        viewMode: isAdmin ? "admin" : "client",
      })
    }

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

  sendMagicLink: async (email) => {
    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: { emailRedirectTo: `${window.location.origin}/command` },
    })
    return { error: error?.message ?? null }
  },

  signInWithGoogle: async () => {
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: `${window.location.origin}/command` },
    })
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
