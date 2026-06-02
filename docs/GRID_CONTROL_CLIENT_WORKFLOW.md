# Grid Control — Client Workflow Design

> Living document. Started: May 28, 2026
> Every step documented as Gaurav walks through the ideal client experience.

---

## Step 1 — Client Onboarding

**Decision:** Two-part onboarding.

### Part A — Client fills onboarding form (external)
- Client receives a form link (Notion form / Typeform / custom page)
- They fill: brand name, category, target audience, competitors, social handles, brand voice references, goals, pain points
- This is the RAW INPUT — what the client knows about themselves

### Part B — Admin wires it into Grid Control (admin panel)
- Gaurav reviews the form submission
- Opens admin panel → Add New Brand
- Fills the structured fields: brand_profile.json fields, connects platforms, uploads logo
- Adds what the client DOESN'T know: positioning gaps, competitor analysis angles, content strategy direction
- Brand goes live in the system

### Backend — What happens when a brand is onboarded:

**Flow: Form → Admin Review → System Wire → Agents**

```
Client fills form
       ↓
Form data lands in Supabase (raw_onboarding table)
       ↓
Gaurav opens admin panel → sees new submission
       ↓
Admin panel pre-fills brand_profile fields FROM form data
       ↓
Gaurav reviews, adds his layer:
  - Corrects positioning if client got it wrong
  - Adds strategy direction client doesn't know they need
  - Sets agent priorities (which agents run first)
  - Connects platform accounts
       ↓
Hits "Activate Brand"
       ↓
System creates brands/{slug}/ with merged data
  - Client's raw answers = audience, competitors, tone, goals
  - Gaurav's additions = positioning, strategy angles, agent config
       ↓
Brand Guardian runs first (validates profile completeness)
       ↓
Trend Researcher fires (needs only category + competitors)
       ↓
Pipeline begins
```

**Key principle:** Client provides the WHAT (their brand, audience, goals). Gaurav provides the HOW (strategy, positioning, agent orchestration). The system merges both into brand_profile.json.

**The client never touches the admin panel.** They fill one form, then see results in their client dashboard.

---

## Step 2 — Platform Access (Manual)

After brand is created in system, Gaurav manually:
- Gets client's Instagram login (or gets added as collaborator)
- Gets Meta Business Suite access for ads
- Gets Google Analytics / Search Console access
- Gets LinkedIn page admin access
- Any other platform the client is on

This is done over a call or WhatsApp — NOT through the dashboard.
Gaurav marks each platform as "connected" in admin panel.

**Only after all accounts are connected does the client get their login.**

---

## Step 2.5 — Admin Onboarding Wizard (inside Grid Control)

> Tested live May 28, 2026 with sample brand "GlowLab"

Admin clicks brand switcher (top-left "AS" avatar) → "New brand" → navigates to `/onboarding`.

### 3-Step Wizard

**Step 1 — "Tell us about your brand"**
- Brand name (required)
- What do you sell? (required)
- Who is your audience?
- Website URL (optional)
- Slug auto-generated from brand name
- Next button disabled until name + product filled

**Step 2 — "Connect your platforms"**
- Instagram handle
- LinkedIn page URL or handle
- YouTube channel URL
- TikTok handle
- All optional — agents need these for scraping + competitor analysis
- Back / Next buttons

**Step 3 — "Review and launch"**
- Shows all entered data in a summary card
- Back / **Launch brand** buttons
- On launch:
  1. POST `/api/auth/create-brand` with slug, name, profile
  2. Supabase: creates `brands` row + `brand_members` row (owner)
  3. Server: creates `brands/{slug}/` directory
  4. Server: writes `brand_profile.json` with merged form data
  5. Frontend: updates Zustand store, navigates to `/` (main dashboard)

### What "Launch brand" creates on disk:

```
brands/glowlab/
  └── brand_profile.json    ← name, product, audience, website, social_handles, platforms
```

**Bug fixed during walkthrough:** Slug was only computed on first keystroke (e.g. "G" → slug "g"). Fixed by tracking `slugManuallyEdited` state — slug now updates with every keystroke until user manually edits it.

### What's missing from the wizard (admin adds later):
- Competitors (admin fills from industry knowledge)
- Voice/tone direction
- Content strategy angles
- Agent priorities (which agents run first)
- Platform account connections (done offline — Step 2 below)

---

## Step 3 — Platform Access (Manual)

After brand is created in system, Gaurav manually:
- Gets client's Instagram login (or gets added as collaborator)
- Gets Meta Business Suite access for ads
- Gets Google Analytics / Search Console access
- Gets LinkedIn page admin access
- Any other platform the client is on

This is done over a call or WhatsApp — NOT through the dashboard.
Gaurav marks each platform as "connected" in admin panel.

**Only after all accounts are connected does the client get their login.**

---

## Step 4 — Client First Login

**What the client sees on first login:**

The Brain-first dashboard — a clean chat interface with the brand name personalized:

> "What can I help you with?"
> "I manage your content, research trends, write scripts, and track performance for **GlowLab**."

**4 quick-action cards:**
- 📅 Create content plan
- 📝 Write scripts
- 📊 Analyze performance
- ⚡ Research trends

**Chat input** at the bottom: "Tell me what you need..." (Cmd+Enter to send)

**Left rail (admin view):**
- Brand avatar + name (brand switcher dropdown)
- ADMIN label
- Nav icons: Review, Calendar, Analytics, Agents, System
- Eye icon (client preview toggle)

### Client Nav (what the client can access):

| Icon | Page | Route | Purpose |
|------|------|-------|---------|
| Chat bubble | The Brain | `/` | Main chat interface — ask anything, quick-action cards |
| Checkmark | Review | `/review` | Approve/reject agent outputs. Empty state: "No drafts waiting." |
| Calendar | Calendar | `/calendar` | Content calendar view. Platform filters (X, IG, LinkedIn, TikTok, YT). Monthly grid. |
| Bar chart | Insights | `/insights` | Performance metrics: impressions, engagements, followers, save rate. Follower growth + engagement rate charts. Top posts table. Agent learnings + winning/dead patterns. |

### Admin Nav (Gaurav only — never shown to clients):

| Icon | Page | Route | Purpose |
|------|------|-------|---------|
| Shield | Business Overview | `/admin` | Total brands, MRR, agent costs, profit margin, cost by agent/brand |
| Users | Clients | `/admin/clients` | All brands table: name, slug, owner, plan, status, cost, created date |
| Revenue | Revenue | `/admin/revenue` | MRR, active subs, ARR, recent payments table |
| System | System Health | `/admin/system` | Total runs, successes, errors, error rate. Cost by model. API/FAL/Apify cost summary. |

### View Toggle (eye icon):
- Bottom of left rail — toggles between ADMIN and CLIENT view
- Lets Gaurav preview exactly what the client sees
- Admin pages disappear in CLIENT mode
- Client pages appear in ADMIN mode too (admin can see everything)

---

## Step 5 — What Happens Next (Post-Onboarding)

After the brand is onboarded and accounts are connected:

1. **Brand Guardian** runs first — validates brand_profile.json completeness
2. **Trend Researcher** fires — needs only category + competitors to start
3. Outputs land in Review page for client approval
4. Approved content moves to Calendar for scheduling
5. Performance data starts populating Insights after first posts go live

---

## Bugs Found & Fixed During Walkthrough (May 28-29, 2026)

1. **Slug bug** — OnboardingPage only computed slug on first keystroke ("G" → "g"). Fixed with `slugManuallyEdited` state tracking.
2. **"New brand" dead link** — DropdownMenuItem had no onClick. Wired to `navigate("/onboarding")`. Now admin-only (hidden from clients).
3. **`/api/brands` returned all brands** — No user filtering. Fixed: super admins see all, clients see only their `brand_members` brands. Response key changed from `data` to `brands`.
4. **Onboarding redirect race** — `OnboardingGuard` redirected to `/onboarding` before brands query loaded. Fixed with `isLoading` check.
5. **Infinite loop** — `brands` in useEffect deps caused re-render loop. Removed from deps, used `getState()` for current brand check.
6. **Brain chat open to abuse** — No auth, no rate limit, no topic restriction. Fixed: clients get brand-only prompt, 30 msg/hour limit, 800 token cap, no tools, no Opus.

## Brain Chat — Admin vs Client

| Feature | Admin | Client |
|---------|-------|--------|
| System prompt | Full tools + file access | Brand marketing Q&A only |
| Tools | read_file, propose_edit, propose_bash | None |
| Model | Sonnet (default) / Opus (opt-in) | Sonnet only |
| Max tokens/response | 2000 | 800 |
| Rate limit | None | 30 msgs/hour per brand |
| Token tracking | Yes (brain_usage table) | Yes (brain_usage table) |
| Proposals visible | Yes | No |
| Off-topic | Allowed (admin controls system) | Refused with redirect message |

## Token Cost Tracking

Every Brain chat message logs to `brain_usage` table in Supabase:
- brand_slug, user_id, model, input_tokens, output_tokens, cost_usd, is_admin, created_at
- Cost formula: Sonnet $3/$15 per M tokens (in/out), Opus $15/$75 per M tokens
- Feeds into Admin → Business Overview → "Cost by Brand" card

---

## Next Steps (May 29, 2026)

1. **PILLAR-FORGE-29MAY** — Edit AskGauravAI YouTube long-form from raw recordings
2. **SECURITY FIX** — Decorator ordering bug exposes 54 endpoints unauthenticated (including RCE + .env download). Rotate all keys BEFORE recharging Anthropic credits.
3. Start using Grid Control for both AskGauravAI and GlowLab (sample)
4. Clean up stale "g" brand from Supabase
5. Wire Cost by Brand admin card to pull from brain_usage table
6. Add client-facing usage meter (show remaining messages)

