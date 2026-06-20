# VPMA Competitive Research Plan — v2
## Feature Matrix + Stack Consolidation Business Case

**Purpose**: Build a competitor feature matrix AND a business case showing VPMA replaces the entire vet practice software stack  
**Date**: 2026-06-19  
**Strategic Frame**: "Stop paying for 6 systems. Run your whole practice on one."

---

## The Core Argument

A typical vet practice today pays for:

| Tool | Purpose | Typical Cost |
|---|---|---|
| Cornerstone / Avimark | Practice management | $200–500/mo |
| PetDesk / Petvisor | Client comms & texting | $200–400/mo |
| Airvet / GuardianVets | Telemedicine | $150–300/mo |
| VetSuccess / custom | Analytics & reporting | $200–500/mo |
| Cubex / Impromed Inventory | Drug inventory | $100–300/mo |
| Gusto / ADP | Payroll & HR | $150–300/mo |
| **TOTAL** | **6 systems, 6 logins, 6 bills** | **$1,000–2,300/mo** |

VPMA + MODs covers all of it for $249–599/mo base + modular add-ons.  
**That's the business case.** The matrix proves it feature-by-feature.

---

## Research Tracks

### Track A — PMS Competitors (feature comparison)
Who does scheduling, records, labs, billing better?

**Tier 1 (deep — all 60 features):**
1. Cornerstone (IDEXX)
2. Avimark (Henry Schein)
3. ezyVet (IDEXX)
4. Shepherd ← closest AI competitor, gets separate deep-dive
5. Provet Cloud

**Tier 2 (summary — top 30 features):**
6. Covetrus Pulse
7. Digitail
8. Vetspire
9. DaySmart Vet

### Track B — Companion Tools (stack consolidation research)
What software do practices use *alongside* their PMS? What does each cost?

| Category | Tools to Research | VPMA MOD Replacement |
|---|---|---|
| Client comms / texting | PetDesk, Petvisor, Vet2Pet, VitusVet | MOD-COM |
| Telemedicine | Airvet, GuardianVets, WhiskerDocs | MOD-TEL |
| Analytics & BI | VetSuccess (Covetrus), Practice Insight | MOD-ANL |
| Inventory / pharmacy | Covetrus Inventory, Cubex, Vetcove | MOD-INV |
| Staff & HR / payroll | Gusto, ADP, Paychex (vet practice usage) | MOD-STF |
| Marketing & reputation | VetMatrix, Podium, Birdeye (vet) | MOD-MAR |

For each tool: pricing (monthly), key features, contract terms, integration pain.

### Track C — Shepherd Deep-Dive (separate teardown doc)
Shepherd is the closest AI competitor. Founded by vets. Has:
- TranscribeAI for SOAP note dictation
- Built-in diagnostic assistance
- Modern cloud UX

Research: exactly where they're ahead, where they're behind, their pricing, their G2 positioning, user reviews, what vets say they're missing.

---

## Feature Taxonomy (60 features, 8 categories)

### 🗓️ S — Scheduling & Practice Management
| ID | Feature | Replaces |
|---|---|---|
| S01 | Appointment scheduling (calendar) | Core PMS |
| S02 | Multi-location / multi-clinic support | Core PMS |
| S03 | Room & resource management | Core PMS |
| S04 | Waitlist management | Core PMS |
| S05 | Automated appointment reminders | PetDesk / Petvisor |
| S06 | Two-way client texting | PetDesk / Petvisor |
| S07 | Online self-scheduling (client) | PetDesk / Petvisor |
| S08 | Boarding / kennel management | Core PMS |

### 🐾 C — Clinical Records
| ID | Feature | Replaces |
|---|---|---|
| C01 | SOAP note creation | Core PMS |
| C02 | AI-assisted SOAP drafting | Shepherd / add-ons |
| C03 | Pre-visit intake / symptom collection | PetDesk |
| C04 | Photo / imaging attachment | Core PMS |
| C05 | Vaccine & care protocol tracking | Core PMS |
| C06 | Prescription management | Core PMS |
| C07 | Breed-specific clinical alerts | None (VPMA unique) |
| C08 | Patient risk scoring | None (VPMA unique) |
| C09 | Post-visit follow-up automation | PetDesk |
| C10 | Telemedicine / video consults | Airvet / GuardianVets |

### 🔬 L — Lab & Diagnostics
| ID | Feature | Replaces |
|---|---|---|
| L01 | IDEXX in-house analyzer integration | IDEXX native |
| L02 | IDEXX Reference Lab integration | IDEXX native |
| L03 | Antech integration | Antech portal |
| L04 | Heska integration | Heska portal |
| L05 | Vetscan / Abaxis integration | Vetscan portal |
| L06 | DICOM / imaging integration | Separate PACS |
| L07 | Critical value flags & alerts | Manual |
| L08 | Auto-filing lab results to patient record | Manual |

### 💰 F — Financial & Billing
| ID | Feature | Replaces |
|---|---|---|
| F01 | Invoice generation | Core PMS |
| F02 | Auto-invoice from signed SOAP notes | None (VPMA MOD-FIN) |
| F03 | Card-present payments (terminal) | Stripe Terminal / Square |
| F04 | Apple Pay / Google Pay | Stripe / Square |
| F05 | Payment plans / financing (CareCredit) | CareCredit portal |
| F06 | Split-tender payments | POS system |
| F07 | End-of-day reconciliation | Manual / QuickBooks |
| F08 | QuickBooks / Xero integration | Direct |
| F09 | Pet insurance claims | Manual / insurance portal |
| F10 | Outstanding balance / collections | Manual / collections tool |

### 💊 I — Inventory & Pharmacy
| ID | Feature | Replaces |
|---|---|---|
| I01 | Drug inventory tracking | Covetrus / Cubex |
| I02 | Controlled substance logging (DEA) | Paper / Cubex |
| I03 | Smart reorder / purchase orders | Manual |
| I04 | Prescription label printing | Label printer |
| I05 | Dispensing workflow | Manual |
| I06 | Lot & expiry tracking | Spreadsheet |

### 📊 R — Reporting & Analytics
| ID | Feature | Replaces |
|---|---|---|
| R01 | Revenue & financial reports | Core PMS / QuickBooks |
| R02 | Appointment utilization | Core PMS |
| R03 | Patient retention / churn analysis | VetSuccess |
| R04 | Custom report builder | Tableau / VetSuccess |
| R05 | Regional / multi-clinic dashboards | VetSuccess / custom |
| R06 | AI-driven practice insights | None (VPMA MOD-ANL) |

### 🔌 P — Platform & Integrations
| ID | Feature | Replaces |
|---|---|---|
| P01 | Open API / developer access | — |
| P02 | Payroll export / integration | Gusto / ADP |
| P03 | Accounting software integration | QuickBooks |
| P04 | Supplier / GPO integration | Covetrus / MWI |
| P05 | Data migration from legacy systems | Migration vendor |
| P06 | Mobile app (iOS/Android) | — |
| P07 | Cloud-based (no local server) | — |
| P08 | SSO / enterprise auth | — |

### 🤖 A — Agentic AI (VPMA differentiator)
| ID | Feature | Replaces |
|---|---|---|
| A01 | AI SOAP note drafting | Shepherd / CoVet AI scribe |
| A02 | Agentic pre-visit intake (zero staff) | PetDesk + staff time |
| A03 | Automated patient risk scoring | None |
| A04 | Agentic follow-up (zero staff) | PetDesk + staff time |
| A05 | AI waitlist backfill | None |
| A06 | Agentic reminder pipeline | PetDesk |
| A07 | Predictive capacity forecasting | VetSuccess |
| A08 | Agentic billing from SOAP (MOD-FIN) | Manual billing workflow |
| A09 | Verbose agent audit log | None |
| A10 | Modular AI add-on architecture | None |

---

## Rating Scale

| Symbol | Meaning |
|---|---|
| ✅ | Full — fully featured, well-reviewed |
| ⚠️ | Partial — limited, add-on cost, or poor UX |
| 🔌 | Via integration — third-party connector required |
| ❌ | Not available |
| 🆕 | Recently launched / beta |
| 💰 | Paid add-on — costs extra beyond base |

---

## Research Methodology

### Per Competitor (Tier 1 — deep)
For each feature, research agent must:
1. Find direct evidence (feature page, help doc, YouTube demo, G2 feature list)
2. Assign rating with confidence (high/medium/low)
3. Note source URL
4. Note any pricing implications (included vs. add-on)
5. Note notable user complaints (from G2/Capterra reviews)

**Sources to hit per competitor:**
- Official feature/product pages
- Help center / docs
- Pricing page
- G2 feature ratings + top 10 reviews
- Capterra feature checklist + top 10 reviews
- YouTube: search "{competitor name} demo" — first 2 results
- Reddit r/veterinary mentions
- dvm360.com review if exists

### Per Companion Tool (Track B)
- Pricing page (monthly cost, tiers)
- Top 3 features
- Contract terms (annual lock-in?)
- Integration with which PMS systems
- User review pain points (what's missing)

---

## Output Deliverables

### D1 — `VetPractice/vpma_competitor_matrix.md`
Master 60-row × 10-competitor markdown table with all ratings + source notes

### D2 — `VetPractice/vpma_stack_costs.md`
Companion tools cost analysis: typical practice stack cost breakdown, VPMA replacement cost, savings calculation

### D3 — `VetPractice/vpma_shepherd_teardown.md`
Shepherd deep-dive: feature-by-feature, pricing, AI positioning, where VPMA wins, where Shepherd leads

### D4 — `VetPractice/vpma_competitive_summary.md`
Executive summary: VPMA's top 5 unique advantages, top 3 gaps, recommended marketing angles

### D5 — `VetPractice/vpma_feature_gaps.md` *(internal only, not in marketing materials)*
Honest gap analysis: what competitors have that VPMA doesn't, prioritized by market impact

### D6 — `marketing/comparison.html`
Designed marketing page (see below)

---

## Marketing Page Design Brief (`comparison.html`)

**URL**: `/marketing/comparison.html` (static HTML, no framework needed)

**Sections:**

### Hero
- Headline: "One platform. Your entire practice."
- Subhead: "Replace 6 subscriptions with one intelligent system."
- CTA: "See the full comparison ↓"
- Visual: animated stack of competitor logos fading into VPMA logo

### The Stack Problem
- Visual: typical practice "software stack" with logos + costs ($1,000–2,300/mo total)
- Arrow → VPMA stack ($249 base + MODs shown as building blocks)
- Animated total cost calculator: "Your practice is currently paying ~$X/mo for {N} systems"

### Feature Comparison Matrix
- Full 60-row table, filterable by category
- Columns: VPMA | Cornerstone | ezyVet | Shepherd | Avimark | Provet Cloud
- VPMA column highlighted (indigo)
- Rows where VPMA is ✅ and all others ❌ → highlighted gold "VPMA Advantage" row
- Sticky header + zebra striping

### Agentic AI Section
- Full-width dark section
- "Every legacy system records. VPMA acts."
- 10 agentic features listed with animations
- Quote: competitor comparison showing all ❌ in the AI rows

### Shepherd Comparison Callout
- Side-by-side: Shepherd vs VPMA in AI features specifically
- "The closest competitor to VPMA in AI — and here's how they compare"

### Stack Savings Calculator
- Interactive: checkboxes for which tools they currently use
- Running total of current monthly spend
- VPMA equivalent shown below
- Annual savings highlighted

### CTA
- "Replace your stack" → demo request
- "See pricing" → pricing page

**Design**: Dark theme, indigo/violet accent (#6C63FF), premium glassmorphism cards, Outfit/Inter font, smooth scroll animations, fully responsive.

---

## Execution Plan

### Agents to Launch (parallel)
1. **Agent-Cornerstone** — Tier 1 deep research
2. **Agent-Avimark** — Tier 1 deep research
3. **Agent-ezyVet** — Tier 1 deep research
4. **Agent-Shepherd** — Tier 1 + deep-dive teardown (combined)
5. **Agent-ProvetCloud** — Tier 1 deep research
6. **Agent-Tier2** — All 4 Tier 2 competitors (summary depth)
7. **Agent-CompanionTools** — Track B: pricing + features of 6 companion tool categories

**7 parallel research agents → merge → synthesize → build HTML**
