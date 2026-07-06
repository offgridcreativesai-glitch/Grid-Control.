import { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { motion } from "framer-motion"
import { Rocket, TrendingUp, ArrowRight, ArrowLeft, Loader2, Check, Camera, Briefcase, Video, Hash } from "lucide-react"
import { apiFetch } from "@/lib/api"
import { useBrandStore } from "@/store/brandStore"
import { AgentCharacter } from "@/components/AgentCharacter"
import { SpaceBackground } from "@/components/SpaceBackground"
import { Wordmark } from "@/components/brand/Logo"
import { cn } from "@/lib/utils"

/**
 * Brand onboarding intake — the client (or owner-as-client) brief that bootstraps a brand.
 * Branches on New vs Existing because it changes what the agents can do:
 *   - existing → handles + follower range + what's working are required (agents scrape/derive)
 *   - new      → reference accounts + voice declaration + visual identity are required
 * Dark-cinematic design language. Submits the full profile to /api/auth/create-brand.
 */

type BrandType = "" | "new" | "existing"

interface BrandData {
  brandType: BrandType
  name: string
  slug: string
  offer: string
  /** business-model archetype — Product / Service / Personal brand. Feeds the
   * backend STEP-0 reasoning layer (brand_profile.business_model_archetype). */
  archetype: string
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
  brandType: "", name: "", slug: "", offer: "", archetype: "", heroProducts: "", industry: "", stage: "",
  website: "", audience: "", usp: "", goal: "", bottleneck: "", market: "English / Global",
  tone: "", wordsLove: "", redLines: "", brandFace: "", referenceAccounts: "",
  followerRange: "", whatsWorking: "", instagram: "", linkedin: "", youtube: "", tiktok: "",
  x: "", competitors: "", brandColors: "",
}

function slugify(name: string): string {
  return name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 60)
}

// ── Input normalization (mirrors backend _normalize_brand_profile) ──────────────
// "NA"/blank/placeholder handles must NOT count as a real account.
const NULLISH = new Set(["", "na", "n/a", "none", "nil", "-", "—", "tbd", "null", "n.a."])
function cleanHandle(v: string): string {
  let s = (v || "").trim().replace(/^@+/, "").replace(/\/+$/, "")
  const m = s.match(/(?:instagram\.com|twitter\.com|x\.com|tiktok\.com|linkedin\.com\/(?:in|company))\/([^/?#]+)/i)
  if (m) s = m[1].replace(/^@+/, "")
  return NULLISH.has(s.toLowerCase()) ? "" : s
}
function splitHandles(raw: string): string[] {
  const seen = new Set<string>(); const out: string[] = []
  for (const tok of (raw || "").split(/\s+and\s+|[,;|&\n]+|\s+/i)) {
    const h = cleanHandle(tok)
    if (h && !seen.has(h.toLowerCase())) { seen.add(h.toLowerCase()); out.push(h) }
  }
  return out
}
const HEX_RE = /^#?[0-9a-fA-F]{3}([0-9a-fA-F]{3})?$/

// ── Small styled primitives ────────────────────────────────────────────────────
function Label({ children, required }: { children: React.ReactNode; required?: boolean }) {
  return (
    <label className="mb-1.5 block text-[10px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
      {children} {required && <span className="text-primary">*</span>}
    </label>
  )
}

const inputCls =
  "w-full rounded-xl border border-input bg-black/30 px-4 py-3 text-[14px] text-foreground outline-none transition-colors placeholder:text-muted-foreground/70 focus:border-primary/60"

function Text({
  value, onChange, placeholder, autoFocus,
}: { value: string; onChange: (v: string) => void; placeholder?: string; autoFocus?: boolean }) {
  return (
    <input className={inputCls} value={value} autoFocus={autoFocus} placeholder={placeholder} onChange={(e) => onChange(e.target.value)} />
  )
}

function Area({
  value, onChange, placeholder, rows = 3,
}: { value: string; onChange: (v: string) => void; placeholder?: string; rows?: number }) {
  return (
    <textarea className={cn(inputCls, "resize-none")} rows={rows} value={value} placeholder={placeholder} onChange={(e) => onChange(e.target.value)} />
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
            className={cn(
              "rounded-full border px-4 py-2 text-[13px] font-medium transition-colors",
              on ? "border-emerald/50 bg-emerald/15 text-foreground" : "border-border bg-white/[0.02] text-muted-foreground hover:text-foreground",
            )}
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
// Step 0 = type pick. 1..4 = sections. 5 = review. 6 = connect accounts.
const STEP_TITLES = [
  "Are we launching new, or scaling what's active?",
  "Brand basics",
  "Audience & goal",
  "Voice & brand safety",
  "Platforms, competitors & identity",
  "Review & confirm",
  "Connect your accounts",
]

export function OnboardingPage() {
  const navigate = useNavigate()
  const { setActiveBrand, setBrands, brands } = useBrandStore()
  const [step, setStep] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [data, setData] = useState<BrandData>(EMPTY)
  const [slugEdited, setSlugEdited] = useState(false)
  const [created, setCreated] = useState(false)
  const [createdSlug, setCreatedSlug] = useState("")
  const [conn, setConn] = useState<Record<string, string>>({}) // platform -> account
  const [connecting, setConnecting] = useState<string | null>(null) // platform mid-connect

  const isExisting = data.brandType === "existing"
  const isNew = data.brandType === "new"
  const N = STEP_TITLES.length
  const anyConnected = Object.keys(conn).length > 0

  // Receive an OAuth result from the popup (relayed by ConnectionsPage)
  useEffect(() => {
    function onMsg(e: MessageEvent) {
      if (e.origin !== window.location.origin) return
      const d = e.data
      if (!d || d.type !== "oauth_connect") return
      setConnecting(null)
      if (d.status === "connected") setConn((prev) => ({ ...prev, [d.platform]: d.detail || "Connected" }))
      else setError(d.status === "denied" ? "Connection cancelled." : `Connect failed${d.detail ? `: ${d.detail}` : ""}`)
    }
    window.addEventListener("message", onMsg)
    return () => window.removeEventListener("message", onMsg)
  }, [])

  async function connectOAuth(platform: string) {
    setError(""); setConnecting(platform)
    try {
      const r = await apiFetch(`/api/connections/${platform}/authorize-url?brand_slug=${encodeURIComponent(createdSlug)}`)
      const j = await r.json()
      if (!j.success || !j.data?.url) throw new Error(j.error || "Could not start connect")
      const w = 600, h = 720
      const left = window.screenX + (window.outerWidth - w) / 2
      const top = window.screenY + (window.outerHeight - h) / 2
      window.open(j.data.url, "oauth", `width=${w},height=${h},left=${left},top=${top}`)
    } catch (e) {
      setConnecting(null); setError((e as Error).message)
    }
  }

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
      case 1: return !!data.name.trim() && !!data.offer.trim() && !!data.stage && !!data.archetype
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
    const competitor_handles = splitHandles(data.competitors)
    const brand_colors = data.brandColors.split(",").map((s) => s.trim()).filter((c) => HEX_RE.test(c))
    const ig = cleanHandle(data.instagram)
    const li = cleanHandle(data.linkedin)
    const yt = cleanHandle(data.youtube)
    const tk = cleanHandle(data.tiktok)
    const xh = cleanHandle(data.x)
    const profile = {
      brand_type: data.brandType,
      // "Personal brand" → "personal"; matches agents/_lib/brand_archetype.py ARCHETYPES
      business_model_archetype: data.archetype.toLowerCase().split(" ")[0],
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
      instagram_handle: ig,
      platform_handles: { linkedin: li, youtube: yt, tiktok: tk, x: xh },
      competitor_handles,
      brand_colors,
      social_handles: { instagram: ig, linkedin: li, youtube: yt, tiktok: tk, x: xh },
      platforms: [
        ig && "Instagram", li && "LinkedIn",
        yt && "YouTube", tk && "TikTok", xh && "X",
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
      setCreated(true); setCreatedSlug(slug)
      setStep(6) // → connect accounts, brand now exists so OAuth can store tokens
    } catch {
      setError("Network error")
    }
    setLoading(false)
  }

  function pickType(t: BrandType) {
    up("brandType", t)
    setStep(1)
  }

  return (
    <div className="relative min-h-screen overflow-hidden">
      <SpaceBackground />

      {/* top bar */}
      <div className="absolute left-0 right-0 top-0 z-10 flex items-center justify-between px-7 py-6">
        <Wordmark small />
      </div>

      <div className="relative flex min-h-screen items-center justify-center px-6 py-20">
        {/* ── STEP 0 — brand type, the Atlas greeter ── */}
        {step === 0 ? (
          <div className="grid w-full max-w-6xl items-center gap-10 lg:grid-cols-[minmax(280px,380px)_1fr]">
            {/* Atlas + speech bubble */}
            <div className="flex flex-col items-center text-center lg:items-start lg:text-left">
              <div className="relative">
                <span className="absolute inset-0 -z-10 rounded-full bg-[radial-gradient(circle,rgba(255,77,0,0.22),transparent_65%)] blur-xl" />
                <AgentCharacter agent="atlas" size="lg" showGlow still />
              </div>
              <div className="glass-panel mt-5 max-w-sm rounded-2xl rounded-tl-sm p-5 text-left">
                <p className="mb-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-primary">Atlas</p>
                <p className="text-[15px] leading-relaxed text-foreground/90">
                  Welcome, I am Atlas. Let's get your marketing engine started. Are we launching something new, or scaling what's active?
                </p>
              </div>
            </div>

            {/* choice cards */}
            <div className="grid gap-5 sm:grid-cols-2">
              {[
                { id: "new" as BrandType, icon: Rocket, t: "New Venture", d: "Launch something new and build momentum from the ground up.", accent: "primary" },
                { id: "existing" as BrandType, icon: TrendingUp, t: "Active Brand", d: "Scale what's working and unlock your next level of growth.", accent: "blue" },
              ].map((o, i) => {
                const isLava = o.accent === "primary"
                return (
                  <motion.button
                    key={o.id}
                    initial={{ opacity: 0, y: 24 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 * i }}
                    onClick={() => pickType(o.id)}
                    className={cn(
                      "group relative flex h-full flex-col items-center gap-5 rounded-3xl border p-8 text-center transition-all hover:scale-[1.02]",
                      isLava ? "border-primary/40 bg-primary/[0.06] hover:border-primary/70" : "border-blue/40 bg-[#2E6BFF]/[0.06] hover:border-blue/70",
                    )}
                  >
                    <span
                      className={cn(
                        "grid h-20 w-20 place-items-center rounded-2xl ring-1",
                        isLava ? "bg-primary/10 text-primary ring-primary/30" : "bg-[#2E6BFF]/10 text-blue ring-blue/30",
                      )}
                    >
                      <o.icon className="h-9 w-9" />
                    </span>
                    <div>
                      <p className="font-display text-2xl font-bold text-foreground">{o.t}</p>
                      <p className="mx-auto mt-2 max-w-[220px] text-sm leading-relaxed text-muted-foreground">{o.d}</p>
                    </div>
                    <span
                      className={cn(
                        "mt-auto grid h-10 w-10 place-items-center rounded-full border transition-colors",
                        isLava ? "border-primary/40 text-primary group-hover:bg-primary group-hover:text-primary-foreground" : "border-blue/40 text-blue group-hover:bg-blue group-hover:text-white",
                      )}
                    >
                      <ArrowRight className="h-4 w-4" />
                    </span>
                  </motion.button>
                )
              })}
            </div>
          </div>
        ) : (
          /* ── STEPS 1–5 — form card ── */
          <div className="w-full max-w-xl">
            <div className="glass-panel rounded-3xl p-8">
              <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-primary">
                Step {step + 1} of {N}
              </p>
              <h1 className="mb-6 mt-1 font-display text-2xl font-bold tracking-tight text-foreground">{STEP_TITLES[step]}</h1>

              {/* No AnimatePresence mode="wait" here: a stuck exit animation left the
                  card EMPTY on step change (old fields unmounting, new never mounting).
                  A simple keyed fade-in can't strand the user. */}
              <motion.div
                key={step}
                initial={{ opacity: 0, x: 16 }}
                animate={{ opacity: 1, x: 0 }}
                className="space-y-4"
              >
                  {/* STEP 1 — basics */}
                  {step === 1 && (
                    <>
                      <Field label="Brand name" required>
                        <Text value={data.name} onChange={(v) => up("name", v)} placeholder="e.g. AskGauravAI" autoFocus />
                      </Field>
                      <Field label="What you sell / your offer" required>
                        <Area value={data.offer} onChange={(v) => up("offer", v)} placeholder="What you do, who it's for, in a sentence or two." rows={2} />
                      </Field>
                      <Field label="What kind of brand is this" required>
                        <Choice
                          options={["Product", "Service", "Personal brand"]}
                          value={data.archetype}
                          onChange={(v) => up("archetype", v)}
                        />
                        <p className="mt-1.5 text-[11px] leading-relaxed text-muted-foreground">
                          This changes how the team writes for you — a product sells on desire, a service on trust, a personal brand on connection.
                        </p>
                      </Field>
                      <Field label="Hero products + rough price points">
                        <Text value={data.heroProducts} onChange={(v) => up("heroProducts", v)} placeholder="e.g. Reporting ₹2.5–7k · Grid Control ₹15–50k" />
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
                        <p className="rounded-xl border border-border bg-white/[0.02] px-4 py-3 text-[12px] leading-relaxed text-muted-foreground">
                          You're an existing brand — agents derive your real voice from your posts. The tone below is a guide, not the source of truth.
                        </p>
                      )}
                      <Field label="Brand voice / tone (a few adjectives)" required>
                        <Text value={data.tone} onChange={(v) => up("tone", v)} placeholder="e.g. direct, founder-to-founder, no fluff" />
                      </Field>
                      <Field label="Words / phrases you love">
                        <Text value={data.wordsLove} onChange={(v) => up("wordsLove", v)} placeholder="Signature phrases, vocabulary you use." />
                      </Field>
                      <Field label="Red lines / do-not-post" required>
                        <Area value={data.redLines} onChange={(v) => up("redLines", v)} placeholder="Banned claims, topics, anything off-limits. Aegis enforces this." rows={2} />
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
                      <Field label="Primary brand color">
                        <div className="flex items-center gap-3">
                          <input
                            type="color"
                            value={(data.brandColors.split(",")[0] || "#FF4D00").trim()}
                            onChange={(e) => up("brandColors", e.target.value)}
                            className="h-11 w-14 cursor-pointer rounded-lg border border-input bg-transparent"
                          />
                          <Text value={data.brandColors} onChange={(v) => up("brandColors", v)} placeholder="#FF4D00, #0A0C0B — Lumen uses these" />
                        </div>
                      </Field>
                    </>
                  )}

                  {/* STEP 5 — review */}
                  {step === 5 && (
                    <div className="space-y-2 rounded-2xl border border-border bg-white/[0.02] p-5 text-[13px]">
                      {[
                        ["Type", isNew ? "New Venture" : "Active Brand"],
                        ["Brand", data.name],
                        ["Kind", data.archetype || "—"],
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
                          <span className="w-24 shrink-0 text-[10px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">{k}</span>
                          <span className="text-foreground/85">{v}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* STEP 6 — connect accounts */}
                  {step === 6 && (
                    <div className="space-y-4">
                      <p className="rounded-xl border border-border bg-white/[0.02] px-4 py-3 text-[12.5px] leading-relaxed text-muted-foreground">
                        Connect your accounts so your team can post for you and pull real numbers — no passwords ever shared with us.
                        <br />
                        <span className="text-foreground/80">Instagram must be a Professional account.</span> If it's a personal one, open Instagram → Settings → <span className="text-foreground/80">Account type and tools → Switch to Professional</span> (free, ~10 seconds), then connect.
                      </p>

                      {/* Live one-click OAuth platforms */}
                      {[
                        { id: "instagram", name: "Instagram", icon: Camera, sub: "Insights + publishing" },
                        { id: "youtube", name: "YouTube", icon: Video, sub: "Upload + analytics" },
                        { id: "linkedin", name: "LinkedIn", icon: Briefcase, sub: "Posting + profile" },
                        { id: "twitter", name: "X", icon: Hash, sub: "Read + insights" },
                      ].map((p) => {
                        const acct = conn[p.id]
                        return (
                          <button
                            key={p.id}
                            type="button"
                            onClick={() => connectOAuth(p.id)}
                            disabled={connecting === p.id || !!acct}
                            className={cn(
                              "flex w-full items-center justify-between gap-3 rounded-2xl border px-4 py-3.5 text-left transition-colors",
                              acct ? "border-emerald/50 bg-emerald/10" : "border-border bg-white/[0.02] hover:border-primary/50 hover:bg-white/[0.04]",
                            )}
                          >
                            <span className="flex items-center gap-3">
                              <span className="grid h-10 w-10 place-items-center rounded-xl border border-border bg-white/[0.03]">
                                <p.icon className="h-[18px] w-[18px] text-foreground/80" />
                              </span>
                              <span>
                                <span className="block text-[14px] font-semibold text-foreground">{p.name}</span>
                                <span className="block text-[12px] text-muted-foreground">
                                  {acct ? `Connected · ${acct}` : p.sub}
                                </span>
                              </span>
                            </span>
                            <span className="shrink-0 text-[12.5px] font-semibold">
                              {connecting === p.id ? <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                                : acct ? <span className="inline-flex items-center gap-1 text-emerald"><Check className="h-4 w-4" /> Done</span>
                                : <span className="text-primary">Connect</span>}
                            </span>
                          </button>
                        )
                      })}

                      <p className="text-center text-[12px] text-muted-foreground">
                        You can connect or change these anytime in <span className="text-foreground/80">Connections</span>.
                      </p>
                    </div>
                  )}
                </motion.div>

              {error && (
                <div className="mt-4 rounded-xl border border-destructive/40 bg-destructive/10 px-4 py-3 text-[13px] font-medium text-destructive">
                  {error}
                </div>
              )}

              {/* nav */}
              <div className="mt-7 flex items-center gap-2">
                <button
                  onClick={() => setStep((s) => s - 1)}
                  className="inline-flex items-center gap-1.5 rounded-full border border-border px-4 py-2.5 text-[13px] font-medium text-foreground/85 transition-colors hover:bg-white/[0.04]"
                >
                  <ArrowLeft className="h-3.5 w-3.5" /> Back
                </button>
                <div className="flex-1" />
                {step < 5 ? (
                  <button
                    disabled={!canAdvance()}
                    onClick={() => setStep((s) => s + 1)}
                    className="group inline-flex items-center gap-2 rounded-full bg-primary px-6 py-2.5 text-[14px] font-semibold text-primary-foreground shadow-[0_0_30px_-8px_rgba(255,77,0,0.7)] transition-transform hover:scale-[1.02] disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:scale-100"
                  >
                    Next <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
                  </button>
                ) : step === 5 ? (
                  <button
                    disabled={loading}
                    onClick={() => (created ? setStep(6) : handleCreate())}
                    className="group inline-flex items-center gap-2 rounded-full bg-primary px-6 py-2.5 text-[14px] font-semibold text-primary-foreground shadow-[0_0_30px_-8px_rgba(255,77,0,0.7)] transition-transform hover:scale-[1.02] disabled:opacity-60"
                  >
                    {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />}
                    {loading ? "Creating…" : created ? "Continue" : "Create & continue"}
                  </button>
                ) : (
                  <button
                    onClick={() => navigate("/command")}
                    className="inline-flex items-center gap-2 rounded-full bg-primary px-6 py-2.5 text-[14px] font-semibold text-primary-foreground shadow-[0_0_30px_-8px_rgba(255,77,0,0.7)] transition-transform hover:scale-[1.02]"
                  >
                    <Check className="h-4 w-4" /> {anyConnected ? "Enter command center" : "Skip for now"}
                  </button>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* bottom progress bar */}
      <div className="absolute inset-x-0 bottom-0 z-10 px-7 pb-7">
        <div className="mx-auto flex max-w-6xl items-center gap-4">
          <span className="shrink-0 text-[12px] font-medium text-muted-foreground">
            Step <span className="text-primary">{step + 1}</span> of {N}
          </span>
          <div className="flex flex-1 items-center gap-1.5">
            {STEP_TITLES.map((_, i) => (
              <div
                key={i}
                className={cn("h-1 flex-1 rounded-full transition-colors", i <= step ? "bg-primary" : "bg-white/10")}
              />
            ))}
          </div>
          <span className="hidden shrink-0 text-[12px] text-muted-foreground sm:block">Let's build your command center.</span>
        </div>
      </div>
    </div>
  )
}
