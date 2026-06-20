import "./cockpit.css"

const NAV = [
  ["Command Center", true],
  ["The Floor", false],
  ["Work", false],
  ["Results", false],
] as const

const APPROVALS = [
  { title: "Launch carousel — 6 slides", by: "Made by Lumen", c: "#FF4D00" },
  { title: "Week 1 hooks — 3 options", by: "Made by Riveter", c: "#2FBF98" },
  { title: "Competitor teardown — Q2", by: "Made by Scout", c: "#34D399" },
]

const FLOOR = [
  { n: "Atlas", r: "Chief of Staff", c: "#FF4D00", s: "Coordinating this week’s plan", t: "work", tag: "Working" },
  { n: "Lumen", r: "Creative", c: "#FF4D00", s: "Designing your launch carousel", t: "work", tag: "Working" },
  { n: "Scout", r: "Strategist", c: "#34D399", s: "Competitor teardown ready", t: "done", tag: "Ready" },
  { n: "Riveter", r: "Writer", c: "#2FBF98", s: "3 hooks ready for review", t: "done", tag: "Ready" },
  { n: "Cadence", r: "Planner", c: "#34D399", s: "Next sprint queued", t: "queue", tag: "Queued" },
  { n: "Gauge", r: "Analyst", c: "#2FBF98", s: "Weekly read at 6pm", t: "queue", tag: "Queued" },
]

function Visor({ c, sm }: { c: string; sm?: boolean }) {
  return (
    <div className="visor" style={{ background: c, width: sm ? 22 : 28 }}>
      <i />
      <i />
    </div>
  )
}

export function CockpitPage() {
  return (
    <div className="gc-cockpit">
      <aside className="cp-rail">
        <div className="cp-brand">
          grid<b>·</b>control
        </div>
        <div className="cp-railsec">Your deck</div>
        <nav className="cp-nav">
          {NAV.map(([label, on]) => (
            <div key={label} className={"cp-navi" + (on ? " on" : "")}>
              {label}
            </div>
          ))}
        </nav>
        <div className="cp-railsec">Account</div>
        <nav className="cp-nav">
          <div className="cp-navi">Settings</div>
          <div className="cp-navi">Help</div>
        </nav>
        <div className="cp-brandswitch">
          <div className="cp-bs-orb">A</div>
          <div>
            <div className="cp-bs-name">AskGaurav AI</div>
            <div className="cp-bs-sub">Phase 1 · Awareness</div>
          </div>
        </div>
      </aside>

      <main className="cp-main">
        <div className="cp-top">
          <h1>Command Center</h1>
          <div className="meta">
            <span className="cp-live">
              <span className="pulse" /> Team live
            </span>
            <span>SAT 20 JUN · 11:42</span>
          </div>
        </div>

        <div className="cp-body">
          <div className="cp-brief">
            <div className="cp-avatar">
              <Visor c="#FF4D00" />
            </div>
            <div>
              <div className="who">Atlas · your Chief of Staff</div>
              <div className="say">
                Morning, Gaurav. <b>Lumen</b> finished your launch carousel and <b>Riveter</b> has
                three hooks ready — both waiting on your call. <b>Scout</b> just dropped the
                competitor teardown. The rest of the crew is on this week’s plan.
              </div>
            </div>
          </div>

          <div className="cp-grid">
            <section>
              <div className="cp-h">
                <span className="lbl">Needs your approval</span>
                <span className="cnt">03 waiting</span>
              </div>
              <div className="cp-appr">
                {APPROVALS.map((a) => (
                  <div className="cp-card" key={a.title}>
                    <div className="row">
                      <div className="cp-thumb">
                        <Visor c={a.c} sm />
                      </div>
                      <div style={{ flex: 1 }}>
                        <div className="title">{a.title}</div>
                        <div className="by">{a.by} · ready for you</div>
                      </div>
                      <span className="cp-chip ready">Ready</span>
                    </div>
                    <div className="cp-acts">
                      <button className="cp-btn ghost">Request changes</button>
                      <button className="cp-btn lava">Approve</button>
                    </div>
                  </div>
                ))}
              </div>
            </section>

            <section>
              <div className="cp-h">
                <span className="lbl">On the floor now</span>
                <span className="cnt">09 crew</span>
              </div>
              <div className="cp-floor">
                {FLOOR.map((f) => (
                  <div className="cp-fitem" key={f.n}>
                    <div className="cp-forb">
                      <Visor c={f.c} sm />
                    </div>
                    <div>
                      <div className="cp-fname">{f.n}</div>
                      <div className="cp-frole">{f.r}</div>
                    </div>
                    <div className="cp-fstat">
                      <div className="s">{f.s}</div>
                      <span className={"tag " + f.t}>
                        <span className="d" /> {f.tag}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          </div>
        </div>
      </main>
    </div>
  )
}
