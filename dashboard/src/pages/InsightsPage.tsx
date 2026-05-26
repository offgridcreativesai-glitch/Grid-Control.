import { useState, useMemo } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { cn, formatNumber, formatDelta, formatTimeAgo } from "@/lib/utils";
import type { Platform } from "@/store/appStore";
import { StatusDot } from "@/components/ui/status-dot";
import { PlatformIcon } from "@/components/ui/platform-icon";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { usePerformanceHistory } from "@/hooks/useGridApi";

const PLATFORMS: (Platform | "all")[] = ["all", "x", "instagram", "linkedin", "tiktok", "youtube"];

interface PerfPost {
  id?: string
  post_id?: string
  platform?: string
  caption?: string
  impressions?: number
  engagements?: number
  saves?: number
  posted_at?: string
}

function inferPlat(p?: string): Platform {
  if (!p) return "x"
  const v = p.toLowerCase()
  if (v.includes("instagram") || v === "ig") return "instagram"
  if (v.includes("linkedin") || v === "li") return "linkedin"
  if (v.includes("tiktok") || v === "tt") return "tiktok"
  if (v.includes("youtube") || v === "yt") return "youtube"
  return "x"
}

export function InsightsPage() {
  const [selectedPlatform, setSelectedPlatform] = useState<Platform | "all">("all");
  const [sortBy, setSortBy] = useState<"impressions" | "engagements" | "saves">("impressions");

  const { data: perfData } = usePerformanceHistory();
  const history: any = perfData?.history ?? {};

  const posts: PerfPost[] = Array.isArray(history.posts) ? history.posts : [];
  const winningPatterns: string[] = useMemo(() => {
    const wp = history.winning_patterns ?? {};
    const out: string[] = [];
    for (const arr of [wp.hook_patterns_top_3, wp.topic_clusters_top_3, wp.formats_top_3]) {
      if (Array.isArray(arr)) {
        for (const item of arr) {
          if (typeof item === "string") out.push(item);
          else if (item?.label) out.push(item.label);
          else if (item?.name) out.push(item.name);
          else if (item?.pattern) out.push(item.pattern);
        }
      }
    }
    return out;
  }, [history]);

  const deadPatterns: string[] = useMemo(() => {
    const dp = history.dead_patterns ?? [];
    if (!Array.isArray(dp)) return [];
    return dp
      .map((d: any) => (typeof d === "string" ? d : d?.label || d?.name || d?.pattern || ""))
      .filter(Boolean);
  }, [history]);

  // KPIs derived from posts
  const totalImpressions = posts.reduce((s, p) => s + (p.impressions ?? 0), 0);
  const totalEngagements = posts.reduce((s, p) => s + (p.engagements ?? 0), 0);
  const totalSaves = posts.reduce((s, p) => s + (p.saves ?? 0), 0);
  const saveRate = totalImpressions > 0 ? (totalSaves / totalImpressions) * 100 : 0;

  const insightKpis = [
    { label: "Impressions", value: totalImpressions, unit: "", delta: 0 },
    { label: "Engagements", value: totalEngagements, unit: "", delta: 0 },
    { label: "Followers", value: Number(history.followers_total ?? 0), unit: "", delta: Number(history.followers_delta ?? 0) },
    { label: "Save rate", value: saveRate, unit: "%", delta: 0 },
  ];

  // Charts derived from posts (or empty if none)
  const followerData = useMemo(() => {
    if (posts.length === 0) return [];
    return posts
      .filter((p) => p.posted_at)
      .map((p) => ({
        date: p.posted_at!,
        value: p.impressions ?? 0,
      }))
      .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
  }, [posts]);

  const engagementData = useMemo(() => {
    return posts
      .filter((p) => p.posted_at && p.impressions)
      .map((p) => ({
        date: p.posted_at!,
        value: ((p.engagements ?? 0) / (p.impressions || 1)) * 100,
      }))
      .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
  }, [posts]);

  const filteredPosts = posts
    .filter((post) => selectedPlatform === "all" || inferPlat(post.platform) === selectedPlatform)
    .map((p) => ({
      id: p.id ?? p.post_id ?? Math.random().toString(),
      platform: inferPlat(p.platform),
      caption: p.caption ?? "(no caption)",
      impressions: p.impressions ?? 0,
      engagements: p.engagements ?? 0,
      saves: p.saves ?? 0,
      postedAt: p.posted_at ? new Date(p.posted_at) : new Date(),
    }))
    .sort((a, b) => (b[sortBy] as number) - (a[sortBy] as number));

  return (
    <div className="p-6 space-y-6 overflow-auto h-full">
      {/* Platform Tabs */}
      <Tabs
        value={selectedPlatform}
        onValueChange={(v) => setSelectedPlatform(v as Platform | "all")}
      >
        <TabsList>
          {PLATFORMS.map((platform) => (
            <TabsTrigger key={platform} value={platform} className="capitalize">
              {platform === "all" ? (
                "All"
              ) : (
                <span className="flex items-center gap-1.5">
                  <PlatformIcon platform={platform} className="h-3.5 w-3.5" />
                  {platform}
                </span>
              )}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>

      {/* KPI Cards */}
      <div className="grid grid-cols-4 gap-4">
        {insightKpis.map((kpi) => (
          <div
            key={kpi.label}
            className="rounded-lg border border-border bg-card p-4"
          >
            <p className="text-xs text-muted-foreground mb-1">{kpi.label}</p>
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-semibold font-mono">
                {kpi.unit ? kpi.value.toFixed(1) + kpi.unit : formatNumber(kpi.value)}
              </span>
              {kpi.delta !== 0 && (
                <span
                  className={cn(
                    "text-xs font-mono",
                    kpi.delta >= 0 ? "text-primary" : "text-destructive",
                  )}
                >
                  {formatDelta(kpi.delta)} 30d
                </span>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Charts */}
      <div className="grid grid-cols-2 gap-6">
        <div className="rounded-lg border border-border bg-card p-4">
          <h3 className="text-sm font-medium mb-4">Follower growth (30d)</h3>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={followerData}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 10, fill: "var(--muted-foreground)" }}
                tickFormatter={(v) => new Date(v).getDate().toString()}
                stroke="var(--border)"
              />
              <YAxis
                tick={{ fontSize: 10, fill: "var(--muted-foreground)" }}
                tickFormatter={(v) => formatNumber(v)}
                stroke="var(--border)"
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "var(--card)",
                  border: "1px solid var(--border)",
                  borderRadius: "8px",
                  fontSize: "12px",
                }}
                labelStyle={{ color: "var(--muted-foreground)" }}
              />
              <Line
                type="monotone"
                dataKey="value"
                stroke="var(--primary)"
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="rounded-lg border border-border bg-card p-4">
          <h3 className="text-sm font-medium mb-4">Engagement rate (30d)</h3>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={engagementData}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 10, fill: "var(--muted-foreground)" }}
                tickFormatter={(v) => new Date(v).getDate().toString()}
                stroke="var(--border)"
              />
              <YAxis
                tick={{ fontSize: 10, fill: "var(--muted-foreground)" }}
                tickFormatter={(v) => v.toFixed(1) + "%"}
                stroke="var(--border)"
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "var(--card)",
                  border: "1px solid var(--border)",
                  borderRadius: "8px",
                  fontSize: "12px",
                }}
                formatter={(value: unknown) => [Number(value).toFixed(2) + "%", "Rate"]}
                labelStyle={{ color: "var(--muted-foreground)" }}
              />
              <Line
                type="monotone"
                dataKey="value"
                stroke="var(--chart-2)"
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Top Posts */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-medium">Top posts</h3>
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">Sort by:</span>
            {(["impressions", "engagements", "saves"] as const).map((sort) => (
              <button
                key={sort}
                onClick={() => setSortBy(sort)}
                className={cn(
                  "text-xs capitalize transition-colors",
                  sortBy === sort
                    ? "text-foreground font-medium"
                    : "text-muted-foreground hover:text-foreground"
                )}
              >
                {sort}
              </button>
            ))}
          </div>
        </div>

        <div className="rounded-lg border border-border bg-card overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border bg-secondary/30">
                <th className="px-4 py-2 text-left text-xs font-medium text-muted-foreground">
                  Post
                </th>
                <th className="px-4 py-2 text-right text-xs font-medium text-muted-foreground">
                  Impressions
                </th>
                <th className="px-4 py-2 text-right text-xs font-medium text-muted-foreground">
                  Engagements
                </th>
                <th className="px-4 py-2 text-right text-xs font-medium text-muted-foreground">
                  Saves
                </th>
                <th className="px-4 py-2 text-right text-xs font-medium text-muted-foreground">
                  Posted
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {filteredPosts.map((post) => (
                <tr key={post.id} className="hover:bg-secondary/30 transition-colors">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <PlatformIcon platform={post.platform} className="h-4 w-4" />
                      <span className="text-sm line-clamp-1">{post.caption}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right text-sm font-mono text-muted-foreground">
                    {formatNumber(post.impressions)}
                  </td>
                  <td className="px-4 py-3 text-right text-sm font-mono text-muted-foreground">
                    {formatNumber(post.engagements)}
                  </td>
                  <td className="px-4 py-3 text-right text-sm font-mono text-muted-foreground">
                    {formatNumber(post.saves)}
                  </td>
                  <td className="px-4 py-3 text-right text-sm font-mono text-muted-foreground">
                    {formatTimeAgo(post.postedAt)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Patterns */}
      <div className="grid grid-cols-2 gap-6">
        <div className="rounded-lg border border-border bg-card p-4">
          <h3 className="text-sm font-medium mb-3">Winning patterns</h3>
          {winningPatterns.length === 0 ? (
            <p className="text-xs text-muted-foreground italic">
              Performance Tracker hasn&apos;t detected patterns yet. Ship 5+ posts and re-run.
            </p>
          ) : (
            <ul className="space-y-2">
              {winningPatterns.map((pattern, i) => (
                <li key={i} className="flex items-start gap-2">
                  <StatusDot status="success" className="mt-1.5" />
                  <span className="text-sm text-muted-foreground italic">
                    {pattern}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="rounded-lg border border-border bg-card p-4">
          <h3 className="text-sm font-medium mb-3">Dead patterns</h3>
          {deadPatterns.length === 0 ? (
            <p className="text-xs text-muted-foreground italic">
              No dead patterns yet.
            </p>
          ) : (
            <ul className="space-y-2">
              {deadPatterns.map((pattern, i) => (
                <li key={i} className="flex items-start gap-2">
                  <StatusDot status="error" className="mt-1.5" />
                  <span className="text-sm text-muted-foreground italic line-through">
                    {pattern}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
