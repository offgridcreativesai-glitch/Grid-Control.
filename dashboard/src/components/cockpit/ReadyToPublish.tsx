/**
 * Ready to Publish — approved carousels waiting to go live on Instagram.
 * Pulls approved-but-unposted items (status "scheduled") from /api/published, and lets
 * the operator publish each via the real Graph API (/api/publish/instagram).
 *
 * Honest dual-mode UX, driven by real token liveness:
 *   - token live  → "Publish to Instagram" posts for real, shows the permalink.
 *   - token blocked → publish prepares hosted slides + caption for manual posting.
 */
import { useState } from "react"
import { Send, Loader2, ExternalLink, Check, Copy } from "lucide-react"
import {
  usePublishedPosts,
  usePublishInstagram,
  usePublishCheck,
  type PublishResult,
  type PublishedPost,
} from "@/hooks/useGridApi"
import { Card, ModuleHeader, Eyebrow, STATUS } from "./primitives"

function fileNameOf(p: PublishedPost): string {
  return (p.filepath || "").split("/").pop() || ""
}

function isCarousel(p: PublishedPost): boolean {
  const f = fileNameOf(p).toLowerCase()
  return f.includes("carousel") || (p.slide_images?.length ?? 0) > 0
}

function PublishRow({ post }: { post: PublishedPost }) {
  const publish = usePublishInstagram()
  const [result, setResult] = useState<PublishResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  const go = () => {
    setResult(null)
    setError(null)
    publish.mutate(fileNameOf(post), {
      onSuccess: (r) => (r.success && r.data ? setResult(r.data) : setError(r.error || "Publish failed")),
      onError: (e) => setError(e instanceof Error ? e.message : String(e)),
    })
  }

  const busy = publish.isPending

  return (
    <li className="rounded-xl border border-white/[0.06] bg-white/[0.015] p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="truncate text-[13.5px] font-medium text-zinc-100">
            {post.title || post.post_id || "Carousel"}
          </div>
          <div className="mt-0.5 font-mono text-[10.5px] text-zinc-600">
            {(post.slide_images?.length ?? 0)} slides · instagram
          </div>
        </div>
        {!result && (
          <button
            onClick={go}
            disabled={busy}
            className="inline-flex shrink-0 items-center gap-1.5 rounded-lg px-3 py-1.5 text-[12.5px] font-semibold text-white transition-[filter] hover:brightness-110 disabled:opacity-50"
            style={{ background: "var(--accent)" }}
          >
            {busy ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
            {busy ? "Publishing…" : "Publish to Instagram"}
          </button>
        )}
      </div>

      {post.caption && !result && (
        <p className="mt-2.5 line-clamp-2 text-[12.5px] leading-relaxed text-zinc-400">{post.caption}</p>
      )}

      {result?.mode === "published" && (
        <div
          className="mt-3 flex items-center justify-between gap-2 rounded-lg border px-3 py-2.5"
          style={{ borderColor: STATUS.green.bd, background: STATUS.green.bg }}
        >
          <span className="flex items-center gap-2 text-[12.5px] font-medium" style={{ color: STATUS.green.fg }}>
            <Check size={14} /> Live on Instagram
          </span>
          {result.permalink && (
            <a
              href={result.permalink}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 text-[12px] font-medium underline"
              style={{ color: STATUS.green.fg }}
            >
              View post <ExternalLink size={12} />
            </a>
          )}
        </div>
      )}

      {result?.mode === "prepared" && (
        <div
          className="mt-3 rounded-lg border px-3 py-2.5"
          style={{ borderColor: STATUS.amber.bd, background: STATUS.amber.bg }}
        >
          <div className="text-[12.5px] font-medium" style={{ color: STATUS.amber.fg }}>
            Slides hosted &amp; caption ready — post manually (token not live: {result.reason})
          </div>
          {result.caption && (
            <button
              onClick={() => {
                navigator.clipboard.writeText(result.caption || "")
                setCopied(true)
                setTimeout(() => setCopied(false), 1500)
              }}
              className="mt-2 inline-flex items-center gap-1.5 text-[11.5px] font-medium text-zinc-300 hover:text-white"
            >
              {copied ? <Check size={12} /> : <Copy size={12} />} {copied ? "Caption copied" : "Copy caption"}
            </button>
          )}
          <div className="mt-2 space-y-0.5">
            {(result.slide_urls || []).map((u, i) => (
              <a
                key={i}
                href={u}
                target="_blank"
                rel="noreferrer"
                className="block truncate font-mono text-[10.5px] text-zinc-500 hover:text-zinc-300"
              >
                slide {i + 1}: {u}
              </a>
            ))}
          </div>
        </div>
      )}

      {error && (
        <div
          className="mt-3 rounded-lg border px-3 py-2.5 text-[12px] font-medium"
          style={{ borderColor: STATUS.red.bd, background: STATUS.red.bg, color: STATUS.red.fg }}
        >
          {error}
        </div>
      )}
    </li>
  )
}

export function ReadyToPublish() {
  const { data } = usePublishedPosts()
  const { data: check } = usePublishCheck()

  const ready = (data?.data ?? []).filter((p) => p.status === "scheduled" && isCarousel(p))

  if (ready.length === 0) return null // nothing approved-and-unposted → hide the module

  return (
    <Card className="mt-5 p-6">
      <ModuleHeader
        title="Ready to Publish"
        sub={`${ready.length} approved · awaiting post`}
        right={
          <Eyebrow className="mt-1">
            {check?.live ? `auto · @${check.username}` : "token not live"}
          </Eyebrow>
        }
      />
      <ul className="mt-5 space-y-3">
        {ready.map((p) => (
          <PublishRow key={p.id || p.post_id} post={p} />
        ))}
      </ul>
    </Card>
  )
}
