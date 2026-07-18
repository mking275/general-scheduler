# Analyze Report — Feature 009 (Vera Envelope Onboarding)

**Produced by**: speckit-analyze (ANALYZE + REMEDIATE minion) — 2026-07-18
**Inputs cross-checked**: `spec.md`, `plan.md`, `tasks.md`, `discover.md`; reuse targets `backend/relationship/entity_ref.py`, `backend/relationship/review_queue.py`, `backend/models.py` (structure + `HouseholdReviewQueue`), `backend/scripts/generate_avimark_fixture.py`, `backend/relationship/household_repository.py` (init_db/RLS pattern); the 011 seam in `specs/011-relationship-memory/spec.md`; 008 native tier `backend/onboarding_repository.py` + `backend/agents/onboarding_agent.py`.

**Verdict summary**: No CRITICAL blockers. The spec/plan/tasks triad is unusually coherent (all 33 FRs and 9 build-time SCs map to ≥1 task or an explicit Pilot-Activation home; the four hard gates exist as state-machine guards). Findings concentrate on (a) two plan/tasks structural disagreements, (b) two unauthored-but-cited docs, (c) one gate-integrity test gap on the most load-bearing gate, and (d) three seam-precision issues against the reused 011 artifacts.

**Counts**: CRITICAL 0 · HIGH 3 · MEDIUM 4 · LOW 4 (11 total).

---

## Flagged-item verdicts (the three the tasks step raised)

### FI-1 — SC-007 (time-to-shadow-ready) homed in Pilot-Activation — correct? → **VERDICT: CORRECT.**
SC-007 is a wall-clock/real-data metric ("first practice shadow-ready within ~1 week of *data receipt*"). The build runs against a synthetic fixture with no calendar-time proxy, so "1 week from receipt" is unprovable at build time — it can only be verified against the real ~Aug 3 delivery. `tasks.md` T045 verify explicitly defers "SC-007 calendar/real-data figure to Pilot-Activation," and the Pilot-Activation section carries a dedicated "SC-007 real-data timing gate." The *architectural enablers* SC-007 depends on (per-practice independence, blocked-≠-stalled, prior inheritance) ARE build-time provable and are covered by T033/T044/SC-010. Correctly homed. See LOW finding F8 for a one-line coverage-clarity annotation.

### FI-2 — Canonical financial/inventory tables: `models.py` (T002) vs a separate `canonical_model.py` — plan/tasks disagree. → **VERDICT: `models.py` (T002) wins; strike `canonical_model.py`.**
`plan.md`'s file tree (line 114) lists `backend/envelope/canonical_model.py` as "canonical entity definitions + the net-new financial/AR/ledger/payment + inventory tables," but the same plan's **Setup phase** (line 154) and `tasks.md` **T002** both put those Pydantic entities in `backend/models.py`. The shipped 010/011 precedent is a single shared `backend/models.py` (every table model — `HouseholdReviewQueue`, `VerificationChallenge`, etc. — lives there; SQL/`init_db` lives in the repository classes, not the model file). A separate `canonical_model.py` for entity/table *definitions* is redundant and would fork the model-definition convention. Resolution: entities → `models.py` (T002); `canonical_model.py` struck from the plan tree. See HIGH finding F1.

### FI-3 — `data-model.md` and `research.md` cited by tasks/plan but no task authors them. → **VERDICT: author `data-model.md`; strip `research.md`.**
- `data-model.md` is **load-bearing**: T002 says "per `data-model.md`", the tasks Coverage line names "data-model onboarding-control tables + canonical-model extensions", and the plan tree lists it — yet no task authors it. Author it in remediation (derived from spec Key Entities + plan canonical model + the T002 enum set). See HIGH finding F2.
- `research.md` is referenced **exactly once** — `plan.md` file tree line 137 — and never in tasks. Its intended content (Phase-0 decisions/rationale) is already fully carried by `plan.md` (Technical Context, Conflicts, Top-3 Risks, Constitution Check). Not genuinely needed → strip the reference rather than author a redundant doc. See MEDIUM finding F3.

---

## Findings

### F1 — [HIGH] `canonical_model.py` vs `models.py` disagreement (FI-2)
`plan.md` file tree lists `canonical_model.py` for entity/table definitions while the plan's Setup phase and `tasks.md` T002 both target `models.py`; 010/011 precedent is single-file `models.py`. A build starting from the tree would create a redundant/forking module.
**Verdict**: `models.py` (T002) is authoritative. Remove `canonical_model.py` from the plan tree; canonical entities are appended to `models.py`, normalization logic lives in `normalizer.py` + the `ezyvet_adapter.py`.
**Remediation**: FIXED — `plan.md` file tree edited (canonical_model.py line removed, note folded into the models.py/normalizer entries).

### F2 — [HIGH] `data-model.md` cited (T002 "per data-model.md", Coverage line) but unauthored (FI-3a)
T002 derives every net-new entity + enum "per `data-model.md`", which does not exist. A build would have no entity source of truth beyond the T002 inline list.
**Verdict**: Author it. Derive from spec Key Entities + plan canonical-model paragraph + the T002 enum set; enumerate the onboarding-control tables, the net-new canonical financial/AR/ledger/payment + inventory tables, lineage fields, RLS/practice_id scoping, and the reused-artifact seams (entity_ref, HouseholdReviewQueue).
**Remediation**: FIXED — `specs/009-vera-envelope-onboarding/data-model.md` authored.

### F3 — [MEDIUM] `research.md` cited in plan tree but unauthored and redundant (FI-3b)
Referenced once (plan tree line 137), never in tasks; its content duplicates `plan.md`'s own Phase-0 material.
**Verdict**: Strip the reference (do not author a redundant doc).
**Remediation**: FIXED — plan tree line removed.

### F4 — [HIGH] Counsel gate (the whole-spec legal gate, FR-004) has no dedicated go-live/Phase-H test — gate-integrity gap
The four hard gates are real state-machine guards (T006 enumerates all four; T011/T014/T023/T025 implement them). But of the four, the **counsel gate** is the only one with **no dedicated Phase-H harness**: T037 covers the profile gate, T039 the zero-AR gate, T040 the quality floor — the counsel gate is proven only by T011's inline verify and T006's state-machine verify, and the plan's 9-item Test Strategy omits it entirely. For the single most load-bearing gate (no engineering bypass by design; the §3.2(h) legal spine), the absence of a batch-level "no normalization reachable without a `counsel_signoff` row" assertion at the go-live checkpoint is a real integrity gap.
**Verdict**: Add a counsel-gate assertion to the go-live checkpoint (T045) and the plan Test Strategy; no new numbered task required (avoids renumbering the 45-task list).
**Remediation**: FIXED — T045 verify + checkpoint list now include the counsel-gate-before-normalize assertion; plan Test Strategy gains item 0 (counsel-gate).

### F5 — [MEDIUM] 011 handoff overstated — 011 spec defines no consumed `IdentityAuditCorpus` schema
`spec.md` FR-020 / `tasks.md` T029 / `plan.md` claim 009 produces the corpus "in the exact shape 011's resolver/verification tiers **consume**." Cross-check of `specs/011-relationship-memory/spec.md`: 011 references a "real-export identity audit" only as a **gating activity** (line 174, SC-004 Pilot-Activation), and its concrete shared artifacts are `entity_ref` keys and the `HouseholdReviewQueue` (candidate-set/FR-010). 011 specifies **no** `IdentityAuditCorpus` data type as a consumed input. So the corpus schema is 009-defined, not 011-specified; the "exact shape 011 consumes" wording overstates 011's side and risks a phantom-contract expectation.
**Verdict**: Reframe as "009 **defines** the audit-corpus seam in `contracts/identity-handoff.md` (T030) as the proposed 011 input gate; 011 to adopt — coordinate, don't fork." The two artifacts that genuinely already exist and are reused verbatim (`entity_ref.py`, `HouseholdReviewQueue`) stay as-is.
**Remediation**: FIXED — softened wording in `spec.md` FR-020, `plan.md` (seam bullet), `tasks.md` T029/T030.

### F6 — [MEDIUM] Reused `HouseholdReviewQueue` is clinic-scoped (no `practice_id`); 009 is practice-scoped
`backend/models.py` `HouseholdReviewQueue` and `review_queue.propose_grouping(clinic_id, …)` key on `clinic_id` only. 009 processes 23 practices as independent `practice_id`-scoped units (T002: "practice-scoped tables key on `practice_id`"), and reuses `review_queue.py` **verbatim** (must not fork). Collisions from different practices would land in one clinic-scoped queue with no practice attribution column, and its RLS would be clinic- not practice-scoped.
**Verdict**: Do not fork the reused module. Carry `practice_id` inside `evidence_json`/`subject_refs` (both are open JSON on the existing model), so per-practice attribution and drill-down work without a schema change.
**Remediation**: FIXED — documented in `data-model.md` (Reused-artifact seams) and noted in `tasks.md` T028.

### F7 — [MEDIUM] Spec Key Entity "ReviewItem" vs reuse-verbatim `HouseholdReviewQueue` — risk of a duplicate model
`spec.md` Key Entities lists "ReviewItem" as a distinct entity and `tasks.md` T002 lists `ReviewItem` among the net-new Pydantic models to add to `models.py` — but plan/tasks elsewhere mandate reusing `review_queue.py` + `HouseholdReviewQueue` **verbatim**. Creating a new `ReviewItem` model would duplicate the shipped queue and split the never-auto-merge write path.
**Verdict**: "ReviewItem" is the conceptual name for the reused `HouseholdReviewQueue` row — not a net-new model. Clarify so T002 does not author a duplicate.
**Remediation**: FIXED — `data-model.md` maps ReviewItem → reused `HouseholdReviewQueue`; T002 annotated ("ReviewItem is the reused `HouseholdReviewQueue`, not a net-new model").

### F8 — [LOW] SC-007 coverage-clarity (FI-1)
The tasks Coverage line reads "SC-001–SC-010" without noting SC-007 has no build task (it is Pilot-Activation-homed). Correct as designed; a one-line annotation prevents a future reader treating it as an unmapped SC.
**Remediation**: FIXED — Coverage line annotated "(SC-007 timing is Pilot-Activation-homed; build proves only its enablers via T033/T044/SC-010)."

### F9 — [LOW] 008-collision risk — well-managed, no change
008's native tier is `backend/onboarding_repository.py` (raw sqlite3) + `backend/agents/onboarding_agent.py`; 009's is `backend/envelope/onboarding_repository.py` (Postgres). Distinct import paths (`backend.onboarding_repository` vs `backend.envelope.onboarding_repository`); T001 verify already asserts no shadow/collision. No structural risk.
**Remediation**: NO CHANGE NEEDED — collision already guarded by T001; path separation is correct.

### F10 — [LOW] FR-011 (initial-bulk-load-only; delta/dual-path out of scope) has no explicit scope-assertion test
FR-011 is a scope-boundary requirement. It is owned by T018 (bulk load) + the T031 scope-guard assertion ("no delta-sync/dual-path-write/cutover verb exists in the tier"), which is adequate. No dedicated "delta is out of scope" test, but the scope-guard assertion covers the intent.
**Remediation**: NO CHANGE NEEDED — T031 scope-guard assertion is sufficient; noted for traceability.

### F11 — [LOW] SC-005 (recon report produced+delivered for 100% before shadow-ready) has no dedicated harness
Covered transitively: T031 readiness criteria require "reconciliation report produced AND group-acknowledged" before `shadow_ready`, and T024 produces the report. No standalone SC-005 harness, but the readiness gate enforces it structurally.
**Remediation**: NO CHANGE NEEDED — enforced by the T031 readiness gate; acceptable.

---

## Gate-integrity summary (the four hard gates)

| Gate | Guard (impl) | State-machine (T006) | Dedicated Phase-H test | Status |
|---|---|---|---|---|
| Counsel sign-off before normalize (FR-004) | T011 | ✅ | **was missing → added to T045 (F4)** | FIXED |
| Profile-before-normalize (FR-006) | T014 | ✅ | T037 | OK |
| >20% quality floor (FR-015) | T023 | ✅ | T040 | OK |
| Zero-AR-tolerance (FR-017) | T025 | ✅ | T039 | OK |

All four are genuine guards routed through the single-write-path state machine (T006), not checkboxes. Post-remediation, all four have go-live test coverage.

## Requirement-coverage summary
- **FR-001…033**: all 33 map to ≥1 task (spot-checked end-to-end; tasks Coverage line corroborated). FR-011 is a scope-boundary FR covered by T018 + T031 scope-guard (F10).
- **SC-001…010**: SC-001→T036, SC-002→T037, SC-003→T038, SC-004→T039, SC-005→T031/T024 (F11), SC-006→T041, **SC-007→Pilot-Activation** (F8, correct), SC-008→T042, SC-009→T043, SC-010→T044. No unmapped SC.
- **Contracts**: `pims-adapter-port.md` (T017), `reconciliation-report.md` (T027), `identity-handoff.md` (T030) — all authored by tasks. `data-model.md` was the only cited-but-unauthored doc (F2, fixed); `research.md` reference stripped (F3).
- **Scope integrity**: 009 ends at `shadow_ready`; no delta-sync/dual-path/verb-promotion/cutover leakage (plan Conflict #3 + T031 scope guard hold). No scope leak past shadow-ready detected.
