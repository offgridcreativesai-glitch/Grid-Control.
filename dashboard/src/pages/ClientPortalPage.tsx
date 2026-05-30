/**
 * Client Portal — the restricted managed-client view (route "/portal").
 * A brand owner who is NOT the operator: they review work and read insights only.
 * NO agent triggering, NO operator tools, NO Brain write-actions.
 *
 * Real data only: the review queue is the brand's real pending outputs rendered
 * human-readable (never raw JSON). Insights are read-only. The Ask box is Q&A only —
 * it calls the Brain but never surfaces or executes proposals.
 */
import { useState, useRef, useEffect } from "react"
import { ListChecks, Check, RefreshCw, TrendingUp, ArrowUp } from "lucide-react"
import { apiFetch } from "@/lib/api"
import { useBrandStore } from "@/store/brandStore"
import {
  usePendingOutputs,
  useApproveOutput,
  useDigest,
  type PendingOutput,
} from "@/hooks/useGridApi"
import { useRequestRevision } from "@/hooks/useRevisions"
import {
  CockpitRoot,
  Card,
  Eyebrow,
  STATUS,
} from "@/components/cockpit/primitives"
import { brandMark } from "@/lib/cockpitFormat"

// ── Human-readable preview of one pending output (NEVER raw JSON) ──────────────
function OutputPreview({ item }: { item: PendingOutput }) {
  const hashtags = item.hashtags ?? []
  const text = item.caption || item.body_text || item.preview || ""
  return (
    <div>
      {item.title && (
        <p className="text-[13.5px] font-semibold leading-relaxed text-zinc-100">{item.title}</p>
      )}
      {text && (
        <p className="mt-1.5 whitespace-pre-wrap text-[13.5px] leading-relaxed text-zinc-200">
          {text}
        </p>
      )}
      {hashtags.length > 0 && (
        <p className="mt-2 text-[12.5px] leading-relaxed text-zinc-500">
          {hashtags.map((h) => (h.startsWith("#") ? h : `#${h}`)).join(" · ")}
        </p>
      )}
      {!text && !item.title && (
        <p className="text-[13px] italic text-zinc-500">
          {item.platform ? `${item.platform} content` : "Content"} ready for your review.
        </p>
      )}
    </div>
  )
}

type CardStatus = "pending" | "approved" | "changes"

function ReviewCard({ item }: { item: PendingOutput }) {
  const approve = useApproveOutput()
  const requestRevision = useRequestRevision()
  const [status, setStatus] = useState<CardStatus>("pending")
  const [noting, setNoting] = useState(false)
  const [note, setNote] = useState("")

  const onApprove = () => {
    approve.mutate(item.filename)
    setStatus("approved")
  }
  const onSendRequest = () => {
    if (!note.trim()) return
    requestRevision.mutate({ output_id: item.filename, feedback: note.trim() })
    setStatus("changes")
    setNoting(false)
  }

  const resolved = status !== "pending"
  const typeLabel = item.platform || item.agent_name || "Content"

  return (
    <Card className="overflow-hidden">
      {resolved && (
        <div
          className="flex items-center justify-between px-5 py-2.5"
          style={{
            background: status === "approved" ? STATUS.green.bg : STATUS.amber.bg,
            borderBottom: "1px solid " + (status === "approved" ? STATUS.green.bd : STATUS.amber.bd),
          }}
        >
          <span
            className="flex items-center gap-2 text-[12.5px] font-medium"
            style={{ color: status === "approved" ? STATUS.green.fg : STATUS.amber.fg }}
          >
            {status === "approved" ? <Check size={14} /> : <RefreshCw size={14} />}
            {status === "approved"
              ? "Approved — your team has been notified"
              : "Changes requested — your team will revise"}
          </span>
        </div>
      )}

      <div className={"p-5 " + (resolved ? "opacity-60" : "")}>
        <div className="flex items-center justify-between gap-3">
          <span className="inline-flex items-center gap-1.5 rounded-md border border-white/[0.08] bg-white/[0.02] px-2 py-1 font-mono text-[10px] uppercase tracking-[0.12em] text-zinc-400">
            <ListChecks size={12} className="text-zinc-500" />
            {typeLabel}
          </span>
          <span className="font-mono text-[10.5px] text-zinc-600">drafted for review</span>
        </div>

        <div className="mt-4 rounded-xl border border-white/[0.06] bg-[#0e0f12] p-4">
          <OutputPreview item={item} />
        </div>

        {!resolved &&
          (noting ? (
            <div className="mt-4">
              <textarea
                autoFocus
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="What would you like changed? Your team will see this note…"
                rows={3}
                className="w-full resize-none rounded-lg border border-white/[0.1] bg-[#0e0f12] px-3 py-2.5 text-[13px] text-zinc-200 placeholder:text-zinc-600 focus:border-white/[0.2] focus:outline-none"
              />
              <div className="mt-2.5 flex items-center justify-end gap-2">
                <button
                  onClick={() => {
                    setNoting(false)
                    setNote("")
                  }}
                  className="rounded-lg px-3 py-1.5 text-[12.5px] font-medium text-zinc-500 transition-colors hover:text-zinc-300"
                >
                  Cancel
                </button>
                <button
                  onClick={onSendRequest}
                  disabled={!note.trim()}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-white/[0.1] px-3 py-1.5 text-[12.5px] font-medium text-zinc-200 transition-colors hover:bg-white/[0.05] disabled:opacity-40"
                >
                  Send request
                </button>
              </div>
            </div>
          ) : (
            <div className="mt-4 flex items-center gap-2.5">
              <button
                onClick={onApprove}
                className="inline-flex items-center gap-1.5 rounded-lg px-3.5 py-2 text-[13px] font-semibold text-white transition-[filter] hover:brightness-110"
                style={{ background: "var(--accent)" }}
              >
                <Check size={15} /> Approve
              </button>
              <button
                onClick={() => setNoting(true)}
                className="inline-flex items-center gap-1.5 rounded-lg border border-white/[0.1] px-3.5 py-2 text-[13px] font-medium text-zinc-300 transition-colors hover:bg-white/[0.04] hover:text-zinc-100"
              >
                Request changes
              </button>
            </div>
          ))}
      </div>
    </Card>
  )
}

function ReviewQueue() {
  const { data, isLoading } = usePendingOutputs()
  const items = data?.outputs ?? []

  return (
    <section>
      <div className="flex items-baseline justify-between">
        <h2 className="text-[17px] font-semibold tracking-tight text-zinc-100">
          Awaiting your approval
        </h2>
        <span className="font-mono text-[11.5px] text-zinc-500">
          {isLoading ? "loading…" : items.length > 0 ? `${items.length} to review` : "all caught up"}
        </span>
      </div>
      <div className="mt-5 space-y-4">
        {items.length === 0 && !isLoading ? (
          <Card className="p-8 text-center">
            <p className="text-[13.5px] text-zinc-400">
              Nothing waiting right now. We&rsquo;ll let you know when there&rsquo;s something to review.
            </p>
          </Card>
        ) : (
          items.map((item) => <ReviewCard key={item.filename} item={item} />)
        )}
      </div>
    </section>
  )
}

// ── Read-only insights (derived from the real digest — no controls) ───────────
function InsightsSection() {
  const { data } = useDigest()
  const takeaways: string[] = []
  if (data?.verdict && data.verdict_reason) takeaways.push(data.verdict_reason)
  for (const s of data?.sentinel?.signals ?? []) {
    if (s.reason) takeaways.push(s.reason)
  }

  return (
    <section>
      <h2 className="text-[17px] font-semibold tracking-tight text-zinc-100">Insights</h2>
      <p className="mt-1 font-mono text-[11px] text-zinc-500">Read-only</p>

      <div className="mt-5 rounded-2xl border border-white/[0.07] bg-[#141518] p-5">
        <Eyebrow>What this means</Eyebrow>
        {takeaways.length > 0 ? (
          <ul className="mt-3.5 space-y-3">
            {takeaways.slice(0, 4).map((t, i) => (
              <li key={i} className="flex items-start gap-2.5">
                <TrendingUp
                  size={15}
                  className="mt-[2px] shrink-0"
                  style={{ color: STATUS.blue.fg }}
                />
                <span className="text-[13.5px] leading-relaxed text-zinc-300">{t}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-3 text-[13px] leading-relaxed text-zinc-400">
            No insights yet — they appear once your team runs the daily pipeline.
          </p>
        )}
      </div>
    </section>
  )
}

// ── Read-only Q&A (Brain chat, proposals never surfaced) ──────────────────────
function AskSection() {
  const { activeBrand } = useBrandStore()
  const [draft, setDraft] = useState("")
  const [thread, setThread] = useState<{ role: "you" | "brand"; text: string }[]>([])
  const [busy, setBusy] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight
  }, [thread])

  const ask = async () => {
    const q = draft.trim()
    if (!q || busy) return
    const next = [...thread, { role: "you" as const, text: q }]
    setThread(next)
    setDraft("")
    setBusy(true)
    try {
      const r = await apiFetch("/api/brain/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          brand_slug: activeBrand.slug,
          agent_scope: null,
          messages: next.map((m) => ({ role: m.role === "you" ? "user" : "assistant", content: m.text })),
        }),
      })
      const j = await r.json()
      setThread((t) => [
        ...t,
        { role: "brand", text: j.success ? j.response || "(no answer)" : `Error: ${j.error}` },
      ])
    } catch (e) {
      setThread((t) => [...t, { role: "brand", text: `Error: ${e instanceof Error ? e.message : String(e)}` }])
    } finally {
      setBusy(false)
    }
  }

  return (
    <section>
      <h2 className="text-[17px] font-semibold tracking-tight text-zinc-100">Ask about your brand</h2>
      <p className="mt-1 font-mono text-[11px] text-zinc-500">
        Questions only · answers from your content &amp; performance
      </p>

      <Card className="mt-5 p-5">
        {thread.length > 0 && (
          <div ref={scrollRef} className="mb-4 max-h-64 space-y-4 overflow-y-auto pr-1">
            {thread.map((m, i) =>
              m.role === "you" ? (
                <div key={i} className="flex justify-end">
                  <div className="max-w-[82%] rounded-2xl rounded-br-md border border-white/[0.07] bg-white/[0.04] px-3.5 py-2.5 text-[13px] text-zinc-200">
                    {m.text}
                  </div>
                </div>
              ) : (
                <div key={i} className="max-w-[88%] whitespace-pre-wrap text-[13px] leading-relaxed text-zinc-300">
                  {m.text}
                </div>
              ),
            )}
          </div>
        )}
        <div className="flex items-center gap-2 rounded-xl border border-white/[0.09] bg-[#0e0f12] p-1.5 pl-3.5 transition-colors focus-within:border-white/[0.18]">
          <input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && ask()}
            placeholder="Ask about your content or performance…"
            className="min-w-0 flex-1 bg-transparent text-[13.5px] text-zinc-100 placeholder:text-zinc-600 focus:outline-none"
          />
          <button
            onClick={ask}
            disabled={!draft.trim() || busy}
            className="grid h-8 w-8 shrink-0 place-items-center rounded-lg text-white transition-[filter] hover:brightness-110 disabled:opacity-40"
            style={{ background: "var(--accent)" }}
          >
            <ArrowUp size={16} />
          </button>
        </div>
      </Card>
    </section>
  )
}

export function ClientPortalPage() {
  const { activeBrand } = useBrandStore()

  return (
    <CockpitRoot>
      <header className="sticky top-0 z-20 border-b border-white/[0.06] bg-[#0b0c0e]/85 backdrop-blur-xl">
        <div className="mx-auto flex h-14 max-w-[860px] items-center gap-2.5 px-6">
          <span
            className="grid h-7 w-7 place-items-center rounded-md text-[13px] font-semibold text-zinc-100"
            style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.08)" }}
          >
            {brandMark(activeBrand.name)}
          </span>
          <span className="text-[14px] font-semibold tracking-tight text-zinc-100">
            {activeBrand.name}
          </span>
        </div>
      </header>

      <main className="mx-auto max-w-[860px] px-6 pb-24 pt-9">
        <h1 className="text-[22px] font-medium tracking-tight text-zinc-200">
          Here&rsquo;s what your team prepared for{" "}
          <span className="font-semibold text-white">{activeBrand.name}</span>.
        </h1>

        <div className="mt-9 space-y-12">
          <ReviewQueue />
          <InsightsSection />
          <AskSection />
        </div>
      </main>
    </CockpitRoot>
  )
}
