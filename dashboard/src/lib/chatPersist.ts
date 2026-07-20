/** Atlas chat thread persistence. The thread was pure in-memory useState, so
 * navigating away (e.g. to Review to find the thing to approve) unmounted the
 * page and reset it to [] — the user's typed message vanished (Jul 20 bug).
 * Persist per-brand in sessionStorage: survives in-tab navigation, clears on
 * tab close (no stale threads resurrected weeks later), never crosses brands.
 * Pure/guarded so the decision is testable and a bad store can't crash chat. */

export type ChatMsg = {
  id: string
  role: "user" | "assistant"
  text: string
  dispatch?: {
    agent_name: string
    rationale: string
    status: "pending" | "running" | "done" | "failed"
    note?: string
  }
}

export function chatKey(slug: string): string {
  return `gc_chat_${slug}`
}

function store(): Storage | null {
  try {
    return typeof sessionStorage !== "undefined" ? sessionStorage : null
  } catch {
    return null // Storage can throw (private mode, disabled) — degrade, don't crash
  }
}

/** Restore a brand's thread. A dispatch left "running" when the page unmounted
 * can never resolve after a remount (its async patch is gone) — downgrade to
 * "pending" so the user can retry, instead of a spinner that hangs forever. */
export function loadThread(slug: string): ChatMsg[] {
  const s = store()
  if (!s || !slug) return []
  try {
    const raw = s.getItem(chatKey(slug))
    if (!raw) return []
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    return parsed
      .filter((m): m is ChatMsg => m && typeof m.text === "string" && (m.role === "user" || m.role === "assistant"))
      .map((m) =>
        m.dispatch?.status === "running"
          ? { ...m, dispatch: { ...m.dispatch, status: "pending" as const } }
          : m,
      )
  } catch {
    return []
  }
}

export function saveThread(slug: string, msgs: ChatMsg[]): void {
  const s = store()
  if (!s || !slug) return
  try {
    if (msgs.length === 0) s.removeItem(chatKey(slug))
    else s.setItem(chatKey(slug), JSON.stringify(msgs))
  } catch {
    /* quota / disabled — persistence is best-effort, never blocks the chat */
  }
}
