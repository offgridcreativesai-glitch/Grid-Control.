/** Pins the login-code-dropped-on-landing bug (Jul 16): a fresh Google
 * sign-in returning to "/" rendered LandingPage outside AuthGate — the
 * ?code= was never exchanged, user stayed signed out ("it sent me back to
 * the landing page"). Old behavior = null for every input (landing always
 * rendered); fixed = auth params forward into the app. */
import { describe, expect, it } from "vitest"
import { authReturnPath } from "./authReturn"

describe("authReturnPath", () => {
  it("forwards a PKCE code to /command (THE bug)", () => {
    expect(authReturnPath("?code=abc123", "")).toBe("/command?code=abc123")
  })

  it("forwards implicit-flow tokens in the hash", () => {
    expect(authReturnPath("", "#access_token=xyz&token_type=bearer"))
      .toBe("/command#access_token=xyz&token_type=bearer")
  })

  it("forwards magic-link token_hash", () => {
    expect(authReturnPath("?token_hash=th&type=magiclink", ""))
      .toBe("/command?token_hash=th&type=magiclink")
  })

  it("routes auth errors to the sign-in page", () => {
    expect(authReturnPath("?error=access_denied&error_description=x", ""))
      .toBe("/signin?error=access_denied&error_description=x")
  })

  it("plain landing visits stay on landing", () => {
    expect(authReturnPath("", "")).toBeNull()
    expect(authReturnPath("?utm_source=x", "#pricing")).toBeNull()
  })
})
