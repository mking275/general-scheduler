# IDEXX Cornerstone — Competitive Intelligence Report
**Research Date:** June 2026 | Source: Competitive Research Agent

## Executive Summary
IDEXX Cornerstone is the market-leading **on-premise, server-based** veterinary practice management software, with decades of installed-base momentum among multi-doctor, specialty, and corporate hospital groups. Its defining strength is **unmatched native integration with IDEXX's own diagnostic ecosystem** (in-house analyzers, VetConnect PLUS reference lab, IDEXX-PACS imaging) — an ecosystem moat no competitor replicates. However, Cornerstone's architecture is fundamentally a legacy Windows application: it lacks cloud-native remote access, has no built-in AI, does not offer online self-scheduling natively, and relies on an expanding constellation of add-on modules (Vello, IDEXX Integrated Payments, IDEXX-PACS) for features modern cloud-native competitors bake in at no additional cost.

## Pricing
| Item | Detail |
|---|---|
| Base subscription | Est. $420–$549/month (third-party estimates) |
| Pricing model | Per-user tier; custom-quoted |
| Contract terms | Multi-year initial term |
| Additional costs | Implementation fees, on-site server hardware, Vello (separate), IDEXX-PACS (separate) |
| Target segment | Multi-doctor GP, specialty/referral, corporate groups (3+ DVM) |

## Feature Scores

### S — Scheduling
| ID | Feature | Rating | Confidence | Notes |
|---|---|---|---|---|
| S01 | Appointment scheduling | ✅ | HIGH | Robust scheduler with whiteboard views |
| S02 | Multi-location support | ✅ | HIGH | MLSD mode; consolidated reporting |
| S03 | Room & resource management | ⚠️ | MED | No visual drag-drop room board |
| S04 | Waitlist management | ⚠️ | MED | "Want List" / scheduling queue; manual |
| S05 | Automated reminders | ✅ | HIGH | Via Vello (paid module) — SMS/email |
| S06 | Two-way client texting | 🔌 | HIGH | Vello or PetDesk; not native core |
| S07 | Online self-scheduling | 🔌 | HIGH | Vetstoria or Vello; no native portal |
| S08 | Boarding/kennel management | ⚠️ | MED | Optional module; less robust than dedicated tools |

### C — Clinical
| ID | Feature | Rating | Confidence | Notes |
|---|---|---|---|---|
| C01 | SOAP note creation | ✅ | HIGH | Full EMR, customizable SOAP templates |
| C02 | AI-assisted SOAP drafting | 🔌 | HIGH | VetGeni/Scribenote only; not native |
| C03 | Pre-visit intake | 🔌 | MED | Vello digital forms; not core |
| C04 | Photo/imaging attachment | ✅ | HIGH | Native photos + IDEXX-PACS for DICOM |
| C05 | Vaccine & care protocol tracking | ✅ | HIGH | Vaccine tag defaults, series reminders |
| C06 | Prescription management | ✅ | HIGH | Full Rx with label printing, DEA tracking |
| C07 | Breed-specific alerts | ⚠️ | MED | Manual alert flags; no automated logic |
| C08 | Patient risk scoring | ⚠️ | MED | IDEXX DecisionIQ for lab-based risk only |
| C09 | Post-visit follow-up automation | 🔌 | HIGH | Vello; not core |
| C10 | Telemedicine | 🔌 | HIGH | Anipanion, TeleVet; not native |

### L — Laboratory
| ID | Feature | Rating | Confidence | Notes |
|---|---|---|---|---|
| L01 | IDEXX in-house analyzer | ✅ | HIGH | Deep native via VetConnect PLUS — top differentiator |
| L02 | IDEXX Reference Lab | ✅ | HIGH | VetConnect PLUS unified |
| L03 | Antech integration | ✅ | HIGH | Online ordering, auto charge capture, auto download |
| L04 | Heska integration | ✅ | MED | Direct result download confirmed |
| L05 | Vetscan/Abaxis integration | ✅ | MED | USB result download confirmed |
| L06 | DICOM/imaging | ✅ | HIGH | IDEXX-PACS / Web PACS (paid module) |
| L07 | Critical value flags | ⚠️ | MED | DecisionIQ interpretive flags; no standalone alerts |
| L08 | Auto-filing lab results | ✅ | HIGH | Auto-file via VetConnect PLUS |

### F — Financial
| ID | Feature | Rating | Confidence | Notes |
|---|---|---|---|---|
| F01 | Invoice generation | ✅ | HIGH | Core feature |
| F02 | Auto-invoice from SOAP | ⚠️ | MED | PVL → invoice tightly linked but not one-click |
| F03 | Card-present payments | ✅ | HIGH | IDEXX Integrated Payments via Clover/Fiserv |
| F04 | Apple/Google Pay | ✅ | HIGH | Clover terminals support NFC/contactless |
| F05 | Payment plans/financing | 🔌 | HIGH | CareCredit integration; no native installments |
| F06 | Split-tender payments | ✅ | HIGH | Multi-payment-type workflow documented |
| F07 | End-of-day reconciliation | ✅ | HIGH | Daily Deposit Report, Audit Trail |
| F08 | QuickBooks/Xero integration | ⚠️ | HIGH | QB Desktop file-based only; no QB Online API; no Xero |
| F09 | Pet insurance claims | ⚠️ | HIGH | Trupanion EDO in-practice; Claim submission still in insurer portal |
| F10 | Collections tracking | ⚠️ | MED | AR reporting; no dedicated collections workflow |

### I — Inventory
| ID | Feature | Rating | Confidence | Notes |
|---|---|---|---|---|
| I01 | Drug inventory tracking | ✅ | HIGH | QOH, vendor management, reorder points |
| I02 | Controlled substance logging | ✅ | HIGH | ASAP 4.2 export, DEA tracking |
| I03 | Smart reorder/POs | ✅ | MED | Purchasing Work List, Want List, automated POs |
| I04 | Prescription label printing | ✅ | HIGH | Full label with NDC, client address, DEA# |
| I05 | Dispensing workflow | ✅ | HIGH | Integrated with PVL |
| I06 | Lot & expiry tracking | ✅ | HIGH | Per-item lot/expiry on receipt and dispensing |

### R — Reporting
| ID | Feature | Rating | Confidence | Notes |
|---|---|---|---|---|
| R01 | Revenue reports | ✅ | HIGH | EOD/EOM/EOY financial reports |
| R02 | Utilization reports | ✅ | MED | Practice Explorer module |
| R03 | Patient retention analytics | ⚠️ | MED | Client/Patient Report Builder; no pre-built dashboard |
| R04 | Custom report builder | ✅ | HIGH | Practice Explorer + Report Builder |
| R05 | Multi-clinic dashboards | ⚠️ | MED | MLSD consolidated reporting; no real-time web dash |
| R06 | AI-driven insights | ❌ | HIGH | None; DecisionIQ = diagnostic only |

### P — Platform
| ID | Feature | Rating | Confidence | Notes |
|---|---|---|---|---|
| P01 | Open API | ⚠️ | HIGH | IDEXX Data Services API (partner-only, not public) |
| P02 | Payroll integration | ❌ | HIGH | None; manual export to ADP/Paychex |
| P03 | Accounting integration | ⚠️ | HIGH | QB Desktop file-based only |
| P04 | Supplier/GPO integration | 🔌 | MED | Inventory Ally; no universal marketplace |
| P05 | Data migration tools | ⚠️ | MED | IDEXX-supported migration; not self-service |
| P06 | Mobile app | ⚠️ | MED | Vello pet owner app; no staff mobile app |
| P07 | Cloud-based | ❌ | HIGH | On-premise Windows server only |
| P08 | SSO | ⚠️ | MED | MyIDEXX SSO for web services; not core desktop |

### A — Agentic AI
| ID | Feature | Rating | Notes |
|---|---|---|---|
| A01 | AI SOAP drafting | ❌ | Third-party only (VetGeni, Scribenote) |
| A02 | Agentic pre-visit intake | ❌ | None |
| A03 | Patient risk scoring (automated) | ❌ | None |
| A04 | Agentic follow-up | ❌ | None |
| A05 | AI waitlist backfill | ❌ | None |
| A06 | Agentic reminder pipeline | ❌ | Rule-based Vello reminders only |
| A07 | Predictive forecasting | ❌ | None |
| A08 | Agentic billing from SOAP | ❌ | None |
| A09 | Agent audit log | ❌ | None |
| A10 | Modular AI architecture | ❌ | None |

## Score Summary
| Category | ✅ | ⚠️ | 🔌 | ❌ |
|---|---|---|---|---|
| Scheduling (8) | 2 | 3 | 3 | 0 |
| Clinical (10) | 3 | 3 | 4 | 0 |
| Laboratory (8) | 6 | 2 | 0 | 0 |
| Financial (10) | 4 | 4 | 2 | 0 |
| Inventory (6) | 6 | 0 | 0 | 0 |
| Reporting (6) | 3 | 2 | 0 | 1 |
| Platform (8) | 0 | 4 | 2 | 2 |
| AI/Agentic (10) | 0 | 0 | 0 | **10** |
| **TOTAL (60)** | **24** | **18** | **11** | **13** |

## Top 3 Strengths
1. **IDEXX Diagnostic Ecosystem Lock-in** — Unmatched native integration with IDEXX analyzers and reference labs via VetConnect PLUS
2. **Inventory & Controlled Substance Management** — Mature, fully featured: lot/expiry, reorder, ASAP 4.2 DEA export
3. **Clinical Record Depth & Customization** — Decades of EMR development; highly configurable for power users

## Top 3 Weaknesses
1. **Legacy On-Premise Architecture** — Windows server only, no cloud, VPN-only remote access, hardware costs
2. **Zero Native AI** — All 10 agentic features absent; third-party AI requires additional subscriptions and creates fragmented workflow
3. **Dated UX & Steep Learning Curve** — Keyboard-heavy, right-click menus, slow during peak hours; new staff struggle

## Key Review Quotes
> *"The UI is horrible to navigate. Lots of confusing keystrokes and right-click menus."* — Capterra

> *"The integration with IDEXX lab equipment is the best in the industry. Results come right into the patient record."* — G2

> *"Cornerstone freezes during busy times. Our server goes down and the whole clinic stops."* — Software Advice

> *"Switching from Cornerstone to ezyVet was painful but our new grads are so much happier with the interface."* — Reddit r/VetTech
