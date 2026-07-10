# Vera Pilot Program — Proposal for the Goldsmith Veterinary Group

**Prepared for:** Dr. Jay Goldsmith
**Prepared by:** VetAgent · Matt King
**Date:** July 9, 2026
**Validity:** 30 days

---

## Executive Summary

You keep ezyVet. Nothing migrates, no staff retraining, no cutover, no disruption to any of your 23 clinics.

What your group doesn't have today is a Chief of Staff: someone who reads every record, watches every schedule, notices what needs noticing, and handles the administrative follow-through — without a $100K+ salary per location. That is what Vera is. She is an AI Chief of Staff who learns your practices from their own records and earns each responsibility with evidence before she's given it.

We propose a three-phase pilot over approximately 16 weeks:

| Phase | What happens | Duration |
|---|---|---|
| **1 — Data & Ingestion** | Your group requests copies of its clinic data from ezyVet (a standard contractual right — we draft the letter). Vera ingests it and builds a working model of each practice. | Weeks 1–3 |
| **2 — Design Loops** | Three two-week design cycles with you and your staff, working entirely on your real data. You shape what Vera notices, how she briefs, and what she's allowed to touch. | Weeks 4–9 |
| **3 — Side-by-Side** | Vera runs live alongside ezyVet at one clinic you choose — expandable to three under the same flat fee. ezyVet remains the system of record throughout. We measure results weekly against criteria we set together. | Weeks 10–16 |

At the end: a joint go/no-go against the numbers, and a decision about the rest of the group. You can stop at any phase boundary and keep everything you've learned, including your data-quality reports.

---

## What Vera Is — and Is Not

Vera operates on a strict three-layer principle:

| Layer | Who | What it means in your clinics |
|---|---|---|
| **KNOW** | Vera | She reads and remembers everything in the practice record — patients, schedules, histories, patterns. |
| **ADVISE** | Vera | She briefs, flags, drafts, and proposes — with her reasoning shown. |
| **DECIDE** | Your team | Every clinical and financial action is approved by your people. Always. |

Vera is not a veterinarian and not a lawyer. She cannot prescribe, diagnose, or render legal opinions — this is architecture, not policy: those actions do not exist in her capability set at any permission level. Every action she does take is logged and auditable.

---

## Phase 1 — Data & Ingestion (Weeks 1–3)

**The mechanism.** Your ezyVet agreement (One IDEXX Master Terms, ezyVet Offering Specific Terms §5) entitles you to copies of your data on ten business days' written request, delivered by drive or file transfer. We provide the request letter for your signature; ezyVet does the rest. No integration, no IT project on your side.

**What we do with it.** Vera ingests each clinic's data and builds its practice model: providers, patients, appointment patterns, scheduling history, communication records. Her extraction pipeline reads the standard export formats directly.

**What you get, even if we stop here:**
- A **Data Quality Report** per clinic — duplicates, gaps, inconsistencies, records that need attention. Most groups have never seen this view of their own data.
- A complete, clinic-owned backup of your group's records — which your ezyVet terms (§6.3) make your responsibility to maintain, and which most practices don't have.

**Our data commitments (contractual):**

| Commitment | Terms |
|---|---|
| Ownership | Your data remains yours, entirely. |
| Security | Encrypted in transit and at rest; access logged; US-based processing. |
| Use | Used solely to deliver this pilot. We do not train foundation models on your data. |
| Subprocessors | Disclosed in full (cloud infrastructure, document AI, messaging), each under a data processing agreement. |
| Deletion | Full deletion within 30 days of your written request, at any time, no questions. |

---

## Phase 2 — Design Loops (Weeks 4–9)

Three two-week cycles, each ending in a working session. This is product design on your real operations, not a demo environment.

**Loop 1 — The Unveiling.** Vera presents what she's learned: each pilot-candidate clinic reflected back — schedules, patterns, and a first set of observations drawn strictly from the record. Your staff correct her; corrections become configuration.

**Loop 2 — The Briefing.** We design the morning briefing with the people who'd read it: what a front desk lead needs at 7:45am vs. what you need across 23 clinics. Vera produces real briefings from real weeks; your team marks up every line.

**Loop 3 — The Rules.** Your team decides Vera's permission ladder, verb by verb: what she may only *flag*, what she may *draft for one-click approval*, and what routine items she may *handle and report*. Nothing defaults to autonomous; everything starts at "advise."

**Staff involvement:** roughly six hours total across 2–3 clinics — front desk, technicians, and practice managers. Their answers to questions like "what would you never let an AI touch?" become hard boundaries in Vera's configuration.

**Deliverables:** a configured Vera instance per pilot-candidate clinic; an accuracy scorecard (every Vera observation verified against the record by your staff — we track the hit rate and publish it to you); the agreed permission ladder and briefing formats.

---

## Phase 3 — Side-by-Side (Weeks 10–16)

One clinic to start, chosen by you — expandable to as many as three under the same flat pilot fee. ezyVet runs exactly as it does today and remains the system of record for everything. Vera works alongside:

- **Morning briefing** to the clinic lead: today's schedule risks, patients needing attention, unfinished follow-through from yesterday.
- **No-show and gap watch:** flagged in advance, with waitlist candidates identified for staff to contact — or, if your team has promoted that verb, drafted outreach ready for one-click approval.
- **Follow-up drafts:** discharge and follow-up communications drafted from the visit record for staff review and approval.
- **Counterfactual receipts:** each week, Vera reports what she saw and what she would have done — so you can judge her performance even on responsibilities she hasn't been given yet.

**Measurement.** Final metrics are set jointly in Loop 3. Our proposed starting set:

| Metric | Baseline source | Target direction |
|---|---|---|
| Cancellation slots refilled | Trailing 90 days from your own data | Up |
| Staff hours on cross-system admin | Staff time sampling, week 10 | Down |
| After-hours charting time (DVMs) | Self-reported, week 10 | Down |
| Vera observation accuracy | Staff verification | ≥ agreed threshold |
| Client response latency | ezyVet comm records | Down |
| Staff sentiment | Pulse survey, weeks 10 and 16 | Up |

You receive a one-page scorecard weekly.

**Error policy.** Any trust-relevant error — a wrong draft sent, a misidentified patient, an incorrect flag acted on — triggers an immediate full stop of the affected capability, a written post-mortem to you within 48 hours, and re-enablement only with your sign-off.

---

## What We Ask of You

| # | Item | When |
|---|---|---|
| 1 | Sign the data-request letter (we draft it) | Week 1 |
| 2 | Name a pilot champion (typically a practice manager) as our working contact | Week 1 |
| 3 | Staff interview access — ~6 hours total across 2–3 clinics | Weeks 4–9 |
| 4 | Select the side-by-side clinic(s) — up to 3 | Week 8 |
| 5 | 48-hour turnaround on design-loop feedback | Weeks 4–9 |
| 6 | Weekly 30-minute scorecard review | Weeks 10–16 |

---

## Investment

*Indicative terms — final commercial terms in the pilot agreement.*

| Item | Terms |
|---|---|
| Phases 1–2 (data, design loops, all deliverables) | **No charge.** We are investing in getting this right with your group. Your data-quality reports and backups are yours regardless of outcome. |
| Phase 3 (side-by-side) | **$895/month flat, covering up to 3 clinics.** Month-to-month, cancel anytime. |
| Group rollout (on a joint "go") | **Founder pricing: estimated $500–650 per clinic per month** — set at **50% of commercial pricing**, which we determine jointly during this project. Flat per-clinic, never per-user. Priced against the administrative tooling and labor it displaces, not against your PIMS. |

No long-term commitment is requested or implied by this pilot.

---

## Timeline Summary

- **Weeks 1–3 — Phase 1:** data request → delivery → ingestion → Data Quality Reports
- **Weeks 4–9 — Phase 2:** three design loops (Unveiling → Briefing → Rules)
- **Week 8:** side-by-side clinic(s) selected
- **Weeks 10–16 — Phase 3:** live side-by-side, weekly scorecards
- **Week 16:** joint go/no-go review against agreed metrics

---

## Next Steps

1. A 30-minute call to walk this document and adjust scope.
2. Pilot agreement + data-request letter to you for signature in July — the letter starts ezyVet's ten-business-day delivery clock.
3. **Kickoff targeted for the first week of August.**

We're ready to start on signature.

**Matt King** · VetAgent · mking275@gmail.com
