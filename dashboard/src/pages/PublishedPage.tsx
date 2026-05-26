import { useState, useMemo } from "react";
import { cn, formatNumber, formatTimeAgo } from "@/lib/utils";
import { PlatformIcon } from "@/components/ui/platform-icon";
import { StatusDot } from "@/components/ui/status-dot";
import { usePublishedPosts, type PublishedPost } from "@/hooks/useGridApi";
import type { Platform } from "@/store/appStore";

const PLATFORMS: (Platform | "all")[] = ["all", "x", "instagram", "linkedin", "tiktok", "youtube"];

function inferPlatform(p: string | null | undefined): Platform {
  if (!p) return "x";
  const v = p.toLowerCase();
  if (v.includes("instagram") || v === "ig") return "instagram";
  if (v.includes("linkedin") || v === "li") return "linkedin";
  if (v.includes("tiktok") || v === "tt") return "tiktok";
  if (v.includes("youtube") || v === "yt") return "youtube";
  return "x";
}

function formatScheduled(iso: string | null): string {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return d.toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

export function PublishedPage() {
  const { data, isLoading } = usePublishedPosts();
  const posts: PublishedPost[] = data?.data ?? [];
  const [filter, setFilter] = useState<Platform | "all">("all");
  const [statusFilter, setStatusFilter] = useState<"all" | "scheduled" | "published">("all");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const filtered = useMemo(() => {
    return posts.filter((p) => {
      if (filter !== "all" && inferPlatform(p.platform) !== filter) return false;
      if (statusFilter !== "all" && p.status !== statusFilter) return false;
      return true;
    });
  }, [posts, filter, statusFilter]);

  // Aggregate engagement totals (only published)
  const totals = useMemo(() => {
    const t = { likes: 0, comments: 0, shares: 0, impressions: 0, saves: 0, posts: 0 };
    for (const p of filtered) {
      if (p.engagement) {
        t.likes += p.engagement.likes;
        t.comments += p.engagement.comments;
        t.shares += p.engagement.shares;
        t.impressions += p.engagement.impressions;
        t.saves += p.engagement.saves;
        t.posts += 1;
      }
    }
    return t;
  }, [filtered]);

  const selected = filtered.find((p) => p.id === selectedId) ?? filtered[0] ?? null;

  return (
    <div className="flex h-full">
      {/* List */}
      <div className="w-[420px] border-r border-border overflow-auto">
        <div className="p-4 border-b border-border space-y-3">
          <div className="flex items-baseline justify-between">
            <h1 className="text-lg font-semibold">Published</h1>
            <span className="text-xs font-mono text-muted-foreground">
              {filtered.length} post{filtered.length === 1 ? "" : "s"}
            </span>
          </div>

          {/* Aggregate KPIs (only meaningful when totals.posts > 0) */}
          {totals.posts > 0 && (
            <div className="grid grid-cols-2 gap-2 pt-1">
              <KPIChip label="Impressions" value={totals.impressions} />
              <KPIChip label="Likes" value={totals.likes} />
              <KPIChip label="Comments" value={totals.comments} />
              <KPIChip label="Shares" value={totals.shares} />
            </div>
          )}

          {/* Platform filter */}
          <div className="flex flex-wrap gap-1 pt-1">
            {PLATFORMS.map((p) => (
              <button
                key={p}
                onClick={() => setFilter(p)}
                className={cn(
                  "rounded-full border px-2.5 py-0.5 text-[10px] capitalize transition-colors",
                  filter === p
                    ? "border-primary bg-primary/10 text-foreground"
                    : "border-border text-muted-foreground hover:bg-secondary",
                )}
              >
                {p === "all" ? "All" : p}
              </button>
            ))}
          </div>

          {/* Status filter */}
          <div className="flex gap-1">
            {(["all", "scheduled", "published"] as const).map((s) => (
              <button
                key={s}
                onClick={() => setStatusFilter(s)}
                className={cn(
                  "rounded-full border px-2.5 py-0.5 text-[10px] capitalize transition-colors",
                  statusFilter === s
                    ? "border-primary bg-primary/10 text-foreground"
                    : "border-border text-muted-foreground hover:bg-secondary",
                )}
              >
                {s}
              </button>
            ))}
          </div>
        </div>

        {isLoading ? (
          <div className="p-8 text-center text-sm text-muted-foreground">Loading…</div>
        ) : filtered.length === 0 ? (
          <div className="p-8 text-center">
            <p className="text-sm font-medium">No published posts yet.</p>
            <p className="text-xs text-muted-foreground mt-1">
              Approve a draft on the Review page — it will land here.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-border">
            {filtered.map((p) => (
              <button
                key={p.id}
                onClick={() => setSelectedId(p.id)}
                className={cn(
                  "w-full px-4 py-3 text-left hover:bg-secondary/50 transition-colors",
                  selected?.id === p.id && "bg-secondary",
                )}
              >
                <div className="flex items-center gap-2 mb-1">
                  <PlatformIcon platform={inferPlatform(p.platform)} className="h-3.5 w-3.5" />
                  <span className="text-xs text-muted-foreground capitalize">
                    {p.platform || "—"}
                  </span>
                  <StatusDot
                    status={p.status === "published" ? "success" : "queued"}
                    className="ml-auto"
                  />
                </div>
                <p className="text-sm font-medium line-clamp-1">
                  {p.title || p.caption?.slice(0, 60) || "(untitled)"}
                </p>
                <div className="mt-1 flex items-center justify-between text-[10px] font-mono text-muted-foreground">
                  <span>
                    {p.status === "scheduled"
                      ? `scheduled ${formatScheduled(p.scheduled_for)}`
                      : p.posted_at
                        ? `posted ${formatTimeAgo(new Date(p.posted_at))}`
                        : `approved ${formatTimeAgo(new Date(p.approved_at))}`}
                  </span>
                  {p.engagement && (
                    <span>
                      ♥ {formatNumber(p.engagement.likes)} · 💬 {formatNumber(p.engagement.comments)}
                    </span>
                  )}
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Detail */}
      {selected && (
        <div className="flex-1 overflow-auto">
          <div className="max-w-2xl mx-auto p-6 space-y-6">
            <div className="flex items-center gap-3">
              <PlatformIcon platform={inferPlatform(selected.platform)} className="h-5 w-5" />
              <span className="text-sm font-medium capitalize">{selected.platform || "—"}</span>
              <span className="text-xs text-muted-foreground">· {selected.agent_slug}</span>
              <StatusDot
                status={selected.status === "published" ? "success" : "queued"}
                className="ml-auto"
              />
              <span className="text-xs font-mono text-muted-foreground capitalize">
                {selected.status}
              </span>
            </div>

            {selected.title && (
              <h2 className="text-lg font-semibold">{selected.title}</h2>
            )}

            {selected.slide_images && selected.slide_images.length > 0 && (
              <div className="rounded-lg border border-border bg-card overflow-hidden">
                <div className="aspect-square overflow-x-auto flex snap-x snap-mandatory">
                  {selected.slide_images.map((path, i) => (
                    <img
                      key={path}
                      src={`/api/outputs/media/${path}`}
                      alt={`Slide ${i + 1}`}
                      className="h-full w-full flex-shrink-0 object-contain snap-center"
                      onError={(e) => {
                        (e.currentTarget as HTMLImageElement).style.display = "none";
                      }}
                    />
                  ))}
                </div>
              </div>
            )}

            {selected.caption && (
              <div>
                <h3 className="text-xs font-medium text-muted-foreground mb-2">Caption</h3>
                <p className="text-sm whitespace-pre-wrap">{selected.caption}</p>
              </div>
            )}

            {selected.body_text && selected.body_text !== selected.caption && (
              <div>
                <h3 className="text-xs font-medium text-muted-foreground mb-2">Body</h3>
                <p className="text-sm whitespace-pre-wrap">{selected.body_text}</p>
              </div>
            )}

            {selected.hashtags && selected.hashtags.length > 0 && (
              <div>
                <h3 className="text-xs font-medium text-muted-foreground mb-2">Hashtags</h3>
                <div className="flex flex-wrap gap-1">
                  {selected.hashtags.map((tag) => (
                    <span key={tag} className="text-xs text-primary">
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Schedule + posted timestamps */}
            <div className="rounded-lg border border-border bg-card p-4 grid grid-cols-3 gap-4 text-xs">
              <div>
                <div className="text-muted-foreground mb-1">Scheduled for</div>
                <div className="font-mono">{formatScheduled(selected.scheduled_for)}</div>
              </div>
              <div>
                <div className="text-muted-foreground mb-1">Approved</div>
                <div className="font-mono">{formatTimeAgo(new Date(selected.approved_at))}</div>
              </div>
              <div>
                <div className="text-muted-foreground mb-1">Posted</div>
                <div className="font-mono">
                  {selected.posted_at ? formatTimeAgo(new Date(selected.posted_at)) : "not yet"}
                </div>
              </div>
            </div>

            {/* Engagement */}
            {selected.engagement ? (
              <div>
                <h3 className="text-xs font-medium text-muted-foreground mb-2">Engagement</h3>
                <div className="grid grid-cols-5 gap-3">
                  <EngagementStat label="Impressions" value={selected.engagement.impressions} />
                  <EngagementStat label="Likes" value={selected.engagement.likes} />
                  <EngagementStat label="Comments" value={selected.engagement.comments} />
                  <EngagementStat label="Shares" value={selected.engagement.shares} />
                  <EngagementStat label="Saves" value={selected.engagement.saves} />
                </div>
              </div>
            ) : (
              <div className="rounded-lg border border-border bg-card p-4 text-xs text-muted-foreground italic">
                No engagement data yet. POST metrics to{" "}
                <span className="font-mono">/api/performance/log-post</span> with{" "}
                <span className="font-mono">post_id={selected.post_id}</span> once the post
                is published.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function KPIChip({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded border border-border bg-card px-2 py-1.5">
      <div className="text-[9px] uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className="text-sm font-mono font-medium">{formatNumber(value)}</div>
    </div>
  );
}

function EngagementStat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border border-border bg-card p-3">
      <div className="text-[10px] text-muted-foreground mb-0.5">{label}</div>
      <div className="text-base font-mono font-semibold">{formatNumber(value)}</div>
    </div>
  );
}
