# Marketing Brief: Vera After-Hours — Your Phone, Always Answered

**Feature**: 010-vera-voice (Vera Voice — after-hours line, cycles 3a/3b)
**Stage**: Stage 2 — Implementation (demo-grade, pilot committed)
**Generated**: 2026-07-10
**Source**: speckit-marketing — compiled from the 010 speckit lifecycle artifacts (discover / spec / plan / tasks Marketing Output sections + marketing-notes.md)
**Audience (priority)**: (1) practice owner / manager (pilot-facing); (2) Goldsmith pilot brief insert — see `goldsmith-pilot-insert.md`

> **Claim discipline**: Every factual claim traces to `../../../marketing/engine-inputs/verified-claims.md` (`[VC-n]`) or the 010 test evidence, cited as such. Scope is the **after-hours line only** — evenings, overnight, weekends, and holidays outside the clinic's configured hours. Daytime answering is post-pilot and is not claimed here. The engineering-harness results below are simulation results ("designed and tested to"); live-clinic numbers are to be measured at the Goldsmith pilot.

---

## Elevator Pitch

**One sentence**: Your clinic's after-hours phone, answered on the first ring — booking the routine straight onto your calendar and getting a real emergency to a real person, fast, every time.

**Three sentences**: Today, after-hours calls roll to voicemail — and a voicemail is a booking you lost and a client who called the ER instead. Vera answers every after-hours call the moment it comes in, tells the caller up front she's an AI, books and reschedules against your live calendar, and captures refill requests as drafts for your vet to approve. When it's a genuine emergency, she stops what she's doing and puts a person on the line — briefed before they pick up — and if no one answers she reads out emergency care and guarantees a call-back, so no caller is ever left in silence.

**Paragraph** (~90 words): An independent practice owner spends evenings charting and mornings clearing voicemail — and every missed after-hours call is a booking that walked and a client who may not call back. Vera answers the after-hours line the instant it rings, discloses she's an AI, and handles the routine: she books and reschedules on your real calendar, logs refill requests for your veterinarian's approval — never automatic — and hands genuine emergencies to your on-call team with a spoken summary. Each morning you get a rollup of every overnight call and the short list that needs you. The category has no published benchmark for this; the pilot will set one.

---

## Why Now

The front door is filling fast: front-desk phone tools are broadening toward operations on a 6–12 month horizon, and **no veterinary voice player publishes containment or pricing** [discover.md — OST, L3/L5 timeline]. That gap is the opening. Meanwhile, the market is in the biggest PIMS displacement wave in decades — Cornerstone has no cloud roadmap and Avimark is being sunset, forcing 25,000+ practices to evaluate alternatives `[VC-1]`. A practice re-evaluating its stack right now is deciding between another record-keeper and the first system that actually runs the front door after hours. The Goldsmith pilot's measured after-hours numbers become the category's only published benchmark.

---

## Key Benefits

In the words our customers would use:

1. **Never lose a client to a missed after-hours call.** Every after-hours call is answered on the first ring instead of rolling to voicemail — routine bookings happen overnight and are on your calendar by morning `[VC-8 — PRODUCT-CLAIM; booking flow built & sim-tested, T023]`.
2. **Get your team off the phones and out of morning callback triage.** The routine is handled overnight; your staff start the day with a briefing of what happened, not a voicemail queue to work through `[VC-8; morning briefing built & sim-tested, T034]`.
3. **Sleep knowing a real emergency always reaches a real person.** When it's urgent, Vera puts your on-call team on the line — briefed first — and if no one answers, she reads out emergency care and guarantees a call-back. Refills are logged for your veterinarian's approval, never automatic. This is administrative AI: the vet decides, Vera routes — she never diagnoses `[010 test evidence: escalation & refill-draft paths built and sim-tested, T017/T028/T029]`.

---

## What Makes This Different

**Identity continuity inside a whole-clinic Chief of Staff.** Every other option answers the phone; the direction here is a Vera who eventually knows the family and your schedule — the same Vera across calls, channels, and visits — because she's the operating layer for the whole practice, not a stateless per-call receptionist [discover.md — differentiation; Matt's continuity thesis].

> **Scope note (binding)**: In THIS feature the after-hours line answers, books, escalates, and captures refills. **Caller recognition ("is this about Rex's follow-up?") ships in parallel via VP-4a caller identity — it is not built in the 010 after-hours line and must not be claimed as such in customer copy.** Copy sold today should lead with the benefits (missed-call revenue recovered, staff hours returned, safe escalation), and present identity continuity as the platform direction, not an as-shipped feature of this line [spec.md — "Cycle 3a alone is a competent but stateless after-hours line; the identity-continuity moat lands only when VP-4a lands in parallel"].

**The safety architecture is a differentiator on its own — for practice-owner audiences.** The guarantees live in the adapter, below the language model, not in a prompt we hope it follows: the AI disclosure plays before the model engages, escalation has independent transfer authority, and there is deliberately no code path for Vera to approve a refill. This is the Expert Firewall / AAVSB administrative-vs-clinical line, preserved architecturally — no clinical verbs at any autonomy level, triage is pure routing (zero assessment language), refills draft-for-approval [discover.md L119; spec.md — Autonomy Gate / Expert Firewall].

**The measurement is the moat.** No competitor publishes after-hours containment or pricing. The pilot will produce the first published numbers in the category — that "to be measured at the pilot" framing is itself the differentiator [discover.md — OST].

---

## Top 3 Objections + Answers

| Objection | Answer |
|---|---|
| "I don't want a robot fooling my clients into thinking it's a nurse." | It never does. The first thing every caller hears — before anything else — is that Vera is an AI assistant, not a nurse or veterinarian, that the call is recorded, and that they can say "emergency" to reach a person. The disclosure is enforced below the model, so it can't be skipped. (Built and tested on 100% of simulated calls, T016.) |
| "What if it mishandles a real emergency?" | Emergencies never depend on the AI getting it right. A stated "emergency" or a protocol-flagged call fires an escalation with independent authority — even if the model stalls or disconnects — and warm-transfers to your on-call team with a spoken summary; if no one answers, the caller gets emergency-care directions and a guaranteed call-back, never dead air. In the engineering harness this reached a human on 100% of flagged calls with zero silent drops; the live figure is what we'll measure at your clinic. |
| "Will it start approving medications or making medical calls?" | No — architecturally, not just as a promise. Refill requests are logged as drafts for your veterinarian's approval; there is no path for Vera to approve one herself. She schedules and routes; your vet decides. That's the Expert Firewall. |

---

## Claims Softened or Removed for Discipline (audit trail)

| Original / tempting claim | Why changed | As-published |
|---|---|---|
| Discover seed "answered — 2pm or 2am" / any-hour framing | After-hours scope only (G1/G2); daytime is post-pilot | Scoped every claim to "after-hours"; no "24/7", "around the clock", or "day or night" anywhere |
| "100% escalation / 100% booking accuracy / 0.0% false barge-in / 100% disclosure" as performance | Those are engineering-harness (simulation) results, not live-clinic performance | Framed as "designed and tested to" / "in the engineering harness"; live numbers "to be measured at the pilot" |
| "The same Vera who already knows the family" as a built after-hours capability | Caller identity is VP-4a, shipping in parallel — not built in 010 | Kept as platform *direction* / differentiation thesis; not asserted as as-shipped in the after-hours line |
| "50–60% containment" as an achieved result | Provisional target, ceiling set by Goldsmith's real after-hours call mix | Presented as a pilot measurement, not a claim |
| Competitor names (Dodo / Otto / GuardianVets) | Rule 4 — no competitor names in customer-facing copy | Differentiation stated as benefits + category gap, no names |

---

## Source Artifacts

| Artifact | Used for |
|---|---|
| discover.md `## Marketing Output` | Positioning seed, why-now, differentiation |
| spec.md `## Marketing Output` (post-G1/G2 remediation) | Feature name, 3 benefits, one-liner |
| plan.md `## Marketing Output` | Demo flow (see demo-script.md) |
| tasks.md `## Marketing Output` | Demoable milestones, [MARKETING] task flags |
| marketing-notes.md | Built-milestone plain-language claims + copy guardrails |
| engine-inputs/verified-claims.md | Claim discipline (`[VC-n]`) |
| vpma_communication_guide.md | Voice rules (concrete, numeric, never hype — VC-11) |

---

*Stage-gated note: at Stage 2, speckit-marketing mandates `brief.md` + `demo-script.md` only. GTM materials (changelog, blog, social — Stage 5; sales one-pager/deck — Stage 6; case study/press — Stage 7) are intentionally NOT generated. The `goldsmith-pilot-insert.md` in this directory is a pilot-facing brief for the already-committed Goldsmith pilot, not a cold-prospect GTM asset.*

**These artifacts are for internal use and the committed pilot only. NEVER publish, post, or distribute without human review and product-truth validation of the PRODUCT-CLAIMs above.**
