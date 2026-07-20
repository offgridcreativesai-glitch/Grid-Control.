/** Pins the vanished-Atlas-message bug (Jul 20): the chat thread was in-memory
 * useState([]), so leaving the page and returning wiped what the user typed.
 * Fail-on-old: there was no persistence at all — every one of these round-trips
 * would return []. Fixed: threads persist per-brand and restore. */
import { afterEach, beforeAll, describe, expect, it } from "vitest"
import { chatKey, loadThread, saveThread, type ChatMsg } from "./chatPersist"

const user = (text: string): ChatMsg => ({ id: "1", role: "user", text })

// Minimal in-memory Storage — vitest runs in node with no DOM, and pulling in
// jsdom just for this would change every other test's environment.
beforeAll(() => {
  const m = new Map<string, string>()
  ;(globalThis as { sessionStorage?: unknown }).sessionStorage = {
    getItem: (k: string) => (m.has(k) ? m.get(k)! : null),
    setItem: (k: string, v: string) => void m.set(k, v),
    removeItem: (k: string) => void m.delete(k),
    clear: () => m.clear(),
  }
})

afterEach(() => sessionStorage.clear())

describe("chatPersist", () => {
  it("round-trips a thread (THE bug: this used to vanish)", () => {
    saveThread("acme", [user("plan my week")])
    expect(loadThread("acme")).toEqual([user("plan my week")])
  })

  it("keys by brand — no cross-brand bleed", () => {
    saveThread("acme", [user("acme secret")])
    saveThread("globex", [user("globex secret")])
    expect(loadThread("acme")[0].text).toBe("acme secret")
    expect(loadThread("globex")[0].text).toBe("globex secret")
    expect(chatKey("acme")).not.toBe(chatKey("globex"))
  })

  it("empty thread clears the stored key", () => {
    saveThread("acme", [user("x")])
    saveThread("acme", [])
    expect(sessionStorage.getItem(chatKey("acme"))).toBeNull()
  })

  it("downgrades a stale 'running' dispatch to 'pending' on restore", () => {
    const msg: ChatMsg = {
      id: "2", role: "assistant", text: "on it",
      dispatch: { agent_name: "Trend Researcher", rationale: "r", status: "running" },
    }
    saveThread("acme", [msg])
    expect(loadThread("acme")[0].dispatch?.status).toBe("pending")
  })

  it("survives corrupt / non-array storage without crashing", () => {
    sessionStorage.setItem(chatKey("acme"), "{not json")
    expect(loadThread("acme")).toEqual([])
    sessionStorage.setItem(chatKey("acme"), JSON.stringify({ nope: true }))
    expect(loadThread("acme")).toEqual([])
  })

  it("empty slug is a no-op, not a crash", () => {
    expect(loadThread("")).toEqual([])
    saveThread("", [user("x")]) // must not throw
  })
})
