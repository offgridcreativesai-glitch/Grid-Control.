/** Pins the SSE 401-hammering bug (UAT Jul 7): the FE opened
 * EventSource("/api/events") with NO token while the backend requires ?token=
 * (EventSource can't send headers) -> guaranteed 401 -> infinite reconnect.
 * Old logic always connected (url for a null token). Fixed logic: no token,
 * no connection. */
import { describe, expect, it } from "vitest"
import { sseUrl } from "./sse"

describe("sseUrl", () => {
  it("returns null when logged out — never connect to a guaranteed 401", () => {
    expect(sseUrl(null)).toBeNull()
    expect(sseUrl(undefined)).toBeNull()
    expect(sseUrl("")).toBeNull()
  })

  it("builds the tokened URL the backend contract requires", () => {
    expect(sseUrl("abc123")).toBe("/api/events?token=abc123")
  })

  it("URL-encodes the token", () => {
    expect(sseUrl("a+b/c=")).toBe("/api/events?token=a%2Bb%2Fc%3D")
  })
})
