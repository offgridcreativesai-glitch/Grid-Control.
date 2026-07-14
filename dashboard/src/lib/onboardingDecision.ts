// The decision OnboardingGuard makes. Pure + testable on purpose:
// the onboarding-restart bug (Jul 14) lived here — an API error was mistaken
// for "no brands" and bounced an onboarded brand back to onboarding.
// This function is guarded by onboardingDecision.test.ts so that bug can't return.

export type OnboardingState = {
  isLoading: boolean
  isError: boolean
  brandCount: number
  demo: boolean
  pathname: string
}

export type OnboardingOutcome =
  | "wait" // still loading — render nothing
  | "backend-down" // API unreachable — show retry, NEVER treat as no-brands
  | "onboarding" // genuinely no brands — go to onboarding
  | "app" // has brands (or demo) — render the app

export function onboardingDecision(s: OnboardingState): OnboardingOutcome {
  if (s.isLoading) return "wait"
  if (s.isError && !s.demo) return "backend-down"
  const hasBrands = s.brandCount > 0
  if (!s.demo && !hasBrands && s.pathname !== "/onboarding") return "onboarding"
  return "app"
}
