/**
 * Cockpit primitives — ported from the Claude Design handoff (ui.jsx) to TS.
 *
 * These deliberately use a self-contained palette (hardcoded hex + white/[0.0x])
 * rather than the app's oklch tokens, so the cockpit's editorial visual language
 * renders identically regardless of the global theme. The ONE accent
 * (#7c6fe6 purple) is read from the `--accent` CSS var, which each cockpit page
 * scopes on its root via CockpitRoot below.
 */
import { type ReactNode, type CSSProperties, type ComponentType } from "react"

export const ACCENT = "#7c6fe6"

/** Wrap any cockpit page in this to scope the purple accent locally. */
export function CockpitRoot({
  children,
  className = "",
  style = {},
}: {
  children: ReactNode
  className?: string
  style?: CSSProperties
}) {
  return (
    <div
      className={"min-h-full bg-[#0b0c0e] text-zinc-100 " + className}
      style={{ ["--accent" as any]: ACCENT, ...style }}
    >
      {children}
    </div>
  )
}

export const STATUS: Record<
  "amber" | "blue" | "green" | "red" | "gray",
  { fg: string; bg: string; bd: string }
> = {
  amber: { fg: "#e0b873", bg: "rgba(224,184,115,0.12)", bd: "rgba(224,184,115,0.22)" },
  blue: { fg: "#86a8e6", bg: "rgba(134,168,230,0.12)", bd: "rgba(134,168,230,0.22)" },
  green: { fg: "#7ec6a3", bg: "rgba(126,198,163,0.12)", bd: "rgba(126,198,163,0.22)" },
  red: { fg: "#e09090", bg: "rgba(224,144,144,0.10)", bd: "rgba(224,144,144,0.20)" },
  gray: { fg: "#9aa0a8", bg: "rgba(255,255,255,0.05)", bd: "rgba(255,255,255,0.09)" },
}

export const VERDICT_TONE: Record<"PIVOT" | "TRACK" | "STAY", keyof typeof STATUS> = {
  PIVOT: "amber",
  TRACK: "blue",
  STAY: "green",
}

export function Card({
  className = "",
  children,
  ...rest
}: { className?: string; children: ReactNode } & React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={"rounded-2xl border border-white/[0.07] bg-[#141518] " + className}
      style={{ boxShadow: "0 1px 0 rgba(255,255,255,0.02) inset, 0 8px 24px -16px rgba(0,0,0,0.6)" }}
      {...rest}
    >
      {children}
    </div>
  )
}

export function Eyebrow({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={
        "font-mono text-[10.5px] uppercase tracking-[0.16em] text-zinc-500 " + className
      }
    >
      {children}
    </div>
  )
}

export function ModuleHeader({
  title,
  sub,
  right,
}: {
  title: string
  sub?: string
  right?: ReactNode
}) {
  return (
    <div className="flex items-start justify-between gap-4">
      <div>
        <h2 className="text-[15px] font-semibold tracking-tight text-zinc-100">{title}</h2>
        {sub && <div className="mt-1 font-mono text-[11px] text-zinc-500">{sub}</div>}
      </div>
      {right}
    </div>
  )
}

type IconType = ComponentType<{ size?: number | string; className?: string }>

export function SoftButton({
  children,
  onClick,
  className = "",
  icon: I,
  disabled,
}: {
  children: ReactNode
  onClick?: () => void
  className?: string
  icon?: IconType
  disabled?: boolean
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={
        "inline-flex items-center gap-1.5 rounded-lg border border-white/[0.08] bg-white/[0.02] px-3 py-1.5 text-[12.5px] font-medium text-zinc-300 transition-colors hover:border-white/[0.14] hover:bg-white/[0.05] disabled:opacity-40 " +
        className
      }
    >
      {I && <I size={14} className="text-zinc-400" />}
      {children}
    </button>
  )
}

export function PrimaryButton({
  children,
  onClick,
  className = "",
  icon: I,
  disabled,
}: {
  children: ReactNode
  onClick?: () => void
  className?: string
  icon?: IconType
  disabled?: boolean
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={
        "inline-flex items-center justify-center gap-2 rounded-lg px-3.5 py-2 text-[13px] font-semibold text-white transition-[filter,transform] hover:brightness-110 active:scale-[0.99] disabled:opacity-40 " +
        className
      }
      style={{
        background: "var(--accent)",
        boxShadow: "0 6px 20px -8px color-mix(in oklab, var(--accent) 70%, transparent)",
      }}
    >
      {I && <I size={15} />}
      {children}
    </button>
  )
}

export function Sparkline({
  data,
  color = "#86a8e6",
  w = 96,
  h = 30,
}: {
  data: number[]
  color?: string
  w?: number
  h?: number
}) {
  if (!data || data.length < 2) return <svg width={w} height={h} />
  const min = Math.min(...data)
  const max = Math.max(...data)
  const span = max - min || 1
  const pts = data.map((d, i) => {
    const x = (i / (data.length - 1)) * (w - 2) + 1
    const y = h - 2 - ((d - min) / span) * (h - 6)
    return `${x.toFixed(1)},${y.toFixed(1)}`
  })
  const last = pts[pts.length - 1].split(",")
  return (
    <svg width={w} height={h} className="overflow-visible">
      <polyline
        points={pts.join(" ")}
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity="0.9"
      />
      <circle cx={last[0]} cy={last[1]} r="2" fill={color} />
    </svg>
  )
}

export function StatusDot({
  tone,
  pulse = false,
  title,
}: {
  tone: keyof typeof STATUS
  pulse?: boolean
  title?: string
}) {
  const color = STATUS[tone].fg
  return (
    <span
      className="relative grid place-items-center"
      style={{ width: 8, height: 8 }}
      title={title}
    >
      {pulse && (
        <span
          className="absolute inset-0 rounded-full"
          style={{ background: color, animation: "agentpulse 1.8s ease-out infinite" }}
        />
      )}
      <span className="relative h-2 w-2 rounded-full" style={{ background: color }} />
    </span>
  )
}

export function VerdictPill({ verdict }: { verdict: "PIVOT" | "TRACK" | "STAY" }) {
  const s = STATUS[VERDICT_TONE[verdict]]
  return (
    <span
      className="inline-flex items-center rounded-md px-2 py-0.5 font-mono text-[11px] font-semibold tracking-[0.08em]"
      style={{ color: s.fg, background: s.bg, border: "1px solid " + s.bd }}
    >
      {verdict}
    </span>
  )
}
