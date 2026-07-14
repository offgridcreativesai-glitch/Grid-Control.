import { describe, it, expect } from "vitest"
import { onboardingDecision } from "./onboardingDecision"

const base = { isLoading: false, isError: false, brandCount: 1, demo: false, pathname: "/command" }

describe("onboardingDecision", () => {
  it("still loading → wait, never redirect", () => {
    expect(onboardingDecision({ ...base, isLoading: true })).toBe("wait")
  })

  // THE Jul 14 bug: Flask down → brands fetch errors → must show backend-down,
  // NOT bounce an already-onboarded brand back to onboarding.
  it("API error → backend-down, NOT onboarding", () => {
    expect(onboardingDecision({ ...base, isError: true, brandCount: 0 })).toBe("backend-down")
  })

  it("genuinely no brands → onboarding", () => {
    expect(onboardingDecision({ ...base, brandCount: 0 })).toBe("onboarding")
  })

  it("has brands → app", () => {
    expect(onboardingDecision(base)).toBe("app")
  })

  it("already on /onboarding with no brands → stay (no redirect loop)", () => {
    expect(onboardingDecision({ ...base, brandCount: 0, pathname: "/onboarding" })).toBe("app")
  })
})
