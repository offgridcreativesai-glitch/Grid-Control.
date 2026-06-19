# Flow v2 — Locked Decisions + Open Gaps (Jun 9 2026)

> Captured from the Jun 9 discussion refining `docs/askgauravai_flow_explainer.html` (the 15-step
> AskGauravAI flow). This is the client-interaction layer of the system. Nothing built yet — these are
> locked product decisions + flagged gaps to feed `DASHBOARD_V2_BUILD_PLAN.md`. Companion to
> `docs/AGENCY_WORKFLOW_RESEARCH.md`.

## A. Client-interaction model (the 6 touchpoint decisions — LOCKED)

1. **Connecting accounts** — no change to the current OAuth/token Connect flow for now. The
   "how does a *client* grant access" question is deferred until we onboard the **first external paying
   client**. Today we onboard our OWN brands, so existing connect flow stands.
2. **Brand Book / Audit = a formal sign-off gate (new Step 3.5).** Between research and strategy,
   produce the brand book (same artifact as the Reporting SaaS), client reviews on the portal (PDF
   export available), approves / requests changes BEFORE any calendar is built. Aligns Grid Control's
   understanding with the client's vision → kills downstream rework. **Build AFTER deep research on the
   brand-book report itself** (see Pending Research). Doubles as the sellable Reporting product + the
   ascension foot-in-the-door.
3. **Existing-data ingestion = an upload surface, two ways in.** (a) Paste a cloud link (Google
   Drive / Dropbox / whatever they use) AND (b) direct file/folder/PDF/image upload (like dragging a
   file into Claude). Auto-pull of their *past posts* from connected accounts also applies (no manual
   upload of what's already on their handle). Stored per-brand; read by brand-guardian / creative-
   director / strategy.
4. **Production hand-back = per-request upload button.** When we ask for a video/image/voice note,
   the client uploads it on that specific request/card (file or cloud link, same as #3) → routes to
   creative-director for editing → back to approval.
5. **Approval is mandatory on everything. NO trust dial (for now).** Nothing uploads/publishes
   without explicit client approval. Friction is solved by **pinging the client (email/WhatsApp)** to
   approve — not by automating approval away.
6. **One concierge, not six.** The client talks to ONE agent — the **Chief of Staff (ceo-brain)** —
   never the 6 roles directly. It answers directly or dispatches the right specialist; the result lands
   in the **approval dashboard** for final review/change/approve. No answer conflict, one relationship.
   The 6 roles stay visible (The Team page) but everything routes through the Chief of Staff.
   **Tiering (from gap #1):** trivial/deterministic requests (reschedule, pause, swap slide, edit a
   caption word) execute instantly with NO LLM spin-up; only substantive requests (re-plan, inject a
   trend, new angle) get dispatched to a specialist.

## B. Review counters + the 10 gaps (resolved)

1. **Concierge cost/latency** → AGREED. Tier it: trivial = instant, no agent; substantive = dispatch.
   (Folded into A6.)
2. **Unlimited post-approval changes = scope creep** → AGREED. **Put a limit on everything.** Keep the
   change-chat open and freeing, but track every change request and flag when a "change" is really new
   scope (a Phase-2 upsell), with a revision cap.
3. **Billing / contract / subscription** → DEFERRED. We're onboarding our own brands now; revisit at
   first paying client.
4. **Ad-spend gate (separate from content approval)** → AGREED. ad-strategist needs its own budget
   cap + per-spend approval gate, distinct from the content gate. (Spending real Meta budget ≠ posting.)
5. **Silence on approval breaks cadence** → resolved by A5: ping via email/WhatsApp until approved.
   No auto-publish fallback (because no trust dial).
6. **Notifications** → AGREED. WhatsApp/email ping is how mandatory-approval-everything stays fast.
   Directly enables A5.
7. **Trust dial / auto-rules** → REFRAMED, not day-1. NOT a slider we ship now. Instead: by running our
   OWN brands first, we **learn empirically which content types are safe to let through without asking,
   then codify those rules.** Through-line: *approve-everything + notify today → test-and-codify auto-
   rules later.*
8. **Time-to-first-value** → Gaurav's stance: the pipeline is a strict dependency chain (each step
   must be complete + "green" before the next). Accepted. Note (Claude): the green-gate chain is what
   *creates* the 2–3 week delay; a quick-win post can still run in parallel without breaking the chain
   if we want week-1 life. Optional, his call later.
9. **CRM** → BUILD IT. Grid Control has no CRM. **Adopt `marmelab/atomic-crm`** (React + shadcn +
   Supabase = our exact stack, MIT, ~15k LOC, reuses our Supabase/RLS, zero new heavy services). Use it
   for (a) Grid Control's own Loop-A lead pipeline AND (b) resold client-CRM ("give ours at extra cost"
   when the client has none). Twenty (45.5k★) = fallback only if we outgrow Atomic (it needs a NestJS +
   GraphQL backend + 4–8GB RAM). EspoCRM rejected (PHP, wrong stack). Decide Twenty-vs-Atomic for
   full-featured client resale later.
10. **Offboarding / pause / revoke / data export** → SKIP for now, build later.

## C. New build items this discussion created (for DASHBOARD_V2_BUILD_PLAN.md)
- Step 3.5 **Brand Book → client sign-off** gate (after the brand-book research).
- **Asset ingestion** surface: cloud-link + direct upload, per-brand store + auto-pull past posts.
- **Per-content-card upload** hand-off (video/image/voice) → creative-director → approval.
- **Concierge chat** (Chief of Staff) that *triggers* agent re-runs, with trivial-vs-substantive
  tiering; output to approval dashboard. (= Phase C "Team-Room/brief trigger".)
- **Change-request tracking + revision cap + scope-flagging** (anti scope-creep).
- **Ad-spend gate** (budget cap + per-spend approval) for ad-strategist.
- **Notifications**: email/WhatsApp approval pings.
- **CRM**: integrate Atomic CRM on our Supabase (Loop-A pipeline + resale).
- (Deferred: billing/subscription; offboarding/export.)

## D. Pending research (before building the above)
1. **Brand-book report — deep research** (extensive). What a world-class brand book / brand-audit
   deliverable contains. Scope as BOTH the sellable Reporting product (₹2.5–7k) and the internal
   onboarding sign-off doc (same artifact, two uses). ← next action.
2. ~~CRM repo research~~ — DONE (Atomic CRM picked, see B9).
