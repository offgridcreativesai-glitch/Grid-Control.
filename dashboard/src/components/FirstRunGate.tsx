/**
 * FirstRunGate — the pre-flight validation gate (onboarding flow, piece 1).
 *
 * Shown on the Command Center BEFORE a brand has a brand-book. Atlas verifies
 * every handle live (own IG + competitors + other socials) via /validate-handles
 * — zero assumptions. Any handle that doesn't resolve is surfaced for the user to
 * correct in place (→ /profile/handles → re-check). Only when ALL resolve does the
 * "Generate my brand report" action unlock (→ brand-book/generate, PAID).
 *
 * Later pieces (status loop + review/approve card) replace the "generating" state.
 */
import { useState } from "react"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { Loader2, Check, AlertTriangle, ShieldCheck, Sparkles, RefreshCw } from "lucide-react"
import { apiFetch } from "@/lib/api"
import { useBrandStore } from "@/store/brandStore"

type HandleResult = { platform: string; handle: string; role?: string; status: string; note?: string }
type Phase = "idle" | "validating" | "results" | "generating" | "started"

const keyOf = (i: HandleResult) => `${i.platform}:${i.role}:${i.handle}`
const PLATFORM_LABEL: Record<string, string> = {
  instagram: "Instagram", youtube: "YouTube", x: "X", linkedin: "LinkedIn", tiktok: "TikTok",
}

export function FirstRunGate() {
  const { activeBrand } = useBrandStore()
  const slug = activeBrand.slug
  const qc = useQueryClient()

  const { data: bb } = useQuery({
    queryKey: ["brand-book", slug],
    enabled: !!slug,
    queryFn: async () => (await (await apiFetch(`/api/brands/${slug}/brand-book`)).json()),
  })
  const status: string = bb?.data?.status ?? "none"

  const [phase, setPhase] = useState<Phase>("idle")
  const [results, setResults] = useState<HandleResult[]>([])
  const [edits, setEdits] = useState<Record<string, string>>({})
  const [savingKey, setSavingKey] = useState<string | null>(null)
  const [err, setErr] = useState("")

  // Only the pre-report gate lives here. Once a report exists, later pieces take over.
  if (!slug || status !== "none") return null

  const invalid = results.filter((r) => r.status === "not_found")
  const checked = results.filter((r) => r.status !== "skipped")
  const allValid = phase === "results" && results.length > 0 && invalid.length === 0
  const generating = phase === "generating"

  async function validate() {
    setErr(""); setPhase("validating")
    try {
      const r = await apiFetch(`/api/brands/${slug}/validate-handles`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: "{}",
      })
      const j = await r.json()
      if (!j.success) throw new Error(j.error || "Validation failed")
      setResults(j.data.results || [])
      setPhase("results")
    } catch (e) { setErr((e as Error).message); setPhase("idle") }
  }

  async function saveFix(item: HandleResult) {
    const nv = (edits[keyOf(item)] || "").trim().replace(/^@+/, "")
    if (!nv) return
    setErr(""); setSavingKey(keyOf(item))
    const payload: Record<string, unknown> = {}
    if (item.platform === "instagram" && item.role === "own") payload.instagram_handle = nv
    else if (item.platform === "instagram" && item.role === "competitor") {
      payload.competitor_handles = results
        .filter((r) => r.role === "competitor" && r.platform === "instagram")
        .map((r) => (r.handle === item.handle ? nv : r.handle))
    } else payload.social_handles = { [item.platform]: nv }
    try {
      const r = await apiFetch(`/api/brands/${slug}/profile/handles`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
      })
      const j = await r.json()
      if (!j.success) throw new Error(j.error || "Save failed")
      setSavingKey(null)
      await validate()
    } catch (e) { setErr((e as Error).message); setSavingKey(null) }
  }

  async function generate() {
    setErr(""); setPhase("generating")
    try {
      const cr = await (await apiFetch(`/api/brands/${slug}/connections`)).json()
      const igOn = (cr.data || []).some((c: { platform: string; connected: boolean }) => c.platform === "instagram" && c.connected)
      const r = await apiFetch(`/api/brands/${slug}/brand-book/generate`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode: igOn ? "onboarding_connected" : "cold_sellable" }),
      })
      const j = await r.json()
      if (!j.success) throw new Error(j.error || "Could not start the report")
      setPhase("started")
      qc.invalidateQueries({ queryKey: ["brand-book", slug] })
    } catch (e) { setErr((e as Error).message); setPhase("results") }
  }

  return (
    <div className="glass-panel mt-7 overflow-hidden rounded-2xl border border-border">
      <div className="flex items-center gap-2 border-b border-border px-4 py-3">
        <ShieldCheck size={16} className="text-primary" />
        <span className="text-[13.5px] font-semibold text-foreground">Before I research — let&rsquo;s verify your accounts</span>
      </div>

      <div className="p-4">
        {phase === "started" ? (
          <div className="flex items-start gap-2.5 text-[13.5px] text-foreground/90">
            <Sparkles size={16} className="mt-0.5 shrink-0 text-primary" />
            <p>On it — I&rsquo;m researching your brand and building your report now. This takes a few minutes; I&rsquo;ll have it ready for you to review shortly.</p>
          </div>
        ) : (
          <>
            <p className="text-[13px] leading-relaxed text-muted-foreground">
              I check every handle live before spending anything on research — no guessing. If one doesn&rsquo;t resolve, you can fix it right here.
            </p>

            {phase === "idle" && (
              <button
                onClick={validate}
                className="mt-3 inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-[13px] font-semibold text-primary-foreground transition-transform hover:scale-[1.02]"
              >
                <ShieldCheck size={15} /> Verify accounts
              </button>
            )}

            {phase === "validating" && (
              <div className="mt-3 flex items-center gap-2 text-[13px] text-muted-foreground">
                <Loader2 size={15} className="animate-spin" /> Checking each handle live…
              </div>
            )}

            {(phase === "results" || phase === "generating") && (
              <div className="mt-3 space-y-2">
                {checked.map((item) => {
                  const bad = item.status === "not_found"
                  const k = keyOf(item)
                  return (
                    <div key={k} className="rounded-xl border border-border bg-white/[0.02] px-3.5 py-2.5">
                      <div className="flex items-center justify-between gap-3">
                        <div className="flex items-center gap-2 text-[13px]">
                          {bad ? <AlertTriangle size={14} className="text-destructive" />
                               : <Check size={14} className="text-emerald" />}
                          <span className="font-medium text-foreground">@{item.handle}</span>
                          <span className="text-[11.5px] text-muted-foreground">
                            {PLATFORM_LABEL[item.platform] || item.platform}
                            {item.role === "competitor" ? " · competitor" : ""}
                          </span>
                        </div>
                        <span className={"text-[11.5px] font-medium " + (bad ? "text-destructive" : "text-emerald")}>
                          {bad ? "Not found" : "Verified"}
                        </span>
                      </div>
                      {bad && (
                        <div className="mt-2 flex items-center gap-2">
                          <input
                            value={edits[k] ?? ""}
                            onChange={(e) => setEdits((s) => ({ ...s, [k]: e.target.value }))}
                            placeholder="Correct handle…"
                            className="w-full rounded-lg border border-input bg-black/30 px-3 py-1.5 text-[12.5px] text-foreground outline-none placeholder:text-muted-foreground/70 focus:border-primary/50"
                          />
                          <button
                            onClick={() => saveFix(item)}
                            disabled={savingKey === k || !(edits[k] || "").trim()}
                            className="inline-flex shrink-0 items-center gap-1 rounded-lg border border-border px-3 py-1.5 text-[12px] font-medium text-foreground/85 transition-colors hover:bg-white/[0.05] disabled:opacity-40"
                          >
                            {savingKey === k ? <Loader2 size={13} className="animate-spin" /> : <RefreshCw size={13} />}
                            Save & recheck
                          </button>
                        </div>
                      )}
                    </div>
                  )
                })}

                {invalid.length > 0 && (
                  <p className="text-[12px] text-destructive">
                    {invalid.length} handle{invalid.length > 1 ? "s" : ""} couldn&rsquo;t be found. Fix {invalid.length > 1 ? "them" : "it"} above, and I&rsquo;ll re-check before researching.
                  </p>
                )}

                {allValid && (
                  <div className="rounded-xl border border-emerald/40 bg-emerald/10 px-3.5 py-2.5 text-[13px] text-emerald">
                    <Check size={14} className="mr-1 inline" /> All accounts verified. Ready to research.
                  </div>
                )}

                <div className="flex items-center gap-2 pt-1">
                  <button
                    onClick={generate}
                    disabled={!allValid || generating}
                    className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-[13px] font-semibold text-primary-foreground transition-transform hover:scale-[1.02] disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    {generating ? <Loader2 size={15} className="animate-spin" /> : <Sparkles size={15} />}
                    Generate my brand report
                  </button>
                  <button
                    onClick={validate}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-border px-3 py-2 text-[12.5px] font-medium text-foreground/80 transition-colors hover:bg-white/[0.05]"
                  >
                    <RefreshCw size={13} /> Re-check
                  </button>
                </div>
              </div>
            )}
          </>
        )}

        {err && <p className="mt-2 text-[12px] text-destructive">{err}</p>}
      </div>
    </div>
  )
}
