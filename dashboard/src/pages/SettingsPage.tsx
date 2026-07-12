/**
 * Settings — owner-facing spend cap + per-platform publish policy (route "/settings").
 * Both controls are brand-owner preferences, not admin/super-admin controls
 * (unlike the agent trust-dial on the Team page) — any authenticated brand
 * member can set these. Ported from the GC Cleanroom Prototype comparison:
 * cleanroom exposed both as plain editable Settings controls; GC had the
 * underlying enforcement (paid_ops cap, manual-publish fallback) but neither
 * was per-brand or visible to the owner until now.
 */
import { useState, useEffect } from "react"
import { Camera, Briefcase, Loader2 } from "lucide-react"
import { cn } from "@/lib/utils"
import {
  usePublishPolicy, useSetPublishPolicy, type PublishLevel,
  useCostCap, useSetCostCap,
  useWhiteLabel, useSetWhiteLabel, type WhiteLabel,
} from "@/hooks/useGridApi"

const PLATFORM_META: Record<string, { name: string; icon: typeof Camera }> = {
  instagram: { name: "Instagram", icon: Camera },
  linkedin: { name: "LinkedIn", icon: Briefcase },
}

function SectionSkeleton({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-2 rounded-xl border border-border bg-white/[0.02] px-4 py-3 text-[12.5px] text-muted-foreground">
      <Loader2 className="h-3.5 w-3.5 animate-spin" /> {label}
    </div>
  )
}

function SectionError({ label }: { label: string }) {
  return (
    <div className="rounded-xl border border-destructive/30 bg-destructive/5 px-4 py-3 text-[12.5px] text-destructive">
      Couldn't load {label}. Try reloading the page.
    </div>
  )
}

function PublishPolicySection() {
  const { data, isLoading, isError } = usePublishPolicy()
  const setLevel = useSetPublishPolicy()

  const header = (
    <>
      <h2 className="mb-1 text-[15px] font-semibold text-foreground">Publishing</h2>
      <p className="mb-4 text-[12.5px] leading-relaxed text-muted-foreground">
        Default is <span className="font-medium text-foreground">manual</span>: the team prepares every post,
        you post it. Assisted auto-publishes the moment a platform's connection is live — nothing changes about
        the approval gate either way, this only governs the step after you've already approved something.
      </p>
    </>
  )

  if (isLoading) return <div>{header}<SectionSkeleton label="publishing settings…" /></div>
  if (isError || !data) return <div>{header}<SectionError label="publishing settings" /></div>

  const editablePlatforms = Object.keys(PLATFORM_META).filter((p) => !data.locked_manual.includes(p))

  return (
    <div>
      {header}
      <div className="space-y-2">
        {editablePlatforms.map((platform) => {
          const meta = PLATFORM_META[platform]
          const level = data.settings[platform] || data.default_level
          return (
            <div key={platform} className="flex items-center justify-between rounded-xl border border-border bg-white/[0.02] px-4 py-3">
              <div className="flex items-center gap-2.5">
                <meta.icon className="h-4 w-4 text-muted-foreground" />
                <span className="text-[13.5px] font-medium text-foreground">{meta.name}</span>
              </div>
              <div className="flex overflow-hidden rounded-lg border border-border">
                {(data.levels as PublishLevel[]).map((l) => (
                  <button
                    key={l}
                    onClick={() => setLevel.mutate({ platform, level: l })}
                    disabled={setLevel.isPending}
                    className={cn(
                      "px-3 py-1.5 text-[12px] font-medium capitalize transition-colors",
                      level === l ? "bg-emerald text-[#06120E]" : "bg-transparent text-muted-foreground hover:text-foreground",
                    )}
                  >
                    {l}
                  </button>
                ))}
              </div>
            </div>
          )
        })}
        {data.locked_manual.length > 0 && (
          <div className="flex items-center justify-between rounded-xl border border-border bg-white/[0.02] px-4 py-3 opacity-70">
            <span className="text-[13.5px] font-medium text-foreground">X / Twitter</span>
            <span className="rounded-lg border border-border px-3 py-1.5 text-[12px] font-medium text-muted-foreground">
              Manual only — standing policy
            </span>
          </div>
        )}
      </div>
    </div>
  )
}

function CostCapSection() {
  const { data, isLoading, isError } = useCostCap()
  const setCap = useSetCostCap()
  const [draft, setDraft] = useState("")

  useEffect(() => {
    if (data) setDraft(String(data.daily_cap_usd))
  }, [data?.daily_cap_usd])

  const header = (
    <>
      <h2 className="mb-1 text-[15px] font-semibold text-foreground">Spending cap</h2>
      <p className="mb-4 text-[12.5px] leading-relaxed text-muted-foreground">
        A hard daily limit on what the team may spend doing paid work for this brand. If the cap is hit — or the
        check itself fails — everything stops and waits for you. It never fails open.
      </p>
    </>
  )

  if (isLoading) return <div>{header}<SectionSkeleton label="spending cap…" /></div>
  if (isError || !data) return <div>{header}<SectionError label="spending cap" /></div>

  const pct = data.daily_cap_usd > 0 ? Math.min(100, (data.spent_today_usd / data.daily_cap_usd) * 100) : 0

  return (
    <div>
      {header}
      <div className="rounded-xl border border-border bg-white/[0.02] p-4">
        <div className="mb-3 flex items-center justify-between text-[12.5px]">
          <span className="text-muted-foreground">
            Spent today: <span className="font-medium text-foreground">${data.spent_today_usd.toFixed(2)}</span> of
            {" "}${data.daily_cap_usd.toFixed(2)}
          </span>
          {!data.enabled && (
            <span className="rounded-full bg-white/[0.06] px-2 py-0.5 text-[10.5px] font-medium uppercase tracking-wide text-muted-foreground">
              paid ops off
            </span>
          )}
        </div>
        <div className="mb-4 h-1.5 w-full overflow-hidden rounded-full bg-white/[0.06]">
          <div
            className={cn("h-full rounded-full", pct >= 100 ? "bg-destructive" : "bg-emerald")}
            style={{ width: `${pct}%` }}
          />
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[12.5px] text-muted-foreground">Daily cap (USD)</span>
          <input
            type="number"
            min={0.01}
            step={0.5}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            className="w-24 rounded-lg border border-border bg-white/[0.02] px-2 py-1 text-[12.5px] text-foreground focus:outline-none focus:ring-1 focus:ring-primary/40"
          />
          <button
            onClick={() => {
              const val = parseFloat(draft)
              if (!isNaN(val) && val > 0) setCap.mutate({ daily_usd_cap: val })
            }}
            disabled={setCap.isPending}
            className="rounded-lg bg-emerald px-3 py-1 text-[12px] font-semibold text-[#06120E] transition-[filter] hover:brightness-110 disabled:opacity-50"
          >
            Save
          </button>
          {!data.is_override && (
            <span className="text-[11px] text-muted-foreground">using the account-wide default</span>
          )}
        </div>
      </div>
    </div>
  )
}

const WL_FIELDS: { key: keyof WhiteLabel; label: string; placeholder: string }[] = [
  { key: "brand_name", label: "Brand name", placeholder: "Acme Agency" },
  { key: "logo_url", label: "Logo URL", placeholder: "https://…/logo.svg" },
  { key: "accent", label: "Accent colour (hex)", placeholder: "#22d3ee" },
  { key: "support_email", label: "Support email", placeholder: "team@acme.com" },
  { key: "custom_domain", label: "Custom domain", placeholder: "app.acme.com" },
]

function WhiteLabelSection() {
  const { data, isLoading, isError } = useWhiteLabel()
  const save = useSetWhiteLabel()
  const [draft, setDraft] = useState<WhiteLabel>({})

  useEffect(() => {
    if (data) setDraft(data)
  }, [data])

  const header = (
    <>
      <h2 className="mb-1 text-[15px] font-semibold text-foreground">White-label branding</h2>
      <p className="mb-4 text-[12.5px] leading-relaxed text-muted-foreground">
        Reselling this brand's workspace? Put your own name, logo and accent on it. Leave a field
        blank to fall back to the default Grid Control branding. (Pricing and seat management are set
        with Gaurav — this only controls what the client sees.)
      </p>
    </>
  )

  if (isLoading) return <div>{header}<SectionSkeleton label="branding…" /></div>
  if (isError) return <div>{header}<SectionError label="branding" /></div>

  return (
    <div>
      {header}
      <div className="space-y-3 rounded-xl border border-border bg-white/[0.02] p-4">
        {WL_FIELDS.map((f) => (
          <label key={f.key} className="flex items-center gap-3 text-[12.5px]">
            <span className="w-36 shrink-0 text-muted-foreground">{f.label}</span>
            <input
              type={f.key === "accent" ? "text" : "text"}
              value={draft[f.key] ?? ""}
              placeholder={f.placeholder}
              onChange={(e) => setDraft((d) => ({ ...d, [f.key]: e.target.value }))}
              className="flex-1 rounded-lg border border-border bg-white/[0.02] px-2 py-1 text-foreground focus:outline-none focus:ring-1 focus:ring-primary/40"
            />
          </label>
        ))}
        <div className="flex items-center gap-3 pt-1">
          <button
            onClick={() => save.mutate(draft)}
            disabled={save.isPending}
            className="rounded-lg bg-emerald px-3 py-1 text-[12px] font-semibold text-[#06120E] transition-[filter] hover:brightness-110 disabled:opacity-50"
          >
            {save.isPending ? "Saving…" : "Save branding"}
          </button>
          {save.isError && <span className="text-[11px] text-destructive">{(save.error as Error)?.message || "Save failed"}</span>}
          {draft.accent && (
            <span className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
              <span className="h-3.5 w-3.5 rounded-full border border-border" style={{ background: draft.accent }} /> preview
            </span>
          )}
        </div>
      </div>
    </div>
  )
}

export function SettingsPage() {
  return (
    <div className="flex h-full flex-col overflow-auto bg-background/60 px-6 py-6">
      <div className="mx-auto w-full max-w-lg space-y-8">
        <div>
          <h1 className="font-display text-[24px] font-semibold tracking-tight text-foreground">Settings</h1>
          <p className="mt-1 text-[13px] text-muted-foreground">How your team publishes and spends, on your terms.</p>
        </div>
        <PublishPolicySection />
        <CostCapSection />
        <WhiteLabelSection />
      </div>
    </div>
  )
}
