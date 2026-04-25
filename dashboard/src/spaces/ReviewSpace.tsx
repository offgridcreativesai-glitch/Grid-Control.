/**
 * ReviewSpace — Space 2
 * Unified approval queue + content/media hub.
 * Tab 1: Approvals (Notion cards + local files)
 * Tab 2: Media (images, video, audio with inline preview)
 */

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import {
  ThumbsUp, XCircle, Edit3, ExternalLink, Download,
  Loader2, Clock, Inbox, FileText, Play, Music,
  ImageIcon, Maximize2, X, Check, Copy, FolderOpen,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { apiFetch } from "@/lib/api"
import { useBrandStore } from "@/store/brandStore"
import type { PendingOutput, NotionCard, ApiResponse } from "@/types"

// ── Types ──────────────────────────────────────────────────────────────────────

interface OutputFile {
  filename:    string
  filepath:    string
  agentName:   string
  contentType: string
  status:      "pending" | "approved"
  timestamp:   string
}

// ── Media helpers ──────────────────────────────────────────────────────────────

const IMAGE_EXTS = new Set(["PNG", "JPG", "JPEG", "WEBP", "GIF"])
const VIDEO_EXTS = new Set(["MP4", "MOV", "WEBM"])
const AUDIO_EXTS = new Set(["MP3", "WAV", "M4A", "OGG"])

function mediaCategory(ct: string): "image" | "video" | "audio" | "text" {
  const t = ct.toUpperCase()
  if (IMAGE_EXTS.has(t)) return "image"
  if (VIDEO_EXTS.has(t)) return "video"
  if (AUDIO_EXTS.has(t)) return "audio"
  return "text"
}

function mediaUrl(filepath: string)    { return `/api/outputs/media/${encodeURIComponent(filepath)}` }
function downloadUrl(filepath: string) { return `/api/outputs/download/${encodeURIComponent(filepath)}` }

// ── API helpers ────────────────────────────────────────────────────────────────

async function fetchNotionCards(slug: string): Promise<NotionCard[]> {
  const res  = await apiFetch(`/api/notion/cards?brand_slug=${slug}`)
  const json: ApiResponse<NotionCard[]> = await res.json()
  if (!json.success) throw new Error(json.error)
  return json.data
}

async function approveNotionCard(page_id: string, slug: string): Promise<void> {
  await apiFetch("/api/notion/approve", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ page_id, brand_slug: slug }),
  })
}

async function rejectNotionCard(page_id: string, slug: string): Promise<void> {
  await apiFetch("/api/notion/reject", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ page_id, brand_slug: slug }),
  })
}

async function fetchPending(slug: string): Promise<PendingOutput[]> {
  const res  = await apiFetch(`/api/outputs/pending?brand_slug=${slug}`)
  const json: ApiResponse<PendingOutput[]> = await res.json()
  if (!json.success) throw new Error(json.error)
  return json.data
}

async function approveFile(filepath: string, slug: string, output_id?: string | null): Promise<void> {
  await apiFetch("/api/outputs/approve", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ filepath, brand_slug: slug, output_id: output_id ?? "" }),
  })
}

async function rejectFile(filepath: string, slug: string, output_id?: string | null): Promise<void> {
  await apiFetch("/api/outputs/reject", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ filepath, brand_slug: slug, output_id: output_id ?? "" }),
  })
}

async function requestChanges(filepath: string, note: string): Promise<void> {
  await apiFetch("/api/outputs/request-changes", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ filepath, note }),
  })
}

async function fetchAllOutputs(slug: string): Promise<OutputFile[]> {
  const res  = await apiFetch(`/api/outputs/all?brand_slug=${slug}`)
  const json: ApiResponse<OutputFile[]> = await res.json()
  if (!json.success) throw new Error(json.error)
  return json.data
}

async function fetchOutputContent(filepath: string): Promise<string> {
  const res  = await apiFetch(`/api/outputs/content?filepath=${encodeURIComponent(filepath)}`)
  const json: ApiResponse<{ content: string; filename: string }> = await res.json()
  if (!json.success) throw new Error(json.error)
  return json.data.content
}

// ── Shared badge components ────────────────────────────────────────────────────

function AgentBadge({ label }: { label: string }) {
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded border"
      style={{ fontSize: 12, fontWeight: 600,
        background: "rgba(201,168,76,0.10)", color: "hsl(var(--gc-gold))",
        borderColor: "rgba(201,168,76,0.22)" }}>
      {label}
    </span>
  )
}


// ── Lightbox ───────────────────────────────────────────────────────────────────

function Lightbox({ src, onClose }: { src: string; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ background: "rgba(0,0,0,0.92)" }} onClick={onClose}>
      <button onClick={onClose}
        className="absolute top-5 right-5 w-10 h-10 rounded-full flex items-center justify-center"
        style={{ background: "rgba(255,255,255,0.1)" }}>
        <X size={16} className="text-white" />
      </button>
      <img src={src} alt="Preview"
        className="max-w-[90vw] max-h-[90vh] rounded-xl object-contain"
        onClick={e => e.stopPropagation()} />
    </div>
  )
}

// ── Notion Approvals ───────────────────────────────────────────────────────────

function NotionSection() {
  const { activeBrand } = useBrandStore()
  const queryClient     = useQueryClient()
  const [filter, setFilter] = useState<"pending_approval" | "all">("pending_approval")

  const { data: cards = [], isLoading } = useQuery({
    queryKey:        ["notion-cards", activeBrand.slug],
    queryFn:         () => fetchNotionCards(activeBrand.slug),
    refetchInterval: 10000,
  })

  const approveMutation = useMutation({
    mutationFn: (page_id: string) => approveNotionCard(page_id, activeBrand.slug),
    onSettled:  () => queryClient.invalidateQueries({ queryKey: ["notion-cards"] }),
  })

  const rejectMutation = useMutation({
    mutationFn: (page_id: string) => rejectNotionCard(page_id, activeBrand.slug),
    onSettled:  () => queryClient.invalidateQueries({ queryKey: ["notion-cards"] }),
  })

  const visible      = filter === "all" ? cards : cards.filter(c => c.status === "pending_approval")
  const pendingCount = cards.filter(c => c.status === "pending_approval").length

  const statusStyle = (s: string) => {
    if (s === "approved") return { color: "hsl(var(--gc-green))",  bg: "rgba(46,204,113,0.08)",  border: "rgba(46,204,113,0.2)"  }
    if (s === "rejected") return { color: "hsl(var(--gc-red))",    bg: "rgba(231,76,60,0.08)",   border: "rgba(231,76,60,0.2)"   }
    return                       { color: "hsl(var(--gc-amber))",  bg: "rgba(240,165,0,0.08)",   border: "rgba(240,165,0,0.22)"  }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        {(["pending_approval", "all"] as const).map(f => (
          <button key={f} onClick={() => setFilter(f)}
            className="px-3 py-1.5 rounded-lg font-medium transition-colors"
            style={{ fontSize: 13, ...(filter === f
              ? { background: "rgba(201,168,76,0.10)", color: "hsl(var(--gc-gold))",   border: "1px solid rgba(201,168,76,0.28)" }
              : { background: "hsl(var(--gc-surface))", color: "hsl(var(--gc-text-2))", border: "1px solid hsl(var(--border))" }) }}>
            {f === "pending_approval" ? `Pending (${pendingCount})` : `All (${cards.length})`}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="space-y-3">{[1,2,3].map(i => <div key={i} className="h-28 gc-card rounded-xl animate-pulse" />)}</div>
      ) : visible.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <div className="w-14 h-14 rounded-full gc-card flex items-center justify-center mb-4">
            <Inbox size={24} className="text-[hsl(var(--gc-text-2))]" />
          </div>
          <p className="text-white font-semibold" style={{ fontSize: 15 }}>
            {filter === "pending_approval" ? "No pending outputs" : "No Notion cards yet"}
          </p>
          <p className="text-[hsl(var(--gc-text-2))] mt-1" style={{ fontSize: 13 }}>
            {filter === "pending_approval" ? "Run an agent to generate outputs" : "Notion cards appear after agents run"}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {visible.map(card => {
            const ss         = statusStyle(card.status)
            const isPending  = card.status === "pending_approval"
            const isApproving = approveMutation.isPending && approveMutation.variables === card.page_id
            const isRejecting = rejectMutation.isPending  && rejectMutation.variables  === card.page_id

            return (
              <div key={card.page_id}
                className="gc-card rounded-xl p-5 space-y-4"
                style={isPending ? { borderColor: "rgba(240,165,0,0.2)" } : undefined}>
                <div className="flex items-start justify-between gap-4">
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 flex-wrap">
                      <AgentBadge label={card.agent} />
                      <span className="inline-flex items-center px-2 py-0.5 rounded border"
                        style={{ fontSize: 11, fontWeight: 600, color: ss.color, background: ss.bg, borderColor: ss.border }}>
                        {card.status === "pending_approval" ? "Pending" : card.status === "approved" ? "Approved" : "Rejected"}
                      </span>
                    </div>
                    <p className="text-white font-semibold" style={{ fontSize: 15 }}>{card.output_type}</p>
                  </div>
                  <div className="flex items-center gap-1.5 shrink-0 text-[hsl(var(--gc-text-2))]" style={{ fontSize: 12 }}>
                    <Clock size={12} />
                    {new Date(card.timestamp).toLocaleString("en-IN", { dateStyle: "short", timeStyle: "short" })}
                  </div>
                </div>

                <div className="flex items-center gap-2 flex-wrap">
                  {isPending && (
                    <>
                      <button
                        onClick={() => approveMutation.mutate(card.page_id)}
                        disabled={isApproving || isRejecting}
                        className="h-9 px-5 rounded-lg font-semibold flex items-center gap-2 transition-opacity disabled:opacity-50 hover:opacity-85"
                        style={{ fontSize: 13, background: "hsl(var(--gc-gold))", color: "#000" }}>
                        {isApproving ? <Loader2 size={13} className="animate-spin" /> : <ThumbsUp size={13} />}
                        Approve
                      </button>
                      <button
                        onClick={() => rejectMutation.mutate(card.page_id)}
                        disabled={isApproving || isRejecting}
                        className="h-9 px-5 rounded-lg font-semibold flex items-center gap-2 transition-opacity disabled:opacity-40 hover:opacity-80"
                        style={{ fontSize: 13, background: "transparent", color: "hsl(var(--gc-red))", border: "1px solid rgba(231,76,60,0.3)" }}>
                        {isRejecting ? <Loader2 size={13} className="animate-spin" /> : <XCircle size={13} />}
                        Reject
                      </button>
                    </>
                  )}
                  <a href={card.notion_url} target="_blank" rel="noopener noreferrer" className={isPending ? "ml-auto" : ""}>
                    <button className="h-8 px-3 rounded-lg flex items-center gap-1.5 text-[hsl(var(--gc-text-2))] hover:text-white transition-colors"
                      style={{ fontSize: 13, background: "transparent" }}>
                      <ExternalLink size={12} /> Open in Notion
                    </button>
                  </a>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

// ── Output Content Renderer ────────────────────────────────────────────────────

const SKIP_FIELDS = new Set(["scraped_at","scrape_status_per_source","topic_clusters","_last_updated","_note","variant_evaluation"])

function humanize(key: string) {
  return key.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase())
}

function JsonValue({ value, depth = 0 }: { value: unknown; depth?: number }) {
  if (value === null || value === undefined || value === "") {
    return <span className="text-[hsl(var(--gc-text-3))]">—</span>
  }
  if (typeof value === "string") {
    return (
      <p className="text-[hsl(var(--gc-text-1))] leading-relaxed" style={{ fontSize: 14 }}>
        {value}
      </p>
    )
  }
  if (Array.isArray(value)) {
    if (value.length === 0) return <span className="text-[hsl(var(--gc-text-3))]">—</span>
    if (value.every(v => typeof v === "string")) {
      return (
        <ul className="space-y-1.5 mt-1">
          {(value as string[]).map((v, i) => (
            <li key={i} className="flex items-start gap-2">
              <span className="mt-1.5 shrink-0 w-1.5 h-1.5 rounded-full bg-[hsl(var(--gc-gold))]" />
              <span className="text-[hsl(var(--gc-text-1))]" style={{ fontSize: 14 }}>{v}</span>
            </li>
          ))}
        </ul>
      )
    }
    return (
      <div className="space-y-3 mt-1">
        {(value as unknown[]).map((v, i) => (
          <div key={i} className="pl-3 border-l-2 border-[hsl(var(--border))]">
            <JsonValue value={v} depth={depth + 1} />
          </div>
        ))}
      </div>
    )
  }
  if (typeof value === "object") {
    const entries = Object.entries(value as Record<string, unknown>)
    return (
      <div className="space-y-3 mt-1">
        {entries.map(([k, v]) => (
          <div key={k}>
            <p className="font-semibold text-[hsl(var(--gc-text-2))] mb-1" style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: "0.06em" }}>
              {humanize(k)}
            </p>
            <JsonValue value={v} depth={depth + 1} />
          </div>
        ))}
      </div>
    )
  }
  return <span className="text-[hsl(var(--gc-text-1))]" style={{ fontSize: 14 }}>{String(value)}</span>
}

const SECTION_ORDER = [
  "summary","recommended_topic","recommendation_reason","contrarian_opportunities",
  "content_angles_to_pursue","content_angles_to_avoid",
  "instagram_trends","audience_language","google_trends","competitor_intel",
]

function OutputContentReader({ content }: { content: string }) {
  const [raw, setRaw] = useState(false)
  const parts    = content.split(/\n---+\n/, 2)
  const header   = parts[0].trim()
  const jsonText = parts[1]?.trim() ?? ""

  let jsonData: Record<string, unknown> | null = null
  try { jsonData = JSON.parse(jsonText) } catch {}

  const headerLines = header.split("\n").map(line => {
    const idx = line.indexOf(":")
    if (idx === -1) return { key: "", value: line.trim() }
    return { key: line.slice(0, idx).trim(), value: line.slice(idx + 1).trim() }
  }).filter(l => l.value)

  const sections = jsonData
    ? [
        ...SECTION_ORDER.filter(k => jsonData![k] !== undefined && !SKIP_FIELDS.has(k)).map(k => [k, jsonData![k]] as [string, unknown]),
        ...Object.entries(jsonData).filter(([k]) => !SKIP_FIELDS.has(k) && !SECTION_ORDER.includes(k))
      ]
    : []

  if (!jsonData) {
    return (
      <pre className="whitespace-pre-wrap text-[hsl(var(--gc-text-1))] leading-relaxed"
        style={{ fontSize: 13, fontFamily: "inherit", lineHeight: 1.7 }}>
        {content}
      </pre>
    )
  }

  return (
    <div className="space-y-6">
      {/* Toggle */}
      <div className="flex justify-end">
        <button onClick={() => setRaw(r => !r)}
          className="text-[hsl(var(--gc-text-3))] hover:text-[hsl(var(--gc-text-2))] transition-colors"
          style={{ fontSize: 12 }}>
          {raw ? "Show Formatted" : "Show Raw"}
        </button>
      </div>

      {raw ? (
        <pre className="whitespace-pre-wrap text-[hsl(var(--gc-text-2))] leading-relaxed"
          style={{ fontSize: 12, fontFamily: "monospace", lineHeight: 1.6 }}>
          {content}
        </pre>
      ) : (
        <>
          {/* LOOP Header */}
          <div className="space-y-3 pb-5 border-b border-[hsl(var(--border))]">
            {headerLines.map((line, i) => (
              <div key={i}>
                {line.key === "WINNER" ? (
                  <div className="p-4 rounded-xl"
                    style={{ background: "rgba(201,168,76,0.08)", border: "1px solid rgba(201,168,76,0.22)" }}>
                    <p className="font-bold text-[hsl(var(--gc-gold))] mb-1" style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.07em" }}>Winner</p>
                    <p className="text-white font-semibold leading-snug" style={{ fontSize: 15 }}>{line.value}</p>
                  </div>
                ) : line.key ? (
                  <div>
                    <p className="text-[hsl(var(--gc-text-3))] font-semibold mb-0.5" style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.06em" }}>{line.key}</p>
                    <p className="text-[hsl(var(--gc-text-1))]" style={{ fontSize: 14 }}>{line.value}</p>
                  </div>
                ) : (
                  <p className="text-[hsl(var(--gc-text-2))]" style={{ fontSize: 14 }}>{line.value}</p>
                )}
              </div>
            ))}
          </div>

          {/* JSON Sections */}
          <div className="space-y-6">
            {sections.map(([key, value]) => (
              <div key={key} className="space-y-2">
                <p className="font-bold text-white" style={{ fontSize: 13, textTransform: "uppercase", letterSpacing: "0.07em" }}>
                  {humanize(key)}
                </p>
                <JsonValue value={value} />
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}

// ── Output Reader Card ─────────────────────────────────────────────────────────

function OutputCard({ item, onApprove, onReject, approving, rejecting }: {
  item: PendingOutput
  onApprove: () => void
  onReject:  () => void
  approving: boolean
  rejecting: boolean
}) {
  const [expanded, setExpanded]     = useState(false)
  const [changing, setChanging]     = useState(false)
  const [changeNote, setChangeNote] = useState("")
  const queryClient = useQueryClient()
  const { activeBrand } = useBrandStore()

  const { data: fullContent, isLoading: contentLoading } = useQuery({
    queryKey: ["output-content", item.filepath],
    queryFn:  () => fetchOutputContent(item.filepath),
    enabled:  expanded && !!item.filepath,
    staleTime: Infinity,
  })

  const changesMutation = useMutation({
    mutationFn: ({ filepath, note }: { filepath: string; note: string }) => requestChanges(filepath, note),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["pending", activeBrand.slug] })
      setChanging(false); setChangeNote("")
    },
  })

  // Extract a human-readable title from preview or filename
  const title = (() => {
    if (item.preview) {
      const firstLine = item.preview.split("\n").find(l => l.trim())
      if (firstLine) return firstLine.replace(/^LOOP:\s*/i, "").slice(0, 80)
    }
    return item.filename.replace(/_/g, " ").replace(/\.\w+$/, "")
  })()

  const previewLines = item.preview
    ? item.preview.split("\n").slice(0, 6).join("\n")
    : ""

  const agentLabel = item.agentName
    .replace(/-/g, " ")
    .replace(/\b\w/g, c => c.toUpperCase())

  return (
    <div className="gc-card rounded-xl overflow-hidden"
      style={{ borderColor: "rgba(201,168,76,0.15)" }}>

      {/* Header */}
      <div className="p-5 space-y-3">
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-2 flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <AgentBadge label={agentLabel} />
              <span className="inline-flex items-center px-2 py-0.5 rounded border"
                style={{ fontSize: 11, fontWeight: 600,
                  color: "hsl(var(--gc-amber))", background: "rgba(240,165,0,0.08)",
                  borderColor: "rgba(240,165,0,0.22)" }}>
                Pending Approval
              </span>
            </div>
            <p className="text-white font-semibold leading-snug" style={{ fontSize: 15 }}>{title}</p>
          </div>
          <div className="flex items-center gap-1.5 shrink-0 text-[hsl(var(--gc-text-2))]" style={{ fontSize: 12 }}>
            <Clock size={12} />
            {new Date(item.timestamp).toLocaleString("en-IN", { dateStyle: "short", timeStyle: "short" })}
          </div>
        </div>

        {/* Preview snippet */}
        {previewLines && !expanded && (
          <p className="text-[hsl(var(--gc-text-2))] leading-relaxed whitespace-pre-wrap"
            style={{ fontSize: 13, lineHeight: 1.65 }}>
            {previewLines}
            {item.preview && item.preview.length > previewLines.length ? "…" : ""}
          </p>
        )}

        {/* Read Full Output toggle */}
        <button onClick={() => setExpanded(e => !e)}
          className="flex items-center gap-1.5 hover:text-white transition-colors"
          style={{ fontSize: 13, color: "hsl(var(--gc-gold))", background: "transparent", border: "none", padding: 0 }}>
          <FileText size={13} />
          {expanded ? "Collapse" : "Read Full Output"}
        </button>
      </div>

      {/* Expanded content */}
      {expanded && (
        <div className="border-t border-[hsl(var(--border))] mx-0">
          {contentLoading ? (
            <div className="flex items-center gap-2 p-5 text-[hsl(var(--gc-text-2))]" style={{ fontSize: 13 }}>
              <Loader2 size={14} className="animate-spin" /> Loading output…
            </div>
          ) : fullContent ? (
            <div className="p-5 max-h-[600px] overflow-y-auto"
              style={{ background: "rgba(0,0,0,0.25)" }}>
              <OutputContentReader content={fullContent} />
            </div>
          ) : (
            <p className="p-5 text-[hsl(var(--gc-text-2))]" style={{ fontSize: 13 }}>
              Could not load content.
            </p>
          )}
        </div>
      )}

      {/* Request changes input */}
      {changing && (
        <div className="border-t border-[hsl(var(--border))] p-5 space-y-2">
          <textarea
            className="w-full rounded-lg p-3 resize-none focus:outline-none"
            style={{ background: "rgba(0,0,0,0.3)", border: "1px solid hsl(var(--border))",
              color: "hsl(var(--foreground))", fontSize: 13, minHeight: 70 }}
            placeholder="Describe what needs to change…"
            value={changeNote}
            onChange={e => setChangeNote(e.target.value)}
          />
          <div className="flex gap-2">
            <button onClick={() => changesMutation.mutate({ filepath: item.filepath, note: changeNote })}
              disabled={!changeNote.trim()}
              className="h-8 px-4 rounded-lg font-semibold disabled:opacity-40 hover:opacity-85 transition-opacity"
              style={{ fontSize: 13, background: "hsl(var(--gc-gold))", color: "#000" }}>
              Save Note
            </button>
            <button onClick={() => { setChanging(false); setChangeNote("") }}
              className="h-8 px-3 rounded-lg text-[hsl(var(--gc-text-2))] hover:text-white transition-colors"
              style={{ fontSize: 13, background: "transparent" }}>
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Action bar */}
      <div className="flex items-center gap-2 px-5 py-3 border-t border-[hsl(var(--border))]"
        style={{ background: "rgba(0,0,0,0.15)" }}>
        <button onClick={onApprove} disabled={approving || rejecting}
          className="h-9 px-5 rounded-lg font-semibold flex items-center gap-2 disabled:opacity-40 hover:opacity-85 transition-opacity"
          style={{ fontSize: 13, background: "hsl(var(--gc-gold))", color: "#000" }}>
          {approving ? <Loader2 size={13} className="animate-spin" /> : <ThumbsUp size={13} />}
          Approve
        </button>
        <button onClick={() => setChanging(c => !c)}
          className="h-9 px-4 rounded-lg flex items-center gap-2 hover:text-white transition-colors"
          style={{ fontSize: 13, background: "transparent", color: "hsl(var(--gc-text-2))", border: "1px solid hsl(var(--border))" }}>
          <Edit3 size={13} /> Request Changes
        </button>
        <button onClick={onReject} disabled={approving || rejecting}
          className="h-9 px-4 rounded-lg flex items-center gap-2 disabled:opacity-40 hover:opacity-80 transition-opacity"
          style={{ fontSize: 13, background: "transparent", color: "hsl(var(--gc-red))", border: "1px solid rgba(231,76,60,0.3)" }}>
          {rejecting ? <Loader2 size={13} className="animate-spin" /> : <XCircle size={13} />}
          Reject
        </button>
        <div className="ml-auto flex items-center gap-1">
          {item.notion_url && (
            <a href={item.notion_url} target="_blank" rel="noopener noreferrer">
              <button className="h-8 px-3 rounded-lg flex items-center gap-1.5 text-[hsl(var(--gc-text-2))] hover:text-white transition-colors"
                style={{ fontSize: 12, background: "transparent" }}>
                <ExternalLink size={11} /> Notion
              </button>
            </a>
          )}
          {item.filepath && (
            <a href={downloadUrl(item.filepath)} download>
              <button className="h-8 px-3 rounded-lg flex items-center gap-1.5 text-[hsl(var(--gc-text-2))] hover:text-white transition-colors"
                style={{ fontSize: 12, background: "transparent" }}>
                <Download size={11} /> Download
              </button>
            </a>
          )}
        </div>
      </div>
    </div>
  )
}

// ── Local Files Section ────────────────────────────────────────────────────────

function LocalFilesSection() {
  const { activeBrand } = useBrandStore()
  const queryClient     = useQueryClient()

  const { data: items = [], isLoading } = useQuery({
    queryKey:        ["pending", activeBrand.slug],
    queryFn:         () => fetchPending(activeBrand.slug),
    refetchInterval: 10000,
    enabled:         !!activeBrand.slug,
  })

  const approveMutation = useMutation({
    mutationFn: ({ filepath, output_id }: { filepath: string; output_id?: string | null }) =>
      approveFile(filepath, activeBrand.slug, output_id),
    onSettled: () => queryClient.invalidateQueries({ queryKey: ["pending", activeBrand.slug] }),
  })

  const rejectMutation = useMutation({
    mutationFn: ({ filepath, output_id }: { filepath: string; output_id?: string | null }) =>
      rejectFile(filepath, activeBrand.slug, output_id),
    onSettled: () => queryClient.invalidateQueries({ queryKey: ["pending", activeBrand.slug] }),
  })

  if (isLoading) return <div className="space-y-3">{[1,2,3].map(i => <div key={i} className="h-28 gc-card rounded-xl animate-pulse" />)}</div>

  if (items.length === 0) return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="w-14 h-14 rounded-full gc-card flex items-center justify-center mb-4">
        <Inbox size={24} className="text-[hsl(var(--gc-text-2))]" />
      </div>
      <p className="text-white font-semibold" style={{ fontSize: 15 }}>No outputs pending approval</p>
      <p className="text-[hsl(var(--gc-text-2))] mt-1" style={{ fontSize: 13 }}>Run an agent from the Agents space to generate output</p>
    </div>
  )

  return (
    <div className="space-y-4">
      {items.map(item => (
        <OutputCard
          key={item.filepath || item.output_id}
          item={item}
          onApprove={() => approveMutation.mutate({ filepath: item.filepath, output_id: item.output_id })}
          onReject={() => rejectMutation.mutate({ filepath: item.filepath, output_id: item.output_id })}
          approving={approveMutation.isPending && approveMutation.variables?.filepath === item.filepath}
          rejecting={rejectMutation.isPending  && rejectMutation.variables?.filepath  === item.filepath}
        />
      ))}
    </div>
  )
}

// ── Media Grid ─────────────────────────────────────────────────────────────────

function MediaGrid() {
  const { activeBrand }                 = useBrandStore()
  const [filterType, setFilterType]     = useState("all")
  const [filterStatus, setFilterStatus] = useState<"all" | "pending" | "approved">("all")
  const [lightboxSrc, setLightboxSrc]   = useState<string | null>(null)
  const [selected, setSelected]         = useState<Set<string>>(new Set())

  const { data: files = [], isLoading } = useQuery({
    queryKey:        ["outputs-all", activeBrand.slug],
    queryFn:         () => fetchAllOutputs(activeBrand.slug),
    refetchInterval: 10000,
  })

  const contentTypes = ["all", ...Array.from(new Set(files.map(f => mediaCategory(f.contentType))))]

  const filtered = files.filter(f => {
    const sm = filterStatus === "all" || f.status === filterStatus
    const tm = filterType   === "all" || mediaCategory(f.contentType) === filterType
    return sm && tm
  })

  const toggleSelect = (fp: string) =>
    setSelected(prev => { const n = new Set(prev); n.has(fp) ? n.delete(fp) : n.add(fp); return n })

  return (
    <div className="space-y-5">
      {/* Filters */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-[hsl(var(--gc-text-2))] uppercase tracking-widest font-medium mr-1" style={{ fontSize: 12 }}>Status</span>
        {(["all", "pending", "approved"] as const).map(s => (
          <button key={s} onClick={() => setFilterStatus(s)}
            className="px-3 py-1.5 rounded-lg font-medium capitalize transition-colors"
            style={{ fontSize: 13, ...(filterStatus === s
              ? { background: "rgba(201,168,76,0.10)", color: "hsl(var(--gc-gold))", border: "1px solid rgba(201,168,76,0.28)" }
              : { background: "hsl(var(--gc-surface))", color: "hsl(var(--gc-text-2))", border: "1px solid hsl(var(--border))" }) }}>
            {s}
          </button>
        ))}
        {contentTypes.length > 1 && (
          <>
            <div className="w-px mx-2 h-4 bg-[hsl(var(--border))]" />
            <span className="text-[hsl(var(--gc-text-2))] uppercase tracking-widest font-medium mr-1" style={{ fontSize: 12 }}>Type</span>
            {contentTypes.map(t => (
              <button key={t} onClick={() => setFilterType(t)}
                className="px-3 py-1.5 rounded-lg font-medium capitalize transition-colors"
                style={{ fontSize: 13, ...(filterType === t
                  ? { background: "hsl(var(--gc-surface2))", color: "hsl(var(--foreground))", border: "1px solid rgba(201,168,76,0.3)" }
                  : { background: "hsl(var(--gc-surface))", color: "hsl(var(--gc-text-2))", border: "1px solid hsl(var(--border))" }) }}>
                {t}
              </button>
            ))}
          </>
        )}
        {selected.size >= 2 && (
          <button className="ml-auto h-9 px-4 rounded-lg flex items-center gap-1.5 font-semibold hover:opacity-85 transition-opacity"
            style={{ fontSize: 13, background: "hsl(var(--gc-gold))", color: "#000" }}>
            <Download size={13} /> Download ({selected.size})
          </button>
        )}
      </div>

      {/* Grid */}
      {isLoading ? (
        <div className="grid grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => <div key={i} className="h-56 gc-card rounded-xl animate-pulse" />)}
        </div>
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <div className="w-16 h-16 rounded-full gc-card flex items-center justify-center mb-4">
            <FolderOpen size={28} className="text-[hsl(var(--gc-text-2))]" />
          </div>
          <p className="text-white font-semibold" style={{ fontSize: 15 }}>No media yet</p>
          <p className="text-[hsl(var(--gc-text-2))] mt-1" style={{ fontSize: 13 }}>Run agents to generate content</p>
        </div>
      ) : (
        <div className="grid grid-cols-3 gap-4">
          {filtered.map(file => <MediaCard key={file.filepath} file={file}
            selected={selected.has(file.filepath)}
            onToggle={toggleSelect}
            onLightbox={setLightboxSrc} />
          )}
        </div>
      )}

      {lightboxSrc && <Lightbox src={lightboxSrc} onClose={() => setLightboxSrc(null)} />}
    </div>
  )
}

function MediaCard({ file, selected, onToggle, onLightbox }: {
  file: OutputFile; selected: boolean
  onToggle: (fp: string) => void; onLightbox: (src: string) => void
}) {
  const [copied, setCopied] = useState(false)
  const cat = mediaCategory(file.contentType)
  const url = mediaUrl(file.filepath)

  const statusStyle = file.status === "approved"
    ? { bg: "rgba(46,204,113,0.08)", color: "hsl(var(--gc-green))", border: "rgba(46,204,113,0.2)", label: "Approved" }
    : { bg: "rgba(240,165,0,0.08)",  color: "hsl(var(--gc-amber))", border: "rgba(240,165,0,0.22)", label: "Pending" }

  return (
    <div className={cn("gc-card rounded-xl flex flex-col overflow-hidden gc-card-hover transition-all")}
      style={selected ? { borderColor: "hsl(var(--gc-gold))", boxShadow: "0 0 0 1px rgba(201,168,76,0.15)" } : undefined}>
      {/* Preview */}
      {cat === "image" ? (
        <div className="relative w-full cursor-zoom-in group overflow-hidden rounded-t-xl"
          style={{ height: 160, background: "hsl(var(--gc-surface2))" }}
          onClick={() => onLightbox(url)}>
          <img src={url} alt={file.filename}
            className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105" loading="lazy" />
          <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
            style={{ background: "rgba(0,0,0,0.4)" }}>
            <Maximize2 size={20} className="text-white" />
          </div>
          <span className="absolute top-2 right-2 px-1.5 py-0.5 rounded text-[10px] font-bold uppercase"
            style={{ background: "rgba(0,0,0,0.6)", color: "#fff" }}>{file.contentType}</span>
        </div>
      ) : cat === "video" ? (
        <div className="w-full rounded-t-xl overflow-hidden" style={{ background: "#000" }}>
          <video src={url} controls preload="metadata" className="w-full" style={{ maxHeight: 180, display: "block" }} />
        </div>
      ) : cat === "audio" ? (
        <div className="w-full rounded-t-xl flex flex-col items-center justify-center gap-3"
          style={{ height: 100, background: "hsl(var(--gc-surface2))", padding: "12px 16px" }}>
          <Music size={24} className="text-[hsl(var(--gc-gold))]" />
          <audio controls src={url} className="w-full" style={{ height: 32 }} />
        </div>
      ) : (
        <div className="w-full rounded-t-xl flex items-center justify-center"
          style={{ height: 80, background: "hsl(var(--gc-surface2))" }}>
          <FileText size={28} className="text-[hsl(var(--gc-text-3))]" />
        </div>
      )}

      {/* Body */}
      <div className="p-4 flex flex-col gap-3 flex-1">
        <div className="flex items-start gap-2">
          <input type="checkbox" checked={selected} onChange={() => onToggle(file.filepath)}
            className="mt-0.5 w-3.5 h-3.5 shrink-0 cursor-pointer"
            style={{ accentColor: "hsl(var(--gc-gold))" }} />
          <div className="flex-1 min-w-0">
            <p className="text-white font-semibold truncate" style={{ fontSize: 13 }}>{file.filename}</p>
            <p className="text-[hsl(var(--gc-text-2))] truncate mt-0.5" style={{ fontSize: 12 }}>{file.agentName}</p>
          </div>
        </div>

        <div className="flex flex-wrap gap-1.5">
          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded border"
            style={{ fontSize: 11, fontWeight: 600, background: "hsl(var(--gc-surface2))", color: "hsl(var(--gc-text-2))", borderColor: "hsl(var(--border))" }}>
            {cat === "image" ? <ImageIcon size={10} /> : cat === "video" ? <Play size={10} /> : cat === "audio" ? <Music size={10} /> : <FileText size={10} />}
            {file.contentType}
          </span>
          <span className="inline-flex items-center px-1.5 py-0.5 rounded border"
            style={{ fontSize: 11, fontWeight: 600, background: statusStyle.bg, color: statusStyle.color, borderColor: statusStyle.border }}>
            {statusStyle.label}
          </span>
        </div>

        <p className="text-[hsl(var(--gc-text-2))]" style={{ fontSize: 12 }}>
          {new Date(file.timestamp).toLocaleString("en-IN", { dateStyle: "short", timeStyle: "short" })}
        </p>

        <div className="flex items-center gap-1.5 mt-auto">
          <a href={downloadUrl(file.filepath)} download className="flex-1">
            <button className="w-full h-7 rounded-lg text-[12px] font-medium flex items-center justify-center gap-1 hover:text-white transition-colors"
              style={{ background: "transparent", color: "hsl(var(--gc-text-2))", border: "1px solid hsl(var(--border))" }}>
              <Download size={11} /> Download
            </button>
          </a>
          <button className="h-7 w-7 rounded-lg flex items-center justify-center hover:text-white transition-colors flex-shrink-0"
            style={{ color: "hsl(var(--gc-text-2))", background: "transparent" }}
            onClick={() => { navigator.clipboard.writeText(file.filepath); setCopied(true); setTimeout(() => setCopied(false), 2000) }}>
            {copied ? <Check size={11} style={{ color: "hsl(var(--gc-green))" }} /> : <Copy size={11} />}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Root ───────────────────────────────────────────────────────────────────────

type Tab = "approvals" | "media"

export function ReviewSpace() {
  const { activeBrand } = useBrandStore()
  const [tab, setTab]   = useState<Tab>("approvals")

  const { data: notionCards = [] } = useQuery({
    queryKey:        ["notion-cards", activeBrand.slug],
    queryFn:         () => fetchNotionCards(activeBrand.slug),
    refetchInterval: 10000,
    enabled:         !!activeBrand.slug,
  })
  const pendingCount = notionCards.filter(c => c.status === "pending_approval").length

  const TABS: { id: Tab; label: string; badge?: number }[] = [
    { id: "approvals", label: "Approvals", badge: pendingCount },
    { id: "media",     label: "Media Library" },
  ]

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Top bar */}
      <div style={{ height: 52, flexShrink: 0 }}
        className="flex items-center justify-between px-8 border-b border-[hsl(var(--border))]">
        <div className="flex items-center gap-2">
          <span className="text-[hsl(var(--gc-text-2))]" style={{ fontSize: 13 }}>Review</span>
          <span className="text-[hsl(var(--gc-text-2))]" style={{ fontSize: 13 }}>/</span>
          <span className="text-white font-semibold" style={{ fontSize: 14 }}>
            {activeBrand.name || "—"}
          </span>
        </div>
        {pendingCount > 0 && (
          <span className="px-3 py-1 rounded border font-semibold"
            style={{ fontSize: 12, color: "hsl(var(--gc-amber))", background: "rgba(240,165,0,0.08)", borderColor: "rgba(240,165,0,0.25)" }}>
            {pendingCount} Pending
          </span>
        )}
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto">
        <div className="px-8 pt-8 pb-12 space-y-6">

          {/* Page title */}
          <div>
            <h1 className="text-white font-bold" style={{ fontSize: 26 }}>Review</h1>
            <p className="text-[hsl(var(--gc-text-2))] mt-1" style={{ fontSize: 14 }}>
              Approve agent outputs and browse generated media
            </p>
          </div>

          {/* Tab bar */}
          <div className="flex gap-0 border-b border-[hsl(var(--border))]">
            {TABS.map(t => (
              <button key={t.id} onClick={() => setTab(t.id)}
                className="relative px-5 py-3 font-medium transition-colors -mb-px border-b-2"
                style={{ fontSize: 14, ...(tab === t.id
                  ? { color: "hsl(var(--gc-gold))", borderBottomColor: "hsl(var(--gc-gold))" }
                  : { color: "hsl(var(--gc-text-2))", borderBottomColor: "transparent" }) }}>
                {t.label}
                {t.badge != null && t.badge > 0 && (
                  <span className="ml-2 rounded-full inline-flex items-center justify-center"
                    style={{ minWidth: 18, height: 18, padding: "0 5px", fontSize: 11, fontWeight: 700,
                      background: "rgba(240,165,0,0.12)", color: "hsl(var(--gc-amber))" }}>
                    {t.badge}
                  </span>
                )}
              </button>
            ))}
          </div>

          {tab === "approvals" && (
            <div className="space-y-8">
              <div>
                <p className="text-[hsl(var(--gc-text-2))] uppercase tracking-widest font-medium mb-4" style={{ fontSize: 12 }}>
                  Notion Outputs
                </p>
                <NotionSection />
              </div>
              <div>
                <p className="text-[hsl(var(--gc-text-2))] uppercase tracking-widest font-medium mb-4" style={{ fontSize: 12 }}>
                  Local Files
                </p>
                <LocalFilesSection />
              </div>
            </div>
          )}

          {tab === "media" && <MediaGrid />}
        </div>
      </div>
    </div>
  )
}
