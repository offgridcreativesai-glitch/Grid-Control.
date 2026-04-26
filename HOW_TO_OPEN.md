# Window 2 — GRID CONTROL Build Window
## What this window is for
Building and fixing the GRID CONTROL system.
- Fixing bugs in the dashboard or agents
- Adding new agent features
- Running agents and checking outputs
- Anything technical about the marketing OS

## How to open this window

**Step 1:** Open Terminal on your Mac
(Spotlight → type "Terminal" → Enter)

**Step 2:** Paste this command and press Enter:
```
cd /Users/gauravoffgrid/offgrid-marketing-os && claude
```

Claude Code opens here and knows the full GRID CONTROL build history.

## What to say when you open it
- "Fix the MeetingRoom stale closure bug"
- "Run the Strategy Agent and show me the output"
- "Add a new screen for content calendar"
- "Why is the dashboard showing the wrong brand?"

## How to start the dashboard (for testing)
```
# Terminal 1 — Start the Flask backend
cd /Users/gauravoffgrid/offgrid-marketing-os
python3 dashboard_api.py

# Terminal 2 — Start the React frontend
cd /Users/gauravoffgrid/offgrid-marketing-os/dashboard
npm run dev
```
Then open: http://localhost:5173

## Folder map
```
offgrid-marketing-os/
├── agents/             ← All 9 AI agents (strategy, content, creative, etc.)
├── ceo_brain/          ← Orchestrator that runs everything
├── dashboard/          ← React frontend (GRID CONTROL UI)
├── dashboard_api.py    ← Flask backend (port 5001)
├── brands/             ← Brand profiles + session state
└── .env                ← API keys (never commit this)
```
