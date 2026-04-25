/**
 * SystemSpace — Space 5
 * API keys, live connections, cost tracker.
 * Visited rarely — monthly maintenance.
 */

import { useState } from "react"
import { useQuery, useMutation } from "@tanstack/react-query"
import {
  Wifi, WifiOff, CheckCircle2, XCircle, Key,
  Loader2, RefreshCw, Eye, EyeOff, Save,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { apiFetch } from "@/lib/api"
import { useBrandStore } from "@/store/brandStore"
import type { ApiResponse } from "@/types"

// ── Types ──────────────────────────────────────────────────────────────────────

interface ConnectionStatus {
  connected: boolean
  account:   string
}

interface KeyStatus {
  anthropic:   boolean
  elevenlabs:  boolean
  notion:      boolean
  fal:         boolean
  apify:       boolean
  meta:        boolean
}

interface SaveTokenPayload {
  platform: string
  token:    string
}

// ── API helpers ────────────────────────────────────────────────────────────────

async function fetchConnections(): Promise<Record<string, ConnectionStatus>> {
  const res  = await apiFetch("/api/connections/check")
  const json: ApiResponse<Record<string, ConnectionStatus>> = await res.json()
  if (!json.success) return {}
  return json.data
}

async function fetchKeyStatus(): Promise<KeyStatus> {
  const res  = await apiFetch("/api/config/keys")
  const json: ApiResponse<KeyStatus> = await res.json()
  if (!json.success) throw new Error(json.error)
  return json.data
}

async function saveToken(payload: SaveTokenPayload): Promise<void> {
  const res  = await apiFetch("/api/connections/save-token", {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify(payload),
  })
  const json: ApiResponse<unknown> = await res.json()
  if (!json.success) throw new Error(json.error)
}

// ── Platform config ────────────────────────────────────────────────────────────

const PLATFORMS = [
  {
    id:       "instagram",
    label:    "Instagram",
    icon:     "📸",
    envKey:   "INSTAGRAM_ACCESS_TOKEN",
    docUrl:   "https://developers.facebook.com/docs/instagram-api/getting-started",
    docLabel: "Meta for Developers",
    note:     "Requires Meta App Review for public access. Personal token works for testing.",
  },
  {
    id:       "linkedin",
    label:    "LinkedIn",
    icon:     "💼",
    envKey:   "LINKEDIN_ACCESS_TOKEN",
    docUrl:   "https://www.linkedin.com/developers/apps",
    docLabel: "LinkedIn Developer Portal",
    note:     "Create an app → Products → Marketing Developer Platform → Request access.",
    badge:    "Pending Approval",
  },
  {
    id:       "youtube",
    label:    "YouTube",
    icon:     "▶️",
    envKey:   "YOUTUBE_API_KEY",
    docUrl:   "https://console.cloud.google.com/apis/library/youtube.googleapis.com",
    docLabel: "Google Cloud Console",
    note:     "Enable YouTube Data API v3 → Credentials → Create API Key.",
  },
  {
    id:       "twitter",
    label:    "Twitter / X",
    icon:     "𝕏",
    envKey:   "TWITTER_BEARER_TOKEN",
    docUrl:   "https://developer.twitter.com/en/portal/dashboard",
    docLabel: "Twitter Developer Portal",
    note:     "Create project → App → Keys and tokens → Bearer Token.",
  },
  {
    id:       "whatsapp",
    label:    "WhatsApp",
    icon:     "💬",
    envKey:   "WHATSAPP_PHONE_NUMBER",
    docUrl:   "https://business.whatsapp.com/",
    docLabel: "WhatsApp Business",
    note:     "Enter your WhatsApp business number including country code.",
  },
  {
    id:       "notion",
    label:    "Notion",
    icon:     "📋",
    envKey:   "NOTION_API_KEY",
    docUrl:   "https://www.notion.so/my-integrations",
    docLabel: "Notion Integrations",
    note:     "Create integration → copy Internal Integration Token.",
  },
  {
    id:       "apify",
    label:    "Apify",
    icon:     "🕷️",
    envKey:   "APIFY_API_KEY",
    docUrl:   "https://console.apify.com/account/integrations",
    docLabel: "Apify Console",
    note:     "Account Settings → Integrations → Personal API tokens.",
  },
]

// ── Section label ──────────────────────────────────────────────────────────────

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[hsl(var(--gc-text-2))] uppercase tracking-widest font-medium mb-5" style={{ fontSize: 12 }}>
      {children}
    </p>
  )
}

// ── API Key dot ────────────────────────────────────────────────────────────────

function KeyRow({ name, active }: { name: string; active: boolean }) {
  return (
    <div className="flex items-center gap-3 py-2">
      <div className={cn("w-2 h-2 rounded-full shrink-0", active ? "bg-[hsl(var(--gc-green))]" : "bg-[hsl(var(--gc-text-3))]")} />
      <span className="flex-1 font-mono" style={{ fontSize: 13, color: active ? "hsl(var(--foreground))" : "hsl(var(--gc-text-2))" }}>
        {name}
      </span>
      {active
        ? <CheckCircle2 size={14} className="text-[hsl(var(--gc-green))] shrink-0" />
        : <XCircle      size={14} className="text-[hsl(var(--gc-text-3))] shrink-0" />
      }
    </div>
  )
}

// ── Connection row ─────────────────────────────────────────────────────────────

function ConnectionRow({ name, status }: { name: string; status?: ConnectionStatus }) {
  if (!status) return null
  return (
    <div className="flex items-center gap-3 py-2">
      {status.connected
        ? <Wifi    size={14} className="text-[hsl(var(--gc-green))] shrink-0" />
        : <WifiOff size={14} className="text-[hsl(var(--gc-text-3))] shrink-0" />
      }
      <span className="flex-1 font-mono" style={{ fontSize: 13, color: status.connected ? "hsl(var(--foreground))" : "hsl(var(--gc-text-2))" }}>
        {name}
      </span>
      <span className={cn("px-2 py-0.5 rounded border font-mono", status.connected
          ? "text-[hsl(var(--gc-green))] bg-[rgba(46,204,113,0.07)] border-[rgba(46,204,113,0.2)]"
          : "text-[hsl(var(--gc-text-2))] bg-[hsl(var(--gc-surface2))] border-[hsl(var(--border))]")}
        style={{ fontSize: 11 }}>
        {status.account}
      </span>
    </div>
  )
}

// ── Platform token editor ──────────────────────────────────────────────────────

function PlatformCard({ platform }: { platform: typeof PLATFORMS[0] }) {
  const [token, setToken]       = useState("")
  const [show, setShow]         = useState(false)
  const [guideOpen, setGuideOpen] = useState(false)
  const [saved, setSaved]       = useState(false)

  const mutation = useMutation({
    mutationFn: () => saveToken({ platform: platform.id, token: token.trim() }),
    onSuccess: () => { setSaved(true); setToken(""); setTimeout(() => setSaved(false), 3000) },
  })

  return (
    <div className="gc-card rounded-xl p-5 space-y-4">
      <div className="flex items-center gap-3">
        <span style={{ fontSize: 20 }}>{platform.icon}</span>
        <div className="flex-1">
          <p className="text-white font-semibold" style={{ fontSize: 15 }}>{platform.label}</p>
          <p className="text-[hsl(var(--gc-text-2))] font-mono" style={{ fontSize: 12 }}>{platform.envKey}</p>
        </div>
        {platform.badge && (
          <span className="px-2.5 py-1 rounded border font-semibold"
            style={{ fontSize: 11, color: "hsl(var(--gc-amber))", background: "rgba(240,165,0,0.08)", borderColor: "rgba(240,165,0,0.25)" }}>
            {platform.badge}
          </span>
        )}
        {saved && (
          <span className="flex items-center gap-1.5 px-2.5 py-1 rounded border"
            style={{ fontSize: 11, color: "hsl(var(--gc-green))", background: "rgba(46,204,113,0.08)", borderColor: "rgba(46,204,113,0.2)" }}>
            <CheckCircle2 size={11} /> Saved
          </span>
        )}
      </div>

      <div className="flex gap-2">
        <div className="relative flex-1">
          <input
            type={show ? "text" : "password"}
            value={token}
            onChange={e => setToken(e.target.value)}
            placeholder={`Paste ${platform.label} token…`}
            className="w-full rounded-lg px-3 py-2.5 pr-10 focus:outline-none text-white placeholder:text-[hsl(var(--gc-text-3))]"
            style={{ background: "hsl(var(--gc-surface2))", border: "1px solid hsl(var(--border))", fontSize: 13 }}
          />
          <button onClick={() => setShow(!show)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-[hsl(var(--gc-text-2))] hover:text-white transition-colors">
            {show ? <EyeOff size={14} /> : <Eye size={14} />}
          </button>
        </div>
        <button
          onClick={() => mutation.mutate()}
          disabled={!token.trim() || mutation.isPending}
          className="h-10 px-4 rounded-lg font-semibold flex items-center gap-1.5 hover:opacity-85 transition-opacity disabled:opacity-40"
          style={{ fontSize: 13, background: "hsl(var(--gc-gold))", color: "#000" }}>
          {mutation.isPending ? <Loader2 size={13} className="animate-spin" /> : <Save size={13} />}
          Save
        </button>
      </div>

      {mutation.isError && (
        <p style={{ fontSize: 12, color: "hsl(var(--gc-red))" }}>
          {(mutation.error as Error).message}
        </p>
      )}

      <button
        onClick={() => setGuideOpen(!guideOpen)}
        className="text-[hsl(var(--gc-text-2))] hover:text-[hsl(var(--gc-gold))] transition-colors"
        style={{ fontSize: 12 }}>
        {guideOpen ? "▾ Hide guide" : "▸ How to get this token"}
      </button>

      {guideOpen && (
        <div className="rounded-lg p-4 space-y-2"
          style={{ background: "rgba(201,168,76,0.05)", border: "1px solid rgba(201,168,76,0.15)" }}>
          <p className="text-white" style={{ fontSize: 13, lineHeight: 1.6 }}>{platform.note}</p>
          <a href={platform.docUrl} target="_blank" rel="noopener noreferrer"
            className="text-[hsl(var(--gc-gold))] hover:underline" style={{ fontSize: 12 }}>
            → {platform.docLabel} ↗
          </a>
        </div>
      )}
    </div>
  )
}

// ── Root ───────────────────────────────────────────────────────────────────────

export function SystemSpace() {
  useBrandStore()

  const { data: connections, refetch: refetchConnections, isFetching: connFetching } = useQuery({
    queryKey:   ["connections"],
    queryFn:    fetchConnections,
    staleTime:  60000,
    refetchInterval: false,
  })

  const { data: keys, isLoading: keysLoading } = useQuery({
    queryKey: ["key-status"],
    queryFn:  fetchKeyStatus,
    staleTime: 60000,
  })

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Top bar */}
      <div style={{ height: 52, flexShrink: 0 }}
        className="flex items-center px-8 border-b border-[hsl(var(--border))]">
        <div className="flex items-center gap-2">
          <span className="text-[hsl(var(--gc-text-2))]" style={{ fontSize: 13 }}>System</span>
          <span className="text-[hsl(var(--gc-text-2))]" style={{ fontSize: 13 }}>/</span>
          <span className="text-white font-semibold" style={{ fontSize: 14 }}>Connections & Keys</span>
        </div>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto">
        <div className="px-8 pt-8 pb-12 space-y-10" style={{ maxWidth: 820 }}>

          {/* Page title */}
          <div>
            <h1 className="text-white font-bold" style={{ fontSize: 26 }}>System</h1>
            <p className="text-[hsl(var(--gc-text-2))] mt-1" style={{ fontSize: 14 }}>
              API keys, platform connections, and costs. Check monthly.
            </p>
          </div>

          {/* API Keys */}
          <div>
            <SectionTitle><Key size={12} className="inline mr-2 -mt-0.5" />API Keys</SectionTitle>
            <div className="gc-card rounded-xl p-5">
              {keysLoading ? (
                <div className="space-y-2">{[1,2,3,4].map(i => <div key={i} className="h-8 gc-card rounded animate-pulse" />)}</div>
              ) : keys ? (
                <div className="divide-y divide-[hsl(var(--border))]">
                  <KeyRow name="ANTHROPIC_API_KEY"   active={keys.anthropic} />
                  <KeyRow name="NOTION_API_KEY"       active={keys.notion} />
                  <KeyRow name="APIFY_API_KEY"        active={keys.apify} />
                  <KeyRow name="FAL_API_KEY"           active={keys.fal} />
                  <KeyRow name="ELEVENLABS_API_KEY"   active={keys.elevenlabs} />
                  <KeyRow name="META_GRAPH_API_TOKEN" active={keys.meta} />
                </div>
              ) : (
                <p className="text-[hsl(var(--gc-text-2))]" style={{ fontSize: 13 }}>Unable to load key status.</p>
              )}
            </div>
          </div>

          {/* Live Connections */}
          <div>
            <div className="flex items-center justify-between mb-5">
              <SectionTitle><Wifi size={12} className="inline mr-2 -mt-0.5" />Live Connections</SectionTitle>
              <button
                onClick={() => refetchConnections()}
                disabled={connFetching}
                className="flex items-center gap-1.5 text-[hsl(var(--gc-text-2))] hover:text-white transition-colors disabled:opacity-50"
                style={{ fontSize: 12 }}>
                <RefreshCw size={12} className={cn(connFetching && "animate-spin")} />
                Run Check
              </button>
            </div>
            <div className="gc-card rounded-xl p-5">
              {connections ? (
                <div className="divide-y divide-[hsl(var(--border))]">
                  <ConnectionRow name="Anthropic (Claude)" status={connections.anthropic} />
                  <ConnectionRow name="Apify"              status={connections.apify} />
                  <ConnectionRow name="Notion"             status={connections.notion} />
                  <ConnectionRow name="Meta / Instagram"   status={connections.meta} />
                  <ConnectionRow name="ElevenLabs"         status={connections.elevenlabs} />
                  <ConnectionRow name="LinkedIn"           status={connections.linkedin} />
                  <ConnectionRow name="YouTube"            status={connections.youtube} />
                  <ConnectionRow name="Twitter / X"        status={connections.twitter} />
                </div>
              ) : (
                <p className="text-[hsl(var(--gc-text-2))]" style={{ fontSize: 14 }}>
                  Click "Run Check" to test all live connections
                </p>
              )}
            </div>
          </div>

          {/* Platform Tokens */}
          <div>
            <SectionTitle>Platform Tokens</SectionTitle>
            <p className="text-[hsl(var(--gc-text-2))] mb-5" style={{ fontSize: 14 }}>
              Paste access tokens to connect each platform. Tokens are saved to your .env file.
            </p>
            <div className="space-y-4">
              {PLATFORMS.map(p => <PlatformCard key={p.id} platform={p} />)}
            </div>
          </div>

          {/* Cost estimate */}
          <div>
            <SectionTitle>Estimated Costs</SectionTitle>
            <div className="gc-card rounded-xl p-6 space-y-4">
              <div className="grid grid-cols-3 gap-4">
                {[
                  { label: "Claude Sonnet (per agent run)",  value: "~$0.05–0.20",  sub: "Depends on output size" },
                  { label: "Claude Opus (per agent run)",    value: "~$0.30–1.50",  sub: "Strategy / Creative agents" },
                  { label: "Apify scraping",                 value: "~$0.50/month", sub: "1–2 full pipelines" },
                ].map(({ label, value, sub }) => (
                  <div key={label} className="p-4 rounded-lg" style={{ background: "hsl(var(--gc-surface2))", border: "1px solid hsl(var(--border))" }}>
                    <p className="text-white font-bold" style={{ fontSize: 18 }}>{value}</p>
                    <p className="text-[hsl(var(--gc-text-2))] mt-1" style={{ fontSize: 13 }}>{label}</p>
                    <p className="text-[hsl(var(--gc-text-2))] mt-0.5" style={{ fontSize: 12 }}>{sub}</p>
                  </div>
                ))}
              </div>
              <p className="text-[hsl(var(--gc-text-2))] border-t border-[hsl(var(--border))] pt-4" style={{ fontSize: 13, lineHeight: 1.6 }}>
                Full 5-agent pipeline (Trend → Strategy → Content → Script → Creative) for one brand ≈ <strong className="text-[hsl(var(--gc-text-2))]">$2–5</strong> per run.
                Monthly cost for weekly runs ≈ <strong className="text-[hsl(var(--gc-text-2))]">$8–20</strong>. Top up at{" "}
                <a href="https://console.anthropic.com" target="_blank" rel="noopener noreferrer"
                  className="text-[hsl(var(--gc-gold))] hover:underline">console.anthropic.com</a>.
              </p>
            </div>
          </div>

        </div>
      </div>
    </div>
  )
}
