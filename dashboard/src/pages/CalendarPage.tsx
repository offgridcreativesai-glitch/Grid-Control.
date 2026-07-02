/**
 * Brand Engine — everything the brand has planned + scheduled (route "/calendar").
 * Real data: scheduled pending outputs. Client-safe (no slugs / models).
 */
import { useState, useMemo } from "react"
import { ChevronLeft, ChevronRight, X } from "lucide-react"
import { cn, formatTime } from "@/lib/utils"
import { type CalendarPost } from "@/data/mock"
import type { Platform, AgentStatus } from "@/store/appStore"
import { StatusDot } from "@/components/ui/status-dot"
import { PlatformIcon } from "@/components/ui/platform-icon"
import { usePendingOutputs } from "@/hooks/useGridApi"
import { useBrandStore } from "@/store/brandStore"

const PLATFORMS: Platform[] = ["x", "instagram", "linkedin", "tiktok", "youtube"]

function inferPlatform(filename: string, agent: string): Platform {
  const hay = `${filename} ${agent}`.toLowerCase()
  if (hay.includes("instagram") || hay.includes("ig")) return "instagram"
  if (hay.includes("linkedin") || hay.includes("li_") || hay.includes("li.")) return "linkedin"
  if (hay.includes("tiktok") || hay.includes("tt_") || hay.includes("tt.")) return "tiktok"
  if (hay.includes("youtube") || hay.includes("yt_") || hay.includes("yt.")) return "youtube"
  return "x"
}

export function CalendarPage() {
  const { activeBrand } = useBrandStore()
  const [currentDate, setCurrentDate] = useState(new Date())
  const [selectedPlatforms, setSelectedPlatforms] = useState<Platform[]>(PLATFORMS)
  const [selectedDay, setSelectedDay] = useState<Date | null>(null)

  const { data: pending } = usePendingOutputs()

  const calendarPosts: CalendarPost[] = useMemo(() => {
    const items = pending?.outputs ?? []
    return items
      .filter((o) => !!o.scheduled_for)
      .map((o) => ({
        id: o.filename,
        platform: inferPlatform(o.filename, o.agent_slug),
        caption: o.caption || o.preview || "(no caption)",
        scheduledTime: new Date(o.scheduled_for!),
        status: "queued" as AgentStatus,
      }))
  }, [pending])

  const year = currentDate.getFullYear()
  const month = currentDate.getMonth()
  const firstDayOfMonth = new Date(year, month, 1)
  const lastDayOfMonth = new Date(year, month + 1, 0)
  const startingDayOfWeek = firstDayOfMonth.getDay()
  const daysInMonth = lastDayOfMonth.getDate()

  const togglePlatform = (platform: Platform) =>
    setSelectedPlatforms((prev) =>
      prev.includes(platform) ? prev.filter((p) => p !== platform) : [...prev, platform],
    )

  const getPostsForDay = (day: number) =>
    calendarPosts.filter((post) => {
      const d = new Date(post.scheduledTime)
      return (
        d.getDate() === day &&
        d.getMonth() === month &&
        d.getFullYear() === year &&
        selectedPlatforms.includes(post.platform)
      )
    })

  const monthName = currentDate.toLocaleString("default", { month: "long" })
  const totalThisMonth = useMemo(
    () =>
      calendarPosts.filter(
        (p) => p.scheduledTime.getMonth() === month && p.scheduledTime.getFullYear() === year,
      ).length,
    [calendarPosts, month, year],
  )

  const selectedDayPosts = selectedDay
    ? calendarPosts.filter((post) => {
        const d = new Date(post.scheduledTime)
        return (
          d.getDate() === selectedDay.getDate() &&
          d.getMonth() === selectedDay.getMonth() &&
          d.getFullYear() === selectedDay.getFullYear() &&
          selectedPlatforms.includes(post.platform)
        )
      })
    : []

  return (
    <div className="flex h-full bg-background/60">
      <div className="flex-1 overflow-auto">
        <div className="mx-auto max-w-[1100px] px-6 pb-16 pt-10">
          {/* Header */}
          <div className="flex items-end justify-between gap-6">
            <div>
              <h1 className="font-display text-[26px] font-semibold tracking-tight text-foreground">Brand engine</h1>
              <p className="mt-1.5 text-[14px] text-muted-foreground">
                Everything planned and scheduled for <span className="text-foreground">{activeBrand.name}</span>.
              </p>
            </div>
            <span className="shrink-0 rounded-full border border-border bg-white/[0.02] px-3.5 py-2 text-[12px] font-medium text-foreground/80">
              {totalThisMonth} scheduled in {monthName}
            </span>
          </div>

          {/* Month nav + platform filters */}
          <div className="mt-7 flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <h2 className="font-display text-[18px] font-semibold tracking-tight text-foreground">
                {monthName} {year}
              </h2>
              <div className="flex items-center gap-1">
                <button onClick={() => setCurrentDate(new Date(year, month - 1, 1))} className="grid h-8 w-8 place-items-center rounded-lg border border-border text-muted-foreground transition-colors hover:bg-white/[0.04] hover:text-foreground">
                  <ChevronLeft className="h-4 w-4" />
                </button>
                <button onClick={() => setCurrentDate(new Date(year, month + 1, 1))} className="grid h-8 w-8 place-items-center rounded-lg border border-border text-muted-foreground transition-colors hover:bg-white/[0.04] hover:text-foreground">
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              {PLATFORMS.map((platform) => (
                <button
                  key={platform}
                  onClick={() => togglePlatform(platform)}
                  className={cn(
                    "flex items-center gap-1.5 rounded-full border px-3 py-1 text-[12px] capitalize transition-colors",
                    selectedPlatforms.includes(platform)
                      ? "border-emerald/40 bg-emerald/[0.08] text-foreground"
                      : "border-border text-muted-foreground hover:bg-white/[0.04]",
                  )}
                >
                  <PlatformIcon platform={platform} className="h-3 w-3" />
                  {platform}
                </button>
              ))}
            </div>
          </div>

          {/* Grid */}
          <div className="glass-panel mt-6 overflow-hidden rounded-2xl">
            <div className="grid grid-cols-7 border-b border-border">
              {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((day) => (
                <div key={day} className="px-2 py-2.5 text-center text-[11px] font-medium uppercase tracking-[0.1em] text-muted-foreground">
                  {day}
                </div>
              ))}
            </div>

            <div className="grid grid-cols-7">
              {Array.from({ length: startingDayOfWeek }).map((_, i) => (
                <div key={`empty-${i}`} className="min-h-28 border-b border-r border-border bg-black/10" />
              ))}

              {Array.from({ length: daysInMonth }).map((_, i) => {
                const day = i + 1
                const posts = getPostsForDay(day)
                const isToday =
                  day === new Date().getDate() && month === new Date().getMonth() && year === new Date().getFullYear()
                return (
                  <div
                    key={day}
                    onClick={() => setSelectedDay(new Date(year, month, day))}
                    className={cn(
                      "min-h-28 cursor-pointer border-b border-r border-border p-2 transition-colors hover:bg-white/[0.03]",
                      isToday && "bg-primary/[0.06]",
                    )}
                  >
                    <span
                      className={cn(
                        "inline-flex h-6 w-6 items-center justify-center rounded-full text-[12px]",
                        isToday && "bg-primary font-semibold text-primary-foreground",
                      )}
                    >
                      {day}
                    </span>
                    <div className="mt-1 space-y-1">
                      {posts.slice(0, 3).map((post) => (
                        <PostTile key={post.id} post={post} compact />
                      ))}
                      {posts.length > 3 && (
                        <span className="text-[10px] text-muted-foreground">+{posts.length - 3} more</span>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          {totalThisMonth === 0 && (
            <p className="mt-5 text-center text-[13px] text-muted-foreground">
              Nothing scheduled this month yet. Ask Atlas to plan the week and it&rsquo;ll land here.
            </p>
          )}
        </div>
      </div>

      {/* Day drawer */}
      {selectedDay && (
        <div className="flex w-80 shrink-0 flex-col border-l border-border bg-background/60">
          <div className="flex items-center justify-between border-b border-border px-4 py-3.5">
            <span className="text-[13px] font-semibold text-foreground">
              {selectedDay.toLocaleDateString("en-US", { weekday: "long", month: "short", day: "numeric" })}
            </span>
            <button onClick={() => setSelectedDay(null)} className="text-muted-foreground transition-colors hover:text-foreground">
              <X className="h-4 w-4" />
            </button>
          </div>
          <div className="flex-1 space-y-3 overflow-auto p-4">
            {selectedDayPosts.length === 0 ? (
              <p className="py-8 text-center text-[13px] text-muted-foreground">Nothing scheduled for this day.</p>
            ) : (
              selectedDayPosts.map((post) => <PostTile key={post.id} post={post} />)
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function PostTile({ post, compact = false }: { post: CalendarPost; compact?: boolean }) {
  if (compact) {
    return (
      <div className="flex items-center gap-1 rounded-md bg-white/[0.05] px-1.5 py-0.5">
        <PlatformIcon platform={post.platform} className="h-2.5 w-2.5" />
        <span className="flex-1 truncate text-[10px] text-foreground/80">{post.caption}</span>
        <StatusDot status={post.status} className="h-1.5 w-1.5" />
      </div>
    )
  }
  return (
    <div className="glass-panel rounded-xl p-3 transition-colors hover:bg-white/[0.03]">
      <div className="mb-2 flex items-center gap-2">
        <PlatformIcon platform={post.platform} className="h-4 w-4" />
        <span className="text-[11px] text-muted-foreground">{formatTime(post.scheduledTime)}</span>
        <StatusDot status={post.status} className="ml-auto" />
      </div>
      <p className="line-clamp-2 text-[13px] text-foreground/90">{post.caption}</p>
    </div>
  )
}
