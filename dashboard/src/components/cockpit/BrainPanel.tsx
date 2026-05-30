/**
 * The Brain — embedded chat driver. Ported from brain.jsx (visual language) and wired to
 * the REAL Brain: /api/brain/chat for turns, /api/brain/execute for approved proposals.
 * History persists per brand via brainStore. The approval-gate pattern is preserved:
 * proposals render as cards with Approve / Dismiss and never auto-run.
 */
import { useState, useRef, useEffect } from "react"
import { Calendar, ListChecks, TrendingUp, BarChart3, Sparkles, ArrowUp, Check, X } from "lucide-react"
import { apiFetch } from "@/lib/api"
import { useBrandStore } from "@/store/brandStore"
import { useBrainStore, type BrainMessage, type BrainProposal } from "@/store/brainStore"
import { Card, Eyebrow, ModuleHeader, STATUS } from "./primitives"

const QUICK_ACTIONS = [
  { label: "Plan this week", icon: Calendar, prompt: "Plan this week's content for my brand" },
  { label: "Review pending", icon: ListChecks, prompt: "Show me what's waiting for my approval" },
  { label: "What's trending", icon: TrendingUp, prompt: "What's trending in my niche right now?" },
  { label: "Check performance", icon: BarChart3, prompt: "How is my content performing?" },
]

function BrandMark({ size = 26 }: { size?: number }) {
  return (
    <span
      className="grid shrink-0 place-items-center rounded-[7px]"
      style={{
        width: size,
        height: size,
        background: "color-mix(in oklab, var(--accent) 22%, #15161a)",
        border: "1px solid color-mix(in oklab, var(--accent) 35%, transparent)",
      }}
    >
      <Sparkles size={size * 0.56} style={{ color: "var(--accent)" }} />
    </span>
  )
}

function UserBubble({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[82%] rounded-2xl rounded-br-md border border-white/[0.07] bg-white/[0.04] px-3.5 py-2.5 text-[13px] leading-relaxed text-zinc-200 whitespace-pre-wrap">
        {children}
      </div>
    </div>
  )
}

function BrainBubble({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex gap-3">
      <BrandMark />
      <div className="max-w-[86%] flex-1">{children}</div>
    </div>
  )
}

function ProposalCard({
  proposal,
  onResolve,
}: {
  proposal: BrainProposal
  onResolve: (approve: boolean) => void
}) {
  const resolved = proposal.status !== "pending"
  const title =
    proposal.kind === "edit"
      ? `Edit ${proposal.payload?.path ?? "a file"}`
      : `Run: ${proposal.payload?.command ?? proposal.payload?.cmd ?? "a command"}`
  const done = proposal.status === "executed" || proposal.status === "approved"

  return (
    <div className="mt-3 rounded-xl border border-white/[0.09] bg-[#0e0f12] p-3.5">
      <div className="flex items-center gap-2">
        <Eyebrow>Proposed action</Eyebrow>
        <span className="font-mono text-[10px] text-zinc-600">· needs approval</span>
      </div>
      <p className="mt-2 break-words text-[13px] font-medium text-zinc-200">{title}</p>
      {proposal.result && (
        <p className="mt-1 break-words font-mono text-[11px] leading-relaxed text-zinc-500">
          {proposal.result}
        </p>
      )}

      {resolved ? (
        <div
          className="mt-3 flex items-center gap-1.5 text-[12px] font-medium"
          style={{ color: done ? STATUS.green.fg : "#9aa0a8" }}
        >
          {done ? <Check size={14} /> : <X size={14} />}
          {proposal.status === "executed"
            ? "Approved & executed"
            : proposal.status === "approved"
              ? "Approved — running…"
              : proposal.status === "failed"
                ? "Failed"
                : "Dismissed"}
        </div>
      ) : (
        <div className="mt-3.5 flex items-center gap-2">
          <button
            onClick={() => onResolve(true)}
            className="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-[12.5px] font-semibold text-white transition-[filter] hover:brightness-110"
            style={{ background: "var(--accent)" }}
          >
            <Check size={14} /> Approve
          </button>
          <button
            onClick={() => onResolve(false)}
            className="inline-flex items-center gap-1.5 rounded-lg border border-white/[0.08] px-3 py-1.5 text-[12.5px] font-medium text-zinc-400 transition-colors hover:bg-white/[0.04] hover:text-zinc-200"
          >
            <X size={14} /> Dismiss
          </button>
        </div>
      )}
    </div>
  )
}

export function BrainPanel() {
  const { activeBrand } = useBrandStore()
  const scope = "global"
  const { threads, appendMessage, updateMessage } = useBrainStore()
  const threadKey = `${activeBrand.slug}::${scope}`
  const messages: BrainMessage[] = threads[threadKey] ?? []

  const [draft, setDraft] = useState("")
  const [thinking, setThinking] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight
  }, [messages, thinking])

  const send = async (text?: string) => {
    const msg = (text ?? draft).trim()
    if (!msg || thinking) return
    const userMessage: BrainMessage = {
      id: Date.now().toString(),
      role: "user",
      content: msg,
      createdAt: Date.now(),
    }
    const history = [...messages, userMessage]
    appendMessage(activeBrand.slug, scope, userMessage)
    setDraft("")
    setThinking(true)
    try {
      const r = await apiFetch("/api/brain/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          brand_slug: activeBrand.slug,
          agent_scope: null,
          messages: history.map((m) => ({ role: m.role, content: m.content })),
        }),
      })
      const j = await r.json()
      if (!j.success) throw new Error(j.error || "Brain unavailable")
      appendMessage(activeBrand.slug, scope, {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: j.response || "(empty response)",
        proposals: (j.proposals || []).map((p: BrainProposal) => ({ ...p, status: "pending" as const })),
        createdAt: Date.now(),
      })
    } catch (e) {
      appendMessage(activeBrand.slug, scope, {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: `Error: ${e instanceof Error ? e.message : String(e)}`,
        createdAt: Date.now(),
      })
    } finally {
      setThinking(false)
    }
  }

  const resolveProposal = async (msgId: string, idx: number, approve: boolean) => {
    const msg = messages.find((m) => m.id === msgId)
    if (!msg?.proposals) return
    const prop = msg.proposals[idx]
    if (!prop || prop.status !== "pending") return

    const patch = (status: BrainProposal["status"], result?: string) => {
      const updated = msg.proposals!.map((p, i) =>
        i === idx ? { ...p, status, ...(result !== undefined ? { result } : {}) } : p,
      )
      updateMessage(activeBrand.slug, scope, msgId, { proposals: updated })
    }

    if (!approve) {
      patch("rejected")
      return
    }
    patch("approved")
    try {
      const r = await apiFetch("/api/brain/execute", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ kind: prop.kind, payload: prop.payload }),
      })
      const j = await r.json()
      patch(j.success ? "executed" : "failed", j.success ? j.result : j.error)
    } catch (e) {
      patch("failed", e instanceof Error ? e.message : String(e))
    }
  }

  return (
    <Card className="flex h-full flex-col p-6">
      <ModuleHeader
        title="The Brain"
        sub="Your operator — proposes, you approve"
        right={<BrandMark size={30} />}
      />

      <div
        ref={scrollRef}
        className="mt-6 flex-1 space-y-5 overflow-y-auto pr-1"
        style={{ minHeight: 220, maxHeight: 420 }}
      >
        {messages.length === 0 && (
          <BrainBubble>
            <p className="text-[13px] leading-relaxed text-zinc-300">
              I run {activeBrand.name}&rsquo;s marketing — research, planning, scripts, performance.
              Ask me anything, or pick a quick action below. I propose; you approve.
            </p>
          </BrainBubble>
        )}

        {messages.map((m) =>
          m.role === "user" ? (
            <UserBubble key={m.id}>{m.content}</UserBubble>
          ) : (
            <BrainBubble key={m.id}>
              <p className="whitespace-pre-wrap text-[13px] leading-relaxed text-zinc-300">
                {m.content}
              </p>
              {m.proposals?.map((p, i) => (
                <ProposalCard
                  key={i}
                  proposal={p}
                  onResolve={(approve) => resolveProposal(m.id, i, approve)}
                />
              ))}
            </BrainBubble>
          ),
        )}

        {thinking && (
          <BrainBubble>
            <p className="text-[13px] italic leading-relaxed text-zinc-500">Thinking…</p>
          </BrainBubble>
        )}
      </div>

      <div className="mt-5 flex flex-wrap gap-2">
        {QUICK_ACTIONS.map((q) => (
          <button
            key={q.label}
            onClick={() => send(q.prompt)}
            className="inline-flex items-center gap-1.5 rounded-full border border-white/[0.08] bg-white/[0.02] px-3 py-1.5 text-[12px] font-medium text-zinc-400 transition-colors hover:border-white/[0.16] hover:text-zinc-200"
          >
            <q.icon size={13} className="text-zinc-500" />
            {q.label}
          </button>
        ))}
      </div>

      <div className="mt-3 flex items-center gap-2 rounded-xl border border-white/[0.09] bg-[#0e0f12] p-1.5 pl-3.5 transition-colors focus-within:border-white/[0.18]">
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder="Tell me what you need…"
          className="min-w-0 flex-1 bg-transparent text-[13.5px] text-zinc-100 placeholder:text-zinc-600 focus:outline-none"
        />
        <button
          onClick={() => send()}
          disabled={!draft.trim() || thinking}
          className="grid h-8 w-8 shrink-0 place-items-center rounded-lg text-white transition-[filter] hover:brightness-110 disabled:opacity-40"
          style={{ background: "var(--accent)" }}
        >
          <ArrowUp size={16} />
        </button>
      </div>
    </Card>
  )
}
