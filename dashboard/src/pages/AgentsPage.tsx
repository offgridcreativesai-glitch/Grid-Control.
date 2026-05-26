import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Play, MessageSquare, FileOutput, X, ArrowLeft } from "lucide-react";
import { cn, formatTimeAgo } from "@/lib/utils";
import { type Agent } from "@/data/agents";
import { useLiveAgents, useRunAgent } from "@/hooks/useGridApi";
import { StatusDot } from "@/components/ui/status-dot";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useAppStore } from "@/store/appStore";
import { useBrainStore } from "@/store/brainStore";

export function AgentsPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const agents = useLiveAgents();
  const selectedAgent = id ? agents.find((a) => a.id === parseInt(id)) : null;

  if (selectedAgent) {
    return <AgentDetail agent={selectedAgent} onBack={() => navigate("/agents")} />;
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-xl font-semibold">Agents</h1>
        <p className="text-sm text-muted-foreground">
          18 autonomous agents powering your content machine
        </p>
      </div>

      <div className="grid grid-cols-3 gap-4">
        {agents.map((agent) => (
          <AgentCard
            key={agent.id}
            agent={agent}
            onClick={() => navigate(`/agents/${agent.id}`)}
          />
        ))}
      </div>
    </div>
  );
}

function AgentCard({ agent, onClick }: { agent: Agent; onClick: () => void }) {
  const [isHovered, setIsHovered] = useState(false);
  const runAgent = useRunAgent();
  const { setBrainOpen } = useAppStore();
  const { setScope } = useBrainStore();

  return (
    <div
      onClick={onClick}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      className={cn(
        "rounded-lg border border-border bg-card p-4 cursor-pointer transition-colors",
        isHovered && "bg-secondary border-border"
      )}
    >
      <div className="flex items-start justify-between mb-2">
        <span className="font-mono text-xs text-muted-foreground">
          {String(agent.id).padStart(2, "0")}
        </span>
        <StatusDot status={agent.status} />
      </div>
      <h3 className="font-medium text-sm mb-1">{agent.name}</h3>
      <p className="text-xs text-muted-foreground mb-3">{agent.role}</p>
      <div className="flex items-center justify-between">
        <span className="text-xs font-mono text-muted-foreground">
          {agent.lastRun ? formatTimeAgo(agent.lastRun) : "—"}
        </span>
        {isHovered && (
          <div className="flex items-center gap-1">
            <button
              onClick={(e) => {
                e.stopPropagation();
                runAgent.mutate(agent.slug);
              }}
              disabled={runAgent.isPending && runAgent.variables === agent.slug}
              className="flex h-6 w-6 items-center justify-center rounded hover:bg-background transition-colors disabled:opacity-50"
              title="Run"
            >
              <Play className="h-3 w-3" />
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation();
                setScope(agent.slug);
                setBrainOpen(true);
              }}
              className="flex h-6 w-6 items-center justify-center rounded hover:bg-background transition-colors"
              title={`Chat scoped to ${agent.name}`}
            >
              <MessageSquare className="h-3 w-3" />
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onClick();
              }}
              className="flex h-6 w-6 items-center justify-center rounded hover:bg-background transition-colors"
              title="Outputs"
            >
              <FileOutput className="h-3 w-3" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function AgentDetail({ agent, onBack }: { agent: Agent; onBack: () => void }) {
  const runHistory = [
    { id: 1, timestamp: new Date(Date.now() - 1000 * 60 * 5), status: "success" as const, duration: "12s", output: "Generated 3 content ideas" },
    { id: 2, timestamp: new Date(Date.now() - 1000 * 60 * 60 * 2), status: "success" as const, duration: "8s", output: "Updated content calendar" },
    { id: 3, timestamp: new Date(Date.now() - 1000 * 60 * 60 * 5), status: "error" as const, duration: "3s", output: "API rate limit exceeded" },
    { id: 4, timestamp: new Date(Date.now() - 1000 * 60 * 60 * 8), status: "success" as const, duration: "15s", output: "Processed 12 engagement signals" },
    { id: 5, timestamp: new Date(Date.now() - 1000 * 60 * 60 * 24), status: "success" as const, duration: "22s", output: "Completed weekly analysis" },
  ];

  return (
    <div className="flex h-full">
      {/* Main content */}
      <div className="flex-1 p-6 overflow-auto">
        <button
          onClick={onBack}
          className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground mb-4 transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to agents
        </button>

        <div className="flex items-start justify-between mb-6">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <span className="font-mono text-sm text-muted-foreground">
                {String(agent.id).padStart(2, "0")}
              </span>
              <h1 className="text-xl font-semibold">{agent.name}</h1>
              <StatusDot status={agent.status} />
            </div>
            <p className="text-sm text-muted-foreground">{agent.role}</p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm">
              <MessageSquare className="h-4 w-4 mr-1" />
              Chat
            </Button>
            <Button size="sm">
              <Play className="h-4 w-4 mr-1" />
              Run now
            </Button>
          </div>
        </div>

        <Tabs defaultValue="history" className="w-full">
          <TabsList>
            <TabsTrigger value="history">Run History</TabsTrigger>
            <TabsTrigger value="output">Last Output</TabsTrigger>
            <TabsTrigger value="settings">Settings</TabsTrigger>
          </TabsList>

          <TabsContent value="history" className="mt-4">
            <div className="rounded-lg border border-border bg-card overflow-hidden">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-border bg-secondary/50">
                    <th className="px-4 py-2 text-left text-xs font-medium text-muted-foreground">
                      Status
                    </th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-muted-foreground">
                      Timestamp
                    </th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-muted-foreground">
                      Duration
                    </th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-muted-foreground">
                      Output
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {runHistory.map((run) => (
                    <tr key={run.id} className="hover:bg-secondary/30 transition-colors">
                      <td className="px-4 py-3">
                        <StatusDot status={run.status} />
                      </td>
                      <td className="px-4 py-3 text-sm font-mono text-muted-foreground">
                        {formatTimeAgo(run.timestamp)}
                      </td>
                      <td className="px-4 py-3 text-sm font-mono text-muted-foreground">
                        {run.duration}
                      </td>
                      <td className="px-4 py-3 text-sm">{run.output}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </TabsContent>

          <TabsContent value="output" className="mt-4">
            <div className="rounded-lg border border-border bg-card p-4">
              <pre className="text-sm font-mono text-muted-foreground whitespace-pre-wrap">
{`{
  "timestamp": "${new Date().toISOString()}",
  "agent": "${agent.name}",
  "result": {
    "status": "success",
    "items_processed": 3,
    "output": [
      "Content idea: AI tools comparison carousel",
      "Content idea: Morning routine optimization thread",
      "Content idea: Behind the scenes of GRID CONTROL"
    ]
  }
}`}
              </pre>
            </div>
          </TabsContent>

          <TabsContent value="settings" className="mt-4">
            <div className="rounded-lg border border-border bg-card p-4 space-y-4">
              <div>
                <label className="text-sm font-medium">Auto-run schedule</label>
                <p className="text-xs text-muted-foreground mt-1">
                  Currently set to run every 4 hours
                </p>
              </div>
              <div>
                <label className="text-sm font-medium">Output format</label>
                <p className="text-xs text-muted-foreground mt-1">JSON (default)</p>
              </div>
              <div>
                <label className="text-sm font-medium">Notifications</label>
                <p className="text-xs text-muted-foreground mt-1">
                  Notify on error only
                </p>
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </div>

      {/* Chat panel */}
      <div className="w-80 border-l border-border bg-background flex flex-col">
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <span className="text-sm font-medium">Chat with {agent.name}</span>
          <button className="text-muted-foreground hover:text-foreground transition-colors">
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="flex-1 p-4 flex items-center justify-center">
          <p className="text-sm text-muted-foreground text-center">
            Start a conversation with this agent to get insights or trigger actions.
          </p>
        </div>
        <div className="border-t border-border p-4">
          <input
            type="text"
            placeholder="Ask something..."
            className="w-full rounded-lg border border-border bg-card px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
          />
        </div>
      </div>
    </div>
  );
}
