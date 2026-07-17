/** Pins the blank-screen-after-login bug (Jul 16, deployed /command):
 * a stale stored session made supabase auth THROW during boot
 * (AuthApiError: Invalid Refresh Token) -> init() rejected before set() ->
 * loading stayed true forever -> permanent dark "Loading..." (blank) screen.
 * Old code FAILS these (unhandled rejection, loading:true); fixed init
 * resolves every auth failure to signed-out. */
import { beforeEach, describe, expect, it, vi } from "vitest"

const getSession = vi.fn()
const onAuthStateChange = vi.fn(() => ({ data: { subscription: { unsubscribe: vi.fn() } } }))

vi.mock("@/lib/supabase", () => ({
  supabase: { auth: { get getSession() { return getSession }, get onAuthStateChange() { return onAuthStateChange } } },
}))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn(async () => ({ ok: false })) }))

import { useAuthStore } from "./authStore"

beforeEach(() => {
  useAuthStore.setState({ user: null, session: null, loading: true, isSuperAdmin: false })
  getSession.mockReset()
  onAuthStateChange.mockClear()
})

describe("authStore.init", () => {
  it("a throwing auth boot resolves to signed-out, never a blank hang", async () => {
    getSession.mockRejectedValue(new Error("AuthApiError: Invalid Refresh Token"))
    await useAuthStore.getState().init()
    const s = useAuthStore.getState()
    expect(s.loading).toBe(false) // THE bug: stayed true on old code
    expect(s.user).toBeNull()
  })

  it("an auth error result also resolves to signed-out", async () => {
    getSession.mockResolvedValue({ data: { session: null }, error: { message: "bad" } })
    await useAuthStore.getState().init()
    expect(useAuthStore.getState().loading).toBe(false)
    expect(useAuthStore.getState().user).toBeNull()
  })

  it("still registers the auth listener after a failed boot (later login recovers)", async () => {
    getSession.mockRejectedValue(new Error("boom"))
    await useAuthStore.getState().init()
    expect(onAuthStateChange).toHaveBeenCalled()
  })

  it("a healthy signed-out boot clears loading", async () => {
    getSession.mockResolvedValue({ data: { session: null }, error: null })
    await useAuthStore.getState().init()
    expect(useAuthStore.getState().loading).toBe(false)
  })
})
