# Grid Control — FAL Robot Cast (avatar generation prompts)

Recovered from session 388a88de (FE design session, Jun 21–22). WALL·E-inspired full-body
robot cast — one per agent. The robots ARE the design system.

## STYLE BLOCK — paste into EVERY generation (the "token" layer; keeps the cast consistent)

```
STYLE: full-body 3D character render, Pixar / WALL·E inspired robot, expressive
binocular-lens eyes with a soulful gaze, weathered-but-premium matte finish (not glossy
toy), warm soft cinematic studio lighting, plain warm cream background #F2EEE6 for clean
cutout, friendly approachable personality, clean readable silhouette, 3/4 front view,
ENTIRE body visible head-to-toe including legs/treads (built to walk and run), character
model-sheet quality, subtle wear and scratches, high detail, octane render, no text,
no logos, no gold. Off-white #FBF9F4 body base with painted [ACCENT] accents only.
```

## Per-agent prompts (append the STYLE BLOCK, swap [ACCENT])

| Agent | Role | WALL·E match | Accent |
|---|---|---|---|
| Atlas | Chief of Staff | The Captain (benevolent) | Lava `#FF4D00` |
| Scout | Strategist | EVE | Emerald `#0A5E4E` |
| Cadence | Planner | NAN-E | Teal `#103F46` |
| Riveter | Writer | WALL·E | Teal `#1F6F63` |
| Lumen | Creative | PR-T | Lava `#FF4D00` |
| Gauge | Analyst | EVE scan-core | Teal `#2A6E66` |
| Echo | Community | Axiom announcer bots | Emerald `#0A5E4E` |
| Sentry | Brand Guardian | M-O | Deep Teal `#155E50` |
| Finch | Researcher | recon drone | Teal `#2A6E66` |

**Atlas — accent Lava `#FF4D00`:** A confident leader robot standing upright with commanding but warm posture, slightly larger and sturdier than the others, a calm captain's presence, a subtle insignia plate on the chest, one articulated hand raised mid-gesture as if directing a team, planted on solid dual treads, steady binocular eyes. The reassuring chief who runs the floor.

**Scout — accent Emerald `#0A5E4E`:** A sleek egg-smooth reconnaissance robot leaning forward in an alert scouting stance, a glowing horizontal scanner visor across the eyes, one retractable scanner-arm extended surveying the horizon, smooth aerodynamic body, slim agile legs ready to dart. Decisive and curious.

**Cadence — accent Teal `#103F46`:** A methodical planner robot with a chest panel of glowing calendar/grid cells, two small precise arms arranging floating tiles into rows, a metronome-style head that tilts, a steady balanced stance on compact treads. Calm, orderly, keeps the rhythm.

**Riveter — accent Teal `#1F6F63`:** A boxy hardworking builder robot in the spirit of WALL·E, big earnest expressive eyes, a typewriter-key panel across the chest and slender stylus-fingers, slightly hunched diligent posture holding a glowing pen, worn matte plating with honest scratches, tracked treads. The wordsmith who assembles ideas into sentences.

**Lumen — accent Lava `#FF4D00`:** A graceful creative robot with a large camera-aperture iris eye that opens like a lens, an elegant paint/light-wand in one hand, poised artistic posture, refined slim limbs, a small palette panel on the forearm. Makes everything beautiful.

**Gauge — accent Teal `#2A6E66`:** An analytical robot with a round dashboard face of small dials, needles and gauges, a glowing readout strip on the chest, a magnifier-lens arm, an attentive measured stance on compact treads. Reads the numbers and stays calm under data.

**Echo — accent Emerald `#0A5E4E`:** A friendly communicator robot with a speaker-grille chest and two antenna ears, a small horn/megaphone arm, an animated welcoming wave, springy bouncy legs. Warm, sociable, always listening and replying.

**Sentry — accent Deep Teal `#155E50`:** A diligent guardian robot in the spirit of M-O, upright and vigilant, holding a small rounded shield, a precise scanning-brush wand in the other hand, a check-mark emblem on the chest, sturdy reliable legs. The protector who keeps everything on-standard.

**Finch — accent Teal `#2A6E66`:** A nimble curious researcher robot with a satellite-dish/antenna crown tilted as if listening, big wide inquisitive eyes, a small notebook-and-probe arm, an alert forward-leaning stance, light quick legs. Always catching signals before anyone else.

## Generation tips
- Generate each on the plain cream bg (clean cutout), full-body with feet/treads visible.
- Hero pose first; then re-run each with `…in a mid-run pose, leaning forward, one leg lifted` for a run-cycle frame (enables walk animation on the floor).
- No gold. Lava is scarce. Off-white body, single painted accent per character.
