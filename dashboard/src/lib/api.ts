/**
 * Central API fetch wrapper.
 * Injects Supabase JWT (Authorization: Bearer) on every request.
 * Falls back to X-Dashboard-Secret for backward compatibility.
 *
 * Hardening: supabase.auth.getSession() can deadlock on the navigator LockManager
 * (a known supabase-js issue) — if it hangs, every request wedges and the UI freezes
 * (e.g. a stuck "Creating…" on submit). We race getSession() against a short timeout
 * and fall back to the persisted session token in localStorage, so a request never hangs.
 */

import { supabase } from "./supabase"

const DASHBOARD_SECRET = import.meta.env.VITE_DASHBOARD_SECRET ?? ""

function tokenFromStorage(): string | null {
  try {
    for (const k of Object.keys(localStorage)) {
      if (k.startsWith("sb-") && k.endsWith("-auth-token")) {
        const v = JSON.parse(localStorage.getItem(k) || "null")
        if (v?.access_token) return v.access_token as string
      }
    }
  } catch {
    /* ignore */
  }
  return null
}

async function getAccessToken(): Promise<string | null> {
  try {
    const timeout = new Promise<null>((resolve) => setTimeout(() => resolve(null), 1500))
    const live = supabase.auth
      .getSession()
      .then((r) => r.data.session?.access_token ?? null)
      .catch(() => null)
    const tok = await Promise.race([live, timeout])
    return tok ?? tokenFromStorage()
  } catch {
    return tokenFromStorage()
  }
}

export async function apiFetch(input: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers)

  const token = await getAccessToken()
  if (token) {
    headers.set("Authorization", `Bearer ${token}`)
  } else if (DASHBOARD_SECRET) {
    headers.set("X-Dashboard-Secret", DASHBOARD_SECRET)
  }

  return fetch(input, { ...init, headers })
}
