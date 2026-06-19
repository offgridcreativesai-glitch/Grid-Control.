"""
Generate Google Ads API — Basic Access design documentation PDF.
Required upload for Google review (Q7 of the application form).
Output: docs/GoogleAds_API_DesignDoc_OffGrid.pdf
"""
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
)
from reportlab.lib.enums import TA_LEFT
import os

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "docs", "GoogleAds_API_DesignDoc_OffGrid.pdf")
os.makedirs(os.path.dirname(OUT), exist_ok=True)

styles = getSampleStyleSheet()
h1 = ParagraphStyle("h1", parent=styles["Heading1"], fontSize=20,
                    spaceAfter=14, textColor=colors.HexColor("#0B1F3A"))
h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=14,
                    spaceAfter=8, spaceBefore=14, textColor=colors.HexColor("#0B1F3A"))
body = ParagraphStyle("body", parent=styles["BodyText"], fontSize=10.5,
                      leading=15, spaceAfter=8, alignment=TA_LEFT)
small = ParagraphStyle("small", parent=styles["BodyText"], fontSize=9,
                       leading=12, textColor=colors.HexColor("#444"))
tcell = ParagraphStyle("tcell", parent=styles["BodyText"], fontSize=9,
                       leading=12, alignment=TA_LEFT, spaceAfter=0)
tcell_head = ParagraphStyle("tcell_head", parent=tcell, fontSize=9,
                            textColor=colors.white, fontName="Helvetica-Bold")

def _row(cells, header=False):
    style = tcell_head if header else tcell
    return [Paragraph(str(c), style) for c in cells]

doc = SimpleDocTemplate(OUT, pagesize=LETTER,
                        leftMargin=0.85*inch, rightMargin=0.85*inch,
                        topMargin=0.9*inch, bottomMargin=0.9*inch,
                        title="OffGrid Marketing OS — Google Ads API Design Documentation")

story = []

# Cover
story.append(Paragraph("OffGrid Marketing OS", h1))
story.append(Paragraph("Google Ads API — Design Documentation", h2))
story.append(Paragraph(
    "<b>Applicant:</b> OffGrid Marketing OS<br/>"
    "<b>Manager Account (MCC) ID:</b> 702-326-7019<br/>"
    "<b>Contact:</b> askgauravai@gmail.com<br/>"
    "<b>Company URL:</b> https://gridcontrol.lovable.app/<br/>"
    "<b>Country:</b> India<br/>"
    "<b>Access level requested:</b> Basic Access<br/>"
    "<b>Doc version:</b> v1.0 · 2026-06-19",
    body))
story.append(Spacer(1, 0.15*inch))

# 1. Executive summary
story.append(Paragraph("1. Executive Summary", h2))
story.append(Paragraph(
    "OffGrid Marketing OS is an autonomous AI marketing platform that manages "
    "paid advertising on behalf of Direct-to-Consumer (D2C) brand clients in India. "
    "Our product is delivered through the Grid Control dashboard, operated by 18 "
    "specialized AI agents under explicit human approval gates. The platform "
    "integrates Google Ads, Meta Ads, and Google Analytics 4 into a single brand-isolated "
    "workspace so a brand owner can plan, create, deploy, and analyze campaigns end-to-end "
    "with one-click human approval on every mutation.",
    body))
story.append(Paragraph(
    "We are requesting Google Ads API Basic Access so our <b>Ad Strategist</b> and "
    "<b>Data Analyst</b> agents can interact with client Google Ads accounts that are "
    "linked to our Manager (MCC) account. No autonomous spend changes are made — "
    "every mutation is queued for human approval before execution.",
    body))

# 2. Architecture
story.append(Paragraph("2. System Architecture", h2))
story.append(Paragraph(
    "Grid Control is a multi-brand, multi-tenant marketing operations platform. "
    "Each brand has an isolated workspace (`brands/&lt;slug&gt;/`) containing its own "
    "brand profile, content calendar, performance history, OAuth credentials, "
    "and ad account linkage. The Flask API (`dashboard_api.py`) loads per-brand "
    "secrets only at request time — no cross-brand contamination.",
    body))
story.append(Paragraph("<b>Component layers:</b>", body))
arch_rows = [
    _row(["Layer", "Component", "Role"], header=True),
    _row(["Frontend",  "React 19 + Vite + TanStack Query v5",
          "Grid Control dashboard, approval queue UI, brand switcher"]),
    _row(["API",       "Flask (Railway-hosted)",
          "Per-brand auth, agent dispatch, approval state, audit log"]),
    _row(["Agents",    "18 Python agents on Claude Agent SDK",
          "Strategy, Content, Creative, Ad Strategist, Data Analyst, etc."]),
    _row(["Storage",   "Supabase (Postgres + RLS)",
          "Brand-isolated rows, audit trail, OAuth tokens encrypted at rest"]),
    _row(["Obs/Cost",  "Langfuse (Cloud)",
          "Per-agent trace + token + cost telemetry"]),
    _row(["Vector",    "Supabase pgvector + Voyage embeddings",
          "Semantic memory (Brand scope + Grid Control scope)"]),
]
t = Table(arch_rows, colWidths=[0.9*inch, 2.3*inch, 3.4*inch])
t.setStyle(TableStyle([
    ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#0B1F3A")),
    ("TEXTCOLOR", (0,0), (-1,0), colors.white),
    ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
    ("FONTSIZE", (0,0), (-1,-1), 9),
    ("GRID", (0,0), (-1,-1), 0.4, colors.HexColor("#CCCCCC")),
    ("VALIGN", (0,0), (-1,-1), "TOP"),
    ("LEFTPADDING", (0,0), (-1,-1), 6),
    ("RIGHTPADDING", (0,0), (-1,-1), 6),
    ("TOPPADDING", (0,0), (-1,-1), 5),
    ("BOTTOMPADDING", (0,0), (-1,-1), 5),
]))
story.append(t)
story.append(Spacer(1, 0.1*inch))

# 3. Data flow with Google Ads API
story.append(PageBreak())
story.append(Paragraph("3. Data Flow — Google Ads API Interactions", h2))
flow_rows = [
    _row(["#", "Trigger", "Direction", "API surface used"], header=True),
    _row(["1", "Brand owner approves a paid campaign in Grid Control",
          "Write", "campaigns / ad_groups / ads / criteria mutate services"]),
    _row(["2", "Weekly performance report (Data Analyst agent)",
          "Read",  "GoogleAdsService search query (campaign, ad_group, keyword stats)"]),
    _row(["3", "Keyword research request by Ad Strategist agent",
          "Read",  "KeywordPlanIdeaService"]),
    _row(["4", "Bid adjustment within human-approved policy",
          "Write", "ad_group / ad_group_criterion mutate (cpc_bid_micros)"]),
    _row(["5", "Pull search-term reports for negative keyword discovery",
          "Read",  "GoogleAdsService (search_term_view)"]),
    _row(["6", "Pause / resume campaigns per human approval",
          "Write", "campaign mutate (status field)"]),
]
t = Table(flow_rows, colWidths=[0.3*inch, 2.8*inch, 0.7*inch, 2.8*inch])
t.setStyle(TableStyle([
    ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#0B1F3A")),
    ("TEXTCOLOR", (0,0), (-1,0), colors.white),
    ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
    ("FONTSIZE", (0,0), (-1,-1), 9),
    ("GRID", (0,0), (-1,-1), 0.4, colors.HexColor("#CCCCCC")),
    ("VALIGN", (0,0), (-1,-1), "TOP"),
    ("LEFTPADDING", (0,0), (-1,-1), 6),
    ("RIGHTPADDING", (0,0), (-1,-1), 6),
    ("TOPPADDING", (0,0), (-1,-1), 5),
    ("BOTTOMPADDING", (0,0), (-1,-1), 5),
]))
story.append(t)
story.append(Spacer(1, 0.15*inch))

story.append(Paragraph("<b>Approval gate (illustrated):</b>", body))
story.append(Paragraph(
    "Agent proposes mutation → mutation serialized to JSON → posted to "
    "<code>brands/&lt;slug&gt;/outputs/pending_approval/</code> → Grid Control UI shows "
    "diff to brand owner → owner approves or rejects → on approval, Flask calls "
    "Google Ads API with the brand's refresh token → response logged to audit trail "
    "+ Langfuse trace. No mutation executes without an audit entry tying it to "
    "a human approval ID.",
    body))

# 4. Authentication
story.append(Paragraph("4. Authentication & Token Handling", h2))
story.append(Paragraph(
    "<b>Per-brand OAuth model.</b> Each client brand completes a Google OAuth 2.0 "
    "consent flow that grants OffGrid Marketing OS read/write scopes on their "
    "Google Ads account (linked under our MCC 702-326-7019). The resulting "
    "refresh token is stored encrypted at rest in Supabase, scoped to a single "
    "brand row protected by Row-Level Security. Refresh tokens are never logged, "
    "never exposed to client-side code, and never shared across brands.",
    body))
story.append(Paragraph(
    "<b>Developer token isolation.</b> The Google Ads API developer token is held "
    "only in the Flask backend's environment (Railway secret manager). It is never "
    "sent to the browser, never logged, and never embedded in client builds. "
    "All Google Ads API calls originate from the backend on the brand owner's behalf.",
    body))
story.append(Paragraph(
    "<b>Scope minimization.</b> Each brand's OAuth grant requests only the "
    "<code>adwords</code> scope required for campaign management. We do not "
    "request unrelated Google scopes (Drive, Gmail, Calendar) during the Google "
    "Ads OAuth flow.",
    body))

# 5. Compliance posture
story.append(Paragraph("5. Compliance & Policy Posture", h2))
compliance_rows = [
    _row(["Policy area", "Our practice"], header=True),
    _row(["Required Minimum Functionality (RMF)",
          "Our tool provides multi-account management, reporting, and bid-policy "
          "automation — well above RMF."]),
    _row(["No reselling / no repackaging",
          "We do not resell API access, do not surface raw API responses to third "
          "parties, and do not whitelabel the Google Ads API."]),
    _row(["Data retention",
          "Performance data is retained for the active client relationship + 30 days, "
          "then purged. Raw OAuth tokens are encrypted at rest and rotated on revocation."]),
    _row(["Rate-limit hygiene",
          "Client library handles backoff. We additionally throttle write mutations "
          "to &le; 5 / minute per ad account to stay well under platform quotas."]),
    _row(["Audit log",
          "Every API call (read or write) is recorded with: brand_id, agent_id, "
          "human_approval_id (write only), request payload, response status, "
          "and Langfuse trace ID."]),
    _row(["Prohibited content / categories",
          "We do not run campaigns for prohibited content categories (e.g. weapons, "
          "adult, regulated pharma). Onboarding checklist verifies category fit."]),
    _row(["User consent",
          "Each brand owner explicitly consents in writing (DocuSign) before any API "
          "action is taken on their ad account."]),
]
t = Table(compliance_rows, colWidths=[1.8*inch, 4.9*inch])
t.setStyle(TableStyle([
    ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#0B1F3A")),
    ("TEXTCOLOR", (0,0), (-1,0), colors.white),
    ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
    ("FONTSIZE", (0,0), (-1,-1), 9),
    ("GRID", (0,0), (-1,-1), 0.4, colors.HexColor("#CCCCCC")),
    ("VALIGN", (0,0), (-1,-1), "TOP"),
    ("LEFTPADDING", (0,0), (-1,-1), 6),
    ("RIGHTPADDING", (0,0), (-1,-1), 6),
    ("TOPPADDING", (0,0), (-1,-1), 5),
    ("BOTTOMPADDING", (0,0), (-1,-1), 5),
]))
story.append(t)
story.append(Spacer(1, 0.1*inch))

# 6. Expected volume + scale
story.append(PageBreak())
story.append(Paragraph("6. Expected Call Volume & Scale", h2))
vol_rows = [
    _row(["Use case", "Frequency", "Typical calls / day"], header=True),
    _row(["Weekly performance pull (Data Analyst)",  "weekly",      "1 search query per client (paged)"]),
    _row(["Campaign create / edit (approved only)",  "ad-hoc",      "5&ndash;20 mutates per client per week"]),
    _row(["Bid policy adjustments",                   "daily",       "10&ndash;40 mutates per client per day"]),
    _row(["Keyword research",                         "weekly",      "5&ndash;10 KeywordPlanIdeaService calls"]),
    _row(["Search-term report",                       "weekly",      "1 paged search query"]),
]
t = Table(vol_rows, colWidths=[3.0*inch, 1.2*inch, 2.5*inch])
t.setStyle(TableStyle([
    ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#0B1F3A")),
    ("TEXTCOLOR", (0,0), (-1,0), colors.white),
    ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
    ("FONTSIZE", (0,0), (-1,-1), 9),
    ("GRID", (0,0), (-1,-1), 0.4, colors.HexColor("#CCCCCC")),
    ("VALIGN", (0,0), (-1,-1), "TOP"),
    ("LEFTPADDING", (0,0), (-1,-1), 6),
    ("RIGHTPADDING", (0,0), (-1,-1), 6),
    ("TOPPADDING", (0,0), (-1,-1), 5),
    ("BOTTOMPADDING", (0,0), (-1,-1), 5),
]))
story.append(t)
story.append(Spacer(1, 0.1*inch))
story.append(Paragraph(
    "<b>Initial scale:</b> 2 brand clients linked to MCC 702-326-7019 in the first "
    "60 days. Expected to grow to 10–15 brand clients within the next 6 months as "
    "Grid Control onboarding stabilizes. We will stay well within standard quota tiers "
    "and request quota increases through standard channels if needed.",
    body))

# 7. Out of scope
story.append(Paragraph("7. Out of Scope (Explicit)", h2))
story.append(Paragraph(
    "We do <b>not</b> plan to use this token for: "
    "(a) App Conversion Tracking and Remarketing API — we focus on D2C brand "
    "search/display/video campaigns, not mobile app install measurement; "
    "(b) reselling Google Ads API access to third parties; "
    "(c) automated content generation that bypasses Google's ad policies — every "
    "creative is reviewed by our Brand Guardian agent and a human reviewer; "
    "(d) any scraping, harvesting, or unauthorized access to Google services "
    "outside the Google Ads API surface area.",
    body))

# 8. Contact + signature
story.append(Paragraph("8. Contact", h2))
story.append(Paragraph(
    "<b>Primary contact:</b> Gaurav Khanna, Founder &amp; CEO, OffGrid Marketing OS<br/>"
    "<b>Email:</b> askgauravai@gmail.com<br/>"
    "<b>Country:</b> India<br/>"
    "<b>Manager Account (MCC):</b> 702-326-7019<br/>"
    "<b>Application date:</b> 2026-06-19",
    body))
story.append(Spacer(1, 0.15*inch))
story.append(Paragraph(
    "We confirm that all information in this design document is accurate and "
    "that OffGrid Marketing OS will comply with the Google Ads API Terms and "
    "Conditions and Required Minimum Functionality (RMF) policy at all times.",
    small))

doc.build(story)
print(f"PDF generated: {OUT}")
print(f"Pages: ~3-4, file size:", os.path.getsize(OUT), "bytes")
