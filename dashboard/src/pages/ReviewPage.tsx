/**
 * Vault — every draft from first cut to live (route "/review").
 * Three stages: Drafts → Ready → Published. Real approve / publish flow.
 * THE SECRET: contributors shown as personas (never backend slugs / models).
 */
import { useState, useEffect, useCallback, useMemo } from "react"
import { useNavigate } from "react-router-dom"
import { Check, X, Send, ChevronDown, ChevronUp, MessageSquare, ExternalLink, Loader2 } from "lucide-react"
import { cn, formatTime } from "@/lib/utils"
import { type Platform } from "@/store/appStore"
import { StatusDot } from "@/components/ui/status-dot"
import { PlatformIcon } from "@/components/ui/platform-icon"
import { Button } from "@/components/ui/button"
import {
  usePendingOutputs, useApproveOutput, useRejectOutput, type PendingOutput,
  usePublishedPosts, usePublish, type PublishedPost, type PublishResult,
} from "@/hooks/useGridApi"
import { useBrainStore } from "@/store/brainStore"
import { useBrandStore } from "@/store/brandStore"
import { personaForSlug } from "@/lib/agentPersona"

type PipelineItem = {
  id: string
  platform: Platform
  draftedBy: string
  time: Date
  title?: string
  caption: string
  hashtags: string[]
  script?: string
  slideImages: string[]
  permalink?: string
}

type Stage = "pending" | "approved" | "published"

function inferPlatform(hay: string): Platform {
  const h = hay.toLowerCase()
  if (h.includes("instagram") || h.includes("ig")) return "instagram"
  if (h.includes("linkedin") || h.includes("li")) return "linkedin"
  if (h.includes("tiktok") || h.includes("tt")) return "tiktok"
  if (h.includes("youtube") || h.includes("yt")) return "youtube"
  return "x"
}

function adaptPending(po: PendingOutput): PipelineItem {
  return {
    id: po.filename,
    platform: inferPlatform(`${po.platform ?? ""} ${po.filename} ${po.agent_slug}`),
    draftedBy: personaForSlug(po.agent_slug).name,
    time: po.scheduled_for ? new Date(po.scheduled_for) : new Date(po.created_at),
    title: po.title || undefined,
    caption: po.caption || po.body_text || po.preview || "(no caption)",
    hashtags: po.hashtags || [],
    script: po.body_text || undefined,
    slideImages: po.slide_images || [],
  }
}

function adaptPublished(p: PublishedPost): PipelineItem {
  return {
    id: p.id,
    platform: inferPlatform(`${p.platform ?? ""} ${p.id} ${p.agent_slug}`),
    draftedBy: personaForSlug(p.agent_slug).name,
    time: p.posted_at ? new Date(p.posted_at) : p.scheduled_for ? new Date(p.scheduled_for) : new Date(p.approved_at),
    title: p.title || undefined,
    caption: p.caption || p.body_text || "(no caption)",
    hashtags: p.hashtags || [],
    script: p.body_text || undefined,
    slideImages: p.slide_images || [],
    permalink: (p as PublishedPost & { permalink?: string }).permalink,
  }
}

const STAGES: { key: Stage; label: string }[] = [
  { key: "pending", label: "Drafts" },
  { key: "approved", label: "Ready" },
  { key: "published", label: "Published" },
]

export function ReviewPage() {
  const { data: pendingData } = usePendingOutputs()
  const { data: publishedData } = usePublishedPosts()
  const approveMut = useApproveOutput()
  const rejectMut = useRejectOutput()
  const publishMut = usePublish()
  const navigate = useNavigate()
  const { activeBrand } = useBrandStore()
  const { appendMessage } = useBrainStore()

  const brandName = activeBrand.name
  const handle = (activeBrand.handle || activeBrand.slug || "").replace(/^@/, "")

  const [stage, setStage] = useState<Stage>("pending")
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [showScript, setShowScript] = useState(false)
  const [publishResult, setPublishResult] = useState<PublishResult | null>(null)

  const pending = useMemo(() => (pendingData?.outputs ?? []).map(adaptPending), [pendingData])
  const approved = useMemo(
    () => (publishedData?.data ?? []).filter((p) => p.status === "scheduled").map(adaptPublished),
    [publishedData],
  )
  const published = useMemo(
    () => (publishedData?.data ?? []).filter((p) => p.status === "published").map(adaptPublished),
    [publishedData],
  )

  const counts: Record<Stage, number> = { pending: pending.length, approved: approved.length, published: published.length }
  const items = stage === "pending" ? pending : stage === "approved" ? approved : published

  useEffect(() => {
    setSelectedId(items[0]?.id ?? null)
    setPublishResult(null)
    setShowScript(false)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stage])

  useEffect(() => {
    if ((!selectedId || !items.some((i) => i.id === selectedId)) && items.length > 0) {
      setSelectedId(items[0].id)
    }
  }, [items, selectedId])

  const selected = items.find((i) => i.id === selectedId) ?? null

  const navigateBy = useCallback(
    (dir: 1 | -1) => {
      const idx = items.findIndex((i) => i.id === selectedId)
      const next = idx + dir
      if (next >= 0 && next < items.length) setSelectedId(items[next].id)
    },
    [items, selectedId],
  )

  const handleApprove = useCallback(() => {
    if (!selectedId || stage !== "pending") return
    approveMut.mutate(selectedId)
    navigateBy(1)
  }, [selectedId, stage, navigateBy, approveMut])

  const handleReject = useCallback(() => {
    if (!selectedId || stage !== "pending") return
    rejectMut.mutate(selectedId)
    navigateBy(1)
  }, [selectedId, stage, navigateBy, rejectMut])

  const handlePublish = useCallback(() => {
    if (!selected || stage !== "approved") return
    setPublishResult(null)
    publishMut.mutate(
      { platform: selected.platform === "x" ? "twitter" : selected.platform, filename: selected.id },
      { onSuccess: (r) => setPublishResult(r.data ?? null) },
    )
  }, [selected, stage, publishMut])

  const handleRequestChanges = useCallback(() => {
    if (!selected) return
    const context = [
      `I want changes to this ${selected.platform} post:`,
      selected.title ? `Title: "${selected.title}"` : null,
      `Caption: "${selected.caption.slice(0, 200)}${selected.caption.length > 200 ? "..." : ""}"`,
      "",
      "Here's what I'd like changed: ",
    ]
      .filter(Boolean)
      .join("\n")
    appendMessage(activeBrand.slug, "global", {
      id: Date.now().toString(),
      role: "user",
      content: context,
      createdAt: Date.now(),
    })
    navigate("/command")
  }, [selected, activeBrand.slug, appendMessage, navigate])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return
      switch (e.key.toLowerCase()) {
        case "a": if (stage === "pending") handleApprove(); break
        case "r": if (stage === "pending") handleReject(); break
        case "e": if (stage === "pending") handleRequestChanges(); break
        case "j": if (!e.metaKey && !e.ctrlKey) navigateBy(1); break
        case "k": navigateBy(-1); break
      }
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [stage, handleApprove, handleReject, handleRequestChanges, navigateBy])

  return (
    <div className="flex h-full flex-col bg-background/60">
      {/* Header */}
      <div className="border-b border-border px-6 pb-4 pt-6">
        <div className="flex items-end justify-between gap-6">
          <div>
            <h1 className="font-display text-[24px] font-semibold tracking-tight text-foreground">Vault</h1>
            <p className="mt-1 text-[13.5px] text-muted-foreground">Every draft for {brandName} — from first cut to live.</p>
          </div>
          <div className="inline-flex rounded-xl border border-border bg-white/[0.02] p-0.5">
            {STAGES.map((s) => (
              <button
                key={s.key}
                onClick={() => setStage(s.key)}
                className={cn(
                  "flex items-center gap-1.5 rounded-lg px-3.5 py-1.5 text-[12.5px] font-medium transition-colors",
                  stage === s.key ? "bg-white/[0.07] text-foreground" : "text-muted-foreground hover:text-foreground",
                )}
              >
                {s.label}
                <span className={cn("rounded-full px-1.5 py-0.5 text-[10px]", stage === s.key ? "bg-primary/15 text-primary" : "text-muted-foreground")}>
                  {counts[s.key]}
                </span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {items.length === 0 ? (
        <div className="flex flex-1 items-center justify-center">
          <div className="text-center">
            <p className="text-[16px] font-semibold text-foreground">
              {stage === "pending" ? "No drafts waiting." : stage === "approved" ? "Nothing ready yet." : "Nothing published yet."}
            </p>
            <p className="mt-1 text-[13.5px] text-muted-foreground">
              {stage === "pending"
                ? "When the team prepares something, it shows here for your sign-off."
                : stage === "approved"
                  ? "Approve a draft and it lands here, ready to publish."
                  : "Published posts show here with their live links."}
            </p>
          </div>
        </div>
      ) : (
        <div className="flex flex-1 overflow-hidden">
          {/* List */}
          <div className="w-80 overflow-auto border-r border-border">
            <div className="divide-y divide-border">
              {items.map((it) => (
                <button
                  key={it.id}
                  onClick={() => { setSelectedId(it.id); setPublishResult(null) }}
                  className={cn(
                    "w-full px-4 py-3 text-left transition-colors hover:bg-white/[0.03]",
                    selectedId === it.id && "bg-white/[0.05]",
                  )}
                >
                  <div className="mb-1 flex items-center gap-2">
                    <PlatformIcon platform={it.platform} className="h-3.5 w-3.5" />
                    <span className="text-[11.5px] text-muted-foreground">{it.draftedBy}</span>
                    <StatusDot status={stage === "published" ? "success" : "queued"} className="ml-auto" />
                  </div>
                  {it.title && <p className="mb-0.5 line-clamp-1 text-[13.5px] font-medium text-foreground">{it.title}</p>}
                  <p className="line-clamp-2 text-[12px] text-muted-foreground">{it.caption}</p>
                </button>
              ))}
            </div>
          </div>

          {/* Preview + actions */}
          {selected && (
            <div className="flex flex-1 flex-col overflow-hidden">
              <div className="flex items-center gap-4 border-b border-border px-6 py-3.5">
                <div className="flex items-center gap-2">
                  <PlatformIcon platform={selected.platform} className="h-5 w-5" />
                  <span className="text-[13.5px] font-medium capitalize text-foreground">{selected.platform}</span>
                </div>
                <span className="text-[12px] text-muted-foreground">by {selected.draftedBy}</span>
                <span className="ml-auto text-[12px] text-muted-foreground">
                  {stage === "published" ? "Posted" : "Scheduled"}: {formatTime(selected.time)}
                </span>
              </div>

              <div className="flex-1 overflow-auto p-6">
                <div className="mx-auto max-w-lg">
                  <PostPreview item={selected} brandName={brandName} handle={handle} />

                  <div className="mt-6 space-y-4">
                    <div>
                      <h3 className="mb-2 text-[11px] font-medium uppercase tracking-[0.12em] text-muted-foreground">Caption</h3>
                      <p className="whitespace-pre-wrap text-[13.5px] text-foreground/90">{selected.caption}</p>
                    </div>

                    {selected.hashtags.length > 0 && (
                      <div>
                        <h3 className="mb-2 text-[11px] font-medium uppercase tracking-[0.12em] text-muted-foreground">Hashtags</h3>
                        <div className="flex flex-wrap gap-1.5">
                          {selected.hashtags.map((tag) => (
                            <span key={tag} className="text-[12.5px] text-emerald">{tag.startsWith("#") ? tag : `#${tag}`}</span>
                          ))}
                        </div>
                      </div>
                    )}

                    {selected.script && (
                      <div>
                        <button onClick={() => setShowScript(!showScript)} className="flex items-center gap-2 text-[12px] font-medium text-muted-foreground transition-colors hover:text-foreground">
                          {showScript ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                          Full script
                        </button>
                        {showScript && (
                          <pre className="mt-2 whitespace-pre-wrap rounded-lg bg-white/[0.03] p-3 text-[12px] text-muted-foreground">{selected.script}</pre>
                        )}
                      </div>
                    )}

                    {selected.permalink && (
                      <a href={selected.permalink} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 text-[12.5px] font-medium text-primary hover:underline">
                        <ExternalLink className="h-3.5 w-3.5" /> View live post
                      </a>
                    )}
                  </div>
                </div>
              </div>

              {/* Action bar */}
              <div className="flex items-center justify-between border-t border-border px-6 py-4">
                {stage === "pending" && (
                  <>
                    <div className="space-x-3 text-[11px] text-muted-foreground">
                      <span><kbd className="rounded bg-white/[0.06] px-1.5 py-0.5">A</kbd> approve</span>
                      <span><kbd className="rounded bg-white/[0.06] px-1.5 py-0.5">R</kbd> reject</span>
                      <span><kbd className="rounded bg-white/[0.06] px-1.5 py-0.5">E</kbd> edit</span>
                      <span><kbd className="rounded bg-white/[0.06] px-1.5 py-0.5">J</kbd>/<kbd className="rounded bg-white/[0.06] px-1.5 py-0.5">K</kbd> move</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button variant="outline" size="sm" onClick={handleReject}>
                        <X className="mr-1 h-4 w-4" /> Reject
                      </Button>
                      <Button variant="outline" size="sm" onClick={handleRequestChanges}>
                        <MessageSquare className="mr-1 h-4 w-4" /> Request changes
                      </Button>
                      <button
                        onClick={handleApprove}
                        className="inline-flex items-center gap-1.5 rounded-lg bg-emerald px-3.5 py-2 text-[13px] font-semibold text-[#06120E] transition-[filter] hover:brightness-110"
                      >
                        <Check className="h-4 w-4" /> Approve
                      </button>
                    </div>
                  </>
                )}

                {stage === "approved" && (
                  <>
                    <PublishOutcome result={publishResult} pending={publishMut.isPending} />
                    <Button size="sm" onClick={handlePublish} disabled={publishMut.isPending}>
                      {publishMut.isPending ? <Loader2 className="mr-1 h-4 w-4 animate-spin" /> : <Send className="mr-1 h-4 w-4" />}
                      {publishMut.isPending ? "Publishing…" : "Publish"}
                    </Button>
                  </>
                )}

                {stage === "published" && (
                  <span className="text-[12.5px] text-muted-foreground">Live. Engagement is tracked automatically.</span>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function PublishOutcome({ result, pending }: { result: PublishResult | null; pending: boolean }) {
  if (pending) return <span className="text-[12px] text-muted-foreground">Sending to platform…</span>
  if (!result) return <span className="text-[12px] text-muted-foreground">Review, then publish to the live account.</span>
  if (result.mode === "published")
    return (
      <span className="flex items-center gap-2 text-[12px] text-emerald">
        <Check className="h-3.5 w-3.5" /> Published.
        {result.permalink && (
          <a href={result.permalink} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 underline">
            <ExternalLink className="h-3 w-3" /> View
          </a>
        )}
      </span>
    )
  if (result.mode === "prepared")
    return <span className="text-[12px] text-[var(--status-queued)]">{result.note || "Prepared — token not live. Post manually for now."}</span>
  if (result.mode === "needs_video")
    return <span className="text-[12px] text-[var(--status-queued)]">{result.note || "Needs a real founder-recorded video. Nothing uploaded."}</span>
  if (result.mode === "unbuilt")
    return <span className="text-[12px] text-[var(--status-queued)]">{result.note || `${result.platform} publisher not built yet — nothing sent.`}</span>
  return <span className="text-[12px] text-destructive">{result.error || "Publish failed."}</span>
}

function PostPreview({ item, brandName, handle }: { item: PipelineItem; brandName: string; handle: string }) {
  const baseClasses = "glass-panel rounded-2xl overflow-hidden"
  const slides = item.slideImages ?? []
  const mediaUrl = (path: string) => `/api/outputs/media/${path}`

  switch (item.platform) {
    case "instagram":
      return (
        <div className={baseClasses}>
          {slides.length > 0 ? (
            <div className="relative aspect-square overflow-hidden bg-black/30">
              <div className="flex h-full snap-x snap-mandatory overflow-x-auto">
                {slides.map((path, i) => (
                  <img key={path} src={mediaUrl(path)} alt={`Slide ${i + 1}`} className="h-full w-full flex-shrink-0 snap-center object-contain" onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = "none" }} />
                ))}
              </div>
              {slides.length > 1 && (
                <div className="absolute right-2 top-2 rounded-full bg-black/60 px-2 py-0.5 text-[10px] text-white">1 / {slides.length}</div>
              )}
            </div>
          ) : (
            <div className="flex aspect-square items-center justify-center bg-black/30">
              <span className="text-[13px] text-muted-foreground">No image yet</span>
            </div>
          )}
          <div className="p-3">
            <div className="mb-2 flex items-center gap-2">
              <div className="h-8 w-8 rounded-full bg-white/[0.06]" />
              <span className="text-[13px] font-medium text-foreground">{handle}</span>
            </div>
            <p className="line-clamp-3 whitespace-pre-wrap text-[13px] text-foreground/90">{item.caption}</p>
          </div>
        </div>
      )

    case "x":
      return (
        <div className={cn(baseClasses, "p-4")}>
          <div className="flex gap-3">
            <div className="h-10 w-10 flex-shrink-0 rounded-full bg-white/[0.06]" />
            <div className="flex-1">
              <div className="mb-1 flex items-center gap-2">
                <span className="text-[13px] font-medium text-foreground">{brandName}</span>
                <span className="text-[13px] text-muted-foreground">@{handle}</span>
              </div>
              <p className="whitespace-pre-wrap text-[13px] text-foreground/90">{item.caption}</p>
            </div>
          </div>
        </div>
      )

    case "linkedin":
      return (
        <div className={baseClasses}>
          <div className="border-b border-border p-4">
            <div className="mb-3 flex items-center gap-3">
              <div className="h-12 w-12 rounded-full bg-white/[0.06]" />
              <div>
                <p className="text-[13px] font-medium text-foreground">{brandName}</p>
                <p className="text-[12px] text-muted-foreground">1st</p>
              </div>
            </div>
            <p className="line-clamp-6 whitespace-pre-wrap text-[13px] text-foreground/90">{item.caption}</p>
          </div>
        </div>
      )

    case "tiktok":
      return (
        <div className={cn(baseClasses, "relative flex aspect-[9/16] max-h-96 items-center justify-center bg-black/30")}>
          <span className="text-[13px] text-muted-foreground">Video preview</span>
          <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-4">
            <p className="line-clamp-2 text-[13px] text-white">{item.caption}</p>
          </div>
        </div>
      )

    case "youtube":
      return (
        <div className={baseClasses}>
          <div className="flex aspect-video items-center justify-center bg-black/30">
            <span className="text-[13px] text-muted-foreground">Thumbnail / video</span>
          </div>
          <div className="p-3">
            <p className="line-clamp-2 text-[13px] font-medium text-foreground">{item.caption}</p>
            <p className="mt-1 text-[12px] text-muted-foreground">{brandName}</p>
          </div>
        </div>
      )

    default:
      return null
  }
}
