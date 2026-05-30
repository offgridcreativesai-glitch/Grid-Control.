/** Small formatting helpers for the cockpit. */

/** "2h ago", "5m ago", "just now" — from an ISO string or epoch. Empty → "—". */
export function relativeTime(input?: string | number | null): string {
  if (!input) return "—"
  const t = typeof input === "number" ? input : Date.parse(input)
  if (Number.isNaN(t)) return "—"
  const diff = Date.now() - t
  if (diff < 0) return "just now"
  const s = Math.floor(diff / 1000)
  if (s < 45) return "just now"
  const m = Math.floor(s / 60)
  if (m < 60) return `${m}m ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h ago`
  const days = Math.floor(h / 24)
  if (days < 7) return `${days}d ago`
  const w = Math.floor(days / 7)
  if (w < 5) return `${w}w ago`
  return new Date(t).toLocaleDateString()
}

/** First non-empty initial(s) for an avatar/mark from a name. */
export function brandMark(name?: string): string {
  if (!name) return "?"
  const parts = name.trim().split(/\s+/)
  if (parts.length === 1) return parts[0].slice(0, 1).toUpperCase()
  return (parts[0][0] + parts[1][0]).toUpperCase()
}
