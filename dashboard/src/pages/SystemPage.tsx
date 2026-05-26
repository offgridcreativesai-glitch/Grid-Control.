import { useState } from "react";
import { Eye, EyeOff, RefreshCw } from "lucide-react";
import { cn, formatTimeAgo } from "@/lib/utils";
import { AGENTS } from "@/data/agents";
import type { Platform } from "@/store/appStore";
import { useConnections, useBrandDashboard, useLiveAgents } from "@/hooks/useGridApi";
import { StatusDot } from "@/components/ui/status-dot";
import { PlatformIcon } from "@/components/ui/platform-icon";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Switch } from "@/components/ui/switch";

const PLATFORMS: Platform[] = ["x", "instagram", "linkedin", "tiktok", "youtube"];

export function SystemPage() {
  return (
    <div className="p-6 h-full overflow-auto">
      <div className="mb-6">
        <h1 className="text-xl font-semibold">System</h1>
        <p className="text-sm text-muted-foreground">
          Settings and configuration for GRID CONTROL
        </p>
      </div>

      <Tabs defaultValue="brand" className="w-full">
        <TabsList>
          <TabsTrigger value="brand">Brand</TabsTrigger>
          <TabsTrigger value="connections">Connections</TabsTrigger>
          <TabsTrigger value="autonomy">Agent Autonomy</TabsTrigger>
          <TabsTrigger value="keys">API Keys</TabsTrigger>
          <TabsTrigger value="activity">Activity Log</TabsTrigger>
        </TabsList>

        <TabsContent value="brand" className="mt-6">
          <BrandSettings />
        </TabsContent>

        <TabsContent value="connections" className="mt-6">
          <ConnectionsSettings />
        </TabsContent>

        <TabsContent value="autonomy" className="mt-6">
          <AutonomySettings />
        </TabsContent>

        <TabsContent value="keys" className="mt-6">
          <APIKeysSettings />
        </TabsContent>

        <TabsContent value="activity" className="mt-6">
          <ActivityLogSettings />
        </TabsContent>
      </Tabs>
    </div>
  );
}

function BrandSettings() {
  const { data, isLoading } = useBrandDashboard();
  const profile: any = data?.profile ?? {};

  if (isLoading) {
    return (
      <div className="max-w-2xl text-sm text-muted-foreground italic">Loading brand profile…</div>
    );
  }

  const dnp = profile.do_not_post;
  const dnpStr = Array.isArray(dnp) ? dnp.join(", ") : (dnp || "—");
  const wh = profile.working_hours || {};
  const whStr = wh.start && wh.end ? `${wh.start} - ${wh.end}` : "—";
  const voice = profile.voice_profile || profile.voice || profile.tone_summary || "—";

  return (
    <div className="max-w-2xl space-y-6">
      <div className="rounded-lg border border-border bg-card p-4 space-y-4">
        <div>
          <label className="text-sm font-medium">Brand name</label>
          <p className="text-sm text-muted-foreground mt-1">{profile.brand_name || profile.name || "—"}</p>
        </div>
        <div>
          <label className="text-sm font-medium">Handle</label>
          <p className="text-sm text-muted-foreground mt-1">{profile.handle || "—"}</p>
        </div>
        <div>
          <label className="text-sm font-medium">Voice profile</label>
          <div className="mt-1 rounded-md bg-secondary/50 p-3 text-sm text-muted-foreground font-mono whitespace-pre-wrap">
            {typeof voice === "string" ? voice : JSON.stringify(voice, null, 2)}
          </div>
        </div>
        <div>
          <label className="text-sm font-medium">Target audience</label>
          <p className="text-sm text-muted-foreground mt-1 whitespace-pre-wrap">
            {profile.audience || profile.target_audience || "—"}
          </p>
        </div>
        <div>
          <label className="text-sm font-medium">Do-not-post topics</label>
          <p className="text-sm text-muted-foreground mt-1">{dnpStr}</p>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-sm font-medium">Working hours</label>
            <p className="text-sm text-muted-foreground mt-1">{whStr}</p>
          </div>
          <div>
            <label className="text-sm font-medium">Timezone</label>
            <p className="text-sm text-muted-foreground mt-1">{wh.tz || profile.timezone || "—"}</p>
          </div>
        </div>
      </div>
    </div>
  );
}

const SERVICE_LABELS: Record<string, string> = {
  anthropic: "Anthropic (Claude)",
  apify: "Apify",
  notion: "Notion",
  fal: "FAL.ai",
  elevenlabs: "ElevenLabs",
  supabase: "Supabase",
  meta_graph: "Meta Graph API",
  meta: "Meta Graph API",
  ga4: "Google Analytics 4",
  search_console: "Google Search Console",
  youtube: "YouTube Data API",
  twitter: "Twitter / X API",
};

const PLATFORM_KEYS: Platform[] = ["x", "instagram", "linkedin", "tiktok", "youtube"];

function ConnectionsSettings() {
  const { data, isLoading, refetch, isFetching } = useConnections();
  const conns = data?.data ?? {};

  const serviceEntries = Object.entries(conns).filter(
    ([k]) => !PLATFORM_KEYS.includes(k as Platform),
  );

  return (
    <div className="max-w-2xl space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium">Live status</h3>
        <Button variant="ghost" size="sm" onClick={() => refetch()} disabled={isFetching}>
          <RefreshCw className={cn("h-3 w-3", isFetching && "animate-spin")} />
          <span className="ml-1.5 text-xs">Refresh</span>
        </Button>
      </div>

      {isLoading ? (
        <div className="rounded-lg border border-border bg-card px-4 py-8 text-center text-sm text-muted-foreground">
          Checking connections…
        </div>
      ) : serviceEntries.length === 0 ? (
        <div className="rounded-lg border border-border bg-card px-4 py-8 text-center text-sm text-muted-foreground">
          No service status returned. Is the Flask backend running?
        </div>
      ) : (
        <div>
          <h3 className="text-sm font-medium mb-3">Services</h3>
          <div className="rounded-lg border border-border bg-card divide-y divide-border">
            {serviceEntries.map(([key, info]) => (
              <ConnectionRow
                key={key}
                name={SERVICE_LABELS[key] ?? key}
                connected={info.connected}
                account={info.account}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function ConnectionRow({ name, connected, account }: { name: string; connected: boolean; account: string }) {
  return (
    <div className="flex items-center justify-between px-4 py-3">
      <div className="flex items-center gap-3">
        <div className="flex h-5 w-5 items-center justify-center rounded bg-secondary text-[10px] font-medium">
          {name.slice(0, 2).toUpperCase()}
        </div>
        <span className="text-sm">{name}</span>
      </div>
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <StatusDot status={connected ? "success" : "error"} />
          <span className="text-xs text-muted-foreground">
            {connected ? "Connected" : "Not connected"}
          </span>
        </div>
        <span className="text-xs font-mono text-muted-foreground truncate max-w-[200px]">
          {account}
        </span>
      </div>
    </div>
  );
}

function AutonomySettings() {
  const [settings, setSettings] = useState<
    Record<Platform, { maxPosts: number; autoApprove: boolean }>
  >({
    x: { maxPosts: 4, autoApprove: false },
    instagram: { maxPosts: 2, autoApprove: false },
    linkedin: { maxPosts: 1, autoApprove: false },
    tiktok: { maxPosts: 2, autoApprove: true },
    youtube: { maxPosts: 1, autoApprove: false },
  });

  const updateMaxPosts = (platform: Platform, delta: number) => {
    setSettings((prev) => ({
      ...prev,
      [platform]: {
        ...prev[platform],
        maxPosts: Math.max(0, Math.min(10, prev[platform].maxPosts + delta)),
      },
    }));
  };

  const toggleAutoApprove = (platform: Platform) => {
    setSettings((prev) => ({
      ...prev,
      [platform]: {
        ...prev[platform],
        autoApprove: !prev[platform].autoApprove,
      },
    }));
  };

  return (
    <div className="max-w-2xl">
      <div className="rounded-lg border border-border bg-card overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-border bg-secondary/30">
              <th className="px-4 py-2 text-left text-xs font-medium text-muted-foreground">
                Platform
              </th>
              <th className="px-4 py-2 text-center text-xs font-medium text-muted-foreground">
                Max posts/day
              </th>
              <th className="px-4 py-2 text-center text-xs font-medium text-muted-foreground">
                Auto-approve
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {PLATFORMS.map((platform) => (
              <tr key={platform}>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <PlatformIcon platform={platform} className="h-4 w-4" />
                    <span className="text-sm capitalize">{platform}</span>
                  </div>
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center justify-center gap-2">
                    <button
                      onClick={() => updateMaxPosts(platform, -1)}
                      className="flex h-6 w-6 items-center justify-center rounded border border-border hover:bg-secondary transition-colors"
                    >
                      -
                    </button>
                    <span className="w-8 text-center font-mono text-sm">
                      {settings[platform].maxPosts}
                    </span>
                    <button
                      onClick={() => updateMaxPosts(platform, 1)}
                      className="flex h-6 w-6 items-center justify-center rounded border border-border hover:bg-secondary transition-colors"
                    >
                      +
                    </button>
                  </div>
                </td>
                <td className="px-4 py-3">
                  <div className="flex justify-center">
                    <Switch
                      checked={settings[platform].autoApprove}
                      onCheckedChange={() => toggleAutoApprove(platform)}
                    />
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function APIKeysSettings() {
  const [visibleKeys, setVisibleKeys] = useState<Record<string, boolean>>({});

  const keys = [
    { name: "ANTHROPIC_API_KEY", value: "sk-ant-api03-xxxxxxxxxxxxxxxxxxxxx" },
    { name: "OPENAI_API_KEY", value: "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" },
    { name: "SUPABASE_KEY", value: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xxxxx" },
    { name: "FAL_KEY", value: "fal-xxxxxxxxxxxxxxxxxxxxxxxxxxxx" },
    { name: "APIFY_TOKEN", value: "apify_api_xxxxxxxxxxxxxxxxxxxx" },
    { name: "META_ACCESS_TOKEN", value: "EAAG...xxxxxxxxxxxxxxxxxxxxx" },
  ];

  const toggleVisibility = (name: string) => {
    setVisibleKeys((prev) => ({ ...prev, [name]: !prev[name] }));
  };

  const maskKey = (value: string) => {
    return "•".repeat(value.length - 4) + value.slice(-4);
  };

  return (
    <div className="max-w-2xl">
      <div className="rounded-lg border border-border bg-card divide-y divide-border">
        {keys.map((key) => (
          <div
            key={key.name}
            className="flex items-center justify-between px-4 py-3"
          >
            <span className="text-sm font-mono">{key.name}</span>
            <div className="flex items-center gap-3">
              <span className="text-sm font-mono text-muted-foreground">
                {visibleKeys[key.name] ? key.value : maskKey(key.value)}
              </span>
              <button
                onClick={() => toggleVisibility(key.name)}
                className="text-muted-foreground hover:text-foreground transition-colors"
              >
                {visibleKeys[key.name] ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ActivityLogSettings() {
  const [filter, setFilter] = useState<"all" | "errors" | number>("all");
  const liveAgents = useLiveAgents();

  // Synthesize event list from live agent status (one per agent with last_run)
  const events = liveAgents
    .filter((a) => a.lastRun)
    .map((a) => ({
      id: a.slug,
      agentId: a.id,
      agentName: a.name,
      status: a.status,
      action:
        a.status === "running"
          ? "is running now"
          : a.status === "error"
            ? "errored on last run"
            : a.status === "queued"
              ? "is queued"
              : "completed last run",
      timestamp: a.lastRun!,
    }))
    .sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime());

  const filteredEvents =
    filter === "all"
      ? events
      : filter === "errors"
      ? events.filter((e) => e.status === "error")
      : events.filter((e) => e.agentId === filter);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 flex-wrap">
        <button
          onClick={() => setFilter("all")}
          className={cn(
            "rounded-full border px-3 py-1 text-xs transition-colors",
            filter === "all"
              ? "border-primary bg-primary/10 text-foreground"
              : "border-border text-muted-foreground hover:bg-secondary"
          )}
        >
          All
        </button>
        <button
          onClick={() => setFilter("errors")}
          className={cn(
            "rounded-full border px-3 py-1 text-xs transition-colors",
            filter === "errors"
              ? "border-destructive bg-destructive/10 text-foreground"
              : "border-border text-muted-foreground hover:bg-secondary"
          )}
        >
          Errors only
        </button>
        {AGENTS.slice(0, 6).map((agent) => (
          <button
            key={agent.id}
            onClick={() => setFilter(agent.id)}
            className={cn(
              "rounded-full border px-3 py-1 text-xs transition-colors",
              filter === agent.id
                ? "border-primary bg-primary/10 text-foreground"
                : "border-border text-muted-foreground hover:bg-secondary"
            )}
          >
            {agent.name}
          </button>
        ))}
      </div>

      <div className="rounded-lg border border-border bg-card divide-y divide-border">
        {filteredEvents.length === 0 ? (
          <div className="p-8 text-center">
            <p className="text-sm text-muted-foreground">
              No activity matching your filters.
            </p>
          </div>
        ) : (
          filteredEvents.map((event) => (
            <div
              key={event.id}
              className="flex items-start gap-3 px-4 py-3 hover:bg-secondary/30 transition-colors"
            >
              <StatusDot status={event.status} className="mt-1.5" />
              <div className="flex-1 min-w-0">
                <p className="text-sm">
                  <span className="font-medium">{event.agentName}</span>{" "}
                  <span className="text-muted-foreground">{event.action}</span>
                </p>
              </div>
              <span className="text-xs font-mono text-muted-foreground whitespace-nowrap">
                {formatTimeAgo(event.timestamp)}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
