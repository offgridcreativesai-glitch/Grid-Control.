import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { motion } from "framer-motion"
import Lenis from "lenis"
import {
  ArrowRight,
  Check,
  PenTool,
  BarChart3,
  Activity,
  ShieldCheck,
  Cpu,
} from "lucide-react"
import { AgentCharacter, AGENTS, type AgentKey } from "@/components/AgentCharacter"
import { SpaceBackground } from "@/components/SpaceBackground"
import { EnergyOrb } from "@/components/EnergyOrb"
import { Wordmark } from "@/components/brand/Logo"
import { cn } from "@/lib/utils"

/* ---------- Navbar ---------- */
function Navbar() {
  const [scrolled, setScrolled] = useState(false)
  const navigate = useNavigate()
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24)
    window.addEventListener("scroll", onScroll, { passive: true })
    return () => window.removeEventListener("scroll", onScroll)
  }, [])

  const links: { label: string; id: string }[] = [
    { label: "How it works", id: "how" },
    { label: "The Grid", id: "grid" },
    { label: "Why us", id: "why" },
    { label: "Pricing", id: "pricing" },
  ]
  const go = (id: string) => document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" })
  return (
    <header
      className={cn(
        "fixed inset-x-0 top-0 z-50 transition-all duration-300",
        scrolled ? "glass-panel border-b border-border/60" : "border-b border-transparent",
      )}
    >
      <nav className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6">
        <Wordmark />
        <div className="hidden items-center gap-9 md:flex">
          {links.map((l) => (
            <button
              key={l.id}
              onClick={() => go(l.id)}
              className="text-[13px] font-medium tracking-wide text-muted-foreground transition-colors hover:text-foreground"
            >
              {l.label}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-3">
          <span className="hidden items-center gap-2 text-[11px] font-medium tracking-[0.18em] text-muted-foreground lg:flex">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald opacity-60" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald" />
            </span>
            SYSTEM ACTIVE
          </span>
          <button
            onClick={() => navigate("/signin")}
            className="text-[13px] font-medium text-muted-foreground transition-colors hover:text-foreground"
          >
            Log in
          </button>
          <button
            onClick={() => navigate("/signin?mode=signup")}
            className="rounded-full bg-primary px-4 py-2 text-[13px] font-semibold text-primary-foreground transition-transform hover:scale-[1.03]"
          >
            Sign up
          </button>
        </div>
      </nav>
    </header>
  )
}

/* ---------- Hero pieces ---------- */
const HERO_AGENTS: AgentKey[] = ["atlas", "riveter", "exactor"]

function HeroAgentCard({ agent, i }: { agent: AgentKey; i: number }) {
  const meta = AGENTS[agent]
  return (
    <motion.div
      initial={{ opacity: 0, x: -24 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: 0.15 * i, type: "spring", stiffness: 80, damping: 16 }}
      className="glass-panel rounded-2xl p-4"
      style={meta.lead ? { borderColor: "rgba(255,77,0,0.35)" } : undefined}
    >
      <div className="flex items-center gap-3">
        <div className="relative grid h-14 w-14 shrink-0 place-items-center rounded-xl bg-black/30 ring-1 ring-border">
          <img src={`/agents/${agent}.png`} alt={meta.name} className="h-12 w-12 object-contain" />
        </div>
        <div className="min-w-0">
          <p className="text-[10px] font-medium uppercase tracking-[0.2em] text-muted-foreground">
            {meta.lead ? "Chief of Staff" : meta.role}
          </p>
          <p className="font-display text-lg font-semibold text-foreground">{meta.name}</p>
          <span className="mt-0.5 inline-flex items-center gap-1.5 text-[11px] font-medium text-primary">
            <span className="h-1.5 w-1.5 rounded-full bg-primary" /> {meta.lead ? "LEADING" : "ACTIVE"}
          </span>
        </div>
      </div>
      <p className="mt-3 text-[12px] leading-relaxed text-muted-foreground">{meta.blurb}</p>
      <button className="mt-3 inline-flex items-center gap-1.5 text-[11px] font-semibold tracking-wide text-foreground/80 transition-colors hover:text-primary">
        VIEW STATUS <ArrowRight className="h-3 w-3" />
      </button>
    </motion.div>
  )
}

function Stat({ label, value, delta }: { label: string; value: string; delta: string }) {
  return (
    <div>
      <p className="text-[10px] uppercase tracking-[0.16em] text-muted-foreground">{label}</p>
      <p className="font-display text-2xl font-semibold text-foreground">{value}</p>
      <p className="text-[11px] font-medium text-emerald">↑ {delta}</p>
    </div>
  )
}

function MissionPanel() {
  const collective: AgentKey[] = ["lumen", "riveter", "exactor", "spark", "nexus"]
  return (
    <div className="space-y-4">
      <motion.div
        initial={{ opacity: 0, x: 24 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: 0.15, type: "spring", stiffness: 80, damping: 16 }}
        className="glass-panel rounded-2xl p-5"
      >
        <div className="mb-4 flex items-center justify-between">
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">Mission Overview</p>
          <span className="rounded-md border border-border px-2 py-0.5 text-[10px] text-muted-foreground">This Month</span>
        </div>
        <div className="grid grid-cols-3 gap-3">
          <Stat label="Campaigns" value="24" delta="18%" />
          <Stat label="Revenue" value="$2.4M" delta="28%" />
          <Stat label="ROAS" value="4.7x" delta="22%" />
        </div>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, x: 24 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: 0.28, type: "spring", stiffness: 80, damping: 16 }}
        className="glass-panel rounded-2xl p-5"
      >
        <p className="mb-3 text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">Orchestration Status</p>
        <div className="flex items-center gap-3">
          <span className="relative grid h-10 w-10 place-items-center rounded-full ring-2 ring-emerald/70">
            <span className="h-2 w-2 rounded-full bg-emerald" />
          </span>
          <div>
            <p className="text-sm font-semibold text-foreground">All Systems Active</p>
            <p className="text-[12px] text-muted-foreground">The grid is optimized and running at peak.</p>
          </div>
        </div>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, x: 24 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: 0.4, type: "spring", stiffness: 80, damping: 16 }}
        className="glass-panel rounded-2xl p-5"
      >
        <p className="mb-4 text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">The Grid</p>
        <div className="flex items-center justify-between">
          {collective.map((a) => (
            <div key={a} className="flex flex-col items-center gap-1.5">
              <div className="relative grid h-11 w-11 place-items-center rounded-full bg-black/30 ring-1 ring-border">
                <img src={`/agents/${a}.png`} alt={AGENTS[a].name} className="h-9 w-9 object-contain" />
                <span className="absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full border border-background bg-emerald" />
              </div>
              <span className="text-[9px] uppercase tracking-wide text-muted-foreground">{AGENTS[a].name}</span>
            </div>
          ))}
        </div>
      </motion.div>
    </div>
  )
}

function Hero() {
  const navigate = useNavigate()
  return (
    <section className="relative mx-auto max-w-7xl px-6 pb-16 pt-28">
      <div className="grid items-start gap-6 lg:grid-cols-[300px_1fr_300px]">
        {/* left agent cards */}
        <div className="order-2 space-y-4 lg:order-1">
          {HERO_AGENTS.map((a, i) => (
            <HeroAgentCard key={a} agent={a} i={i} />
          ))}
        </div>

        {/* center */}
        <div className="order-1 flex flex-col items-center text-center lg:order-2">
          <motion.h1
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="font-display text-5xl font-bold leading-[1.02] tracking-tight text-foreground md:text-6xl"
          >
            The Orchestrator of
            <br />
            Your Marketing<span className="text-primary">.</span>
          </motion.h1>
          <p className="mt-4 text-xs font-medium tracking-[0.34em] text-muted-foreground">
            WE PLAN. WE BUILD. WE <span className="text-primary">WIN.</span>
          </p>

          <div className="relative my-2 flex h-[360px] w-full items-center justify-center">
            <EnergyOrb className="h-[360px] w-[360px]" />
          </div>

          <button
            onClick={() => navigate("/signin")}
            className="group relative inline-flex items-center gap-2 rounded-full bg-primary px-9 py-3.5 text-base font-semibold text-primary-foreground shadow-[0_0_40px_-4px_rgba(255,77,0,0.6)] transition-transform hover:scale-[1.03]"
          >
            Take Control
            <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
          </button>
        </div>

        {/* right mission panel */}
        <div className="order-3">
          <MissionPanel />
        </div>
      </div>

      {/* bottom strip */}
      <div className="mt-14 grid gap-px overflow-hidden rounded-2xl border border-border bg-border/60 md:grid-cols-3">
        {[
          { icon: Cpu, t: "Unified Intelligence", d: "One mind for every move." },
          { icon: Activity, t: "Seamless Execution", d: "Precision at every step." },
          { icon: BarChart3, t: "Unrivaled Results", d: "Built for outcomes that scale." },
        ].map((f) => (
          <div key={f.t} className="flex items-center gap-3 bg-background/80 px-6 py-5">
            <f.icon className="h-5 w-5 text-muted-foreground" />
            <div>
              <p className="text-sm font-semibold text-foreground">{f.t}</p>
              <p className="text-[12px] text-muted-foreground">{f.d}</p>
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}

/* ---------- How it works ---------- */
function HowItWorks() {
  const steps = [
    { n: "01", icon: PenTool, t: "Brief your brand", d: "Tell Atlas who you are and what you sell. One conversation, no forms to dread." },
    { n: "02", icon: Cpu, t: "Agents go to work", d: "The grid researches, plans, writes and designs — in parallel, around the clock." },
    { n: "03", icon: Check, t: "You approve and ship", d: "Every output lands in your queue. Approve, tweak, or send back. You stay in control." },
  ]
  return (
    <section id="how" className="mx-auto max-w-7xl px-6 py-24">
      <h2 className="text-center font-display text-4xl font-bold tracking-tight text-foreground">How The Grid Works</h2>
      <div className="mt-14 grid gap-6 md:grid-cols-3">
        {steps.map((s, i) => (
          <motion.div
            key={s.n}
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-80px" }}
            transition={{ delay: i * 0.1 }}
            className="glass-panel rounded-2xl p-7"
          >
            <div className="flex items-center justify-between">
              <span className="grid h-11 w-11 place-items-center rounded-xl bg-primary/10 text-primary ring-1 ring-primary/30">
                <s.icon className="h-5 w-5" />
              </span>
              <span className="font-display text-3xl font-bold text-border">{s.n}</span>
            </div>
            <p className="mt-5 font-display text-xl font-semibold text-foreground">{s.t}</p>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{s.d}</p>
          </motion.div>
        ))}
      </div>
    </section>
  )
}

/* ---------- Meet the grid ---------- */
function MeetTheGrid() {
  const all = Object.keys(AGENTS) as AgentKey[]
  return (
    <section id="grid" className="relative mx-auto max-w-7xl px-6 py-24">
      <h2 className="text-center font-display text-4xl font-bold tracking-tight text-foreground">Meet The Grid</h2>
      <p className="mx-auto mt-3 max-w-xl text-center text-sm text-muted-foreground">
        Eight specialists. One chief of staff. Each an expert at a single job — together, your entire marketing team.
      </p>
      <div className="mt-12 grid grid-cols-2 gap-x-4 gap-y-10 sm:grid-cols-3 lg:grid-cols-4">
        {all.map((a, i) => (
          <motion.div
            key={a}
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-60px" }}
            transition={{ delay: (i % 4) * 0.07 }}
            className="group flex flex-col items-center text-center"
          >
            <div className="relative mb-1 grid h-56 w-full place-items-center">
              <AgentCharacter agent={a} size="lg" parallax showGlow={AGENTS[a].lead} delay={i * 0.2} />
            </div>
            <p className="mt-2 font-display text-lg font-semibold text-foreground">{AGENTS[a].name}</p>
            <p className={cn("text-[11px] font-medium uppercase tracking-[0.16em]", AGENTS[a].lead ? "text-primary" : "text-emerald")}>
              {AGENTS[a].role}
            </p>
            <p className="mt-1.5 max-w-[200px] text-[12px] leading-relaxed text-muted-foreground">{AGENTS[a].blurb}</p>
          </motion.div>
        ))}
      </div>
    </section>
  )
}

/* ---------- Why ---------- */
function WhyGridControl() {
  const feats = [
    { icon: Cpu, t: "One brain, every channel", d: "Atlas holds the whole plan. No cold starts, no repeating yourself, no silos between channels." },
    { icon: ShieldCheck, t: "Approve, don't micromanage", d: "Nothing ships without your yes. The grid does the work; you make the calls." },
    { icon: BarChart3, t: "Real data, zero guesswork", d: "Every decision traces back to a real scrape, metric or signal. No fabrication, ever." },
  ]
  return (
    <section id="why" className="mx-auto max-w-7xl px-6 py-24">
      <h2 className="text-center font-display text-4xl font-bold tracking-tight text-foreground">Why Grid Control</h2>
      <div className="mt-14 grid gap-6 md:grid-cols-3">
        {feats.map((f, i) => (
          <motion.div
            key={f.t}
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-80px" }}
            transition={{ delay: i * 0.1 }}
            className="rounded-2xl border border-border bg-card/40 p-7"
          >
            <span className="grid h-11 w-11 place-items-center rounded-xl bg-emerald/10 text-emerald ring-1 ring-emerald/30">
              <f.icon className="h-5 w-5" />
            </span>
            <p className="mt-5 font-display text-xl font-semibold text-foreground">{f.t}</p>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{f.d}</p>
          </motion.div>
        ))}
      </div>
    </section>
  )
}

/* ---------- Pricing ---------- */
function Pricing() {
  const navigate = useNavigate()
  const tiers = [
    {
      name: "Starter",
      price: "$199",
      cadence: "/mo",
      blurb: "For founders getting their first engine running.",
      feats: ["1 brand", "Core 4 agents", "30-day content calendar", "Approval queue"],
      featured: false,
    },
    {
      name: "Growth",
      price: "$599",
      cadence: "/mo",
      blurb: "For brands ready to scale what's working.",
      feats: ["3 brands", "All 8 agents", "Paid + organic", "Weekly performance reviews", "Priority orchestration"],
      featured: true,
    },
    {
      name: "Agency",
      price: "Custom",
      cadence: "",
      blurb: "For teams running many brands at once.",
      feats: ["Unlimited brands", "White-label", "Dedicated grid", "API access", "Success manager"],
      featured: false,
    },
  ]
  return (
    <section id="pricing" className="mx-auto max-w-7xl px-6 py-24">
      <h2 className="text-center font-display text-4xl font-bold tracking-tight text-foreground">Pricing</h2>
      <p className="mx-auto mt-3 max-w-md text-center text-sm text-muted-foreground">
        Start with a single brand. Scale to a portfolio when you're ready.
      </p>
      <div className="mt-14 grid items-stretch gap-6 md:grid-cols-3">
        {tiers.map((t) => (
          <div
            key={t.name}
            className={cn(
              "relative flex flex-col rounded-2xl border p-7",
              t.featured ? "border-primary/50 bg-primary/[0.06] shadow-[0_0_50px_-12px_rgba(255,77,0,0.5)]" : "border-border bg-card/40",
            )}
          >
            {t.featured && (
              <span className="absolute -top-3 left-7 rounded-full bg-primary px-3 py-1 text-[10px] font-bold uppercase tracking-wider text-primary-foreground">
                Most popular
              </span>
            )}
            <p className="font-display text-lg font-semibold text-foreground">{t.name}</p>
            <p className="mt-3 flex items-end gap-1">
              <span className="font-display text-4xl font-bold text-foreground">{t.price}</span>
              <span className="pb-1 text-sm text-muted-foreground">{t.cadence}</span>
            </p>
            <p className="mt-2 text-[13px] text-muted-foreground">{t.blurb}</p>
            <ul className="mt-6 flex-1 space-y-2.5">
              {t.feats.map((f) => (
                <li key={f} className="flex items-center gap-2.5 text-sm text-foreground/85">
                  <Check className={cn("h-4 w-4 shrink-0", t.featured ? "text-primary" : "text-emerald")} /> {f}
                </li>
              ))}
            </ul>
            <button
              onClick={() => navigate("/signin")}
              className={cn(
                "mt-7 inline-flex items-center justify-center gap-2 rounded-full px-6 py-3 text-sm font-semibold transition-transform hover:scale-[1.02]",
                t.featured
                  ? "bg-primary text-primary-foreground shadow-[0_0_30px_-6px_rgba(255,77,0,0.6)]"
                  : "border border-border text-foreground hover:border-primary/50",
              )}
            >
              {t.name === "Agency" ? "Talk to us" : "Get started"} <ArrowRight className="h-4 w-4" />
            </button>
          </div>
        ))}
      </div>
    </section>
  )
}

/* ---------- Footer ---------- */
function Footer() {
  return (
    <footer className="border-t border-border">
      <div className="mx-auto flex max-w-7xl flex-col items-center gap-6 px-6 py-12 md:flex-row md:justify-between">
        <div className="flex flex-col items-center gap-2 md:items-start">
          <Wordmark small />
          <p className="font-serif text-sm italic text-primary">Take control.</p>
        </div>
        <div className="flex items-center gap-7 text-[13px] text-muted-foreground">
          {[
            { label: "How it works", id: "how" },
            { label: "The Grid", id: "grid" },
            { label: "Why us", id: "why" },
            { label: "Pricing", id: "pricing" },
          ].map((l) => (
            <button
              key={l.id}
              onClick={() => document.getElementById(l.id)?.scrollIntoView({ behavior: "smooth" })}
              className="transition-colors hover:text-foreground"
            >
              {l.label}
            </button>
          ))}
        </div>
        <p className="text-[12px] text-muted-foreground">© {new Date().getFullYear()} Grid Control</p>
      </div>
    </footer>
  )
}

/* ---------- Page ---------- */
export function LandingPage() {
  useEffect(() => {
    const lenis = new Lenis({ duration: 1.1, smoothWheel: true })
    let raf = 0
    const loop = (t: number) => {
      lenis.raf(t)
      raf = requestAnimationFrame(loop)
    }
    raf = requestAnimationFrame(loop)
    return () => {
      cancelAnimationFrame(raf)
      lenis.destroy()
    }
  }, [])

  return (
    <div className="relative min-h-screen overflow-x-hidden text-foreground">
      <SpaceBackground />
      <Navbar />
      <main>
        <Hero />
        <HowItWorks />
        <MeetTheGrid />
        <WhyGridControl />
        <Pricing />
      </main>
      <Footer />
    </div>
  )
}

export default LandingPage
