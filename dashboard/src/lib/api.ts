/**
 * Central API fetch wrapper.
 * Automatically injects X-Dashboard-Secret header on every request.
 * Use this instead of raw fetch() for all /api/* calls.
 */

const DASHBOARD_SECRET = import.meta.env.VITE_DASHBOARD_SECRET ?? ""

export async function apiFetch(
  input: string,
  init: RequestInit = {}
): Promise<Response> {
  const headers = new Headers(init.headers)
  if (DASHBOARD_SECRET) {
    headers.set("X-Dashboard-Secret", DASHBOARD_SECRET)
  }
  return fetch(input, { ...init, headers })
}
