/**
 * BrandReportCard — onboarding flow pieces 2–4 (the report status loop + review card).
 *
 * Takes over from FirstRunGate once a report run starts. Self-gated on brand-book
 * status:
 *   · generating       → "Atlas is researching…" + polls every 5s
 *   · pending_review   → review card: summary + Open report (PDF) · Approve · Request changes
 *   · change_requested → revision recorded → Regenerate (scoped re-run) + revisions-remaining
 * Approve (piece 5) writes the Foundation + seeds memory server-side.
 */
import { useState } from "react"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { Loader2, FileText, Check, MessageSquare, RefreshCw, Sparkles, X } from "lucide-react"
import { apiFetch } from "@/lib/api"
import { useBrandStore } from "@/store/brandStore"

type Metric = { label: string; value: string | number; basis?: string }
type Summary = {
  brand?: string; version?: string; date?: string; mode?: string; data_basis?: string
  scorecard_metrics?: Metric[]
}
type Busy = "" | "approve" | "change" | "regen" | "pdf"

export function BrandReportCard() {
  const { activeBrand } = useBrandStore()
  const slug = activeBrand.slug
  const qc = useQueryClient()

  const [busy, setBusy] = useState<Busy>("")
  const [showNotes, setShowNotes] = useState(false)
  const [notes, setNotes] = useState("")
  const [err, setErr] = useState("")
  const [done, setDone] = useState("")

  const { data: bb } = useQuery({
    queryKey: ["brand-book", slug],
    enabled: !!slug,
    queryFn: async () => (await (await apiFetch(`/api/brands/${slug}/brand-book`)).json()),
    refetchInterval: (q) =>
      ((q.state.data as { data?: { status?: string } })?.data?.status === "generating" ? 5000 : false),
  })

  const d = bb?.data
  const status: string = d?.status ?? "none"
  if (!slug || !["generating", "pending_review", "change_requested", "error"].includes(status)) return null

  const summary: Summary = d?.report_summary || {}
  const revCount: number = d?.revision_count ?? 0
  const scopeFlag: boolean = d?.scope_flag ?? false

  async function openPdf() {
    setErr(""); setBusy("pdf")
    try {
      const r = await apiFetch(`/api/brands/${slug}/brand-book/pdf`)
      if (!r.ok) throw new Error("Report PDF isn't available yet")
      const blob = await r.blob()
      window.open(URL.createObjectURL(blob), "_blank")
    } catch (e) { setErr((e as Error).message) }
    setBusy("")
  }

  async function approve() {
    setErr(""); setBusy("approve")
    try {
      const j = await (await apiFetch(`/api/brands/${slug}/brand-book/approve`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: "{}",
      })).json()
      if (!j.success) throw new Error(j.error || "Approve failed")
      setDone(j.data?.message || "Brand foundation approved.")
      qc.invalidateQueries({ queryKey: ["brand-book", slug] })
    } catch (e) { setErr((e as Error).message) }
    setBusy("")
  }

  async function requestChange() {
    if (!notes.trim()) return
    setErr(""); setBusy("change")
    try {
      const j = await (await apiFetch(`/api/brands/${slug}/brand-book/request-change`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ notes: notes.trim() }),
      })).json()
      if (!j.success) throw new Error(j.error || "Could not record change")
      setDone(j.data?.message || "Change requested.")
      setShowNotes(false); setNotes("")
      qc.invalidateQueries({ queryKey: ["brand-book", slug] })
    } catch (e) { setErr((e as Error).message) }
    setBusy("")
  }

  async function regenerate() {
    setErr(""); setBusy("regen")
    try {
      const cr = await (await apiFetch(`/api/brands/${slug}/connections`)).json()
      const igOn = (cr.data || []).some((c: { platform: string; connected: boolean }) => c.platform === "instagram" && c.connected)
      const j = await (await apiFetch(`/api/brands/${slug}/brand-book/generate`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode: igOn ? "onboarding_connected" : "cold_sellable" }),
      })).json()
      if (!j.success) throw new Error(j.error || "Could not start re-run")
      setDone(""); qc.invalidateQueries({ queryKey: ["brand-book", slug] })
    } catch (e) { setErr((e as Error).message) }
    setBusy("")
  }

  // ── generating ──────────────────────────────────────────────────────────────
  if (status === "generating") {
    return (
      <Shell title="Building your brand report">
        <div className="flex items-start gap-2.5 text-[13.5px] text-foreground/90">
          <Loader2 size={16} className="mt-0.5 shrink-0 animate-spin text-primary" />
          <p>I&rsquo;m researching your brand and writing your report — real data, no guesswork. This takes a few minutes; it&rsquo;ll appear here the moment it&rsquo;s ready.</p>
        </div>
      </Shell>
    )
  }

  // ── change_requested ────────────────────────────────────────────────────────
  if (status === "change_requested") {
    return (
      <Shell title="Revision requested">
        <p className="text-[13px] leading-relaxed text-muted-foreground">
          Noted your change{revCount ? ` (revision ${revCount})` : ""}. {scopeFlag
            ? "Heads up — this goes beyond the included revision and counts as new scope, so it's best treated as a separate brief."
            : "I'll re-run the affected research and rework the report."}
        </p>
        <div className="mt-3">
          <button
            onClick={regenerate}
            disabled={busy === "regen"}
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-[13px] font-semibold text-primary-foreground transition-transform hover:scale-[1.02] disabled:opacity-50"
          >
            {busy === "regen" ? <Loader2 size={15} className="animate-spin" /> : <RefreshCw size={15} />}
            Rework the report
          </button>
        </div>
        {err && <p className="mt-2 text-[12px] text-destructive">{err}</p>}
      </Shell>
    )
  }

  // ── error ─────────────────────────────────────────────────────────────────────
  if (status === "error") {
    return (
      <Shell title="The report hit a snag">
        <p className="text-[13px] leading-relaxed text-muted-foreground">
          The report run didn&rsquo;t finish. Your research data is safe — this only needs a
          re-run, and it reuses today&rsquo;s data (no new charges).
        </p>
        {d?.error && (
          <p className="mt-2 rounded-lg border border-border bg-black/20 px-3 py-2 text-[11.5px] text-muted-foreground/80">
            {String(d.error).slice(0, 200)}
          </p>
        )}
        <div className="mt-3">
          <button
            onClick={regenerate}
            disabled={busy === "regen"}
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-[13px] font-semibold text-primary-foreground transition-transform hover:scale-[1.02] disabled:opacity-50"
          >
            {busy === "regen" ? <Loader2 size={15} className="animate-spin" /> : <RefreshCw size={15} />}
            Try again
          </button>
        </div>
        {err && <p className="mt-2 text-[12px] text-destructive">{err}</p>}
      </Shell>
    )
  }

  // ── pending_review ──────────────────────────────────────────────────────────
  return (
    <Shell title="Your brand report is ready">
      {done ? (
        <div className="flex items-start gap-2.5 text-[13.5px] text-emerald">
          <Check size={16} className="mt-0.5 shrink-0" /> <p>{done}</p>
        </div>
      ) : (
        <>
          <p className="text-[13px] leading-relaxed text-muted-foreground">
            Here&rsquo;s the foundation I researched for{" "}
            <span className="text-foreground/90">{summary.brand || activeBrand.name}</span>
            {summary.data_basis ? <> · <span className="text-foreground/70">{summary.data_basis}</span></> : null}
            {revCount ? <> · revision {revCount}</> : null}. Review it, then approve to lock it in or tell me what to change.
          </p>

          {!!(summary.scorecard_metrics && summary.scorecard_metrics.length) && (
            <div className="mt-3 grid grid-cols-2 gap-2">
              {summary.scorecard_metrics!.slice(0, 6).map((m, i) => (
                <div key={i} className="rounded-xl border border-border bg-white/[0.02] px-3 py-2">
                  <div className="text-[11px] uppercase tracking-[0.1em] text-muted-foreground">{m.label}</div>
                  <div className="text-[14px] font-semibold text-foreground">{m.value}</div>
                </div>
              ))}
            </div>
          )}

          <div className="mt-3 flex flex-wrap items-center gap-2">
            <button
              onClick={openPdf}
              disabled={busy === "pdf"}
              className="inline-flex items-center gap-1.5 rounded-lg border border-border px-3.5 py-2 text-[13px] font-medium text-foreground/85 transition-colors hover:bg-white/[0.05] disabled:opacity-50"
            >
              {busy === "pdf" ? <Loader2 size={14} className="animate-spin" /> : <FileText size={14} />} Open full report
            </button>
            <button
              onClick={approve}
              disabled={busy === "approve"}
              className="inline-flex items-center gap-1.5 rounded-lg bg-emerald px-3.5 py-2 text-[13px] font-semibold text-[#06120E] transition-[filter] hover:brightness-110 disabled:opacity-50"
            >
              {busy === "approve" ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} />} Approve foundation
            </button>
            <button
              onClick={() => setShowNotes((s) => !s)}
              className="inline-flex items-center gap-1.5 rounded-lg border border-border px-3.5 py-2 text-[13px] font-medium text-foreground/85 transition-colors hover:bg-white/[0.05]"
            >
              <MessageSquare size={14} /> Request changes
            </button>
          </div>

          {showNotes && (
            <div className="mt-3 rounded-xl border border-border bg-black/20 p-3">
              <div className="mb-1.5 flex items-center justify-between">
                <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">What should change?</span>
                <button onClick={() => setShowNotes(false)} className="text-muted-foreground hover:text-foreground"><X size={14} /></button>
              </div>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={3}
                placeholder="Be specific — I re-run just the affected research, not the whole report."
                className="w-full resize-none rounded-lg border border-input bg-black/30 px-3 py-2 text-[13px] text-foreground outline-none placeholder:text-muted-foreground/70 focus:border-primary/50"
              />
              <div className="mt-2 flex items-center justify-between">
                <span className="text-[11px] text-muted-foreground">
                  {revCount >= 3 ? "Revision cap reached — further edits are new scope." : `${3 - revCount} revision${3 - revCount === 1 ? "" : "s"} included`}
                </span>
                <button
                  onClick={requestChange}
                  disabled={busy === "change" || !notes.trim()}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3.5 py-1.5 text-[12.5px] font-semibold text-primary-foreground transition-transform hover:scale-[1.02] disabled:opacity-40"
                >
                  {busy === "change" ? <Loader2 size={13} className="animate-spin" /> : <Sparkles size={13} />} Send change
                </button>
              </div>
            </div>
          )}
        </>
      )}
      {err && <p className="mt-2 text-[12px] text-destructive">{err}</p>}
    </Shell>
  )
}

function Shell({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="glass-panel mt-7 overflow-hidden rounded-2xl border border-border">
      <div className="flex items-center gap-2 border-b border-border px-4 py-3">
        <Sparkles size={16} className="text-primary" />
        <span className="text-[13.5px] font-semibold text-foreground">{title}</span>
      </div>
      <div className="p-4">{children}</div>
    </div>
  )
}
