/** /api/events auth is ?token= only — EventSource cannot set Authorization
 * headers (see routes/system.py sse_events). No token -> no URL: connecting
 * without one is a guaranteed 401 + infinite auto-reconnect, the UAT Jul-7
 * "SSE 401 hammering" bug. Pure so the decision is testable. */
export function sseUrl(token: string | null | undefined): string | null {
  if (!token) return null
  return `/api/events?token=${encodeURIComponent(token)}`
}
