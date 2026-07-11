/**
 * Creative Library — every visual/audio asset the team has generated, in one place (route "/creative").
 * A tagged, versioned library over the Creative Director + Carousel Designer outputs. Real files only,
 * served through the existing media route. Client-safe: no models / slugs / tokens.
 */
import { useMemo, useState, type ReactNode } from "react"
import { cn, formatTimeAgo } from "@/lib/utils"
import { useCreativeLibrary, useSetAssetTags, type CreativeAsset } from "@/hooks/useGridApi"
import { useBrandStore } from "@/store/brandStore"
import { Image as ImageIcon, Video, Music, X, Plus, Tag as TagIcon } from "lucide-react"

function Panel({ className = "", children }: { className?: string; children: ReactNode }) {
  return <div className={"glass-panel rounded-2xl " + className}>{children}</div>
}

const KIND_ICON = { image: ImageIcon, video: Video, audio: Music } as const
const STATE_LABEL: Record<string, string> = { approved: "Approved", pending: "In review", generated: "Draft" }

function Thumb({ asset }: { asset: CreativeAsset }) {
  if (asset.kind === "image")
    return <img src={asset.media_url} alt={asset.filename} loading="lazy" className="h-full w-full object-cover" />
  if (asset.kind === "video")
    return <video src={asset.media_url} muted className="h-full w-full object-cover" />
  const Icon = Music
  return (
    <div className="flex h-full w-full items-center justify-center bg-secondary/40">
      <Icon className="h-8 w-8 text-muted-foreground" />
    </div>
  )
}

function FilterChips<T extends string>({
  options, active, onPick, labelFor,
}: { options: [T, number][]; active?: T; onPick: (v?: T) => void; labelFor?: (v: T) => string }) {
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <button
        onClick={() => onPick(undefined)}
        className={cn("rounded-full px-3 py-1 text-[12px] transition-colors",
          !active ? "bg-secondary text-foreground" : "text-muted-foreground hover:text-foreground")}
      >All</button>
      {options.map(([v, n]) => (
        <button key={v} onClick={() => onPick(active === v ? undefined : v)}
          className={cn("rounded-full px-3 py-1 text-[12px] capitalize transition-colors",
            active === v ? "bg-secondary text-foreground" : "text-muted-foreground hover:text-foreground")}
        >{(labelFor ? labelFor(v) : v)} <span className="text-muted-foreground">· {n}</span></button>
      ))}
    </div>
  )
}

export function CreativeLibraryPage() {
  const { activeBrand } = useBrandStore()
  const [kind, setKind] = useState<string>()
  const [state, setState] = useState<string>()
  const [selected, setSelected] = useState<CreativeAsset | null>(null)

  const { data, isLoading } = useCreativeLibrary({ kind, approval_state: state })
  const assets = data?.assets ?? []
  const facets = data?.facets

  // variant families for the detail view — grouped from the loaded list (no extra call)
  const variants = useMemo(
    () => (selected ? assets.filter((a) => a.group_key === selected.group_key) : []),
    [selected, assets],
  )

  return (
    <div className="min-h-full bg-background/60">
      <div className="mx-auto max-w-[1100px] space-y-6 px-6 pb-20 pt-10">
        {/* Header */}
        <div>
          <h1 className="font-display text-[26px] font-semibold tracking-tight text-foreground">Creative library</h1>
          <p className="mt-1.5 text-[14px] text-muted-foreground">
            Every visual and audio your team has made for <span className="text-foreground">{activeBrand.name}</span> — tagged and reusable.
          </p>
        </div>

        {/* Filters */}
        {facets && facets.total > 0 && (
          <div className="space-y-2.5">
            <FilterChips
              options={Object.entries(facets.kind) as [string, number][]}
              active={kind} onPick={setKind}
            />
            <FilterChips
              options={Object.entries(facets.approval_state) as [string, number][]}
              active={state} onPick={setState} labelFor={(v) => STATE_LABEL[v] ?? v}
            />
          </div>
        )}

        {/* Grid */}
        {isLoading ? (
          <Panel className="p-10 text-center"><p className="text-[14px] text-muted-foreground">Loading your assets…</p></Panel>
        ) : assets.length === 0 ? (
          <Panel className="p-10 text-center">
            <p className="text-[14px] text-muted-foreground">
              No creative yet. As your team generates carousels, images, reels, and voiceovers, they collect here.
            </p>
          </Panel>
        ) : (
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
            {assets.map((a) => {
              const Icon = KIND_ICON[a.kind]
              const family = assets.filter((x) => x.group_key === a.group_key).length
              return (
                <button key={a.id} onClick={() => setSelected(a)}
                  className="group overflow-hidden rounded-xl border border-border bg-card text-left transition-colors hover:border-primary/40">
                  <div className="relative aspect-square overflow-hidden bg-secondary/30">
                    <Thumb asset={a} />
                    <span className="absolute left-2 top-2 flex items-center gap-1 rounded-md bg-black/55 px-1.5 py-0.5 text-[10px] text-white backdrop-blur">
                      <Icon className="h-3 w-3" />{a.kind}
                    </span>
                    {family > 1 && (
                      <span className="absolute right-2 top-2 rounded-md bg-black/55 px-1.5 py-0.5 text-[10px] text-white backdrop-blur">
                        {family} versions
                      </span>
                    )}
                  </div>
                  <div className="space-y-1 p-2.5">
                    <p className="line-clamp-1 text-[12px] text-foreground/90">{a.filename}</p>
                    <div className="flex items-center justify-between text-[10.5px] text-muted-foreground">
                      <span>{a.source_agent}</span>
                      <span>{STATE_LABEL[a.approval_state] ?? a.approval_state}</span>
                    </div>
                    {a.tags.length > 0 && (
                      <div className="flex flex-wrap gap-1 pt-0.5">
                        {a.tags.slice(0, 3).map((t) => (
                          <span key={t} className="rounded bg-secondary px-1.5 py-0.5 text-[10px] text-muted-foreground">{t}</span>
                        ))}
                      </div>
                    )}
                  </div>
                </button>
              )
            })}
          </div>
        )}
      </div>

      {selected && (
        <AssetDetail asset={selected} variants={variants} onClose={() => setSelected(null)} />
      )}
    </div>
  )
}

function AssetDetail({ asset, variants, onClose }: { asset: CreativeAsset; variants: CreativeAsset[]; onClose: () => void }) {
  const [current, setCurrent] = useState(asset)
  const [draft, setDraft] = useState("")
  const setTags = useSetAssetTags()

  const commit = (tags: string[]) => {
    setTags.mutate({ asset_id: current.id, tags })
    setCurrent({ ...current, tags })
  }
  const addTag = () => {
    const t = draft.trim()
    if (t && !current.tags.includes(t)) commit([...current.tags, t])
    setDraft("")
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4" onClick={onClose}>
      <div className="max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-2xl border border-border bg-card"
        onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between border-b border-border px-5 py-3">
          <h3 className="line-clamp-1 text-[14px] font-semibold text-foreground">{current.filename}</h3>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground"><X className="h-5 w-5" /></button>
        </div>

        <div className="space-y-5 p-5">
          {/* preview */}
          <div className="overflow-hidden rounded-xl border border-border bg-secondary/30">
            {current.kind === "image" && <img src={current.media_url} alt={current.filename} className="max-h-[46vh] w-full object-contain" />}
            {current.kind === "video" && <video src={current.media_url} controls className="max-h-[46vh] w-full" />}
            {current.kind === "audio" && <audio src={current.media_url} controls className="w-full p-4" />}
          </div>

          {/* meta */}
          <div className="grid grid-cols-2 gap-3 text-[12.5px] sm:grid-cols-4">
            <Meta label="Made by" value={current.source_agent} />
            <Meta label="Status" value={STATE_LABEL[current.approval_state] ?? current.approval_state} />
            <Meta label="Type" value={current.kind} />
            <Meta label="Created" value={formatTimeAgo(new Date(current.created))} />
          </div>

          {/* tags */}
          <div>
            <p className="mb-2 flex items-center gap-1.5 text-[11px] uppercase tracking-[0.14em] text-muted-foreground">
              <TagIcon className="h-3 w-3" /> Tags
            </p>
            <div className="flex flex-wrap items-center gap-2">
              {current.tags.map((t) => (
                <span key={t} className="flex items-center gap-1 rounded-full bg-secondary px-2.5 py-1 text-[12px] text-foreground">
                  {t}
                  <button onClick={() => commit(current.tags.filter((x) => x !== t))} className="text-muted-foreground hover:text-destructive">
                    <X className="h-3 w-3" />
                  </button>
                </span>
              ))}
              <div className="flex items-center gap-1">
                <input
                  value={draft} onChange={(e) => setDraft(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter") addTag() }}
                  placeholder="add tag"
                  className="w-24 rounded-full border border-border bg-background px-2.5 py-1 text-[12px] text-foreground outline-none focus:border-primary/50"
                />
                <button onClick={addTag} className="text-muted-foreground hover:text-foreground"><Plus className="h-4 w-4" /></button>
              </div>
            </div>
          </div>

          {/* variants */}
          {variants.length > 1 && (
            <div>
              <p className="mb-2 text-[11px] uppercase tracking-[0.14em] text-muted-foreground">
                Versions ({variants.length})
              </p>
              <div className="flex flex-wrap gap-2">
                {variants.map((v) => (
                  <button key={v.id} onClick={() => setCurrent(v)}
                    className={cn("h-16 w-16 overflow-hidden rounded-lg border",
                      v.id === current.id ? "border-primary" : "border-border hover:border-primary/40")}>
                    <Thumb asset={v} />
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[10.5px] uppercase tracking-[0.12em] text-muted-foreground">{label}</p>
      <p className="mt-0.5 capitalize text-foreground/90">{value}</p>
    </div>
  )
}
