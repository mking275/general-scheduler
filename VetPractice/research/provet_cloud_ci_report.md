# Provet Cloud (Nordhealth) — Competitive Intelligence Report
**Vendor:** Provet Cloud (by Nordhealth) | **Research Date:** June 2026 | **Source:** Competitive Research Agent

## Executive Summary
Provet Cloud (by Nordhealth, Helsinki) is a cloud-native, REST API-first veterinary practice management system targeting independent clinics, specialty hospitals, and enterprise veterinary groups across North America, Europe, and the Nordic region. Uses a tiered SaaS model (Core/Pro/Enterprise) emphasizing all-in-one functionality. In 2025, Provet launched its native "Clinical AI" suite (AI Scribe, AI Patient Summary, AI Discharge Instructions), making it one of the first PIMS to offer embedded generative AI at a transparent price point. As of mid-2026, serves **3,000+ practices globally** with ~150 US clinics, pursuing enterprise expansion after a December 2024 pilot with a 200+ location US veterinary group. Reviews average **~4.1/5 stars** (Capterra/GetApp).

## Pricing
| Plan | Per-Vet Fee | Platform Fee | Target |
|---|---|---|---|
| **Core** | $99/vet/mo | $249/mo | Single-site practices |
| **Pro** | $129/vet/mo | $299/mo | Multi-location practices |
| **Enterprise** | Custom | Custom | Large groups (200+ locations) |

**Key Notes:**
- Only vets charged per-seat; all other staff (techs, receptionists, managers) = **free**
- Part-time vet discount available (≤10 logins/month)
- **AI Scribe + Actions add-on**: $40/vet/mo (Core/Pro); Custom (Enterprise)
- **Provet Pay**: $0 upfront + revenue share; available all tiers
- Implementation: 8–12 weeks; **in-house data migration included all plans**
- Support: Core = Chat/Email; Pro = Chat/Email/Phone; Enterprise = Custom SLA (<2 min chat)

## Feature Scores

### S — Scheduling
| ID | Feature | Rating | Confidence | Notes |
|---|---|---|---|---|
| S01 | Appointment scheduling | ✅ | HIGH | ✅ all tiers |
| S02 | Multi-location support | ⚠️ | HIGH | ❌ Core, ✅ Pro+; Multi-Location Management gated to Pro |
| S03 | Room & resource management | ✅ | HIGH | Shift & resource views — clinicians, rooms, equipment side-by-side |
| S04 | Waitlist management | ⚠️ | MED | Basic native waitlist to fill gaps; not smart AI-powered backfill |
| S05 | Automated reminders | ✅ | HIGH | SMS/Email ✅ all tiers |
| S06 | Two-way client texting | ✅ | HIGH | Native two-way SMS/MMS ✅ all tiers |
| S07 | Online self-scheduling | ✅ | HIGH | Online Booking Portal ✅ all tiers; full control over types/slots/doctors |
| S08 | Boarding/kennel management | ✅ | HIGH | Boarding ✅ all tiers (Clinical Workflow section) |

### C — Clinical
| ID | Feature | Rating | Confidence | Notes |
|---|---|---|---|---|
| C01 | SOAP note creation | ✅ | HIGH | Medical Records ✅ all tiers; SOAP + narrative templates; Treatment Sheets |
| C02 | AI-assisted SOAP drafting | 💰 | HIGH | AI Scribe + Actions = $40/vet/mo add-on; dictation → SOAP + treatment detection |
| C03 | Pre-visit intake | ✅ | HIGH | Customizable Forms + eSignature/Consent Forms ✅ all tiers |
| C04 | Photo/imaging attachment | ✅ | HIGH | Imaging & PACS/DICOM ✅ all tiers |
| C05 | Vaccine & care protocol tracking | ✅ | HIGH | Vaccine Certificates + Health Plans ✅ all tiers |
| C06 | Prescription management | ✅ | MED | Prescription/dispensing workflow + label printing confirmed |
| C07 | Breed-specific alerts | ⚠️ | MED | No dedicated breed alert database; workaround via custom patient tags/flags |
| C08 | Patient risk scoring | ⚠️ | HIGH | Triage Board = ❌ Core, ✅ Pro+; Core has basic status flags only |
| C09 | Post-visit follow-up automation | ✅ | HIGH | Rule-based automated reminders for rechecks, vaccine boosters, wellness visits |
| C10 | Telemedicine | 🔌 | HIGH | No native video consult; 150+ integration partners |

### L — Laboratory
| ID | Feature | Rating | Confidence | Notes |
|---|---|---|---|---|
| L01 | IDEXX in-house analyzer | ✅ | HIGH | IDEXX VetLab Station via IDEXX InterLink Cloud Plug-In; ✅ all tiers |
| L02 | IDEXX Reference Lab | ✅ | HIGH | VetConnect PLUS two-way write-back; results auto-filed |
| L03 | Antech | ✅ | HIGH | Antech reference lab sync; ordering + result retrieval |
| L04 | Heska | ✅ | HIGH | Explicitly listed in pricing matrix; Lablink bridge |
| L05 | Vetscan/Abaxis | ✅ | HIGH | Explicitly listed in pricing matrix ("IDEXX, Heska, Abaxis, …") |
| L06 | DICOM/imaging | ✅ | HIGH | Imaging & PACS/DICOM ✅ all tiers |
| L07 | Critical value flags | ❓ | LOW | Results auto-file; configurable critical-value alert thresholds not explicitly documented |
| L08 | Auto-filing lab results | ✅ | HIGH | Two-way lab sync; results auto-attach to patient record |

### F — Financial
| ID | Feature | Rating | Confidence | Notes |
|---|---|---|---|---|
| F01 | Invoice generation | ✅ | HIGH | Client Invoicing & Billing ✅ all tiers; single-step finalization |
| F02 | Auto-invoice from SOAP | ✅ | HIGH | Auto-charge Capture ✅ all tiers; AI Scribe Actions also detects treatments → prompts billing |
| F03 | Card-present payments | 💰 | HIGH | Provet Pay: $0/mo + revenue share; Payment Terminal ✅ all tiers |
| F04 | Apple/Google Pay | ❓ | MED | Provet Pay supports "multiple payment methods" incl. contactless; specific wallet brands not confirmed |
| F05 | Payment plans/financing | ⚠️ | MED | Booking Deposits + Prepayments ✅ all tiers; true installment/financing plans not confirmed |
| F06 | Split-tender payments | ✅ | HIGH | "Paying multiple invoices in a single transaction" + refunds confirmed |
| F07 | End-of-day reconciliation | ✅ | HIGH | End of Day Report + Integrated Payment Reports ✅ all tiers |
| F08 | QuickBooks/Xero integration | 🔌 | HIGH | Via open REST API/webhooks only; no native certified QB or Xero connector |
| F09 | Pet insurance claims | ✅ | HIGH | "Send claims directly from the invoice and track statuses without re-keying" |
| F10 | Collections tracking | ⚠️ | MED | Credit Notes ✅ all tiers; AR tracking available; dedicated collections module not confirmed |

### I — Inventory
| ID | Feature | Rating | Confidence | Notes |
|---|---|---|---|---|
| I01 | Drug inventory tracking | ✅ | HIGH | Inventory Management ✅ all tiers |
| I02 | Controlled substance logging | ⚠️ | MED | Basic CS flagging native; full DEA-compliant digital logging requires VetSnap integration |
| I03 | Smart reorder/POs | ✅ | HIGH | Wholesaler Purchasing ✅ all tiers; MWI, NVS, Covetrus, VetCove confirmed |
| I04 | Prescription label printing | ✅ | HIGH | Confirmed in clinical dispensing workflow |
| I05 | Dispensing workflow | ✅ | HIGH | Integrated treatment/dispensing; charge capture tied to dispensed items |
| I06 | Lot & expiry tracking | ✅ | MED | Expiry alerts in inventory management; lot tracking implied by compliance reports |

### R — Reporting
| ID | Feature | Rating | Confidence | Notes |
|---|---|---|---|---|
| R01 | Revenue reports | ✅ | HIGH | Financial Reports + Integrated Payment Reports ✅ all tiers |
| R02 | Utilization reports | ✅ | HIGH | Practice Performance Reports + Clinic Operations Reports ✅ all tiers |
| R03 | Patient retention analytics | ✅ | HIGH | Patient Reports ✅ all tiers; iVET360 API integration adds advanced analytics |
| R04 | Custom report builder | ✅ | HIGH | Custom reports confirmed (BI, Finances, Performance, Stock categories); PDF/Excel/CSV + scheduled delivery |
| R05 | Multi-clinic dashboards | ⚠️ | HIGH | Full multi-location dashboard = Pro+ only; Core = single-site view |
| R06 | AI-driven insights | ❓ | MED | AI Patient Summary (clinical) free all tiers; AI predictive analytics/revenue forecasting not yet available |

### P — Platform
| ID | Feature | Rating | Confidence | Notes |
|---|---|---|---|---|
| P01 | Open API | ✅ | HIGH | Open REST API ✅ all tiers; OAuth 2.0 (Authorization Code + Client Credentials) |
| P02 | Payroll integration | ❌ | HIGH | No payroll module or payroll integration listed anywhere |
| P03 | Accounting integration | 🔌 | HIGH | Via REST API/webhooks; QuickBooks/Xero possible but no native certified connector |
| P04 | Supplier/GPO integration | ✅ | HIGH | Wholesaler Purchasing ✅ all tiers; MWI, NVS, Covetrus, VetCove |
| P05 | Data migration tools | ✅ | HIGH | In-house Data Migration + Implementation ✅ all tiers; migrates from Cornerstone, Avimark, Impromed |
| P06 | Mobile app | ✅ | HIGH | Provet Mobile App ✅ all tiers |
| P07 | Cloud-based | ✅ | HIGH | ✅ all tiers; AWS-hosted; 99.9% uptime |
| P08 | SSO | ✅ | HIGH | SSO ✅ all tiers (OAuth/Google SSO); SCIM provisioning = Enterprise only |

### A — Agentic AI
| ID | Feature | Rating | Confidence | Notes |
|---|---|---|---|---|
| A01 | AI SOAP drafting | 💰 | HIGH | AI Scribe + Actions = $40/vet/mo; dictation → SOAP; detects treatments → prompts invoice |
| A02 | Agentic pre-visit intake | ❌ | HIGH | Static customizable digital forms only; no AI-driven intelligent intake agent |
| A03 | Patient risk scoring (automated) | ❌ | HIGH | Manual Triage Board (Pro+ only); no AI risk scoring algorithm |
| A04 | Agentic follow-up | ❌ | HIGH | Rule-based automated reminders only; not AI-adaptive |
| A05 | AI waitlist backfill | ❌ | HIGH | In AI roadmap but not yet live as of mid-2026 |
| A06 | AI discharge instructions | 🆕 | HIGH | "AI generates personalized discharge summaries from clinical notes"; FREE all tiers; launched 2025 |
| A07 | AI patient history summary | 🆕 | HIGH | One-click patient history summary; FREE all tiers; launched 2025 |
| A08 | Predictive forecasting | ❌ | HIGH | In AI roadmap (stock control, billing AI); not yet available |
| A09 | Agent audit log | ❓ | MED | Compliance Reports confirmed (ISO 27001); AI-specific activity audit not confirmed |
| A10 | Modular AI architecture | 🆕 | HIGH | Clinical AI suite live (2025); active roadmap for scheduling, stock, billing AI |

## Score Summary
| Category | ✅ | ⚠️ | 🔌 | ❌ | 💰 | 🆕 | ❓ |
|---|---|---|---|---|---|---|---|
| Scheduling (8) | 6 | 2 | 0 | 0 | 0 | 0 | 0 |
| Clinical (10) | 6 | 2 | 1 | 0 | 1 | 0 | 0 |
| Laboratory (8) | 6 | 0 | 0 | 0 | 0 | 0 | 1 |
| Financial (10) | 5 | 2 | 2 | 0 | 1 | 0 | 1 |
| Inventory (6) | 5 | 1 | 0 | 0 | 0 | 0 | 0 |
| Reporting (6) | 4 | 1 | 0 | 0 | 0 | 0 | 1 |
| Platform (8) | 5 | 0 | 2 | 1 | 0 | 0 | 0 |
| AI/Agentic (10) | 0 | 0 | 0 | 4 | 1 | 3 | 1 |
| **TOTAL (60)** | **37** | **8** | **5** | **5** | **2** | **3** | **3** |

> **Key insight:** Provet has one of the strongest feature counts (37 ✅) but its AI story is mixed — 3 new features live and 4 on the roadmap, but none are agentic/autonomous.

## Top 3 Strengths
1. **All-in-One Platform + Best-in-Class Diagnostic Integrations** — Full workflow coverage with confirmed two-way integrations for IDEXX (VetLab Station, VetConnect PLUS), Antech, Heska, and Abaxis/Vetscan. PACS/DICOM standard on all tiers.
2. **Open REST API + Vendor Independence** — Not owned by IDEXX, Zoetis, or pharma. 150+ integration partners. Open API available all tiers. Reviews explicitly cite "not locked into anyone's ecosystem" as a key reason for choosing Provet.
3. **Transparent AI Pricing with Meaningful Free Tier** — AI Patient Summary and AI Discharge Instructions free on all tiers. AI Scribe + Actions ($40/vet/mo) is competitively priced. All AI native, ISO 27001 certified.

## Top 3 Weaknesses
1. **Steep Learning Curve** — Reddit and Capterra reviewers consistently flag complex templates, clinical workflows, and configuration. Migration from legacy (especially Impromed) described as "rough transition."
2. **Core Tier Feature Gaps** — Multi-Location Management, Triage Board, Referral Portal all gated to Pro+. Creates upsell pressure for growing practices.
3. **Performance Issues at Peak + Specific Integration Gaps** — Crashes during busy hours (Saturday mornings mentioned). DEA-compliant CS logging requires VetSnap third-party. Power BI integration deprecated June 2025.

## AI / Agentic Capabilities (Detailed)
### Current Clinical AI Suite (Launched 2025)
| Feature | Status | Cost | Capability |
|---|---|---|---|
| AI Scribe + Actions | 💰 Add-on | $40/vet/mo | Dictation → SOAP; detects treatments → prompts billing |
| AI Patient Summary | 🆕 Included | Free (all tiers) | One-click full patient history summary |
| AI Discharge Instructions | 🆕 Included | Free (all tiers) | Auto-generates personalized post-visit instructions |

**AI Scribe "Actions" — Revenue Capture Feature:** Beyond transcription, detects treatments mentioned in dictated notes and prompts clinician to add to invoice.

### AI Roadmap (Confirmed, Not Yet Released as of mid-2026)
- AI-assisted scheduling optimization
- AI stock/inventory management recommendations
- AI billing automation

### Architecture: Native, Privacy-First
- AI operates within existing Provet interface — no separate login
- ISO 27001 certified; EU-level safeguards; data never sold or repurposed
- AWS-hosted

## Key Review Quotes
> *"Moving from Impromed to Provet Cloud was a rough transition, but the modern interface is worth it once you get past the learning curve."* — Reddit r/veterinary

> *"The software can feel clunky at times — too many clicks to complete certain workflows. And we've had it crash during busy Saturday mornings."* — Reddit r/veterinary

> *"We chose Provet because it isn't owned by IDEXX or another diagnostic company. The open API means we're not locked into anyone's ecosystem."* — Capterra/GetApp reviewer

> *"Customer support is exceptional — they get back to you in under 2 minutes via live chat, and the implementation team actually understands veterinary workflows."* — Capterra/GetApp reviewer

## North America Market Context
| Metric | Value |
|---|---|
| Total global practices | 3,000+ |
| US clinics (Dec 2024) | ~150 |
| Enterprise pilot (Dec 2024) | 200+ location US vet group |
| iVET360 integration | Announced early 2026 |
| Parent company | Nordhealth (Helsinki, Finland) |
| Independence position | Not owned by IDEXX, Zoetis, or pharma |
| Key competitors cited | ezyVet, Cornerstone, AVImark, Shepherd |
