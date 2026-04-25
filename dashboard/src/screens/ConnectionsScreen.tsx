/**
 * ConnectionsScreen — GRID CONTROL Screen 7
 * Manage and authenticate all social media platform connections.
 * Shows real-time status, stores tokens to .env via backend, and
 * provides step-by-step guides for obtaining each platform's token.
 */

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import {
  CheckCircle2, XCircle, AlertTriangle, Eye, EyeOff,
  ChevronDown, ChevronUp, RefreshCw, Loader2, Copy, Check,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { apiFetch } from "@/lib/api"
import type { ApiResponse } from "@/types"

// ── Types ──────────────────────────────────────────────────────────────────────

interface PlatformStatus {
  connected: boolean
  account: string
}

interface ConnectionsData {
  meta:      PlatformStatus
  linkedin:  PlatformStatus
  youtube:   PlatformStatus
  twitter:   PlatformStatus
  whatsapp:  PlatformStatus
}

// ── Platform definitions ───────────────────────────────────────────────────────

interface PlatformDef {
  id:          string
  label:       string
  handle:      string
  handleNote?: string
  statusKey:   keyof ConnectionsData
  tokenLabel:  string
  tokenHint:   string
  pending?:    boolean           // API approval in progress
  steps:       string[]
  docsUrl:     string
  icon:        React.ReactNode
}

const PLATFORMS: PlatformDef[] = [
  {
    id:         "instagram",
    label:      "Instagram",
    handle:     "@AskGauravAI",
    statusKey:  "meta",
    tokenLabel: "Meta Graph API Token",
    tokenHint:  "EAA... (User Access Token from Meta Developers)",
    steps: [
      "Go to developers.facebook.com and log in",
      "Click 'My Apps' → Create App → Business type",
      "Add the 'Instagram Basic Display' product to your app",
      "Under Instagram Basic Display → Basic Display, click 'Generate Token'",
      "Add yourself as a test user and generate a token",
      "Paste that token here — agents will use it to pull your post data & analytics",
    ],
    docsUrl: "https://developers.facebook.com/docs/instagram-basic-display-api",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" className="w-5 h-5" stroke="currentColor" strokeWidth="1.8">
        <rect x="2" y="2" width="20" height="20" rx="5"/>
        <circle cx="12" cy="12" r="4"/>
        <circle cx="17.5" cy="6.5" r="1" fill="currentColor" stroke="none"/>
      </svg>
    ),
  },
  {
    id:         "linkedin",
    label:      "LinkedIn",
    handle:     "In approval",
    handleNote: "LinkedIn API access is pending approval — handle will be set once approved",
    statusKey:  "linkedin",
    tokenLabel: "LinkedIn Access Token",
    tokenHint:  "AQV... (OAuth 2.0 Bearer Token from LinkedIn Developers)",
    pending:    true,
    steps: [
      "Your LinkedIn API application is currently in the approval process",
      "Once LinkedIn approves your app, go to linkedin.com/developers",
      "Open your app → Auth → OAuth 2.0 tokens",
      "Generate a 3-legged OAuth token with r_liteprofile + w_member_social scopes",
      "Paste the Bearer token here",
      "Handle will be updated once the company page is live",
    ],
    docsUrl: "https://learn.microsoft.com/en-us/linkedin/shared/authentication/authorization-code-flow",
    icon: (
      <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
        <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
      </svg>
    ),
  },
  {
    id:         "youtube",
    label:      "YouTube",
    handle:     "@AskGauravAI",
    statusKey:  "youtube",
    tokenLabel: "YouTube Data API Key",
    tokenHint:  "AIzaSy... (API Key from Google Cloud Console)",
    steps: [
      "Go to console.cloud.google.com and sign in with your Google account",
      "Create a new project (or use an existing one) → Enable APIs & Services",
      "Search for 'YouTube Data API v3' → Enable it",
      "Go to Credentials → Create Credentials → API Key",
      "Copy the generated key — no OAuth needed for reading public channel data",
      "Paste it here — agents will use it to pull video performance and subscriber data",
    ],
    docsUrl: "https://developers.google.com/youtube/v3/getting-started",
    icon: (
      <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
        <path d="M23.495 6.205a3.007 3.007 0 00-2.088-2.088c-1.87-.501-9.396-.501-9.396-.501s-7.507-.01-9.396.501A3.007 3.007 0 00.527 6.205a31.247 31.247 0 00-.522 5.805 31.247 31.247 0 00.522 5.783 3.007 3.007 0 002.088 2.088c1.868.502 9.396.502 9.396.502s7.506 0 9.396-.502a3.007 3.007 0 002.088-2.088 31.247 31.247 0 00.5-5.783 31.247 31.247 0 00-.5-5.805zM9.609 15.601V8.408l6.264 3.602z"/>
      </svg>
    ),
  },
  {
    id:         "twitter",
    label:      "Twitter / X",
    handle:     "@AskGauravAI",
    statusKey:  "twitter",
    tokenLabel: "Twitter Bearer Token",
    tokenHint:  "AAAA... (Bearer Token from Twitter Developer Portal)",
    steps: [
      "Go to developer.twitter.com and sign in",
      "Click 'Projects & Apps' → Create a new project and app",
      "Under your app → Keys and Tokens → Bearer Token",
      "Click 'Regenerate' to get a fresh Bearer Token",
      "Paste it here — agents will use it for tweet analytics and engagement data",
      "Note: Free tier allows read-only access to public data",
    ],
    docsUrl: "https://developer.twitter.com/en/docs/authentication/oauth-2-0/bearer-tokens",
    icon: (
      <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
        <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
      </svg>
    ),
  },
  {
    id:         "whatsapp",
    label:      "WhatsApp",
    handle:     "+91 91045 02898",
    statusKey:  "whatsapp",
    tokenLabel: "WhatsApp Business Access Token",
    tokenHint:  "EAA... (Temporary or Permanent token from Meta for Developers)",
    steps: [
      "Go to developers.facebook.com → Your App → WhatsApp → API Setup",
      "You'll see a temporary access token — copy it for testing",
      "For production: go to Business Manager → System Users → Generate permanent token",
      "Ensure your WhatsApp Business Account is linked to the app",
      "Paste the token here — agents will use it to send broadcasts and track engagement",
      "Note: Production use requires submitting for Meta's WhatsApp API review",
    ],
    docsUrl: "https://developers.facebook.com/docs/whatsapp/cloud-api/get-started",
    icon: (
      <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
        <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/>
      </svg>
    ),
  },
]

// ── Data fetching ──────────────────────────────────────────────────────────────

async function fetchConnections(): Promise<ConnectionsData> {
  const res  = await apiFetch("/api/connections/check")
  const json: ApiResponse<ConnectionsData> = await res.json()
  if (!json.success) throw new Error("Failed to fetch connection status")
  return json.data
}

async function saveToken(platform: string, token: string): Promise<void> {
  const res = await apiFetch("/api/connections/save-token", {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify({ platform, token }),
  })
  const json: ApiResponse<unknown> = await res.json()
  if (!json.success) throw new Error((json as unknown as { error: string }).error)
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function StatusBadge({ status, pending }: { status?: PlatformStatus; pending?: boolean }) {
  if (pending && !status?.connected) {
    return (
      <span className="flex items-center gap-1.5" style={{ fontSize: 12 }}>
        <span className="status-dot running" />
        <span className="text-[hsl(var(--gc-amber))]">Pending Approval</span>
      </span>
    )
  }
  if (status?.connected) {
    return (
      <span className="flex items-center gap-1.5" style={{ fontSize: 12 }}>
        <span className="status-dot online" />
        <span className="text-[hsl(var(--gc-green))]">{status.account}</span>
      </span>
    )
  }
  return (
    <span className="flex items-center gap-1.5" style={{ fontSize: 12 }}>
      <span className="status-dot idle" />
      <span className="gc-muted">Not connected</span>
    </span>
  )
}

function GuideStep({ num, text }: { num: number; text: string }) {
  return (
    <div className="flex gap-3">
      <span
        className="flex-shrink-0 flex items-center justify-center rounded-full gc-gold-bg gc-gold-border border"
        style={{ width: 20, height: 20, fontSize: 10, fontWeight: 700, color: "hsl(var(--gc-gold))" }}
      >
        {num}
      </span>
      <p style={{ fontSize: 13 }} className="text-[hsl(var(--gc-text-2))] leading-relaxed">
        {text}
      </p>
    </div>
  )
}

function PlatformCard({
  platform,
  status,
  isRefetching,
}: {
  platform: PlatformDef
  status:   PlatformStatus | undefined
  isRefetching: boolean
}) {
  const qc = useQueryClient()
  const [token,     setToken]     = useState("")
  const [showToken, setShowToken] = useState(false)
  const [guideOpen, setGuideOpen] = useState(false)
  const [copied,    setCopied]    = useState(false)

  const mutation = useMutation({
    mutationFn: () => saveToken(platform.id, token),
    onSuccess: () => {
      setToken("")
      qc.invalidateQueries({ queryKey: ["connections"] })
    },
  })

  const handleCopy = async () => {
    if (!platform.docsUrl) return
    await navigator.clipboard.writeText(platform.docsUrl)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const isConnected  = status?.connected ?? false
  const isPending    = platform.pending && !isConnected
  const canSave      = token.trim().length > 10 && !mutation.isPending

  return (
    <div
      className={cn(
        "gc-card p-5 flex flex-col gap-4 transition-all duration-200",
        isConnected && "border-[rgba(46,204,113,0.2)]",
        isPending   && "border-[rgba(240,165,0,0.2)]",
      )}
    >
      {/* Header row */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          {/* Platform icon */}
          <div
            className={cn(
              "flex items-center justify-center rounded-[8px] flex-shrink-0",
              isConnected ? "text-[hsl(var(--gc-green))]  bg-[rgba(46,204,113,0.08)]  border border-[rgba(46,204,113,0.2)]"
                          : "text-[hsl(var(--gc-text-2))] bg-[hsl(var(--gc-surface2))] border border-[hsl(var(--border))]",
            )}
            style={{ width: 40, height: 40 }}
          >
            {platform.icon}
          </div>
          {/* Name + handle */}
          <div>
            <p style={{ fontSize: 14, fontWeight: 700 }} className="text-[hsl(var(--foreground))]">
              {platform.label}
            </p>
            <p style={{ fontSize: 12 }} className="gc-muted mt-0.5">
              {platform.handle}
              {platform.handleNote && (
                <span className="block mt-0.5 text-[hsl(var(--gc-amber))] opacity-80" style={{ fontSize: 11 }}>
                  {platform.handleNote}
                </span>
              )}
            </p>
          </div>
        </div>
        {/* Status */}
        <div className="flex-shrink-0 pt-0.5">
          {isRefetching
            ? <Loader2 size={14} className="animate-spin gc-muted" />
            : <StatusBadge status={status} pending={platform.pending} />
          }
        </div>
      </div>

      {/* Divider */}
      <div className="border-t border-[hsl(var(--border))]" />

      {/* Token input row */}
      <div className="space-y-2">
        <label style={{ fontSize: 11, fontWeight: 700, letterSpacing: "1.5px", textTransform: "uppercase" }} className="gc-muted block">
          {platform.tokenLabel}
        </label>
        <div className="flex gap-2">
          <div className="relative flex-1">
            <input
              type={showToken ? "text" : "password"}
              value={token}
              onChange={e => setToken(e.target.value)}
              placeholder={isConnected ? "••••••••••••  (token saved)" : platform.tokenHint}
              className={cn(
                "w-full rounded-[6px] border bg-[hsl(var(--gc-surface2))] px-3 pr-9 text-[hsl(var(--foreground))] placeholder-[hsl(var(--gc-text-3))] outline-none transition-colors",
                "focus:border-[rgba(201,168,76,0.5)] focus:ring-0",
                "border-[hsl(var(--border))]",
              )}
              style={{ height: 36, fontSize: 13, fontFamily: "monospace" }}
            />
            <button
              type="button"
              onClick={() => setShowToken(v => !v)}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 gc-muted hover:text-[hsl(var(--foreground))] transition-colors"
            >
              {showToken ? <EyeOff size={13} /> : <Eye size={13} />}
            </button>
          </div>
          <button
            onClick={() => mutation.mutate()}
            disabled={!canSave}
            className={cn(
              "px-4 rounded-[6px] text-black flex-shrink-0 flex items-center gap-1.5 transition-opacity",
              canSave
                ? "bg-[hsl(var(--gc-gold))] hover:opacity-85"
                : "bg-[hsl(var(--gc-surface2))] border border-[hsl(var(--border))] text-[hsl(var(--gc-text-3))] cursor-not-allowed",
            )}
            style={{ height: 36, fontSize: 12, fontWeight: 700 }}
          >
            {mutation.isPending
              ? <><Loader2 size={12} className="animate-spin" /> Saving</>
              : mutation.isSuccess && !token
              ? <><Check size={12} /> Saved</>
              : "Save"
            }
          </button>
        </div>

        {/* Feedback */}
        {mutation.isError && (
          <p className="flex items-center gap-1.5 text-[hsl(var(--gc-red))]" style={{ fontSize: 12 }}>
            <XCircle size={12} />
            {(mutation.error as Error).message}
          </p>
        )}
        {mutation.isSuccess && !token && (
          <p className="flex items-center gap-1.5 text-[hsl(var(--gc-green))]" style={{ fontSize: 12 }}>
            <CheckCircle2 size={12} />
            Token saved. Run the connection check to verify.
          </p>
        )}
        {isPending && !token && (
          <p className="flex items-center gap-1.5 text-[hsl(var(--gc-amber))]" style={{ fontSize: 12 }}>
            <AlertTriangle size={12} />
            Waiting for LinkedIn API approval — you can paste the token as soon as it arrives.
          </p>
        )}
      </div>

      {/* How-to guide toggle */}
      <button
        onClick={() => setGuideOpen(v => !v)}
        className="flex items-center justify-between w-full text-left gc-muted hover:text-[hsl(var(--foreground))] transition-colors"
        style={{ fontSize: 12 }}
      >
        <span style={{ fontWeight: 600 }}>How to get your {platform.tokenLabel}</span>
        {guideOpen ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
      </button>

      {guideOpen && (
        <div className="space-y-3 pt-1">
          {platform.steps.map((step, i) => (
            <GuideStep key={i} num={i + 1} text={step} />
          ))}
          <div className="flex items-center gap-2 pt-1">
            <button
              onClick={handleCopy}
              className="flex items-center gap-1.5 gc-gold-bg gc-gold-border border rounded px-3 py-1.5 gc-gold hover:opacity-80 transition-opacity"
              style={{ fontSize: 11, fontWeight: 600 }}
            >
              {copied ? <Check size={11} /> : <Copy size={11} />}
              {copied ? "Copied!" : "Copy docs URL"}
            </button>
            <span className="gc-dimmed" style={{ fontSize: 11, fontFamily: "monospace" }}>
              {platform.docsUrl.replace("https://", "")}
            </span>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Main Screen ────────────────────────────────────────────────────────────────

export function ConnectionsScreen() {
  const qc = useQueryClient()

  const {
    data:      connections,
    isFetching,
    isError,
  } = useQuery({
    queryKey:  ["connections"],
    queryFn:   fetchConnections,
    staleTime: 30_000,
  })

  const totalConnected = connections
    ? PLATFORMS.filter(p => connections[p.statusKey]?.connected).length
    : 0

  return (
    <div className="p-8 max-w-3xl mx-auto space-y-8">

      {/* Page header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 800, letterSpacing: "-0.5px" }} className="text-[hsl(var(--foreground))]">
            Connections
          </h1>
          <p className="gc-muted mt-1" style={{ fontSize: 14 }}>
            Connect your social accounts so agents can pull real data and act on your behalf.
          </p>
        </div>
        <button
          onClick={() => qc.invalidateQueries({ queryKey: ["connections"] })}
          disabled={isFetching}
          className="flex items-center gap-1.5 gc-muted hover:text-[hsl(var(--foreground))] transition-colors disabled:opacity-50 flex-shrink-0"
          style={{ fontSize: 12 }}
        >
          <RefreshCw size={12} className={cn(isFetching && "animate-spin")} />
          Run Check
        </button>
      </div>

      {/* Status bar */}
      <div className="gc-card p-4 flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div
            className={cn(
              "w-2.5 h-2.5 rounded-full flex-shrink-0",
              totalConnected === PLATFORMS.length
                ? "bg-[hsl(var(--gc-green))] shadow-[0_0_8px_hsl(var(--gc-green)/50%)]"
                : totalConnected > 0
                ? "bg-[hsl(var(--gc-amber))] shadow-[0_0_8px_hsl(var(--gc-amber)/50%)]"
                : "bg-[hsl(var(--gc-text-3))]"
            )}
          />
          <span style={{ fontSize: 13, fontWeight: 600 }} className="text-[hsl(var(--foreground))]">
            {totalConnected} / {PLATFORMS.length} platforms connected
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          {PLATFORMS.map(p => {
            const ok = connections?.[p.statusKey]?.connected
            return (
              <div
                key={p.id}
                title={p.label}
                className={cn(
                  "w-2 h-2 rounded-full",
                  ok ? "bg-[hsl(var(--gc-green))]" : p.pending ? "bg-[hsl(var(--gc-amber))]" : "bg-[hsl(var(--gc-text-3))]"
                )}
              />
            )
          })}
        </div>
      </div>

      {/* Error state */}
      {isError && (
        <div className="gc-card border-[rgba(231,76,60,0.3)] p-4 flex items-center gap-3">
          <XCircle size={16} className="text-[hsl(var(--gc-red))] flex-shrink-0" />
          <p style={{ fontSize: 13 }} className="text-[hsl(var(--gc-red))]">
            Could not reach the API — make sure the Flask server is running on port 5001.
          </p>
        </div>
      )}

      {/* Platform cards */}
      <div className="space-y-4">
        {PLATFORMS.map(platform => (
          <PlatformCard
            key={platform.id}
            platform={platform}
            status={connections?.[platform.statusKey]}
            isRefetching={isFetching}
          />
        ))}
      </div>

      {/* Footer note */}
      <div className="gc-card p-4 flex items-start gap-3 border-[rgba(201,168,76,0.15)]">
        <div className="w-1.5 h-1.5 rounded-full bg-[hsl(var(--gc-gold))] flex-shrink-0 mt-1.5" />
        <p className="gc-muted" style={{ fontSize: 12, lineHeight: 1.7 }}>
          All tokens are stored in your local <span className="font-mono text-[hsl(var(--foreground))]">.env</span> file and never sent to any third party.
          Tokens are only used by agents running on your machine. Each platform's "How to get your token" guide
          above links to the official developer documentation.
        </p>
      </div>
    </div>
  )
}
