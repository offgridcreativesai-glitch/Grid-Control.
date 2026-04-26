/**
 * InsightsSpace — Space 6 (NEW Apr 26)
 * Three panels in one space:
 *  - Performance Log (POST /api/performance/log-post + view inbox + history)
 *  - Contradictions View (run /api/contradictions/check + show findings)
 *  - Provenance Audit (read latest agent outputs and show data_provenance + provenance_validation)
 */

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"
import { useBrandStore } from "@/store/brandStore"

type Tab = "performance" | "contradictions" | "provenance"

export function InsightsSpace() {
  const [tab, setTab] = useState<Tab>("performance")
  const { activeBrand } = useBrandStore()
  const slug = activeBrand?.slug || ""

  if (!slug) {
    return <div className="p-6 text-sm" style={{ color: "var(--gc-text-2)" }}>Select a brand first.</div>
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <header className="px-6 pt-6 pb-3 border-b" style={{ borderColor: "var(--gc-border)" }}>
        <div className="text-[11px] uppercase tracking-wide mb-1" style={{ color: "var(--gc-text-2)" }}>Insights /</div>
        <h1 className="text-2xl font-semibold" style={{ color: "var(--gc-text-1)" }}>Quality + Feedback Layer</h1>
        <p className="text-sm mt-1" style={{ color: "var(--gc-text-2)" }}>
          Performance feedback, contradiction audits, and source-citation traceability for {activeBrand?.name || slug}.
        </p>
        <nav className="flex gap-1 mt-4">
          {(["performance", "contradictions", "provenance"] as Tab[]).map(t => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className="px-4 py-2 text-sm rounded-lg transition-colors"
              style={{
                background: tab === t ? "var(--gc-elev-1)" : "transparent",
                color: tab === t ? "var(--gc-text-1)" : "var(--gc-text-2)",
                border: `1px solid ${tab === t ? "var(--gc-border)" : "transparent"}`,
              }}
            >
              {t === "performance" ? "Performance Log" :
               t === "contradictions" ? "Contradictions" : "Provenance Audit"}
            </button>
          ))}
        </nav>
      </header>

      <main className="flex-1 overflow-auto">
        {tab === "performance" && <PerformancePanel slug={slug} />}
        {tab === "contradictions" && <ContradictionsPanel slug={slug} />}
        {tab === "provenance" && <ProvenancePanel slug={slug} />}
      </main>
    </div>
  )
}

// ─── PANEL 1: PERFORMANCE LOG ───────────────────────────────────────────────

function PerformancePanel({ slug }: { slug: string }) {
  const qc = useQueryClient()
  const [postId, setPostId] = useState("")
  const [topic, setTopic] = useState("")
  const [hookPattern, setHookPattern] = useState("Contrarian Truth")
  const [hookText, setHookText] = useState("")
  const [format, setFormat] = useState("Reel")
  const [impressions, setImpressions] = useState("")
  const [reach, setReach] = useState("")
  const [saves, setSaves] = useState("")
  const [likes, setLikes] = useState("")
  const [shares, setShares] = useState("")
  const [comments, setComments] = useState("")
  const [dms, setDms] = useState("")

  const inboxQ = useQuery({
    queryKey: ["perf-inbox", slug],
    queryFn: async () => {
      const r = await apiFetch(`/api/performance/inbox?brand_slug=${slug}`)
      const j = await r.json()
      return j.data
    },
  })

  const historyQ = useQuery({
    queryKey: ["perf-history", slug],
    queryFn: async () => {
      const r = await apiFetch(`/api/performance/history?brand_slug=${slug}`)
      const j = await r.json()
      return j.data
    },
  })

  const submitMutation = useMutation({
    mutationFn: async () => {
      const body = {
        brand_slug: slug,
        post_id: postId,
        published_at: new Date().toISOString(),
        platform: "instagram",
        format,
        topic,
        hook_pattern_used: hookPattern,
        hook_text: hookText,
        metrics: {
          impressions: Number(impressions) || 0,
          reach: Number(reach) || 0,
          saves: Number(saves) || 0,
          likes: Number(likes) || 0,
          shares: Number(shares) || 0,
          comments: Number(comments) || 0,
          dm_inquiries: Number(dms) || 0,
        },
      }
      const r = await apiFetch("/api/performance/log-post", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      })
      const j = await r.json()
      if (!j.success) throw new Error(j.error || "Failed to log post")
      return j.data
    },
    onSuccess: () => {
      // Reset
      setPostId(""); setTopic(""); setHookText("")
      setImpressions(""); setReach(""); setSaves(""); setLikes("")
      setShares(""); setComments(""); setDms("")
      qc.invalidateQueries({ queryKey: ["perf-inbox", slug] })
    },
  })

  const runTrackerMutation = useMutation({
    mutationFn: async () => {
      const r = await apiFetch("/api/agents/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ agentName: "Performance Tracker", brand_slug: slug }),
      })
      return r.json()
    },
    onSuccess: () => {
      setTimeout(() => {
        qc.invalidateQueries({ queryKey: ["perf-inbox", slug] })
        qc.invalidateQueries({ queryKey: ["perf-history", slug] })
      }, 2000)
    },
  })

  return (
    <div className="p-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Log Post Form */}
      <section className="rounded-xl border p-5" style={{ background: "var(--gc-elev-0)", borderColor: "var(--gc-border)" }}>
        <h3 className="text-base font-semibold mb-1" style={{ color: "var(--gc-text-1)" }}>Log a Published Post</h3>
        <p className="text-xs mb-4" style={{ color: "var(--gc-text-2)" }}>
          Paste metrics from Instagram Insights. Queues for next Performance Tracker run.
        </p>
        <div className="grid grid-cols-2 gap-3 text-sm">
          <Field label="Post ID" value={postId} onChange={setPostId} placeholder="ig_xxxxx" />
          <Field label="Format" value={format} onChange={setFormat} placeholder="Reel | Carousel | Static" />
          <Field label="Topic" value={topic} onChange={setTopic} placeholder="AI Strategy Framework" wide />
          <Field label="Hook Pattern" value={hookPattern} onChange={setHookPattern} placeholder="Contrarian Truth | Specificity | ..." />
          <Field label="Hook Text" value={hookText} onChange={setHookText} placeholder="..." wide />
          <Field label="Impressions" value={impressions} onChange={setImpressions} type="number" />
          <Field label="Reach" value={reach} onChange={setReach} type="number" />
          <Field label="Saves" value={saves} onChange={setSaves} type="number" />
          <Field label="Likes" value={likes} onChange={setLikes} type="number" />
          <Field label="Shares" value={shares} onChange={setShares} type="number" />
          <Field label="Comments" value={comments} onChange={setComments} type="number" />
          <Field label="DM Inquiries" value={dms} onChange={setDms} type="number" />
        </div>
        <div className="flex gap-2 mt-4">
          <button
            onClick={() => submitMutation.mutate()}
            disabled={!postId || !topic || submitMutation.isPending}
            className="px-4 py-2 rounded-lg text-sm font-medium disabled:opacity-50"
            style={{ background: "#D4A24C", color: "#0A0A0A" }}
          >
            {submitMutation.isPending ? "Queueing..." : "Queue Post"}
          </button>
          <button
            onClick={() => runTrackerMutation.mutate()}
            disabled={runTrackerMutation.isPending}
            className="px-4 py-2 rounded-lg text-sm border disabled:opacity-50"
            style={{ borderColor: "var(--gc-border)", color: "var(--gc-text-1)" }}
          >
            {runTrackerMutation.isPending ? "Running..." : "Run Performance Tracker"}
          </button>
        </div>
        {submitMutation.isError && (
          <div className="mt-2 text-xs" style={{ color: "#ef4444" }}>{(submitMutation.error as Error).message}</div>
        )}
      </section>

      {/* Inbox + History */}
      <section className="space-y-5">
        <div className="rounded-xl border p-5" style={{ background: "var(--gc-elev-0)", borderColor: "var(--gc-border)" }}>
          <h3 className="text-base font-semibold mb-3" style={{ color: "var(--gc-text-1)" }}>
            Inbox Queue ({inboxQ.data?.queued_count || 0})
          </h3>
          {inboxQ.data?.queue?.length ? (
            <ul className="space-y-2 text-sm">
              {inboxQ.data.queue.map((p: any, i: number) => (
                <li key={i} className="flex justify-between" style={{ color: "var(--gc-text-2)" }}>
                  <span>{p.post_id} · {p.hook_pattern_used}</span>
                  <span>{p.metrics?.saves || 0} saves</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm" style={{ color: "var(--gc-text-3)" }}>No posts queued. Use the form to add some.</p>
          )}
        </div>

        <div className="rounded-xl border p-5" style={{ background: "var(--gc-elev-0)", borderColor: "var(--gc-border)" }}>
          <h3 className="text-base font-semibold mb-3" style={{ color: "var(--gc-text-1)" }}>Performance History</h3>
          {historyQ.data?.exists ? (
            <div className="text-sm space-y-3">
              <div style={{ color: "var(--gc-text-2)" }}>
                <strong style={{ color: "var(--gc-text-1)" }}>{historyQ.data.posts?.length || 0}</strong> posts in history ·
                top quartile threshold: <strong style={{ color: "var(--gc-text-1)" }}>
                  {historyQ.data.rolling_baselines?.top_quartile_threshold_score || "—"}
                </strong>
              </div>
              <div>
                <div className="text-xs uppercase tracking-wide mb-1" style={{ color: "var(--gc-text-2)" }}>Winning Hook Patterns</div>
                <ul className="space-y-1">
                  {(historyQ.data.winning_patterns?.hook_patterns_top_3 || []).map((w: any, i: number) => (
                    <li key={i} style={{ color: "var(--gc-text-1)" }}>
                      {w.value} <span style={{ color: "var(--gc-text-2)" }}>· {w.median_score}</span>
                    </li>
                  ))}
                </ul>
              </div>
              {historyQ.data.dead_patterns?.length > 0 && (
                <div>
                  <div className="text-xs uppercase tracking-wide mb-1" style={{ color: "#ef4444" }}>Dead Patterns</div>
                  <ul className="space-y-1 text-xs">
                    {historyQ.data.dead_patterns.map((d: any, i: number) => (
                      <li key={i} style={{ color: "var(--gc-text-2)" }}>{d.value} ({d.category})</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ) : (
            <p className="text-sm" style={{ color: "var(--gc-text-3)" }}>No history yet. Log posts and run Performance Tracker to compute baselines.</p>
          )}
        </div>
      </section>
    </div>
  )
}

function Field(props: { label: string; value: string; onChange: (v: string) => void; placeholder?: string; type?: string; wide?: boolean }) {
  return (
    <label className={props.wide ? "col-span-2" : ""}>
      <div className="text-[11px] uppercase tracking-wide mb-1" style={{ color: "var(--gc-text-2)" }}>{props.label}</div>
      <input
        type={props.type || "text"}
        value={props.value}
        onChange={(e) => props.onChange(e.target.value)}
        placeholder={props.placeholder}
        className="w-full px-3 py-2 rounded-lg border text-sm"
        style={{ background: "var(--gc-elev-1)", borderColor: "var(--gc-border)", color: "var(--gc-text-1)" }}
      />
    </label>
  )
}

// ─── PANEL 2: CONTRADICTIONS ────────────────────────────────────────────────

function ContradictionsPanel({ slug }: { slug: string }) {
  const qc = useQueryClient()
  const latestQ = useQuery({
    queryKey: ["contradictions-latest", slug],
    queryFn: async () => {
      const r = await apiFetch(`/api/contradictions/latest?brand_slug=${slug}`)
      const j = await r.json()
      return j.data
    },
  })
  const runMutation = useMutation({
    mutationFn: async () => {
      const r = await apiFetch(`/api/contradictions/check?brand_slug=${slug}`, { method: "POST" })
      const j = await r.json()
      if (!j.success) throw new Error(j.error)
      return j.data
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["contradictions-latest", slug] }),
  })

  const data = runMutation.data || latestQ.data
  const findings = data?.findings || []
  const counts = data?.counts || { CRITICAL: 0, WARNING: 0, INFO: 0 }
  const blocking = data?.blocking || false

  const sevColor = (s: string) => s === "CRITICAL" ? "#ef4444" : s === "WARNING" ? "#f59e0b" : "#3b82f6"

  return (
    <div className="p-6 space-y-5">
      <div className="flex justify-between items-center">
        <div>
          <h3 className="text-base font-semibold" style={{ color: "var(--gc-text-1)" }}>Cross-Agent Contradictions</h3>
          <p className="text-xs mt-1" style={{ color: "var(--gc-text-2)" }}>
            Pure-math detector (Build D). 6 rules. Last scan: {data?.scanned_at ? new Date(data.scanned_at).toLocaleString() : "never"}
          </p>
        </div>
        <button
          onClick={() => runMutation.mutate()}
          disabled={runMutation.isPending}
          className="px-4 py-2 rounded-lg text-sm font-medium disabled:opacity-50"
          style={{ background: "#D4A24C", color: "#0A0A0A" }}
        >
          {runMutation.isPending ? "Scanning..." : "Run Detector Now"}
        </button>
      </div>

      <div className="flex gap-3 text-sm">
        {Object.entries(counts).map(([sev, n]) => (
          <div key={sev} className="px-3 py-2 rounded-lg border"
               style={{ borderColor: "var(--gc-border)", background: "var(--gc-elev-0)" }}>
            <span style={{ color: sevColor(sev) }}>●</span>
            <span className="ml-2" style={{ color: "var(--gc-text-1)" }}>{sev}: {n as number}</span>
          </div>
        ))}
        {blocking && (
          <div className="px-3 py-2 rounded-lg" style={{ background: "#7f1d1d", color: "#fff" }}>
            🚨 BLOCKING — outputs auto-quarantined by Build H
          </div>
        )}
      </div>

      {findings.length === 0 ? (
        <div className="rounded-xl border p-6 text-center" style={{ background: "var(--gc-elev-0)", borderColor: "var(--gc-border)" }}>
          <p className="text-sm" style={{ color: "var(--gc-text-2)" }}>
            {data ? "No contradictions detected. All agents are aligned." : "Click Run Detector Now to scan."}
          </p>
        </div>
      ) : (
        <ul className="space-y-3">
          {findings.map((f: any, i: number) => (
            <li key={i} className="rounded-xl border p-4" style={{ background: "var(--gc-elev-0)", borderColor: "var(--gc-border)" }}>
              <div className="flex justify-between items-start mb-2">
                <div>
                  <span className="text-xs font-semibold px-2 py-0.5 rounded" style={{ background: sevColor(f.severity), color: "#fff" }}>
                    {f.severity}
                  </span>
                  <span className="ml-2 text-sm font-mono" style={{ color: "var(--gc-text-1)" }}>{f.rule_id}</span>
                </div>
                <span className="text-xs" style={{ color: "var(--gc-text-2)" }}>{(f.agents_involved || []).join(" + ")}</span>
              </div>
              <pre className="text-xs whitespace-pre-wrap mt-2 p-2 rounded"
                   style={{ background: "var(--gc-elev-1)", color: "var(--gc-text-2)" }}>
{JSON.stringify(f.evidence, null, 2)}
              </pre>
              <div className="text-sm mt-2" style={{ color: "var(--gc-text-1)" }}>
                <strong>Fix:</strong> {f.proposed_fix}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

// ─── PANEL 3: PROVENANCE AUDIT ──────────────────────────────────────────────

function ProvenancePanel({ slug }: { slug: string }) {
  const filesToInspect = [
    { name: "Strategy", path: "strategy_90day.json" },
    { name: "Calendar", path: "content_calendar.json" },
    { name: "Trends", path: "trends_live.json" },
  ]

  return (
    <div className="p-6 space-y-5">
      <div>
        <h3 className="text-base font-semibold" style={{ color: "var(--gc-text-1)" }}>Source Citation Audit (Rule 10)</h3>
        <p className="text-xs mt-1" style={{ color: "var(--gc-text-2)" }}>
          Every Claude-generated output must cite the real data it was based on.
          See `data_provenance` + `provenance_validation` blocks per agent.
        </p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {filesToInspect.map(f => <ProvenanceCard key={f.path} slug={slug} fileName={f.name} filePath={f.path} />)}
      </div>
    </div>
  )
}

function ProvenanceCard({ slug, fileName, filePath }: { slug: string; fileName: string; filePath: string }) {
  const q = useQuery({
    queryKey: ["provenance", slug, filePath],
    queryFn: async () => {
      // Use brand-scoped output endpoint (existing) or fall back to direct read
      const r = await apiFetch(`/api/brand/file?brand_slug=${slug}&file=${encodeURIComponent(filePath)}`)
      if (!r.ok) return null
      const j = await r.json()
      return j.success ? j.data : null
    },
    retry: 0,
  })

  if (q.isLoading) return <Card title={fileName}><span style={{ color: "var(--gc-text-2)" }}>Loading...</span></Card>
  if (!q.data) return <Card title={fileName}><span style={{ color: "var(--gc-text-3)" }}>Not generated yet</span></Card>

  const provenance = q.data.data_provenance || []
  const validation = q.data.provenance_validation || {}
  const passed = validation.passed
  const total = validation.claims_total || provenance.length
  const validated = validation.claims_validated || 0

  return (
    <Card title={fileName}>
      <div className="text-sm space-y-2">
        <div style={{ color: "var(--gc-text-2)" }}>
          {validated}/{total} citations validated
          <span className="ml-2 px-2 py-0.5 text-xs rounded"
                style={{ background: passed ? "#22c55e" : "#f59e0b", color: "#000" }}>
            {passed ? "PASSED" : "FLAGGED"}
          </span>
        </div>
        {provenance.slice(0, 3).map((p: any, i: number) => (
          <div key={i} className="text-xs p-2 rounded" style={{ background: "var(--gc-elev-1)", color: "var(--gc-text-2)" }}>
            <div className="font-semibold mb-1" style={{ color: "var(--gc-text-1)" }}>{(p.claim || "").slice(0, 80)}</div>
            <div>← {p.source_file}#{(p.source_path || "").slice(0, 50)}</div>
          </div>
        ))}
        {provenance.length > 3 && (
          <div className="text-xs" style={{ color: "var(--gc-text-3)" }}>+ {provenance.length - 3} more</div>
        )}
      </div>
    </Card>
  )
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border p-4" style={{ background: "var(--gc-elev-0)", borderColor: "var(--gc-border)" }}>
      <h4 className="text-sm font-semibold mb-3" style={{ color: "var(--gc-text-1)" }}>{title}</h4>
      {children}
    </div>
  )
}
