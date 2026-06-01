/**
 * Carousel composer — the "create your first carousel" bar at the top of the cockpit.
 * Type a topic (or leave blank to pull the next calendar slot), hit Generate. Calls the
 * real /api/carousel/generate (Carousel Designer + Playwright). On success the carousel
 * lands in the review queue (pending_approval/carousel-designer) for human approval.
 */
import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { Images, Loader2, ArrowRight } from "lucide-react"
import { useGenerateCarousel } from "@/hooks/useGridApi"
import { Card, STATUS } from "./primitives"

export function CarouselComposer() {
  const navigate = useNavigate()
  const gen = useGenerateCarousel()
  const [topic, setTopic] = useState("")
  const [done, setDone] = useState<null | { slides: number }>(null)
  const [error, setError] = useState<string | null>(null)

  const run = () => {
    setDone(null)
    setError(null)
    gen.mutate(
      { topic: topic.trim() || undefined, slides: 7, platform: "instagram" },
      {
        onSuccess: (r) => {
          if (r.success) {
            const n = r.data?.slides?.length ?? r.data?.slide_count ?? 7
            setDone({ slides: n })
            setTopic("")
          } else {
            setError(r.error || "Generation failed")
          }
        },
        onError: (e) => setError(e instanceof Error ? e.message : String(e)),
      },
    )
  }

  const busy = gen.isPending

  return (
    <Card className="mb-5 p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="flex items-center gap-2.5 sm:w-44 sm:shrink-0">
          <span
            className="grid h-8 w-8 place-items-center rounded-lg"
            style={{
              background: "color-mix(in oklab, var(--accent) 22%, #15161a)",
              border: "1px solid color-mix(in oklab, var(--accent) 35%, transparent)",
            }}
          >
            <Images size={16} style={{ color: "var(--accent)" }} />
          </span>
          <div className="leading-tight">
            <div className="text-[13.5px] font-semibold text-zinc-100">Create a carousel</div>
            <div className="font-mono text-[10.5px] text-zinc-600">7 slides · Instagram</div>
          </div>
        </div>

        <input
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !busy && run()}
          disabled={busy}
          placeholder="Topic for the carousel… (leave blank to use your next calendar slot)"
          className="min-w-0 flex-1 rounded-lg border border-white/[0.09] bg-[#0e0f12] px-3.5 py-2.5 text-[13.5px] text-zinc-100 placeholder:text-zinc-600 focus:border-white/[0.18] focus:outline-none disabled:opacity-60"
        />

        <button
          onClick={run}
          disabled={busy}
          className="inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-[13px] font-semibold text-white transition-[filter] hover:brightness-110 disabled:opacity-50 sm:shrink-0"
          style={{ background: "var(--accent)" }}
        >
          {busy ? <Loader2 size={15} className="animate-spin" /> : <Images size={15} />}
          {busy ? "Generating… (~45s)" : "Generate carousel"}
        </button>
      </div>

      {done && (
        <button
          onClick={() => navigate("/review")}
          className="mt-3 flex w-full items-center justify-between rounded-lg border px-3.5 py-2.5 text-left transition-colors"
          style={{ borderColor: STATUS.green.bd, background: STATUS.green.bg }}
        >
          <span className="text-[12.5px] font-medium" style={{ color: STATUS.green.fg }}>
            Carousel generated ({done.slides} slides) — review &amp; approve it
          </span>
          <ArrowRight size={15} style={{ color: STATUS.green.fg }} />
        </button>
      )}

      {error && (
        <div
          className="mt-3 rounded-lg border px-3.5 py-2.5 text-[12.5px] font-medium"
          style={{ borderColor: STATUS.red.bd, background: STATUS.red.bg, color: STATUS.red.fg }}
        >
          {error}
        </div>
      )}
    </Card>
  )
}
