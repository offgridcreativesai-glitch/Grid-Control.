/**
 * Memory — structured, editable brand memory (route "/memory").
 *
 * Mirrors the Noimos workspace-memory layout: three groups (Workspace · Personal ·
 * Account), every field inline-editable, each list item deletable, "+ Add" per list.
 * Auto-filled from onboarding + connected accounts; the team reads this on every task.
 *
 * Demo mode seeds it rich. Real mode starts from an empty structure. Persistence
 * (load from brand profile + a save endpoint) is the next wiring step.
 */
import { useState, useEffect } from "react"
import { useQuery, useMutation } from "@tanstack/react-query"
import { Plus, Trash2, BrainCircuit, ChevronDown, AlertTriangle, Check, Loader2 } from "lucide-react"
import { apiFetch } from "@/lib/api"
import { useBrandStore } from "@/store/brandStore"
import {
  isDemo, DEMO_MEMORY_DOC, EMPTY_MEMORY_DOC,
  type MemoryDoc, type MemoryListItem, type MemoryService,
} from "@/lib/demo"

function uid() {
  return `m_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`
}

/* ---------- primitives ---------- */

function GroupTitle({ children }: { children: React.ReactNode }) {
  return <h2 className="mb-5 mt-12 font-display text-[19px] font-semibold tracking-tight text-foreground first:mt-0">{children}</h2>
}

function FieldLabel({ children }: { children: React.ReactNode }) {
  return <p className="mb-2 text-[13px] font-medium text-foreground/90">{children}</p>
}

function Helper({ children }: { children: React.ReactNode }) {
  return <p className="mt-1.5 text-[12px] text-muted-foreground">{children}</p>
}

const inputCls =
  "w-full rounded-lg border border-input bg-black/30 px-3.5 py-2.5 text-[13.5px] text-foreground outline-none transition-colors placeholder:text-muted-foreground/60 focus:border-primary/50"

function OverviewField({ label, value, onChange, helper }: { label: string; value: string; onChange: (v: string) => void; helper?: string }) {
  return (
    <div>
      <FieldLabel>{label}</FieldLabel>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        rows={3}
        className={inputCls + " resize-none leading-relaxed"}
        placeholder="—"
      />
      {helper && <Helper>{helper}</Helper>}
    </div>
  )
}

function RowDelete({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="grid h-9 w-9 shrink-0 place-items-center rounded-lg text-muted-foreground transition-colors hover:bg-destructive/15 hover:text-destructive"
      aria-label="Remove"
    >
      <Trash2 size={15} />
    </button>
  )
}

function AddButton({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="inline-flex items-center gap-1.5 rounded-lg border border-border px-3 py-2 text-[12.5px] font-medium text-foreground/80 transition-colors hover:bg-white/[0.05] hover:text-foreground"
    >
      <Plus size={14} /> {label}
    </button>
  )
}

interface ListHandlers {
  onAdd: () => void
  onUpdate: (id: string, text: string) => void
  onDelete: (id: string) => void
}

function ListField({
  label, items, addLabel, multiline, placeholder, onAdd, onUpdate, onDelete,
}: { label: string; items: MemoryListItem[]; addLabel: string; multiline?: boolean; placeholder?: string } & ListHandlers) {
  return (
    <div>
      <FieldLabel>{label}</FieldLabel>
      <div className="glass-panel space-y-2 rounded-2xl p-3">
        {items.length === 0 && <p className="px-1 py-2 text-[12.5px] text-muted-foreground">Nothing yet.</p>}
        {items.map((it) => (
          <div key={it.id} className="flex items-start gap-2">
            {multiline ? (
              <textarea
                value={it.text}
                onChange={(e) => onUpdate(it.id, e.target.value)}
                rows={2}
                placeholder={placeholder}
                className={inputCls + " resize-none leading-relaxed"}
              />
            ) : (
              <input value={it.text} onChange={(e) => onUpdate(it.id, e.target.value)} placeholder={placeholder} className={inputCls} />
            )}
            <RowDelete onClick={() => onDelete(it.id)} />
          </div>
        ))}
        <div className="pt-1">
          <AddButton label={addLabel} onClick={onAdd} />
        </div>
      </div>
    </div>
  )
}

function ServicesField({
  services, onAdd, onUpdate, onDelete,
}: { services: MemoryService[]; onAdd: () => void; onUpdate: (id: string, field: "name" | "description", val: string) => void; onDelete: (id: string) => void }) {
  return (
    <div>
      <FieldLabel>Services &amp; products</FieldLabel>
      <div className="space-y-3">
        {services.map((s) => (
          <div key={s.id} className="glass-panel rounded-2xl p-4">
            <div className="flex items-start gap-2">
              <div className="min-w-0 flex-1 space-y-3">
                <div>
                  <p className="mb-1.5 text-[11px] font-medium uppercase tracking-[0.1em] text-muted-foreground">Name</p>
                  <input value={s.name} onChange={(e) => onUpdate(s.id, "name", e.target.value)} className={inputCls} placeholder="Product or service name" />
                </div>
                <div>
                  <p className="mb-1.5 text-[11px] font-medium uppercase tracking-[0.1em] text-muted-foreground">Description</p>
                  <textarea value={s.description} onChange={(e) => onUpdate(s.id, "description", e.target.value)} rows={2} className={inputCls + " resize-none leading-relaxed"} placeholder="What it is, in one line" />
                </div>
              </div>
              <RowDelete onClick={() => onDelete(s.id)} />
            </div>
          </div>
        ))}
        <AddButton label="Add product" onClick={onAdd} />
      </div>
    </div>
  )
}

/* ---------- page ---------- */

export function MemoryPage() {
  const { activeBrand } = useBrandStore()
  const slug = activeBrand.slug
  const [doc, setDoc] = useState<MemoryDoc>(isDemo() ? DEMO_MEMORY_DOC : EMPTY_MEMORY_DOC)
  const [saved, setSaved] = useState(false)

  // Load the persisted Memory doc (real mode). Seeded from the approved Foundation.
  const { data: loaded } = useQuery({
    queryKey: ["memory-doc", slug],
    enabled: !isDemo() && !!slug,
    queryFn: async () => (await (await apiFetch(`/api/brands/${slug}/memory-doc`)).json()),
  })
  useEffect(() => {
    if (isDemo()) return
    const d = loaded?.data
    if (d && typeof d === "object") setDoc(d as MemoryDoc)
  }, [loaded])

  const save = useMutation({
    mutationFn: async () => {
      const r = await apiFetch(`/api/brands/${slug}/memory-doc`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(doc),
      })
      const j = await r.json()
      if (!j.success) throw new Error(j.error || "Save failed")
      return j
    },
    onSuccess: () => { setSaved(true); setTimeout(() => setSaved(false), 2000) },
  })

  const patch = (fn: (d: MemoryDoc) => void) =>
    setDoc((prev) => { const d = structuredClone(prev); fn(d); return d })

  // bind a list (by selector) to add/update/delete handlers
  const list = (get: (d: MemoryDoc) => MemoryListItem[]): ListHandlers => ({
    onAdd: () => patch((d) => { get(d).push({ id: uid(), text: "" }) }),
    onUpdate: (id, text) => patch((d) => { const it = get(d).find((x) => x.id === id); if (it) it.text = text }),
    onDelete: (id) => patch((d) => { const a = get(d); const i = a.findIndex((x) => x.id === id); if (i >= 0) a.splice(i, 1) }),
  })

  const selectedAccount = doc.account.accounts.find((a) => a.id === doc.account.selectedId)

  return (
    <div className="min-h-full bg-background/60">
      <div className="mx-auto max-w-[820px] px-6 pb-24 pt-9">
        {/* Header */}
        <div className="flex items-center gap-2 text-[12px] text-muted-foreground">
          <span>Workspace settings</span>
          <ChevronDown className="h-3 w-3 -rotate-90" />
          <span className="text-foreground">Memory</span>
        </div>
        <div className="mt-3 flex items-start justify-between gap-3">
          <div className="flex items-start gap-3">
            <span className="mt-0.5 grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-primary/10 text-primary ring-1 ring-primary/25">
              <BrainCircuit size={20} />
            </span>
            <div>
              <h1 className="font-display text-[26px] font-semibold tracking-tight text-foreground">Memory</h1>
              <p className="mt-1 text-[14px] text-muted-foreground">
                What your team remembers about <span className="text-foreground">{activeBrand.name}</span>. Every agent reads this on every task.
              </p>
            </div>
          </div>
          {!isDemo() && (
            <button
              onClick={() => save.mutate()}
              disabled={save.isPending}
              className="inline-flex shrink-0 items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-[13px] font-semibold text-primary-foreground transition-transform hover:scale-[1.02] disabled:opacity-50"
            >
              {save.isPending ? <Loader2 size={15} className="animate-spin" /> : saved ? <Check size={15} /> : null}
              {save.isPending ? "Saving…" : saved ? "Saved" : "Save"}
            </button>
          )}
        </div>
        {save.isError && (
          <p className="mt-2 text-[12px] text-destructive">{(save.error as Error)?.message}</p>
        )}

        {/* Auto-adjust notice */}
        <div className="mt-6 flex items-center gap-2.5 rounded-xl border px-4 py-2.5 text-[12.5px]" style={{ background: "rgba(240,160,48,0.08)", borderColor: "rgba(240,160,48,0.22)", color: "var(--status-queued)" }}>
          <AlertTriangle size={15} className="shrink-0" />
          Your team may fine-tune this memory over time to keep performance sharp. Your edits always take priority.
        </div>

        {/* ---- Workspace Memory ---- */}
        <GroupTitle>Workspace memory</GroupTitle>
        <div className="space-y-7">
          <OverviewField
            label="Brand overview"
            value={doc.workspace.brandOverview}
            onChange={(v) => patch((d) => { d.workspace.brandOverview = v })}
            helper="A comprehensive overview of your brand identity, mission, and values."
          />
          <ServicesField
            services={doc.workspace.services}
            onAdd={() => patch((d) => { d.workspace.services.push({ id: uid(), name: "", description: "" }) })}
            onUpdate={(id, field, val) => patch((d) => { const s = d.workspace.services.find((x) => x.id === id); if (s) s[field] = val })}
            onDelete={(id) => patch((d) => { const i = d.workspace.services.findIndex((x) => x.id === id); if (i >= 0) d.workspace.services.splice(i, 1) })}
          />
          <ListField label="Goals" items={doc.workspace.goals} addLabel="Add goal" placeholder="A goal for the brand" {...list((d) => d.workspace.goals)} />
          <ListField label="Key metrics" items={doc.workspace.keyMetrics} addLabel="Add metric" placeholder="A metric you track" {...list((d) => d.workspace.keyMetrics)} />
        </div>

        {/* ---- Personal Memory ---- */}
        <GroupTitle>Personal memory</GroupTitle>
        <div className="space-y-7">
          <OverviewField
            label="Overview"
            value={doc.personal.overview}
            onChange={(v) => patch((d) => { d.personal.overview = v })}
            helper="A comprehensive overview of your profile, style, and approach."
          />
          <ListField label="Voice keywords" items={doc.personal.voiceKeywords} addLabel="Add keyword" placeholder="e.g. Confident" {...list((d) => d.personal.voiceKeywords)} />
          <ListField label="Voice examples" items={doc.personal.voiceExamples} addLabel="Add example" multiline placeholder="A line that sounds like you" {...list((d) => d.personal.voiceExamples)} />
          <ListField label="Content pillars" items={doc.personal.contentPillars} addLabel="Add pillar" placeholder="A recurring content theme" {...list((d) => d.personal.contentPillars)} />
          <OverviewField
            label="Content audience"
            value={doc.personal.contentAudience}
            onChange={(v) => patch((d) => { d.personal.contentAudience = v })}
            helper="Describe the ideal audience for the content you create."
          />
          <ListField label="Effective patterns" items={doc.personal.effectivePatterns} addLabel="Add pattern" placeholder="Something that works" {...list((d) => d.personal.effectivePatterns)} />
          <ListField label="Pitfalls" items={doc.personal.pitfalls} addLabel="Add pitfall" placeholder="Something to avoid" {...list((d) => d.personal.pitfalls)} />
          <ListField label="Rules" items={doc.personal.rules} addLabel="Add rule" placeholder="A hard rule for the team" {...list((d) => d.personal.rules)} />
        </div>

        {/* ---- Account Memory ---- */}
        <GroupTitle>Account memory</GroupTitle>
        <div className="space-y-7">
          <div>
            <FieldLabel>Select account</FieldLabel>
            <div className="relative">
              <select
                value={doc.account.selectedId}
                onChange={(e) => patch((d) => { d.account.selectedId = e.target.value })}
                className={inputCls + " cursor-pointer appearance-none pr-10"}
              >
                {doc.account.accounts.map((a) => (
                  <option key={a.id} value={a.id}>{a.platform} · {a.handle}</option>
                ))}
              </select>
              <ChevronDown className="pointer-events-none absolute right-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            </div>
            <Helper>
              {selectedAccount ? "Pick a connected account to load and edit its memory." : "Connect an account to give it its own memory."}
            </Helper>
          </div>
          <OverviewField
            label="Overview"
            value={doc.account.overview}
            onChange={(v) => patch((d) => { d.account.overview = v })}
            helper="How the brand shows up on this specific account."
          />
          <ListField label="Voice keywords" items={doc.account.voiceKeywords} addLabel="Add keyword" placeholder="e.g. Direct" {...list((d) => d.account.voiceKeywords)} />
        </div>
      </div>
    </div>
  )
}
