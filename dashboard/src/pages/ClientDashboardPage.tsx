import { useState, useRef, useEffect, useMemo } from "react"
import {
  Send,
  Sparkles,
  Calendar,
  FileText,
  BarChart3,
  Zap,
  Loader2,
  Trash2,
  CheckSquare,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { useBrandStore } from "@/store/brandStore"
import { useBrainStore, type BrainMessage, type BrainProposal } from "@/store/brainStore"
import { useAppStore } from "@/store/appStore"
import { usePendingOutputs, usePerformanceHistory, useAgentStatus } from "@/hooks/useGridApi"
import { apiFetch } from "@/lib/api"

interface QuickAction {
  label: string
  icon: typeof Sparkles
  prompt: string
  color: string
}

function getQuickActions(pendingCount: number, hasCalendar: boolean): QuickAction[] {
  const actions: QuickAction[] = [
    {
      label: "Create content plan",
      icon: Calendar,
      prompt: "Create a 30-day content plan for my brand",
      color: "text-blue-400",
    },
    {
      label: "Write scripts",
      icon: FileText,
      prompt: "Write scripts for my next 5 posts",
      color: "text-emerald-400",
    },
    {
      label: "Analyze performance",
      icon: BarChart3,
      prompt: "Show me my content performance and what's working",
      color: "text-amber-400",
    },
    {
      label: "Research trends",
      icon: Zap,
      prompt: "What's trending in my niche right now?",
      color: "text-purple-400",
    },
  ]

  if (pendingCount > 0) {
    actions.unshift({
      label: `Review ${pendingCount} pending`,
      icon: CheckSquare,
      prompt: `Show me the ${pendingCount} outputs waiting for my approval`,
      color: "text-primary",
    })
  }

  return actions.slice(0, 4)
}

export function ClientDashboardPage() {
  const { activeBrand } = useBrandStore()
  const { setBrainOpen } = useAppStore()
  const { threads, appendMessage, updateMessage, clearThread } = useBrainStore()

  const scope = "global"
  const threadKey = `${activeBrand.slug}::${scope}`
  const messages: BrainMessage[] = threads[threadKey] ?? []

  const [input, setInput] = useState("")
  const [isThinking, setIsThinking] = useState(false)
  const [agentProgress, setAgentProgress] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  const { data: pending } = usePendingOutputs()
  const { data: perf } = usePerformanceHistory()
  const { data: agentStatus } = useAgentStatus()

  const pendingCount = pending?.outputs?.length ?? 0
  const runningAgents = agentStatus?.agents?.filter((a) => a.status === "running") ?? []

  useEffect(() => {
    if (runningAgents.length > 0) {
      const names = runningAgents.map((a) => a.name).join(", ")
      setAgentProgress(`Working: ${names}`)
    } else {
      setAgentProgress(null)
    }
  }, [runningAgents])

  const quickActions = useMemo(
    () => getQuickActions(pendingCount, false),
    [pendingCount],
  )

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, isThinking])

  // Close the right-rail Brain when on this page — the main area IS the brain
  useEffect(() => {
    setBrainOpen(false)
  }, [setBrainOpen])

  const handleSend = async (text?: string) => {
    const msg = text ?? input.trim()
    if (!msg || isThinking) return

    const userMessage: BrainMessage = {
      id: Date.now().toString(),
      role: "user",
      content: msg,
      createdAt: Date.now(),
    }

    const history = [...messages, userMessage]
    appendMessage(activeBrand.slug, scope, userMessage)
    setInput("")
    setIsThinking(true)

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
        proposals: (j.proposals || []).map((p: BrainProposal) => ({
          ...p,
          status: "pending" as const,
        })),
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
      setIsThinking(false)
      inputRef.current?.focus()
    }
  }

  const handleProposalAction = async (
    msgId: string,
    proposalIdx: number,
    approve: boolean,
  ) => {
    const msg = messages.find((m) => m.id === msgId)
    if (!msg?.proposals) return
    const prop = msg.proposals[proposalIdx]
    if (!prop || prop.status !== "pending") return

    const patchProposal = (status: BrainProposal["status"], result?: string) => {
      const updated = msg.proposals!.map((p, i) =>
        i === proposalIdx ? { ...p, status, ...(result !== undefined ? { result } : {}) } : p,
      )
      updateMessage(activeBrand.slug, scope, msgId, { proposals: updated })
    }

    if (!approve) {
      patchProposal("rejected")
      return
    }

    patchProposal("approved")
    try {
      const r = await apiFetch("/api/brain/execute", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ kind: prop.kind, payload: prop.payload }),
      })
      const j = await r.json()
      patchProposal(j.success ? "executed" : "failed", j.success ? j.result : j.error)
    } catch (e) {
      patchProposal("failed", e instanceof Error ? e.message : String(e))
    }
  }

  const hasHistory = messages.length > 0

  return (
    <div className="flex h-full flex-col">
      {/* Chat area */}
      <div className="flex-1 overflow-auto">
        {!hasHistory ? (
          /* Empty state — greeting + quick actions */
          <div className="flex h-full flex-col items-center justify-center px-6">
            <div className="w-full max-w-2xl space-y-8">
              {/* Greeting */}
              <div className="text-center space-y-2">
                <h1 className="text-3xl font-semibold tracking-tight">
                  What can I help you with?
                </h1>
                <p className="text-muted-foreground">
                  I manage your content, research trends, write scripts, and track performance for{" "}
                  <span className="font-medium text-foreground">{activeBrand.name}</span>.
                </p>
              </div>

              {/* Quick action cards */}
              <div className="grid grid-cols-2 gap-3">
                {quickActions.map((action) => (
                  <button
                    key={action.label}
                    onClick={() => handleSend(action.prompt)}
                    className="group flex items-start gap-3 rounded-xl border border-border bg-card p-4 text-left hover:bg-secondary/50 hover:border-primary/30 transition-all"
                  >
                    <action.icon className={cn("h-5 w-5 mt-0.5 shrink-0", action.color)} />
                    <span className="text-sm text-muted-foreground group-hover:text-foreground transition-colors">
                      {action.label}
                    </span>
                  </button>
                ))}
              </div>

              {/* Status bar */}
              {(agentProgress || pendingCount > 0) && (
                <div className="flex items-center justify-center gap-4 text-xs text-muted-foreground">
                  {agentProgress && (
                    <span className="flex items-center gap-1.5">
                      <Loader2 className="h-3 w-3 animate-spin" />
                      {agentProgress}
                    </span>
                  )}
                  {pendingCount > 0 && (
                    <span>{pendingCount} items awaiting review</span>
                  )}
                </div>
              )}
            </div>
          </div>
        ) : (
          /* Message history */
          <div className="mx-auto w-full max-w-2xl px-6 py-6 space-y-4">
            {messages.map((message) => (
              <div
                key={message.id}
                className={cn(
                  "flex",
                  message.role === "user" ? "justify-end" : "justify-start",
                )}
              >
                <div
                  className={cn(
                    "max-w-[85%] rounded-2xl px-4 py-3 text-sm",
                    message.role === "user"
                      ? "bg-primary text-primary-foreground"
                      : "bg-card border border-border",
                  )}
                >
                  <p className="whitespace-pre-wrap">{message.content}</p>

                  {/* Proposals */}
                  {message.proposals && message.proposals.length > 0 && (
                    <div className="mt-3 space-y-2">
                      {message.proposals.map((prop, idx) => (
                        <div
                          key={idx}
                          className="rounded-lg border border-border bg-background p-3 text-xs"
                        >
                          <div className="mb-2 flex items-center gap-2">
                            <span className="font-mono uppercase text-[10px] text-muted-foreground">
                              {prop.kind === "edit" ? "Propose edit" : "Propose bash"}
                            </span>
                            <span
                              className={cn(
                                "ml-auto rounded px-1.5 py-0.5 text-[10px] font-mono",
                                prop.status === "pending" && "bg-secondary text-muted-foreground",
                                prop.status === "approved" && "bg-secondary text-muted-foreground",
                                prop.status === "rejected" && "bg-destructive/20 text-destructive",
                                prop.status === "executed" && "bg-primary/20 text-primary",
                                prop.status === "failed" && "bg-destructive/20 text-destructive",
                              )}
                            >
                              {prop.status}
                            </span>
                          </div>
                          {prop.kind === "edit" ? (
                            <div className="space-y-1.5 font-mono">
                              <div className="text-muted-foreground">{prop.payload.path}</div>
                              <div className="rounded bg-destructive/10 p-1.5 text-destructive whitespace-pre-wrap break-all">
                                - {prop.payload.old_string?.slice(0, 200)}
                                {(prop.payload.old_string?.length ?? 0) > 200 ? "..." : ""}
                              </div>
                              <div className="rounded bg-primary/10 p-1.5 text-primary whitespace-pre-wrap break-all">
                                + {prop.payload.new_string?.slice(0, 200)}
                                {(prop.payload.new_string?.length ?? 0) > 200 ? "..." : ""}
                              </div>
                            </div>
                          ) : (
                            <div className="space-y-1.5 font-mono">
                              <div className="rounded bg-secondary p-1.5 whitespace-pre-wrap break-all">
                                $ {prop.payload.command}
                              </div>
                            </div>
                          )}
                          {prop.result && (
                            <pre className="mt-2 max-h-32 overflow-auto rounded bg-secondary/50 p-1.5 text-[10px] font-mono whitespace-pre-wrap break-all">
                              {prop.result.slice(0, 1500)}
                            </pre>
                          )}
                          {prop.status === "pending" && (
                            <div className="mt-2 flex gap-1.5">
                              <button
                                onClick={() => handleProposalAction(message.id, idx, true)}
                                className="flex-1 rounded bg-primary px-2 py-1 text-[11px] font-medium text-primary-foreground hover:opacity-90"
                              >
                                Approve & run
                              </button>
                              <button
                                onClick={() => handleProposalAction(message.id, idx, false)}
                                className="flex-1 rounded border border-border px-2 py-1 text-[11px] hover:bg-secondary"
                              >
                                Reject
                              </button>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}

            {isThinking && (
              <div className="flex justify-start">
                <div className="flex items-center gap-2 rounded-2xl bg-card border border-border px-4 py-3">
                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                  <span className="text-sm text-muted-foreground">Thinking...</span>
                </div>
              </div>
            )}

            {agentProgress && !isThinking && (
              <div className="flex justify-start">
                <div className="flex items-center gap-2 rounded-2xl bg-card border border-border px-4 py-2">
                  <Loader2 className="h-3 w-3 animate-spin text-primary" />
                  <span className="text-xs text-muted-foreground">{agentProgress}</span>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input area — always at bottom */}
      <div className="border-t border-border bg-background px-6 py-4">
        <div className="mx-auto w-full max-w-2xl">
          {/* Quick actions row when in conversation */}
          {hasHistory && (
            <div className="mb-3 flex items-center gap-2">
              <div className="flex gap-1.5 overflow-x-auto hide-scrollbar">
                {quickActions.map((action) => (
                  <button
                    key={action.label}
                    onClick={() => handleSend(action.prompt)}
                    className="flex shrink-0 items-center gap-1.5 rounded-full border border-border bg-card px-3 py-1 text-xs text-muted-foreground hover:bg-secondary transition-colors"
                  >
                    <action.icon className={cn("h-3 w-3", action.color)} />
                    {action.label}
                  </button>
                ))}
              </div>
              <button
                onClick={() => clearThread(activeBrand.slug, scope)}
                title="Clear chat"
                className="ml-auto shrink-0 flex h-6 w-6 items-center justify-center rounded hover:bg-secondary transition-colors"
              >
                <Trash2 className="h-3.5 w-3.5 text-muted-foreground" />
              </button>
            </div>
          )}

          <div className="relative">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                  e.preventDefault()
                  handleSend()
                }
              }}
              placeholder="Tell me what you need..."
              className="w-full resize-none rounded-xl border border-border bg-card px-4 py-3 pr-12 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
              rows={2}
            />
            <button
              onClick={() => handleSend()}
              disabled={!input.trim() || isThinking}
              className="absolute bottom-3 right-3 flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground disabled:opacity-30 transition-opacity hover:opacity-90"
            >
              {isThinking ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </button>
          </div>
          <p className="mt-1.5 text-center text-[10px] text-muted-foreground font-mono">
            Cmd+Enter to send
          </p>
        </div>
      </div>
    </div>
  )
}
