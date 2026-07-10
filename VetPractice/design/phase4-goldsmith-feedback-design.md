# VetAgent Phase 4 — Goldsmith Feedback Design Brief

**Date**: 2026-07-09
**Source**: Dr. Goldsmith feedback (pilot partner, 23 clinics; strategic ambition: multi-hundred-clinic operators → IDEXX exit)
**Foundation**: the Vera Program architecture (`~/ModelGarden/research/vera-architecture/`, completed 2026-07-08 — Programs #1–#10, "the schedule is the spine") + the Envelope Strategy board + spec 009.
**Purpose**: map each feedback item onto the Vera Program, name the deltas, and seed the next specs. Not a spec — the input to `speckit-discover` per item.

---

## F1 — Vera Voice: customer-facing voice interface

**User story**: A pet owner calls the clinic. Vera answers, schedules/reschedules the appointment, answers routine questions (hours, pre-visit prep), and — when the caller describes symptoms suggesting an emergency — routes immediately to the on-call vet or the nearest ER partner, staying on the line until handoff.

**Design shape**: *Voice is a channel, not a product* (Goldsmith's own framing, and correct). One Vera core (same KNOW/ADVISE/DECIDE, same autonomy gate, same Thoth memory) behind a **realtime voice gateway**:
- **Channels**: phone (Twilio Voice — extends the existing `sms_gateway.py` Twilio integration), web-widget voice, in-clinic kiosk, staff voice in exam rooms (later), WhatsApp voice notes (async).
- **Latency class is new**: sub-second turn-taking requires realtime speech models (Gemini Live API given the stack; local STT/TTS candidates via ModelGarden Program #8 evaluation on the DGX hardware — voice at 24/7-phone-line scale is where local inference economics bite first).
- **Emergency triage is routing, not diagnosis** (Expert Firewall, Program #7): protocol-driven question flow modeled on established veterinary nurse-triage standards; always errs toward escalation; every call logged + transcribed; explicit "Vera is not a veterinarian" disclosure. Needs: on-call rota (→ F3), ER-partner directory per clinic, poison-control routing.
- **Wedge order**: **after-hours first.** Lower risk than the daytime primary line, displaces the GuardianVets line item ($200–300/mo, already in our stack-cost model), and converts today's voicemail into booked appointments — the most measurable revenue Vera can generate. Daytime overflow second; primary-line answer third, earned like any verb.
- **Program mapping**: extends Program #3 (Multi-Channel) with a realtime tier; new spec seed **`010-vera-voice`**.
- **Compliance**: call-recording consent by state (two-party states), TCPA for outbound, emergency-disclaimer script. See R2 below.

## F2 — Procurement: real shopping, price-comparison ordering

**User story**: Vera notices vaccine stock will run out in 9 days, compares prices/availability across the clinic's distributors, builds the cart at the best total cost, and presents it for one-tap approval; she tracks delivery and updates inventory on receipt.

**Design shape**:
- Predictive reorder (usage-trend model — already sketched in the original VPMS research as "Predictive Inventory Agent") → **cross-supplier price comparison** → cart assembly → DECIDE gate → order placement → delivery tracking.
- **Sourcing ladder mirrors the data ladder**: Vetcove partnership (the integration report's #5) where granted; supplier APIs where public; **guided-operator mode** (the human API — Vera coaches a staff member through the distributor portal, or agentic browsing with the clinic's own account) for the long tail. Same pattern as FarmAgent input-ordering — this is a COS-platform verb, not a VetAgent one; build it once (Program #9 extraction).
- **Program mapping**: Program #9 (MCP integrations) + guided-operator pattern; spec seed **`011-vera-procurement`**.

## F3 — Worker & shift scheduling

**User story**: Vera drafts next month's rota across the clinic's staff — DVM and tech coverage ratios per shift, licensure constraints, on-call rotation, PTO, float coverage from sister clinics — and staff request swaps by texting her.

**Design shape**: This is **the spine thesis applied to staff instead of patients** — the Generalized Agentic Scheduling Engine (`agentic_scheduling_model.md`: Task × Resource × Time + constraint validation + agentic mutability) with a staffing domain pack:
- Constraints: licensure/skills (DVM vs tech vs assistant), coverage ratios by appointment load (demand-forecast from the patient schedule Vera already owns), labor rules (overtime, breaks), on-call/emergency rota (feeds F1's escalation), **float pools across clinics** (the first genuinely multi-clinic verb — and the first place the F6 hierarchy pays off).
- Swaps/absences conversationally (WhatsApp/SMS — Program #3), manager approves per the autonomy ladder.
- **Comes from COS-platform level as Matt specified**: coordinate with Vera Program #1/#2 and FarmAgent crew-scheduling — extract, don't fork (same rule as the 048 steel thread).
- **Program mapping**: Programs #1/#2 core; spec seed **`012-staff-scheduling`** (thin — mostly domain-pack + constraint config over the shared engine).

## F4 — Financial integrations + business advice

**User story**: Vera reconciles yesterday's invoices to Stripe and Xero overnight; the Monday briefing includes revenue per DVM, no-show cost, and one specific recommendation ("Thursday dental slots run 40% empty; here are three options").

**Design shape**:
- **Integrations**: Stripe + Xero (both scoped in the integration report: 2–3 wks + 3–5 days), payroll read (Gusto-class), via Program #9 MCP connectors, per-tenant credentials (Decision 9).
- **Advice layer**: `FinancialDashboard` canvas component (already in the Decision-7 component list) + advisory domain pack. Boundary discipline: *KNOW the numbers, ADVISE with cited sources, never DECIDE* — "not a CPA, not financial advice" is the same Expert Firewall shape as not-a-vet. Every assertion linked to evidence (the Abridge pattern, Decision 6).
- Benchmarking: within one operator's own group = clean (their data). Cross-customer benchmarks only with explicit consent, later.
- **Program mapping**: Programs #9 + #6; spec seed **`013-financial-copilot`**.

## F5 — Operational efficiency advice

**User story**: Weekly ops review from Vera: room utilization, appointment cycle times, no-show patterns, staff load balance — with counterfactual receipts ("if the two 15-min slots after dentals became buffer, Tuesday's 40-min average wait drops ~15 min — want to trial it for two weeks?").

**Design shape**: This is the **shadow-receipts machinery from spec 009 matured into a continuous-improvement loop** — observe → hypothesize → propose experiment → measure → report. Largely composition of existing parts: insight engine (009), briefings (Program #3), domain pack heuristics (#6), Confidence-to-Urgency matrix (risk register #1) so advice lands in the briefing rather than as interruptions. Spec seed **`014-ops-advisor`** — after 009's insight engine proves accuracy at the pilot.

## F6 — Enterprise hierarchy: the 400-clinic and 11,000-clinic operators

**User story**: A regional director of a 400-clinic group opens *her* Vera briefing: rollups across 32 clinics, exceptions flagged, policy compliance, staffing gaps; corporate sets autonomy policy once and clinics inherit it. At 11,000 clinics, the same structure federates across divisions and brands.

**Design shape** — the biggest structural delta:
- **Org-tree tenancy**: today's model is flat per-tenant RLS (Decision 9) and F007 tops out at the 6–50 "corporate group" archetype. Needed: `clinic → region → division → brand → enterprise` tree; policy inheritance with local override-within-bounds; rollup views; delegated administration; SSO/SCIM; enterprise audit.
- **Hierarchical Vera — the distinctive move**: a Chief of Staff *at every level of the org chart*. Clinic Vera runs the clinic; Regional Vera briefs the director from her clinics' Veras (exception-based, not firehose); Enterprise Vera briefs the COO. Vera-to-Vera rollup is a new interaction pattern → **promote to COS-platform** (`patterns/chief-of-staff/hierarchy.md`) — FarmAgent wants the same for multi-ranch operators.
- **Multi-PIMS reality**: a 400-clinic group runs a mixed estate (ezyVet + Cornerstone + Avimark + …). Rip-and-replace is impossible at that scale — **the envelope/orchestration architecture is the only viable enterprise motion**, which raises the `PimsAdapter` port (envelope board, Appendix C) from Phase-B option to enterprise prerequisite.
- **Program mapping**: extends Decision 9 + F007 + Program #10; spec seeds **`015-org-hierarchy`** and a COS-platform pattern extraction.
- **Sales gate**: nothing at this tier closes without SOC 2 (see R1).

---

## Recommended additions (not in Goldsmith's list)

| # | Recommendation | Why now |
|---|---|---|
| **R1** | **SOC 2 Type II program + enterprise security posture** (pen test, uptime SLA, DPA/subprocessor hygiene, SSO) | 12+ month lead time; gates every F6 conversation; start before the first enterprise meeting, not after |
| **R2** | **Comms-compliance layer** — TCPA consent management, 10DLC SMS registration, per-state call-recording consent, emergency-disclaimer scripts | Voice + SMS at scale is a regulatory surface; one class action erases the company |
| **R3** | **Voice reliability engineering** — SLOs, telephony failover to a human answering service, graceful degradation; the catastrophic failure is a *missed emergency call* | F1 puts Vera on the phone; five-nines expectations arrive with it |
| **R4** | **Policy-based autonomy administration** — corporate sets the verb ladder as *policy*, clinics inherit; unified audit console | The pilot's per-verb promotion UX doesn't scale past ~10 clinics; enterprise version of Program #7 |
| **R5** | **Diagnostics-utilization metric as a first-class product feature** | It's simultaneously the IDEXX shield, the acquisition pitch (Goldsmith's own exit thesis), and a genuine operator KPI — instrument from pilot day 1 |
| **R6** | **Bilingual voice (EN/ES) from the start of F1** | US clinic clientele; FarmAgent's locale machinery already exists (FR-12 in the asset engine, i18n in FA-Web) |
| **R7** | **Voice cost telemetry from day 1** (production stays cloud — per Matt 2026-07-09, the DGX Sparks are a *development resource*, not a production plan) | Track realtime-API cost per call/minute from the first pilot call so the voice pricing tier (R8) is set on data; ModelGarden remains the dev/eval bench for model selection, not a hosting strategy |
| **R8** | **Pricing architecture v2** — per-clinic flat + usage tier for voice minutes; enterprise tier with volume/policy features | Voice has real marginal cost; founder-pricing (50% of commercial) needs the commercial card defined |
| **R9** | **Insurance & wellness-plan operations** (Trupanion direct-pay from the integration report; wellness-plan billing) | Revenue infrastructure clinics ask for early; complements F4 |

## Sequencing recommendation

1. **Now (with pilot, wks 1–16)**: 009 (envelope onboarding) unchanged; **010 voice discovery** in parallel — after-hours answering demo at one Goldsmith clinic is the single highest-impact add to the pilot's Phase 3; R5 instrumentation from day 1; R1 SOC 2 kickoff (paperwork, not eng).
2. **Next (post-pilot, Q4)**: 012 staff scheduling (rides COS Program #1/#2 work), 013 financial copilot (Stripe+Xero are the two "must-haves" per the integration report), R2/R3 hardening as voice expands.
3. **Then (2027)**: 011 procurement (needs Vetcove partnership lead time), 014 ops advisor (needs insight-accuracy track record), 015 enterprise hierarchy (needs SOC 2 + multi-PIMS adapters) — timed to Goldsmith's operator-network introductions.

## The Vera-core / VetAgent split (2026-07-09 addendum)

**Rule of thumb: if a second vertical (Farm, Dentist, FBO/pilot school) would *copy* it, it's Vera-core; if a second vertical would *rewrite* it, it's a domain pack / vertical concern.**

| Concern | Vera-core (ModelGarden / Vera Program) | VetAgent (this repo) |
|---|---|---|
| Voice (F1) | Voice gateway, telephony (Twilio), turn-taking, realtime model selection, escalation *mechanism*, **after-hours answering as a job template** | Vet triage protocol content, ER-partner directory, on-call rota data, "not a veterinarian" scripts, state consent specifics |
| Procurement (F2) | Shopping/verb engine, cart+approval flow, guided-operator capability | Distributor accounts, Vetcove partnership, vet supply catalog semantics |
| Staff scheduling (F3) | Generalized scheduling engine + rostering job template | Licensure/coverage-ratio constraints, vet on-call rules |
| Financial (F4) | MCP connector framework, FinancialDashboard canvas, advisory firewall mechanism | Vet practice KPIs (revenue/DVM, ARPP), Xero/Stripe tenant config |
| Ops advice (F5) | Insight engine, counterfactual-receipt machinery, experiment loop | Clinic-operations heuristics (rooms, cycle times) |
| Hierarchy (F6) | Org-tree tenancy, policy inheritance, hierarchical-Vera pattern | Vet group archetypes, PIMS-estate adapters (ezyVet first) |

This brief's F1–F5 therefore **merge into Vera Program #2 (VetAgent Convergence)** with the core halves feeding Programs #1/#3/#9; F6 splits between Program #10 (infra) and a new COS-platform pattern (hierarchical COS). The vertical halves stay here as domain packs + config + adapters.

## Coordination requirements

- **Extract, don't fork** (three places): staff scheduling ← Vera Program #1/#2; guided-operator/procurement ← COS-platform pattern; Vera-hierarchy ← new COS-platform pattern.
- The Vera Program roadmap's **Phase 1b (VetAgent Convergence)** is where F1–F5 land; F6 belongs in its Phase 3 (SCALE). This brief should be read alongside `~/ModelGarden/research/vera-architecture/07-gap-analysis-roadmap.md` and `08-uber-speckit-jobs.md`.
- Everything client-facing stays inside the Expert Firewall: Vera routes emergencies, cites sources, and never diagnoses, prescribes, or renders financial/legal opinions — at any autonomy level, on any channel.
