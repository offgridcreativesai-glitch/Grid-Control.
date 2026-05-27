/**
 * Revision feedback panel.
 * Shows revision history for an output and allows requesting revisions.
 */
import { useState } from "react"
import { RotateCcw, MessageSquare, Loader2, AlertCircle, Clock } from "lucide-react"
import { useRevisions, useRequestRevision } from "@/hooks/useRevisions"

export function RevisionPanel({ outputId }: { outputId: string }) {
  const { data: revisions, isLoading } = useRevisions(outputId)
  const requestRevision = useRequestRevision()
  const [feedback, setFeedback] = useState("")
  const [showForm, setShowForm] = useState(false)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!feedback.trim()) return
    requestRevision.mutate(
      { output_id: outputId, feedback: feedback.trim() },
      {
        onSuccess: () => {
          setFeedback("")
          setShowForm(false)
        },
      }
    )
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <RotateCcw className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm font-medium text-foreground">
            Revisions ({revisions?.length ?? 0})
          </span>
        </div>
        {!showForm && (
          <button
            onClick={() => setShowForm(true)}
            className="flex items-center gap-1.5 rounded-md bg-secondary px-3 py-1.5 text-xs font-medium text-foreground hover:bg-secondary/80 transition-colors"
          >
            <MessageSquare className="h-3 w-3" />
            Request Revision
          </button>
        )}
      </div>

      {/* Revision Request Form */}
      {showForm && (
        <form onSubmit={handleSubmit} className="rounded-lg border border-border bg-card p-3">
          <textarea
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            placeholder="What should change? Be specific..."
            rows={3}
            className="w-full resize-none rounded-md border border-border bg-background p-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none"
            required
          />
          <div className="mt-2 flex items-center justify-end gap-2">
            <button
              type="button"
              onClick={() => {
                setShowForm(false)
                setFeedback("")
              }}
              className="rounded-md px-3 py-1.5 text-xs text-muted-foreground hover:bg-secondary"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={requestRevision.isPending || !feedback.trim()}
              className="flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              {requestRevision.isPending ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                <RotateCcw className="h-3 w-3" />
              )}
              Submit
            </button>
          </div>
          {requestRevision.isError && (
            <div className="mt-2 flex items-center gap-1.5 text-xs text-red-400">
              <AlertCircle className="h-3 w-3" />
              {requestRevision.error?.message || "Failed to request revision"}
            </div>
          )}
        </form>
      )}

      {/* Revision History */}
      {isLoading ? (
        <div className="flex items-center justify-center py-4">
          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
        </div>
      ) : revisions && revisions.length > 0 ? (
        <div className="space-y-2">
          {revisions.map((rev) => (
            <div key={rev.id} className="rounded-lg border border-border bg-card/50 p-3">
              <div className="mb-1 flex items-center gap-2">
                <span className="text-xs font-medium text-foreground">
                  Revision #{rev.revision_number}
                </span>
                <span
                  className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${
                    rev.status === "completed"
                      ? "bg-green-500/20 text-green-400"
                      : rev.status === "pending"
                      ? "bg-yellow-500/20 text-yellow-400"
                      : "bg-blue-500/20 text-blue-400"
                  }`}
                >
                  {rev.status}
                </span>
                <div className="ml-auto flex items-center gap-1 text-[10px] text-muted-foreground">
                  <Clock className="h-2.5 w-2.5" />
                  {new Date(rev.created_at).toLocaleString()}
                </div>
              </div>
              <p className="text-sm text-muted-foreground">{rev.feedback}</p>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  )
}
