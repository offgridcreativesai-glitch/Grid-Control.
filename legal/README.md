# Legal — GRID CONTROL (S. R. Enterprise)

**STATUS: FIRST DRAFTS. NOT LEGAL ADVICE. Do not publish until reviewed by a qualified Indian advocate (and, ideally, a privacy specialist for GDPR/CCPA).**

These drafts were generated to reflect what GRID CONTROL actually does — store clients' social platform credentials, scrape public social data, generate content with AI, and publish to connected accounts — so a lawyer is editing reality, not a generic template.

## Documents
| File | Purpose | Who signs / sees it |
|------|---------|---------------------|
| `TERMS_OF_SERVICE.md` | The contract between S. R. Enterprise and each customer using GRID CONTROL. | Every customer (click-accept or signed order form). |
| `PRIVACY_POLICY.md` | How we collect, use, store, and share personal data. Public page. | Anyone (visitors, customers). DPDP/GDPR/CCPA notice. |
| `DATA_PROCESSING_AGREEMENT.md` | We process personal data *on behalf of* the customer (their audience/leads). This governs that processor relationship. | B2B customers (GDPR Art. 28 / DPDP processor terms). |

## Fill these placeholders before review
- `[GSTIN]` — S. R. Enterprise GST number
- `[UDYAM_NO]` — Udyam registration number
- `[PROPRIETOR_NAME]` — proprietor's legal name
- `[PRINCIPAL_ADDRESS]` — registered principal place of business (address)
- `[CITY]`, `[STATE]` — for governing law / jurisdiction (courts)
- `[LEGAL_EMAIL]` — contact for legal/privacy (e.g. a dedicated inbox)
- `[GRIEVANCE_OFFICER_NAME]` + `[GRIEVANCE_EMAIL]` — DPDP Act 2023 requires a named grievance officer
- `[DOMAIN]` — production domain once the custom domain is live
- `[EFFECTIVE_DATE]`

## Open questions for the lawyer (flag these explicitly)
1. **Scraping** — we use Apify to scrape public IG/LinkedIn/TikTok/Reddit/X. Confirm exposure (platform ToS breach, CFAA-equivalent, EU personal-data scraping). Should the ToS warrant the customer authorizes us to act on their connected accounts?
2. **Browser-automation publishing** — we post via browser automation on the customer's logged-in sessions. Is the "you authorize us as your agent" clause sufficient, or do we need explicit per-platform consent?
3. **Token storage** — we hold customers' OAuth tokens/API keys. Liability cap + security-incident clause adequacy.
4. **AI content** — who owns AI-generated output; disclaimers on accuracy; FTC/ASCI endorsement rules for testimonials; EU AI Act transparency.
5. **Sole proprietorship liability** — a proprietorship has unlimited personal liability. Discuss whether to convert to an LLP/Pvt Ltd before signing paying clients, and how the liability cap interacts with that.
6. **Cross-border transfer** — data stored on Railway/Vercel/Supabase (likely US/EU regions). DPDP cross-border + GDPR transfer mechanism (SCCs).
