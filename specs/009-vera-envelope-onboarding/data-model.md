# Data Model — Feature 009 (Vera Envelope Onboarding)

**Authored**: 2026-07-18 (remediation, analyze finding F2). Derived from `spec.md` Key Entities + `plan.md` canonical-model paragraph + the `tasks.md` T002 enum set.

**Datastore**: net-new onboarding-control tables + net-new canonical financial/AR/ledger/payment + inventory tables run on **local PostgreSQL via `docker-compose`** (`vetagent-voice-pg`, host port **5433**, `VOICE_DATABASE_URL`; R8). **FORCE-RLS (SEC-20)** on every onboarding-control table; app-level `clinic_id`/`practice_id` scoping stands in for full RLS in the single-clinic build. Provisioning **wraps the full transaction** (no orphan-receipt rows). **Not SQLite** — the demo repo's SQLite is not used for the envelope plane.

**Model file**: all entities below are **Pydantic models appended to `backend/models.py`** (010/011 single-file precedent — there is **no** separate `canonical_model.py`, per finding F1). `init_db()` + raw SQL live in `backend/envelope/onboarding_repository.py` (HouseholdRepository/VoiceRepository pattern), not in the model file.

**Scoping key**: onboarding-control and canonical tables are **practice-scoped** on `practice_id` (plus `clinic_id` tenant scope). The 23 practices are independent units; a `practice_id` isolates one practice's receipt/normalization/verification/reconciliation/readiness rows.

---

## Enums (T002)

| Enum | Members |
|---|---|
| `practice_state` | `received` · `profiled` · `normalized` · `verified` · `reconciled` · `identity_bootstrapped` · `shadow_ready` · `blocked` · `partial` · `held` · `delta` |
| `scope_category` | `patient_client` · `scheduling` · `invoicing_billing_payments` · `communications` · `attachments_imaging` · `configuration` |
| `variance_disposition` | `explained` · `blocking` |
| `readiness_criterion` | `counsel_cleared` · `format_discovered` · `normalization_idempotent` · `completeness_quality_above_floor` · `reconciliation_acknowledged` · `identity_corpus_produced` |

`practice_state`: the linear happy path is `received → profiled → normalized → verified → reconciled → identity_bootstrapped → shadow_ready`; `blocked`/`partial`/`held`/`delta` are **first-class** off-path states (a practice may sit at any of them without stalling the batch and never auto-advances to `shadow_ready`). Enforced by the state machine (T006), the single write path.

---

## Onboarding-control tables

All carry `id` (uuid), `clinic_id`, `practice_id` (except `Delivery`/`BatchRollup`, which are group-scoped), `created_at`. Audit tables are **append-only** (UPDATE/DELETE rejected).

### Delivery — chain-of-custody anchor (group-scoped; append-only)
One received export bundle. `source`, `delivery_timestamp`, `byte_count`, `checksum`, `practice_ids` (list). The §6.3 backup-compliance artifact. (FR-001; spec US1)

### PracticeDatabase
One practice's export within a delivery. `delivery_id`, `practice_id`, `receipt_state`, `state` (`practice_state`), `vault_object_ref`, `checksum`. The per-practice pipeline row the state machine advances. (FR-001; US1/US7)

### ChainOfCustody (append-only)
Per received database: `practice_database_id`, `source`, `delivery_timestamp`, `byte_count`, `checksum`, `vault_written_at`, `parsed` (bool, must be false at write time). Proof of "captured before touched." (FR-001, SC-001; T009/T036)

### CounselSignoff (append-only)
`signed_by`, `signed_at`, `structure_version`, `scope`. The hard pre-normalization gate row — its **presence** is the guard `received → profiled/normalized` checks (FR-004, §3.2(h)). No engineering bypass. (T011)

### ScopeCheck
`practice_database_id`, per-`scope_category` disposition (`present` / `absent` / `short`), computed against `config/envelope/section5_scope.yaml`. Feeds partial-delivery detection. (FR-002; T010)

### FormatProfile
Machine-readable discovery result: `practice_database_id`, `entities` (name → record_count), `encodings`, `referential_relationships`, `export_variant`, `unmapped_flags`. **Normalization is blocked without this row** (FR-005/006). (T013/T014)

### StateTransition (append-only)
`practice_id`, `from_state`, `to_state`, `reason`, `at`. One row per transition; the append-only audit spine and the single write path. (T006)

### CompletenessResult
`practice_id`, per-`scope_category` coverage + `count_vs_profile`, `referential_integrity_findings`, and the **financial block**: `ar_balance_total`, `invoice_count`, `payment_total`. Flags missing/short categories. (FR-012/013; T021)

### QualityAssessment
`practice_id`, dirty-data counts (`shared_phones`, `duplicate_owners`, `deceased_pets`, `orphaned_refs`, `malformed`), `usable_record_share`, `below_floor` (bool; `> 0.20` unusable → true). Config: `quality_thresholds.yaml`. (FR-014/015; T022/T023)

### ReconciliationReport (append-only; owner-facing)
`practice_id`, per-`scope_category` requested/delivered/ingested counts, financial reconciliation (`ar_variance`, `invoice_variance`, `payment_variance` each with `variance_disposition` + `attributed_cause`), `outstanding_gap`, `owner_acknowledged` (group-level ack). **Zero AR tolerance**: any unexplained `ar_variance` → `blocking`. Owner/manager audience only. (FR-016/017/018; T024–T027)

### IdentityAuditCorpus (append-only)
`practice_id`, household/party grouping `proposals` (each with `entity_ref` lineage), `collisions`, `answer_key_scored_precision` (single-match vs multi-match, build-time). **009-defined seam** — frozen in `contracts/identity-handoff.md` as the proposed input gate for 011 to adopt (011 specifies the audit as a gating *activity*, not yet a consumed *schema*; finding F5). No runtime auto-ID/soft-confirm here. (FR-019/020; T028–T030)

### GapNotice (append-only; owner-facing)
`practice_id`, missing `scope_category` set, paper-trail-ready text for the vendor reply. Produced on any detected §5-scope gap; the practice proceeds but is **not** marked complete. (FR-030/031; T034)

### PracticeReadiness
`practice_id`, per-`readiness_criterion` satisfied flags, `shadow_ready` (bool — true only when **all** criteria met), `invisible_adoption_asserted` (bool — no staff artifact emitted). Defines the readiness criteria, not the shadow operation. (FR-022/023/028; T031/T032)

### BatchRollup (group-scoped; computed view)
Group-level view over the per-practice `PracticeDatabase`/`PracticeReadiness` rows — every practice's stage/status. A blocked practice is visible but never stalls the batch. (FR-024; T033)

### ReviewItem → **reused `HouseholdReviewQueue`, NOT a net-new model** (finding F7)
The spec's "ReviewItem" Key Entity is the conceptual name for the **already-shipped** `HouseholdReviewQueue` (011 T012, in `backend/models.py`). 009 writes collisions/probable-duplicates to it via `backend/relationship/review_queue.py` `propose_grouping(... status="pending")` **reused verbatim** — the never-auto-merge write path. **Do not author a new model.** See Reused-artifact seams below. (FR-021; T028)

---

## Net-new canonical practice-model tables (financial/AR/ledger/payment + inventory)

The canonical clinical/scheduling entities (`Owner`/`Patient`/appointments/providers/…) already exist on the platform practice model; 009 **hydrates** them. The net-new tables 009 adds where absent, every row carrying `source_id` + `entity_ref` lineage (FR-008/009):

| Table | Key fields | Purpose |
|---|---|---|
| `LedgerEntry` | `practice_id`, `entity_ref`, `source_id`, `account_ref`, `amount`, `entry_type`, `posted_at` | The financial transaction spine (invoices/adjustments/credits) |
| `InvoiceRecord` | `practice_id`, `entity_ref`, `source_id`, `client_ref`, `total`, `status`, `issued_at` | Invoice history — the reconciliation invoice-count/total source |
| `PaymentRecord` | `practice_id`, `entity_ref`, `source_id`, `client_ref`, `amount`, `method`, `received_at` | Payment history — reconciliation payment-total source |
| `ARBalance` | `practice_id`, `entity_ref`, `source_id`, `client_ref`, `balance`, `as_of` | Open client balances — the **zero-tolerance** reconciliation target (the Digitail gap) |
| `InventoryItem` | `practice_id`, `entity_ref`, `source_id`, `product_ref`, `qty_on_hand`, `unit`, `last_counted_at` | Inventory history — completeness coverage |
| `UnmappedFieldSidecar` | `practice_id`, `entity_ref` (owning record), `source_field`, `raw_value` | Preserves source fields with no canonical mapping — **never silently dropped** (FR-008 US3-scenario-3; T020) |

**Lineage**: every canonical record carries a non-nullable `entity_ref` seeded via `backend/relationship/entity_ref.py` (`client:ezyvet_c*`, `patient:ezyvet_p*`, `household:vah_*`, `staff:*`, `clinic:*`) + a `source_id` back to the source export row. `entity_ref` keys are the byte-identical handoff to 011 — **names never in the key** (entity_ref.py contract). Idempotent upsert keys on deterministic `source_id` (FR-010; re-run → 0 duplicates).

**Staff-as-data-only** (FR-028): a `staff:*` canonical row may be created for scheduling/attribution, but **no auth/login/notification path is reachable from onboarding code** — the provisioning verbs do not exist in this tier. The readiness gate (T032) rejects any run that emitted a staff credential/training/dashboard/notification.

---

## Reused-artifact seams (extract, don't fork)

| Shipped artifact | 009 use | Seam note |
|---|---|---|
| `backend/relationship/entity_ref.py` | Seeds `source_id`/`entity_ref` on every canonical record | Reused verbatim; `{type}:{stable_id}`, names never in key |
| `backend/models.py` `HouseholdReviewQueue` + `backend/relationship/review_queue.py` | The collision / probable-duplicate sink (spec "ReviewItem") | **Clinic-scoped by column — no `practice_id`.** 009 is practice-scoped and must **not** fork the module: carry `practice_id` inside `evidence_json`/`subject_refs` (both open JSON on the model) so per-practice attribution + reconciliation drill-down work without a schema change (finding F6). `propose_grouping` is the only write path; no merge path exists (the 011 guard). |
| `backend/relationship/household_repository.py` `init_db()` pattern | The persistence pattern for 009's net-new tables | Postgres/5433, append-only audit spine, FORCE-RLS added |
| `backend/scripts/generate_avimark_fixture.py` | Pattern for the synthetic ezyVet-shaped export fixture (T005) | Seeded/reproducible ZIP-of-CSVs precedent |

---

## Handoff contracts (frozen under `contracts/`)
- `pims-adapter-port.md` (T017) — the `FormatProfile` + canonical-records-plus-lineage return shape + registry.
- `reconciliation-report.md` (T027) — requested/delivered/ingested-by-category + financial-reconciliation + group-ack/drill-down shape.
- `identity-handoff.md` (T030) — the `entity_ref` keying + `IdentityAuditCorpus` + `HouseholdReviewQueue` shape; **009-defined**, proposed as 011's resolver input gate (finding F5).
