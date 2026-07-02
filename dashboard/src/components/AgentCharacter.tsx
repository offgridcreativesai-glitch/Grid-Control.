import { type MouseEvent } from "react"
import { motion, useMotionValue, useSpring, useTransform } from "framer-motion"
import { cn } from "@/lib/utils"

export type AgentKey =
  | "atlas"
  | "riveter"
  | "aegis"
  | "exactor"
  | "spark"
  | "lumen"
  | "nexus"
  | "forge"

type Size = "sm" | "md" | "lg" | "xl"

const SIZE_PX: Record<Size, number> = { sm: 64, md: 120, lg: 220, xl: 360 }

interface AgentInfo {
  name: string
  role: string
  blurb: string
  /* lead accent (Atlas = lava, the rest = emerald/teal) */
  lead?: boolean
}

export const AGENTS: Record<AgentKey, AgentInfo> = {
  atlas: { name: "Atlas", role: "Chief of Staff", blurb: "Orchestrates the whole grid and keeps every move on plan.", lead: true },
  riveter: { name: "Riveter", role: "Content Architect", blurb: "Crafts content that connects and converts." },
  aegis: { name: "Aegis", role: "Brand Guardian", blurb: "Protects the soul of your brand on every asset." },
  exactor: { name: "Exactor", role: "Performance Analyst", blurb: "Turns data into decisive action." },
  spark: { name: "Spark", role: "Trend Researcher", blurb: "Hunts signals before they become noise." },
  lumen: { name: "Lumen", role: "Creative Director", blurb: "Designs visuals built to stop the scroll." },
  nexus: { name: "Nexus", role: "Community Manager", blurb: "Speaks for you across every conversation." },
  forge: { name: "Forge", role: "Builder", blurb: "Ships pages, funnels and the things that go live." },
}

export function agentMeta(agent: AgentKey): AgentInfo {
  return AGENTS[agent]
}

interface Props {
  agent: AgentKey
  size?: Size
  isActive?: boolean
  showGlow?: boolean
  parallax?: boolean
  /** disable idle float/sway/breathe + parallax — render a still, glowing portrait */
  still?: boolean
  className?: string
  /** offset float/sway timing so a row of agents feels independent */
  delay?: number
}

export function AgentCharacter({
  agent,
  size = "md",
  isActive = false,
  showGlow = false,
  parallax = false,
  still = false,
  className,
  delay = 0,
}: Props) {
  const px = SIZE_PX[size]
  const par = parallax && !still

  // Per-agent timing variance so a row of bots breathes out of sync = alive, not robotic loops.
  const seed = agent.charCodeAt(0) + agent.charCodeAt(agent.length - 1) + agent.length
  const floatDur = 2.6 + (seed % 7) * 0.16 // ~2.6–3.6s
  const swayDur = 4.0 + (seed % 5) * 0.24 // ~4.0–5.0s
  const breatheDur = 4.4 + (seed % 6) * 0.22 // ~4.4–5.5s

  // Mouse parallax — shift up to ±15px, smoothed by a spring.
  const mx = useMotionValue(0)
  const my = useMotionValue(0)
  const sx = useSpring(mx, { stiffness: 120, damping: 18, mass: 0.4 })
  const sy = useSpring(my, { stiffness: 120, damping: 18, mass: 0.4 })
  const px15 = useTransform(sx, [-0.5, 0.5], [-15, 15])
  const py15 = useTransform(sy, [-0.5, 0.5], [-15, 15])

  function onMove(e: MouseEvent<HTMLDivElement>) {
    if (!par) return
    const r = e.currentTarget.getBoundingClientRect()
    mx.set((e.clientX - r.left) / r.width - 0.5)
    my.set((e.clientY - r.top) / r.height - 0.5)
  }
  function onLeave() {
    mx.set(0)
    my.set(0)
  }

  const restGlow = showGlow
    ? "drop-shadow(0 0 26px rgba(255,77,0,0.4))"
    : "drop-shadow(0 16px 30px rgba(0,0,0,0.55))"

  return (
    <motion.div
      onMouseMove={onMove}
      onMouseLeave={onLeave}
      className={cn("relative inline-flex items-center justify-center", className)}
      style={{ width: px, height: px, x: par ? px15 : 0, y: par ? py15 : 0 }}
      initial={{ opacity: 0, y: 40 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: "spring", stiffness: 90, damping: 14 }}
    >
      {/* active pulsing ring */}
      {isActive && (
        <span
          aria-hidden
          className="pointer-events-none absolute inset-[6%] rounded-full"
          style={{ boxShadow: "0 0 0 2px var(--lava), 0 0 24px 2px rgba(255,77,0,0.5)", animation: "agentPulse 1.8s ease-out infinite" }}
        />
      )}

      {/* soft contact-shadow (breathes with the float when alive) */}
      <motion.span
        aria-hidden
        className="pointer-events-none absolute bottom-[2%] left-1/2 h-3 w-2/3 -translate-x-1/2 rounded-[50%]"
        style={{ background: "radial-gradient(50% 100% at 50% 0%, rgba(0,0,0,0.5), transparent 70%)" }}
        animate={still ? undefined : { scaleX: [1, 0.82, 1], opacity: [0.5, 0.32, 0.5] }}
        transition={still ? undefined : { duration: floatDur, repeat: Infinity, ease: "easeInOut", delay }}
      />

      {/* float loop (vertical bob) */}
      <motion.div
        className="h-full w-full"
        animate={still ? undefined : { y: [0, -16, 0] }}
        transition={still ? undefined : { duration: floatDur, repeat: Infinity, ease: "easeInOut", delay }}
      >
        {/* sway loop (gentle tilt) */}
        <motion.div
          className="h-full w-full"
          animate={still ? undefined : { rotate: [-2.5, 2.5, -2.5] }}
          transition={still ? undefined : { duration: swayDur, repeat: Infinity, ease: "easeInOut", delay: delay * 0.5 }}
        >
          {/* breathe loop (idle scale) */}
          <motion.div
            className="h-full w-full"
            animate={still ? undefined : { scale: [1, 1.04, 1] }}
            transition={still ? undefined : { duration: breatheDur, repeat: Infinity, ease: "easeInOut", delay: delay * 0.3 }}
          >
            {/* hover state */}
            <motion.div
              className="h-full w-full cursor-pointer"
              whileHover={{ scale: 1.09, filter: "drop-shadow(0 0 22px rgba(255,77,0,0.6))" }}
              transition={{ type: "spring", stiffness: 260, damping: 18 }}
            >
              <img
                src={`/agents/${agent}.png`}
                alt={AGENTS[agent].name}
                draggable={false}
                loading="lazy"
                className="h-full w-full select-none object-contain"
                style={{ filter: restGlow }}
              />
            </motion.div>
          </motion.div>
        </motion.div>
      </motion.div>
    </motion.div>
  )
}
