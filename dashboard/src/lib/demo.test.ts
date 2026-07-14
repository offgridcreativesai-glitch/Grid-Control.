import { describe, it, expect } from "vitest"
import { demoDecision } from "./demo"

describe("demoDecision", () => {
  // THE bug (Jul 14): a real Supabase session was present but demo hijacked because the
  // decision ran before auth populated. hasRealSession derived synchronously fixes it.
  it("real session present → NEVER demo, even with the flag set", () => {
    expect(demoDecision({ isDev: true, demoFlag: true, hasRealSession: true })).toBe(false)
  })

  it("flag set, no real session, DEV → demo (intended preview path)", () => {
    expect(demoDecision({ isDev: true, demoFlag: true, hasRealSession: false })).toBe(true)
  })

  it("never demo in a production build", () => {
    expect(demoDecision({ isDev: false, demoFlag: true, hasRealSession: false })).toBe(false)
  })

  it("no flag → never demo", () => {
    expect(demoDecision({ isDev: true, demoFlag: false, hasRealSession: false })).toBe(false)
  })
})
