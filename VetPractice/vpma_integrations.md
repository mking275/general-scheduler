# VPMA Integration Design Guide

**Product**: VPMA — Veterinary Practice Management Agent  
**Date**: 2026-06-19  
**Document type**: Integration Architecture — Pre-Build

> **The pattern**: *Integrations aren't just data sync. Every integration is a trigger for an agent action.*  
> A new lab result isn't just filed — the Care Agent reads it and updates the patient risk score.  
> A payroll run isn't just numbers — the Staff Agent flags overtime before it happens.

---

## Integration Tiers

Every integration falls into one of three implementation tiers:

| Tier | Mechanism | Effort | When to use |
|---|---|---|---|
| **Native** | Direct API with OAuth / API key, bidirectional real-time | High | Core revenue-critical workflows |
| **Webhook** | VPMA pushes/receives events via HTTP; partner initiates | Medium | Event-driven triggers (lab results, payment settled) |
| **Export/Import** | CSV/PDF/JSON export; manual or scheduled upload | Low | Accounting, reporting, compliance — where real-time isn't needed |

---

## MOD-FIN Integrations — Accounting & Payroll

### Accounting Systems

| System | Tier | What syncs | Agentic trigger |
|---|---|---|---|
| **QuickBooks Online** | Native | Invoices, payments, expenses, chart of accounts | Payment settled → Billing Agent pushes transaction to QB in real time; reconciliation discrepancies flagged to manager |
| **QuickBooks Desktop** | Export | IIF/CSV export of daily batch | End-of-day → reconciliation agent exports batch file for manual import |
| **Xero** | Native | Invoices, contacts (owners as customers), payments | Same as QBO — invoice approved → Xero draft created; payment → marked paid |
| **Wave** | Webhook | Invoices, payments | Lightweight option for single-vet practices with no accountant |
| **Sage** | Export | CSV journal entries | Export only; targeted at practices already on Sage |
| **FreshBooks** | Native | Invoices, time tracking (for per-hour consults) | Invoice approved → FreshBooks draft; payment link generated from FreshBooks |

**Integration agent pattern (Accounting)**:
```
Payment SETTLED in VPMA
  → Billing Agent: POST /accounting/transactions
  → maps: invoice_id, line_items, tax, payment_method, clinic_id
  → partner API creates/updates invoice record
  → on success: VPMA flags invoice as 'synced_to_accounting'
  → on failure: queued for retry (T+15m, T+1h, T+4h)
  → Verbose Log: BILLING AGENT: Invoice #1042 synced to QuickBooks ✓
```

**Chart of accounts mapping** (practice-configurable):

| VPMA procedure type | Default QB account |
|---|---|
| Wellness / Vaccine | Services Revenue — Preventive |
| Surgery | Services Revenue — Surgical |
| Diagnostics / Labs | Services Revenue — Diagnostic |
| Pharmacy / Rx | Product Revenue — Pharmacy |
| Boarding / Grooming | Services Revenue — Ancillary |

---

### Payroll Systems

| System | Tier | What syncs | Agentic trigger |
|---|---|---|---|
| **Gusto** | Native | Employee hours, pay rates, overtime flags, bonuses | MOD-STF time entries → Gusto payroll run draft; overtime flagged before submission |
| **ADP Workforce Now** | Native | Hours, PTO, headcount changes | Staff scheduling exports to ADP; new hire onboarding triggers ADP provisioning |
| **Paychex Flex** | Webhook | Hours export, payroll approval | Weekly: Staff Agent exports approved hours to Paychex; manager approves in Paychex |
| **QuickBooks Payroll** | Native | Full payroll sync (if using QB for accounting) | Unified: time entries → QB Payroll → QB accounting in one flow |
| **Rippling** | Native | HR + payroll + device management | Best for multi-location groups; single source of truth for headcount |
| **BambooHR** | Native | Employee records, PTO, performance | Pairs with payroll provider; VPMA syncs staff records, not payroll directly |

**Overtime detection agent (MOD-STF)**:
```
Daily at 4pm → Staff Compliance Agent
  → reads: all time entries for this week per staff member
  → computes: projected weekly hours at current pace
  → if projected > 40h: flag to manager action queue
  → if already over 40h: Verbose Log: STAFF AGENT: Dr. Chen at 42.5h — overtime threshold exceeded
  → manager can: approve overtime | reassign shift | adjust schedule
  → approved overtime hours exported to payroll system at week close
```

---

## MOD-INV Integrations — Purchasing & Distribution

The vet supply chain is dominated by a small number of large distributors. These are the integrations that matter most for inventory automation.

### Veterinary Distributors

| Distributor | Tier | Coverage | Agentic trigger |
|---|---|---|---|
| **Covetrus** *(formerly Henry Schein Animal Health)* | Native | Pharmaceuticals, consumables, equipment; largest vet distributor | Stock below reorder point → Inventory Agent drafts PO to Covetrus API; pricing pulled live; backorder status checked |
| **MWI Animal Health** *(AmerisourceBergen)* | Native | Pharmaceuticals, biologics, vaccines | Same as Covetrus; agent compares pricing between distributors before drafting PO |
| **Patterson Veterinary** | Native | Equipment, consumables, dental supplies | Equipment reorder + service contract tracking |
| **IDEXX Direct** | Native | IDEXX-brand diagnostics, reagents, lab supplies | Reagent low → auto-reorder; tied to lab instrument usage data |
| **Zoetis Direct** | Webhook | Zoetis pharmaceuticals (Simparica, Revolution, etc.) | Vaccine stock triggers reorder; lot expiry tracked per batch |
| **Merck Animal Health** | Export | Pharmaceuticals, vaccines | CSV purchase order sent via email/portal |
| **Generic / GPO** | Export | Any distributor not natively integrated | PDF/CSV PO generation; email dispatch |

**Smart reorder agent pattern**:
```
Daily → Inventory Agent sweep
  → for each drug_stock where quantity_on_hand <= reorder_point:
    → check: is there already an open PO for this item? (avoid duplicate order)
    → fetch live pricing from Covetrus API + MWI API
    → select: lower price distributor (or preferred if within 5%)
    → draft PO line item with: quantity, price, ETA
    → group all items into single PO per distributor
    → PO draft → manager action queue for 1-click approval
    → on approval: POST PO to distributor API
    → on dispatch confirmation: update stock status to 'on_order'
    → on receipt scan: update quantity_on_hand, record lot numbers
  → Verbose Log: INVENTORY AGENT: 3 items reordered · Covetrus PO #8821 submitted
```

### DEA / Controlled Substance Reporting

| System | Tier | Purpose | Agentic trigger |
|---|---|---|---|
| **DEA ARCOS** | Export | Schedule I–V controlled substance reporting (federal) | Monthly: DEA log export in ARCOS format; agent flags any gaps in chain-of-custody |
| **State DEA Boards** | Export | State-specific controlled substance reporting | Agent checks state requirements per clinic location |
| **PDMP / AWARxE** | Webhook | Prescription Drug Monitoring Program | Before issuing controlled Rx: agent queries PDMP for patient history; flags concerns to vet |

---

## MOD-ANL / General — Diagnostics & Lab Results

Lab results are one of the highest-value integration surfaces in vet practice. A result arrives and the agent acts immediately.

### Laboratory & Diagnostics

| System | Tier | What integrates | Agentic trigger |
|---|---|---|---|
| **IDEXX Laboratories** | Native | Reference lab results, in-house analyzers (Catalyst, ProCyte, SediVue) | Result webhook → Care Agent attaches to patient, flags abnormal values, notifies vet, updates risk score |
| **Antech Diagnostics** *(Mars Petcare)* | Native | Reference lab results | Same pattern; practices typically use IDEXX or Antech, rarely both |
| **Heska** | Webhook | In-house hematology, chemistry, urinalysis | Instrument pushes result → same agent pipeline |
| **Zoetis Vetscan** | Webhook | In-house chemistry analyzer | Result webhook → patient record |
| **Abaxis** | Export | Point-of-care results | CSV import; less real-time but supported |
| **Sound / Diagnostic Imaging** | Native | Radiology reports, DICOM images | Report received → attaches to patient Imaging tab in VetAppointmentCard |

**Lab result agent pattern**:
```
Lab result RECEIVED (webhook from IDEXX)
  → Care Agent:
    → matches result to patient via lab order ID
    → parses: analyte values, reference ranges, flags
    → abnormal values → appended to patient flags
    → if critical value: immediate alert to vet action queue
    → if routine: attached to SOAP note + care timeline
    → risk score recalculated
    → Verbose Log: LAB AGENT: CBC for Buddy — WBC elevated · Risk updated
    → follow-up draft queued if result requires owner notification
```

---

## MOD-COM Integrations — Communications Delivery

| System | Tier | Purpose | Notes |
|---|---|---|---|
| **Twilio** | Native | SMS delivery + inbound reply handling | Primary SMS; handles 2-way reply routing |
| **SendGrid** | Native | Transactional email (receipts, reminders, results) | Primary email; templates managed in VPMA |
| **Mailchimp / Klaviyo** | Native | Bulk marketing emails (MOD-MAR campaigns) | Used for campaign sends, not transactional |
| **Podium** | Webhook | Review requests + messaging aggregator | Alternative to direct Twilio/Google for review flow |
| **Google Business Messages** | Webhook | Google Business chat | Owners message clinic via Google Maps listing |
| **WhatsApp Business API** | Native | WhatsApp messaging for international clinics | Via Twilio or Meta direct; opt-in required |

---

## MOD-MAR Integrations — Marketing & Social

| System | Tier | Purpose | Agentic trigger |
|---|---|---|---|
| **Meta Graph API** | Native | Facebook + Instagram post publishing, ad performance | Content Agent publishes approved posts; reads impressions 24h post-publish |
| **Google My Business API** | Native | Google Business Posts, review monitoring | Review Agent monitors + drafts responses; Posts Agent publishes weekly update |
| **Google Ads API** | Native (read) | Ad spend, clicks, conversions | Analytics Agent computes cost-per-booking from paid vs organic |
| **Canva API** | Native | On-brand image generation for social posts | Content Agent submits image brief → Canva graphic → attached to post draft |
| **Hootsuite / Buffer** | Webhook | Social scheduling (if practice already uses one) | VPMA drafts → pushed to scheduler queue |
| **Mailchimp / Klaviyo** | Native | Email campaigns, A/B testing, analytics | Campaign Agent builds segment → sends; open rate reported back |
| **Google Analytics 4** | Native (read) | Website traffic from marketing campaigns | UTM-tagged links → GA4 → bookings attributed in VPMA dashboard |

---

## MOD-TEL Integrations — Telemedicine

| System | Tier | Purpose | Notes |
|---|---|---|---|
| **Daily.co** | Native | Video room creation, participant management | Lightweight iframe embed; no app download required |
| **Whereby** | Native | Video rooms | Alternative to Daily; equally simple embed |
| **Zoom (Healthcare)** | Native | Video consultations | HIPAA-compliant; familiar to owners |
| **Twilio Video** | Native | Video (if already using Twilio for SMS) | Unified vendor; one API key |

---

## MOD-STF Integrations — HR & Scheduling

| System | Tier | Purpose | Agentic trigger |
|---|---|---|---|
| **Gusto HR** | Native | Employee records, onboarding, benefits | New staff in VPMA → provisioned in Gusto; termination triggers offboarding |
| **BambooHR** | Native | HR records, performance reviews, PTO | PTO request in BambooHR → blocks shift in VPMA scheduling |
| **WhenIWork** | Native | Shift scheduling (dedicated scheduling tool) | VPMA schedule → synced; staff get mobile notifications |
| **Indeed / LinkedIn** | Export | Job postings when hiring | Staff vacancy detected → agent drafts job description |
| **AVMA Career Center** | Export | Veterinary-specific job board | Same as above; vet-specific audience |

---

## Data Migration — Legacy PMS

One-time import integrations for practices moving from an existing system.

| Legacy System | Market share | Migration approach |
|---|---|---|
| **Avimark** *(Covetrus)* | Large | CSV/XML export → VPMA import; patients, owners, visit history, Rx history |
| **Cornerstone** *(IDEXX)* | Large | Structured export; IDEXX provides migration toolkit |
| **ezyVet** | Growing | REST API available; live migration possible |
| **Hippo Manager** | Mid-market | CSV export |
| **ImproMed** *(Covetrus)* | Mid-market | CSV export |
| **DaySmart Vet** | Small-mid | CSV export |
| **VetLogic / RxWorks** | Regional | CSV export |

**Migration agent pattern**:
```
Practice ONBOARDS to VPMA
  → Migration Agent:
    → ingests legacy export file (CSV/XML/JSON)
    → maps: legacy patient IDs → VPMA patient IDs
    → maps: legacy owner records → VPMA owners
    → imports: visit history as care_events + historical timeblocks
    → imports: Rx history as prescriptions (historical)
    → flags: records with data quality issues for manual review
    → generates: migration summary report
    → Verbose Log: MIGRATION AGENT: 847 patients imported · 12 records flagged for review
```

---

## Insurance / Claims Integrations

| Provider | Tier | Purpose | Notes |
|---|---|---|---|
| **Trupanion** | Native | Direct pay — Trupanion pays clinic directly at checkout | Gold standard; owner pays only their portion at desk |
| **Nationwide / VPI** | Webhook | Claim submission + status tracking | Pre-filled from SOAP + procedure codes |
| **ASPCA Pet Insurance** | Webhook | Claim submission | Same pattern |
| **Embrace Pet Insurance** | Export | Claim form PDF generation | Manual submission; PDF pre-filled from VPMA |
| **Figo / Spot / Lemonade** | Export | Claim form PDF | Newer insurers; API coming |
| **Pumpkin** | Webhook | Claim submission | Growing market share |

**Trupanion direct pay (highest value)**:
```
Invoice APPROVED → Insurance Agent
  → detects: patient has Trupanion flag on record
  → submits: claim to Trupanion API in real time
  → Trupanion returns: covered amount (usually in <60s)
  → Payment Terminal splits automatically:
    → Trupanion portion: settled directly with clinic
    → Owner portion: displayed on payment terminal for collection
  → Verbose Log: INSURANCE AGENT: Trupanion claim approved · $380 covered · Owner owes $65
```

---

## Regulatory / Compliance Integrations

| System | Tier | Purpose | Notes |
|---|---|---|---|
| **DEA ARCOS** | Export | Federal controlled substance reporting | Monthly automated export; agent ensures no gaps |
| **PDMP / AWARxE** | Webhook | Prescription monitoring program | Query before each controlled Rx; varies by state |
| **AVMA Member Directory** | Native (read) | Vet license verification | Staff license validation on onboarding |
| **State Veterinary Boards** | Export | State license renewal tracking | Agent monitors expiry dates, exports renewal applications |
| **OSHA Reporting** | Export | Workplace incident reporting | Incident log export in OSHA format |

---

## Enterprise / BI Integrations (MOD-ENT)

| System | Tier | Purpose | Notes |
|---|---|---|---|
| **Salesforce** | Native | Franchise CRM — lead tracking, new clinic onboarding pipeline | Enterprise tier only |
| **NetSuite** | Native | ERP for large groups — consolidated financials, multi-entity accounting | PE-backed groups; replaces QuickBooks at scale |
| **Power BI** | Export | Custom BI dashboards for ownership groups | VPMA exports standardised data model |
| **Tableau** | Export | Same as Power BI | Preferred by some investor groups |
| **Google Looker Studio** | Export | Lightweight BI for smaller groups | Free; VPMA exports to Google Sheets → Looker |

---

## Integration Priority Matrix

| Integration | Module | Business Impact | Effort | Priority |
|---|---|---|---|---|
| QuickBooks Online | MOD-FIN | 🔴 Critical | Medium | **P0** |
| Stripe Terminal | MOD-FIN | 🔴 Critical | Medium | **P0** |
| Covetrus / MWI | MOD-INV | 🔴 Critical | High | **P0** |
| IDEXX Lab Results | All | 🔴 Critical | Medium | **P0** |
| Twilio SMS | MOD-COM | 🔴 Critical | Low | **P0** |
| Trupanion Direct Pay | MOD-FIN | 🟠 High | High | P1 |
| Gusto Payroll | MOD-STF | 🟠 High | Medium | P1 |
| Meta / Instagram | MOD-MAR | 🟠 High | Medium | P1 |
| Google My Business | MOD-MAR | 🟠 High | Low | P1 |
| Avimark Migration | Platform | 🟠 High | High | P1 (onboarding) |
| Cornerstone Migration | Platform | 🟠 High | High | P1 (onboarding) |
| Antech Lab Results | All | 🟡 Medium | Medium | P2 |
| Xero | MOD-FIN | 🟡 Medium | Medium | P2 |
| PDMP / AWARxE | MOD-INV | 🟡 Medium | Medium | P2 (compliance) |
| BambooHR | MOD-STF | 🟡 Medium | Low | P2 |
| Mailchimp | MOD-MAR | 🟡 Medium | Low | P2 |
| Salesforce | MOD-ENT | 🟢 Lower | High | P3 |
| NetSuite | MOD-ENT | 🟢 Lower | High | P3 |

---

## Integration Architecture Principles

1. **Credentials are practice-configured** — VPMA never hardcodes API keys. Each clinic configures their own credentials in a secure settings panel. Integrations are silently hidden in the UI if credentials are absent.

2. **Every integration has a fallback** — if Covetrus API is down, the PO is queued and emailed as a PDF. If QuickBooks sync fails, the transaction queues for retry with exponential backoff (T+15m, T+1h, T+4h).

3. **Integrations are event-driven, not batch** — wherever possible, VPMA triggers at the moment of the business event (SOAP signed, payment settled, lab result received), not in nightly batches.

4. **Read-only where possible** — for external analytics (Google Ads, GA4), VPMA only reads. No write access to systems that aren't core to the clinical workflow.

5. **Integration health panel** — each integration has a status indicator in Practice Settings: `🟢 Connected`, `🟡 Degraded`, `🔴 Disconnected`. Agents auto-detect connection loss and surface it to the action queue.
