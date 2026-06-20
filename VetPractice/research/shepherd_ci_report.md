# Shepherd CI Report

## Executive Summary

Shepherd is a cloud-native PIMS founded by veterinarians. Marquee differentiators: TranscribeAI (ambient SOAP drafting), SummarizeAI, DiagnoseAI. Pricing starts ~$299/month unlimited users, per-DVM-count model. AI approach is reactive and doctor-controlled (human-in-the-loop) — no autonomous agentic pipeline.

---

## Pricing

- Starting: ~$299/month (1 DVM)
- Model: Subscription by DVM count, unlimited users
- AI tools: Included in subscription
- Shepherd Pay: processing fees above market (user complaint)
- Public pricing page: does not exist

---

## Part 1: Feature Matrix (All 60 Features)

### Scheduling (S)

| Code | Feature | Score | Notes |
|------|---------|-------|-------|
| S01 | Appointment scheduling | ✅ HIGH | Native whiteboard/schedule SOAP-linked |
| S02 | Multi-location support | ✅ HIGH | Dedicated multi-location portal, centralized admin |
| S03 | Room & resource management | ⚠️ MED | Appointment templates; no dedicated room-mapping UI |
| S04 | Waitlist management | 🔌 MED | Oliver integration; not native |
| S05 | Automated reminders | ✅ HIGH | Built-in unlimited texts/emails; no extra cost |
| S06 | Two-way client texting | ✅ HIGH | Native unlimited two-way SMS; syncs to record |
| S07 | Online self-scheduling | 🔌 HIGH | PetDesk Direct Booking or Chckvet; not native |
| S08 | Boarding/kennel management | ⚠️ LOW | Boarding calendar mentioned; no dedicated kennel depth |

### Clinical (C)

| Code | Feature | Score | Notes |
|------|---------|-------|-------|
| C01 | SOAP note creation | ✅ HIGH | Core product strength; SOAP is primary workflow hub |
| C02 | AI-assisted SOAP drafting | ✅ HIGH | TranscribeAI: ambient AI, native, no third party |
| C03 | Pre-visit intake | 🔌 MED | Chckvet/Otto digital forms; no native intake module |
| C04 | Photo/imaging attachment | ✅ HIGH | DICOM via 3 PACS integrations; native photo attachment |
| C05 | Vaccine & care protocol tracking | ✅ HIGH | Core feature; automated vaccine reminders |
| C06 | Prescription management | ✅ HIGH | Native Rx + Koala Health + Blue Rabbit pharmacy |
| C07 | Breed-specific alerts | ⚠️ MED | DiagnoseAI may surface context; no explicit breed-alert UI |
| C08 | Patient risk scoring | ❓ LOW | No explicit risk-scoring module found |
| C09 | Post-visit follow-up automation | ✅ HIGH | Messaging Center, Otto, AllyDVM integrations |
| C10 | Telemedicine | ❌ MED | No telemedicine/video integration found in any source |

### Laboratory (L)

| Code | Feature | Score | Notes |
|------|---------|-------|-------|
| L01 | IDEXX in-house analyzer | ✅ HIGH | Full comprehensive in-house integration |
| L02 | IDEXX Reference Lab | ✅ HIGH | Same integration covers both in-house and reference |
| L03 | Antech | ✅ HIGH | Direct two-way integration; top-tier partner |
| L04 | Heska | ✅ HIGH | Create/manage lab orders from SOAP |
| L05 | Vetscan/Abaxis | ❓ LOW | Not found in integration list |
| L06 | DICOM/imaging | ✅ HIGH | IDEXX PACS, IDEXX Web PACS, Sound SmartPACS (3 options) |
| L07 | Critical value flags | ❓ LOW | Not specifically documented |
| L08 | Auto-filing lab results | ✅ HIGH | Results auto-populate into patient record |

### Financial (F)

| Code | Feature | Score | Notes |
|------|---------|-------|-------|
| F01 | Invoice generation | ✅ HIGH | Auto-builds invoice in real-time as SOAP is documented |
| F02 | Auto-invoice from SOAP | ✅ HIGH | Core differentiator — SOAP actions auto-push to invoice |
| F03 | Card-present payments | ✅ HIGH | Shepherd Pay native payment terminals |
| F04 | Apple/Google Pay | ❓ LOW | Text-to-Pay confirmed; mobile wallets not explicitly confirmed |
| F05 | Payment plans/financing | ✅ HIGH | Sunbit BNPL integration (4 interest-free payments) |
| F06 | Split-tender payments | ❓ LOW | Not found |
| F07 | End-of-day reconciliation | ⚠️ MED | Via QuickBooks integration; native reporting mentioned |
| F08 | QuickBooks/Xero integration | ✅ HIGH | QuickBooks confirmed; Xero unconfirmed |
| F09 | Pet insurance claims | 🔌 HIGH | VICoverage/Vertical Insure marketplace; Pawlicy Advisor |
| F10 | Collections tracking | ❓ LOW | Multi-location group statements confirmed; dedicated collections not found |

### Inventory (I)

| Code | Feature | Score | Notes |
|------|---------|-------|-------|
| I01 | Drug inventory tracking | ✅ HIGH | Real-time deduction as products administered; barcode scanning |
| I02 | Controlled substance logging | 🔌 HIGH | VetSnap integration (automated overnight reconciliation) |
| I03 | Smart reorder/POs | ⚠️ MED | Native basic reorder; Inventory Ally for advanced |
| I04 | Prescription label printing | ✅ HIGH | Native; Koala/Blue Rabbit for fulfillment |
| I05 | Dispensing workflow | ✅ HIGH | SOAP → invoice → inventory chain |
| I06 | Lot & expiry tracking | ✅ HIGH | Lot number tracking confirmed |

### Reporting (R)

| Code | Feature | Score | Notes |
|------|---------|-------|-------|
| R01 | Revenue reports | ✅ HIGH | Native revenue reporting included |
| R02 | Utilization reports | ⚠️ MED | Basic native; advanced via iVET360 integration |
| R03 | Patient retention analytics | 🔌 MED | iVET360, AllyDVM; not confirmed native |
| R04 | Custom report builder | ⚠️ MED | Some customization; users note could be more robust |
| R05 | Multi-clinic dashboards | ✅ HIGH | Centralized admin portal for multi-location |
| R06 | AI-driven insights | ⚠️ MED | DiagnoseAI, SummarizeAI; no predictive business analytics |

### Platform (P)

| Code | Feature | Score | Notes |
|------|---------|-------|-------|
| P01 | Open API | ✅ HIGH | Open API confirmed; powers third-party integrations |
| P02 | Payroll integration | ⚠️ HIGH | Native Time Clock/timesheets; no Gusto/ADP direct integration |
| P03 | Accounting integration | ✅ HIGH | QuickBooks confirmed |
| P04 | Supplier/GPO integration | ✅ MED | mClub (Midwest Vet Supply); VetCove referenced |
| P05 | Data migration tools | ❓ LOW | Not publicly documented; demo-required conversation |
| P06 | Mobile app | ⚠️ MED | Responsive web app on mobile/tablet; no dedicated iOS/Android app |
| P07 | Cloud-based | ✅ HIGH | 100% cloud; no server required |
| P08 | SSO | ❓ LOW | Not mentioned anywhere |

### AI/Agentic (A)

| Code | Feature | Score | Notes |
|------|---------|-------|-------|
| A01 | AI SOAP drafting | ✅ HIGH | TranscribeAI: ambient, no third party, no behavior change required |
| A02 | Agentic pre-visit intake | ❌ HIGH | No autonomous pre-visit AI agent |
| A03 | Patient risk scoring (automated) | ❌ MED | DiagnoseAI = clinical suggestions; no risk score engine |
| A04 | Agentic follow-up | ❌ HIGH | Messaging templates exist; no autonomous follow-up agent |
| A05 | AI waitlist backfill | ❌ HIGH | Waitlist via Oliver; no AI-powered backfill |
| A06 | Agentic reminder pipeline | ❌ MED | Reminders automated but rule-based, not AI-driven |
| A07 | Predictive forecasting | ❌ MED | iVET360 = historical analytics only; no predictive |
| A08 | Agentic billing from SOAP | ⚠️ HIGH | SOAP auto-builds invoice (rule-based trigger, not true agentic AI) |
| A09 | Agent audit log | ❌ HIGH | No AI decision audit trail |
| A10 | Modular AI architecture | ❌ MED | Three discrete AI tools; not a composable agentic framework |

---

## Score Summary

| Category | ✅ | ⚠️ | 🔌 | ❌ | ❓ |
|----------|---|---|---|---|---|
| Scheduling (8) | 4 | 2 | 2 | 0 | — |
| Clinical (10) | 5 | 2 | 1 | 1 | 1 |
| Laboratory (8) | 5 | 0 | 1 | 1 | 1 |
| Financial (10) | 5 | 2 | 1 | 0 | 2 |
| Inventory (6) | 4 | 1 | 1 | 0 | — |
| Reporting (6) | 2 | 3 | 1 | 0 | — |
| Platform (8) | 4 | 3 | 0 | 0 | 1 |
| AI/Agentic (10) | 1 | 1 | 0 | 8 | — |
| **TOTAL (60)** | **30** | **14** | **6** | **10** | **5** |

---

## Part 2: Deep Teardown

### Q1. TranscribeAI

Ambient AI (not dictation). Listens to full two-way client-doctor conversation in real time. Filters non-medical dialogue and ambient noise. Context-aware parsing into S/O/A/P sections. Doctor reviews and approves before finalizing. Native/zero-friction — embedded directly in Shepherd SOAP. Learns from use. No published accuracy %. Recommend closing exam room doors or using wireless microphones. Different from dictation (Dragon): dictation requires active speech commands; TranscribeAI requires zero behavior change.

### Q2. AI Beyond SOAP

3-tool AI suite (ShepherdAI):

- **TranscribeAI:** Ambient SOAP drafting — ❌ not agentic (vet approves)
- **SummarizeAI:** Patient history retrieval on-demand — ❌ not agentic
- **DiagnoseAI:** Differential dx support, dosing, discharge instructions — ❌ advisory only

No agentic or autonomous features. Design philosophy is explicitly "doctor-controlled." All AI is reactive (triggered by vet action), advisory (suggests, doesn't execute), siloed (three discrete tools), single-context (operates within current SOAP).

### Q3. Pricing Model

~$299/mo 1 DVM, unlimited users, by DVM count. No public pricing page (demo required). AI tools appear included. Shepherd Pay (payments) has above-market fees.

### Q4. Target Market

Independent companion animal practices 1–4 DVMs transitioning from legacy. Secondary: small DSO groups 2–8 clinics. Not targeting: emergency/specialty hospitals, large corporate, equine/large animal. "Built by vets, for vets" messaging.

### Q5. Native vs Integrations

**Native:**
- SOAP note creation + TranscribeAI/SummarizeAI/DiagnoseAI
- Auto invoice from SOAP
- Unlimited two-way SMS/email reminders
- Drug inventory tracking (real-time deduction, barcode scanning)
- Lot & expiry tracking
- Prescription label printing
- Time Clock/timesheets
- Multi-location admin portal
- Revenue reporting
- Open API

**Deep Software Integrations:**
- IDEXX (in-house + reference lab + PACS)
- Antech (two-way)
- Heska (two-way)
- QuickBooks
- Sunbit (BNPL)
- VetSnap (CS logging)
- Koala Health / Blue Rabbit (pharmacy fulfillment)
- PetDesk / Chckvet (online scheduling)
- Oliver (waitlist)
- Otto / AllyDVM / iVET360 (client comms & analytics)
- VICoverage / Vertical Insure / Pawlicy Advisor (insurance)
- Inventory Ally (advanced reorder)

**Data Connections / Resources:**
- mClub (Midwest Vet Supply)
- VetCove (supplier marketplace)

### Q6. Top Complaints

1. Click-heavy multi-tab workflows (#1 complaint)
2. Post-update instability/outages
3. Data loss / no auto-save (anesthesia records)
4. Click-heavy Rx workflow
5. Limited reporting customization
6. Shepherd Pay fees
7. Chat-only support

### Q7. Marketing Positioning

"Built by veterinarians, for veterinarians" — clinical credibility. "Workflow-first design." "Never miss a charge." "Modern, cloud-based." "AI-powered." "Doctor-controlled AI." Anti-legacy tone.

### Q8. What Vets Wish Shepherd Had

- Native telemedicine
- Native online scheduling
- Better Rx workflow
- Auto-save/draft protection
- Robust custom reporting
- Lower payment processing fees
- SSO for enterprise
- Agentic follow-up
- Predictive analytics
- Boarding/kennel depth

### Q9. Shepherd vs VPMA

| Dimension | Shepherd | VPMA |
|-----------|----------|------|
| AI philosophy | Reactive, doctor-controlled, advisory only | Proactive, agentic, autonomous pipeline |
| SOAP AI | Ambient (listens, suggests, vet approves) | Agentic (drafts AND triggers downstream actions) |
| Follow-up | Template-based messaging, manually triggered | Autonomous — detects need, drafts, sends |
| Waitlist | Via Oliver integration (passive) | AI waitlist backfill — actively fills gaps |
| Billing | Rule-based auto-charge from SOAP (not AI) | Agentic billing from SOAP — AI-driven |
| Risk scoring | None | Automated patient risk scoring engine |
| Intake | Digital forms via third-party integrations | Agentic pre-visit intake — AI collects and routes info |
| Audit trail | None | Agent audit log — every AI action logged and reviewable |
| Architecture | Three siloed AI features | Modular agentic framework — composable, orchestrated |
| Forecasting | None | AI-driven predictive forecasting |

> **Key quote:** "Shepherd has built AI features that live inside the SOAP. VPMA is building an AI operating system that acts on behalf of the practice. Shepherd's AI helps the vet document faster. VPMA's AI helps the practice run itself."

---

## Top 3 Strengths

1. **Auto charge capture from SOAP** — most praised feature; real-time invoice building; measurably reduces missed charges
2. **TranscribeAI** — genuinely differentiated; ambient not dictation; native, free with subscription
3. **Broad curated integration ecosystem** — 30+ integrations; IDEXX/Antech/Heska are deep two-way

---

## Top 3 Weaknesses

1. **Click-heavy fragmented UX** — excessive tab-switching; undermines 'workflow-first' positioning
2. **No agentic/autonomous capabilities** — all AI reactive and advisory; no autonomous follow-up, no proactive risk, no waitlist AI
3. **Post-update instability** — multi-hour outages; data loss events in clinical setting

---

## Key Quotes

> "The automatic charge capture has been a game-changer — we've seen a significant reduction in missed charges since switching." — Capterra

> "TranscribeAI is genuinely impressive — it listens and fills in the SOAP while I talk to the client. I don't change how I speak at all." — Shepherd.vet source

> "It feels like I'm navigating 5 different tabs just to complete one appointment." — Reddit r/veterinary

> "We had a 3-hour outage right after an update. Lost anesthesia records because the form didn't auto-save." — Capterra 2025

> "Shepherd Pay fees are noticeably higher than what we were paying with our previous processor." — Reddit
