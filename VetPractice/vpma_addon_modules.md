# VPMA Add-On Module Design Guide

**Product**: VPMA — Veterinary Practice Management Agent  
**Version**: 1.0 (Base) + Phase 3 (v1.1) complete  
**Document type**: Add-On Module Design — Pre-Build  
**Date**: 2026-06-19  

> **The pattern**: *Every legacy system records. Every agent acts.*  
> Every module below follows this rule. Each replaces a passive record with a proactive agent decision.

---

## Module Map

| Module ID | Name | Primary Value | Complexity | Priority |
|---|---|---|---|---|
| **MOD-FIN** | Financial Operations | Revenue capture & billing automation | High | P1 |
| **MOD-COM** | Client Communications | Real owner outreach & engagement | Medium | P1 |
| **MOD-INV** | Inventory & Pharmacy | Drug stock, dispensing, reorder intelligence | High | P2 |
| **MOD-TEL** | Telemedicine | Remote consultation & triage | Medium | P2 |
| **MOD-ANL** | Analytics & Business Intelligence | Practice health & growth signals | Medium | P2 |
| **MOD-MAR** | Marketing & Social Media | Agentic content, campaigns & reputation | Medium | P2 |
| **MOD-STF** | Staff & HR | Scheduling, compliance, performance | High | P3 |
| **MOD-REF** | Referral Network | Specialist referral management | Low | P3 |
| **MOD-ENT** | Enterprise & Franchise | Multi-location ownership, benchmarking | High | P3 |

---

## MOD-FIN — Financial Operations Module

### The Problem It Solves
After every appointment, a vet practice must manually create an invoice, enter line items from their notes, chase the owner for payment, and handle insurance reimbursements — often days later. Revenue leaks at every step: forgotten line items, slow follow-up, declined cards with no retry, and insurance claims that expire unclaimed.

### The Agentic Edge
```
SOAP Note SIGNED → Billing Agent
  → reads Plan section: "Carprofen 25mg × 14 days, Rabies vaccine, CBC bloodwork"
  → maps procedures/drugs to fee schedule
  → drafts invoice with line items + totals
  → SOAP Note SIGNED → Billing Agent
  → applies practice discount rules automatically
  → detects insurance eligibility via patient flags
  → dispatches invoice draft to front desk for 1-click approval
  → on approval: sends to owner via SMS/email link (MOD-COM required)
  → tracks payment status, queues auto-retry on failure (T+3, T+7)
  → flags uncollected balances to Front Desk action queue
```

### Key Features

**Invoice Drafting Agent**
- Auto-reads signed SOAP Plan section to extract billable items
- Maps to configurable fee schedule (per clinic, overridable per vet)
- Applies: wellness plan discounts, multi-pet discounts, loyalty credits
- Draft appears in Front Desk view for 1-click approval before sending

**Front Desk Payment Terminal**

Owners pay at checkout — the most common scenario. The terminal panel appears in the Front Desk view the moment an invoice is approved, presenting a clean payment interface with all supported methods:

| Method | How it works in VPMA |
|---|---|
| 💳 **Card — Tap / Chip / Swipe** | Stripe Terminal SDK (or Square) — card reader connected via USB or Bluetooth; transaction processed in <5s; receipt auto-emailed via MOD-COM |
| 📱 **Apple Pay / Google Pay** | NFC tap on card reader or QR code shown on front desk screen — owner taps their phone; same Stripe flow, zero manual entry |
| 💵 **Cash** | Staff enters amount tendered → system calculates change due; cash recorded in drawer tally; end-of-day reconciliation report |
| 🏦 **Check** | Check number + amount entered; flagged for deposit; outstanding until cleared |
| 🏥 **CareCredit / Scratchpay** | Staff selects financing option → application link sent to owner's phone (via MOD-COM) or QR code displayed; approval status returned to terminal; approved amount applied to invoice |
| ✂️ **Split Tender** | Owner pays part card, part cash, part financing — split-tender mode splits the invoice total across up to 3 methods; each leg recorded independently |
| 🔄 **Payment Plan** | Practice-set instalment schedule (e.g. 3 × monthly); first payment captured at front desk; remaining instalments queued for auto-charge (card on file) |

**Payment Flow (agentic)**
```
Invoice APPROVED → Payment Agent
  → presents payment method selector to front desk
  → staff selects method → agent routes:
    Card/Tap/NFC → Stripe Terminal → charge → settled
    Cash         → change calc → drawer tally updated
    Financing    → QR/link sent → approval polled (30s timeout)
    Split        → iterates each leg in sequence
  → on full settlement: invoice status → 'paid'
  → receipt generated → email/SMS via MOD-COM
  → Verbose Log: PAYMENT AGENT: $245.00 collected · Visa tap · receipt sent
  → if partial / declined: outstanding balance flagged to action queue
```

**Payment Tracking & Collections**
- Status lifecycle: `draft → approved → partial | paid | overdue | disputed`
- Auto-retry payment link at T+3d and T+7d if balance outstanding
- Balance tracker per owner — handles accounts with multiple pets / invoices
- Declined card: retry prompt at desk + auto-send payment link for later
- Verbose Log shows every payment agent step in real time

**End-of-Day Reconciliation**
- Drawer report: cash in vs. expected (flags discrepancies > $2)
- Daily batch: card settlements, check deposits pending, financing approved
- Summary: total collected by method, outstanding balances, refunds issued
- PDF export for practice bookkeeping / QuickBooks import

**Insurance Claims Agent** *(add-on to add-on)*
- Detects insurance flag on patient record
- Pre-fills SOAP + procedure codes into claim template
- Submits claim draft; tracks reimbursement status
- Integrates with common vet insurance networks (VPI, Nationwide, ASPCA)

**Revenue Dashboard** *(feeds MOD-ANL)*
- Daily: collected, outstanding, drafted — broken down by payment method
- By procedure type, by vet, by clinic
- Aged receivables (30/60/90 day buckets)
- Financing penetration rate (% of invoices using CareCredit/Scratchpay)

### New Entities
| Entity | Key Fields |
|---|---|
| `Invoice` | patient_id, timeblock_id, line_items[], subtotal, discount, total, status, due_date |
| `LineItem` | invoice_id, description, procedure_code, quantity, unit_price |
| `Payment` | invoice_id, amount, method, status, reference_id, attempted_at, settled_at |
| `PaymentLeg` | payment_id, method, amount, status, reference_id |
| `PaymentTerminal` | clinic_id, provider, terminal_id, status, last_seen_at |
| `CashDrawer` | clinic_id, date, opening_float, total_cash_in, discrepancy, closed_at |
| `InsuranceClaim` | invoice_id, provider, claim_number, submitted_at, reimbursement_amount, status |
| `FeeSchedule` | clinic_id, procedure_type, base_price, effective_date |
| `OwnerPaymentProfile` | owner_id, preferred_method, card_on_file (tokenised), financing_approved |

### Demo Flow (60-second demo path)
1. Vet signs SOAP note → Billing Agent fires → invoice draft appears in Front Desk
2. Staff approves invoice → Payment Terminal panel opens automatically
3. Staff selects "Card — Tap" → owner taps phone (Apple Pay) → settled in 3s
4. Verbose Log streams: `PAYMENT AGENT: $245.00 collected · Apple Pay · receipt queued`
5. Invoice badge flips to `✅ Paid` · receipt sent via MOD-COM · drawer tally updated
6. End-of-day: reconciliation report shows $2,840 collected — 68% card, 18% cash, 14% financing

### Dependencies
- VPMA base (SOAP notes, appointments)
- Phase 3 (Prescriptions — for drug billing line items)
- MOD-COM recommended (receipt delivery, payment link retry)
- External: Stripe Terminal or Square (card-present SDK — practice-configured)
- External: CareCredit / Scratchpay API keys (optional; financing methods hidden if unconfigured)

---

## MOD-COM — Client Communications Module

### The Problem It Solves
The current VPMA demo mocks all outbound communication in-UI. Real practices need actual SMS and email delivery — appointment reminders, post-visit summaries, vaccination reminders, promotional campaigns — all while tracking open rates and replies. Without this, every "agentic" outreach is purely cosmetic to the owner.

### The Agentic Edge
```
Message need identified → Communications Agent
  → selects channel (SMS vs email) based on owner preference
  → selects template based on context (reminder / post-visit / care due / promo)
  → personalises with patient + appointment + vet details
  → sends via configured provider (Twilio / SendGrid)
  → tracks delivery status, open, click
  → owner reply → Reply Handler Agent → routes to correct workflow
    → "YES confirm" → Confirmation Agent (F013)
    → "I have a question" → routes to front desk action queue
    → "STOP" → unsubscribes owner from this channel
```

### Key Features

**Multi-Channel Delivery**
- SMS via Twilio (or equivalent)
- Email via SendGrid (or equivalent)
- Per-owner channel preference stored on Owner record
- Fallback: if SMS fails → retry email

**Template Engine**
- System templates: Appointment Reminder, Post-Visit Summary, Care Due, Rx Ready, Invoice
- Custom templates per clinic (branding, tone)
- Merge variables: `{{patient_name}}`, `{{vet_name}}`, `{{appointment_time}}`, `{{clinic_phone}}`

**Two-Way Reply Handling**
- Inbound SMS/email parsed by Reply Handler Agent
- Intent classification: confirm / reschedule / question / unsubscribe
- Routed to correct VPMA workflow or front desk action queue

**Campaign Manager** *(add-on to add-on)*
- Targeted outreach: "all dogs due for heartworm in July within 10 miles"
- Wellness promotion campaigns with response tracking
- Unsubscribe / compliance management (CAN-SPAM, TCPA)

### New Entities
| Entity | Key Fields |
|---|---|
| `Message` | owner_id, channel, template_id, body, status, sent_at, opened_at |
| `Template` | clinic_id, name, channel, subject, body, merge_fields[] |
| `OwnerPreference` | owner_id, preferred_channel, sms_opt_in, email_opt_in |
| `Campaign` | name, target_segment, template_id, sent_count, response_rate |

### Dependencies
- VPMA base (owners, appointments)
- External: Twilio / SendGrid API keys (practice-configured)
- Replaces: Phase 3's mock reply panels with real delivery

---

## MOD-INV — Inventory & Pharmacy Module

### The Problem It Solves
Most vet practices track drug inventory in a spreadsheet or a disconnected pharmacy system. When a vet prescribes Carprofen, nobody checks whether there are 14 tablets in stock. Controlled substances are logged manually on paper. Reorder happens reactively, when someone notices an empty shelf.

### The Agentic Edge
```
Prescription ISSUED → Inventory Agent
  → checks stock level for drug_name + dose
  → if sufficient: reserves quantity, updates on-hand count
  → if insufficient: flags to front desk with "Stock Alert"
  → if controlled substance: creates DEA log entry automatically
  → when stock falls below reorder_point: drafts Purchase Order to supplier
  → PO draft sent to practice manager for 1-click approval
  → on receipt: stock level updated, lot numbers recorded
```

### Key Features

**Drug Inventory Tracking**
- Per-clinic stock levels with unit tracking (tablets, mL, vials)
- Reservation system: when Rx issued, quantity reserved before dispense
- Lot number + expiry tracking per batch
- Low stock alerts in Front Desk action queue

**Controlled Substance Compliance**
- DEA Schedule II–V automatic log entries on prescription + dispense
- Audit trail with vet signature capture
- Reconciliation alerts when physical count ≠ system count

**Smart Reorder Agent**
- Calculates reorder point from rolling 8-week usage rate (same data as Forecast agent)
- Drafts Purchase Order to preferred supplier when below threshold
- Tracks: on-order, in-transit, received states
- Compares supplier pricing; flags substitutes when preferred item is back-ordered

**Pharmacy Dispensing Workflow**
- Converts approved Rx into dispensing work order
- Label generation: patient name, drug, dose, frequency, refills, vet name
- Dispense recorded, inventory decremented, owner notified via MOD-COM

### New Entities
| Entity | Key Fields |
|---|---|
| `DrugStock` | clinic_id, drug_name, dose, quantity_on_hand, reorder_point, unit |
| `StockLot` | drug_stock_id, lot_number, expiry_date, quantity, received_date |
| `PurchaseOrder` | clinic_id, supplier, line_items[], status, ordered_at, received_at |
| `ControlledSubstanceLog` | prescription_id, drug_name, schedule, quantity_dispensed, vet_id, dea_log_date |
| `DispenseRecord` | prescription_id, quantity_dispensed, dispensed_by, dispensed_at, label_printed |

### Dependencies
- VPMA Phase 3 (Prescriptions — MOD-INV consumes Prescription events)
- MOD-FIN recommended (dispensing triggers billing line item)
- External: Supplier APIs optional (can run as manual PO print)

---

## MOD-TEL — Telemedicine Module

### The Problem It Solves
Post-COVID, owners expect to consult their vet without driving 45 minutes. Minor follow-ups, post-surgical check-ins, and triage calls are best served remotely — but vet practices have no infrastructure for it. Video calls happen on personal phones; notes go nowhere; no charge is captured.

### The Agentic Edge
```
Owner requests tele-consult → Triage Agent
  → reviews patient record + last SOAP + active prescriptions
  → classifies: routine_consult | urgent_in_person_required | emergency
  → if routine: books video slot on vet calendar, sends link to owner
  → if urgent: books same-day in-person, notifies front desk
  → if emergency: provides emergency clinic referral immediately
  
During/after call:
  → Vet uses SOAP workspace in video overlay
  → Post-call: SOAP auto-signed, Billing Agent fires (MOD-FIN)
  → Follow-up: MOD-COM sends post-consult summary to owner
```

### Key Features

**Smart Triage Agent**
- Pre-screen: owner describes issue via intake form (same F002 pattern)
- AI triage: maps symptoms to consult type (routine vs in-person required)
- Prevents unnecessary video consults from becoming in-person emergencies

**Video Consultation**
- Embedded video (Daily.co, Whereby, or similar iframe embed — no heavy SDK)
- Vet has SOAP workspace side-by-side in split view
- Owner can share camera (skin condition, wound, limping gait review)

**Remote Prescription** *(state-law dependent)*
- Vet-client-patient relationship (VCPR) flag required before Rx issuable post-tele-consult
- VCPR status tracked per owner-vet pair
- Controlled substances blocked for remote Rx (compliance)

**Async Tele-Triage** *(lighter version)*
- Owner submits photos + text (extends F002 photo intake)
- Vet reviews async, responds with: "Come in", "Watch and wait", "Here's your Rx"
- Full interaction logged in patient history

### New Entities
| Entity | Key Fields |
|---|---|
| `TeleConsult` | patient_id, vet_id, triage_classification, scheduled_at, video_url, status |
| `VCPRRecord` | patient_id, vet_id, established_date, last_consult_date |
| `AsyncTriage` | patient_id, submitted_at, photos[], symptoms, vet_response, resolved |

### Dependencies
- VPMA base + Phase 3 (uses SOAP, Prescriptions, patient history)
- MOD-COM (for link delivery + follow-up)
- MOD-FIN (for tele-consult billing)
- External: video provider (iframe embed only — no heavy SDK)

---

## MOD-ANL — Analytics & Business Intelligence Module

### The Problem It Solves
Practice owners manage on instinct: "it feels like we're busier than last year." They have no dashboard that shows churn risk, procedure mix trends, vet utilisation gaps, or which referral sources generate the highest lifetime value patients.

### The Agentic Edge
```
Nightly → Analytics Agent
  → reads: appointments, revenue, care events, prescriptions, waitlist
  → computes: utilisation rate, no-show rate, avg revenue per visit,
              patient retention cohorts, procedure mix by vet
  → compares: week-over-week, month-over-month, same-period-last-year
  → generates: Practice Health Score (0-100) with contributing factors
  → surfaces: "3 high-value patients haven't visited in 18 months — consider outreach"
  → pushes: insight cards to Regional Manager view (extends F019 Forecast)
```

### Key Features

**Practice Health Score**
- Composite 0-100 score: revenue pace + utilisation + retention + care compliance
- Trend arrow (improving/declining/stable) with primary driver text
- Drill-down: click any score component to see contributing patients/appointments

**Patient Retention Intelligence**
- Cohort analysis: patients acquired in month X — how many returned?
- Churn risk flags: patients not seen in 12+ months with active care protocols
- Win-back campaign trigger → MOD-COM

**Procedure & Revenue Mix**
- Which procedures are trending up/down?
- Vet-level analysis: Dr. Smith's avg revenue per appointment vs clinic average
- Time-of-day and day-of-week heat map for booking patterns

**Referral Source Tracking**
- Track how new patients were acquired (online, referral, walk-in)
- Lifetime value by acquisition source
- ROI on wellness campaigns (MOD-COM integration)

### New Entities
| Entity | Key Fields |
|---|---|
| `DailySnapshot` | clinic_id, snapshot_date, utilisation_pct, revenue, visit_count, new_patients |
| `RetentionCohort` | clinic_id, cohort_month, acquired_count, returned_3m, returned_12m |
| `InsightCard` | clinic_id, insight_type, title, body, severity, generated_at, dismissed |
| `ReferralSource` | patient_id, source_type, source_detail, acquisition_date |

### Dependencies
- All VPMA modules (reads data across the full system)
- MOD-FIN strongly recommended (revenue data quality)
- MOD-COM for campaign execution

---

## MOD-STF — Staff & HR Module

### The Problem It Solves
Vet practices schedule staff manually — often on paper or in a general-purpose tool like Google Calendar. There's no system that prevents double-scheduling a vet tech, tracks continuing education (CE) credits, flags when a vet's DEA license is expiring, or auto-calculates overtime.

### The Agentic Edge
```
Weekly → Staff Scheduling Agent
  → reads: vet/tech availability windows, clinic capacity, historical demand
  → generates: optimal weekly schedule respecting: max hours, CE days, clinic assignments
  → detects: conflicts with vet clinic assignments from F007 Multi-Clinic
  → flags: upcoming license expirations (30d, 7d, 1d warnings)
  → on schedule approval: notifies staff via MOD-COM

Continuous → Compliance Agent
  → tracks CE credit hours per staff member
  → monitors: DEA registration, state veterinary license, rabies vaccination status
  → flags impending expirations in action queue
  → triggers renewal reminders via MOD-COM
```

### Key Features

**Staff Availability & Scheduling**
- Weekly schedule builder with drag-and-drop (extends RoleSelector concept)
- Conflict detection: prevents double-booking, enforces max hours
- CE day blocking: marks days when vet is at conference
- Integrates with F007 vet-clinic-assignment data

**License & Compliance Tracker**
- Per-staff: DEA registration, state vet license, CPR, CE hours YTD
- Expiry tracking with automated reminder pipeline (MOD-COM)
- Practice-level compliance dashboard for manager review

**Time & Attendance**
- Clock in/out (simple; no biometrics)
- Overtime flagging
- Integration hook for payroll export (CSV or QuickBooks format)

### New Entities
| Entity | Key Fields |
|---|---|
| `StaffMember` | resource_id (FK to resources), role, hire_date, certifications[], max_hours_week |
| `ShiftSchedule` | staff_id, clinic_id, week_start, shifts[] |
| `License` | staff_id, license_type, license_number, expiry_date, status |
| `CERecord` | staff_id, course_name, provider, credits, completed_date |
| `TimeEntry` | staff_id, clock_in, clock_out, approved, overtime_minutes |

### Dependencies
- VPMA base + F007 Multi-Clinic (shares Resource/vet data)
- MOD-COM (for expiry reminders, schedule notifications)

---

## MOD-REF — Referral Network Module

### The Problem It Solves
General practice vets refer out to specialists (cardiologists, oncologists, orthopedic surgeons) constantly — but the referral is a fax or a phone call. There's no tracking: did the specialist receive it? Did the patient go? Did the report come back? Practices lose continuity.

### The Agentic Edge
```
Vet clicks "Refer to Specialist" → Referral Agent
  → searches specialist network (seeded or API-connected)
  → ranks by: specialty, proximity, availability, past relationship
  → generates referral letter draft from SOAP note (name, history, reason, urgency)
  → sends to selected specialist practice via MOD-COM / fax API
  → tracks: sent → accepted → appointment booked → report received
  → when report received: attaches to patient record, notifies referring vet
  → if no response in 5 days: flags to front desk for follow-up
```

### Key Features

**Specialist Directory**
- Seeded with common specialties: Cardiology, Oncology, Dermatology, Orthopedics, Neurology, Ophthalmology, Exotics
- Per-specialist: practice name, vet name, specialties, address, fax, preferred referral method
- Relationship tracking: practices you've referred to before, response rate

**Referral Letter Generator**
- Auto-drafts from SOAP note + patient history
- Includes: reason for referral, history summary, current medications (MOD-INV), diagnostic results
- Vet edits + signs in Rx tab style; staff sends

**Continuity Tracking**
- Referral status board in Vet view: pending / in-progress / report received
- Report attachment to patient record on receipt
- Closes the loop: referring vet notified when specialist sends back report

### New Entities
| Entity | Key Fields |
|---|---|
| `Specialist` | name, practice_name, specialty[], address, fax, preferred_method |
| `Referral` | patient_id, referring_vet_id, specialist_id, reason, urgency, status, sent_at |
| `ReferralReport` | referral_id, received_at, summary, attachment_url |

### Dependencies
- VPMA base + Phase 3 (SOAP notes, Prescriptions)
- MOD-COM (for delivery of referral letters)

---

## MOD-MAR — Marketing & Social Media Module

### The Problem It Solves
Vet practices have zero time for marketing. The owner is also the head vet. Social media accounts go dark for weeks. Google reviews accumulate unanswered. When a happy client leaves the clinic, nobody captures that moment to request a review or share a story. Practices that should be thriving locally are invisible online.

### The Agentic Edge
```
Appointment COMPLETED → Marketing Agent
  → reads: patient species, procedure, outcome (from SOAP), owner satisfaction signal
  → if positive signal: drafts personalised review request to owner (MOD-COM)
  → if 5-star review received: drafts clinic social post ("Buddy's dental went great today!")
  → nightly → Content Calendar Agent:
    → reads: upcoming breed awareness days, pet health calendar events, seasonal hooks
    → reads: this week's appointment types ("3 dental cleans" → dental health content)
    → drafts: 3-5 social posts per week (Instagram caption + image prompt + hashtags)
    → queues for staff approval → 1-click publish to connected accounts
  → monthly → Campaign Agent:
    → reads: care protocol gaps (patients overdue for vaccines) from MOD-ANL
    → drafts: targeted email/SMS campaign ("Heartworm season — is your dog protected?")
    → A/B variants: 2 subject lines, tracks open rate winner
    → reports: campaign reach, bookings attributed, revenue influenced
```

### Key Features

**Reputation & Review Agent**
- Post-visit trigger: 24h after completed appointment, sends personalised review request
- Smart targeting: only requests from satisfied owners (no recent complaints, no billing disputes)
- Platform routing: Google → primary; Facebook → secondary; Vet-specific (VetRatingz, Pawshake) → optional
- Negative signal detection: if owner sent a complaint → suppress review request, flag to manager
- Review monitoring: aggregates reviews across platforms, notifies on new 1-3★ reviews for response

**Social Media Content Agent**
- Content calendar: auto-populates 7-day rolling schedule from:
  - Appointment types that week (dental → dental health tips; vaccines → puppy/kitten season)
  - Pet calendar hooks (National Dog Day, Adopt-a-Cat Month, World Veterinary Day)
  - Breed-specific spotlights (pulls from breed protocols — "Did you know Bulldogs need special anaesthesia care?")
- Post format per channel:
  - Instagram: caption (160 chars) + 5 hashtags + image prompt (handed to generate_image or Canva API)
  - Facebook: longer copy (280 chars) + link to booking page
  - Google Business Post: 750-char update with call-to-action
- Approval workflow: all posts sit in "Pending Approval" queue in Marketing panel; staff reviews + publishes with one click
- Analytics: impressions, reach, engagement rate per post tracked post-publish

**Campaign Manager**
- Segment builder: "dogs 7+ years old, last visit > 6 months" → senior wellness campaign
- Drip sequences: new patient welcome (day 1, day 7, day 30 messages)
- A/B subject line testing: agent picks winner after 4-hour send; auto-sends winner to remainder
- Attribution tracking: links between campaign sends and appointment bookings made within 14 days
- Compliance: CAN-SPAM / TCPA opt-out management; blacklist sync with MOD-COM

**Practice Story Generator** *(differentiator)*
- Once weekly: agent scans completed appointments for compelling stories
  - Species: exotic (bird, reptile) → higher story value
  - Outcome: surgery success, first visit, long-term chronic patient milestone
- Drafts: a 2-paragraph "patient story" formatted for the practice blog or newsletter
- Owner consent flag: only published if owner has opted into story sharing (stored on Owner record)
- Feeds: email newsletter, website blog section, social long-form post

**Ad Performance Integration** *(add-on to add-on)*
- Connects to Google Ads / Meta Ads (read-only API)
- Shows: spend, clicks, conversions alongside organic booking data
- ROI calculation: cost-per-new-patient from paid vs organic vs referral channels
- Budget recommendation: agent flags if ad spend is underperforming vs organic benchmarks

### New Entities
| Entity | Key Fields |
|---|---|
| `ReviewRequest` | owner_id, timeblock_id, platform, status, sent_at, review_url, rating_received |
| `SocialPost` | clinic_id, channel, caption, hashtags, image_prompt, scheduled_at, status, published_at, impressions |
| `ContentCalendar` | clinic_id, week_start, posts[], approved_count, published_count |
| `MarketingCampaign` | name, segment_query, template_id, channel, status, sent_count, open_rate, attributed_bookings |
| `PracticeStory` | patient_id, timeblock_id, headline, body, consent_given, published_at, channels[] |
| `ReviewAggregate` | clinic_id, platform, avg_rating, total_reviews, last_fetched_at |

### Demo Flow (60-second demo path)
1. Vet completes appointment for Buddy → Marketing Agent fires in Verbose Log
2. Review request queued → "Owner notified — Google review requested"
3. Content Calendar panel shows 3 draft posts for this week, each with channel badge
4. Staff clicks "Approve & Schedule" on a dog dental post → published badge appears
5. Campaign panel shows "Senior Wellness Campaign — 12 recipients, 3 attributed bookings"

### New Roles
- **Practice Manager** (new role variant): sees Marketing panel, Content Calendar, Campaign Manager, Review Aggregate
- Vet / Front Desk do not see marketing panels (role-gated)

### Dependencies
- VPMA base (appointments, owners, patients for segmentation)
- Phase 3 (care events, breed protocols — feed content ideas and campaign segments)
- MOD-COM (delivery of review requests and campaigns)
- MOD-ANL (patient segments, churn lists for campaign targeting)
- External: social platform APIs (Meta Graph, Google My Business) — optional; can run in draft-only mode without credentials

---

## MOD-ENT — Enterprise & Franchise Module

### The Problem It Solves
VPMA v1.0 supports multi-clinic within one ownership group. Enterprise practices — franchise networks, DSOs (Dental Service Organizations) in the vet world, PE-backed groups — need: consolidated P&L across 20+ locations, benchmarking between clinics, centralized protocol management ("all clinics use this wellness protocol"), and owner/investor-level dashboards separate from the GM/manager level.

### The Agentic Edge
```
Daily → Enterprise Intelligence Agent
  → aggregates: performance data from all clinics in ownership group
  → computes: enterprise-level KPIs (revenue, utilisation, NPS, compliance score)
  → benchmarks: each clinic against network average and top-quartile peer
  → flags: underperforming clinics ("Downtown -18% vs network avg for 3rd consecutive week")
  → generates: investor-ready weekly summary (PDF export)
  → detects: protocol drift ("Westside not following wellness plan F015 protocols for 12% of patients")
```

### Key Features

**Enterprise Dashboard**
- All clinics in one view with roll-up KPIs
- Drill-down from network → region → clinic → individual vet
- Benchmark heat map: which clinics are top/middle/bottom quartile

**Centralized Protocol Management**
- Define care protocols, breed protocols, fee schedules at enterprise level
- Push to all clinics with version control
- Clinics can customize within allowed bounds; drift is flagged

**Investor Reporting**
- Auto-generated weekly/monthly PDF reports
- Revenue, EBITDA proxy, headcount efficiency, patient growth
- Configurable audience: investor view (financial only) vs. operator view (full)

**Franchise Onboarding**
- New clinic provisioning wizard (extends F007 clinic creation)
- Seed data templates for common clinic configurations
- Compliance checklist: license, DEA, equipment, staff certifications

### New Entities
| Entity | Key Fields |
|---|---|
| `OwnershipGroup` | name, primary_contact, tier (single/group/franchise/enterprise) |
| `EnterpriseSnapshot` | group_id, snapshot_date, total_revenue, avg_utilisation, clinic_count |
| `BenchmarkScore` | clinic_id, metric, score, percentile_rank, snapshot_date |
| `ProtocolOverride` | clinic_id, protocol_type, protocol_id, overridden_at, approved_by |

### Dependencies
- All VPMA modules (reads everything)
- F007 Multi-Clinic (foundational)
- MOD-FIN, MOD-ANL (required for meaningful benchmarking)

---

## Recommended Build Sequence

```
Base VPMA (v1.0+v1.1 Phase 3)
        │
        ├── MOD-COM   ← unlock real delivery first; everything depends on it
        │
        ├── MOD-FIN   ← highest revenue impact; depends on COM for delivery
        │
        ├── MOD-INV   ← pharmacy & drug management; depends on FIN for billing
        │
        ├── MOD-ANL   ← starts returning value immediately after FIN + COM
        │
        ├── MOD-MAR   ← visibility & growth; depends on COM (delivery) + ANL (segments)
        │
        ├── MOD-TEL   ← new revenue stream; depends on COM + FIN
        │
        ├── MOD-STF   ← operational efficiency; can run somewhat standalone
        │
        ├── MOD-REF   ← continuity differentiator; depends on base + COM
        │
        └── MOD-ENT   ← enterprise play; requires FIN + ANL + MAR + all of the above
```

### Pricing Tier Concept

| Tier | Modules | Target |
|---|---|---|
| **Starter** | Base VPMA (v1.0+v1.1) | Single-clinic, 1–3 vets |
| **Professional** | + MOD-COM + MOD-FIN | Growth practices, 3–8 vets |
| **Clinical** | + MOD-INV + MOD-TEL | Full-service clinics with pharmacy |
| **Practice+** | + MOD-ANL + MOD-MAR + MOD-STF + MOD-REF | Multi-vet, growth-focused |
| **Enterprise** | + MOD-ENT (all modules) | Groups, franchises, PE-backed |
