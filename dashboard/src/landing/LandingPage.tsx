import { useEffect, useRef } from "react"
import Lenis from "lenis"
import { gsap } from "gsap"
import { ScrollTrigger } from "gsap/ScrollTrigger"
import { TeamConstellation } from "./TeamConstellation"
import "./landing.css"

gsap.registerPlugin(ScrollTrigger)

const WORK = [
  { t: "30-Day Awareness Launch", s: "Strategy · Content · Growth", g: "#FF4D00,#8B1E00" },
  { t: "Launch Carousel — 6 slides", s: "Creative · Copy", g: "#0A5E4E,#103F46" },
  { t: "Competitor Teardown, Q2", s: "Research · Strategy", g: "#1F8E78,#0A5E4E" },
  { t: "Week 1 Hooks — 3 options", s: "Copy · Voice", g: "#FF6A2B,#993C1D" },
  { t: "Brand Voice System", s: "Strategy · Brand", g: "#2A8E80,#103F46" },
  { t: "Reels Engine — weekly", s: "Creative · Video", g: "#16A07E,#0A5E4E" },
]

const TEAM = [
  { n: "Atlas", r: "Chief of Staff", c: "#FF4D00", d: "The one you talk to. Takes your goal and runs the whole crew so you never manage the work." },
  { n: "Lumen", r: "Creative", c: "#FF6A2B", d: "Turns the plan into carousels, reels and visuals that look like a brand, not a template." },
  { n: "Scout", r: "Strategist", c: "#16A07E", d: "Reads the market and your competitors, then maps the 90 days before anyone writes a word." },
]

export function LandingPage() {
  const root = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const lenis = new Lenis({ duration: 1.2, smoothWheel: true })
    let raf = 0
    const loop = (t: number) => { lenis.raf(t); raf = requestAnimationFrame(loop) }
    raf = requestAnimationFrame(loop)
    lenis.on("scroll", ScrollTrigger.update)

    const ctx = gsap.context(() => {
      gsap.from(".gc-hero [data-rise]", { y: 40, opacity: 0, duration: 1.2, ease: "power3.out", stagger: 0.14, delay: 0.1 })
      gsap.utils.toArray<HTMLElement>("[data-reveal]").forEach((el) => {
        gsap.from(el, { y: 46, opacity: 0, duration: 1.1, ease: "power3.out", scrollTrigger: { trigger: el, start: "top 85%" } })
      })
      gsap.from(".gc-work-item", { y: 50, opacity: 0, duration: 0.9, ease: "power3.out", stagger: 0.08, scrollTrigger: { trigger: ".gc-work-grid", start: "top 82%" } })
      gsap.from(".gc-tm", { y: 46, opacity: 0, duration: 0.9, ease: "power3.out", stagger: 0.1, scrollTrigger: { trigger: ".gc-team-grid", start: "top 82%" } })
    }, root)

    return () => { ctx.revert(); lenis.destroy(); cancelAnimationFrame(raf) }
  }, [])

  return (
    <div className="gc-landing" ref={root}>
      <nav className="gc-nav">
        <div className="wrap">
          <div className="gc-mark">grid<b>·</b>control</div>
          <div className="gc-navr">
            <a href="#work">Work</a>
            <a href="#team">The team</a>
            <a href="#how">How it works</a>
            <a href="#" className="em">Sign in</a>
          </div>
        </div>
      </nav>

      <header className="gc-hero">
        <div className="gc-hero-bg"><TeamConstellation /></div>
        <div className="inner wrap">
          <h1 className="gc-h1" data-rise>
            we build the marketing<br />your brand <em>deserves</em>.
          </h1>
          <div className="gc-ann" data-rise>
            <span>Grid Control runs your marketing with a team of nine AI specialists</span>
            <span className="pill">→</span>
          </div>
        </div>
      </header>

      <section className="gc-feat" id="work">
        <div className="wrap">
          <div className="card" data-reveal>
            <div className="viz"><TeamConstellation /></div>
            <div className="meta">
              <h3>AskGaurav AI — Phase 1, Awareness</h3>
              <div className="tags">
                <span>Strategy</span><span>Content</span><span>Creative</span><span>Growth</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="gc-work">
        <div className="wrap">
          <div className="gc-sec-head" data-reveal>
            <h2>The work</h2>
            <a href="#">Everything the team makes →</a>
          </div>
          <div className="gc-work-grid">
            {WORK.map((w) => (
              <div className="gc-work-item" key={w.t}>
                <div className="gc-work-thumb">
                  <div className="blob" style={{ background: `radial-gradient(120% 120% at 30% 20%, ${w.g.split(",")[0]}, ${w.g.split(",")[1]})` }} />
                </div>
                <h4>{w.t}</h4>
                <div className="wt">{w.s}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="gc-vp" id="how">
        <div className="wrap">
          <h2 data-reveal>We turn one <em>conversation</em> into a month of marketing</h2>
          <p data-reveal>
            Tell your Chief of Staff the goal. Nine specialists plan it, write it, design it,
            and bring every piece back to you for approval. You stay in control. The work just gets done.
          </p>
        </div>
      </section>

      <section className="gc-team" id="team">
        <div className="wrap">
          <div className="gc-sec-head" data-reveal>
            <h2>Your team</h2>
            <a href="#">Meet all nine →</a>
          </div>
          <div className="gc-team-grid">
            {TEAM.map((m) => (
              <div className="gc-tm" key={m.n}>
                <div className="bub" style={{ background: m.c }}><div className="face"><i /><i /></div></div>
                <h4>{m.n}</h4>
                <div className="role">{m.r}</div>
                <p>{m.d}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="gc-cta-sec">
        <div className="wrap" data-reveal>
          <h2>Ready to put a team to <em>work</em>?</h2>
          <button className="gc-btn gc-btn-lava">Get your command deck</button>
        </div>
      </section>

      <footer className="gc-foot">
        <div className="wrap">
          <div className="gc-foot-top">
            <div className="gc-mark">grid<b>·</b>control</div>
            <div className="gc-foot-cols">
              <div className="gc-foot-col"><b>Product</b><a href="#">Work</a><a href="#">The team</a><a href="#">How it works</a></div>
              <div className="gc-foot-col"><b>Company</b><a href="#">About</a><a href="#">Contact</a><a href="#">Sign in</a></div>
              <div className="gc-foot-col"><b>Social</b><a href="#">LinkedIn</a><a href="#">Instagram</a><a href="#">YouTube</a></div>
            </div>
          </div>
          <div className="gc-foot-bot">
            <span>© 2026 Grid Control</span>
            <span>A team you direct. Work you approve.</span>
          </div>
        </div>
      </footer>
    </div>
  )
}
