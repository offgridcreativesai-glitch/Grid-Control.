/** Google/magic-link sign-ins can return to the LANDING page (Supabase falls
 * back to its Site URL — the site root — whenever the requested redirect
 * isn't honored). The landing page lives OUTSIDE AuthGate, so the login code
 * in the URL was silently dropped and the user stayed signed out on landing
 * (Jul 16 bug, Gaurav's fresh Chrome login on localhost).
 * If the URL carries auth params, forward them to /command where AuthGate's
 * supabase client completes the sign-in. Pure so the decision is testable. */
export function authReturnPath(search: string, hash: string): string | null {
  const params = new URLSearchParams(search)
  if (params.has("code") || params.has("token_hash")) return `/command${search}${hash}`
  if (/(^|[#&])access_token=/.test(hash)) return `/command${search}${hash}`
  if (params.has("error") || params.has("error_description")) return `/signin${search}`
  return null
}
