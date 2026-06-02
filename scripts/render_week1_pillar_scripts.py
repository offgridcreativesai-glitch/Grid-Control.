"""
Render Week 1 Pillar Scripts for ASKGauravAI + OffGrid Creatives AI → HTML → PDF.
Uses Chrome headless for PDF conversion.

Outputs:
  brands/askgauravai/deliverables/{date}/pillar_script_askgauravai.{html,pdf}
  brands/askgauravai/deliverables/{date}/pillar_script_offgridcreatives.{html,pdf}
"""
import subprocess
from datetime import datetime
from pathlib import Path

BRAND_DIR = Path("/Users/gauravoffgrid/offgrid-marketing-os/brands/askgauravai")
DATESTAMP = datetime.now().strftime("%Y%m%d")
OUT_DIR = BRAND_DIR / "deliverables" / DATESTAMP
OUT_DIR.mkdir(parents=True, exist_ok=True)
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

CSS = """
@page { size: A4; margin: 18mm 16mm 18mm 16mm; }
* { box-sizing: border-box; }
body {
  font-family: -apple-system, 'SF Pro Text', 'Helvetica Neue', Helvetica, Arial, sans-serif;
  color: #1A1A1A;
  background: #FFFFFF;
  font-size: 10.5pt;
  line-height: 1.65;
  margin: 0;
}
h1 { font-size: 26pt; color: #0F4C5C; margin: 0 0 4pt 0; letter-spacing: -0.4pt; font-weight: 700; }
h2 { font-size: 16pt; color: #0F4C5C; margin: 26pt 0 8pt 0; font-weight: 600; border-bottom: 1.5pt solid #0F4C5C; padding-bottom: 3pt; }
h3 { font-size: 12pt; color: #1A1A1A; margin: 16pt 0 6pt 0; font-weight: 600; }
h4 { font-size: 10pt; color: #0F4C5C; margin: 12pt 0 4pt 0; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5pt; }
p { margin: 0 0 7pt 0; }
.muted { color: #6B7280; font-size: 9pt; }
.kicker { color: #0F4C5C; font-size: 9pt; text-transform: uppercase; letter-spacing: 1pt; font-weight: 600; margin-bottom: 2pt; }
.cover { padding: 50pt 0 30pt 0; border-bottom: 2pt solid #0F4C5C; margin-bottom: 28pt; }
.cover h1 { font-size: 34pt; line-height: 1.15; }
.cover .subtitle { font-size: 14pt; color: #6B7280; margin-top: 8pt; font-weight: 400; }
.cover .meta { color: #6B7280; font-size: 9.5pt; margin-top: 16pt; }

.section-label {
  display: inline-block;
  background: #0F4C5C;
  color: #FFFFFF;
  padding: 3pt 10pt;
  border-radius: 12pt;
  font-size: 8.5pt;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5pt;
  margin-bottom: 8pt;
}

.speak-block {
  background: #F0F7F9;
  border-left: 3pt solid #0F4C5C;
  padding: 12pt 16pt;
  margin: 8pt 0 14pt 0;
  border-radius: 0 4pt 4pt 0;
  page-break-inside: avoid;
  font-size: 11pt;
  line-height: 1.7;
}

.speak-label {
  font-size: 8pt;
  color: #0F4C5C;
  text-transform: uppercase;
  letter-spacing: 1pt;
  font-weight: 700;
  margin-bottom: 4pt;
}

.direction-block {
  background: #FFF7ED;
  border-left: 3pt solid #E07A5F;
  padding: 10pt 14pt;
  margin: 8pt 0 14pt 0;
  border-radius: 0 4pt 4pt 0;
  font-size: 9.5pt;
  color: #6B7280;
  page-break-inside: avoid;
}

.direction-label {
  font-size: 8pt;
  color: #E07A5F;
  text-transform: uppercase;
  letter-spacing: 1pt;
  font-weight: 700;
  margin-bottom: 4pt;
}

.time-marker {
  display: inline-block;
  background: #E5E7EB;
  padding: 2pt 8pt;
  border-radius: 10pt;
  font-size: 8pt;
  color: #6B7280;
  font-weight: 600;
  margin-bottom: 6pt;
}

.callout {
  background: #FAFAFA;
  border: 1pt solid #E5E7EB;
  padding: 12pt 16pt;
  margin: 12pt 0;
  border-radius: 4pt;
  page-break-inside: avoid;
}

.highlight { background: #E07A5F; color: #FFFFFF; padding: 1pt 5pt; border-radius: 2pt; font-weight: 600; }

ul { margin: 4pt 0 8pt 18pt; padding: 0; }
li { margin-bottom: 4pt; }

.page-break { page-break-before: always; }
"""

# ─────────────────────────────────────────────
# SCRIPT 1: ASKGauravAI Pillar
# ─────────────────────────────────────────────
ASKGAURAV_HTML = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><style>{CSS}</style></head><body>

<div class="cover">
  <div class="kicker">ASKGauravAI &middot; Week 1 Pillar Script</div>
  <h1>I Built an AI System That Runs My Entire Marketing &mdash; and I&rsquo;ve Never Written a Line of Code</h1>
  <div class="subtitle">YouTube Long-Form &middot; 12&ndash;15 Minutes &middot; Introduction Video</div>
  <div class="meta">
    Profile: ASKGauravAI &middot; Platform: YouTube (pillar) &middot; Derivatives: IG Reels, Shorts, LinkedIn, X, TikTok<br>
    Generated: {datetime.now().strftime("%B %d, %Y")} &middot; Language: English Only &middot; Content Model: GaryVee Pillar
  </div>
</div>

<!-- ───── OVERVIEW ───── -->
<div class="callout">
  <strong>Script Overview</strong><br>
  This is an introduction video. The goal is not to sell anything. The goal is to make the viewer think: <em>&ldquo;This person is actually building something real. I want to follow this.&rdquo;</em><br><br>
  <strong>Tone:</strong> Calm, honest, founder-to-founder. Not a pitch. Not a tutorial. A story about what you built and why.<br>
  <strong>On Camera:</strong> Gaurav, talking head. Mix with screen recordings of the dashboard and PDF deliverables.<br>
  <strong>No Hinglish.</strong> English only. Global audience.<br>
  <strong>Grid Control Rule:</strong> Do NOT name &ldquo;Grid Control&rdquo; in this video. Call it &ldquo;a system I built&rdquo; / &ldquo;my AI system&rdquo; / &ldquo;something I&rsquo;ve been building.&rdquo;
</div>

<!-- ───── SECTION 1: HOOK ───── -->
<h2>Section 1 &mdash; The Hook</h2>
<span class="time-marker">0:00 &ndash; 0:30</span>

<div class="direction-block">
  <div class="direction-label">Camera Direction</div>
  Talking head, tight frame. Eye contact. No intro music, no logo animation. Start talking immediately. Raw.
</div>

<div class="speak-block">
  <div class="speak-label">Gaurav Says</div>
  Most founders I talk to are spending somewhere between fifteen thousand and fifty thousand rupees a month on a marketing agency. And the agency sends them a content calendar that looks like it was made in thirty minutes &mdash; because it was.<br><br>
  I was one of those founders. I ran brands, I hired agencies, I sat in those calls where they showed me Canva templates and called it a strategy. And at some point I thought &mdash; there has to be a better way to do this.<br><br>
  So I built something. An AI system &mdash; eighteen agents, working together, doing strategy, content planning, scripting, design, trend research, competitor analysis &mdash; all of it. And I have never written a single line of code in my life.<br><br>
  This is the story of how I built it, what it actually does, and why I think most founders are making a mistake they don&rsquo;t even know they&rsquo;re making.
</div>

<!-- ───── SECTION 2: THE PROBLEM ───── -->
<h2>Section 2 &mdash; The Problem</h2>
<span class="time-marker">0:30 &ndash; 3:00</span>

<div class="direction-block">
  <div class="direction-label">Camera Direction</div>
  Talking head. Keep it conversational. You&rsquo;re explaining this to a friend who just asked &ldquo;what are you building?&rdquo;
</div>

<div class="speak-block">
  <div class="speak-label">Gaurav Says</div>
  Here&rsquo;s what most people don&rsquo;t realize about marketing agencies. When you hire an agency &mdash; whether it&rsquo;s for social media, for ads, for content &mdash; what you&rsquo;re actually paying for is not intelligence. You&rsquo;re paying for execution. Someone makes your posts. Someone schedules them. Someone writes captions that sound like every other brand in your category.<br><br>
  But the intelligence part &mdash; the part where someone actually researches what&rsquo;s working in your space, who your competitors are, what hooks are getting engagement, what formats your audience responds to &mdash; that almost never happens. Because real research takes time. And agencies are running fifteen to twenty accounts at once. They don&rsquo;t have time to research yours.<br><br>
  So what happens? You get a content calendar based on trends that are already dead. You get captions written by a twenty-two year old who&rsquo;s never run a business. You get &ldquo;strategy&rdquo; that&rsquo;s actually just a posting schedule.<br><br>
  And the worst part? You don&rsquo;t know what you&rsquo;re missing. Because you&rsquo;ve never seen what real intelligence-driven marketing looks like. You have no reference point.<br><br>
  The pattern I keep seeing is this &mdash; founders think their content problem is creativity. It&rsquo;s not. Their problem is data. They have no data on what actually works in their category. So they&rsquo;re guessing. Every single post is a guess.
</div>

<!-- ───── SECTION 3: THE JOURNEY ───── -->
<h2>Section 3 &mdash; How I Built It</h2>
<span class="time-marker">3:00 &ndash; 7:00</span>

<div class="direction-block">
  <div class="direction-label">Camera Direction</div>
  Talking head for the narrative parts. Cut to screen recordings when showing the system &mdash; the dashboard, the agents running, the outputs. Keep the screen recordings short (10&ndash;15 seconds each), then back to face.
</div>

<div class="speak-block">
  <div class="speak-label">Gaurav Says</div>
  I used to run a fashion brand. And I went through three agencies in about eighteen months. Each one promised something different. Each one delivered the same thing &mdash; a Canva calendar and an invoice.<br><br>
  And at some point during that I started experimenting with AI. This was maybe a year ago. I started with ChatGPT, tried building some workflows, ran into walls. Then I found Claude &mdash; specifically Claude Code &mdash; and something clicked.<br><br>
  Because what Claude let me do was not just generate content. It let me build a system. And I need to be very clear here &mdash; I am not a developer. I have never opened a code editor before this. I don&rsquo;t know Python, I don&rsquo;t know JavaScript, I don&rsquo;t know any of that. But Claude Code lets you describe what you want in plain English, and it builds it.<br><br>
  So I started building. One agent at a time. First, a trend researcher &mdash; something that scrapes Instagram, LinkedIn, Reddit, and tells me what&rsquo;s actually trending in a category right now. Not last week. Right now.<br><br>
  Then a strategy agent &mdash; takes that trend data, compares it with competitor data, and builds a ninety-day roadmap. Not opinions. Data-backed decisions.<br><br>
  Then a content planner. A script writer. A carousel designer. A brand guardian that checks every piece of content against the brand voice before it goes out.<br><br>
  One by one, I kept building. And now there are eighteen of them. Eighteen AI agents, each with a specific job, all connected, all running through one dashboard.
</div>

<div class="direction-block">
  <div class="direction-label">Screen Recording Insert</div>
  Show the dashboard briefly &mdash; the agent list, a calendar view, an output preview. 10&ndash;15 seconds. Don&rsquo;t explain every feature. Let the viewer see it and wonder.
</div>

<div class="speak-block">
  <div class="speak-label">Gaurav Says</div>
  And what nobody tells you about building something like this is &mdash; it&rsquo;s not the AI that&rsquo;s hard. The hard part is the system around the AI. Knowing what to build. Knowing what sequence the agents should run in. Knowing what data each one needs from the last one.<br><br>
  The trap most founders fall into is &mdash; they pick the tool before they pick the problem. They start with &ldquo;I want to use AI&rdquo; instead of starting with &ldquo;my marketing is broken because I have no data.&rdquo; Those are two very different starting points. And they lead to very different outcomes.
</div>

<!-- ───── SECTION 4: THE PROOF ───── -->
<h2>Section 4 &mdash; What It Actually Produces</h2>
<span class="time-marker">7:00 &ndash; 10:30</span>

<div class="direction-block">
  <div class="direction-label">Camera Direction</div>
  This is the show-don&rsquo;t-tell section. Hold up the actual PDFs on camera (print them out or show on iPad). Then cut to screen recordings scrolling through each deliverable. This is where viewers go &ldquo;wait, this is real.&rdquo;
</div>

<div class="speak-block">
  <div class="speak-label">Gaurav Says</div>
  Let me show you what this system actually produces. Because I think this is where it gets real.<br><br>
  For my own brand &mdash; this brand, the one you&rsquo;re watching right now &mdash; I ran the full pipeline. And in one day, here&rsquo;s what came out.
</div>

<div class="direction-block">
  <div class="direction-label">Show Each Deliverable</div>
  Hold up or screen-share each PDF as you mention it. Let the viewer see the quality.
</div>

<div class="speak-block">
  <div class="speak-label">Gaurav Says</div>
  First &mdash; a ninety-day strategy. Not bullet points. A real roadmap with phases, goals, and the reasoning behind each move. This is what a good strategist would charge you two to three lakhs for.<br><br>
  Second &mdash; a thirty-day content calendar. Every post mapped to a funnel stage. Every topic backed by trend data. Not &ldquo;motivational Monday&rdquo; filler. Actual data-driven topics.<br><br>
  Third &mdash; ten scripts. Full scripts with hooks, body, close, and platform-specific directions. Written in my voice. Not generic AI voice &mdash; my actual voice, because the system has a voice profile that it checks every script against.<br><br>
  Fourth &mdash; carousels. Editorial-style, designed automatically. Not Canva templates. Custom layouts generated from the script content.<br><br>
  Fifth &mdash; a brand book. Voice guidelines, visual direction, tone rules, audience mapping. The kind of document an agency charges you separately for and delivers in six weeks.<br><br>
  All of this. One day. One system. Zero code.
</div>

<!-- ───── SECTION 5: WHAT'S NEXT ───── -->
<h2>Section 5 &mdash; What&rsquo;s Coming</h2>
<span class="time-marker">10:30 &ndash; 12:30</span>

<div class="direction-block">
  <div class="direction-label">Camera Direction</div>
  Back to talking head. This is the commitment section. Direct, honest, looking into camera.
</div>

<div class="speak-block">
  <div class="speak-label">Gaurav Says</div>
  Right now, I&rsquo;m running this system on four brands. My personal brand, a fashion brand, and two product brands. Four completely different categories. Four different audiences. Same system.<br><br>
  And I&rsquo;m going to document the entire thing. Publicly. Every number, every result, every time the AI got it wrong and I had to fix it. No highlight reel. No &ldquo;look how easy this is.&rdquo; The real back-end.<br><br>
  Because the pattern I keep seeing in the AI space is &mdash; everyone shows you the magic. The two-second clip where AI generates something beautiful. Nobody shows you the forty hours before that two-second clip. Nobody shows you the prompt that failed twelve times before it worked. Nobody shows you the cost.<br><br>
  That&rsquo;s what this channel is. The back-end that nobody shows you.
</div>

<!-- ───── SECTION 6: CLOSE ───── -->
<h2>Section 6 &mdash; The Close</h2>
<span class="time-marker">12:30 &ndash; 13:30</span>

<div class="direction-block">
  <div class="direction-label">Camera Direction</div>
  Same talking head. Calm close. No excitement spike. No &ldquo;smash that subscribe button.&rdquo; Just a principle and a quiet invitation.
</div>

<div class="speak-block">
  <div class="speak-label">Gaurav Says</div>
  If you&rsquo;re a founder or you&rsquo;re running a brand and you&rsquo;re still figuring out where AI fits &mdash; here&rsquo;s the one thing I&rsquo;d tell you.<br><br>
  Before you pick the tool, pick the problem. Before you ask &ldquo;which AI should I use,&rdquo; ask &ldquo;what process am I actually trying to fix?&rdquo; Because AI without a system is just faster guessing. And faster guessing still loses to someone with data and a plan.<br><br>
  I&rsquo;m going to keep building this. If that sounds useful to you &mdash; follow along. I&rsquo;ll see you in the next one.
</div>

<div class="direction-block">
  <div class="direction-label">End Screen</div>
  Simple end card. ASKGauravAI logo. Subscribe button overlay. No verbal subscribe CTA &mdash; let the end screen do the work.
</div>

<!-- ───── RECORDING NOTES ───── -->
<div class="page-break"></div>
<h2>Recording Notes for Gaurav</h2>

<div class="callout">
  <strong>Total estimated length:</strong> 12&ndash;14 minutes<br>
  <strong>Recording setup:</strong> iPhone 13 Pro Max, tight frame (chest up), natural light preferred. Protronics DASH 7 wireless mic.<br>
  <strong>B-roll needed:</strong> 3&ndash;4 screen recordings of the dashboard (15 seconds each). 1 screen recording scrolling through each PDF deliverable.<br>
  <strong>Energy:</strong> Calm, conversational. Like explaining to a friend over coffee. Not presenting. Not performing.<br>
  <strong>Key rule:</strong> Do NOT name &ldquo;Grid Control.&rdquo; Say &ldquo;my system,&rdquo; &ldquo;the system I built,&rdquo; &ldquo;my AI system.&rdquo;<br>
  <strong>Teleprompter:</strong> Not needed. Use this script as a beat sheet &mdash; know the key points for each section, then speak naturally. Don&rsquo;t memorize lines word-for-word.<br>
  <strong>Cuts from this pillar:</strong> Sections 1, 2, 4, and 6 each work as standalone 60-second Reels/Shorts.
</div>

<h3>Derivative Cut Guide</h3>
<ul>
  <li><strong>Reel 1 (Intro):</strong> Section 1 hook &mdash; &ldquo;18 agents, zero code, never written a line of code&rdquo;</li>
  <li><strong>Reel 2 (Problem):</strong> Section 2 &mdash; &ldquo;Your agency charges 50k and gives you a Canva calendar&rdquo;</li>
  <li><strong>Reel 3 (Proof):</strong> Section 4 &mdash; hold up PDFs, &ldquo;one day, one system, zero code&rdquo;</li>
  <li><strong>Reel 4 (Philosophy):</strong> Section 6 close &mdash; &ldquo;Before you pick the tool, pick the problem&rdquo;</li>
  <li><strong>LinkedIn post:</strong> Founder story version of Section 3 (the journey)</li>
  <li><strong>X thread:</strong> Section 4 as a thread &mdash; &ldquo;Here&rsquo;s what 18 AI agents produced in one day:&rdquo;</li>
</ul>

</body></html>"""

# ─────────────────────────────────────────────
# SCRIPT 2: OffGrid Creatives AI Pillar
# ─────────────────────────────────────────────
OFFGRID_HTML = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><style>{CSS}</style></head><body>

<div class="cover">
  <div class="kicker">OffGrid Creatives AI &middot; Week 1 Pillar Script</div>
  <h1>Grid Control: The AI Marketing OS That Replaces Your Agency</h1>
  <div class="subtitle">YouTube Long-Form &middot; 10&ndash;12 Minutes &middot; Product Introduction Video</div>
  <div class="meta">
    Profile: OffGrid Creatives AI &middot; Platform: YouTube (pillar) &middot; Derivatives: IG Reels, Shorts, LinkedIn, X, TikTok<br>
    Generated: {datetime.now().strftime("%B %d, %Y")} &middot; Language: English Only &middot; Content Model: GaryVee Pillar
  </div>
</div>

<!-- ───── OVERVIEW ───── -->
<div class="callout">
  <strong>Script Overview</strong><br>
  This is a product introduction video for Grid Control. Unlike ASKGauravAI (personal brand), this page is the product page. Grid Control IS named here. The tone is still Gaurav&rsquo;s voice &mdash; founder showing what he built &mdash; but the focus is on the product, not the personal story.<br><br>
  <strong>Tone:</strong> Confident product demo. Not salesy. &ldquo;Let me show you what this does&rdquo; energy.<br>
  <strong>On Camera:</strong> Gaurav, talking head + heavy screen recordings of the dashboard.<br>
  <strong>No Hinglish.</strong> English only. Global audience.<br>
  <strong>Grid Control:</strong> Named freely on this page. This IS the Grid Control brand page.
</div>

<!-- ───── SECTION 1: HOOK ───── -->
<h2>Section 1 &mdash; The Hook</h2>
<span class="time-marker">0:00 &ndash; 0:30</span>

<div class="direction-block">
  <div class="direction-label">Camera Direction</div>
  Talking head, direct to camera. Quick, punchy open. Then immediately cut to dashboard screen.
</div>

<div class="speak-block">
  <div class="speak-label">Gaurav Says</div>
  What if you could run your entire marketing &mdash; strategy, content planning, scripting, trend research, competitor analysis, carousel design &mdash; from one dashboard, powered by eighteen AI agents?<br><br>
  That&rsquo;s Grid Control. I built it. And today I&rsquo;m going to show you exactly what it does.
</div>

<!-- ───── SECTION 2: THE GAP ───── -->
<h2>Section 2 &mdash; The Gap in the Market</h2>
<span class="time-marker">0:30 &ndash; 2:30</span>

<div class="direction-block">
  <div class="direction-label">Camera Direction</div>
  Talking head. Setting up the problem that Grid Control solves.
</div>

<div class="speak-block">
  <div class="speak-label">Gaurav Says</div>
  Right now, if you&rsquo;re a D2C founder or a small brand running your own marketing, you basically have three options.<br><br>
  One &mdash; hire an agency. That&rsquo;s fifteen to fifty thousand rupees a month, and what you get back is a content calendar and some Canva posts. No real research. No competitive intelligence. No data behind any of it.<br><br>
  Two &mdash; do it yourself. Which means you&rsquo;re spending twenty hours a week on content instead of running your business. And you&rsquo;re still guessing about what to post, because you don&rsquo;t have the data either.<br><br>
  Three &mdash; use AI tools. ChatGPT for captions, Canva for design, maybe some scheduling tool. But none of these tools talk to each other. There&rsquo;s no system. You&rsquo;re still the system. You&rsquo;re just using slightly faster tools to do the same guesswork.<br><br>
  Grid Control is the fourth option. It&rsquo;s not a tool. It&rsquo;s a system. Eighteen AI agents, each with a specific role, working together in sequence, producing actual deliverables &mdash; not suggestions, deliverables &mdash; that you can review and publish.
</div>

<!-- ───── SECTION 3: THE SYSTEM ───── -->
<h2>Section 3 &mdash; How Grid Control Works</h2>
<span class="time-marker">2:30 &ndash; 6:00</span>

<div class="direction-block">
  <div class="direction-label">Camera Direction</div>
  This is the core demo section. Primarily screen recordings of the Grid Control dashboard, with Gaurav narrating over them. Cut to talking head occasionally for key points.
</div>

<div class="speak-block">
  <div class="speak-label">Gaurav Says</div>
  Let me walk you through the system. When you onboard a brand into Grid Control, here&rsquo;s what happens.
</div>

<div class="direction-block">
  <div class="direction-label">Screen Recording: Dashboard Overview</div>
  Show the main dashboard. Agent list. Brand switcher.
</div>

<div class="speak-block">
  <div class="speak-label">Gaurav Says</div>
  First, the Trend Researcher goes out and scrapes real data. Instagram, LinkedIn, Reddit, Twitter &mdash; it pulls what&rsquo;s actually trending in your specific category right now. Not generic trends. Your niche. Your competitors. Your audience&rsquo;s actual behavior.<br><br>
  That data feeds into the Strategy Agent, which builds a ninety-day roadmap. It looks at where you are, where your competitors are, where the white space is, and maps out a plan. Every decision in that plan traces back to real data. No opinions.<br><br>
  Then the Content Planner takes that strategy and builds a thirty-day calendar. Every post is mapped to a funnel stage. Every topic is backed by the trend data. It knows what your audience is engaging with this week, not last month.<br><br>
  The Script Writer picks up each post from the calendar and writes full scripts. Hooks, body, close, platform directions. And here&rsquo;s the part that matters &mdash; it checks every script against your Brand Voice profile. So the scripts sound like you, not like generic AI.<br><br>
  The Carousel Designer takes those scripts and generates editorial-style carousel layouts. Not templates. Custom designs built from your content.<br><br>
  And the Brand Guardian reviews everything before it reaches you. It checks tone, voice, positioning, consistency. It catches things like &mdash; &ldquo;this doesn&rsquo;t match the brand direction&rdquo; or &ldquo;this contradicts what we said last week.&rdquo;
</div>

<div class="direction-block">
  <div class="direction-label">Screen Recording: Agent Detail Page</div>
  Show one agent detail page &mdash; its role, recent outputs, status.
</div>

<div class="speak-block">
  <div class="speak-label">Gaurav Says</div>
  There are eighteen agents total. I&rsquo;m not going to walk through all of them now, but the point is &mdash; each one has a specific job. Data Analyst tracks performance. Performance Tracker identifies what&rsquo;s working and what&rsquo;s dead. Trend Sentinel monitors whether a trend is a fad or a structural shift. They all feed into each other. That&rsquo;s what makes this a system, not a tool.
</div>

<!-- ───── SECTION 4: REAL OUTPUT ───── -->
<h2>Section 4 &mdash; Real Deliverables</h2>
<span class="time-marker">6:00 &ndash; 8:30</span>

<div class="direction-block">
  <div class="direction-label">Camera Direction</div>
  Screen recordings scrolling through each deliverable. Cut to talking head for commentary between each one.
</div>

<div class="speak-block">
  <div class="speak-label">Gaurav Says</div>
  Let me show you what actually comes out of this. These are real deliverables generated for a real brand in one day.
</div>

<div class="direction-block">
  <div class="direction-label">Screen Recording: Scroll through 90-day strategy PDF</div>
</div>

<div class="speak-block">
  <div class="speak-label">Gaurav Says</div>
  Ninety-day strategy. Phased rollout with specific goals per phase. Competitor positioning map. White space analysis. Content pillar recommendations &mdash; all backed by scraped data.
</div>

<div class="direction-block">
  <div class="direction-label">Screen Recording: Scroll through content calendar PDF</div>
</div>

<div class="speak-block">
  <div class="speak-label">Gaurav Says</div>
  Thirty-day content calendar. Every post has a topic, format, funnel stage, and the reasoning behind why it&rsquo;s there. Not &ldquo;post a Reel on Tuesday.&rdquo; Actual intelligence behind every slot.
</div>

<div class="direction-block">
  <div class="direction-label">Screen Recording: Show script samples</div>
</div>

<div class="speak-block">
  <div class="speak-label">Gaurav Says</div>
  Full scripts. Hooks written based on what&rsquo;s getting engagement in the category right now. Voice-matched to the brand. Platform directions included &mdash; so a script for an Instagram Reel reads differently from a LinkedIn post, even when the topic is the same.
</div>

<div class="direction-block">
  <div class="direction-label">Screen Recording: Show carousel examples</div>
</div>

<div class="speak-block">
  <div class="speak-label">Gaurav Says</div>
  Carousels. These aren&rsquo;t Canva templates. They&rsquo;re editorial-style designs generated from the script content. Each one is unique to the brand.
</div>

<!-- ───── SECTION 5: WHO THIS IS FOR ───── -->
<h2>Section 5 &mdash; Who This Is For</h2>
<span class="time-marker">8:30 &ndash; 10:00</span>

<div class="direction-block">
  <div class="direction-label">Camera Direction</div>
  Talking head. Direct, honest positioning.
</div>

<div class="speak-block">
  <div class="speak-label">Gaurav Says</div>
  Right now, Grid Control is in testing. I&rsquo;m running it on four brands across different categories &mdash; personal brand, fashion, AI products. I want real results across real categories before I open it up.<br><br>
  But this is who it&rsquo;s built for. D2C founders who are tired of paying agencies for guesswork. Small brands that can&rsquo;t afford a marketing team but need marketing that&rsquo;s actually based on data. Agency owners who want to scale without hiring ten more people. Solopreneurs who want to run their own marketing system instead of being the marketing system.<br><br>
  The vision for Grid Control is simple. You shouldn&rsquo;t need to hire an agency. You should have your own AI-powered marketing system that&rsquo;s better than what most agencies can deliver. That&rsquo;s what we&rsquo;re building.
</div>

<!-- ───── SECTION 6: CLOSE ───── -->
<h2>Section 6 &mdash; The Close</h2>
<span class="time-marker">10:00 &ndash; 11:00</span>

<div class="direction-block">
  <div class="direction-label">Camera Direction</div>
  Talking head. Calm, confident. Future-looking.
</div>

<div class="speak-block">
  <div class="speak-label">Gaurav Says</div>
  Over the next few months, I&rsquo;m going to share everything. How the system performs on real brands. What works. What breaks. The actual numbers.<br><br>
  If you&rsquo;re interested in what AI-powered marketing actually looks like &mdash; not the hype, not the demos, the real thing &mdash; this is the channel for that. Follow along. I&rsquo;ll see you in the next one.
</div>

<div class="direction-block">
  <div class="direction-label">End Screen</div>
  OffGrid Creatives AI logo. Subscribe button overlay. Link to ASKGauravAI in description (&ldquo;Follow the founder&rsquo;s journey&rdquo;).
</div>

<!-- ───── RECORDING NOTES ───── -->
<div class="page-break"></div>
<h2>Recording Notes for Gaurav</h2>

<div class="callout">
  <strong>Total estimated length:</strong> 10&ndash;11 minutes<br>
  <strong>Recording setup:</strong> iPhone 13 Pro Max, talking head. Protronics DASH 7 wireless mic.<br>
  <strong>B-roll needed:</strong> Heavy screen recordings of Grid Control dashboard. Record these BEFORE the talking head &mdash; 5&ndash;6 clips of 15 seconds each: dashboard overview, agent list, calendar view, strategy PDF scroll, script sample, carousel example.<br>
  <strong>Energy:</strong> Confident product demo. Not salesy. Think &ldquo;let me show you what this does&rdquo; &mdash; not &ldquo;buy this.&rdquo;<br>
  <strong>Key rule:</strong> Grid Control IS named in this video. This is the product page. Use the name confidently.<br>
  <strong>Teleprompter:</strong> Not needed. Know the beats, speak naturally. The screen recordings carry the middle section &mdash; you&rsquo;re narrating, not memorizing.<br>
  <strong>Cuts from this pillar:</strong> Sections 1, 3 (agent walkthrough), 4 (deliverables), and 5 (who it&rsquo;s for) each work as standalone Reels/Shorts.
</div>

<h3>Derivative Cut Guide</h3>
<ul>
  <li><strong>Reel 1 (Intro):</strong> Section 1 &mdash; &ldquo;Eighteen AI agents. One dashboard. Your entire marketing.&rdquo;</li>
  <li><strong>Reel 2 (Demo):</strong> Section 3 &mdash; screen recording walkthrough, &ldquo;Let me show you what an AI marketing OS looks like&rdquo;</li>
  <li><strong>Reel 3 (Proof):</strong> Section 4 &mdash; scroll through deliverables, &ldquo;All of this. One day. One system.&rdquo;</li>
  <li><strong>Reel 4 (Vision):</strong> Section 5 close &mdash; &ldquo;You shouldn&rsquo;t need to hire an agency&rdquo;</li>
  <li><strong>LinkedIn post:</strong> &ldquo;Why I&rsquo;m building an AI marketing OS&rdquo; &mdash; Section 2 problem + Section 5 vision</li>
  <li><strong>X thread:</strong> &ldquo;Grid Control has 18 AI agents. Here&rsquo;s what each one does:&rdquo; &mdash; Section 3 breakdown</li>
</ul>

</body></html>"""


def html_to_pdf(html_str: str, name: str):
    """Write HTML, convert to PDF via Chrome headless."""
    html_path = OUT_DIR / f"{name}.html"
    pdf_path = OUT_DIR / f"{name}.pdf"
    html_path.write_text(html_str, encoding="utf-8")
    subprocess.run([
        CHROME,
        "--headless",
        "--disable-gpu",
        "--no-sandbox",
        f"--print-to-pdf={pdf_path}",
        "--no-pdf-header-footer",
        str(html_path),
    ], capture_output=True, timeout=30)
    return pdf_path


if __name__ == "__main__":
    p1 = html_to_pdf(ASKGAURAV_HTML, "pillar_script_askgauravai")
    print(f"  ASKGauravAI script → {p1}")
    p2 = html_to_pdf(OFFGRID_HTML, "pillar_script_offgridcreatives")
    print(f"  OffGrid Creatives script → {p2}")
    print(f"\nBoth scripts saved to: {OUT_DIR}")
