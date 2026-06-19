# VPMA Integration Map — Implementation Registry

**Product**: VPMA — Veterinary Practice Management Agent  
**Date**: 2026-06-19  
**Purpose**: Implementation-ready integration registry. Feed each section into `speckit.specify` to generate tasks.

---

## How to Read This Document

Each integration entry contains:
- **INT-###** — Unique integration ID
- **Tier** — `Native` (real-time API) | `Webhook` (event-push) | `Export` (file-based)
- **Config** — What the practice must configure in Settings
- **New entities** — Database tables/fields this integration adds
- **Agent trigger** — What VPMA agent fires, and when
- **Dependencies** — Other integrations or modules required first

---

## Build Phases

| Phase | Integrations | Gate |
|---|---|---|
| **P0 — Launch Blockers** | INT-010, INT-011, INT-020, INT-021, INT-040, INT-041, INT-050 | Must exist for first paying customer |
| **P1 — Core Value** | INT-012, INT-022, INT-023, INT-030, INT-042, INT-051, INT-060, INT-061 | Needed within 90 days of launch |
| **P2 — Growth** | INT-013, INT-024–028, INT-043–048, INT-062–066, INT-070–072, INT-080–085 | 6-month roadmap |
| **P3 — Enterprise** | INT-001–004, INT-090, INT-100–104 | 12-month / MOD-ENT tier |

---

## CORE VPMA — Platform-Level Integrations

These integrations are not tied to any single add-on module — they are foundational to the platform itself.

---

### INT-001 — Credentials & Secrets Manager *(Core Platform)*

| Field | Value |
|---|---|
| **Tier** | Native |
| **Purpose** | Secure per-clinic storage of all API keys, OAuth tokens, and secrets for every integration |
| **Config** | Admin panel: per-clinic credentials vault; encrypted at rest; never exposed in frontend |
| **New entities** | `IntegrationCredential { clinic_id, integration_id, key_name, encrypted_value, last_verified_at }` |
| **Agent trigger** | On credential add: Integration Health Agent tests connectivity → sets status `🟢 Connected` \| `🔴 Failed` |
| **Notes** | All other integrations depend on this. Build first. |

---

### INT-002 — Integration Health Monitor *(Core Platform)*

| Field | Value |
|---|---|
| **Tier** | Native |
| **Purpose** | Polls each configured integration every 15 minutes; surfaces degradation to action queue |
| **New entities** | `IntegrationStatus { clinic_id, integration_id, status, last_checked_at, error_message }` |
| **Agent trigger** | Nightly sweep + on-demand; if status changes to `🔴 Disconnected` → alert to manager action queue |

---

### INT-003 — Avimark Data Migration *(Core Platform)*

| Field | Value |
|---|---|
| **Tier** | Export/Import |
| **Purpose** | One-time onboarding migration from Avimark (largest legacy PMS) |
| **Config** | Upload: Avimark export ZIP (CSV files) |
| **New entities** | Migration uses existing VPMA entities; adds `MigrationRun { id, source_system, status, imported_count, flagged_count, completed_at }` |
| **Agent trigger** | Upload triggers Migration Agent: maps patients → owners → visit history → care events → Rx history; flags data quality issues |
| **Data mapped** | Patients, owners, appointments (→ historical timeblocks), diagnoses (→ SOAP notes), vaccines (→ care events), prescriptions (→ prescriptions) |

---

### INT-004 — Cornerstone / ezyVet Migration *(Core Platform)*

| Field | Value |
|---|---|
| **Tier** | Export/Import (Cornerstone) \| Native API (ezyVet) |
| **Purpose** | Migration from IDEXX Cornerstone or ezyVet |
| **Notes** | Same Migration Agent as INT-003; different field mapping. ezyVet has REST API enabling live pull rather than file upload. |

---

## MOD-COM — Communications Integrations

---

### INT-010 — Twilio SMS *(MOD-COM, P0)*

| Field | Value |
|---|---|
| **Tier** | Native |
| **Config** | `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER` (per clinic) |
| **New entities** | `OutboundMessage { id, owner_id, channel='sms', body, twilio_sid, status, sent_at, delivered_at }` |
| **New entities** | `InboundReply { id, from_number, body, received_at, intent, routed_to }` |
| **Agent trigger** | Any outbound communication event (reminder, receipt, review request, campaign) → Comms Agent → Twilio API |
| **Inbound** | Twilio webhook → `/api/webhooks/twilio/inbound` → Reply Handler Agent classifies intent → routes to correct VPMA workflow |
| **Fallback** | If Twilio fails → queue message; retry T+5m, T+30m; after 3 failures → send via email (INT-011) |
| **Dependencies** | INT-001 (credentials) |

---

### INT-011 — SendGrid Email *(MOD-COM, P0)*

| Field | Value |
|---|---|
| **Tier** | Native |
| **Config** | `SENDGRID_API_KEY`, `FROM_EMAIL`, `FROM_NAME` (per clinic) |
| **New entities** | `OutboundMessage` (shared with INT-010, channel='email'), `EmailTemplate { id, clinic_id, name, subject, html_body, merge_fields[] }` |
| **Agent trigger** | Post-visit receipts, appointment confirmations, care due notifications, campaign sends |
| **Inbound** | SendGrid Inbound Parse webhook → `/api/webhooks/sendgrid/inbound` → Reply Handler Agent |
| **Fallback** | Queue + retry; after 3 failures → flag to front desk for manual follow-up |

---

### INT-012 — Podium *(MOD-COM / MOD-MAR, P1)*

| Field | Value |
|---|---|
| **Tier** | Webhook |
| **Config** | `PODIUM_API_KEY`, `PODIUM_LOCATION_ID` |
| **Purpose** | Unified messaging + review requests via Podium platform |
| **New entities** | Reuses `OutboundMessage`; adds `PodiumConversation { id, podium_id, owner_id, status }` |
| **Agent trigger** | Review Request Agent can route via Podium instead of direct Twilio/Google |
| **Notes** | Optional alternative to direct Twilio for practices already using Podium |

---

### INT-013 — WhatsApp Business API *(MOD-COM, P2)*

| Field | Value |
|---|---|
| **Tier** | Native (via Twilio or Meta direct) |
| **Config** | `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_TOKEN` |
| **Purpose** | WhatsApp channel for owner communications (high penetration outside US) |
| **New entities** | Adds `channel='whatsapp'` to `OutboundMessage` |
| **Dependencies** | INT-010 (Twilio) if routing via Twilio; or Meta Graph API (INT-060) if direct |

---

### INT-014 — Google Business Messages *(MOD-COM, P2)*

| Field | Value |
|---|---|
| **Tier** | Webhook |
| **Config** | `GOOGLE_BUSINESS_MESSAGES_AGENT_ID` |
| **Purpose** | Owners can message clinic directly from Google Maps / Search listing |
| **Agent trigger** | Inbound message → Reply Handler Agent → routes to front desk action queue |

---

### INT-015 — Mailchimp / Klaviyo *(MOD-COM / MOD-MAR, P1)*

| Field | Value |
|---|---|
| **Tier** | Native |
| **Config** | `MAILCHIMP_API_KEY` + `LIST_ID` OR `KLAVIYO_API_KEY` + `LIST_ID` |
| **Purpose** | Bulk email for marketing campaigns (not transactional — SendGrid handles that) |
| **New entities** | `EmailCampaign { id, clinic_id, platform, platform_campaign_id, status, sent_count, open_rate, click_rate, attributed_bookings }` |
| **Agent trigger** | Campaign Agent builds segment in VPMA → syncs audience to Mailchimp/Klaviyo → triggers send → polls stats 24h/48h/7d post-send |

---

## MOD-FIN — Financial Integrations

---

### INT-020 — Stripe Terminal *(MOD-FIN, P0)*

| Field | Value |
|---|---|
| **Tier** | Native |
| **Config** | `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`, `STRIPE_TERMINAL_LOCATION_ID` (per clinic) |
| **New entities** | `PaymentTerminal { id, clinic_id, provider='stripe', terminal_id, status, last_seen_at }` |
| **New entities** | `PaymentIntent { id, invoice_id, stripe_payment_intent_id, amount, method, status, settled_at }` |
| **Methods covered** | Tap (NFC), chip, swipe, Apple Pay, Google Pay — all via the same Stripe Terminal reader |
| **Agent trigger** | Invoice approved → Payment Agent → `stripe.terminal.readers.processPaymentIntent` → settled → invoice marked `paid` |
| **Fallback** | If reader offline → generate Stripe payment link → send via MOD-COM → owner pays remotely |
| **Dependencies** | INT-001 (credentials), INT-011 (receipt email) |

---

### INT-021 — Square Terminal *(MOD-FIN, P0 — alternative to INT-020)*

| Field | Value |
|---|---|
| **Tier** | Native |
| **Config** | `SQUARE_ACCESS_TOKEN`, `SQUARE_LOCATION_ID`, `SQUARE_TERMINAL_ID` |
| **Purpose** | Alternative payment processor for practices preferring Square |
| **Methods covered** | Tap, chip, swipe, Apple Pay, Google Pay — same as Stripe |
| **Notes** | VPMA implements a `PaymentProcessor` interface; Stripe or Square slot in behind it. Practice configures one at setup. |

---

### INT-022 — QuickBooks Online *(MOD-FIN, P1)*

| Field | Value |
|---|---|
| **Tier** | Native (OAuth 2.0) |
| **Config** | OAuth flow: practice authorises VPMA to access their QBO company; stores `access_token`, `refresh_token`, `realm_id` |
| **New entities** | `AccountingSync { id, invoice_id, platform='quickbooks', external_id, synced_at, status }` |
| **New entities** | `ChartOfAccountsMapping { clinic_id, vpma_procedure_type, accounting_account_id, account_name }` |
| **Agent trigger** | Payment settled → Billing Agent → POST invoice to QBO API → sync confirmed → `AccountingSync.status = 'synced'` |
| **Sync** | Invoices (create), payments (apply), refunds (credit memo), chart of accounts (read on setup) |
| **Fallback** | Retry queue: T+15m, T+1h, T+4h; after 3 failures → flag to manager with manual export option |

---

### INT-023 — Xero *(MOD-FIN, P1)*

| Field | Value |
|---|---|
| **Tier** | Native (OAuth 2.0) |
| **Config** | OAuth flow → `access_token`, `refresh_token`, `tenant_id` |
| **New entities** | Reuses `AccountingSync` with `platform='xero'` |
| **Agent trigger** | Same as QBO (INT-022); VPMA accounting agent is provider-agnostic |
| **Notes** | Popular in Australia, NZ, UK vet markets |

---

### INT-024 — Wave *(MOD-FIN, P2)*

| Field | Value |
|---|---|
| **Tier** | Webhook |
| **Config** | `WAVE_API_KEY`, `WAVE_BUSINESS_ID` |
| **Notes** | Free accounting for smallest single-vet practices; reduced feature set |

---

### INT-025 — CareCredit *(MOD-FIN, P2)*

| Field | Value |
|---|---|
| **Tier** | Native |
| **Config** | `CARECREDIT_MERCHANT_ID`, `CARECREDIT_API_KEY` |
| **Purpose** | Veterinary financing — owner applies and gets approval in <60s at desk |
| **New entities** | `FinancingApplication { id, invoice_id, provider='carecredit', application_url, approved_amount, status, applied_at, approved_at }` |
| **Agent trigger** | Staff selects CareCredit on Payment Terminal → Payment Agent → generates application URL/QR → polls approval status → on approval: splits payment legs |

---

### INT-026 — Scratchpay *(MOD-FIN, P2)*

| Field | Value |
|---|---|
| **Tier** | Native |
| **Config** | `SCRATCHPAY_PARTNER_ID`, `SCRATCHPAY_API_KEY` |
| **Notes** | Alternative to CareCredit; popular at independent vet practices; same agent pattern as INT-025 |

---

### INT-027 — Trupanion Direct Pay *(MOD-FIN, P1)*

| Field | Value |
|---|---|
| **Tier** | Native |
| **Config** | `TRUPANION_PARTNER_ID`, `TRUPANION_API_KEY` (clinic must be enrolled in Trupanion's practice network) |
| **New entities** | `InsuranceClaim { id, invoice_id, provider, claim_number, submitted_at, covered_amount, owner_owes, status, settled_at }` |
| **Agent trigger** | Invoice approved + patient has `insurance_provider='trupanion'` flag → Insurance Agent → POST claim → Trupanion returns covered_amount in <60s → Payment Terminal auto-splits legs |
| **Demo value** | Highest-impact payment integration to demo: "Trupanion approved $380 — the owner only pays $65" |

---

### INT-028 — Nationwide / ASPCA / Embrace *(MOD-FIN, P2)*

| Field | Value |
|---|---|
| **Tier** | Webhook (submit) + Export (claim PDF) |
| **Config** | Per-provider API credentials |
| **Notes** | Pre-fills claim from SOAP + procedure codes; less real-time than Trupanion |

---

### INT-029 — Gusto Payroll *(MOD-FIN / MOD-STF, P2)*

| Field | Value |
|---|---|
| **Tier** | Native (OAuth) |
| **Config** | `GUSTO_CLIENT_ID`, `GUSTO_CLIENT_SECRET`, OAuth flow |
| **Purpose** | Export approved staff hours to Gusto at week close for payroll processing |
| **New entities** | `PayrollExport { id, clinic_id, platform='gusto', week_start, employee_hours[], status, submitted_at }` |
| **Agent trigger** | Manager approves weekly hours in MOD-STF → Payroll Agent → POST to Gusto → payroll run created in Gusto |

---

### INT-030 — QuickBooks Desktop / Sage / FreshBooks *(MOD-FIN, P2)*

| Field | Value |
|---|---|
| **Tier** | Export |
| **Config** | None (file download) |
| **Purpose** | CSV/IIF export for practices not on cloud accounting |
| **Agent trigger** | End-of-day → Reconciliation Agent → generates export file → available to download in Finance panel |

---

## MOD-INV — Inventory & Purchasing Integrations

---

### INT-040 — Covetrus *(MOD-INV, P0)*

| Field | Value |
|---|---|
| **Tier** | Native |
| **Config** | `COVETRUS_ACCOUNT_ID`, `COVETRUS_API_KEY` |
| **New entities** | `PurchaseOrder { id, clinic_id, distributor, status, line_items[], submitted_at, confirmed_at, estimated_delivery }` |
| **New entities** | `POLineItem { id, po_id, drug_name, dose, quantity, unit_price, distributor_sku, backorder_status }` |
| **Agent trigger** | Drug stock below reorder point → Inventory Agent → fetch live Covetrus pricing → draft PO → manager approves → POST PO to Covetrus API → track status |
| **Price comparison** | Agent fetches pricing from Covetrus + MWI (INT-041) before drafting PO; selects lower unless preferred distributor is within 5% |

---

### INT-041 — MWI Animal Health *(MOD-INV, P0)*

| Field | Value |
|---|---|
| **Tier** | Native |
| **Config** | `MWI_ACCOUNT_ID`, `MWI_API_KEY` |
| **Notes** | Same agent pattern as Covetrus (INT-040); used for price comparison and as backup distributor |

---

### INT-042 — Patterson Veterinary *(MOD-INV, P1)*

| Field | Value |
|---|---|
| **Tier** | Native |
| **Config** | `PATTERSON_ACCOUNT_ID`, `PATTERSON_API_KEY` |
| **Coverage** | Equipment, dental supplies, consumables — not primarily pharma |

---

### INT-043 — Zoetis Direct *(MOD-INV, P2)*

| Field | Value |
|---|---|
| **Tier** | Webhook |
| **Config** | `ZOETIS_ACCOUNT_ID`, `ZOETIS_API_KEY` |
| **Coverage** | Zoetis-brand pharmaceuticals: Simparica, Revolution, Apoquel, Cytopoint, vaccines |
| **Notes** | Lot expiry tracking per vaccine batch — critical for compliance |

---

### INT-044 — IDEXX Direct Supply *(MOD-INV, P2)*

| Field | Value |
|---|---|
| **Tier** | Native |
| **Config** | Shared with IDEXX Lab credentials (INT-050) |
| **Coverage** | IDEXX analyzer reagents, diagnostic consumables |
| **Agent trigger** | Reagent stock low → auto-reorder linked to in-house instrument usage data |

---

### INT-045 — DEA ARCOS Reporting *(MOD-INV, P2)*

| Field | Value |
|---|---|
| **Tier** | Export |
| **Config** | `DEA_REGISTRATION_NUMBER` (per clinic), `DEA_REPORTER_NAME` |
| **New entities** | `DEAReport { id, clinic_id, period, file_path, submitted_at, status }` |
| **Agent trigger** | Monthly: DEA Compliance Agent audits `ControlledSubstanceLog` → generates ARCOS-format report → flags any chain-of-custody gaps before submission |

---

### INT-046 — PDMP / AWARxE *(MOD-INV, P2)*

| Field | Value |
|---|---|
| **Tier** | Webhook |
| **Config** | `PDMP_STATE`, `PDMP_API_KEY`, `PDMP_REPORTER_ID` |
| **Purpose** | Prescription Drug Monitoring Program — query patient controlled substance history before issuing Rx |
| **Agent trigger** | Vet issues controlled substance Rx → Rx Agent queries PDMP → response attached to Rx record → if red flags: warning surfaced to vet before signing |

---

### INT-047 — Merck Animal Health *(MOD-INV, P2)*

| Field | Value |
|---|---|
| **Tier** | Export |
| **Config** | None (PDF/CSV order form) |
| **Notes** | Merck doesn't offer a native API for most practices; PO generated as PDF and emailed |

---

### INT-048 — Generic Distributor / GPO *(MOD-INV, P2)*

| Field | Value |
|---|---|
| **Tier** | Export |
| **Config** | Distributor name, email address for PO delivery |
| **Purpose** | Catch-all for any distributor not natively integrated |
| **Agent trigger** | Same reorder logic; generates PDF PO → emails to configured distributor address |

---

## MOD-ANL — Lab & Diagnostic Integrations

These integrations apply across all clinical modules (results feed patient records, SOAP notes, risk scores, and care timelines).

---

### INT-050 — IDEXX Laboratories *(All Clinical Modules, P0)*

| Field | Value |
|---|---|
| **Tier** | Native (webhook inbound) |
| **Config** | `IDEXX_PRACTICE_ID`, `IDEXX_API_KEY`, webhook endpoint registered with IDEXX |
| **New entities** | `LabResult { id, patient_id, timeblock_id, lab_order_id, provider='idexx', panel_name, results[], flagged_values[], received_at, status }` |
| **Agent trigger** | IDEXX POST to `/api/webhooks/idexx/result` → Lab Agent: matches patient, parses analytes, flags abnormals, updates risk score, attaches to SOAP + care timeline, notifies vet if critical |
| **In-house** | IDEXX Catalyst (chemistry), ProCyte (hematology), SediVue (urinalysis) — same webhook pattern |

---

### INT-051 — Antech Diagnostics *(All Clinical Modules, P1)*

| Field | Value |
|---|---|
| **Tier** | Native (webhook inbound) |
| **Config** | `ANTECH_PRACTICE_ID`, `ANTECH_API_KEY` |
| **Notes** | Same agent pattern as IDEXX (INT-050); practices use one or the other — rarely both |

---

### INT-052 — Heska *(All Clinical Modules, P2)*

| Field | Value |
|---|---|
| **Tier** | Webhook |
| **Config** | `HESKA_INSTRUMENT_ID`, configured in Heska device settings |
| **Coverage** | In-house hematology, chemistry, urinalysis, T4 thyroid |
| **Notes** | Instrument pushes result on analysis complete → same Lab Agent pipeline |

---

### INT-053 — Sound / Diagnostic Imaging & DICOM *(All Clinical Modules, P2)*

| Field | Value |
|---|---|
| **Tier** | Native (DICOM or REST) |
| **Config** | `IMAGING_SERVER_URL`, `DICOM_AE_TITLE` (or REST API credentials) |
| **New entities** | Extends existing `PatientImage` with `dicom_study_id`, `modality` (X-Ray, Ultrasound, CT, MRI), `report_text` |
| **Agent trigger** | Imaging report received → attaches to patient Imaging tab in VetAppointmentCard (already built) → notifies vet |

---

### INT-054 — Zoetis Vetscan / Abaxis *(All Clinical Modules, P2)*

| Field | Value |
|---|---|
| **Tier** | Webhook / Export |
| **Config** | Instrument connection (serial/USB) or CSV upload |
| **Notes** | In-house point-of-care chemistry; result file imported → Lab Agent processes same as INT-050 |

---

## MOD-MAR — Marketing & Social Integrations

---

### INT-060 — Meta Graph API *(MOD-MAR, P1)*

| Field | Value |
|---|---|
| **Tier** | Native (OAuth) |
| **Config** | OAuth flow → `META_PAGE_ACCESS_TOKEN`, `INSTAGRAM_BUSINESS_ACCOUNT_ID`, `FACEBOOK_PAGE_ID` |
| **New entities** | `SocialPost { id, clinic_id, channel, caption, hashtags[], image_url, scheduled_at, platform_post_id, status, impressions, reach, engagement }` |
| **Agent trigger** | Content Agent drafts post → queues for approval → on approval: POST to Graph API → schedule or publish immediately → poll analytics 24h post-publish |

---

### INT-061 — Google My Business API *(MOD-MAR, P1)*

| Field | Value |
|---|---|
| **Tier** | Native (OAuth) |
| **Config** | OAuth flow → `GOOGLE_LOCATION_ID`, service account credentials |
| **New entities** | `ReviewAggregate { clinic_id, platform, avg_rating, total_reviews, last_fetched_at }`, `ReviewResponse { review_id, draft_body, published_at }` |
| **Agent trigger** | Review Agent polls GMB for new reviews daily → new 1-3★: alert to manager + draft response → new 4-5★: trigger review request suppression (already sent) |
| **Post publishing** | Google Business Posts published weekly via Content Agent |

---

### INT-062 — Google Ads API *(MOD-MAR, P2)*

| Field | Value |
|---|---|
| **Tier** | Native (read-only, OAuth) |
| **Config** | `GOOGLE_ADS_CUSTOMER_ID`, service account |
| **Purpose** | Read ad spend + conversions; compute cost-per-booking vs organic |
| **New entities** | `AdPerformanceSnapshot { clinic_id, platform, spend, clicks, conversions, cost_per_conversion, snapshot_date }` |

---

### INT-063 — Canva API *(MOD-MAR, P2)*

| Field | Value |
|---|---|
| **Tier** | Native |
| **Config** | `CANVA_API_KEY`, `CANVA_BRAND_TEMPLATE_ID` |
| **Purpose** | Generate on-brand social graphics from Content Agent image prompts |
| **Agent trigger** | Content Agent writes image brief → Canva API generates graphic using clinic brand template → image attached to `SocialPost` for approval |

---

### INT-064 — Mailchimp *(MOD-MAR, P2)*

| Field | Value |
|---|---|
| **Tier** | Native |
| **Config** | `MAILCHIMP_API_KEY`, `MAILCHIMP_AUDIENCE_ID` |
| **New entities** | Reuses `EmailCampaign` from INT-015 |
| **Agent trigger** | Campaign Agent builds segment → syncs to Mailchimp audience → triggers campaign send → A/B test: agent polls open rates at 4h, picks winner, sends to remainder |

---

### INT-065 — Klaviyo *(MOD-MAR, P2 — alternative to INT-064)*

| Field | Value |
|---|---|
| **Tier** | Native |
| **Config** | `KLAVIYO_API_KEY`, `KLAVIYO_LIST_ID` |
| **Notes** | Same agent pattern as Mailchimp; stronger automation and analytics |

---

### INT-066 — Google Analytics 4 *(MOD-MAR, P2)*

| Field | Value |
|---|---|
| **Tier** | Native (read-only, OAuth) |
| **Config** | `GA4_PROPERTY_ID`, `GA4_MEASUREMENT_ID` |
| **Purpose** | UTM-tagged campaign links → GA4 → bookings attributed to campaign in VPMA dashboard |
| **New entities** | `CampaignAttribution { campaign_id, ga4_session_source, bookings_in_14d, revenue_influenced }` |

---

## MOD-TEL — Telemedicine Integrations

---

### INT-070 — Daily.co *(MOD-TEL, P2)*

| Field | Value |
|---|---|
| **Tier** | Native |
| **Config** | `DAILY_API_KEY` |
| **New entities** | `TeleConsult { id, patient_id, vet_id, room_url, started_at, ended_at, recording_url, status }` |
| **Agent trigger** | Tele-consult booked → Triage Agent → `POST /v1/rooms` → room URL generated → sent to owner (MOD-COM) + vet calendar |
| **Notes** | Lightweight iframe embed — no app download; room expires after consult |

---

### INT-071 — Whereby *(MOD-TEL, P2 — alternative to INT-070)*

| Field | Value |
|---|---|
| **Tier** | Native |
| **Config** | `WHEREBY_API_KEY` |
| **Notes** | Same pattern as Daily.co; similarly simple embed |

---

### INT-072 — Zoom Healthcare *(MOD-TEL, P2 — alternative)*

| Field | Value |
|---|---|
| **Tier** | Native |
| **Config** | `ZOOM_ACCOUNT_ID`, `ZOOM_CLIENT_ID`, `ZOOM_CLIENT_SECRET` |
| **Notes** | HIPAA-compliant tier; heavier SDK but more familiar to owners; preferred for larger practices |

---

## MOD-STF — Staff & HR Integrations

---

### INT-080 — Gusto HR *(MOD-STF, P2)*

| Field | Value |
|---|---|
| **Tier** | Native (OAuth) |
| **Config** | OAuth flow → `GUSTO_COMPANY_ID`, access token |
| **New entities** | `StaffMember` (already in MOD-STF) extended with `gusto_employee_id` |
| **Agent trigger** | New staff added in VPMA → Onboarding Agent → creates employee record in Gusto → triggers Gusto onboarding flow; termination → offboarding |

---

### INT-081 — ADP Workforce Now *(MOD-STF, P2)*

| Field | Value |
|---|---|
| **Tier** | Native (OAuth) |
| **Config** | `ADP_CLIENT_ID`, `ADP_CLIENT_SECRET`, `ADP_ORG_ID` |
| **Notes** | Preferred by mid-to-large practices; same pattern as Gusto (INT-080) |

---

### INT-082 — BambooHR *(MOD-STF, P2)*

| Field | Value |
|---|---|
| **Tier** | Native |
| **Config** | `BAMBOOHR_SUBDOMAIN`, `BAMBOOHR_API_KEY` |
| **Purpose** | HR records, PTO, performance reviews |
| **Agent trigger** | PTO approved in BambooHR → webhook → blocks shift in VPMA schedule; Staff Agent notified |

---

### INT-083 — WhenIWork *(MOD-STF, P2)*

| Field | Value |
|---|---|
| **Tier** | Native |
| **Config** | `WHENIWORK_API_KEY` |
| **Purpose** | Staff mobile shift notifications + schedule acknowledgement |
| **Agent trigger** | VPMA schedule approved → Scheduling Agent → syncs shifts to WhenIWork → staff receive mobile push |

---

### INT-084 — AVMA License Verification *(MOD-STF, P2)*

| Field | Value |
|---|---|
| **Tier** | Native (read-only) |
| **Config** | None (public registry) |
| **Purpose** | Verify vet license number on staff onboarding; monitor for lapses |
| **Agent trigger** | New vet added → Compliance Agent queries AVMA registry → confirms active license → logs verification date |

---

### INT-085 — Paychex Flex *(MOD-STF, P2)*

| Field | Value |
|---|---|
| **Tier** | Webhook |
| **Config** | `PAYCHEX_CLIENT_ID`, `PAYCHEX_CLIENT_SECRET` |
| **Notes** | Alternative to Gusto/ADP; prevalent in smaller regional practices |

---

## MOD-REF — Referral Network Integration

---

### INT-090 — VetConnect Plus / Specialist Directory *(MOD-REF, P3)*

| Field | Value |
|---|---|
| **Tier** | Native (read) + Export (referral letter) |
| **Config** | `VETCONNECT_API_KEY` (optional; can run with seeded specialist directory) |
| **New entities** | `Specialist { id, name, practice_name, specialty[], address, phone, fax, preferred_method, response_rate }` |
| **Agent trigger** | Referral created → Referral Agent queries specialist directory → ranks by specialty + proximity + relationship → drafts referral letter from SOAP → sends via MOD-COM / fax |

---

## MOD-ENT — Enterprise & BI Integrations

---

### INT-100 — Salesforce *(MOD-ENT, P3)*

| Field | Value |
|---|---|
| **Tier** | Native (OAuth) |
| **Config** | `SALESFORCE_CLIENT_ID`, `SALESFORCE_CLIENT_SECRET`, OAuth flow |
| **Purpose** | Franchise CRM — new clinic lead pipeline, onboarding tracking |
| **Agent trigger** | New clinic added to VPMA → Enterprise Agent → creates Account in Salesforce; onboarding milestones synced |

---

### INT-101 — NetSuite ERP *(MOD-ENT, P3)*

| Field | Value |
|---|---|
| **Tier** | Native |
| **Config** | `NETSUITE_ACCOUNT_ID`, `NETSUITE_TOKEN_ID`, `NETSUITE_TOKEN_SECRET` |
| **Purpose** | Consolidated multi-entity financials for PE-backed groups |
| **Notes** | Replaces QuickBooks at enterprise scale; each clinic maps to a NetSuite subsidiary |

---

### INT-102 — Power BI / Tableau *(MOD-ENT, P3)*

| Field | Value |
|---|---|
| **Tier** | Export |
| **Config** | None (scheduled export) |
| **New entities** | `BIExport { clinic_id, export_type, generated_at, file_path }` |
| **Agent trigger** | Weekly: Enterprise Agent generates standardised data export (JSON/CSV) in VPMA data model schema; available for Power BI / Tableau to consume |

---

### INT-103 — Google Looker Studio *(MOD-ENT, P3)*

| Field | Value |
|---|---|
| **Tier** | Export → Google Sheets |
| **Config** | `GOOGLE_SHEETS_SPREADSHEET_ID`, service account |
| **Notes** | Lightweight BI option; VPMA writes to Google Sheets → Looker reads from there; free tier |

---

### INT-104 — QuickBooks Online (Multi-Entity) *(MOD-ENT, P3)*

| Field | Value |
|---|---|
| **Tier** | Native |
| **Notes** | Each clinic in an enterprise group connects its own QBO company; Enterprise Agent aggregates P&L across all companies for the group dashboard |

---

## Integration Summary Table

| ID | Integration | Module | Tier | Phase |
|---|---|---|---|---|
| INT-001 | Credentials Manager | Core | Native | P0 |
| INT-002 | Health Monitor | Core | Native | P0 |
| INT-003 | Avimark Migration | Core | Import | P3 |
| INT-004 | Cornerstone / ezyVet Migration | Core | Import/API | P3 |
| INT-010 | Twilio SMS | MOD-COM | Native | **P0** |
| INT-011 | SendGrid Email | MOD-COM | Native | **P0** |
| INT-012 | Podium | MOD-COM | Webhook | P1 |
| INT-013 | WhatsApp Business | MOD-COM | Native | P2 |
| INT-014 | Google Business Messages | MOD-COM | Webhook | P2 |
| INT-015 | Mailchimp / Klaviyo | MOD-COM/MAR | Native | P1 |
| INT-020 | Stripe Terminal | MOD-FIN | Native | **P0** |
| INT-021 | Square Terminal | MOD-FIN | Native | **P0** |
| INT-022 | QuickBooks Online | MOD-FIN | Native | P1 |
| INT-023 | Xero | MOD-FIN | Native | P1 |
| INT-024 | Wave | MOD-FIN | Webhook | P2 |
| INT-025 | CareCredit | MOD-FIN | Native | P2 |
| INT-026 | Scratchpay | MOD-FIN | Native | P2 |
| INT-027 | Trupanion Direct Pay | MOD-FIN | Native | P1 |
| INT-028 | Nationwide / ASPCA / Embrace | MOD-FIN | Webhook | P2 |
| INT-029 | Gusto Payroll | MOD-FIN/STF | Native | P2 |
| INT-030 | QB Desktop / Sage / FreshBooks | MOD-FIN | Export | P2 |
| INT-040 | Covetrus | MOD-INV | Native | **P0** |
| INT-041 | MWI Animal Health | MOD-INV | Native | **P0** |
| INT-042 | Patterson Veterinary | MOD-INV | Native | P1 |
| INT-043 | Zoetis Direct | MOD-INV | Webhook | P2 |
| INT-044 | IDEXX Direct Supply | MOD-INV | Native | P2 |
| INT-045 | DEA ARCOS | MOD-INV | Export | P2 |
| INT-046 | PDMP / AWARxE | MOD-INV | Webhook | P2 |
| INT-047 | Merck Animal Health | MOD-INV | Export | P2 |
| INT-048 | Generic Distributor | MOD-INV | Export | P2 |
| INT-050 | IDEXX Laboratories | All Clinical | Native | **P0** |
| INT-051 | Antech Diagnostics | All Clinical | Native | P1 |
| INT-052 | Heska | All Clinical | Webhook | P2 |
| INT-053 | Sound / DICOM Imaging | All Clinical | Native | P2 |
| INT-054 | Zoetis Vetscan / Abaxis | All Clinical | Webhook/Export | P2 |
| INT-060 | Meta Graph API | MOD-MAR | Native | P1 |
| INT-061 | Google My Business | MOD-MAR | Native | P1 |
| INT-062 | Google Ads | MOD-MAR | Native (read) | P2 |
| INT-063 | Canva | MOD-MAR | Native | P2 |
| INT-064 | Mailchimp | MOD-MAR | Native | P2 |
| INT-065 | Klaviyo | MOD-MAR | Native | P2 |
| INT-066 | Google Analytics 4 | MOD-MAR | Native (read) | P2 |
| INT-070 | Daily.co | MOD-TEL | Native | P2 |
| INT-071 | Whereby | MOD-TEL | Native | P2 |
| INT-072 | Zoom Healthcare | MOD-TEL | Native | P2 |
| INT-080 | Gusto HR | MOD-STF | Native | P2 |
| INT-081 | ADP Workforce Now | MOD-STF | Native | P2 |
| INT-082 | BambooHR | MOD-STF | Native | P2 |
| INT-083 | WhenIWork | MOD-STF | Native | P2 |
| INT-084 | AVMA License Verification | MOD-STF | Native (read) | P2 |
| INT-085 | Paychex Flex | MOD-STF | Webhook | P2 |
| INT-090 | VetConnect Plus / Specialists | MOD-REF | Native/Export | P3 |
| INT-100 | Salesforce | MOD-ENT | Native | P3 |
| INT-101 | NetSuite ERP | MOD-ENT | Native | P3 |
| INT-102 | Power BI / Tableau | MOD-ENT | Export | P3 |
| INT-103 | Google Looker Studio | MOD-ENT | Export | P3 |
| INT-104 | QuickBooks Multi-Entity | MOD-ENT | Native | P3 |
