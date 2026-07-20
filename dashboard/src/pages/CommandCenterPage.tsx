/**
 * Command Center — the page where the owner RUNS their brand (route "/command").
 *
 * Practical, chat-first cockpit:
 *  · LEFT  — talk to Atlas (chief of staff). Work the team prepared appears INLINE
 *            as human-readable approve cards. Never raw JSON / slugs / models / tokens.
 *  · RIGHT — Live Work Feed: who's working right now + recent activity, in plain English.
 *
 * Real data only: chat → /api/brain/chat · approvals → usePendingOutputs +
 * useApproveOutput + useRequestRevision · activity → live agent status + SSE stream.
 */
import { useEffect, useMemo, useRef, useState } from "react"
import { loadThread, saveThread } from "@/lib/chatPersist"
import { ArrowUp, Check, RefreshCw, CalendarRange, Sparkles, LineChart, Inbox } from "lucide-react"
import { apiFetch } from "@/lib/api"
import { cn } from "@/lib/utils"
import { useBrandStore } from "@/store/brandStore"
import { useAppStore } from "@/store/appStore"
import {
  usePendingOutputs,
  useApproveOutput,
  useLiveAgents,
  useWeek,
  type PendingOutput,
  type WeekRun,
} from "@/hooks/useGridApi"
import { useRequestRevision } from "@/hooks/useRevisions"
import { personaForSlug, activityPhrase, type Persona } from "@/lib/agentPersona"
import { relativeTime } from "@/lib/cockpitFormat"
import { FirstRunGate } from "@/components/FirstRunGate"
import { BrandReportCard } from "@/components/BrandReportCard"
import { ProgramPhaseCard } from "@/components/ProgramPhaseCard"

// ── Small shared bits ─────────────────────────────────────────────────────────

function PersonaAvatar({ slug, px = 32 }: { slug?: string; px?: number }) {
  const p = personaForSlug(slug)
  return (
    <span
      className="relative inline-grid shrink-0 place-items-center rounded-full bg-white/[0.04] ring-1 ring-white/[0.08]"
      style={{ width: px, height: px }}
    >
      <img
        src={`/agents/${p.key}.png`}
        alt={p.name}
        draggable={false}
        className="h-[80%] w-[80%] select-none object-contain"
      />
    </span>
  )
}

function LiveDot({ on }: { on: boolean }) {
  return (
    <span className="relative grid h-2 w-2 place-items-center">
      {on && (
        <span
          className="absolute inset-0 rounded-full bg-emerald"
          style={{ animation: "agentpulse 1.8s ease-out infinite" }}
        />
      )}
      <span
        className="relative h-2 w-2 rounded-full"
        style={{ background: on ? "var(--emerald)" : "var(--status-blocked)" }}
      />
    </span>
  )
}

// ── One approve card (human-readable; reuses the real approve / revise flow) ────

type CardStatus = "pending" | "approved" | "changes"

// Proactive system moves (GRIDLOCK-PROGRAM-01JUL) get an emerald border to read
// as "Atlas did this on the program's own clock" — distinct from a content-approval
// card. Quarterly QBR reuses Strategy Agent's own card type on purpose (it's a
// normal Strategy Agent output, just on a new cadence) so it's NOT in this map —
// badging every manual Strategy Agent run as a "system move" would be wrong.
const PROGRAM_CARD_SLUGS: Record<string, string> = {
  "weekly-program": "Weekly Program",
  "weekly-review-composer": "Weekly Program",
  "monthly-program": "Monthly Program",
  "monthly-mix-composer": "Monthly Program",
}

function ApprovalCard({ item }: { item: PendingOutput }) {
  const approve = useApproveOutput()
  const requestRevision = useRequestRevision()
  const [status, setStatus] = useState<CardStatus>("pending")
  const [noting, setNoting] = useState(false)
  const [note, setNote] = useState("")

  const programLabel = PROGRAM_CARD_SLUGS[item.agent_slug]
  const isProgramCard = Boolean(programLabel)
  const persona = personaForSlug(item.agent_slug)
  const typeLabel = programLabel || item.platform || persona.role
  const text = item.caption || item.body_text || item.preview || ""

  const onApprove = () => {
    approve.mutate(item.filename)
    setStatus("approved")
  }
  const onSend = () => {
    if (!note.trim()) return
    requestRevision.mutate({ output_id: item.filename, feedback: note.trim() })
    setStatus("changes")
    setNoting(false)
  }

  const resolved = status !== "pending"

  return (
    <div className={"glass-panel overflow-hidden rounded-2xl" + (isProgramCard ? " border border-emerald/40" : "")}>
      {isProgramCard && !resolved && (
        <div className="flex items-center gap-2 border-b border-emerald/20 bg-emerald/[0.06] px-4 py-2 text-[11.5px] font-medium text-emerald">
          <Sparkles size={13} /> Atlas ran your {programLabel!.toLowerCase()}
        </div>
      )}
      {resolved && (
        <div
          className="flex items-center gap-2 px-4 py-2 text-[12.5px] font-medium"
          style={{
            background: status === "approved" ? "rgba(22,160,126,0.12)" : "rgba(240,160,48,0.12)",
            color: status === "approved" ? "var(--emerald)" : "var(--status-queued)",
            borderBottom:
              "1px solid " + (status === "approved" ? "rgba(22,160,126,0.22)" : "rgba(240,160,48,0.22)"),
          }}
        >
          {status === "approved" ? <Check size={14} /> : <RefreshCw size={14} />}
          {status === "approved"
            ? "Approved — your team is on it"
            : "Changes requested — your team will revise"}
        </div>
      )}

      <div className={"p-4 " + (resolved ? "opacity-60" : "")}>
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <PersonaAvatar slug={item.agent_slug} px={24} />
            <span className="text-[12.5px] font-medium text-foreground">{persona.name}</span>
            <span className="rounded-md border border-border bg-white/[0.02] px-2 py-0.5 text-[10.5px] uppercase tracking-[0.12em] text-muted-foreground">
              {typeLabel}
            </span>
          </div>
          <span className="text-[10.5px] text-muted-foreground">{relativeTime(item.created_at)}</span>
        </div>

        <div className="mt-3 rounded-xl border border-border bg-black/20 p-3.5">
          {item.title && (
            <p className="text-[13.5px] font-semibold leading-relaxed text-foreground">{item.title}</p>
          )}
          {text && (
            <p className="mt-1 whitespace-pre-wrap text-[13.5px] leading-relaxed text-foreground/85">{text}</p>
          )}
          {(item.hashtags?.length ?? 0) > 0 && (
            <p className="mt-2 text-[12px] leading-relaxed text-muted-foreground">
              {item.hashtags!.map((h) => (h.startsWith("#") ? h : `#${h}`)).join(" · ")}
            </p>
          )}
          {!text && !item.title && (
            <p className="text-[13px] italic text-muted-foreground">
              {item.platform ? `${item.platform} content` : "Content"} ready for your review.
            </p>
          )}
        </div>

        {!resolved &&
          (noting ? (
            <div className="mt-3">
              <textarea
                autoFocus
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="What should change? Your team will see this note…"
                rows={3}
                className="w-full resize-none rounded-lg border border-input bg-black/30 px-3 py-2.5 text-[13px] text-foreground placeholder:text-muted-foreground/70 focus:border-primary/50 focus:outline-none"
              />
              <div className="mt-2 flex items-center justify-end gap-2">
                <button
                  onClick={() => {
                    setNoting(false)
                    setNote("")
                  }}
                  className="rounded-lg px-3 py-1.5 text-[12.5px] font-medium text-muted-foreground transition-colors hover:text-foreground"
                >
                  Cancel
                </button>
                <button
                  onClick={onSend}
                  disabled={!note.trim()}
                  className="rounded-lg border border-border px-3 py-1.5 text-[12.5px] font-medium text-foreground transition-colors hover:bg-white/[0.05] disabled:opacity-40"
                >
                  Send request
                </button>
              </div>
            </div>
          ) : (
            <div className="mt-3 flex items-center gap-2.5">
              <button
                onClick={onApprove}
                className="inline-flex items-center gap-1.5 rounded-lg bg-emerald px-3.5 py-2 text-[13px] font-semibold text-[#06120E] transition-[filter] hover:brightness-110"
              >
                <Check size={15} /> Approve
              </button>
              <button
                onClick={() => setNoting(true)}
                className="inline-flex items-center gap-1.5 rounded-lg border border-border px-3.5 py-2 text-[13px] font-medium text-foreground/80 transition-colors hover:bg-white/[0.04] hover:text-foreground"
              >
                Request changes
              </button>
            </div>
          ))}
      </div>
    </div>
  )
}

// ── Live Work Feed (right rail) ─────────────────────────────────────────────────

// ── Your Week (operating rhythm · Fable 5 UX pass) ─────────────────────────────
// The agency cadence made visible: what the team DID this week, what's WAITING
// on the owner, what's COMING UP on the program clock. Personas only — THE
// SECRET holds (no slugs, no status codes, no pipeline jargon).

const DOW_LABEL: Record<string, string> = {
  mon: "Monday", tue: "Tuesday", wed: "Wednesday", thu: "Thursday",
  fri: "Friday", sat: "Saturday", sun: "Sunday",
}

function nextLabel(n: { pipeline: string; day_of_week?: string | null; hour?: number | null; minute?: number | null }): string {
  const t =
    n.hour != null ? `${String(n.hour).padStart(2, "0")}:${String(n.minute ?? 0).padStart(2, "0")}` : ""
  switch (n.pipeline) {
    case "daily":
      return `Fresh research every morning${t ? ` · ${t}` : ""}`
    case "weekly":
      return `Weekly review lands ${DOW_LABEL[n.day_of_week ?? ""] ?? "each week"}${t ? ` · ${t}` : ""}`
    case "monthly":
      return "Monthly content-mix check-in"
    case "quarterly":
      return "Quarterly strategy review"
    default:
      return "Scheduled team run"
  }
}

const DONE_PHRASE: Record<string, string> = {
  atlas: "wrapped a team review",
  riveter: "finished new drafts",
  lumen: "finished new visuals",
  spark: "finished this week's research",
  exactor: "finished the performance review",
  aegis: "finished brand checks",
  nexus: "caught up on conversations",
  forge: "finished build work",
}

function weekRunPhrase(run: WeekRun): string {
  const p = personaForSlug(run.agent_slug)
  if ((run.status || "").toLowerCase() === "running") return `${p.name} ${p.action}`
  if ((run.status || "").toLowerCase() === "error") return `${p.name} hit a snag — Atlas is on it`
  return `${p.name} ${DONE_PHRASE[p.key] ?? "finished a task"}`
}

function WeekPulse({ pendingCount, onReview }: { pendingCount: number; onReview: () => void }) {
  const { data: week } = useWeek()
  if (!week) return null
  const ran = (week.ran || []).slice(0, 5)
  const upcoming = (week.next || []).slice(0, 3)
  const waitingCount = Math.max(week.waiting?.count ?? 0, pendingCount)
  if (ran.length === 0 && upcoming.length === 0 && waitingCount === 0) return null

  return (
    <section className="mb-6">
      <p className="mb-2.5 text-[10.5px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
        Your week
      </p>
      <div className="space-y-3 rounded-xl border border-border bg-white/[0.02] p-3.5">
        {ran.length > 0 && (
          <div>
            <p className="mb-1.5 text-[10.5px] font-medium uppercase tracking-[0.12em] text-muted-foreground/80">
              What ran
            </p>
            <div className="space-y-1">
              {ran.map((r, i) => (
                <div key={i} className="flex items-center gap-2">
                  <PersonaAvatar slug={r.agent_slug} px={18} />
                  <p className="min-w-0 flex-1 truncate text-[12px] text-foreground/80">{weekRunPhrase(r)}</p>
                  <span className="shrink-0 text-[10px] text-muted-foreground">{relativeTime(r.started_at)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {waitingCount > 0 && (
          <button
            onClick={onReview}
            className="flex w-full items-center gap-2 rounded-lg border border-gold/30 bg-gold/[0.07] px-2.5 py-2 text-left transition-colors hover:bg-gold/[0.12]"
            style={{ borderColor: "color-mix(in oklch, var(--status-queued) 35%, transparent)", background: "color-mix(in oklch, var(--status-queued) 8%, transparent)" }}
          >
            <Inbox size={13} style={{ color: "var(--status-queued)" }} />
            <span className="text-[12px] font-medium" style={{ color: "var(--status-queued)" }}>
              Waiting on you: {waitingCount} decision{waitingCount === 1 ? "" : "s"}
            </span>
          </button>
        )}

        {upcoming.length > 0 && (
          <div>
            <p className="mb-1.5 text-[10.5px] font-medium uppercase tracking-[0.12em] text-muted-foreground/80">
              Coming up
            </p>
            <div className="space-y-1">
              {upcoming.map((n, i) => (
                <p key={i} className="text-[12px] text-foreground/70">
                  {nextLabel(n)}
                </p>
              ))}
            </div>
          </div>
        )}
      </div>
    </section>
  )
}

function LiveWorkFeed({
  working,
  pendingCount,
  onReview,
}: {
  working: Persona[]
  pendingCount: number
  onReview: () => void
}) {
  const activity = useAppStore((s) => s.activity)
  const recent = activity.slice(0, 8)
  const quiet = working.length === 0 && recent.length === 0

  return (
    <aside className="hidden w-[336px] shrink-0 flex-col border-l border-border bg-background/30 lg:flex">
      <div className="flex items-center justify-between border-b border-border px-5 py-4">
        <div className="flex items-center gap-2">
          <LiveDot on={working.length > 0} />
          <span className="text-[13px] font-semibold tracking-tight text-foreground">Live Work Feed</span>
        </div>
        <span className="text-[11px] text-muted-foreground">
          {working.length > 0 ? `${working.length} working` : "idle"}
        </span>
      </div>

      <div className="flex-1 overflow-auto px-5 py-5">
        <WeekPulse pendingCount={pendingCount} onReview={onReview} />
        {quiet ? (
          <div className="rounded-xl border border-border bg-white/[0.02] p-5 text-center">
            <p className="text-[13px] leading-relaxed text-muted-foreground">
              Your team is standing by. Give Atlas a task and you&rsquo;ll see the work happen here.
            </p>
          </div>
        ) : (
          <>
            {working.length > 0 && (
              <section>
                <p className="mb-2.5 text-[10.5px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                  Working now
                </p>
                <div className="space-y-2.5">
                  {working.map((p) => (
                    <div
                      key={p.key}
                      className="flex items-center gap-3 rounded-xl border border-emerald/20 bg-emerald/[0.06] px-3 py-2.5"
                    >
                      <PersonaAvatar slug={p.key} px={30} />
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-[13px] font-medium text-foreground">{p.name}</p>
                        <p className="truncate text-[11.5px] text-emerald">{p.action}</p>
                      </div>
                      <LiveDot on />
                    </div>
                  ))}
                </div>
              </section>
            )}

            {recent.length > 0 && (
              <section className={working.length > 0 ? "mt-6" : ""}>
                <p className="mb-2.5 text-[10.5px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                  Recent
                </p>
                <div className="space-y-1">
                  {recent.map((ev, i) => (
                    <div key={i} className="flex items-center gap-2.5 py-1.5">
                      <PersonaAvatar slug={ev.agent} px={22} />
                      <p className="min-w-0 flex-1 truncate text-[12.5px] text-foreground/80">
                        {activityPhrase(ev.agent, ev.status)}
                      </p>
                      <span className="shrink-0 text-[10.5px] text-muted-foreground">
                        {relativeTime(ev.timestamp)}
                      </span>
                    </div>
                  ))}
                </div>
              </section>
            )}
          </>
        )}
      </div>

      {pendingCount > 0 && (
        <div className="border-t border-border p-4">
          <button
            onClick={onReview}
            className="flex w-full items-center justify-center gap-2 rounded-xl border border-primary/40 bg-primary/[0.08] py-2.5 text-[13px] font-semibold text-primary transition-colors hover:bg-primary/[0.14]"
          >
            <Inbox size={15} />
            {pendingCount} awaiting your approval
          </button>
        </div>
      )}
    </aside>
  )
}

// ── Page ────────────────────────────────────────────────────────────────────────

type Dispatch = {
  agent_name: string
  rationale: string
  status: "pending" | "running" | "done" | "failed"
  note?: string
}
type Msg = { id: string; role: "user" | "assistant"; text: string; dispatch?: Dispatch }

const QUICK = [
  { label: "Plan my week", icon: CalendarRange, send: "Plan my content for this week." },
  { label: "Create content", icon: Sparkles, send: "Let's create this week's content." },
  { label: "How are we doing?", icon: LineChart, send: "How are we performing right now?" },
]

export function CommandCenterPage() {
  const { activeBrand } = useBrandStore()
  const liveAgents = useLiveAgents()
  const { data: pendingData } = usePendingOutputs()
  // Exclude the brand-book from the generic approval feed — it has its own dedicated
  // review surface (BrandReportCard). Leaving it in made it render as a raw text dump
  // ("brand-book Output") alongside the proper report card.
  const pending = useMemo(
    () => (pendingData?.outputs ?? []).filter((o) => o.agent_slug !== "brand-book"),
    [pendingData],
  )

  // Persist the chat per-brand so navigating away and back doesn't wipe what
  // the user typed (Jul 20 vanish bug). See lib/chatPersist.
  const [thread, setThread] = useState<Msg[]>(() => loadThread(activeBrand.slug))
  const [draft, setDraft] = useState("")
  const [thinking, setThinking] = useState(false)

  // The slug the current thread belongs to. Save keys on [thread] ONLY (not
  // slug), so on a brand switch the reload effect replaces the thread first and
  // the save that follows writes under the right brand — never clobbering.
  const threadSlug = useRef(activeBrand.slug)
  useEffect(() => {
    threadSlug.current = activeBrand.slug
    setThread(loadThread(activeBrand.slug))
  }, [activeBrand.slug])
  useEffect(() => {
    saveThread(threadSlug.current, thread)
  }, [thread])

  const bottomRef = useRef<HTMLDivElement>(null)
  const approvalsRef = useRef<HTMLDivElement>(null)

  // Personas currently working — deduped (many backend agents map to one persona).
  const working = useMemo(() => {
    const out: Persona[] = []
    const seen = new Set<string>()
    for (const a of liveAgents) {
      if (a.status !== "running") continue
      const p = personaForSlug(a.slug)
      if (seen.has(p.key)) continue
      seen.add(p.key)
      out.push(p)
    }
    return out
  }, [liveAgents])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [thread, thinking])

  const send = async (text: string) => {
    const q = text.trim()
    if (!q || thinking) return
    const next: Msg[] = [...thread, { id: `${Date.now()}`, role: "user", text: q }]
    setThread(next)
    setDraft("")
    setThinking(true)
    try {
      const r = await apiFetch("/api/brain/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          brand_slug: activeBrand.slug,
          agent_scope: null,
          messages: next.map((m) => ({ role: m.role, content: m.text })),
        }),
      })
      const j = await r.json()
      // THE SECRET: hide file/bash proposals — but DO surface an agent dispatch so the
      // user can approve Atlas putting a specialist on the job (this is what Atlas is FOR).
      const agentProp = (j.proposals || []).find((p: { kind: string }) => p.kind === "agent")
      setThread((t) => [
        ...t,
        {
          id: `${Date.now() + 1}`,
          role: "assistant",
          text: j.success ? j.response || "(no answer)" : `Sorry — I couldn't reach the team just now.`,
          dispatch: agentProp
            ? { agent_name: agentProp.payload.agent_name, rationale: agentProp.payload.rationale, status: "pending" }
            : undefined,
        },
      ])
    } catch {
      setThread((t) => [
        ...t,
        { id: `${Date.now() + 1}`, role: "assistant", text: "Sorry — I couldn't reach the team just now." },
      ])
    } finally {
      setThinking(false)
    }
  }

  const patchDispatch = (msgId: string, patch: Partial<Dispatch>) =>
    setThread((t) => t.map((m) => (m.id === msgId && m.dispatch ? { ...m, dispatch: { ...m.dispatch, ...patch } } : m)))

  const approveDispatch = async (msgId: string, agentName: string) => {
    patchDispatch(msgId, { status: "running" })
    try {
      const r = await apiFetch("/api/agents/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ agent_name: agentName, brand_slug: activeBrand.slug }),
      })
      const j = await r.json()
      if (j.success) {
        patchDispatch(msgId, { status: "done", note: "On it — the result will show up in your approvals when it's ready." })
      } else {
        patchDispatch(msgId, { status: "failed", note: j.error || "Couldn't start that specialist." })
      }
    } catch {
      patchDispatch(msgId, { status: "failed", note: "Couldn't reach the team just now." })
    }
  }

  const scrollToApprovals = () =>
    approvalsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" })

  return (
    <div className="flex h-full">
      {/* Chat console — a clear, readable dark box; the universe shows around it */}
      <div className="flex min-w-0 flex-1 flex-col bg-background/80 backdrop-blur-sm">
        {/* Header — Atlas identity + team status */}
        <header className="flex items-center justify-between border-b border-border px-6 py-3.5">
          <div className="flex items-center gap-3">
            <PersonaAvatar slug="atlas" px={38} />
            <div>
              <p className="text-[14px] font-semibold leading-tight tracking-tight text-foreground">Atlas</p>
              <p className="text-[11.5px] text-muted-foreground">Your chief of staff · {activeBrand.name}</p>
            </div>
          </div>
          <div className="flex items-center gap-2 rounded-full border border-border bg-white/[0.02] px-3 py-1.5">
            <LiveDot on={working.length > 0} />
            <span className="text-[11.5px] font-medium text-foreground/80">
              {working.length > 0 ? "Team is working" : "Standing by"}
            </span>
          </div>
        </header>

        {/* Thread */}
        <div className="flex-1 overflow-auto">
          <div className="mx-auto max-w-[720px] px-6 py-7">
            {/* Greeting */}
            <div className="flex gap-3">
              <PersonaAvatar slug="atlas" px={32} />
              <div className="max-w-[88%] pt-1 text-[14px] leading-relaxed text-foreground/90">
                Hey — I&rsquo;m Atlas, chief of staff for{" "}
                <span className="font-semibold text-foreground">{activeBrand.name}</span>. Tell me what you
                want to get done and I&rsquo;ll put the team on it. You can plan the week, create content, or
                check how we&rsquo;re performing.
              </div>
            </div>

            {/* Brand-book flow — each self-gated on status, only one shows at a time:
                gate (none) → report status loop + review card (generating/review/change). */}
            <FirstRunGate />
            <BrandReportCard />
            <ProgramPhaseCard onStartTask={send} />

            {/* Pending work — presented inline as approve cards */}
            {pending.length > 0 && (
              <div ref={approvalsRef} className="mt-7 flex gap-3">
                <PersonaAvatar slug="atlas" px={32} />
                <div className="min-w-0 flex-1">
                  <p className="pt-1 text-[14px] leading-relaxed text-foreground/90">
                    Here&rsquo;s what the team prepared for you to review:
                  </p>
                  <div className="mt-3 space-y-3">
                    {pending.map((item) => (
                      <ApprovalCard key={item.filename} item={item} />
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Conversation */}
            {thread.map((m) =>
              m.role === "user" ? (
                <div key={m.id} className="mt-6 flex justify-end">
                  <div className="max-w-[82%] rounded-2xl rounded-br-md border border-primary/25 bg-primary/[0.08] px-4 py-2.5 text-[14px] leading-relaxed text-foreground">
                    {m.text}
                  </div>
                </div>
              ) : (
                <div key={m.id} className="mt-6 flex gap-3">
                  <PersonaAvatar slug="atlas" px={32} />
                  <div className="max-w-[88%] pt-1">
                    <div className="whitespace-pre-wrap text-[14px] leading-relaxed text-foreground/90">{m.text}</div>
                    {m.dispatch && (
                      <div className="mt-3 rounded-xl border border-primary/25 bg-primary/[0.05] p-3.5">
                        <p className="text-[12px] uppercase tracking-[0.12em] text-primary/80">Put the team on it</p>
                        <p className="mt-1 text-[13.5px] font-semibold text-foreground">{m.dispatch.agent_name}</p>
                        <p className="mt-0.5 text-[12.5px] text-muted-foreground">{m.dispatch.rationale}</p>
                        {m.dispatch.status === "pending" ? (
                          <div className="mt-3 flex items-center gap-2">
                            <button
                              onClick={() => approveDispatch(m.id, m.dispatch!.agent_name)}
                              className="rounded-lg bg-primary px-3 py-1.5 text-[12.5px] font-semibold text-primary-foreground transition-[filter] hover:brightness-110"
                            >
                              Approve &amp; run
                            </button>
                            <button
                              onClick={() => patchDispatch(m.id, { status: "failed", note: "Dismissed." })}
                              className="rounded-lg border border-border px-3 py-1.5 text-[12.5px] text-muted-foreground transition-colors hover:text-foreground"
                            >
                              Not now
                            </button>
                          </div>
                        ) : (
                          <p className={cn("mt-2.5 text-[12.5px]",
                            m.dispatch.status === "failed" ? "text-destructive" : "text-emerald")}>
                            {m.dispatch.status === "running" ? "Starting…" : m.dispatch.note}
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              ),
            )}

            {thinking && (
              <div className="mt-6 flex items-center gap-3">
                <PersonaAvatar slug="atlas" px={32} />
                <span className="text-[13px] text-muted-foreground">Atlas is thinking…</span>
              </div>
            )}

            <div ref={bottomRef} />
          </div>
        </div>

        {/* Composer */}
        <div className="border-t border-border px-6 py-4">
          <div className="mx-auto max-w-[720px]">
            <div className="mb-2.5 flex flex-wrap gap-2">
              {QUICK.map((q) => (
                <button
                  key={q.label}
                  onClick={() => send(q.send)}
                  disabled={thinking}
                  className="inline-flex items-center gap-1.5 rounded-full border border-border bg-white/[0.02] px-3 py-1.5 text-[12.5px] font-medium text-foreground/80 transition-colors hover:border-white/20 hover:bg-white/[0.05] disabled:opacity-40"
                >
                  <q.icon size={13} className="text-muted-foreground" />
                  {q.label}
                </button>
              ))}
              {pending.length > 0 && (
                <button
                  onClick={scrollToApprovals}
                  className="inline-flex items-center gap-1.5 rounded-full border border-primary/40 bg-primary/[0.08] px-3 py-1.5 text-[12.5px] font-semibold text-primary transition-colors hover:bg-primary/[0.14]"
                >
                  <Inbox size={13} />
                  {pending.length} to approve
                </button>
              )}
            </div>

            <div className="flex items-end gap-2 rounded-2xl border border-input bg-black/30 p-2 pl-4 transition-colors focus-within:border-primary/50">
              <textarea
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault()
                    send(draft)
                  }
                }}
                placeholder="Tell Atlas what you want to get done…"
                rows={1}
                className="max-h-40 min-h-[24px] flex-1 resize-none bg-transparent py-1.5 text-[14px] text-foreground placeholder:text-muted-foreground focus:outline-none"
              />
              <button
                onClick={() => send(draft)}
                disabled={!draft.trim() || thinking}
                className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-primary text-primary-foreground transition-[filter] hover:brightness-110 disabled:opacity-40"
              >
                <ArrowUp size={18} />
              </button>
            </div>
            <p className="mt-2 text-center text-[11px] text-muted-foreground">
              Enter to send · Shift + Enter for a new line
            </p>
          </div>
        </div>
      </div>

      {/* Live Work Feed */}
      <LiveWorkFeed working={working} pendingCount={pending.length} onReview={scrollToApprovals} />
    </div>
  )
}
