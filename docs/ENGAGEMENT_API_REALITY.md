# Engagement API Reality — Community Manager & DM Hunter

> Hard constraints for agents **13 community-manager** and **14 dm-customer-hunter** (and their
> sub-agents: instagram-community, linkedin-community, outreach-writer, prospect-researcher).
> Written 2026-06-04. Read this BEFORE promising or building any DM/comment automation.

## The one-line truth

**Proactive cold DMs to strangers are NOT API-allowed and automating them risks a platform ban.**
Do not promise cold-DM automation. Ever.

## Instagram (Messaging / Graph API)

| Action | Allowed? | How |
|--------|----------|-----|
| Reply to an **inbound** DM | ✅ only within **24h** of user's message | Messaging API, requires Live mode + `instagram_manage_messages` |
| Cold/proactive DM to a stranger | ❌ NOT allowed via API | — (browser automation = ban risk) |
| Read/reply to comments | ⚠️ needs **Live mode + App Review** | Graph API + webhook |
| Real-time comment/DM webhooks | ⚠️ needs Live mode + **public hosted endpoint** + App Review | Separate infra project |

Today askgauravai runs in **dev mode** (own account, publish + insights). Messaging/comment
automation is **not** unlocked — that needs Live mode + App Review, a separate build.

## LinkedIn

- No public Messaging API for arbitrary cold outreach. Connection-request + InMail automation
  is against ToS and a ban/restriction risk.

## What these agents CAN legitimately do

1. **Propose** replies/DMs as drafts → human approval gate → **Gaurav sends manually** (or via
   logged-in browser session he controls, per `feedback_browser_publishing`).
2. **Research** prospects from public profile data (prospect-researcher) and **score** ICP fit.
3. **Draft** value-first first-touch messages (outreach-writer) — never auto-sent.
4. **Monitor** inbound (once Live mode lands) and propose 24h-window replies.

## The rule going forward

- Agent output for community/DM = **drafts + queue**, not autonomous sends.
- If a feature needs Live mode + App Review + hosted webhook, it is a **separate project** —
  flag it, scope it, don't silently assume it exists.
- Rate limits (OpenClaw-style browser actions, if ever used) stay conservative and human-gated.
