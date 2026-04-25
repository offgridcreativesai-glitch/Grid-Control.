/**
 * BrandOnboarding — GRID CONTROL
 * Screen for creating a new brand profile.
 * Agents read this before doing any work for the brand.
 */

import { useState, useEffect } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import {
  Loader2, CheckCircle, AlertCircle, RefreshCw,
  Plus, X, ExternalLink, Wifi, WifiOff, Lock,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { useBrandStore } from "@/store/brandStore"
import type { ApiResponse } from "@/types"
import { apiFetch } from "@/lib/api"

// ── Types ──────────────────────────────────────────────────────────────────────

interface PlatformHandle {
  platform: string
  handle: string
}

interface CreateBrandPayload {
  brand_name: string
  brand_slug: string
  industry: string
  phase: string
  product_description: string
  website_url: string
  price_india: string
  price_international: string
  target_audience: string
  platforms: string[]
  platform_handles: PlatformHandle[]
  primary_bottleneck: string
  instagram_handle: string   // kept for agent backward-compat
  competitor_handles: string[]
  brand_face: string
  tone_of_voice: string
  tone_specifics: string
  content_goal_90d: string
  weekly_post_target: string
  past_content_worked: string
  what_to_never_say: string
  has_existing_pipeline: boolean
  existing_pipeline: string
  railway_url: string
}

interface ConnectionStatus {
  instagram: boolean
  linkedin: boolean
  youtube: boolean
  meta_ads: boolean
}

// ── Helpers ────────────────────────────────────────────────────────────────────

function slugify(name: string): string {
  return name.toLowerCase().replace(/\s+/g, "-").replace(/[^a-z0-9-]/g, "").replace(/-+/g, "-")
}

async function createBrand(payload: CreateBrandPayload): Promise<{ slug: string; name: string }> {
  let res: Response
  try {
    res = await apiFetch("/api/brands/create", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
  } catch {
    throw new Error("Cannot reach server — make sure the Flask API is running on port 5001.")
  }
  let json: ApiResponse<{ slug: string; brand_slug: string; name: string }>
  try {
    json = await res.json()
  } catch {
    throw new Error(`Server error (HTTP ${res.status}) — check the Flask API logs.`)
  }
  if (!json.success) throw new Error((json as unknown as { error: string }).error)
  const d = json.data
  return { slug: d.slug ?? d.brand_slug, name: d.name }
}

async function fetchConnectionStatus(): Promise<ConnectionStatus> {
  const res = await apiFetch("/api/connections/check")
  const json: ApiResponse<Record<string, { connected: boolean }>> = await res.json()
  if (!json.success) return { instagram: false, linkedin: false, youtube: false, meta_ads: false }
  const d = json.data
  return {
    instagram: d.meta?.connected ?? false,
    linkedin:  d.linkedin?.connected ?? false,
    youtube:   false,  // not yet wired
    meta_ads:  d.meta?.connected ?? false,
  }
}

// ── Platform config ────────────────────────────────────────────────────────────

const PLATFORM_CONFIG: Record<string, {
  label: string
  handleLabel: string
  placeholder: string
  prefix?: string
  oauthNote: string
}> = {
  Instagram: {
    label: "Instagram",
    handleLabel: "Instagram handle",
    placeholder: "yourbrand",
    prefix: "@",
    oauthNote: "Connect via Meta Graph API to pull real post data, engagement rates, and audience insights.",
  },
  LinkedIn: {
    label: "LinkedIn",
    handleLabel: "LinkedIn company page",
    placeholder: "your-company-name",
    prefix: "linkedin.com/company/",
    oauthNote: "Connect via LinkedIn API to pull company updates, follower data, and post analytics.",
  },
  YouTube: {
    label: "YouTube",
    handleLabel: "YouTube channel handle",
    placeholder: "yourchannel",
    prefix: "@",
    oauthNote: "Connect via YouTube Data API to pull video performance, subscribers, and watch time.",
  },
  Twitter: {
    label: "Twitter / X",
    handleLabel: "Twitter / X handle",
    placeholder: "yourbrand",
    prefix: "@",
    oauthNote: "Connect via Twitter API v2 for tweet analytics and follower insights.",
  },
  WhatsApp: {
    label: "WhatsApp",
    handleLabel: "WhatsApp Business number",
    placeholder: "+91 98765 43210",
    oauthNote: "WhatsApp Business API for broadcast and engagement tracking.",
  },
}

const ALL_PLATFORMS = ["Instagram", "LinkedIn", "YouTube", "Twitter", "WhatsApp"]

const BOTTLENECK_OPTIONS = [
  { value: "Awareness",  label: "Awareness — not enough people know us" },
  { value: "Trust",      label: "Trust — people know us but don't convert" },
  { value: "Conversion", label: "Conversion — traffic but no sales" },
  { value: "Retention",  label: "Retention — one-time buyers, no repeat" },
  { value: "All",        label: "All of the above" },
]

const BRAND_FACE_OPTIONS = [
  { value: "Person",    label: "Person — founder or a specific person is the face" },
  { value: "Product",   label: "Product — product/service is the hero, no face" },
  { value: "Both",      label: "Both — mix of person and product content" },
  { value: "Character", label: "Brand character / mascot" },
]

const GOAL_OPTIONS = [
  { value: "Followers",   label: "Grow followers — build audience first" },
  { value: "Sales",       label: "Drive sales — convert audience to buyers" },
  { value: "Awareness",   label: "Brand awareness — be known in the category" },
  { value: "Leads",       label: "Lead generation — get inbound interest" },
  { value: "Trust",       label: "Build trust — social proof + credibility" },
]

const POST_FREQ_OPTIONS = [
  { value: "1x",    label: "1x per week" },
  { value: "3x",    label: "3x per week" },
  { value: "5x",    label: "5x per week" },
  { value: "Daily", label: "Daily" },
]

// ── Sub-components ─────────────────────────────────────────────────────────────

function SectionHeader({ num, title, desc }: { num: string; title: string; desc?: string }) {
  return (
    <div className="pb-4 border-b border-[hsl(var(--border))]">
      <div className="flex items-center gap-2.5">
        <span className="text-[10px] font-mono gc-gold gc-gold-bg border gc-gold-border px-2 py-0.5 rounded">
          {num}
        </span>
        <p className="gc-label" style={{ fontSize: "11px" }}>{title}</p>
      </div>
      {desc && (
        <p className="text-xs gc-muted mt-2 leading-relaxed">{desc}</p>
      )}
    </div>
  )
}

function Field({ label, required, hint, children }: {
  label: string; required?: boolean; hint?: string; children: React.ReactNode
}) {
  return (
    <div className="space-y-1.5">
      <label className="gc-label" style={{ fontSize: "11px", display: "block" }}>
        {label}{required && <span className="text-[hsl(var(--gc-red))] ml-1">*</span>}
      </label>
      {children}
      {hint && (
        <p className="text-[10px] gc-muted italic leading-relaxed">{hint}</p>
      )}
    </div>
  )
}

const inputClass = cn(
  "w-full rounded-lg border border-[hsl(var(--border))]",
  "bg-[hsl(var(--gc-surface2))]",
  "text-sm text-[hsl(var(--foreground))] placeholder:text-[hsl(var(--gc-text-3))]",
  "px-3 py-2 focus:outline-none focus:border-[rgba(201,168,76,0.4)]",
  "transition-colors"
)

const selectClass = cn(
  "w-full rounded-lg border border-[hsl(var(--border))]",
  "bg-[hsl(var(--gc-surface2))]",
  "text-sm text-[hsl(var(--foreground))]",
  "px-3 py-2 focus:outline-none focus:border-[rgba(201,168,76,0.4)]",
  "transition-colors"
)

// ── Connection badge ──────────────────────────────────────────────────────────

function ConnectionBadge({ connected }: { connected: boolean }) {
  return connected ? (
    <span className="flex items-center gap-1 text-[10px] text-[hsl(var(--gc-green))] bg-[hsl(var(--gc-green)/0.08)] border border-[hsl(var(--gc-green)/0.25)] px-2 py-0.5 rounded-full">
      <Wifi size={9} /> Connected
    </span>
  ) : (
    <span className="flex items-center gap-1 text-[10px] gc-muted border border-[hsl(var(--border))] px-2 py-0.5 rounded-full">
      <WifiOff size={9} /> Not connected
    </span>
  )
}

// ── Competitor handle row ──────────────────────────────────────────────────────

function CompetitorRow({ value, placeholder, onChange, onRemove, canRemove }: {
  value: string; placeholder: string
  onChange: (v: string) => void; onRemove: () => void; canRemove: boolean
}) {
  return (
    <div className="flex gap-2">
      <div className="relative flex-1">
        <span className="absolute left-3 top-1/2 -translate-y-1/2 gc-muted text-sm select-none">@</span>
        <input
          className={cn(inputClass, "pl-7")}
          value={value}
          onChange={e => onChange(e.target.value.replace(/^@/, ""))}
          placeholder={placeholder}
        />
      </div>
      {canRemove && (
        <button
          type="button"
          onClick={onRemove}
          className="flex items-center justify-center w-9 h-9 rounded-lg border border-[hsl(var(--border))] gc-muted hover:text-[hsl(var(--gc-red))] hover:border-[hsl(var(--gc-red)/0.4)] transition-colors"
        >
          <X size={13} />
        </button>
      )}
    </div>
  )
}

// ── Main Component ─────────────────────────────────────────────────────────────

const DEFAULT_FORM: CreateBrandPayload = {
  brand_name: "",
  brand_slug: "",
  industry: "",
  phase: "Beta",
  product_description: "",
  website_url: "",
  price_india: "",
  price_international: "",
  target_audience: "",
  platforms: ["Instagram"],
  platform_handles: [{ platform: "Instagram", handle: "" }],
  primary_bottleneck: "Awareness",
  instagram_handle: "",
  competitor_handles: ["", ""],
  brand_face: "Person",
  tone_of_voice: "Professional",
  tone_specifics: "",
  content_goal_90d: "Followers",
  weekly_post_target: "3x",
  past_content_worked: "",
  what_to_never_say: "",
  has_existing_pipeline: false,
  existing_pipeline: "",
  railway_url: "",
}

export function BrandOnboarding() {
  const { setActiveBrand, setBrands, brands, navigate } = useBrandStore()
  const queryClient = useQueryClient()

  const [form, setForm] = useState<CreateBrandPayload>(DEFAULT_FORM)
  const [slugEdited, setSlugEdited] = useState(false)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  // Auto-generate slug
  useEffect(() => {
    if (!slugEdited) {
      setForm(prev => ({ ...prev, brand_slug: slugify(prev.brand_name) }))
    }
  }, [form.brand_name, slugEdited])

  const { data: connStatus, refetch: refetchConn, isFetching: connFetching } = useQuery({
    queryKey: ["connections"],
    queryFn: fetchConnectionStatus,
    refetchInterval: false,
    staleTime: 60000,
  })

  const createMutation = useMutation({
    mutationFn: createBrand,
    onSuccess: (brand) => {
      queryClient.invalidateQueries({ queryKey: ["brands"] })
      setActiveBrand(brand)
      setBrands([...brands, brand])
      navigate(5)
    },
    onError: (err: Error) => setErrorMsg(err.message),
  })

  // When platforms change, sync platform_handles array
  const handlePlatformToggle = (p: string) => {
    setForm(prev => {
      const isSelected = prev.platforms.includes(p)
      const newPlatforms = isSelected
        ? prev.platforms.filter(x => x !== p)
        : [...prev.platforms, p]
      const newHandles = newPlatforms.map(plat => ({
        platform: plat,
        handle: prev.platform_handles.find(h => h.platform === plat)?.handle ?? "",
      }))
      // Keep instagram_handle in sync
      const igHandle = newHandles.find(h => h.platform === "Instagram")?.handle ?? prev.instagram_handle
      return { ...prev, platforms: newPlatforms, platform_handles: newHandles, instagram_handle: igHandle }
    })
  }

  const updateHandle = (platform: string, value: string) => {
    setForm(prev => {
      const newHandles = prev.platform_handles.map(h =>
        h.platform === platform ? { ...h, handle: value } : h
      )
      const igHandle = platform === "Instagram" ? value : prev.instagram_handle
      return { ...prev, platform_handles: newHandles, instagram_handle: igHandle }
    })
  }

  const updateCompetitorHandle = (i: number, value: string) => {
    setForm(prev => {
      const updated = [...prev.competitor_handles]
      updated[i] = value
      return { ...prev, competitor_handles: updated }
    })
  }

  const handleSubmit = () => {
    setErrorMsg(null)
    if (!form.brand_name.trim()) { setErrorMsg("Brand name is required"); return }
    if (!form.product_description.trim()) { setErrorMsg("Product description is required — agents need to understand what you sell"); return }
    if (!form.target_audience.trim()) { setErrorMsg("Target audience is required — agents need to know who they're talking to"); return }
    createMutation.mutate({ ...form, brand_slug: form.brand_slug || slugify(form.brand_name) })
  }

  const platformConnectionStatus: Record<string, boolean> = {
    Instagram: connStatus?.instagram ?? false,
    LinkedIn:  connStatus?.linkedin ?? false,
    YouTube:   connStatus?.youtube ?? false,
    Twitter:   false,
    WhatsApp:  false,
  }

  return (
    <div className="h-full flex flex-col bg-[hsl(var(--background))]">

      {/* Topbar */}
      <div className="h-[52px] shrink-0 flex items-center justify-between px-6 border-b border-[hsl(var(--border))]">
        <div className="flex items-center gap-2 text-sm">
          <span className="gc-muted">GRID CONTROL</span>
          <span className="gc-dimmed">/</span>
          <span className="text-[hsl(var(--foreground))] font-medium">Add Brand</span>
        </div>
        <button
          onClick={handleSubmit}
          disabled={createMutation.isPending}
          className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-sm font-bold bg-[hsl(var(--gc-gold))] text-black disabled:opacity-50 transition-opacity"
        >
          {createMutation.isPending
            ? <><Loader2 size={13} className="animate-spin" /> Creating...</>
            : <><CheckCircle size={13} /> Create Brand</>
          }
        </button>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto">
        <div className="p-6 space-y-5 max-w-3xl">

          {/* Page heading */}
          <div>
            <h1 className="text-base font-bold text-[hsl(var(--foreground))]">Add a Brand</h1>
            <p className="text-xs gc-muted mt-1">
              Answer these as if briefing a new team member on day one. Agents read this before doing any work.
            </p>
          </div>

          {/* Error */}
          {errorMsg && (
            <div className="flex items-center gap-2 text-[hsl(var(--gc-red))] bg-[hsl(var(--gc-red)/0.08)] border border-[hsl(var(--gc-red)/0.3)] rounded-lg px-4 py-3 text-sm">
              <AlertCircle size={14} className="shrink-0" />
              {errorMsg}
            </div>
          )}

          {/* ── 01 IDENTITY ───────────────────────────────────────────────── */}
          <section className="gc-card p-5 space-y-5">
            <SectionHeader num="01" title="Identity" desc="Basic facts about the brand." />

            <Field label="Brand Name" required>
              <input
                className={inputClass}
                value={form.brand_name}
                onChange={e => setForm(prev => ({ ...prev, brand_name: e.target.value }))}
                placeholder="e.g. Zara India, Bombay Shaving, Fresh Threads..."
              />
            </Field>

            <Field label="Brand Slug" hint="Auto-generated from name. Used as folder ID — cannot change after creation.">
              <input
                className={inputClass}
                value={form.brand_slug}
                onChange={e => { setSlugEdited(true); setForm(prev => ({ ...prev, brand_slug: slugify(e.target.value) })) }}
                placeholder="e.g. zara-india, fresh-threads"
              />
            </Field>

            <div className="grid grid-cols-2 gap-4">
              <Field label="Industry" required>
                <input
                  className={inputClass}
                  value={form.industry}
                  onChange={e => setForm(prev => ({ ...prev, industry: e.target.value }))}
                  placeholder="e.g. D2C Fashion, AI SaaS, EdTech, Food..."
                />
              </Field>
              <Field label="Phase">
                <select className={selectClass} value={form.phase} onChange={e => setForm(prev => ({ ...prev, phase: e.target.value }))}>
                  <option value="Beta">Beta</option>
                  <option value="Launch">Launch</option>
                  <option value="Growth">Growth</option>
                  <option value="Scale">Scale</option>
                </select>
              </Field>
            </div>

            <Field label="What does this brand sell? What problem does it solve?" required>
              <textarea
                className={cn(inputClass, "min-h-[90px] resize-y")}
                value={form.product_description}
                onChange={e => setForm(prev => ({ ...prev, product_description: e.target.value }))}
                placeholder="Describe the product, the customer's problem it solves, and why someone would buy it over alternatives..."
              />
            </Field>

            <Field label="Website URL">
              <input
                className={inputClass}
                value={form.website_url}
                onChange={e => setForm(prev => ({ ...prev, website_url: e.target.value }))}
                placeholder="https://yourbrand.com"
              />
            </Field>

            <div className="grid grid-cols-2 gap-4">
              <Field label="Price — India">
                <input
                  className={inputClass}
                  value={form.price_india}
                  onChange={e => setForm(prev => ({ ...prev, price_india: e.target.value }))}
                  placeholder="₹999 / ₹3,500 / ₹15,000..."
                />
              </Field>
              <Field label="Price — International">
                <input
                  className={inputClass}
                  value={form.price_international}
                  onChange={e => setForm(prev => ({ ...prev, price_international: e.target.value }))}
                  placeholder="$29 / $99 / $499..."
                />
              </Field>
            </div>
          </section>

          {/* ── 02 AUDIENCE ───────────────────────────────────────────────── */}
          <section className="gc-card p-5 space-y-5">
            <SectionHeader
              num="02"
              title="Audience"
              desc="Who exactly is this brand talking to. Be specific — agents write for real people, not demographics."
            />

            <Field label="Describe your target audience in detail" required>
              <textarea
                className={cn(inputClass, "min-h-[90px] resize-y")}
                value={form.target_audience}
                onChange={e => setForm(prev => ({ ...prev, target_audience: e.target.value }))}
                placeholder="Age, income, job, what they care about, their current frustration, what they're already doing instead of buying from you..."
              />
            </Field>

            <Field label="Primary Bottleneck Right Now">
              <select className={selectClass} value={form.primary_bottleneck} onChange={e => setForm(prev => ({ ...prev, primary_bottleneck: e.target.value }))}>
                {BOTTLENECK_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </Field>
          </section>

          {/* ── 03 PLATFORMS ──────────────────────────────────────────────── */}
          <section className="gc-card p-5 space-y-5">
            <SectionHeader
              num="03"
              title="Active Platforms"
              desc="Select all platforms this brand is active on. You'll enter the handle for each one below."
            />

            {/* Platform toggles */}
            <div className="flex flex-wrap gap-2">
              {ALL_PLATFORMS.map(p => (
                <button
                  key={p}
                  type="button"
                  onClick={() => handlePlatformToggle(p)}
                  className={cn(
                    "px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors",
                    form.platforms.includes(p)
                      ? "gc-gold-bg gc-gold-border gc-gold"
                      : "bg-[hsl(var(--gc-surface2))] border-[hsl(var(--border))] gc-muted hover:text-[hsl(var(--foreground))]"
                  )}
                >
                  {p}
                </button>
              ))}
            </div>

            {/* Dynamic handle fields for each selected platform */}
            {form.platforms.length > 0 && (
              <div className="space-y-4 pt-2 border-t border-[hsl(var(--border))]">
                <p className="gc-label" style={{ fontSize: "10px" }}>
                  Enter the handle / username for each selected platform
                </p>
                {form.platform_handles.map(({ platform, handle }) => {
                  const cfg = PLATFORM_CONFIG[platform]
                  if (!cfg) return null
                  return (
                    <Field key={platform} label={cfg.handleLabel}>
                      <div className="relative">
                        {cfg.prefix && (
                          <span className="absolute left-3 top-1/2 -translate-y-1/2 gc-muted text-xs select-none whitespace-nowrap">
                            {cfg.prefix}
                          </span>
                        )}
                        <input
                          className={cn(inputClass, cfg.prefix ? (cfg.prefix.length > 2 ? "pl-36" : "pl-7") : "")}
                          value={handle}
                          onChange={e => updateHandle(platform, e.target.value.replace(/^@/, ""))}
                          placeholder={cfg.placeholder}
                        />
                      </div>
                    </Field>
                  )
                })}
              </div>
            )}

            {/* Competitor handles */}
            <div className="pt-2 border-t border-[hsl(var(--border))] space-y-3">
              <Field
                label="Competitor Instagram Handles"
                hint="Strategy Agent pulls their public post data to understand what's working in your category."
              >
                <div className="space-y-2">
                  {form.competitor_handles.map((handle, i) => (
                    <CompetitorRow
                      key={i}
                      value={handle}
                      placeholder={`Competitor ${i + 1} Instagram handle`}
                      onChange={v => updateCompetitorHandle(i, v)}
                      onRemove={() => setForm(prev => ({ ...prev, competitor_handles: prev.competitor_handles.filter((_, idx) => idx !== i) }))}
                      canRemove={form.competitor_handles.length > 1}
                    />
                  ))}
                  {form.competitor_handles.length < 5 && (
                    <button
                      type="button"
                      onClick={() => setForm(prev => ({ ...prev, competitor_handles: [...prev.competitor_handles, ""] }))}
                      className="flex items-center gap-1.5 text-xs gc-muted hover:gc-gold transition-colors"
                    >
                      <Plus size={12} /> Add another competitor
                    </button>
                  )}
                </div>
              </Field>
            </div>
          </section>

          {/* ── 04 CONNECT ACCOUNTS ───────────────────────────────────────── */}
          <section className="gc-card p-5 space-y-5">
            <div className="flex items-start justify-between">
              <SectionHeader
                num="04"
                title="Connect Your Accounts"
                desc="Agents pull real data — post performance, engagement rates, audience insights — only from connected accounts. Disconnected = agents work on scraped public data only, which is less accurate."
              />
              <button
                onClick={() => refetchConn()}
                disabled={connFetching}
                className="flex items-center gap-1.5 text-[10px] gc-muted hover:text-[hsl(var(--foreground))] transition-colors shrink-0 mt-1"
              >
                <RefreshCw size={10} className={cn(connFetching && "animate-spin")} />
                Recheck
              </button>
            </div>

            <div className="space-y-3">
              {form.platforms.filter(p => ["Instagram", "LinkedIn", "YouTube"].includes(p)).map(platform => {
                const cfg = PLATFORM_CONFIG[platform]
                const isConnected = platformConnectionStatus[platform]
                return (
                  <div
                    key={platform}
                    className={cn(
                      "rounded-lg border p-4 space-y-2",
                      isConnected
                        ? "bg-[hsl(var(--gc-green)/0.06)] border-[hsl(var(--gc-green)/0.25)]"
                        : "bg-[hsl(var(--gc-surface2))] border-[hsl(var(--border))]"
                    )}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-medium text-[hsl(var(--foreground))]">{cfg.label}</p>
                        <ConnectionBadge connected={isConnected} />
                      </div>
                      {!isConnected && (
                        <div className="flex items-center gap-1.5">
                          <Lock size={11} className="gc-muted" />
                          <span className="text-[10px] gc-muted">Requires API setup</span>
                        </div>
                      )}
                    </div>
                    <p className="text-[11px] gc-muted leading-relaxed">
                      {cfg.oauthNote}
                    </p>
                    {!isConnected && (
                      <div className="pt-1">
                        {platform === "Instagram" && (
                          <a
                            href="https://developers.facebook.com/apps/"
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1.5 text-[11px] gc-gold hover:underline"
                          >
                            <ExternalLink size={10} />
                            Set up Meta Graph API token → add to .env as META_GRAPH_API_TOKEN
                          </a>
                        )}
                        {platform === "LinkedIn" && (
                          <a
                            href="https://www.linkedin.com/developers/apps"
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1.5 text-[11px] gc-gold hover:underline"
                          >
                            <ExternalLink size={10} />
                            Set up LinkedIn app → add LINKEDIN_ACCESS_TOKEN to .env
                          </a>
                        )}
                        {platform === "YouTube" && (
                          <a
                            href="https://console.cloud.google.com/apis/library/youtube.googleapis.com"
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1.5 text-[11px] gc-gold hover:underline"
                          >
                            <ExternalLink size={10} />
                            Enable YouTube Data API v3 → add YOUTUBE_API_KEY to .env
                          </a>
                        )}
                      </div>
                    )}
                  </div>
                )
              })}

              {form.platforms.filter(p => ["Instagram", "LinkedIn", "YouTube"].includes(p)).length === 0 && (
                <p className="text-xs gc-muted italic">
                  Select Instagram, LinkedIn, or YouTube above to see connection options.
                </p>
              )}
            </div>

            <div className="rounded-lg gc-gold-bg border gc-gold-border px-4 py-3">
              <p className="text-xs gc-gold leading-relaxed">
                <span className="font-semibold">Note:</span> You can create the brand without connecting accounts.
                Agents will use Apify to scrape public data. For private analytics (your own engagement rates, audience demographics, ad performance)
                you must connect. Do this before running Data Analyst or Ad Strategist.
              </p>
            </div>
          </section>

          {/* ── 05 CONTENT & VOICE ────────────────────────────────────────── */}
          <section className="gc-card p-5 space-y-5">
            <SectionHeader
              num="05"
              title="Content & Voice"
              desc="How the brand communicates. Script Writer and Creative Director read this before writing a single word."
            />

            <Field label="Who is the face of the brand?">
              <select className={selectClass} value={form.brand_face} onChange={e => setForm(prev => ({ ...prev, brand_face: e.target.value }))}>
                {BRAND_FACE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </Field>

            <div className="grid grid-cols-2 gap-4">
              <Field label="Tone of Voice">
                <select className={selectClass} value={form.tone_of_voice} onChange={e => setForm(prev => ({ ...prev, tone_of_voice: e.target.value }))}>
                  <option value="Professional">Professional — authoritative, precise</option>
                  <option value="Casual">Casual — friendly, conversational</option>
                  <option value="Bold">Bold — direct, punchy, high-energy</option>
                  <option value="Educational">Educational — clear, trust-building</option>
                  <option value="Inspirational">Inspirational — motivating, visionary</option>
                </select>
              </Field>
              <Field label="Weekly Posting Target">
                <select className={selectClass} value={form.weekly_post_target} onChange={e => setForm(prev => ({ ...prev, weekly_post_target: e.target.value }))}>
                  {POST_FREQ_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              </Field>
            </div>

            <Field
              label="Tone specifics — how do you sound exactly?"
              hint="Short sentences? First person? Emoji yes or no? Formal or casual? Give examples if you have them."
            >
              <textarea
                className={cn(inputClass, "min-h-[80px] resize-y")}
                value={form.tone_specifics}
                onChange={e => setForm(prev => ({ ...prev, tone_specifics: e.target.value }))}
                placeholder="Direct, no fluff. Talk like explaining to a smart friend. Short sentences. Use 'I' and 'you'. Specific numbers over vague adjectives..."
              />
            </Field>

            <Field
              label="What must agents NEVER say or do?"
              hint="Hard rules. Agents treat these as absolute constraints."
            >
              <textarea
                className={cn(inputClass, "min-h-[80px] resize-y")}
                value={form.what_to_never_say}
                onChange={e => setForm(prev => ({ ...prev, what_to_never_say: e.target.value }))}
                placeholder="Never use: leverage, synergy, game-changer, disruption. Never start with 'In today's digital age'. Never attack competitors by name. Never sound like a press release..."
              />
            </Field>

            <Field label="Past content that worked (links or describe it)">
              <textarea
                className={cn(inputClass, "min-h-[70px] resize-y")}
                value={form.past_content_worked}
                onChange={e => setForm(prev => ({ ...prev, past_content_worked: e.target.value }))}
                placeholder="Any post, reel, or email that got good traction. What format was it? What did the hook say? Why do you think it worked?"
              />
            </Field>
          </section>

          {/* ── 06 90-DAY GOAL ────────────────────────────────────────────── */}
          <section className="gc-card p-5 space-y-5">
            <SectionHeader
              num="06"
              title="90-Day Goal"
              desc="What does success look like 3 months from now? Strategy Agent builds every roadmap around this."
            />
            <Field label="Primary goal for the next 90 days">
              <select className={selectClass} value={form.content_goal_90d} onChange={e => setForm(prev => ({ ...prev, content_goal_90d: e.target.value }))}>
                {GOAL_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </Field>
          </section>

          {/* ── 07 EXISTING TECH ──────────────────────────────────────────── */}
          <section className="gc-card p-5 space-y-5">
            <SectionHeader
              num="07"
              title="Existing Tech Stack"
              desc="Do you already have a tech pipeline running for this brand?"
            />

            <Field label="Do you have an existing tech stack or automation pipeline?">
              <div className="flex gap-3">
                {[
                  { val: true,  label: "Yes — I'll describe it" },
                  { val: false, label: "No — we'll build from scratch" },
                ].map(opt => (
                  <button
                    key={String(opt.val)}
                    type="button"
                    onClick={() => setForm(prev => ({ ...prev, has_existing_pipeline: opt.val }))}
                    className={cn(
                      "flex-1 py-2.5 rounded-lg text-sm font-medium border transition-colors",
                      form.has_existing_pipeline === opt.val
                        ? "gc-gold-bg gc-gold-border gc-gold"
                        : "bg-[hsl(var(--gc-surface2))] border-[hsl(var(--border))] gc-muted hover:text-[hsl(var(--foreground))]"
                    )}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </Field>

            {form.has_existing_pipeline && (
              <div className="space-y-4 pt-2">
                <Field label="Describe your pipeline / tools in use">
                  <textarea
                    className={cn(inputClass, "min-h-[70px] resize-y")}
                    value={form.existing_pipeline}
                    onChange={e => setForm(prev => ({ ...prev, existing_pipeline: e.target.value }))}
                    placeholder="e.g. Google Forms → Make.com → Apify → Claude API → Railway → Gmail. Or: Zapier, Notion, Buffer, etc."
                  />
                </Field>
                <Field label="Deployed URL (Railway / Vercel / custom domain)">
                  <input
                    className={inputClass}
                    value={form.railway_url}
                    onChange={e => setForm(prev => ({ ...prev, railway_url: e.target.value }))}
                    placeholder="https://your-app.up.railway.app"
                  />
                </Field>
              </div>
            )}
          </section>

          {/* Bottom submit */}
          <div className="flex justify-end pb-8">
            <button
              onClick={handleSubmit}
              disabled={createMutation.isPending}
              className="flex items-center gap-2 px-8 py-2.5 rounded-lg text-sm font-bold bg-[hsl(var(--gc-gold))] text-black disabled:opacity-50 transition-opacity"
            >
              {createMutation.isPending
                ? <><Loader2 size={14} className="animate-spin" /> Creating Brand...</>
                : <><CheckCircle size={14} /> Create Brand — Agents Ready</>
              }
            </button>
          </div>

        </div>
      </div>
    </div>
  )
}
