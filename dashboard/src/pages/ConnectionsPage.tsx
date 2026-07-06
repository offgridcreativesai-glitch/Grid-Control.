/**
 * Connections — per-brand social account wiring.
 * Each platform's token lives in brands/<slug>/.env (isolated from Grid Control infra).
 * Reads live status from GET /api/brands/<slug>/connections; writes via
 * POST /api/connections/save-token { brand_slug, platform, token, extra }.
 * Cinematic look. Never displays raw tokens. Client-safe copy.
 */
import { useState, useEffect } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Camera, Briefcase, Video, Hash, Music2, Check, X, Loader2 } from "lucide-react"
import { apiFetch } from "@/lib/api"
import { useBrandStore } from "@/store/brandStore"
import { isDemo, DEMO_CONNECTIONS } from "@/lib/demo"

type Conn = {
  platform: string
  handle: string
  env_key: string
  has_token: boolean
  connected: boolean
  account: string
}

const META: Record<string, { name: string; icon: typeof Camera; tokenLabel: string; extra?: { key: string; label: string } }> = {
  instagram: { name: "Instagram", icon: Camera, tokenLabel: "Instagram Graph / Login token", extra: { key: "IG_USER_ID", label: "IG User ID (optional)" } },
  linkedin: { name: "LinkedIn", icon: Briefcase, tokenLabel: "LinkedIn access token", extra: { key: "LINKEDIN_URN", label: "Member/Org URN (optional)" } },
  youtube: { name: "YouTube", icon: Video, tokenLabel: "YouTube API key / OAuth token" },
  twitter: { name: "X / Twitter", icon: Hash, tokenLabel: "Bearer token" },
  tiktok: { name: "TikTok", icon: Music2, tokenLabel: "TikTok access token" },
}

// Platforms wired for one-click OAuth (vs. manual token paste). `key` = the
// query param the callback bounces back with (/connections?<key>=connected).
const OAUTH_PLATFORMS: Record<string, { key: string; name: string }> = {
  instagram: { key: "ig", name: "Instagram" },
  youtube: { key: "yt", name: "YouTube" },
  linkedin: { key: "li", name: "LinkedIn" },
  twitter: { key: "tw", name: "X" },
}

const TONE = {
  green: "var(--emerald)",
  red: "var(--destructive)",
  gray: "var(--status-blocked)",
} as const

export function ConnectionsPage() {
  const { activeBrand } = useBrandStore()
  const slug = activeBrand.slug
  const qc = useQueryClient()
  const [editing, setEditing] = useState<string | null>(null)
  const [token, setToken] = useState("")
  const [extra, setExtra] = useState("")
  const [oauthBanner, setOauthBanner] = useState<{ ok: boolean; msg: string } | null>(null)
  const [oauthLoading, setOauthLoading] = useState<string | null>(null) // platform id

  // Catch any OAuth round-trip return (/connections?ig=… or ?yt=…)
  useEffect(() => {
    const p = new URLSearchParams(window.location.search)
    for (const [platform, meta] of Object.entries(OAUTH_PLATFORMS)) {
      const st = p.get(meta.key)
      if (!st) continue
      const detail = p.get(`${meta.key}_detail`) || ""
      // If opened as an OAuth popup (e.g. from onboarding), relay to opener + close.
      if (window.opener && window.opener !== window) {
        try { window.opener.postMessage({ type: "oauth_connect", platform, status: st, detail }, window.location.origin) } catch { /* ignore */ }
        window.close()
        return
      }
      if (st === "connected") setOauthBanner({ ok: true, msg: `${meta.name} connected${detail ? ` — ${detail}` : ""}` })
      else if (st === "denied") setOauthBanner({ ok: false, msg: `${meta.name} connection cancelled.` })
      else setOauthBanner({ ok: false, msg: `${meta.name} connect failed${detail ? `: ${detail}` : ""}` })
      qc.invalidateQueries({ queryKey: ["connections", slug] })
      window.history.replaceState({}, "", window.location.pathname)
      break
    }
  }, [qc, slug])

  async function connectOAuth(platform: string) {
    setOauthLoading(platform)
    try {
      const r = await apiFetch(`/api/connections/${platform}/authorize-url?brand_slug=${encodeURIComponent(slug)}`)
      const j = await r.json()
      if (!j.success || !j.data?.url) throw new Error(j.error || "Could not start connect")
      window.location.assign(j.data.url)
    } catch (e) {
      setOauthBanner({ ok: false, msg: (e as Error).message })
      setOauthLoading(null)
    }
  }

  const { data, isLoading } = useQuery({
    queryKey: ["connections", slug],
    enabled: !!slug,
    queryFn: async () => {
      if (isDemo()) return DEMO_CONNECTIONS as Conn[]
      const r = await apiFetch(`/api/brands/${slug}/connections`)
      const j = await r.json()
      return (j.data ?? []) as Conn[]
    },
  })

  const save = useMutation({
    mutationFn: async (platform: string) => {
      const m = META[platform]
      const body: Record<string, unknown> = { brand_slug: slug, platform, token: token.trim() }
      if (m.extra && extra.trim()) body.extra = { [m.extra.key]: extra.trim() }
      const r = await apiFetch("/api/connections/save-token", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
      })
      const j = await r.json()
      if (!j.success) throw new Error(j.error || "Save failed")
      return j.data
    },
    onSuccess: () => {
      setEditing(null); setToken(""); setExtra("")
      qc.invalidateQueries({ queryKey: ["connections", slug] })
    },
  })

  function openEditor(platform: string) {
    setEditing(platform); setToken(""); setExtra("")
  }

  if (!slug) {
    return (
      <div className="min-h-full bg-background/60">
        <div className="mx-auto max-w-[900px] px-6 py-16 text-center text-[14px] text-muted-foreground">
          No brand selected. Onboard or pick a brand first.
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-full bg-background/60">
      <div className="mx-auto max-w-[900px] px-6 pb-20 pt-10">
        <div className="mb-7">
          <h1 className="font-display text-[26px] font-semibold tracking-tight text-foreground">Connections</h1>
          <p className="mt-1.5 text-[14px] text-muted-foreground">
            Connect <span className="text-foreground">{activeBrand.name}</span>&rsquo;s accounts so your team can publish for you. Your keys are stored privately and never shown back.
          </p>
        </div>

        {oauthBanner && (
          <div
            className="mb-4 rounded-xl border px-4 py-3 text-[13px]"
            style={{
              borderColor: oauthBanner.ok ? "var(--emerald)" : "var(--destructive)",
              color: oauthBanner.ok ? "var(--emerald)" : "var(--destructive)",
              background: "rgba(255,255,255,0.02)",
            }}
          >
            {oauthBanner.msg}
          </div>
        )}

        <div className="glass-panel divide-y divide-border overflow-hidden rounded-2xl">
          {isLoading && (
            <div className="flex items-center gap-2 px-5 py-8 text-[13px] text-muted-foreground">
              <Loader2 size={15} className="animate-spin" /> Checking connections…
            </div>
          )}

          {(data ?? []).map((c) => {
            const m = META[c.platform]
            if (!m) return null
            const Icon = m.icon
            const tone: keyof typeof TONE = c.connected ? "green" : c.has_token ? "red" : "gray"
            const isOpen = editing === c.platform
            return (
              <div key={c.platform} className="px-5 py-4">
                <div className="flex items-center justify-between gap-4">
                  <div className="flex items-center gap-3">
                    <span className="grid h-9 w-9 place-items-center rounded-lg border border-border bg-white/[0.02]">
                      <Icon size={17} className="text-foreground/80" />
                    </span>
                    <div>
                      <div className="text-[14px] font-semibold text-foreground">{m.name}</div>
                      <div className="mt-0.5 flex items-center gap-2 text-[12px] text-muted-foreground">
                        <span className="h-2 w-2 rounded-full" style={{ background: TONE[tone] }} />
                        <span>{c.connected ? c.account : c.has_token ? c.account : "Not connected"}</span>
                        {c.handle && <span className="text-muted-foreground/70">· {c.handle}</span>}
                      </div>
                    </div>
                  </div>
                  {!isOpen && OAUTH_PLATFORMS[c.platform] && (
                    <button
                      onClick={() => connectOAuth(c.platform)}
                      disabled={oauthLoading === c.platform}
                      className="inline-flex items-center gap-1.5 rounded-lg border border-border px-3.5 py-1.5 text-[12.5px] font-medium text-foreground/80 transition-colors hover:bg-white/[0.05] hover:text-foreground disabled:opacity-50"
                    >
                      {oauthLoading === c.platform && <Loader2 size={13} className="animate-spin" />}
                      {c.has_token ? "Reconnect" : `Connect ${OAUTH_PLATFORMS[c.platform].name}`}
                    </button>
                  )}
                  {!isOpen && !OAUTH_PLATFORMS[c.platform] && (
                    <button
                      onClick={() => openEditor(c.platform)}
                      className="rounded-lg border border-border px-3.5 py-1.5 text-[12.5px] font-medium text-foreground/80 transition-colors hover:bg-white/[0.05] hover:text-foreground"
                    >
                      {c.has_token ? "Update" : "Connect"}
                    </button>
                  )}
                </div>

                {isOpen && (
                  <div className="mt-4 rounded-xl border border-border bg-black/20 p-4">
                    <label className="text-[10.5px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                      {m.tokenLabel}
                    </label>
                    <input
                      autoFocus
                      type="password"
                      value={token}
                      onChange={(e) => setToken(e.target.value)}
                      placeholder="Paste token…"
                      className="mt-1.5 w-full rounded-lg border border-input bg-black/30 px-3.5 py-2.5 text-[13.5px] text-foreground outline-none placeholder:text-muted-foreground/70 focus:border-primary/50"
                    />
                    {m.extra && (
                      <input
                        type="text"
                        value={extra}
                        onChange={(e) => setExtra(e.target.value)}
                        placeholder={m.extra.label}
                        className="mt-2 w-full rounded-lg border border-input bg-black/30 px-3.5 py-2.5 text-[13px] text-foreground outline-none placeholder:text-muted-foreground/70 focus:border-primary/50"
                      />
                    )}
                    {save.isError && (
                      <div className="mt-2 text-[12px] text-destructive">{(save.error as Error)?.message}</div>
                    )}
                    <div className="mt-3 flex items-center gap-2">
                      <button
                        onClick={() => save.mutate(c.platform)}
                        disabled={!token.trim() || save.isPending}
                        className="inline-flex items-center gap-1.5 rounded-lg bg-emerald px-3.5 py-2 text-[13px] font-semibold text-[#06120E] transition-[filter] hover:brightness-110 disabled:opacity-40"
                      >
                        {save.isPending ? <Loader2 size={15} className="animate-spin" /> : <Check size={15} />}
                        {save.isPending ? "Verifying…" : "Save & verify"}
                      </button>
                      <button
                        onClick={() => { setEditing(null); setToken(""); setExtra("") }}
                        className="inline-flex items-center gap-1.5 rounded-lg border border-border px-3.5 py-2 text-[12.5px] font-medium text-foreground/80 transition-colors hover:bg-white/[0.05]"
                      >
                        <X size={14} /> Cancel
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>

        <div className="mt-4 text-[11.5px] text-muted-foreground">
          <span style={{ color: TONE.green }}>●</span> Live ·{" "}
          <span style={{ color: TONE.red }}>●</span> Needs attention ·{" "}
          <span style={{ color: TONE.gray }}>●</span> Not connected
        </div>
      </div>
    </div>
  )
}
