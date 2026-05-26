import { useState, useMemo } from "react";
import { ChevronLeft, ChevronRight, X } from "lucide-react";
import { cn, formatTime } from "@/lib/utils";
import { type CalendarPost } from "@/data/mock";
import type { Platform, AgentStatus } from "@/store/appStore";
import { StatusDot } from "@/components/ui/status-dot";
import { PlatformIcon } from "@/components/ui/platform-icon";
import { Button } from "@/components/ui/button";
import { usePendingOutputs } from "@/hooks/useGridApi";

const PLATFORMS: Platform[] = ["x", "instagram", "linkedin", "tiktok", "youtube"];

function inferPlatform(filename: string, agent: string): Platform {
  const hay = `${filename} ${agent}`.toLowerCase();
  if (hay.includes("instagram") || hay.includes("ig")) return "instagram";
  if (hay.includes("linkedin") || hay.includes("li_") || hay.includes("li.")) return "linkedin";
  if (hay.includes("tiktok") || hay.includes("tt_") || hay.includes("tt.")) return "tiktok";
  if (hay.includes("youtube") || hay.includes("yt_") || hay.includes("yt.")) return "youtube";
  return "x";
}

export function CalendarPage() {
  const [currentDate, setCurrentDate] = useState(new Date());
  const [selectedPlatforms, setSelectedPlatforms] = useState<Platform[]>(PLATFORMS);
  const [selectedDay, setSelectedDay] = useState<Date | null>(null);

  const { data: pending } = usePendingOutputs();

  const calendarPosts: CalendarPost[] = useMemo(() => {
    const items = pending?.outputs ?? [];
    return items
      .filter((o) => !!o.scheduled_for)
      .map((o) => ({
        id: o.filename,
        platform: inferPlatform(o.filename, o.agent_slug),
        caption: o.caption || o.preview || "(no caption)",
        scheduledTime: new Date(o.scheduled_for!),
        status: "queued" as AgentStatus,
      }));
  }, [pending]);

  const year = currentDate.getFullYear();
  const month = currentDate.getMonth();

  const firstDayOfMonth = new Date(year, month, 1);
  const lastDayOfMonth = new Date(year, month + 1, 0);
  const startingDayOfWeek = firstDayOfMonth.getDay();
  const daysInMonth = lastDayOfMonth.getDate();

  const togglePlatform = (platform: Platform) => {
    setSelectedPlatforms((prev) =>
      prev.includes(platform)
        ? prev.filter((p) => p !== platform)
        : [...prev, platform]
    );
  };

  const getPostsForDay = (day: number) => {
    return calendarPosts.filter((post) => {
      const postDate = new Date(post.scheduledTime);
      return (
        postDate.getDate() === day &&
        postDate.getMonth() === month &&
        postDate.getFullYear() === year &&
        selectedPlatforms.includes(post.platform)
      );
    });
  };

  const prevMonth = () => {
    setCurrentDate(new Date(year, month - 1, 1));
  };

  const nextMonth = () => {
    setCurrentDate(new Date(year, month + 1, 1));
  };

  const monthName = currentDate.toLocaleString("default", { month: "long" });

  const selectedDayPosts = selectedDay
    ? calendarPosts.filter((post) => {
        const postDate = new Date(post.scheduledTime);
        return (
          postDate.getDate() === selectedDay.getDate() &&
          postDate.getMonth() === selectedDay.getMonth() &&
          postDate.getFullYear() === selectedDay.getFullYear() &&
          selectedPlatforms.includes(post.platform)
        );
      })
    : [];

  return (
    <div className="flex h-full">
      {/* Calendar */}
      <div className="flex-1 p-6 overflow-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-4">
            <h1 className="text-xl font-semibold">
              {monthName} {year}
            </h1>
            <div className="flex items-center gap-1">
              <Button variant="ghost" size="sm" onClick={prevMonth}>
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <Button variant="ghost" size="sm" onClick={nextMonth}>
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>

          {/* Platform filters */}
          <div className="flex items-center gap-2">
            {PLATFORMS.map((platform) => (
              <button
                key={platform}
                onClick={() => togglePlatform(platform)}
                className={cn(
                  "flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs transition-colors",
                  selectedPlatforms.includes(platform)
                    ? "border-primary bg-primary/10 text-foreground"
                    : "border-border text-muted-foreground hover:bg-secondary"
                )}
              >
                <PlatformIcon platform={platform} className="h-3 w-3" />
                <span className="capitalize">{platform}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Calendar Grid */}
        <div className="rounded-lg border border-border bg-card overflow-hidden">
          {/* Weekday headers */}
          <div className="grid grid-cols-7 border-b border-border bg-secondary/30">
            {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((day) => (
              <div
                key={day}
                className="px-2 py-2 text-xs font-medium text-muted-foreground text-center"
              >
                {day}
              </div>
            ))}
          </div>

          {/* Days */}
          <div className="grid grid-cols-7">
            {/* Empty cells for days before start of month */}
            {Array.from({ length: startingDayOfWeek }).map((_, i) => (
              <div
                key={`empty-${i}`}
                className="min-h-24 border-b border-r border-border bg-secondary/20"
              />
            ))}

            {/* Day cells */}
            {Array.from({ length: daysInMonth }).map((_, i) => {
              const day = i + 1;
              const posts = getPostsForDay(day);
              const isToday =
                day === new Date().getDate() &&
                month === new Date().getMonth() &&
                year === new Date().getFullYear();

              return (
                <div
                  key={day}
                  onClick={() => setSelectedDay(new Date(year, month, day))}
                  className={cn(
                    "min-h-24 p-2 border-b border-r border-border cursor-pointer hover:bg-secondary/50 transition-colors",
                    isToday && "bg-primary/5"
                  )}
                >
                  <span
                    className={cn(
                      "inline-flex h-6 w-6 items-center justify-center rounded-full text-xs",
                      isToday && "bg-primary text-primary-foreground font-medium"
                    )}
                  >
                    {day}
                  </span>
                  <div className="mt-1 space-y-1">
                    {posts.slice(0, 3).map((post) => (
                      <PostTile key={post.id} post={post} compact />
                    ))}
                    {posts.length > 3 && (
                      <span className="text-[10px] text-muted-foreground">
                        +{posts.length - 3} more
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Day Detail Drawer */}
      {selectedDay && (
        <div className="w-80 border-l border-border bg-background flex flex-col">
          <div className="flex items-center justify-between border-b border-border px-4 py-3">
            <span className="text-sm font-medium">
              {selectedDay.toLocaleDateString("en-US", {
                weekday: "long",
                month: "short",
                day: "numeric",
              })}
            </span>
            <button
              onClick={() => setSelectedDay(null)}
              className="text-muted-foreground hover:text-foreground transition-colors"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
          <div className="flex-1 overflow-auto p-4 space-y-3">
            {selectedDayPosts.length === 0 ? (
              <div className="text-center py-8">
                <p className="text-sm text-muted-foreground">
                  No posts scheduled for this day.
                </p>
              </div>
            ) : (
              selectedDayPosts.map((post) => (
                <PostTile key={post.id} post={post} />
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function PostTile({ post, compact = false }: { post: CalendarPost; compact?: boolean }) {
  if (compact) {
    return (
      <div className="flex items-center gap-1 rounded bg-secondary/50 px-1.5 py-0.5">
        <PlatformIcon platform={post.platform} className="h-2.5 w-2.5" />
        <span className="text-[10px] truncate flex-1">{post.caption}</span>
        <StatusDot status={post.status} className="h-1.5 w-1.5" />
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-border bg-card p-3 hover:bg-secondary/50 transition-colors">
      <div className="flex items-center gap-2 mb-2">
        <PlatformIcon platform={post.platform} className="h-4 w-4" />
        <span className="text-xs font-mono text-muted-foreground">
          {formatTime(post.scheduledTime)}
        </span>
        <StatusDot status={post.status} className="ml-auto" />
      </div>
      <p className="text-sm line-clamp-2">{post.caption}</p>
    </div>
  );
}
