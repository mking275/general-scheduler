# Specification Analysis Report — 010 Vera Voice

**Feature**: `010-vera-voice` (VP-3, cycles 3a + 3b) — Vera After-Hours Front Door
**Analyzed**: 2026-07-09 · **Mode**: read-only cross-artifact consistency (speckit-analyze, passes A–F + G)
**Artifacts**: discover.md, spec.md, plan.md, research.md, data-model.md, contracts/voice-channel.md, tasks.md
**Constitution**: `.specify/memory/constitution.md` v1.0.0 (demo-scoped; not yet amended)

> Verified against source: constitution Principle III does mandate "SQLite… No external services in demo scope"; `backend/agents/prescriptions.py::request_refill()` does set `status = "auto_approved"` when `refills_remaining > 0` (~line 124). Both load-bearing claims are accurate.

---

## Findings

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| X1 | Constitution | **CRITICAL** | constitution.md III + spec.md L211 / plan.md L52 / data-model.md L3 | Principle III (SQLite, no external LLM, no external services) is violated by design (external realtime LLM + Postgres/RLS). Declared "flagged for amendment" in 4 artifacts, but the constitution is still v1.0.0 with **no amendment made**, and Governance requires deviations be justified in the plan. Documentation does not dissolve a MUST conflict. | Land a formal constitution amendment (or a scoped-exception clause covering platform features) **before** speckit-implement. Departure is otherwise consistently declared — this is the outstanding formal step, not a hidden assumption. |
| X2 | Constitution | LOW | plan.md L44–56 (Constitution Check) | Governance clause requires deviation justification in "the plan's Complexity Tracking section"; the plan documents it under "Constitution Check" instead. | Rename/alias the section or add a Complexity Tracking pointer to satisfy the Governance format literally. |
| F1 | Inconsistency | **HIGH** | spec.md L212 vs plan.md L16–24 & L142–144, research.md D6, tasks.md L9 | Candidate (a) confirmed. Spec Assumptions still frame **C3 as an external "hard pilot gate" that "must land before go-live."** Plan/research/tasks all encode the accepted 2026-07-09 negotiation: **L3 is VetAgent-owned/built in-stream**; only L1/L2 conditions are external. Spec is stale vs the architecture every downstream artifact builds. | Update spec Assumptions dependency language from "C3 tier must land before go-live" to "L1/L2 conditions accepted + L3 built in-stream (extract to core C3 post-pilot)," per plan's own recommendation (plan L144). |
| F2 | Inconsistency | **HIGH** | data-model.md L21 & L23, contracts B6 (L111), spec.md US1 sc.3 (L37), FR-027 (L169), SC-004 (L193) | **Containment is defined two incompatible ways.** `disposition` and telemetry `containment_outcome` are 4-value enums where `contained` and `booked` are **mutually exclusive**; but FR-027 defines containment as *any* non-emergency resolved without a human, and US1 logs a booking "**as contained**." The headline published pilot metric (SC-004 50–60%) is therefore computable two ways (booked counted, or not). | Decide whether `booked` ⊆ contained. Keep `containment_flag` BOOLEAN as the metric source (independent of the disposition enum), and define SC-004 containment rate explicitly as `count(containment_flag) / non-emergency calls`. Align telemetry `containment_outcome` naming so it is not read as the metric. |
| C1 | Underspecification | **HIGH** | FR-010 (L142), data-model call_session (no key col), contracts B5 (L98), tasks T023 (L85) | Candidate (c) confirmed. FR-010 mandates idempotent booking but defines **no idempotency key**; data-model has no key column; only T023's verify line assumes `call_session_id + slot`. That key is unsafe: (1) the **same slot for a second patient in one call** would be wrongly deduped; (2) a caller who **calls back** (new session) to retry would not dedupe. | Define the idempotency key in FR-010 + data-model (e.g. `(clinic_id, slot_id, patient_ref, requested_reason)` or a client-supplied booking token), not session+slot. Add the column and reflect in booking_agent contract. |
| E1 | Coverage Gap | **HIGH** | FR-014 (L148); no task in tasks.md | FR-014 MUST ("informational answers — hours, prep, pricing — come **only** from clinic config, never model priors") has **zero owning task**. Red-team T037 probes clinical questions but never asserts config-grounding of informational answers. Model-hallucinated hours/pricing is a live liability surface. | Add a task (Phase D or G) that grounds informational answers in `clinic_voice_config` and a red-team assertion that Vera refuses/declines rather than inventing hours/prices. |
| C2 | Underspecification | MEDIUM | data-model call_turn `gate_decision` (L45), contracts B3 (L82), tasks T002/T027 | Candidate (d) confirmed. `advise\|propose\|do\|reject` are persisted and gated, but the **voice-channel semantics of `advise` and `propose` are undefined** — a synchronous live turn has no mid-call human-approval loop. T027 only exercises `reject` + `do`-blocking. | Define what `advise`/`propose` cause on a live call (speak-suggestion? defer to briefing? no-op?) or restrict the voice gate to `do\|reject\|escalate` and document why the C4 ladder collapses on this channel. |
| C3 | Underspecification | MEDIUM | tasks T025 (L88), contracts B3 (L84), plan Phase D (L105) | Candidate (e) confirmed. VP-4a household-summary is consumed via a "stubbed interface" but **the stub's shape is specified nowhere** (no type in contracts, no field in data-model). | Add the household-summary stub interface (fields + `audience_scope` contract) to contracts/voice-channel.md so T025 has a frozen shape to build against. |
| C4 | Underspecification | MEDIUM | tasks T032 (L112), FR-030 (L172), data-model clinic_voice_config | Candidate (h) confirmed. Cost-per-call requires "per-provider audio/token pricing config," but that config has **no home** — no data-model field, no `config/voice/` fixture created in T003. | Define a pricing-rates source (config file fixture or table) and reference it from T032/FR-030; add its creation to T003. |
| C5 | Underspecification | MEDIUM | spec US1 (L36) & Edge Cases (L117), contracts A1 (L18), tasks T006 (L30) | Candidate (g) confirmed. Only **single-match soft-confirm** is specified. Contract A1 returns `candidate_parties` >1 for shared lines, and the edge case says "stay unverified until soft-confirmed," but **no artifact specifies the disambiguation dialog** (how Vera picks among N candidates without leaking identity). No task implements it. | Specify the multi-candidate soft-confirm dialog (identity-safe prompts) and add an implementing task/verify; today shared-line callers can only ever stay unverified. |
| C6 | Underspecification | MEDIUM | tasks T014 (L52), FR-002 (L130), FR-003 (L131) | Candidate (f) confirmed. T014 verify silently assumes resume "**preserves consent, not re-disclosed**," but no FR/spec decides whether a resumed session must re-disclose. FR-002 says disclosure on "100% of calls" — undefined whether a resumed WS is the same call. | State the policy explicitly (a resumed session is the same call → no re-disclosure, consent record persists) in FR-002/FR-003 so the assumption is owned, not implicit. |
| C7 | Coverage Gap | MEDIUM | FR-004 (L132), data-model clinic_voice_config.after_hours_window (L102); no task | Candidate (b) confirmed. FR-004 scopes the feature to after-hours only and the data-model has `after_hours_window`, but **no task consumes it** to gate/route calls by the after-hours boundary. | Add a task that reads `after_hours_window` and enforces the boundary (or explicitly note the pilot line is always-after-hours so no runtime gate is needed — decide and document). |
| E2 | Coverage Gap | MEDIUM | FR-019 (L155); no task | FR-019 MUST ("always offer to escalate and never dismiss a stated concern") has **no owning task**; it is implied by escalation tasks but never asserted (T037 does not test it). | Add an always-offer-to-escalate assertion to the red-team/SLO harness. |
| E3 | Coverage Gap | MEDIUM | tasks.md L5 ("Coverage: FR-001–FR-030…") | The coverage banner asserts full FR-001–FR-030 coverage, but FR-004, FR-014, and FR-019 lack owning tasks (C7/E1/E2). Claim is overstated. | Correct the coverage banner or add the missing tasks; do not ship an inaccurate coverage claim. |
| B1 | Ambiguity | MEDIUM | FR-020/US5 (L90, L98), data-model escalation_event.trigger `low_confidence`\|`slo_breach` (L69) | "Low confidence" and "SLO thresholds breached" trigger overflow, but **no numeric thresholds are defined** anywhere. `low_confidence`/`slo_breach` triggers are unquantified. | Quantify the confidence and SLO breach thresholds (or reference a config field) so the overflow trigger is testable. |
| F3 | Inconsistency | MEDIUM | discover Registry (L106) vs data-model L45 / contracts B3 / tasks T002,T027 | Autonomy-ladder terminology drift: discover names the ladder **KNOW→ADVISE→DECIDE**; data-model/contracts/tasks use **advise\|propose\|do\|reject** ("C4"). C4 is referenced but never defined in these artifacts, and the two vocabularies are not reconciled. | Add a one-line C4 mapping (KNOW/ADVISE/DECIDE ↔ advise/propose/do/reject) in research or contracts; use one vocabulary. |
| F4 | Inconsistency | MEDIUM | tasks.md L2–3 vs data-model.md L3, plan L3, T004 (L26) | tasks names the build target "**General_Scheduler repo (feature branch)**" with sim/dual-mode, while data-model/plan mandate **Postgres+RLS, not SQLite**. T004 says "Postgres/RLS-ready… app-level scoping fallback" but does not say which DB `init_db()` actually targets in this build. The one place the platform departure is muddied. | State explicitly whether the in-repo build runs the 8 tables on SQLite (demo repo) or a local Postgres, and how that reconciles with the "not SQLite" data-model claim. |
| G1 | Messaging Drift | MEDIUM | spec.md ## Marketing Output — Benefit 1 (L225) | Benefit 1 says every call is answered "**day or night**," but the feature is **after-hours only** (FR-004); daytime answering is an explicit Non-Goal (US6/3c, post-pilot). Overclaims shipped scope. | Qualify to "after-hours" (or "overnight") until 3c daytime overflow ships; do not carry "day or night" into speckit-marketing. |
| G2 | Messaging Drift | MEDIUM | spec.md ## Marketing Output — One-Line Description (L229) | One-liner says "answered **around the clock**" — same 24/7 overclaim vs after-hours-only 3a/3b scope. | Reword to after-hours framing before running speckit-marketing. |
| F5 | Inconsistency | LOW | plan.md L66 (`voice/`) vs tasks.md L7 (`backend/voice/`) | Path rooting differs. **Already reconciled** in tasks' Path note (voice/ rooted at backend/voice/ because existing Python lives under backend/). Plan not back-updated. | Optional: update plan's structure block to `backend/voice/` for symmetry; non-blocking. |
| F6 | Inconsistency | LOW | tasks T017 (L62) deps vs T020/T021 (L73–75) | Escalation watchdog (T017) declares dep on T015 only, but its `protocol_flag` branch depends on the protocol engine (T020). The literal-"emergency"/silence branches are testable without T020; the protocol_flag branch is not. | Add T020 as a soft dependency for full watchdog coverage, or note the protocol_flag path is validated in T035 (which does dep T021). |
| F7 | Inconsistency | LOW | data-model call_turn (L30) vs spec Key Entities (L176–182) | `call_turn` — described as "the auditable spine" — is not listed among spec Key Entities. Minor entity-model gap. | Add call_turn (or "conversational turn") to spec Key Entities for traceability. |
| D1 | Inconsistency | LOW | FR-007 (L137) | FR-007 says VP-4a "**MUST ship in parallel**" (a MUST on an external program) while simultaneously defining stateless graceful degradation "if VP-4a is unavailable." A MUST plus its own fallback is mildly self-contradictory. | Reword the MUST to "VP-4a is the intended parallel baseline; stateless is the documented degradation." |

**50-finding cap**: not reached (22 findings). No overflow.

---

## Coverage Summary (Functional Requirements → Tasks)

| FR | Has Task? | Task IDs | Notes |
|----|-----------|----------|-------|
| FR-001 answer immediately | Yes | T013, T016 | first-ring answer + disclosure seq=1 |
| FR-002 disclosure 100% | Yes | T003, T016, T040 | |
| FR-003 consent posture | Yes | T016, T033 | |
| FR-004 after-hours only | **No** | — | C7 — `after_hours_window` unconsumed |
| FR-005 identify + soft-confirm | Partial | T006, T025 | single-match only; multi-candidate dialog missing (C5) |
| FR-006 unverified scope | Yes | T024 | |
| FR-007 VP-4a parallel / degrade | Yes | T025, T040 | |
| FR-008 book via pipeline | Yes | T023 | |
| FR-009 read-back + confirm | Yes | T023 | |
| FR-010 idempotent writes | Partial | T023, T039 | key undefined/unsafe (C1) |
| FR-011 deterministic gate | Yes | T021, T027 | |
| FR-012 no clinical language | Yes | T027, T037 | |
| FR-013 no self-ID as clinician | Yes | T037 | |
| FR-014 info answers from config only | **No** | — | E1 (HIGH) |
| FR-015 protocol state machine | Yes | T020, T022 | |
| FR-016 barge-in, no partial write | Yes | T019, T021, T031 | |
| FR-017 100% escalation | Yes | T017, T035, T036 | |
| FR-018 warm transfer + summary | Yes | T029 | |
| FR-019 always offer to escalate | **No** | — | E2 |
| FR-020 ER-directory + callback | Yes | T030 | thresholds vague (B1) |
| FR-021 6-month transcript retain | Yes | T018, T033 | |
| FR-022 refill draft only | Yes | T028 | |
| FR-023 confirm review, never approved | Yes | T028 | |
| FR-024 transcribe + log | Yes | T018, T033 | |
| FR-025 morning briefing | Yes | T034 | |
| FR-026 no-training + consent | Yes | T033 | |
| FR-027 containment measured | Yes | T032 | metric definition ambiguous (F2) |
| FR-028 booking accuracy measured | Yes | T032, T039 | |
| FR-029 escalation completion measured | Yes | T032, T035 | |
| FR-030 cost/call from call #1 | Yes | T032 | pricing source has no home (C4) |

**Success Criteria**: SC-001 (T016/T040), SC-002 (T035/T036), SC-003 (T039), SC-004 (T032; def ambiguous F2), SC-005 (T028), SC-006 (T032/T033/T034), SC-007 (T038) — all mapped.

**FR coverage: 27/30 fully mapped (90%).** Three MUST-level FRs have zero owning task: **FR-004, FR-014, FR-019.**

---

## Constitution Alignment Issues

- **X1 (CRITICAL)** — Principle III violated by design (external realtime LLM + Postgres/RLS). Consistently declared as by-design in discover, spec, plan, data-model; **muddied in tasks** (F4). Governance requires a plan justification; constitution is unamended. Deliberate, well-documented departure — the outstanding step is the formal amendment, not the declaration. NOT silently assumed.
- **X2 (LOW)** — departure documented under "Constitution Check," not the Governance-mandated "Complexity Tracking" section.
- Principles I, II, IV, V — compliant. Binding vet "constitution" (no clinical verbs, pure-routing triage, refills draft-only) preserved architecturally and consistently across all artifacts.

## Unmapped Tasks

None fully unmapped. Weakly-traced: **T014** (session resumption) traces only to an edge case (spec L119) + research D3; carries the C6 undecided disclosure policy.

## Safety-Invariant Consistency (checked, positive)

Disclosure 100%, escalation 100% zero-silent-drop, and refill zero-auto-approve are stated identically across all artifacts. The `refill_request_draft` CHECK constraint + no-code-path-to-`request_refill` + gate guard is genuine defense-in-depth. Booking accuracy ≥99% consistent everywhere.

## Dependency / Cycle Sanity (tasks.md)

No cycles. Critical path (T001→…→T036) coherent. Minor: T004 declares dep T002 not T001; T017 under-declares protocol-engine dep for its protocol_flag branch (F6). 40 tasks / 6 [MARKETING] counts internally consistent.

## Pass G — Messaging Drift Verdict

Feature Brief present. Two MEDIUM drifts: G1 ("day or night") and G2 ("around the clock") both overclaim 24/7 against after-hours-only 3a/3b scope (daytime is a Non-Goal). Name (consumer vs internal) and Benefits 2-3 fine. Fix G1/G2 before speckit-marketing.

---

## Metrics

- Total FRs: 30 · Total SCs: 7 · Total Tasks: 40
- FR Coverage: 90% (27/30) · SC Coverage: 100%
- Ambiguity: 1 · Duplication: 0 harmful · Constitution: 2 (1 CRITICAL) · Messaging drift: 2
- **Severity: CRITICAL 1 · HIGH 4 · MEDIUM 12 · LOW 5 (total 22)**

---

## Next Actions

CRITICAL/HIGH exist — resolve before `/speckit-implement`. Order: X1 → F1 → F2 → C1 → E1 → (C7/E2/E3) → (C2–C6, B1, F3, F4) → (G1/G2) → LOW (X2, F5–F7, D1).

Suggested commands: `/speckit-specify` (F1, C1, C5, C6, E-series, G1/G2), `/speckit-plan` (X1 amendment, C2–C4, F3/F4), manual tasks.md edits (C7/E1/E2/E3, F6).

*Read-only analysis. No artifacts modified. Remediation edits require explicit approval.*
