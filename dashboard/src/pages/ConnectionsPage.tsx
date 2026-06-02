/**
 * Connections — per-brand social account wiring.
 * Each platform's token lives in brands/<slug>/.env (isolated from Grid Control infra).
 * Reads live status from GET /api/brands/<slug>/connections; writes via
 * POST /api/connections/save-token { brand_slug, platform, token, extra }.
 * Cockpit visual language. Never displays raw tokens.
 */
import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Camera, Briefcase, Video, Hash, Music2, Check, X, Loader2 } from "lucide-react"
import { apiFetch } from "@/lib/api"
import { useBrandStore } from "@/store/brandStore"
import {
  CockpitRoot, Card, Eyebrow, PrimaryButton, SoftButton, StatusDot, STATUS,
} from "@/components/cockpit/primitives"

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
  linkedin:  { name: "LinkedIn",  icon: Briefcase, tokenLabel: "LinkedIn access token", extra: { key: "LINKEDIN_URN", label: "Member/Org URN (optional)" } },
  youtube:   { name: "YouTube",   icon: Video,  tokenLabel: "YouTube API key / OAuth token" },
  twitter:   { name: "X / Twitter", icon: Hash,  tokenLabel: "Bearer token" },
  tiktok:    { name: "TikTok",    icon: Music2, tokenLabel: "TikTok access token" },
}

export function ConnectionsPage() {
  const { activeBrand } = useBrandStore()
  const slug = activeBrand.slug
  const qc = useQueryClient()
  const [editing, setEditing] = useState<string | null>(null)
  const [token, setToken] = useState("")
  const [extra, setExtra] = useState("")

  const { data, isLoading } = useQuery({
    queryKey: ["connections", slug],
    enabled: !!slug,
    queryFn: async () => {
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
      <CockpitRoot>
        <div className="mx-auto max-w-[900px] px-6 py-16 text-center text-zinc-500">
          No brand selected. Onboard or pick a brand first.
        </div>
      </CockpitRoot>
    )
  }

  return (
    <CockpitRoot>
      <div className="mx-auto max-w-[900px] px-6 pb-20 pt-6">
        <div className="mb-6">
          <Eyebrow>{activeBrand.name} · platform wiring</Eyebrow>
          <h1 className="mt-1 text-[22px] font-semibold tracking-tight text-zinc-100">Connections</h1>
          <p className="mt-1.5 text-[13px] text-zinc-500">
            Each token is stored in this brand’s private <span className="font-mono text-zinc-400">.env</span>, isolated from Grid Control. Tokens are never displayed back.
          </p>
        </div>

        <Card className="divide-y divide-white/[0.06]">
          {isLoading && (
            <div className="flex items-center gap-2 px-5 py-8 text-[13px] text-zinc-500">
              <Loader2 size={15} className="animate-spin" /> Checking connections…
            </div>
          )}

          {(data ?? []).map((c) => {
            const m = META[c.platform]
            if (!m) return null
            const Icon = m.icon
            const tone: keyof typeof STATUS = c.connected ? "green" : c.has_token ? "red" : "gray"
            const isOpen = editing === c.platform
            return (
              <div key={c.platform} className="px-5 py-4">
                <div className="flex items-center justify-between gap-4">
                  <div className="flex items-center gap-3">
                    <span className="grid h-9 w-9 place-items-center rounded-lg border border-white/[0.08] bg-white/[0.02]">
                      <Icon size={17} className="text-zinc-300" />
                    </span>
                    <div>
                      <div className="text-[14px] font-semibold text-zinc-100">{m.name}</div>
                      <div className="mt-0.5 flex items-center gap-2 text-[12px] text-zinc-500">
                        <StatusDot tone={tone} />
                        <span>
                          {c.connected ? c.account : c.has_token ? c.account : "Not connected"}
                        </span>
                        {c.handle && <span className="font-mono text-zinc-600">· {c.handle}</span>}
                      </div>
                    </div>
                  </div>
                  {!isOpen && (
                    <SoftButton onClick={() => openEditor(c.platform)}>
                      {c.has_token ? "Update" : "Connect"}
                    </SoftButton>
                  )}
                </div>

                {isOpen && (
                  <div className="mt-4 rounded-xl border border-white/[0.08] bg-[#0e0f12] p-4">
                    <label className="font-mono text-[10.5px] uppercase tracking-[0.14em] text-zinc-500">
                      {m.tokenLabel}
                    </label>
                    <input
                      autoFocus
                      type="password"
                      value={token}
                      onChange={(e) => setToken(e.target.value)}
                      placeholder="Paste token…"
                      className="mt-1.5 w-full rounded-lg border border-white/[0.09] bg-[#141518] px-3.5 py-2.5 text-[13.5px] text-zinc-100 outline-none placeholder:text-zinc-600 focus:border-white/[0.18]"
                    />
                    {m.extra && (
                      <input
                        type="text"
                        value={extra}
                        onChange={(e) => setExtra(e.target.value)}
                        placeholder={m.extra.label}
                        className="mt-2 w-full rounded-lg border border-white/[0.09] bg-[#141518] px-3.5 py-2.5 text-[13px] text-zinc-100 outline-none placeholder:text-zinc-600 focus:border-white/[0.18]"
                      />
                    )}
                    {save.isError && (
                      <div className="mt-2 text-[12px]" style={{ color: STATUS.red.fg }}>
                        {(save.error as Error)?.message}
                      </div>
                    )}
                    <div className="mt-3 flex items-center gap-2">
                      <PrimaryButton
                        onClick={() => save.mutate(c.platform)}
                        disabled={!token.trim() || save.isPending}
                        icon={save.isPending ? undefined : Check}
                      >
                        {save.isPending ? "Verifying…" : "Save & verify"}
                      </PrimaryButton>
                      <SoftButton icon={X} onClick={() => { setEditing(null); setToken(""); setExtra("") }}>
                        Cancel
                      </SoftButton>
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </Card>

        <div className="mt-4 font-mono text-[11px] text-zinc-600">
          Green = verified live · Red = token set but failing · Grey = no token yet
        </div>
      </div>
    </CockpitRoot>
  )
}
