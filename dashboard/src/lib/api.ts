/**
 * Central API fetch wrapper.
 * Injects Supabase JWT (Authorization: Bearer) on every request.
 * Falls back to X-Dashboard-Secret for backward compatibility.
 */

import { supabase } from "./supabase"

const DASHBOARD_SECRET = import.meta.env.VITE_DASHBOARD_SECRET ?? ""

export async function apiFetch(
  input: string,
  init: RequestInit = {}
): Promise<Response> {
  const headers = new Headers(init.headers)

  const { data } = await supabase.auth.getSession()
  if (data.session?.access_token) {
    headers.set("Authorization", `Bearer ${data.session.access_token}`)
  } else if (DASHBOARD_SECRET) {
    headers.set("X-Dashboard-Secret", DASHBOARD_SECRET)
  }

  return fetch(input, { ...init, headers })
}
