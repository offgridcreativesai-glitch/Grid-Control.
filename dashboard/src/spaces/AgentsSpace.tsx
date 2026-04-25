/**
 * AgentsSpace — Space 3
 * Tab 1 "Run": pipeline-ordered agent list with run buttons (absorbs AgentCommandCenter)
 * Tab 2 "Chat": 1-on-1 and group chat with agents (absorbs MeetingRoom)
 * Notion/Linear aesthetic: large text, generous padding, status-first.
 */

import {
  useState, useEffect, useRef, useCallback,
} from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import {
  Play, Loader2,
  Send, Mic, MicOff, MessagesSquare, Users,
  Radio, X, BookmarkPlus, Check, RefreshCw,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { apiFetch } from "@/lib/api"
import { useBrandStore } from "@/store/brandStore"
import type { Agent, ApiResponse } from "@/types"

// ── Types ──────────────────────────────────────────────────────────────────────

type Tab      = "run" | "chat"
type RoomMode = "individual" | "group"

interface Message {
  role:       "user" | "agent"
  content:    string
  timestamp:  string
  agentName?: string
}

interface ChatPayload {
  agentName:  string
  message:    string
  brand_slug: string
}

interface ChatMutationVars {
  payload:      ChatPayload
  agentSlugKey: string
}

interface GroupEntry {
  role:       "user" | "group"
  content:    string
  timestamp:  string
  responses?: { agent: string; message: string; timestamp: string }[]
}

// ── API helpers ────────────────────────────────────────────────────────────────

async function fetchAgents(slug: string): Promise<Agent[]> {
  const res  = await apiFetch(`/api/agents/status?brand_slug=${slug}`)
  const json: ApiResponse<Agent[]> = await res.json()
  if (!json.success) throw new Error(json.error)
  return json.data
}

async function fetchAgentList(): Promise<Agent[]> {
  const res  = await apiFetch("/api/agents")
  const json: ApiResponse<Agent[]> = await res.json()
  if (!json.success) throw new Error(json.error)
  return json.data
}

async function runAgent(agentName: string, brandSlug: string) {
  const res  = await apiFetch("/api/agents/run", {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify({ agentName, brand_slug: brandSlug }),
  })
  const json: ApiResponse<{ message: string; agent: string }> = await res.json()
  if (!json.success) throw new Error(json.error ?? "Agent run failed")
  return json.data
}

async function sendChat(vars: ChatMutationVars): Promise<string> {
  const res  = await apiFetch("/api/agents/chat", {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify(vars.payload),
  })
  const json = await res.json()
  if (!json.success) throw new Error(json.error)
  return typeof json.data === "string" ? json.data : (json.data?.response ?? json.data?.message ?? String(json.data))
}

async function sendGroupChat(payload: { brand_slug: string; message: string }): Promise<{ agent: string; message: string; timestamp: string }[]> {
  const res  = await apiFetch("/api/agents/group-chat", {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify(payload),
  })
  const json = await res.json()
  if (!json.success) throw new Error(json.error)
  return json.data
}

async function saveTraining(data: { agentName: string; note: string }): Promise<void> {
  await apiFetch("/api/agents/train", {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify(data),
  })
}

async function fetchStandup(brand_slug: string): Promise<string> {
  const res  = await apiFetch(`/api/agents/standup?brand_slug=${brand_slug}`)
  const json = await res.json()
  if (!json.success) throw new Error(json.error)
  return json.data
}

async function fetchConversation(brandSlug: string, agentSlug: string): Promise<Message[]> {
  const res  = await apiFetch(`/api/agents/conversation?brand_slug=${brandSlug}&agent_slug=${agentSlug}`)
  const json = await res.json()
  if (!json.success || !Array.isArray(json.data)) return []
  return json.data
}

// ── Helpers ────────────────────────────────────────────────────────────────────

function aSlug(name: string) {
  return name.toLowerCase().replace(/\s+/g, "-").replace(/[^a-z0-9-]/g, "")
}

function mentionSlug(name: string) { return aSlug(name) }

const AGENT_EMOJI: Record<string, string> = {
  "CEO Brain":             "🧠",
  "Trend Researcher":      "📊",
  "Strategy Agent":        "🎯",
  "Content Planner":       "📅",
  "Script Writer":         "✍️",
  "Creative Director":     "🎨",
  "Data Analyst":          "📈",
  "Funnel Specialist":     "🔁",
  "Website Agent":         "🌐",
  "Brand Guardian":        "🛡️",
  "SEO+AEO Agent":         "🔍",
  "Email Marketing Agent": "📧",
  "Community Manager":     "💬",
  "DM+Customer Hunter":    "🎣",
  "Ad Strategist":         "📣",
}

// Pipeline-first ordering for Run tab
const PIPELINE_ORDER = [
  "CEO Brain",
  "Trend Researcher",
  "Strategy Agent",
  "Content Planner",
  "Script Writer",
  "Creative Director",
  "Brand Guardian",
  "Data Analyst",
  "Funnel Specialist",
  "Website Agent",
  "SEO+AEO Agent",
  "Email Marketing Agent",
  "Community Manager",
  "DM+Customer Hunter",
  "Ad Strategist",
]

function sortAgents(agents: Agent[]): Agent[] {
  return [...agents].sort((a, b) => {
    const ai = PIPELINE_ORDER.indexOf(a.name)
    const bi = PIPELINE_ORDER.indexOf(b.name)
    return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi)
  })
}

// ── Voice input types ──────────────────────────────────────────────────────────

interface ISpeechRecognition {
  continuous: boolean; interimResults: boolean; lang: string
  onresult: ((e: ISpeechRecognitionEvent) => void) | null
  onerror: (() => void) | null; onend: (() => void) | null
  start: () => void; stop: () => void
}
interface ISpeechRecognitionEvent {
  results: { [key: number]: { [key: number]: { transcript: string } } }
}
function getSpeechRecognition() {
  const w = window as Window & { SpeechRecognition?: new () => ISpeechRecognition; webkitSpeechRecognition?: new () => ISpeechRecognition }
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null
}

// ── Save-as-training button ────────────────────────────────────────────────────

function SaveButton({ agentName, content }: { agentName: string; content: string }) {
  const [saved, setSaved] = useState(false)
  const mutation = useMutation({
    mutationFn: saveTraining,
    onSuccess: () => { setSaved(true); setTimeout(() => setSaved(false), 2000) },
  })
  return (
    <button onClick={() => mutation.mutate({ agentName, note: content })}
      className="flex items-center gap-1 text-[hsl(var(--gc-text-2))] hover:text-[hsl(var(--gc-gold))] transition-colors mt-1"
      style={{ fontSize: 12 }} disabled={mutation.isPending}>
      {saved ? <Check size={10} className="text-[hsl(var(--gc-green))]" /> : <BookmarkPlus size={10} />}
      {saved ? "Saved!" : "Save as Training"}
    </button>
  )
}

// ── Mic button ─────────────────────────────────────────────────────────────────

function MicButton({ onTranscript, disabled }: { onTranscript: (t: string) => void; disabled?: boolean }) {
  const [isListening, setIsListening] = useState(false)
  const [supported, setSupported]     = useState(false)
  const recogRef = useRef<ISpeechRecognition | null>(null)

  useEffect(() => { setSupported(!!getSpeechRecognition()) }, [])

  const startListening = useCallback(() => {
    const SR = getSpeechRecognition(); if (!SR) return
    const r = new SR()
    r.continuous = false; r.interimResults = false; r.lang = "en-US"
    r.onresult = (e: ISpeechRecognitionEvent) => { onTranscript(e.results[0][0].transcript); setIsListening(false) }
    r.onerror = () => setIsListening(false)
    r.onend   = () => setIsListening(false)
    recogRef.current = r; r.start(); setIsListening(true)
  }, [onTranscript])

  const stopListening = useCallback(() => { recogRef.current?.stop(); setIsListening(false) }, [])

  if (!supported) return null
  return (
    <button type="button" onClick={isListening ? stopListening : startListening}
      disabled={disabled}
      className={cn("flex items-center justify-center rounded-lg border transition-all shrink-0 w-9 h-9",
        isListening
          ? "bg-[rgba(231,76,60,0.1)] border-[rgba(231,76,60,0.4)] text-[hsl(var(--gc-red))] animate-pulse"
          : "border-[hsl(var(--border))] text-[hsl(var(--gc-text-2))] hover:text-white hover:border-[rgba(201,168,76,0.3)]"
      )}>
      {isListening ? <MicOff size={15} /> : <Mic size={15} />}
    </button>
  )
}

// ── Run tab ────────────────────────────────────────────────────────────────────

function RunTab() {
  const { activeBrand } = useBrandStore()
  const queryClient     = useQueryClient()
  const [runningAgent, setRunningAgent]   = useState<string | null>(null)
  const [runResults, setRunResults]       = useState<Record<string, { type: "success" | "error"; message: string }>>({})
  const prevStatusesRef = useRef<Record<string, string>>({})

  const { data: agents = [], isLoading, dataUpdatedAt } = useQuery({
    queryKey:        ["agents-run-tab", activeBrand.slug],
    queryFn:         () => fetchAgents(activeBrand.slug),
    refetchInterval: 10000,
    enabled:         !!activeBrand.slug,
  })

  useEffect(() => {
    const prev = prevStatusesRef.current
    let anyCompleted = false
    for (const a of agents) {
      if (prev[a.name] === "running" && a.status === "done") anyCompleted = true
      prev[a.name] = a.status
    }
    if (anyCompleted) {
      queryClient.invalidateQueries({ queryKey: ["outputs-pending", activeBrand.slug] })
      queryClient.invalidateQueries({ queryKey: ["brand-summary", activeBrand.slug] })
    }
  }, [agents, activeBrand.slug, queryClient])

  const mutation = useMutation({
    mutationFn: ({ name }: { name: string }) => runAgent(name, activeBrand.slug),
    onMutate: ({ name }) => {
      setRunningAgent(name)
      setRunResults(prev => { const n = { ...prev }; delete n[name]; return n })
    },
    onSuccess: (data) => {
      setRunResults(prev => ({ ...prev, [data.agent]: { type: "success", message: data.message } }))
      setTimeout(() => setRunResults(prev => { const n = { ...prev }; delete n[data.agent]; return n }), 8000)
    },
    onError: (err: Error, { name }) => {
      setRunResults(prev => ({ ...prev, [name]: { type: "error", message: err.message } }))
    },
    onSettled: () => {
      setRunningAgent(null)
      queryClient.invalidateQueries({ queryKey: ["agents-run-tab", activeBrand.slug] })
    },
  })

  const sorted     = sortAgents(agents)
  const ceoBrain   = sorted.find(a => a.id === 0)
  const specialists = sorted.filter(a => a.id !== 0)
  const runningCount = agents.filter(a => a.status === "running").length
  const doneCount    = specialists.filter(a => a.status === "done").length

  const statusColor = (s: string) =>
    s === "done"    ? "hsl(var(--gc-green))"  :
    s === "running" ? "hsl(var(--gc-amber))"  :
    s === "error"   ? "hsl(var(--gc-red))"    :
    "hsl(var(--gc-text-3))"

  const AgentRow = ({ agent }: { agent: Agent }) => {
    const result    = runResults[agent.name]
    const isRunning = runningAgent === agent.name || agent.status === "running"
    const isCEO     = agent.id === 0

    return (
      <div className={cn("gc-card rounded-xl p-5 flex items-center gap-4 gc-card-hover transition-all",
        isCEO && "border-[rgba(201,168,76,0.2)]")}>
        {/* Emoji */}
        <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 text-lg"
          style={{ background: isCEO ? "rgba(201,168,76,0.12)" : "hsl(var(--gc-surface2))",
            border: isCEO ? "1px solid rgba(201,168,76,0.25)" : "1px solid hsl(var(--border))" }}>
          {AGENT_EMOJI[agent.name] ?? "🤖"}
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <p className="text-white font-semibold" style={{ fontSize: 14 }}>{agent.name}</p>
            {isCEO && <span className="gc-verified">✓ Orchestrator</span>}
          </div>
          <p className="text-[hsl(var(--gc-text-2))] truncate mt-0.5" style={{ fontSize: 12 }}>{agent.role}</p>
          {result && (
            <p className="mt-1 truncate" style={{ fontSize: 12,
              color: result.type === "success" ? "hsl(var(--gc-green))" : "hsl(var(--gc-red))" }}>
              {result.type === "success" ? "✓ " : "✗ "}{result.message}
            </p>
          )}
        </div>

        {/* Status + last run */}
        <div className="text-right shrink-0 space-y-1">
          <div className="flex items-center justify-end gap-1.5">
            <div className="w-1.5 h-1.5 rounded-full" style={{ background: statusColor(agent.status) }} />
            <span style={{ fontSize: 12, color: statusColor(agent.status), fontWeight: 600, textTransform: "capitalize" }}>
              {agent.status}
            </span>
          </div>
          {agent.lastRun && (
            <p className="text-[hsl(var(--gc-text-2))]" style={{ fontSize: 12 }}>
              {new Date(agent.lastRun).toLocaleString("en-IN", { dateStyle: "short", timeStyle: "short" })}
            </p>
          )}
        </div>

        {/* Run button */}
        <button
          onClick={() => mutation.mutate({ name: agent.name })}
          disabled={isRunning || !!runningAgent}
          className={cn("h-9 px-4 rounded-lg font-semibold flex items-center gap-2 shrink-0 transition-all disabled:opacity-40",
            isCEO
              ? "bg-[hsl(var(--gc-gold))] text-black hover:opacity-85"
              : "border border-[hsl(var(--border))] text-[hsl(var(--gc-text-2))] hover:text-white hover:border-[rgba(201,168,76,0.4)]"
          )}
          style={{ fontSize: 13, background: isCEO ? "hsl(var(--gc-gold))" : "transparent" }}>
          {isRunning ? <Loader2 size={13} className="animate-spin" /> : <Play size={13} />}
          {isRunning ? "Running…" : "Run"}
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {/* Stats bar */}
      <div className="flex items-center gap-4">
        {runningCount > 0 && (
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg border"
            style={{ fontSize: 13, fontWeight: 600, color: "hsl(var(--gc-green))",
              background: "rgba(46,204,113,0.07)", borderColor: "rgba(46,204,113,0.2)" }}>
            <div className="w-2 h-2 rounded-full bg-[hsl(var(--gc-green))] animate-pulse" />
            {runningCount} Running
          </div>
        )}
        <span className="text-[hsl(var(--gc-text-2))]" style={{ fontSize: 13 }}>
          {doneCount} / {specialists.length} specialist agents done this session
        </span>
        <div className="ml-auto flex items-center gap-1.5 text-[hsl(var(--gc-text-2))]" style={{ fontSize: 12 }}>
          <RefreshCw size={10} className={cn(isLoading && "animate-spin")} />
          {dataUpdatedAt ? new Date(dataUpdatedAt).toLocaleTimeString("en-IN", { timeStyle: "short" }) : "—"}
        </div>
      </div>

      {isLoading ? (
        <div className="space-y-3">{Array.from({ length: 6 }).map((_, i) => <div key={i} className="h-20 gc-card rounded-xl animate-pulse" />)}</div>
      ) : (
        <>
          {/* CEO Brain */}
          {ceoBrain && (
            <div>
              <p className="text-[hsl(var(--gc-text-2))] uppercase tracking-widest font-medium mb-3" style={{ fontSize: 12 }}>
                Master Orchestrator
              </p>
              <AgentRow agent={ceoBrain} />
            </div>
          )}

          {/* Pipeline order */}
          <div>
            <p className="text-[hsl(var(--gc-text-2))] uppercase tracking-widest font-medium mb-3" style={{ fontSize: 12 }}>
              Specialist Agents — Pipeline Order
            </p>
            <div className="space-y-3">
              {specialists.map(a => <AgentRow key={a.id} agent={a} />)}
            </div>
          </div>
        </>
      )}
    </div>
  )
}

// ── Chat tab ───────────────────────────────────────────────────────────────────

function ChatTab() {
  const {
    activeBrand,
    individualHistories,
    groupHistories,
    setIndividualHistory,
    appendIndividualMessage,
    appendGroupEntry,
    clearGroupHistory,
  } = useBrandStore()
  const queryClient = useQueryClient()

  const [roomMode, setRoomMode]               = useState<RoomMode>("individual")
  const [input, setInput]                     = useState("")
  const [standupOpen, setStandupOpen]         = useState(false)
  const [selectedAgent, setSelectedAgent]     = useState<Agent | null>(null)
  const [mentionQuery, setMentionQuery]       = useState("")
  const [showMentionMenu, setShowMentionMenu] = useState(false)
  const bottomRef   = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const currentHistory: Message[] = selectedAgent
    ? (individualHistories[activeBrand.slug]?.[aSlug(selectedAgent.name)] ?? [])
    : []
  const groupHistory: GroupEntry[] = groupHistories[activeBrand.slug] ?? []

  const { data: agentList = [] } = useQuery({ queryKey: ["agents-list"], queryFn: fetchAgentList })

  const { data: persistedHistory = [] } = useQuery({
    queryKey: ["conversation", activeBrand.slug, selectedAgent ? aSlug(selectedAgent.name) : ""],
    queryFn:  () => selectedAgent ? fetchConversation(activeBrand.slug, aSlug(selectedAgent.name)) : Promise.resolve([]),
    enabled:  !!selectedAgent,
  })

  useEffect(() => {
    if (!selectedAgent) return
    const slug = aSlug(selectedAgent.name)
    if (persistedHistory.length > 0 && !individualHistories[activeBrand.slug]?.[slug]) {
      setIndividualHistory(activeBrand.slug, slug, persistedHistory)
    }
  }, [persistedHistory, selectedAgent]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [currentHistory, groupHistory])

  const handleTranscript = useCallback((text: string) => {
    setInput(prev => prev ? prev + " " + text : text)
  }, [])

  const standupMutation = useMutation({ mutationFn: () => fetchStandup(activeBrand.slug) })

  const chatMutation = useMutation({
    mutationFn: sendChat,
    onSuccess: (response, variables) => {
      const slug = variables.agentSlugKey
      appendIndividualMessage(activeBrand.slug, slug, {
        role: "agent", content: response, timestamp: new Date().toISOString(),
      })
      queryClient.invalidateQueries({ queryKey: ["conversation", activeBrand.slug, slug] })
    },
  })

  const groupChatMutation = useMutation({
    mutationFn: sendGroupChat,
    onSuccess: (responses) => {
      appendGroupEntry(activeBrand.slug, {
        role: "group", content: "", timestamp: new Date().toISOString(), responses,
      })
    },
  })

  const handleSendIndividual = () => {
    if (!input.trim() || !selectedAgent) return
    const slug = aSlug(selectedAgent.name)
    appendIndividualMessage(activeBrand.slug, slug, {
      role: "user", content: input.trim(), timestamp: new Date().toISOString(),
    })
    chatMutation.mutate({
      payload: { agentName: selectedAgent.name, message: input.trim(), brand_slug: activeBrand.slug },
      agentSlugKey: slug,
    })
    setInput("")
  }

  const handleSendGroup = () => {
    if (!input.trim()) return
    const msg = input.trim()
    setShowMentionMenu(false)
    appendGroupEntry(activeBrand.slug, { role: "user", content: msg, timestamp: new Date().toISOString() })
    groupChatMutation.mutate({ brand_slug: activeBrand.slug, message: msg })
    setInput("")
  }

  const handleSend = () => roomMode === "individual" ? handleSendIndividual() : handleSendGroup()

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend() }
  }

  const insertMention = (name: string) => {
    const slug    = mentionSlug(name)
    const lastAt  = input.lastIndexOf("@")
    const newInput = lastAt !== -1 ? input.slice(0, lastAt) + `@${slug} ` : `${input}@${slug} `
    setInput(newInput); setShowMentionMenu(false); setMentionQuery("")
    textareaRef.current?.focus()
  }

  const handleInputChange = (val: string) => {
    setInput(val)
    const lastAt = val.lastIndexOf("@")
    if (lastAt !== -1) {
      const afterAt = val.slice(lastAt + 1)
      if (!afterAt.includes(" ")) { setMentionQuery(afterAt.toLowerCase()); setShowMentionMenu(true); return }
    }
    setShowMentionMenu(false); setMentionQuery("")
  }

  const isSending  = chatMutation.isPending || groupChatMutation.isPending
  const canSend    = input.trim().length > 0 && (roomMode === "individual" ? !!selectedAgent : true)
  const mentionMatches = agentList.filter(a => mentionSlug(a.name).startsWith(mentionQuery) && a.name !== "CEO Brain")

  return (
    <div className="flex h-full overflow-hidden" style={{ minHeight: 0 }}>

      {/* ── Left panel ─────────────────────────────────────────────────── */}
      <div className="flex flex-col border-r border-[hsl(var(--border))] shrink-0" style={{ width: 220 }}>
        {/* Header */}
        <div className="px-4 py-4 border-b border-[hsl(var(--border))] flex items-center justify-between">
          <p className="text-[hsl(var(--gc-text-2))] uppercase tracking-widest font-medium" style={{ fontSize: 12 }}>Agents</p>
          <button
            onClick={() => { setStandupOpen(o => { if (!o) standupMutation.mutate(); return !o }) }}
            className={cn("flex items-center gap-1.5 px-2.5 py-1 rounded-lg border transition-colors",
              standupOpen
                ? "bg-[rgba(201,168,76,0.12)] border-[rgba(201,168,76,0.3)] text-[hsl(var(--gc-gold))]"
                : "border-transparent text-[hsl(var(--gc-text-2))] hover:text-white"
            )}
            style={{ fontSize: 12 }}>
            {standupMutation.isPending ? <Loader2 size={11} className="animate-spin" /> : <Radio size={11} />}
            Standup
          </button>
        </div>

        {/* Mode toggle */}
        <div className="px-3 py-3 border-b border-[hsl(var(--border))] flex gap-1.5">
          {[
            { mode: "individual" as const, icon: <MessagesSquare size={12} />, label: "1-on-1" },
            { mode: "group"      as const, icon: <Users           size={12} />, label: "Group"  },
          ].map(({ mode, icon, label }) => (
            <button key={mode} onClick={() => setRoomMode(mode)}
              className={cn("flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg border transition-colors",
                roomMode === mode
                  ? "bg-[rgba(201,168,76,0.1)] border-[rgba(201,168,76,0.3)] text-[hsl(var(--gc-gold))]"
                  : "border-[hsl(var(--border))] text-[hsl(var(--gc-text-2))] hover:text-white"
              )}
              style={{ fontSize: 12, fontWeight: 500 }}>
              {icon}{label}
            </button>
          ))}
        </div>

        {/* Agent list */}
        <div className="flex-1 overflow-y-auto py-2">
          {roomMode === "individual" ? agentList.map(agent => {
            const isActive = selectedAgent?.id === agent.id
            return (
              <button key={agent.id} onClick={() => setSelectedAgent(agent)}
                className={cn("w-full text-left flex items-center gap-3 px-4 py-2.5 border-l-2 transition-colors",
                  isActive
                    ? "border-l-[hsl(var(--gc-gold))] bg-[linear-gradient(90deg,rgba(201,168,76,0.07),transparent)]"
                    : "border-l-transparent hover:bg-[hsl(var(--gc-surface2))]"
                )}>
                <span style={{ fontSize: 15 }}>{AGENT_EMOJI[agent.name] ?? "🤖"}</span>
                <p style={{ fontSize: 13, fontWeight: 500 }}
                  className={isActive ? "text-white" : "text-[hsl(var(--gc-text-2))]"}>
                  {agent.name}
                </p>
              </button>
            )
          }) : (
            <div className="px-3 py-3 space-y-2">
              <div className="flex items-center gap-2 px-3 py-2 rounded-lg"
                style={{ background: "rgba(201,168,76,0.08)", border: "1px solid rgba(201,168,76,0.2)" }}>
                <div className="w-1.5 h-1.5 rounded-full bg-[hsl(var(--gc-gold))] shrink-0" />
                <span className="text-[hsl(var(--gc-gold))] font-semibold" style={{ fontSize: 12 }}>CEO Brain</span>
                <span className="text-[hsl(var(--gc-text-2))] ml-auto" style={{ fontSize: 11 }}>always replies</span>
              </div>
              <p className="text-[hsl(var(--gc-text-2))] uppercase tracking-widest font-medium px-1 pt-2" style={{ fontSize: 11 }}>Tag a specialist</p>
              {agentList.map(agent => (
                <button key={agent.id} type="button" onClick={() => insertMention(agent.name)}
                  className="w-full flex items-center gap-2 px-2 py-2 rounded-lg border border-transparent hover:bg-[hsl(var(--gc-surface2))] hover:border-[hsl(var(--border))] text-left transition-colors group">
                  <span style={{ fontSize: 13 }}>{AGENT_EMOJI[agent.name] ?? "🤖"}</span>
                  <p style={{ fontSize: 12, fontWeight: 500 }} className="text-[hsl(var(--gc-text-2))] group-hover:text-white truncate transition-colors">
                    {agent.name}
                  </p>
                  <span style={{ fontSize: 11, fontFamily: "monospace" }} className="ml-auto text-[hsl(var(--gc-text-2))] group-hover:text-[hsl(var(--gc-gold))] shrink-0 transition-colors">
                    @{mentionSlug(agent.name)}
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* ── Standup panel ──────────────────────────────────────────────── */}
      {standupOpen && (
        <div className="flex flex-col border-r border-[hsl(var(--border))] shrink-0" style={{ width: 260 }}>
          <div className="px-4 py-3 border-b border-[hsl(var(--border))] flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Radio size={13} className="text-[hsl(var(--gc-gold))]" />
              <p className="text-white font-semibold" style={{ fontSize: 14 }}>Team Standup</p>
            </div>
            <button onClick={() => setStandupOpen(false)} className="text-[hsl(var(--gc-text-2))] hover:text-white transition-colors">
              <X size={14} />
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-4">
            {standupMutation.isPending ? (
              <div className="flex items-center gap-2 text-[hsl(var(--gc-text-2))]" style={{ fontSize: 13 }}>
                <Loader2 size={14} className="animate-spin" /> Generating…
              </div>
            ) : standupMutation.isError ? (
              <p className="text-[hsl(var(--gc-red))]" style={{ fontSize: 13 }}>Failed to generate standup.</p>
            ) : standupMutation.data ? (
              <p className="text-white whitespace-pre-line" style={{ fontSize: 13, lineHeight: 1.7 }}>{standupMutation.data}</p>
            ) : (
              <p className="text-[hsl(var(--gc-text-2))]" style={{ fontSize: 13 }}>Click Standup to generate.</p>
            )}
          </div>
          <div className="px-4 py-3 border-t border-[hsl(var(--border))]">
            <button onClick={() => standupMutation.mutate()} disabled={standupMutation.isPending}
              className="w-full text-center text-[hsl(var(--gc-text-2))] hover:text-white transition-colors disabled:opacity-50"
              style={{ fontSize: 12 }}>
              Refresh
            </button>
          </div>
        </div>
      )}

      {/* ── Main chat area ──────────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col overflow-hidden">

        {/* INDIVIDUAL */}
        {roomMode === "individual" && (
          !selectedAgent ? (
            <div className="flex-1 flex flex-col items-center justify-center text-center p-8">
              <div className="w-16 h-16 rounded-2xl gc-card flex items-center justify-center mb-5 text-3xl">💬</div>
              <p className="text-white font-semibold" style={{ fontSize: 16 }}>Select an agent</p>
              <p className="text-[hsl(var(--gc-text-2))] mt-2" style={{ fontSize: 14 }}>
                Pick from the list on the left to start a conversation.
              </p>
            </div>
          ) : (
            <>
              <div className="flex items-center gap-4 px-6 py-4 border-b border-[hsl(var(--border))] shrink-0">
                <span style={{ fontSize: 22 }}>{AGENT_EMOJI[selectedAgent.name] ?? "🤖"}</span>
                <div className="flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-white font-semibold" style={{ fontSize: 15 }}>{selectedAgent.name}</span>
                    <span className="font-mono px-2 py-0.5 rounded border text-[hsl(var(--gc-text-2))] bg-[hsl(var(--gc-surface2))] border-[hsl(var(--border))]" style={{ fontSize: 11 }}>
                      {selectedAgent.model}
                    </span>
                    <span className="gc-verified">✓ Grounded</span>
                  </div>
                  <p className="text-[hsl(var(--gc-text-2))] mt-0.5" style={{ fontSize: 12 }}>{selectedAgent.role}</p>
                </div>
                <span className="text-[hsl(var(--gc-text-2))]" style={{ fontSize: 13 }}>
                  {currentHistory.length} messages
                </span>
              </div>

              <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
                {currentHistory.length === 0 && (
                  <div className="text-center py-12">
                    <p className="text-[hsl(var(--gc-text-2))]" style={{ fontSize: 14 }}>Start a conversation with {selectedAgent.name}</p>
                    <p className="text-[hsl(var(--gc-text-2))] mt-1" style={{ fontSize: 13 }}>Responses are grounded in your real brand data.</p>
                  </div>
                )}
                {currentHistory.map((msg, i) => (
                  <div key={i} className={cn("flex flex-col", msg.role === "user" ? "items-end" : "items-start")}>
                    <p className="text-[hsl(var(--gc-text-2))] mb-1.5 px-1" style={{ fontSize: 12 }}>
                      {msg.role === "user" ? "You" : selectedAgent.name}
                      {" · "}
                      {new Date(msg.timestamp).toLocaleTimeString("en-IN", { timeStyle: "short" })}
                    </p>
                    <div
                      className={cn("rounded-2xl px-4 py-3 whitespace-pre-line",
                        msg.role === "user" ? "rounded-br-sm text-black" : "rounded-bl-sm text-white border border-[hsl(var(--border))]"
                      )}
                      style={{
                        maxWidth: "75%", fontSize: 14, lineHeight: 1.7,
                        background: msg.role === "user" ? "hsl(var(--gc-gold))" : "hsl(var(--gc-surface2))",
                      }}>
                      {msg.content}
                    </div>
                    {msg.role === "agent" && <SaveButton agentName={selectedAgent.name} content={msg.content} />}
                  </div>
                ))}
                {chatMutation.isPending && (
                  <div className="flex items-start">
                    <div className="rounded-2xl rounded-bl-sm border border-[hsl(var(--border))] px-4 py-3"
                      style={{ background: "hsl(var(--gc-surface2))" }}>
                      <Loader2 size={15} className="animate-spin text-[hsl(var(--gc-text-2))]" />
                    </div>
                  </div>
                )}
                <div ref={bottomRef} />
              </div>
            </>
          )
        )}

        {/* GROUP */}
        {roomMode === "group" && (
          <>
            <div className="flex items-center justify-between px-6 py-4 border-b border-[hsl(var(--border))] shrink-0">
              <div>
                <p className="text-white font-semibold" style={{ fontSize: 15 }}>Group Meeting Room</p>
                <p className="text-[hsl(var(--gc-text-2))] mt-0.5" style={{ fontSize: 12 }}>
                  CEO Brain coordinates all specialists · use @name to address specific agents
                </p>
              </div>
              <div className="flex items-center gap-2">
                <span className="gc-verified">✓ Grounded</span>
                <button onClick={() => clearGroupHistory(activeBrand.slug)}
                  className="text-[hsl(var(--gc-text-3))] hover:text-[hsl(var(--gc-red))] transition-colors" title="Clear chat">
                  <X size={14} />
                </button>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
              {groupHistory.length === 0 && (
                <div className="text-center py-12">
                  <p className="text-[hsl(var(--gc-text-2))]" style={{ fontSize: 14 }}>Ask the full team a question</p>
                  <p className="text-[hsl(var(--gc-text-2))] mt-1" style={{ fontSize: 13 }}>Type @ to mention a specific agent</p>
                </div>
              )}
              {groupHistory.map((entry, i) => (
                <div key={i}>
                  {entry.role === "user" ? (
                    <div className="flex justify-end">
                      <div className="rounded-2xl rounded-br-sm px-4 py-3 text-black whitespace-pre-line"
                        style={{ maxWidth: "70%", fontSize: 14, lineHeight: 1.7, background: "hsl(var(--gc-gold))" }}>
                        {entry.content}
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {entry.responses?.map((r, j) => (
                        <div key={j} className="flex gap-3 items-start">
                          <div className="w-8 h-8 rounded-xl flex items-center justify-center text-sm shrink-0 mt-0.5"
                            style={{
                              background: r.agent === "CEO Brain" ? "rgba(201,168,76,0.12)" : "hsl(var(--gc-surface2))",
                              border: r.agent === "CEO Brain" ? "1px solid rgba(201,168,76,0.25)" : "1px solid hsl(var(--border))",
                            }}>
                            {AGENT_EMOJI[r.agent] ?? "🤖"}
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-baseline gap-2 mb-1.5">
                              <span style={{ fontSize: 13, fontWeight: 700 }}
                                className={r.agent === "CEO Brain" ? "text-[hsl(var(--gc-gold))]" : "text-white"}>
                                {r.agent}
                              </span>
                              <span className="text-[hsl(var(--gc-text-2))]" style={{ fontSize: 12 }}>
                                {new Date(r.timestamp).toLocaleTimeString("en-IN", { timeStyle: "short" })}
                              </span>
                              {r.agent === "CEO Brain" && <span className="gc-verified">✓ CEO</span>}
                            </div>
                            <p className="whitespace-pre-line" style={{ fontSize: 14, lineHeight: 1.7, color: "hsl(var(--gc-text-2))" }}>
                              {r.message}
                            </p>
                            <SaveButton agentName={r.agent} content={r.message} />
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
              {groupChatMutation.isPending && (
                <div className="flex items-center gap-2 text-[hsl(var(--gc-text-2))]" style={{ fontSize: 14 }}>
                  <Loader2 size={15} className="animate-spin text-[hsl(var(--gc-gold))]" />
                  Team is thinking…
                </div>
              )}
              <div ref={bottomRef} />
            </div>
          </>
        )}

        {/* ── Input ──────────────────────────────────────────────────────── */}
        <div className="shrink-0 px-5 py-4 border-t border-[hsl(var(--border))] relative"
          style={{ background: "hsl(var(--background))" }}>
          {/* @mention dropdown */}
          {showMentionMenu && mentionMatches.length > 0 && (
            <div className="absolute left-5 bottom-full mb-1 rounded-xl overflow-hidden shadow-xl z-50"
              style={{ background: "hsl(var(--gc-surface))", border: "1px solid rgba(255,255,255,0.06)", minWidth: 220 }}>
              {mentionMatches.map(a => (
                <button key={a.id} type="button" onClick={() => insertMention(a.name)}
                  className="w-full flex items-center gap-2 px-3 py-2.5 text-left hover:bg-[hsl(var(--gc-surface2))] transition-colors">
                  <span style={{ fontSize: 14 }}>{AGENT_EMOJI[a.name] ?? "🤖"}</span>
                  <span className="text-white font-medium" style={{ fontSize: 13 }}>{a.name}</span>
                  <span className="text-[hsl(var(--gc-text-2))] ml-auto font-mono" style={{ fontSize: 12 }}>@{mentionSlug(a.name)}</span>
                </button>
              ))}
            </div>
          )}

          <div className="flex items-end gap-2 rounded-xl overflow-hidden"
            style={{ background: "hsl(var(--gc-surface2))", border: "1px solid rgba(255,255,255,0.1)" }}>
            <textarea ref={textareaRef} value={input}
              onChange={e => handleInputChange(e.target.value)}
              onKeyDown={handleKeyDown} rows={1}
              placeholder={
                roomMode === "individual"
                  ? selectedAgent ? `Message ${selectedAgent.name}…` : "Select an agent first"
                  : "Ask the team anything… type @ to mention a specific agent"
              }
              disabled={isSending || (roomMode === "individual" && !selectedAgent)}
              className="flex-1 bg-transparent border-none outline-none resize-none text-white placeholder:text-[hsl(var(--gc-text-3))] py-3 px-4"
              style={{ fontSize: 14, maxHeight: 120, minHeight: 48, lineHeight: 1.6 }}
            />
            <div className="flex items-center gap-1.5 px-2 pb-2 shrink-0">
              <MicButton onTranscript={handleTranscript} disabled={isSending} />
              <button onClick={handleSend} disabled={!canSend || isSending}
                className="flex items-center gap-1.5 px-4 py-2.5 rounded-lg transition-opacity disabled:opacity-40 bg-[hsl(var(--gc-gold))] text-black font-bold"
                style={{ fontSize: 12, letterSpacing: 1 }}>
                {isSending ? <Loader2 size={12} className="animate-spin" /> : <Send size={12} />}
                Send
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Root ───────────────────────────────────────────────────────────────────────

export function AgentsSpace() {
  const { activeBrand } = useBrandStore()
  const [tab, setTab]   = useState<Tab>("run")

  const TABS: { id: Tab; label: string }[] = [
    { id: "run",  label: "Run Agents" },
    { id: "chat", label: "Chat" },
  ]

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Top bar */}
      <div style={{ height: 52, flexShrink: 0 }}
        className="flex items-center justify-between px-8 border-b border-[hsl(var(--border))]">
        <div className="flex items-center gap-2">
          <span className="text-[hsl(var(--gc-text-2))]" style={{ fontSize: 13 }}>Agents</span>
          <span className="text-[hsl(var(--gc-text-2))]" style={{ fontSize: 13 }}>/</span>
          <span className="text-white font-semibold" style={{ fontSize: 14 }}>
            {activeBrand.name || "—"}
          </span>
        </div>
        {/* Tab switcher */}
        <div className="flex gap-0 border-b-0">
          {TABS.map(t => (
            <button key={t.id} onClick={() => setTab(t.id)}
              className="px-4 py-1.5 rounded-lg font-medium transition-colors"
              style={{ fontSize: 13, ...(tab === t.id
                ? { background: "rgba(201,168,76,0.10)", color: "hsl(var(--gc-gold))", border: "1px solid rgba(201,168,76,0.28)" }
                : { background: "transparent", color: "hsl(var(--gc-text-2))", border: "1px solid transparent" }) }}>
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      {tab === "run" && (
        <div className="flex-1 overflow-y-auto">
          <div className="px-8 pt-8 pb-12 space-y-6">
            <div>
              <h1 className="text-white font-bold" style={{ fontSize: 24 }}>Run Agents</h1>
              <p className="text-[hsl(var(--gc-text-2))] mt-1" style={{ fontSize: 14 }}>
                Execute agents in pipeline order. CEO Brain orchestrates all.
              </p>
            </div>
            <RunTab />
          </div>
        </div>
      )}

      {tab === "chat" && (
        <div className="flex-1 overflow-hidden">
          <ChatTab />
        </div>
      )}
    </div>
  )
}
