/**
 * BrandSpace — Space 4
 * Brand profile: view all brand data, edit key fields, onboard new brands.
 * Notion/Linear aesthetic: large text, generous padding, clean sections.
 */

import { useState, useEffect } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import {
  Target, Users, AlertTriangle,
  CheckCircle2, XCircle, Edit3, Save, X, Plus, Loader2,
  AtSign, Globe, Clock, Mic, Trash2,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { apiFetch } from "@/lib/api"
import { useBrandStore } from "@/store/brandStore"
import type { BrandSummary, ApiResponse } from "@/types"

// ── Types ──────────────────────────────────────────────────────────────────────

interface BrandProfilePayload {
  brand_name:        string
  product:           string
  price_india:       string
  price_international: string
  audience:          string[]
  platforms:         string[]
  bottlenecks:       string[]
  phase:             string
  railway_url:       string
  instagram_handle:  string
  competitor_handles: string[]
  brand_face:        string
  tone_specifics:    string
  content_goal_90d:  string
  weekly_post_target: string
  what_to_never_say: string
}

// ── API helpers ────────────────────────────────────────────────────────────────

async function fetchSummary(slug: string): Promise<BrandSummary> {
  const res  = await apiFetch(`/api/brand/summary?brand_slug=${slug}`)
  const json: ApiResponse<BrandSummary> = await res.json()
  if (!json.success) throw new Error(json.error)
  return json.data
}

async function fetchProfile(slug: string): Promise<BrandProfilePayload> {
  const res  = await apiFetch(`/api/brand/profile?brand_slug=${slug}`)
  const json: ApiResponse<BrandProfilePayload> = await res.json()
  if (!json.success) throw new Error(json.error)
  return json.data
}

async function saveProfile(slug: string, payload: BrandProfilePayload): Promise<void> {
  const res  = await apiFetch(`/api/brand/profile?brand_slug=${slug}`, {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify(payload),
  })
  const json: ApiResponse<unknown> = await res.json()
  if (!json.success) throw new Error(json.error)
}

async function fetchVoiceProfile(slug: string): Promise<{ exists: boolean; [key: string]: unknown }> {
  const res  = await apiFetch(`/api/voice/profile?brand_slug=${slug}`)
  const json: ApiResponse<{ exists: boolean; [key: string]: unknown }> = await res.json()
  if (!json.success) throw new Error(json.error)
  return json.data
}

async function extractVoiceProfile(slug: string, rawScripts: string): Promise<unknown> {
  const res  = await apiFetch("/api/voice/extract-profile", {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify({ brand_slug: slug, raw_scripts: rawScripts }),
  })
  const json: ApiResponse<unknown> = await res.json()
  if (!json.success) throw new Error(json.error ?? "Extraction failed")
  return json.data
}

// ── Helpers ────────────────────────────────────────────────────────────────────

function slugify(name: string): string {
  return name.toLowerCase().replace(/\s+/g, "-").replace(/[^a-z0-9-]/g, "").replace(/-+/g, "-")
}

async function createBrand(payload: Record<string, unknown>): Promise<{ slug: string; name: string }> {
  const res  = await apiFetch("/api/brands/create", {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify(payload),
  })
  const json: ApiResponse<{ slug: string; brand_slug: string; name: string }> = await res.json()
  if (!json.success) throw new Error(json.error ?? "Failed to create brand")
  return { slug: json.data.brand_slug ?? json.data.slug, name: String(payload.brand_name ?? "") }
}

// ── Section label ──────────────────────────────────────────────────────────────

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[hsl(var(--gc-text-2))] uppercase tracking-widest font-medium mb-4" style={{ fontSize: 12 }}>
      {children}
    </p>
  )
}

// ── Tag list editor ────────────────────────────────────────────────────────────

function TagListEditor({
  values, onChange, placeholder,
}: { values: string[]; onChange: (v: string[]) => void; placeholder: string }) {
  const [input, setInput] = useState("")

  const add = () => {
    const v = input.trim()
    if (v && !values.includes(v)) { onChange([...values, v]); setInput("") }
  }

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-2">
        {values.map((v, i) => (
          <span key={i} className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg border"
            style={{ fontSize: 13, background: "hsl(var(--gc-surface2))", color: "hsl(var(--foreground))", borderColor: "hsl(var(--border))" }}>
            {v}
            <button onClick={() => onChange(values.filter((_, j) => j !== i))}
              className="text-[hsl(var(--gc-text-3))] hover:text-[hsl(var(--gc-red))] transition-colors">
              <X size={11} />
            </button>
          </span>
        ))}
      </div>
      <div className="flex gap-2">
        <input
          value={input} onChange={e => setInput(e.target.value)}
          onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); add() } }}
          placeholder={placeholder}
          className="flex-1 rounded-lg px-3 py-2 focus:outline-none text-white placeholder:text-[hsl(var(--gc-text-3))]"
          style={{ background: "hsl(var(--gc-surface2))", border: "1px solid hsl(var(--border))", fontSize: 13 }}
        />
        <button onClick={add}
          className="h-9 w-9 rounded-lg flex items-center justify-center hover:opacity-75 transition-opacity"
          style={{ background: "rgba(201,168,76,0.15)", color: "hsl(var(--gc-gold))" }}>
          <Plus size={14} />
        </button>
      </div>
    </div>
  )
}

// ── Field input ────────────────────────────────────────────────────────────────

function Field({ label, value, onChange, placeholder, textarea }: {
  label: string; value: string; onChange: (v: string) => void
  placeholder?: string; textarea?: boolean
}) {
  return (
    <div>
      <label className="block text-[hsl(var(--gc-text-2))] font-medium mb-1.5" style={{ fontSize: 13 }}>{label}</label>
      {textarea ? (
        <textarea
          value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder}
          className="w-full rounded-lg px-3 py-2.5 focus:outline-none text-white placeholder:text-[hsl(var(--gc-text-3))] resize-none"
          style={{ background: "hsl(var(--gc-surface2))", border: "1px solid hsl(var(--border))", fontSize: 14, minHeight: 80, lineHeight: 1.6 }}
        />
      ) : (
        <input
          value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder}
          className="w-full rounded-lg px-3 py-2.5 focus:outline-none text-white placeholder:text-[hsl(var(--gc-text-3))]"
          style={{ background: "hsl(var(--gc-surface2))", border: "1px solid hsl(var(--border))", fontSize: 14 }}
        />
      )}
    </div>
  )
}

// ── Profile View ───────────────────────────────────────────────────────────────

function ProfileView({ data, onEdit }: { data: BrandSummary; onEdit: () => void }) {
  const [productExpanded, setProductExpanded] = useState(false)

  return (
    <div className="space-y-8">
      {/* Hero */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-white font-bold" style={{ fontSize: 28, letterSpacing: -0.5 }}>{data.brand_name}</h1>
          {data.phase && (
            <span className="inline-flex items-center mt-2 px-3 py-1 rounded border font-bold"
              style={{ fontSize: 11, letterSpacing: 1, textTransform: "uppercase",
                color: "hsl(var(--gc-gold))", background: "rgba(201,168,76,0.1)", borderColor: "rgba(201,168,76,0.25)" }}>
              {data.phase}
            </span>
          )}
        </div>
        <button onClick={onEdit}
          className="flex items-center gap-2 h-9 px-4 rounded-lg transition-colors hover:text-white"
          style={{ fontSize: 13, fontWeight: 600, color: "hsl(var(--gc-text-2))", border: "1px solid hsl(var(--border))", background: "transparent" }}>
          <Edit3 size={14} /> Edit Profile
        </button>
      </div>

      {/* Metrics bar */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "Posts Scripted",  value: data.posts_scripted,  color: "text-white" },
          { label: "Agents Run",      value: data.agents_run,      color: "text-white" },
          { label: "Approved",        value: data.notion_approved, color: "text-[hsl(var(--gc-green))]" },
        ].map(({ label, value, color }) => (
          <div key={label} className="gc-card rounded-xl p-5">
            <p className={cn("font-bold", color)} style={{ fontSize: 26, lineHeight: 1 }}>{value}</p>
            <p className="text-[hsl(var(--gc-text-2))] mt-1.5" style={{ fontSize: 13 }}>{label}</p>
          </div>
        ))}
      </div>

      {/* Product */}
      <div className="gc-card rounded-xl p-6 space-y-5">
        <SectionTitle>Product</SectionTitle>
        <p className={cn("text-white leading-relaxed", !productExpanded && "line-clamp-4")}
          style={{ fontSize: 15, lineHeight: 1.7 }}>
          {data.product || "Not set"}
        </p>
        {data.product && data.product.length > 220 && (
          <button onClick={() => setProductExpanded(!productExpanded)}
            className="text-[hsl(var(--gc-gold))] hover:opacity-75 transition-opacity"
            style={{ fontSize: 13 }}>
            {productExpanded ? "Show less ↑" : "Show more ↓"}
          </button>
        )}
      </div>

      {/* Audience · Platforms · Pricing */}
      <div className="gc-card rounded-xl p-6">
        <div className="grid grid-cols-3 gap-6">
          <div>
            <div className="flex items-center gap-2 mb-3">
              <Users size={13} className="text-[hsl(var(--gc-text-3))]" />
              <SectionTitle>Audience</SectionTitle>
            </div>
            <p className="text-white" style={{ fontSize: 14, lineHeight: 1.6 }}>
              {data.audience.length > 0 ? data.audience.join(", ") : "—"}
            </p>
          </div>
          <div>
            <SectionTitle>Platforms</SectionTitle>
            <p className="text-white" style={{ fontSize: 14, lineHeight: 1.6 }}>
              {data.platforms.length > 0 ? data.platforms.join(", ") : "—"}
            </p>
          </div>
          <div>
            <div className="flex items-center gap-2 mb-3">
              <Target size={13} className="text-[hsl(var(--gc-text-3))]" />
              <SectionTitle>Pricing</SectionTitle>
            </div>
            <p className="text-white" style={{ fontSize: 14 }}>
              {[data.price_india && `₹${data.price_india}`, data.price_international && `$${data.price_international}`]
                .filter(Boolean).join(" · ") || "—"}
            </p>
          </div>
        </div>
      </div>

      {/* Social presence */}
      {(data.instagram_handle || (data.competitor_handles ?? []).length > 0) && (
        <div className="gc-card rounded-xl p-6 space-y-4">
          <div className="flex items-center gap-2 mb-1">
            <AtSign size={13} className="text-[hsl(var(--gc-text-3))]" />
            <SectionTitle>Brand Presence</SectionTitle>
          </div>
          {data.instagram_handle && (
            <div className="flex items-center gap-4">
              <span className="text-[hsl(var(--gc-text-2))] font-medium w-28" style={{ fontSize: 13 }}>Instagram</span>
              <a href={`https://instagram.com/${data.instagram_handle}`} target="_blank" rel="noopener noreferrer"
                className="text-[hsl(var(--gc-gold))] hover:underline font-mono" style={{ fontSize: 14 }}>
                @{data.instagram_handle}
              </a>
            </div>
          )}
          {(data.competitor_handles ?? []).filter(Boolean).length > 0 && (
            <div className="flex items-start gap-4">
              <span className="text-[hsl(var(--gc-text-2))] font-medium w-28 pt-0.5" style={{ fontSize: 13 }}>Competitors</span>
              <div className="flex gap-2 flex-wrap">
                {(data.competitor_handles ?? []).filter(Boolean).map((h, i) => (
                  <a key={i} href={`https://instagram.com/${h}`} target="_blank" rel="noopener noreferrer"
                    className="text-[hsl(var(--gc-text-2))] hover:text-white hover:underline font-mono transition-colors" style={{ fontSize: 13 }}>
                    @{h}
                  </a>
                ))}
              </div>
            </div>
          )}
          {data.content_goal_90d && (
            <div className="flex items-center gap-4">
              <span className="text-[hsl(var(--gc-text-2))] font-medium w-28" style={{ fontSize: 13 }}>90-day Goal</span>
              <span className="text-white" style={{ fontSize: 14 }}>{data.content_goal_90d}</span>
            </div>
          )}
          {data.railway_url && (
            <div className="flex items-center gap-4">
              <Globe size={13} className="text-[hsl(var(--gc-text-3))] w-28 shrink-0" />
              <a href={data.railway_url} target="_blank" rel="noopener noreferrer"
                className="text-[hsl(var(--gc-gold))] hover:underline font-mono" style={{ fontSize: 13 }}>
                {data.railway_url}
              </a>
            </div>
          )}
        </div>
      )}

      {/* Bottlenecks */}
      {data.bottlenecks.length > 0 && (
        <div className="gc-card rounded-xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <AlertTriangle size={14} className="text-[hsl(var(--gc-red))]" />
            <SectionTitle>Active Bottlenecks</SectionTitle>
          </div>
          <div className="flex gap-2 flex-wrap">
            {data.bottlenecks.map(b => (
              <span key={b} className="px-3 py-1 rounded-lg border" style={{ fontSize: 13,
                color: "hsl(var(--gc-red))", background: "rgba(231,76,60,0.08)", borderColor: "rgba(231,76,60,0.2)" }}>
                {b}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Completed agents */}
      {data.completed_agents.length > 0 && (
        <div className="gc-card rounded-xl p-6">
          <SectionTitle>Completed Agents</SectionTitle>
          <div className="flex flex-wrap gap-2">
            {data.completed_agents.map(a => (
              <span key={a} className="flex items-center gap-1.5 px-3 py-1 rounded-lg border" style={{ fontSize: 13,
                color: "hsl(var(--gc-green))", background: "rgba(46,204,113,0.07)", borderColor: "rgba(46,204,113,0.2)" }}>
                <CheckCircle2 size={12} /> {a}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ── Profile Edit ───────────────────────────────────────────────────────────────

function ProfileEdit({ initial, slug, onDone }: { initial: BrandProfilePayload; slug: string; onDone: () => void }) {
  const queryClient = useQueryClient()
  const [form, setForm] = useState<BrandProfilePayload>({ ...initial })

  const set = <K extends keyof BrandProfilePayload>(key: K) => (value: BrandProfilePayload[K]) =>
    setForm(prev => ({ ...prev, [key]: value }))

  const mutation = useMutation({
    mutationFn: () => saveProfile(slug, form),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["brand-summary", slug] })
      queryClient.invalidateQueries({ queryKey: ["brand-profile", slug] })
      onDone()
    },
  })

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between gap-4">
        <h1 className="text-white font-bold" style={{ fontSize: 26 }}>Edit Brand Profile</h1>
        <div className="flex items-center gap-2">
          <button onClick={onDone}
            className="flex items-center gap-2 h-9 px-4 rounded-lg transition-colors hover:text-white"
            style={{ fontSize: 13, color: "hsl(var(--gc-text-2))", border: "1px solid hsl(var(--border))", background: "transparent" }}>
            <X size={14} /> Cancel
          </button>
          <button onClick={() => mutation.mutate()}
            disabled={mutation.isPending}
            className="flex items-center gap-2 h-9 px-5 rounded-lg font-semibold hover:opacity-85 transition-opacity disabled:opacity-50"
            style={{ fontSize: 13, background: "hsl(var(--gc-gold))", color: "#000" }}>
            {mutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
            Save Changes
          </button>
        </div>
      </div>

      {mutation.isError && (
        <div className="flex items-center gap-2 px-4 py-3 rounded-lg border"
          style={{ background: "rgba(231,76,60,0.08)", borderColor: "rgba(231,76,60,0.2)", color: "hsl(var(--gc-red))", fontSize: 13 }}>
          <XCircle size={14} /> {(mutation.error as Error).message}
        </div>
      )}

      <div className="gc-card rounded-xl p-6 space-y-5">
        <SectionTitle>Core</SectionTitle>
        <Field label="Brand Name"   value={form.brand_name}   onChange={set("brand_name")}   placeholder="e.g. DropVolt" />
        <Field label="Phase"        value={form.phase ?? ""}  onChange={set("phase")}        placeholder="e.g. Phase 1 — Awareness" />
        <Field label="Product"      value={form.product}      onChange={set("product")}      placeholder="Describe your product…" textarea />
      </div>

      <div className="gc-card rounded-xl p-6 space-y-5">
        <SectionTitle>Pricing</SectionTitle>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Price India (₹)"         value={form.price_india}        onChange={set("price_india")}         placeholder="999" />
          <Field label="Price International ($)" value={form.price_international} onChange={set("price_international")} placeholder="29" />
        </div>
      </div>

      <div className="gc-card rounded-xl p-6 space-y-5">
        <SectionTitle>Target Audience</SectionTitle>
        <TagListEditor values={form.audience}  onChange={set("audience")}  placeholder="Add audience segment…" />
      </div>

      <div className="gc-card rounded-xl p-6 space-y-5">
        <SectionTitle>Platforms</SectionTitle>
        <TagListEditor values={form.platforms} onChange={set("platforms")} placeholder="Add platform…" />
      </div>

      <div className="gc-card rounded-xl p-6 space-y-5">
        <SectionTitle>Content Strategy</SectionTitle>
        <Field label="Content Goal (90 days)"  value={form.content_goal_90d ?? ""}  onChange={set("content_goal_90d")}  placeholder="e.g. 10k Instagram followers" />
        <Field label="Weekly Post Target"      value={String(form.weekly_post_target ?? "")} onChange={set("weekly_post_target")} placeholder="e.g. 5" />
        <Field label="Brand Voice / Tone"      value={form.tone_specifics ?? ""}    onChange={set("tone_specifics")}    placeholder="How should the brand sound?" textarea />
        <Field label="What to NEVER say"       value={form.what_to_never_say ?? ""} onChange={set("what_to_never_say")} placeholder="Words, phrases, or topics to avoid…" textarea />
      </div>

      <div className="gc-card rounded-xl p-6 space-y-5">
        <SectionTitle>Social Presence</SectionTitle>
        <Field label="Instagram Handle"        value={form.instagram_handle ?? ""}  onChange={set("instagram_handle")}  placeholder="@yourhandle (no @)" />
        <div>
          <label className="block text-[hsl(var(--gc-text-2))] font-medium mb-1.5" style={{ fontSize: 13 }}>Competitor Handles</label>
          <TagListEditor values={form.competitor_handles ?? []} onChange={set("competitor_handles")} placeholder="Add competitor handle…" />
        </div>
        <Field label="Railway / Website URL"   value={form.railway_url ?? ""}       onChange={set("railway_url")}       placeholder="https://…" />
      </div>

      <div className="gc-card rounded-xl p-6 space-y-5">
        <SectionTitle>Bottlenecks</SectionTitle>
        <TagListEditor values={form.bottlenecks} onChange={set("bottlenecks")} placeholder="Add bottleneck…" />
      </div>
    </div>
  )
}

// ── New Brand Form ─────────────────────────────────────────────────────────────

function NewBrandForm({ onDone }: { onDone: () => void }) {
  const { setBrands, setActiveBrand, brands } = useBrandStore()
  const [name, setName]   = useState("")
  const [product, setProduct] = useState("")
  const [error, setError] = useState("")

  const mutation = useMutation({
    mutationFn: () => createBrand({
      brand_name: name.trim(),
      brand_slug: slugify(name.trim()),
      product_description: product.trim(),
      industry: "", phase: "Phase 1", website_url: "", price_india: "", price_international: "",
      target_audience: "", platforms: [], platform_handles: [], primary_bottleneck: "",
      instagram_handle: "", competitor_handles: [], brand_face: "", tone_of_voice: "",
      tone_specifics: "", content_goal_90d: "", weekly_post_target: "", past_content_worked: "",
      what_to_never_say: "", has_existing_pipeline: false, existing_pipeline: "", railway_url: "",
    }),
    onSuccess: (result) => {
      const newBrand = { slug: result.slug, name: result.name }
      setBrands([...brands, newBrand])
      setActiveBrand(newBrand)
      onDone()
    },
    onError: (err: Error) => setError(err.message),
  })

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between gap-4">
        <h1 className="text-white font-bold" style={{ fontSize: 26 }}>New Brand</h1>
        <button onClick={onDone}
          className="flex items-center gap-2 h-9 px-4 rounded-lg hover:text-white transition-colors"
          style={{ fontSize: 13, color: "hsl(var(--gc-text-2))", border: "1px solid hsl(var(--border))", background: "transparent" }}>
          <X size={14} /> Cancel
        </button>
      </div>

      {error && (
        <div className="flex items-center gap-2 px-4 py-3 rounded-lg border"
          style={{ background: "rgba(231,76,60,0.08)", borderColor: "rgba(231,76,60,0.2)", color: "hsl(var(--gc-red))", fontSize: 13 }}>
          <XCircle size={14} /> {error}
        </div>
      )}

      <div className="gc-card rounded-xl p-6 space-y-5">
        <Field label="Brand Name"   value={name}    onChange={setName}    placeholder="e.g. DropVolt" />
        <Field label="What do you sell?" value={product} onChange={setProduct} placeholder="Short product description…" textarea />
      </div>

      <p className="text-[hsl(var(--gc-text-2))]" style={{ fontSize: 13 }}>
        You can fill in the full brand profile after creation.
      </p>

      <button
        onClick={() => { if (!name.trim()) { setError("Brand name is required"); return }; setError(""); mutation.mutate() }}
        disabled={mutation.isPending || !name.trim()}
        className="flex items-center gap-2 h-10 px-6 rounded-lg font-bold hover:opacity-85 transition-opacity disabled:opacity-40"
        style={{ fontSize: 14, background: "hsl(var(--gc-gold))", color: "#000" }}>
        {mutation.isPending ? <Loader2 size={15} className="animate-spin" /> : <Plus size={15} />}
        Create Brand
      </button>
    </div>
  )
}

// ── Voice Profile Pane ─────────────────────────────────────────────────────────

function VoiceProfilePane({ slug, onBack }: { slug: string; onBack: () => void }) {
  const queryClient = useQueryClient()
  const [rawScripts, setRawScripts] = useState("")

  const { data: vpData, isLoading } = useQuery({
    queryKey: ["voice-profile", slug],
    queryFn:  () => fetchVoiceProfile(slug),
    enabled:  !!slug,
  })

  const extractMutation = useMutation({
    mutationFn: () => extractVoiceProfile(slug, rawScripts),
    onSuccess:  () => {
      queryClient.invalidateQueries({ queryKey: ["voice-profile", slug] })
      setRawScripts("")
    },
  })

  const profileExists = vpData?.exists === true

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <button onClick={onBack}
            className="text-[hsl(var(--gc-text-2))] hover:text-white transition-colors"
            style={{ fontSize: 13 }}>
            ← Back
          </button>
          <h1 className="text-white font-bold" style={{ fontSize: 26 }}>Voice Profile</h1>
        </div>
        {profileExists && (
          <span className="flex items-center gap-1.5 px-3 py-1 rounded-lg border"
            style={{ fontSize: 12, fontWeight: 600, color: "hsl(var(--gc-green))", background: "rgba(46,204,113,0.07)", borderColor: "rgba(46,204,113,0.2)" }}>
            <CheckCircle2 size={11} /> DNA Extracted
          </span>
        )}
      </div>

      <p className="text-[hsl(var(--gc-text-2))]" style={{ fontSize: 14, lineHeight: 1.6 }}>
        Voice DNA is extracted from 20–30 of your past scripts. Once extracted, Script Writer reads it and matches your writing style exactly.
      </p>

      {isLoading && <div className="h-32 gc-card rounded-xl animate-pulse" />}

      {!isLoading && profileExists && vpData && (
        <div className="gc-card rounded-xl p-6 space-y-4">
          <SectionTitle>Extracted Voice DNA</SectionTitle>
          <pre className="text-white overflow-x-auto rounded-lg p-4"
            style={{ fontSize: 12, lineHeight: 1.7, background: "hsl(var(--gc-surface2))", border: "1px solid hsl(var(--border))", whiteSpace: "pre-wrap" }}>
            {JSON.stringify(
              Object.fromEntries(Object.entries(vpData).filter(([k]) => k !== "exists")),
              null, 2
            )}
          </pre>
        </div>
      )}

      {!isLoading && (
        <div className="gc-card rounded-xl p-6 space-y-4">
          <SectionTitle>{profileExists ? "Re-extract Voice DNA" : "Extract Voice DNA"}</SectionTitle>
          <p className="text-[hsl(var(--gc-text-2))]" style={{ fontSize: 13 }}>
            Paste 20–30 of your past scripts, captions, or posts below. Claude will extract your vocabulary, sentence patterns, energy, and CTA style.
          </p>
          <textarea
            value={rawScripts}
            onChange={e => setRawScripts(e.target.value)}
            placeholder="Paste your past scripts here (captions, Reels scripts, LinkedIn posts…)"
            rows={10}
            className="w-full rounded-xl px-4 py-3 text-white placeholder:text-[hsl(var(--gc-text-3))] focus:outline-none resize-none"
            style={{ background: "hsl(var(--gc-surface2))", border: "1px solid hsl(var(--border))", fontSize: 13, lineHeight: 1.7 }}
          />

          {extractMutation.isError && (
            <div className="flex items-center gap-2 px-4 py-3 rounded-lg border"
              style={{ background: "rgba(231,76,60,0.08)", borderColor: "rgba(231,76,60,0.2)", color: "hsl(var(--gc-red))", fontSize: 13 }}>
              <XCircle size={14} /> {(extractMutation.error as Error).message}
            </div>
          )}

          <button
            onClick={() => { if (!rawScripts.trim()) return; extractMutation.mutate() }}
            disabled={extractMutation.isPending || !rawScripts.trim()}
            className="flex items-center gap-2 h-10 px-6 rounded-xl font-bold hover:opacity-85 transition-opacity disabled:opacity-40"
            style={{ fontSize: 14, background: "hsl(var(--gc-gold))", color: "#000" }}
          >
            {extractMutation.isPending ? <Loader2 size={15} className="animate-spin" /> : <Mic size={15} />}
            {extractMutation.isPending ? "Extracting…" : "Extract Voice DNA"}
          </button>

          {extractMutation.isSuccess && (
            <div className="flex items-center gap-2 px-4 py-3 rounded-lg border"
              style={{ background: "rgba(46,204,113,0.07)", borderColor: "rgba(46,204,113,0.2)", color: "hsl(var(--gc-green))", fontSize: 13 }}>
              <CheckCircle2 size={14} /> Voice DNA extracted and saved. Script Writer will now use it.
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── Root ───────────────────────────────────────────────────────────────────────

type Mode = "view" | "edit" | "new" | "voice"

export function BrandSpace() {
  const { activeBrand, brands, setActiveBrand, setBrands } = useBrandStore()
  const queryClient = useQueryClient()
  const [mode, setMode] = useState<Mode>("view")

  const deleteMutation = useMutation({
    mutationFn: async (slug: string) => {
      const res  = await apiFetch(`/api/brands/${slug}`, { method: "DELETE" })
      const json = await res.json()
      if (!json.success) throw new Error(json.error ?? "Delete failed")
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["brands"] })
      const remaining = brands.filter(b => b.slug !== activeBrand.slug)
      if (remaining.length > 0) {
        setBrands(remaining)
        setActiveBrand(remaining[0])
      }
    },
  })

  const { data: summary, isLoading: summaryLoading, dataUpdatedAt } = useQuery({
    queryKey:        ["brand-summary", activeBrand.slug],
    queryFn:         () => fetchSummary(activeBrand.slug),
    refetchInterval: 30000,
    enabled:         !!activeBrand.slug,
  })

  const { data: profile } = useQuery({
    queryKey: ["brand-profile", activeBrand.slug],
    queryFn:  () => fetchProfile(activeBrand.slug),
    enabled:  !!activeBrand.slug,
  })

  // Reset to view when brand changes
  useEffect(() => { setMode("view") }, [activeBrand.slug])

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Top bar */}
      <div style={{ height: 52, flexShrink: 0 }}
        className="flex items-center justify-between px-8 border-b border-[hsl(var(--border))]">
        <div className="flex items-center gap-2">
          <span className="text-[hsl(var(--gc-text-2))]" style={{ fontSize: 13 }}>Brand</span>
          <span className="text-[hsl(var(--gc-text-2))]" style={{ fontSize: 13 }}>/</span>
          <span className="text-white font-semibold" style={{ fontSize: 14 }}>
            {activeBrand.name || "Profile"}
          </span>
        </div>
        <div className="flex items-center gap-3">
          {dataUpdatedAt && (
            <div className="flex items-center gap-1.5 text-[hsl(var(--gc-text-2))]" style={{ fontSize: 12 }}>
              <Clock size={11} />
              {new Date(dataUpdatedAt).toLocaleTimeString("en-IN", { timeStyle: "short" })}
            </div>
          )}
          {mode === "view" && (
            <div className="flex items-center gap-2">
              <button onClick={() => setMode("voice")}
                className="flex items-center gap-1.5 h-8 px-3 rounded-lg font-medium hover:text-white transition-colors"
                style={{ fontSize: 13, color: "hsl(var(--gc-text-2))", border: "1px solid hsl(var(--border))", background: "transparent" }}>
                <Mic size={13} /> Voice Profile
              </button>
              <button onClick={() => setMode("new")}
                className="flex items-center gap-1.5 h-8 px-3 rounded-lg font-medium hover:text-white transition-colors"
                style={{ fontSize: 13, color: "hsl(var(--gc-text-2))", border: "1px solid hsl(var(--border))", background: "transparent" }}>
                <Plus size={13} /> New Brand
              </button>
              <button
                onClick={() => {
                  if (window.confirm(`Delete "${activeBrand.name}"? This cannot be undone.`)) {
                    deleteMutation.mutate(activeBrand.slug)
                  }
                }}
                disabled={deleteMutation.isPending}
                className="flex items-center gap-1.5 h-8 px-3 rounded-lg font-medium transition-colors hover:bg-red-950/40"
                style={{ fontSize: 13, color: "#f87171", border: "1px solid #7f1d1d", background: "transparent" }}>
                {deleteMutation.isPending ? <Loader2 size={13} className="animate-spin" /> : <Trash2 size={13} />}
                Delete
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto">
        <div className="px-8 pt-8 pb-12" style={{ maxWidth: 860 }}>

          {mode === "new"   && <NewBrandForm onDone={() => setMode("view")} />}
          {mode === "voice" && <VoiceProfilePane slug={activeBrand.slug} onBack={() => setMode("view")} />}

          {mode !== "new" && summaryLoading && (
            <div className="space-y-4">
              {[1,2,3].map(i => <div key={i} className="h-24 gc-card rounded-xl animate-pulse" />)}
            </div>
          )}

          {mode === "view" && !summaryLoading && summary && (
            <ProfileView data={summary} onEdit={() => setMode("edit")} />
          )}

          {mode === "view" && !summaryLoading && !summary && (
            <div className="flex flex-col items-center justify-center py-24 text-center">
              <div className="w-16 h-16 rounded-full gc-card flex items-center justify-center mb-5 text-3xl">🏢</div>
              <h2 className="text-white font-bold" style={{ fontSize: 22 }}>No brand loaded</h2>
              <p className="text-[hsl(var(--gc-text-2))] mt-2" style={{ fontSize: 15, maxWidth: 340 }}>
                Select a brand from the sidebar or create your first brand.
              </p>
              <button onClick={() => setMode("new")}
                className="mt-6 flex items-center gap-2 h-10 px-6 rounded-lg font-bold hover:opacity-85 transition-opacity"
                style={{ fontSize: 14, background: "hsl(var(--gc-gold))", color: "#000" }}>
                <Plus size={15} /> Create Brand
              </button>
            </div>
          )}

          {mode === "edit" && profile && (
            <ProfileEdit
              initial={profile}
              slug={activeBrand.slug}
              onDone={() => {
                setMode("view")
                queryClient.invalidateQueries({ queryKey: ["brand-summary", activeBrand.slug] })
              }}
            />
          )}

        </div>
      </div>
    </div>
  )
}
