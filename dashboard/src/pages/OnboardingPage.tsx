import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { Rocket, Sparkles, ArrowRight, ArrowLeft, Loader2, Check } from "lucide-react"
import { apiFetch } from "@/lib/api"
import { useBrandStore } from "@/store/brandStore"
import { CockpitRoot, Card, PrimaryButton, STATUS } from "@/components/cockpit/primitives"

/**
 * Brand onboarding intake — the client (or owner-as-client) brief that bootstraps a brand.
 * Branches on New vs Existing because it changes what the agents can do:
 *   - existing → handles + follower range + what's working are required (agents scrape/derive)
 *   - new      → reference accounts + voice declaration + visual identity are required
 * Built in the cockpit design language. Submits the full profile to /api/auth/create-brand
 * (assigns the user as owner + writes brand_profile.json with every field).
 */

type BrandType = "" | "new" | "existing"

interface BrandData {
  brandType: BrandType
  name: string
  slug: string
  offer: string
  heroProducts: string
  industry: string
  stage: string
  website: string
  audience: string
  usp: string
  goal: string
  bottleneck: string
  market: string
  tone: string
  wordsLove: string
  redLines: string
  brandFace: string
  referenceAccounts: string // new: admired accounts | existing: posts/links they love
  followerRange: string // existing only
  whatsWorking: string // existing only
  instagram: string
  linkedin: string
  youtube: string
  tiktok: string
  x: string
  competitors: string
  brandColors: string
}

const EMPTY: BrandData = {
  brandType: "", name: "", slug: "", offer: "", heroProducts: "", industry: "", stage: "",
  website: "", audience: "", usp: "", goal: "", bottleneck: "", market: "English / Global",
  tone: "", wordsLove: "", redLines: "", brandFace: "", referenceAccounts: "",
  followerRange: "", whatsWorking: "", instagram: "", linkedin: "", youtube: "", tiktok: "",
  x: "", competitors: "", brandColors: "",
}

function slugify(name: string): string {
  return name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 60)
}

// ── Small styled primitives (cockpit look) ────────────────────────────────────
function Label({ children, required }: { children: React.ReactNode; required?: boolean }) {
  return (
    <label className="mb-1.5 block font-mono text-[10.5px] uppercase tracking-[0.14em] text-zinc-500">
      {children} {required && <span style={{ color: STATUS.amber.fg }}>*</span>}
    </label>
  )
}

const inputCls =
  "w-full rounded-lg border border-white/[0.09] bg-[#0e0f12] px-3.5 py-2.5 text-[13.5px] text-zinc-100 placeholder:text-zinc-600 focus:border-white/[0.18] focus:outline-none"

function Text({
  value, onChange, placeholder, autoFocus,
}: { value: string; onChange: (v: string) => void; placeholder?: string; autoFocus?: boolean }) {
  return (
    <input
      className={inputCls}
      value={value}
      autoFocus={autoFocus}
      placeholder={placeholder}
      onChange={(e) => onChange(e.target.value)}
    />
  )
}

function Area({
  value, onChange, placeholder, rows = 3,
}: { value: string; onChange: (v: string) => void; placeholder?: string; rows?: number }) {
  return (
    <textarea
      className={inputCls + " resize-none"}
      rows={rows}
      value={value}
      placeholder={placeholder}
      onChange={(e) => onChange(e.target.value)}
    />
  )
}

function Choice({
  options, value, onChange,
}: { options: string[]; value: string; onChange: (v: string) => void }) {
  return (
    <div className="flex flex-wrap gap-2">
      {options.map((o) => {
        const on = value === o
        return (
          <button
            key={o}
            type="button"
            onClick={() => onChange(o)}
            className="rounded-lg border px-3 py-1.5 text-[12.5px] font-medium transition-colors"
            style={{
              borderColor: on ? "color-mix(in oklab, var(--accent) 45%, transparent)" : "rgba(255,255,255,0.09)",
              background: on ? "color-mix(in oklab, var(--accent) 18%, #0e0f12)" : "rgba(255,255,255,0.02)",
              color: on ? "#fff" : "#9aa0a8",
            }}
          >
            {o}
          </button>
        )
      })}
    </div>
  )
}

function Field({
  label, required, children,
}: { label: string; required?: boolean; children: React.ReactNode }) {
  return (
    <div>
      <Label required={required}>{label}</Label>
      {children}
    </div>
  )
}

// ── Steps config ──────────────────────────────────────────────────────────────
// Step 0 = type pick. 1..4 = sections. 5 = review.
const STEP_TITLES = [
  "Are you launching new, or already active?",
  "Brand basics",
  "Audience & goal",
  "Voice & brand safety",
  "Platforms, competitors & identity",
  "Review & launch",
]

export function OnboardingPage() {
  const navigate = useNavigate()
  const { setActiveBrand, setBrands, brands } = useBrandStore()
  const [step, setStep] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [data, setData] = useState<BrandData>(EMPTY)
  const [slugEdited, setSlugEdited] = useState(false)

  const isExisting = data.brandType === "existing"
  const isNew = data.brandType === "new"

  function up<K extends keyof BrandData>(field: K, value: BrandData[K]) {
    setData((prev) => {
      const next = { ...prev, [field]: value }
      if (field === "name" && !slugEdited) next.slug = slugify(value as string)
      if (field === "slug") setSlugEdited(true)
      return next
    })
  }

  // Per-step required-field gates
  function canAdvance(): boolean {
    switch (step) {
      case 0: return data.brandType !== ""
      case 1: return !!data.name.trim() && !!data.offer.trim() && !!data.stage
      case 2: return !!data.audience.trim() && !!data.usp.trim() && !!data.goal
      case 3: return !!data.tone.trim() && !!data.redLines.trim() && !!data.brandFace &&
                     (isNew ? !!data.referenceAccounts.trim() : true)
      case 4:
        if (isExisting) return !!data.instagram.trim() && !!data.competitors.trim() &&
                                !!data.followerRange && !!data.whatsWorking.trim()
        return !!data.competitors.trim() // new: handles optional
      default: return true
    }
  }

  async function handleCreate() {
    setLoading(true); setError("")
    const slug = data.slug || slugify(data.name)
    const competitor_handles = data.competitors.split(",").map((s) => s.trim().replace(/^@/, "")).filter(Boolean)
    const brand_colors = data.brandColors.split(",").map((s) => s.trim()).filter(Boolean)
    const profile = {
      brand_type: data.brandType,
      name: data.name,
      product_description: data.offer,
      hero_products: data.heroProducts,
      industry: data.industry,
      phase: data.stage,
      website_url: data.website,
      target_audience: data.audience,
      brand_brief: data.usp,
      content_goal_90d: data.goal,
      primary_bottleneck: data.bottleneck,
      market: data.market,
      tone_of_voice: data.tone,
      tone_specifics: data.wordsLove,
      what_to_never_say: data.redLines,
      brand_face: data.brandFace,
      reference_accounts: data.referenceAccounts,
      follower_range: data.followerRange,
      past_content_worked: data.whatsWorking,
      instagram_handle: data.instagram.replace(/^@/, ""),
      platform_handles: { linkedin: data.linkedin, youtube: data.youtube, tiktok: data.tiktok, x: data.x },
      competitor_handles,
      brand_colors,
      social_handles: {
        instagram: data.instagram, linkedin: data.linkedin,
        youtube: data.youtube, tiktok: data.tiktok, x: data.x,
      },
      platforms: [
        data.instagram && "Instagram", data.linkedin && "LinkedIn",
        data.youtube && "YouTube", data.tiktok && "TikTok", data.x && "X",
      ].filter(Boolean),
    }
    try {
      const res = await apiFetch("/api/auth/create-brand", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ slug, name: data.name, profile }),
      })
      const json = await res.json()
      if (!json.success) { setError(json.error || "Failed to create brand"); setLoading(false); return }
      const newBrand = { slug, name: data.name, primary: brands.length === 0 }
      setBrands([...brands, newBrand])
      setActiveBrand(newBrand)
      navigate("/")
    } catch {
      setError("Network error")
    }
    setLoading(false)
  }

  return (
    <CockpitRoot>
      <div className="flex min-h-screen items-center justify-center px-4 py-10">
        <div className="w-full max-w-xl">
          {/* progress */}
          <div className="mb-5 flex items-center gap-1.5">
            {STEP_TITLES.map((_, i) => (
              <div
                key={i}
                className="h-1 flex-1 rounded-full transition-colors"
                style={{ background: i <= step ? "var(--accent)" : "rgba(255,255,255,0.08)" }}
              />
            ))}
          </div>

          <Card className="p-7">
            <div className="mb-1 font-mono text-[10.5px] uppercase tracking-[0.16em] text-zinc-600">
              Step {step + 1} of {STEP_TITLES.length}
            </div>
            <h1 className="mb-6 text-[19px] font-semibold tracking-tight text-zinc-100">
              {STEP_TITLES[step]}
            </h1>

            <div className="space-y-4">
              {/* STEP 0 — type */}
              {step === 0 && (
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  {[
                    { id: "new", icon: Rocket, t: "Brand new", d: "Starting fresh — little or no social presence yet." },
                    { id: "existing", icon: Sparkles, t: "Already active", d: "You already post and have an audience to build on." },
                  ].map((o) => {
                    const on = data.brandType === o.id
                    return (
                      <button
                        key={o.id}
                        onClick={() => up("brandType", o.id as BrandType)}
                        className="flex flex-col items-start gap-2 rounded-xl border p-4 text-left transition-colors"
                        style={{
                          borderColor: on ? "color-mix(in oklab, var(--accent) 45%, transparent)" : "rgba(255,255,255,0.08)",
                          background: on ? "color-mix(in oklab, var(--accent) 14%, #141518)" : "rgba(255,255,255,0.015)",
                        }}
                      >
                        <o.icon size={18} style={{ color: on ? "var(--accent)" : "#9aa0a8" }} />
                        <div className="text-[14px] font-semibold text-zinc-100">{o.t}</div>
                        <div className="text-[12px] leading-relaxed text-zinc-500">{o.d}</div>
                      </button>
                    )
                  })}
                </div>
              )}

              {/* STEP 1 — basics */}
              {step === 1 && (
                <>
                  <Field label="Brand name" required>
                    <Text value={data.name} onChange={(v) => up("name", v)} placeholder="e.g. AskGauravAI" autoFocus />
                  </Field>
                  <Field label="What you sell / your offer" required>
                    <Area value={data.offer} onChange={(v) => up("offer", v)} placeholder="What you do, who it's for, in a sentence or two." rows={2} />
                  </Field>
                  <Field label="Hero products + rough price points">
                    <Text value={data.heroProducts} onChange={(v) => up("heroProducts", v)} placeholder="e.g. Reporting Project ₹2.5–7k · Grid Control ₹15–50k" />
                  </Field>
                  <Field label="Industry / category">
                    <Text value={data.industry} onChange={(v) => up("industry", v)} placeholder="e.g. AI marketing / SaaS" />
                  </Field>
                  <Field label="Business stage" required>
                    <Choice options={["Idea", "Early", "Growing", "Established"]} value={data.stage} onChange={(v) => up("stage", v)} />
                  </Field>
                  <Field label="Website">
                    <Text value={data.website} onChange={(v) => up("website", v)} placeholder="https://…" />
                  </Field>
                </>
              )}

              {/* STEP 2 — audience & goal */}
              {step === 2 && (
                <>
                  <Field label="Who is your audience" required>
                    <Area value={data.audience} onChange={(v) => up("audience", v)} placeholder="Demographics + what they care about." rows={2} />
                  </Field>
                  <Field label="What makes you different (USP / positioning)" required>
                    <Area value={data.usp} onChange={(v) => up("usp", v)} placeholder="Why you, not a competitor." rows={2} />
                  </Field>
                  <Field label="Primary 90-day goal" required>
                    <Choice options={["Followers", "Leads", "Sales", "Awareness"]} value={data.goal} onChange={(v) => up("goal", v)} />
                  </Field>
                  <Field label="Biggest bottleneck right now">
                    <Text value={data.bottleneck} onChange={(v) => up("bottleneck", v)} placeholder="What's stuck / hardest right now." />
                  </Field>
                  <Field label="Market & language">
                    <Text value={data.market} onChange={(v) => up("market", v)} placeholder="e.g. English / Global" />
                  </Field>
                </>
              )}

              {/* STEP 3 — voice & safety */}
              {step === 3 && (
                <>
                  {isExisting && (
                    <p className="rounded-lg border border-white/[0.07] bg-white/[0.015] px-3.5 py-2.5 text-[12px] leading-relaxed text-zinc-500">
                      You're an existing brand — agents will derive your real voice from your posts. The
                      tone below is a guide, not the source of truth.
                    </p>
                  )}
                  <Field label="Brand voice / tone (a few adjectives)" required>
                    <Text value={data.tone} onChange={(v) => up("tone", v)} placeholder="e.g. direct, founder-to-founder, no fluff" />
                  </Field>
                  <Field label="Words / phrases you love">
                    <Text value={data.wordsLove} onChange={(v) => up("wordsLove", v)} placeholder="Signature phrases, vocabulary you use." />
                  </Field>
                  <Field label="Red lines / do-not-post" required>
                    <Area value={data.redLines} onChange={(v) => up("redLines", v)} placeholder="Banned claims, topics, anything off-limits. Brand Guardian enforces this." rows={2} />
                  </Field>
                  <Field label="Who's the face?" required>
                    <Choice options={["Founder on camera", "Team", "AI avatar", "Logo-only"]} value={data.brandFace} onChange={(v) => up("brandFace", v)} />
                  </Field>
                  <Field label={isNew ? "Accounts whose vibe you admire (1–3)" : "Posts / links whose vibe you love (1–3)"} required={isNew}>
                    <Area value={data.referenceAccounts} onChange={(v) => up("referenceAccounts", v)} placeholder={isNew ? "@handles you want to feel like — used to build your voice profile." : "Links or @handles of posts you love."} rows={2} />
                  </Field>
                </>
              )}

              {/* STEP 4 — platforms, competitors, identity */}
              {step === 4 && (
                <>
                  <Field label="Instagram handle" required={isExisting}>
                    <Text value={data.instagram} onChange={(v) => up("instagram", v)} placeholder="@yourhandle" autoFocus />
                  </Field>
                  <div className="grid grid-cols-2 gap-3">
                    <Field label="LinkedIn"><Text value={data.linkedin} onChange={(v) => up("linkedin", v)} placeholder="URL / handle" /></Field>
                    <Field label="YouTube"><Text value={data.youtube} onChange={(v) => up("youtube", v)} placeholder="channel URL" /></Field>
                    <Field label="TikTok"><Text value={data.tiktok} onChange={(v) => up("tiktok", v)} placeholder="@handle" /></Field>
                    <Field label="X"><Text value={data.x} onChange={(v) => up("x", v)} placeholder="@handle" /></Field>
                  </div>
                  <Field label="Competitor handles (3–5, comma-separated)" required>
                    <Text value={data.competitors} onChange={(v) => up("competitors", v)} placeholder="@comp1, @comp2, @comp3" />
                  </Field>
                  {isExisting && (
                    <>
                      <Field label="Current follower range" required>
                        <Choice options={["<1k", "1k–10k", "10k–100k", "100k+"]} value={data.followerRange} onChange={(v) => up("followerRange", v)} />
                      </Field>
                      <Field label="What's working / not working" required>
                        <Area value={data.whatsWorking} onChange={(v) => up("whatsWorking", v)} placeholder="What's performing, what's flat — your read on it." rows={2} />
                      </Field>
                    </>
                  )}
                  <Field label="Brand colors (hex, comma-separated)">
                    <Text value={data.brandColors} onChange={(v) => up("brandColors", v)} placeholder="#7c6fe6, #0b0c0e — Carousel Designer uses these" />
                  </Field>
                </>
              )}

              {/* STEP 5 — review */}
              {step === 5 && (
                <div className="space-y-2 rounded-xl border border-white/[0.07] bg-white/[0.015] p-4 text-[13px]">
                  {[
                    ["Type", isNew ? "Brand new" : "Already active"],
                    ["Brand", data.name],
                    ["Offer", data.offer],
                    ["Audience", data.audience],
                    ["Goal", data.goal],
                    ["Voice", data.tone],
                    ["Red lines", data.redLines],
                    ["Face", data.brandFace],
                    ["Instagram", data.instagram || "—"],
                    ["Competitors", data.competitors || "—"],
                  ].map(([k, v]) => (
                    <div key={k} className="flex gap-3">
                      <span className="w-24 shrink-0 font-mono text-[10.5px] uppercase tracking-[0.12em] text-zinc-600">{k}</span>
                      <span className="text-zinc-300">{v}</span>
                    </div>
                  ))}
                </div>
              )}

              {error && (
                <div className="rounded-lg border px-3.5 py-2.5 text-[12.5px] font-medium"
                  style={{ borderColor: STATUS.red.bd, background: STATUS.red.bg, color: STATUS.red.fg }}>
                  {error}
                </div>
              )}
            </div>

            {/* nav */}
            <div className="mt-7 flex items-center gap-2">
              {step > 0 && (
                <button
                  onClick={() => setStep((s) => s - 1)}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-white/[0.08] px-3.5 py-2 text-[13px] font-medium text-zinc-300 transition-colors hover:bg-white/[0.04]"
                >
                  <ArrowLeft size={14} /> Back
                </button>
              )}
              <div className="flex-1" />
              {step < 5 ? (
                <PrimaryButton icon={ArrowRight} disabled={!canAdvance()} onClick={() => setStep((s) => s + 1)}>
                  Next
                </PrimaryButton>
              ) : (
                <PrimaryButton icon={loading ? Loader2 : Check} disabled={loading} onClick={handleCreate}>
                  {loading ? "Creating…" : "Launch brand"}
                </PrimaryButton>
              )}
            </div>
          </Card>
        </div>
      </div>
    </CockpitRoot>
  )
}
