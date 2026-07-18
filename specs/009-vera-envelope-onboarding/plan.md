# Feature 009 — Vera Envelope Onboarding ("Vera's First Day"): Implementation Plan

**Branch**: `009-vera-envelope-onboarding` · **Scope**: the on-ramp only — **data receipt → verified live envelope, shadow-ready**: chain-of-custody vault receipt, format discovery, ingest/normalization to the canonical practice model, completeness-and-quality verification (financials/AR/inventory included), an owner-trusted reconciliation report, identity/`entity_ref` bootstrap that hands off to 011, and the criteria that mark a practice shadow-ready — under a hard invisible-adoption constraint, generalizing across mixed PIMS via a pluggable adapter port. Ongoing envelope operations (delta sync, dual-path writes, the shadow/advise engine, verb promotion, the Phase-D cutover/Replace event) are **out of scope** (010/011/envelope-MVP). · **Target**: VP-1 convergence platform (Postgres + RLS) — **NOT** the demo SQLite scaffold — extending the tier 010/011 shipped under `backend/`. · **Pilot**: Goldsmith 23-clinic batch; §5 data-copy request submitted **2026-07-18**, complete copies for 23 practice databases arrive by secure file transfer within ten business days (**~Aug 3**), kickoff first week of August. **Format is unknown until delivery** — the pipeline is format-discovery-driven for exactly this reason.

---

## Technical Context

### Runtime stack (platform, not demo repo)
- **Python 3.11 + FastAPI** on the VP-1 platform; **Postgres + RLS** (`clinic_id` tenant scope; onboarding-control tables also filter `practice_id`). Local `docker-compose` Postgres (the shipped `vetagent-voice-pg` container, host port **5433**, `VOICE_DATABASE_URL` convention — R8: never another port/container), app-level scoping standing in for full RLS in the single-clinic build (VP-1-slip degradation, same posture as 010/011).
- **FORCE-RLS on all onboarding-control tables (SEC-20)** — a documented FarmAgent tuition; onboarding tables hold chain-of-custody, reconciliation, and identity-audit rows that must never leak cross-tenant even to a table owner. Provisioning **wraps the full transaction** (the FarmAgent orphan-account bug: a rolled-back receipt must leave no partial vault/lineage rows).
- **Extraction subprocessor**: **Gemini** for parse/vision on unknown-format exports, behind a provider-agnostic `ExtractionPort` (config swap, not rewrite), operated under a **no-retention** posture — no raw source content or screen frames retained (FR-003, DPA). In this build the port runs in **sim-mode** over synthetic fixtures; no live PII crosses a subprocessor until the real data lands and counsel clears (Pilot-Activation).
- **Canonical practice model = the platform practice model, hydrated by 009.** Normalization writes into the platform Postgres practice tables (`owners`/`patients`/appointments/…, extended with net-new **financial/AR/ledger/payment** and **inventory** tables where absent), every record carrying `source_id`/`entity_ref` lineage. 011's flat-owners→household migration reads the `owners` table 009 hydrates (011 data-model M1) — **this is the agreed seam; coordinate, don't fork.**
- **Reused mechanisms (extract, don't fork)**: the 008/032/044 extraction pipeline + streaming extract-narrate-confirm UX (`backend/agents/document_parser_agent.py`, `migration_agent.py` field-map precedent), the FarmAgent *fixed* provisioning/RLS transaction semantics, `backend/relationship/entity_ref.py` (the `{type}:{stable_id}` mapper — `client:ezyvet_c*`, `patient:ezyvet_p*`, `household:vah_*`), the never-auto-merge `backend/relationship/review_queue.py` pattern, and the 048 job-router/session-log seams. `sms_gateway.py`'s outbound leg carries owner-facing report/gap-notice delivery.

### Architecture — per-practice staged state machine behind a pluggable PIMS port
Each practice database is an **independent unit** advancing through an explicit state machine, one row per practice, transitions append-only:

```
received → profiled → normalized → verified → reconciled → identity_bootstrapped → shadow_ready
   │           │           │           │            │                │                    │
   └ vault +   └ format    └ canonical └ complete-  └ recon report   └ audit corpus       └ readiness
     chain-of-   profile     load +      ness +       + owner ack       for 011 +            criteria
     custody     (adapter    lineage +   quality      (zero-AR-         proposals +          all met
   [COUNSEL      selected)   idempotent  (>20% floor  tolerance)        never auto-merge
    GATE before               ingest)     gate)
    normalize]
    │
    └ blocked / partial / delta states are first-class (US8): a practice may sit at `received`
      (counsel gate not cleared), `verified`-with-gap (partial delivery), or `held`
      (quality-floor / AR-variance) without ever being marked complete or stalling the batch.
```

- **`PimsAdapterPort`** (stable port): `profile(raw_export) -> FormatProfile` and `normalize(profile, raw_export) -> canonical records + lineage`. **ezyVet is the first and only adapter built this cycle**; the port is designed for a second adapter (selection deferred — the target group's PIMS mix is undetermined, spec clarification 2026-07-18). The orchestration/verification/reconciliation core is **PIMS-agnostic and MUST NOT be forked per PIMS** (FR-027); everything PIMS-specific lives behind the port.
- **Format discovery is the seam** where a new adapter plugs in and the guard that makes the pipeline robust to "format unknown until Aug 3": normalization is **blocked** for any database lacking a completed `FormatProfile` (FR-006), and the adapter re-profiles against the real export when it lands (config-swap, no core change).
- **Group rollup** is a computed view over the per-practice rows; a **blocked practice never holds the batch** (FR-025), and practice N **inherits group-level mappings/priors** (the adapter's per-variant field map is a *prior*, not an assumption — each database is profiled independently for schema drift; FR-026, SC-010).

### 010/011 reuse surfaces — 009 EXTENDS these, no duplication
| Existing artifact | 009 use |
|---|---|
| `backend/relationship/entity_ref.py` (011 T005) — `{type}:{stable_id}` mapper, names never in the key | Reused verbatim to seed `source_id`/`entity_ref` lineage on every canonical record (FR-009); `client:ezyvet_c*`/`patient:ezyvet_p*` are the handoff keys to 011 |
| `backend/relationship/review_queue.py` (011 T012) — `propose_grouping`, **no auto-merge code path** | The identity-bootstrap collision/probable-duplicate sink; 009 writes proposals, never merges (FR-021); reuses `household_review_queue` |
| `backend/relationship/identity_resolver.py` candidate-set shape (011) | Identity bootstrap produces the **real-export identity audit corpus** in the exact shape 011's gated resolver/verification tiers consume (FR-020, SC-008) — this is 011's hard input gate; 009 produces it |
| `backend/relationship/household_repository.py` + `voice_repository.py` — Postgres/RLS, `init_db()`, append-only audit spine, docker-compose PG on 5433 | The persistence pattern for 009's net-new onboarding-control tables (same conventions, FORCE-RLS added) |
| `backend/agents/migration_agent.py` — per-source CSV field maps, ZIP ingest, `MigrationRun` progress + verbose log | Precedent for the ezyVet adapter's field-map normalization and the append-only ingest-run progress/log |
| `backend/scripts/generate_avimark_fixture.py` — seeded synthetic PIMS export (ZIP of CSVs) | Pattern for the **synthetic ezyVet-shaped complete-export** fixture generator — the test substrate that lets the whole build run before Aug 3 |
| `sms_gateway.py` outbound leg + `INBOUND_LIVE`/credential auto-detect (011 `inbound_sim.py`) | Owner-facing report/gap-notice delivery; the sim/dual-mode env-resolver pattern for the vault + extraction subprocessor |

### Sim / dual-mode discipline (consistent with 010/011)
**Everything external runs in sim/dual-mode; live is a config swap deferred to Pilot-Activation.** The entire list is completable and testable with **zero live subprocessor / secure-transfer / real-PII calls**:
- **The test substrate is a synthetic ezyVet-shaped complete-export fixture** (built early, Foundational phase) — seeded, reproducible, carrying deliberately injected dirty-data and known financial ground-truth so completeness/quality/reconciliation are *assertable against an answer key*, plus a **partial-delivery variant** (attachments omitted) and a **delta variant** for US8. The `FormatProfile` discovery stage is designed to **re-profile against the real export when it lands (~Aug 3)** — a config swap, no core change (Pilot-Activation).
- **Vault** = a local encrypted-at-rest store in the build; the live secure-file-transfer intake and clinic-owned vault provisioning are the config swap.
- **Extraction subprocessor** (Gemini) runs against fixtures with a stubbed no-retention adapter; the live DPA'd subprocessor flip is Pilot-Activation and **counsel-gated**.
- Reconciliation ties ingested financials to the fixture's **synthetic source-reported figures** (build-time proxy for "the source system's own reported figures"); the real ezyVet reported-figure reconciliation is verified at pilot.

### Performance / correctness goals
| Metric | Target | Method |
|---|---|---|
| Chain-of-custody before parse (SC-001) | **100%** received w/ full record; **0** parses pre-receipt | vault-write + checksum + scope-vs-request precedes any parser; state-machine guard |
| Profiled before normalize (SC-002) | **0** databases normalized without a `FormatProfile` | hard transition guard (`normalized` unreachable from `received` without `profiled`) |
| Lineage + idempotency (SC-003) | **100%** canonical records carry `entity_ref`; re-run → **0** duplicates | deterministic `source_id` keys; idempotent upsert; re-run diff assertion |
| Financial completeness (SC-004) | **100%** practices cover clinical+scheduling+comms **+ financial/AR/inventory** | category-coverage matrix vs profile; AR/invoice/payment totals computed |
| Zero-AR-tolerance reconciliation (FR-017) | any unexplained AR variance **blocks**; **0** silent AR discrepancies | recon engine surfaces every AR delta as blocking; other variances itemized-or-block |
| Quality floor (FR-015) | **>20% unusable → held**, gap itemized; never shadow-ready below floor | sampled usable-record share vs threshold config |
| Zero staff artifacts (SC-006) | **0** staff logins/training/dashboards/notifications; **0** staff identities provisioned | invisible-adoption guard + red-team; owner/manager-only surfaces |
| Identity handoff (SC-008) | audit corpus in 011's shape; **0** auto-merges | reuse `review_queue` (no merge path); corpus-shape contract test |
| Partial-delivery detection (SC-009) | **100%** detected; **0** silently complete; gap notice produced | scope-vs-request diff → `GapNotice`; partial state is first-class |
| Time-to-first-shadow-ready (SC-007) | first practice ≤ **~1 week** of receipt; batch reconciled in ~4–6-wk window; **no cutover** | independent per-practice units + prior inheritance; batch not held to slowest |

---

## Constitution Check

> **Complexity Tracking** — this Constitution Check *is* the plan's Complexity Tracking section (aliased per the speckit-plan template). One tracked departure (Principle III), justified in place under the v1.1.0 Platform-track exception.

GS constitution **v1.1.0**: Principle III carries a Platform-track exception permitting PostgreSQL+RLS and external services for platform-track specs (VP-1 and dependents) whose plan declares the departure. 009 is platform-track (Postgres+RLS, hydrates the platform practice model, uses an external extraction subprocessor) and **declares that departure here**.

| Principle | Status | Notes |
|---|---|---|
| I Demo-First / Verbose Log | ✅ (exceeds) | every receipt, format profile, ingest run, verification, reconciliation, reveal-of-gap, and readiness transition is an append-only, owner-visible record; the chain-of-custody + reconciliation spine *is* the auditable log |
| II Agentic Pipeline Integrity | ✅ | normalization flows through the adapter port only; **no bypass write** into the canonical store; no normalization before the counsel gate; the state machine is the single write path |
| III Data Simplicity (SQLite, no external services) | ✅ **departure permitted under v1.1.0 Platform-track exception** | canonical load + chain-of-custody ride VP-1 PG/RLS; extraction subprocessor is external. Not an unresolved violation. |
| IV Role-Aware UI | ✅ **generalized to invisible-adoption** | onboarding surfaces are **owner/manager-only** (reconciliation report, readiness rollup); staff experience *nothing* — role-awareness taken to its zero-staff-artifact limit (FR-028/029) |
| V Incremental Buildability | ✅ | US1 (receipt+vault) delivers standalone value; each practice is independently deployable; a blocked practice never stalls the batch |

**Binding constraints preserved architecturally**:
- **Counsel gate is a hard state-machine guard**, not a checkbox: `received → profiled/normalized` is unreachable until a `counsel_signoff` row on the clinic-owned-data structure is recorded (FR-004, §3.2(h) posture). Vault receipt (a §6.3 backup) is permitted *before* the gate.
- **Licensed-act firewall preserved**: no clinical verb exists in the onboarding catalog at any level; onboarding runs entirely in KNOW/ADVISE.
- **Claim discipline extended to runtime**: every canonical record traces to a source record via `entity_ref`/`source_id`, so every fact Vera later states is verifiable (FR-009).

### Code-level reconcile — the invisible-adoption guard (FR-028/029, SC-006), edge case "clinician appears in export"
The known failure mode: a normalizer that encounters a clinician/staff record in the export **auto-provisions a login or a staff-facing surface** as a side effect. This MUST NOT happen. Plan: (1) the canonical `staff:*` entity is created as **data only** (for scheduling/attribution) with **no auth/login/notification path reachable from onboarding code** — the provisioning verbs simply do not exist in this tier; (2) an **invisible-adoption assertion** in the readiness gate rejects any onboarding run that emitted a staff credential, training artifact, dashboard, or notification; (3) all report/rollup surfaces are constructed owner/manager-audience-only (reusing 011's audience-scoping vocabulary at the surface edge). Enforced by a red-team test that scans a full batch run for any staff-facing artifact and asserts **zero** (SC-006).

---

## Project Structure — New Files (on VP-1 platform)

```
backend/envelope/                            # 009-owned envelope-onboarding tier (distinct from 008's native backend/onboarding_repository.py)
├── __init__.py
├── onboarding_repository.py                 # Postgres/RLS ops for the net-new onboarding-control tables (HouseholdRepository/VoiceRepository pattern; FORCE-RLS; wrap-full-transaction)
├── state_machine.py                         # per-practice staged state machine + transition guards (counsel gate, profile-before-normalize, floor/AR blocks)
├── vault.py                                 # clinic-owned encrypted-at-rest vault: receipt, checksum, byte-count, chain-of-custody record (sim store; live = config swap)
├── scope_check.py                           # scope-vs-request against the §5 category list; gap detection (feeds US8)
├── counsel_gate.py                          # records/enforces counsel sign-off; the hard pre-normalization gate (FR-004)
├── extraction_port.py                       # provider-agnostic ExtractionPort (Gemini adapter) — no-retention posture; sim over fixtures
├── format_discovery.py                      # profiler → FormatProfile (entities, counts, encodings, referential structure, export variant); blocks normalize w/o profile
├── pims/
│   ├── __init__.py
│   ├── port.py                              # the stable PimsAdapterPort (profile/normalize) + adapter registry
│   └── ezyvet_adapter.py                    # first adapter: ezyVet complete-export → canonical map + lineage (migration_agent field-map precedent)
├── normalizer.py                            # canonical load into the platform practice model; source_id/entity_ref lineage; deterministic + idempotent upsert
│                                            #   (canonical entity + net-new financial/AR/ledger/payment + inventory MODELS live in backend/models.py per T002 — 010/011 single-file precedent, NOT a separate canonical_model.py)
├── completeness.py                          # category coverage + counts vs profile + referential integrity; financial/AR/inventory explicit (FR-012/013)
├── quality.py                               # dirty-data signals (shared phones, dup owners, deceased pets, orphans) → QualityAssessment; >20% floor (FR-014/015)
├── reconciliation.py                        # ReconciliationReport: requested/delivered/ingested by category + financial recon; zero-AR-tolerance; owner acknowledgment (FR-016–018)
├── identity_bootstrap.py                    # seeds entity_ref, household/party grouping proposals, IdentityAuditCorpus for 011; routes collisions to review_queue; never auto-merge (FR-019–021)
├── readiness.py                             # PracticeReadiness criteria evaluation → shadow_ready; the invisible-adoption assertion (FR-022/023/028)
├── batch.py                                 # multi-practice batch orchestration + group rollup + prior inheritance; blocked practice never stalls batch (FR-024–026)
├── gap_notice.py                            # owner-facing, paper-trail-ready gap notice for partial deliveries (FR-031)
├── owner_surface.py                         # owner/manager-only report + rollup surfacing (invisible-adoption guard, FR-029)
└── sim.py                                   # dual-mode env resolver (vault + extraction live vs sim; ONBOARDING_LIVE flag, sms_gateway/inbound_sim pattern)

config/envelope/
├── section5_scope.yaml                      # the §5 letter's enumerated categories — the scope-vs-request source of truth
├── ezyvet_mapping.<variant>.yaml            # ezyVet export → canonical field map (adapter config; the reusable group prior)
└── quality_thresholds.yaml                  # >20% unusable floor + dirty-data rule config; AR zero-tolerance flag

backend/tests/envelope/
├── conftest.py                              # docker-compose PG fixture (5433), same posture as tests/relationship/conftest.py
├── fixtures/
│   └── ezyvet_synthetic_export.py           # seeded synthetic ezyVet-shaped complete-export generator + partial + delta variants + financial answer key (the test substrate)
└── test_*.py                                # per-phase + red-team suites

specs/009-vera-envelope-onboarding/
├── plan.md                                  # this file — also carries the Phase-0 decisions/rationale (Technical Context, Conflicts, Top-3 Risks); no separate research.md
├── data-model.md                            # net-new onboarding-control tables + canonical-model extensions (authored; T002 entity source of truth)
└── contracts/
    ├── pims-adapter-port.md                 # the stable profile/normalize port (second-adapter seam)
    ├── identity-handoff.md                  # entity_ref + identity-audit-corpus shape to 011 (the agreed seam)
    └── reconciliation-report.md             # requested/delivered/ingested + financial-reconciliation shape (owner-facing artifact)
```
*(The skill's AGENTS.md pointer update is deferred — this task is scoped to the spec directory only.)*

---

## Implementation Phases & Effort (engineer-weeks; ew)

Total **~15–19 ew**. Calendar shorter with parallelism (the adapter/discovery chain ‖ the verification/reconciliation chain once the state machine + fixtures land). The real-data re-profile is **gated on the ~Aug 3 delivery** and lives in Pilot-Activation, not the critical build path.

| Phase | Scope | Effort | Notes / risk |
|---|---|---|---|
| **Setup** | `backend/envelope/` package + `config/envelope/` + deps confirm; net-new tables appended to `backend/models.py` + `onboarding_repository.init_db()` (FORCE-RLS, append-only audit spine, docker-compose PG); dual-mode env resolver (`sim.py`). | **1–1.5 ew** | Reuses the 011 repo/conftest pattern wholesale. |
| **Foundational** | The **synthetic ezyVet-shaped fixture** generator (complete + partial + delta variants + financial/dirty-data answer key) — the substrate everything tests against; the **state machine** engine + transition guards; the **`PimsAdapterPort`** interface. | **2–2.5 ew** | Fixture fidelity is load-bearing — the whole build stands on it until Aug 3. Blocking prerequisite for all phases. |
| **A — Receipt + vault + chain-of-custody + counsel gate** (US1) | Encrypted-at-rest vault write; checksum/byte-count/source/timestamp chain-of-custody record; scope-vs-request against §5 categories; the **counsel-gate guard** (no normalize before sign-off); subprocessor no-retention posture. | **2–2.5 ew** | The trust spine; FORCE-RLS + wrap-full-transaction here (orphan-receipt bug). |
| **B — Format discovery + PIMS port + ezyVet adapter** (US2, US7-port) | Profiler → `FormatProfile`; normalize-blocked-without-profile guard; the stable port; the ezyVet adapter (profile + normalize); unmapped entities/fields **flagged, never dropped**. | **2.5–3 ew** | The Aug-3-unknown-format hedge; the second-adapter seam. |
| **C — Normalize to canonical model + lineage + idempotency** (US3) | Canonical load into the platform practice model (+ net-new financial/AR/ledger/inventory tables); `source_id`/`entity_ref` on every record; deterministic, re-runnable, **idempotent** ingest. | **2–2.5 ew** | Idempotency + lineage are SC-003; re-run-diff test gates it. |
| **D — Completeness + quality verification, financials included** (US4) | Category coverage + counts vs profile + referential integrity; **financial/AR/inventory** totals computed; dirty-data quality assessment; **>20% floor** block. | **1.5–2 ew** | Financial completeness is the Digitail-gap differentiator; the floor is a hard gate. |
| **E — Reconciliation report + zero-AR-tolerance + owner ack** (US5) | Requested/delivered/ingested by category; financial reconciliation (AR/invoices/payments) vs source-reported figures; **zero AR tolerance** blocking; **group-level acknowledgment** w/ per-practice drill-down; owner/manager-only. | **1.5–2 ew** | The owner-trust centerpiece; the only trust surface allowed during onboarding. |
| **F — Identity bootstrap + audit-corpus handoff to 011** (US6) | Seed `entity_ref`/`source_id`; household/party grouping **proposals** over the real export; the **identity audit corpus** in 011's shape; collisions/dupes → `review_queue` (owner/manager-surfaced), **never auto-merged**. | **1.5–2 ew** | Produces 011's hard input gate; corpus-shape contract with core. |
| **G — Shadow-readiness state + batch + gap-notice/partial-delta** (US7, US8) | `PracticeReadiness` criteria (all gates met) → `shadow_ready`; **batch orchestration** + group rollup + prior inheritance (blocked ≠ stalled); partial-delivery detection + **gap notice** + idempotent **delta re-ingest**; the **invisible-adoption assertion**. | **2–2.5 ew** | Ties the pipeline together; SC-006/007/009/010 land here. |
| **H — Test + verification + red-team** | Idempotency re-run diff; zero-AR-tolerance + quality-floor gate suite; **invisible-adoption red-team** (scan a batch for any staff artifact = 0); identity-corpus-shape + no-auto-merge; partial→delta reconciliation; chain-of-custody-before-parse. | **2 ew** | Gates go-live; the SC harness. |

**Hard gates before the first real record is normalized**: **counsel sign-off on the clinic-owned-data structure recorded** (the whole-spec gate, §3.2(h)); the DPA no-retention posture confirmed for the live extraction subprocessor; the §5 delivery received into the vault under chain-of-custody; the synthetic-fixture suite green (the build-time proxy for every SC). Vault receipt of the ~Aug 3 delivery may precede the counsel gate (§6.3 backup); **normalization may not.**

---

## Dependencies & Fallbacks

- **§5 delivery (~Aug 3) — the real data. Format unknown until it lands.** *Fallback (this entire build):* the synthetic ezyVet-shaped fixture is the substrate; format discovery re-profiles the real export as a **config swap** (Pilot-Activation) with no core change. A delivered variant the ezyVet adapter cannot fully map **flags for adapter work** rather than forcing a wrong mapping (edge case).
- **Counsel sign-off on the clinic-owned-data structure — HARD gate, whole-spec.** *Fallback:* none on normalization — the state machine cannot advance past `received` into `profiled/normalized` without the `counsel_signoff` row. Vault receipt proceeds (§6.3). This is the one gate with no engineering bypass by design.
- **Live extraction subprocessor DPA (Gemini no-retention) — pending.** *Fallback:* sim extraction over fixtures; the live flip is counsel-gated Pilot-Activation.
- **011 identity resolver/verification tiers — the corpus consumer.** *Coordinate, don't fork:* 011's spec references a real-export identity audit as the **gating activity** that must precede trusted auto-ID (011 spec: resolver "gated on a real-export identity audit"), and its concrete shared artifacts are the `entity_ref` keys and the `HouseholdReviewQueue` (candidate-set/FR-010) — but 011 does **not** yet specify an `IdentityAuditCorpus` *schema* as a consumed input. So 009 **defines** that seam: it produces the real-export audit corpus and **freezes its shape in `contracts/identity-handoff.md` (T030) as the proposed 011 input gate, for 011 to adopt** — not "the shape 011 already consumes." 009 reuses `entity_ref.py` + `review_queue.py` verbatim and does **not** implement runtime auto-ID / soft-confirm / the verification bar (011). 011's flat-owners migration reads the `owners` table 009 hydrates — coordinate at the seam, don't fork.
- **Canonical-model shape read by the shadow/advise engine (010/011/envelope-MVP) — the downstream consumer.** *Coordinate:* the canonical practice model + lineage shape must be agreed at the seam so the advise engine reads what 009 writes; 009 ends at *shadow-ready* and does not build the shadow operation.
- **VP-1 Postgres + RLS** — same posture as 010/011: single-clinic app-scoped Postgres degradation if RLS slips (pilot-only); do **not** regress to SQLite (chain-of-custody + reconciliation + identity-audit need the envelope plane).
- **Second PIMS adapter — deferred** (the target group's PIMS mix is undetermined, spec clarification). The port stays pluggable; only ezyVet is built this cycle. Not a blocker.

---

## Test Strategy (summary; detail in Phase H)

0. **Counsel-gate-before-normalize (FR-004, the whole-spec legal gate)** — assert that across a full batch **no** database is reachable at `profiled`/`normalized` without a recorded `counsel_signoff` row; the guard has no engineering bypass. (The one gate previously lacking a dedicated harness — now asserted at the T045 go-live checkpoint alongside the other three.)
1. **Chain-of-custody-before-parse (SC-001)** — assert every received database has a vault object + checksum + scope-vs-request record written **before** any parser runs; no parse is reachable pre-receipt.
2. **Profile-gate (SC-002)** — assert normalization is unreachable for a database with no `FormatProfile`; **0** databases normalized without a profile.
3. **Idempotency + lineage (SC-003)** — normalize the fixture twice; assert **0** duplicate canonical records, stable identifiers, and **100%** of records resolve back to a source record via `entity_ref`/`source_id`.
4. **Financial completeness + zero-AR-tolerance (SC-004, FR-013/017)** — assert coverage of clinical+scheduling+comms+financial/AR/inventory; reconcile AR/invoice/payment totals to the fixture's synthetic reported figures; assert any unexplained AR variance **blocks** and every other variance is itemized-or-blocks.
5. **Quality floor (FR-015)** — a fixture practice seeded >20% unusable is **held** out of shadow-mode with the gap itemized; a category-lopsided practice (financials reconcile, clinical thin) is held category-aware (edge case).
6. **Invisible-adoption red-team (SC-006)** — run a full synthetic batch; scan for any staff login/training/dashboard/notification/identity; assert **zero**; assert the clinician-in-export edge case provisions no staff surface.
7. **Identity handoff (SC-008)** — assert the audit corpus matches 011's consumed shape; every collision/duplicate lands a `pending` `review_queue` row; **0** auto-merges (static assertion: no merge call path, reusing the 011 guard).
8. **Partial→delta (SC-009)** — the partial fixture (attachments omitted) is detected against §5 scope, produces an owner-facing gap notice, proceeds on delivered data **without** being marked complete; the delta fixture re-ingests idempotently (no duplicates) and updates the report.
9. **Batch independence + prior reuse (SC-010, FR-025)** — a blocked practice does not stall the batch; marginal mapping steps trend down as practice N inherits group priors.

---

## Top 3 Technical Risks

1. **Format unknown until Aug 3, against a build that must ship before it** (feasibility, HIGH). Building normalization against a guessed schema is how a migration silently drops financials or mangles identity. *Mitigation*: the pipeline is **format-discovery-driven** — normalization is structurally blocked without a `FormatProfile`, unmapped entities are flagged not dropped, and the ezyVet adapter is built against a **synthetic ezyVet-shaped fixture** with the real-export re-profile as a config swap. The port isolates every PIMS-specific assumption behind discovery so the core never bakes in a schema.
2. **Dirty data → Vera confidently wrong; financial reconciliation that misses** (existential — this is the likeliest near-term killer and the Digitail-beating differentiator). A false "complete" on partial financials is exactly the failure that cost a competitor thousands in dropped open balances. *Mitigation*: **zero AR tolerance** (any unexplained AR variance blocks), financial/AR/inventory completeness is explicit and load-bearing, the **>20% quality floor** holds a practice out of shadow-mode, and reconciliation ties to the source's own reported figures with every variance itemized — all gated on an answer-keyed fixture and, at pilot, the real week-1 data-quality ground-truth audit.
3. **A staff-facing artifact leaks as a side effect** (invisible-adoption breach, reputational/strategic). The clinician-in-export edge case auto-provisioning a login would violate the whole doctrine. *Mitigation*: onboarding provisions **no auth/login/notification path** (the verbs do not exist in the tier), the readiness gate asserts zero staff artifacts, all surfaces are owner/manager-audience-only, and a batch-wide red-team scan asserts **SC-006 = 0** before go-live.

---

## Conflicts: spec vs shipped seams

1. **Canonical-model ownership (the §3.2(h) live tension).** The spec's whole structure rides on the **clinic-owns-its-records** posture: the clinic contracts the §5 request, the clinic populates its own next system, VetAgent develops *for that clinic* — §3.2(h) bans the *partner* from building conversion tooling, not the clinic populating its own canonical model. Resolution in this plan: normalization is **counsel-gated as a hard state-machine guard** (no engineering bypass), public posture stays "orchestrate the stack," and the replacement endgame is never marketed. This is a **legal gate, not a code conflict** — but it is load-bearing enough to be the whole-spec gate.
2. **`entity_ref` keying + identity-corpus shape (handoff to 011).** 011 requires **stable-id keys** (`client:ezyvet_c*`) and consumes a specific audit-corpus shape as its resolver's hard input gate. 009 must produce exactly that shape and **not** drift its own keying. Resolution: 009 reuses `backend/relationship/entity_ref.py` verbatim and freezes the corpus/`review_queue` shape in `contracts/identity-handoff.md`; 009 produces the corpus and groupings, 011 owns the runtime resolver — coordinate at the seam, do not fork the mapper or the queue.
3. **Scope boundary — 009 ends at shadow-ready.** The discover.md frames a four-phase arc (Connect→Shadow→Verb-promotion→Cutover); the spec deliberately scopes 009 to **the on-ramp only** (receipt → shadow-ready). Resolution: 009 defines the **readiness criteria and the shadow-ready state** but not the shadow operation, delta sync, dual-path writes, verb promotion, or the cutover/Replace event (010/011/envelope-MVP). A scope guard, not a conflict — but named so tasks.md does not bleed into the envelope-MVP.

---

## Marketing Output
**Produced by**: speckit-plan — 2026-07-18

### Demo Flow Sketch

**Audience**: Goldsmith group owner + operations manager (and, as an asset, prospective PE-owned multi-site operators / investors).
**Estimated runtime**: ~6 minutes.
**Pre-demo setup**: the synthetic 23-practice ezyVet-shaped batch loaded (one practice seeded partial — attachments omitted; one seeded >20% dirty; one with a planted AR variance); the counsel-gate `signoff` row present; the owner reconciliation rollup open. **No staff surface exists anywhere in the demo** — that is the point.

**Step 1 — The Arrival (chain of custody)**: The group's data copies "arrive." On the owner rollup, all 23 practices appear at `received` — each with a checksum, a delivery timestamp, and a scope-vs-request line (what the §5 letter asked for vs what landed). Nothing has been interpreted yet. One practice already flags: *attachments/imaging missing.*

**Step 2 — The Gate (the part competitors skip)**: Normalization does not start. The rollup shows the counsel gate cleared — *then* the practices advance to `profiled`. Each database was profiled before a single record was mapped; the one unrecognized-variant practice flags for adapter review rather than being force-fit.

**Step 3 — The Reconciliation (the proof)**: We open one practice's reconciliation report: requested vs delivered vs ingested by category — and the trust centerpiece, **financials**: AR balances, invoice totals, payment totals, tied back to the practice's own reported numbers. The planted AR variance is surfaced **red and blocking** — not buried. This is the exact failure ("open client balances didn't transfer — thousands lost") that cost a competitor its customers; here it *cannot* pass silently.

**Step 4 — The Held Practice (honesty)**: The >20%-dirty practice is **held** out of shadow-mode with its gap itemized, and the partial-delivery practice shows an owner-facing gap notice — paper-trail-ready for the reply to the vendor — while still processing everything that *did* arrive. Neither is marked complete. When the missing attachments arrive later as a delta, they merge with no duplicates and the report updates.

**Step 5 — The Payoff (invisible)**: With one **group-level acknowledgment**, the reconciled practices flip to `shadow_ready`. The next practice onboarded reuses the last one's mapping — marginal effort trending toward a paste. And the whole time: **zero logins, zero training, zero cutover, zero staff notifications** — a clinician who appeared in the export got a schedule entry, never an account. Vera already knows each practice, and here is the proof every number reconciles.

**Key talking point**: We meet Digitail's ~1-week bar and close the gap they can't — a reconciliation the owner can trust down to the AR balance — and we do it with **no cutover at the end** and **nothing for staff to learn**, because the counsel gate, the zero-AR-tolerance, and the invisible-adoption guarantee are rails below the pipeline, not a promise we hope holds.
