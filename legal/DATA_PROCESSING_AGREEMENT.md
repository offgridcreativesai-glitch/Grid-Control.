> **FIRST DRAFT — NOT LEGAL ADVICE. Requires review by a qualified Indian advocate / privacy specialist before use.**
> Placeholders in `[BRACKETS]` must be completed. See `legal/README.md`.

# Data Processing Agreement (DPA) — GRID CONTROL

**Effective date:** [EFFECTIVE_DATE]

This Data Processing Agreement ("**DPA**") forms part of, and is subject to, the Terms of Service between **S. R. Enterprise** (GSTIN: **[GSTIN]**; Udyam Reg. No.: **[UDYAM_NO]**; **[PRINCIPAL_ADDRESS]**) ("**Processor**", "**we**") and the customer ("**Controller**", "**you**"). It governs our processing of Personal Data **on your behalf** when you use GRID CONTROL.

Where you are the controller of personal data about your audience, leads, or contacts, and we process that data to provide the Service, you are the **Data Fiduciary/Controller** and we act as the **Data Processor**. This DPA implements India's **DPDP Act, 2023** processor obligations and, where applicable, **Article 28 of the EU/UK GDPR**.

## 1. Definitions
"**Personal Data**", "**processing**", "**controller**", "**processor**", "**data principal/subject**" have the meanings given under applicable Data Protection Law. "**Data Protection Law**" means the DPDP Act 2023 and rules, and, where applicable, the EU/UK GDPR and CCPA/CPRA.

## 2. Scope & roles
2.1 We process Personal Data only as a processor, on your documented instructions (including via the Service's features and configuration), and for the purposes set out in **Annex A**.
2.2 You are responsible for the lawfulness of the Personal Data you provide and the instructions you give, including having a valid legal basis/consent for the data you bring into the Service and for the actions you direct us to take on your Connected Accounts.

## 3. Our obligations as processor
We will:
(a) process Personal Data only on your documented instructions, unless required by law (and then we notify you unless legally prohibited);
(b) ensure persons authorized to process Personal Data are under confidentiality obligations;
(c) implement appropriate **technical and organizational security measures** (Annex B);
(d) respect the conditions for engaging **sub-processors** (Section 5);
(e) assist you, taking into account the nature of processing, in responding to **data principal/subject requests**;
(f) assist you with security, breach notification, and (where applicable) data protection impact assessments;
(g) at your choice, **delete or return** all Personal Data at the end of the Service, except where retention is required by law;
(h) make available information reasonably necessary to demonstrate compliance and allow for reasonable audits (Section 8).

## 4. Security & personal data breach
4.1 We maintain the security measures in **Annex B** and review them periodically.
4.2 We will notify you **without undue delay** (and, where feasible, within **[72] hours**) after becoming aware of a Personal Data breach affecting your data, with the information reasonably available to help you meet your own notification duties (including, in India, to the Data Protection Board and affected data principals as required).

## 5. Sub-processors
5.1 You provide **general authorization** for us to engage sub-processors to provide the Service (e.g. cloud hosting, database, AI model providers, payment processing). A current list is available on request.
5.2 We impose data-protection obligations on each sub-processor substantially similar to those in this DPA, and remain responsible for their performance.
5.3 We will give you reasonable notice of intended changes to sub-processors and an opportunity to object on reasonable grounds.

## 6. International transfers
Personal Data may be processed outside India by us or our sub-processors. We will ensure such transfers comply with the DPDP Act (and any government restrictions on transfer) and, for EU/UK Personal Data, are made under an approved transfer mechanism (e.g. Standard Contractual Clauses).

## 7. Data principal / data subject rights
We will, where technically feasible, assist you in fulfilling requests from data principals/subjects to access, correct, update, erase, or restrict their Personal Data, and to withdraw consent. If a request reaches us directly, we will (unless legally required to act) refer it to you.

## 8. Audit
On reasonable prior written notice and no more than **[once per year]** (or after a breach, or where required by a regulator), we will make available information necessary to demonstrate compliance with this DPA, subject to confidentiality and to protecting other customers' data.

## 9. Liability
The liability provisions of the Terms of Service apply to this DPA. Nothing in this DPA limits rights that data principals/subjects have under Data Protection Law.

## 10. Term & termination
This DPA remains in effect for as long as we process Personal Data on your behalf. On termination, Section 3(g) (deletion/return) applies.

---

## Annex A — Details of processing
- **Subject matter:** provision of the GRID CONTROL marketing platform.
- **Duration:** the term of the Service.
- **Nature & purpose:** content planning, generation, review, scheduling, and publishing; analytics; trend and competitor research; community/outreach management as configured by you.
- **Categories of data principals/subjects:** your audience, followers, leads, prospects, and contacts; individuals who appear in publicly available content you analyze.
- **Categories of Personal Data:** names, social handles/usernames, public profile data, public post content and engagement metrics, contact details you provide or collect (e.g. emails for outreach), and account identifiers. **No special-category/sensitive data is intended to be processed.**

## Annex B — Technical & organizational security measures
- Access controls and authentication (Supabase JWT; brand-scoped authorization; deny-by-default).
- Per-customer data isolation (`brands/<slug>/` segregation).
- Encryption of data in transit (HTTPS/TLS).
- **[Roadmap] Encryption at rest for stored platform tokens/credentials.**
- Rate limiting and request-size limits.
- Restricted privileged/operator access; audit logging.
- Secrets excluded from source control; environment-based secret management.
- Periodic security review.

*(Lawyer/security: align Annex B with the actual deployed controls before signing; complete the encryption-at-rest item — see security review in `GRIDLOCK-WIRE-24JUN`.)*
