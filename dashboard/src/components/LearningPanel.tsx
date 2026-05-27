/**
 * Learning stats + recent entries panel.
 * Embedded in InsightsPage.
 */
import { Brain, BookOpen, Loader2, TrendingUp } from "lucide-react"
import { useLearnings, useLearningStats } from "@/hooks/useLearning"

const typeColors: Record<string, string> = {
  pattern: "bg-blue-500/20 text-blue-400",
  preference: "bg-green-500/20 text-green-400",
  correction: "bg-orange-500/20 text-orange-400",
  insight: "bg-purple-500/20 text-purple-400",
}

export function LearningPanel() {
  const { data: stats, isLoading: statsLoading } = useLearningStats()
  const { data: entries, isLoading: entriesLoading } = useLearnings(10)

  if (statsLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Brain className="h-5 w-5 text-primary" />
        <h2 className="text-lg font-semibold text-foreground">Agent Learning</h2>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid gap-3 sm:grid-cols-3">
          <div className="rounded-xl border border-border bg-card p-4">
            <p className="text-xs text-muted-foreground">Total Learnings</p>
            <p className="text-2xl font-bold text-foreground">{stats.total_learnings}</p>
          </div>
          <div className="rounded-xl border border-border bg-card p-4">
            <div className="flex items-center gap-1.5">
              <TrendingUp className="h-3.5 w-3.5 text-green-400" />
              <p className="text-xs text-muted-foreground">This Month</p>
            </div>
            <p className="text-2xl font-bold text-foreground">{stats.this_month}</p>
          </div>
          <div className="rounded-xl border border-border bg-card p-4">
            <p className="text-xs text-muted-foreground">Active Agents</p>
            <p className="text-2xl font-bold text-foreground">
              {Object.keys(stats.by_agent).length}
            </p>
          </div>
        </div>
      )}

      {/* By Agent Breakdown */}
      {stats && Object.keys(stats.by_agent).length > 0 && (
        <div className="rounded-xl border border-border bg-card">
          <div className="border-b border-border px-4 py-2">
            <p className="text-xs font-medium text-muted-foreground">Learnings by Agent</p>
          </div>
          <div className="divide-y divide-border">
            {Object.entries(stats.by_agent)
              .sort(([, a], [, b]) => b - a)
              .map(([slug, count]) => (
                <div key={slug} className="flex items-center justify-between px-4 py-2">
                  <span className="text-sm text-foreground">{slug}</span>
                  <span className="text-xs text-muted-foreground">{count} learnings</span>
                </div>
              ))}
          </div>
        </div>
      )}

      {/* Recent Entries */}
      <div className="rounded-xl border border-border bg-card">
        <div className="flex items-center gap-2 border-b border-border px-4 py-2">
          <BookOpen className="h-3.5 w-3.5 text-muted-foreground" />
          <p className="text-xs font-medium text-muted-foreground">Recent Learnings</p>
        </div>

        {entriesLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
          </div>
        ) : entries && entries.length > 0 ? (
          <div className="divide-y divide-border">
            {entries.map((entry) => (
              <div key={entry.id} className="px-4 py-3">
                <div className="mb-1 flex items-center gap-2">
                  <span className="text-xs font-medium text-foreground">{entry.agent_slug}</span>
                  <span
                    className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${
                      typeColors[entry.learning_type] ?? "bg-muted text-muted-foreground"
                    }`}
                  >
                    {entry.learning_type}
                  </span>
                  <span className="ml-auto text-[10px] text-muted-foreground">
                    {new Date(entry.created_at).toLocaleDateString()}
                  </span>
                </div>
                <p className="text-sm text-muted-foreground line-clamp-2">{entry.content}</p>
              </div>
            ))}
          </div>
        ) : (
          <div className="py-8 text-center text-sm text-muted-foreground">
            No learnings yet. Agents will capture patterns as they run.
          </div>
        )}
      </div>
    </div>
  )
}
