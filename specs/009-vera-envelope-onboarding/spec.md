# Feature Specification: Vera Envelope Onboarding — "Vera's First Day"

**Feature Branch**: `009-vera-envelope-onboarding`

**Created**: 2026-07-18

**Status**: Draft

**Input**: User description: "When a practice group adopts Vera alongside its existing PIMS, the group's own complete data copies arrive by written customer request, and Vera turns them into a running envelope — ingested, normalized to the canonical practice model, verified complete (including financials/AR/inventory), reconciled in a report the owner can trust, identity-bootstrapped, and shadow-ready — without the staff ever experiencing 'new software.' What works for 23 ezyVet clinics must generalize to N practices across heterogeneous PIMS, so per-PIMS ingest adapters are pluggable."

---

## Problem Statement

The Goldsmith pilot's §5 written data-copy request was **submitted 2026-07-18**. Under the One IDEXX Master Terms (ezyVet Offering Terms §5), complete copies of Customer Data for **23 practice databases** will be delivered by secure file transfer within **ten business days (~Aug 3)**; pilot kickoff is the first week of August. The **format is unknown until delivery** — "your standard complete-export format" per the letter — and partial exports (e.g., attachments/imaging omitted) are a documented risk.

This spec defines the pipeline that converts that delivery into a running Vera envelope: **data receipt → verified live envelope, shadow-ready.** It is *not* the ongoing envelope operations (delta sync, write verbs, cutover) — those are specs 010/011 and the envelope-MVP. It is the on-ramp: chain-of-custody receipt, format discovery, ingest/normalization to the canonical model, completeness-and-quality verification (financials included), a reconciliation report the owner can trust, identity/`entity_ref` bootstrapping that hands off to 011's verification tiers, and the criteria that mark a practice shadow-ready — all under a hard invisible-adoption constraint (no staff-facing events) and designed so the ezyVet path generalizes to N practices across mixed PIMS.

The competitive bar is explicit: Digitail markets a "Test Playground" sandbox on the clinic's real data in **~1 week** with **4–6 weeks of hypercare**. Their published weakness — and the worst story on record against them — is migration that **does not promise financial/AR history** ("open client balances didn't transfer — thousands in lost revenue"). This spec must meet or beat the ~1-week bar **and** close the financial gap with a reconciliation the owner can trust — with the twist that ours has no cutover at the end.

---

## Clarifications

### Session 2026-07-18

- Q: What is the staff-facing footprint of onboarding? → A: **Zero.** Onboarding produces no logins, no training, no cutover, no staff notifications, no dashboards pushed at staff. All surfaces (reconciliation reports, readiness views) are owner/manager-only, per the Invisible Adoption Doctrine (Working Rule 0). Success is that staff experience nothing.
- Q: What legal basis authorizes building the native canonical model from the exports, and is there a gate? → A: The **clinic's statutory ownership of its own records**, exercised via the §5 request; §6.3 (customer solely responsible for backups) makes a continuous clinic-owned vault contract-compliant. §3.2(h) bans the *partner* from building conversion tooling — not the clinic populating its own next system. **Counsel sign-off on the clinic-owned-data structure is a hard gate before the first record is ingested.**
- Q: Does the pipeline assume a known export format? → A: **No.** Format is unknown until delivery (~Aug 3). A format-discovery stage profiles each delivered database before any normalization runs; ingest adapters are **per-PIMS/per-format and pluggable** — ezyVet is the first adapter, and the port is designed for the mixed-PIMS ICP.
- Q: Must completeness verification include financials/AR/inventory, or only clinical/scheduling? → A: **Financials are in scope and load-bearing.** Verification and the reconciliation report cover financial, AR, and inventory history explicitly — this is Digitail's published gap and the owner-trust differentiator.
- Q: What is the unit of onboarding — the group or the practice? → A: The **practice** is the independent ingest, verification, reconciliation, and activation unit; the 23 practices are processed as a **batch** with a group-level rollup. A blocked practice never holds the batch, and practice N inherits group-level mappings/priors.

*Open product questions are marked `[NEEDS CLARIFICATION]` inline in the requirements below.*

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Data Arrives and Is Received Under Chain of Custody (Priority: P1)

The group's complete data copies arrive by secure file transfer — one export per practice database, in ezyVet's standard complete-export format. Each delivery is received into a clinic-owned encrypted vault, fingerprinted (checksum), timestamped, attributed to its source delivery, and checked against the exact scope the §5 letter requested — before any interpretation happens. Nothing is processed until it is provably captured.

**Why this priority**: Everything downstream depends on a trustworthy, auditable receipt. The vault is the §6.3 backup-compliance artifact and the chain-of-custody spine; if receipt is not provable, no reconciliation or completeness claim can be trusted.

**Independent Test**: Deliver a sample export bundle; verify each database file is stored in the vault with a checksum, receipt timestamp, source attribution, and a scope-vs-request record listing which requested categories are present, with no normalization yet performed.

**Acceptance Scenarios**:

1. **Given** an incoming delivery, **When** it is received, **Then** each database export is written to the clinic-owned vault encrypted at rest, with a persisted chain-of-custody record (source, delivery timestamp, byte-count, checksum) before any parsing runs.
2. **Given** a received bundle, **When** receipt completes, **Then** a scope-vs-request record is produced comparing delivered contents against the §5 letter's enumerated scope (patient/client records, scheduling, invoicing/billing/payments, communications, attachments/imaging, configuration).
3. **Given** any raw PII passes through an extraction subprocessor (e.g., Gemini for parsing/vision), **When** it is processed, **Then** no raw source content or screen frames are retained by the subprocessor and the DPA/no-retention posture is honored.

---

### User Story 2 — Format Discovery Before Normalization (Priority: P1)

Because the export format is unknown until it lands, the pipeline first **profiles** each delivered database — file types, encodings, table/entity schemas, record counts, referential structure, and the ezyVet complete-export variant — and produces a machine-readable format profile. Only after a database is profiled does normalization run against it, driven by the pluggable ezyVet adapter.

**Why this priority**: Guessing the schema is how a migration silently drops financials or mangles identities. Format discovery is the stage that makes the pipeline robust to "format unknown until Aug 3" and is the seam where a second PIMS adapter plugs in.

**Independent Test**: Feed a database whose schema is not hard-coded; verify the discovery stage emits a format profile (entities, counts, encodings, relationships) and that normalization refuses to run against a database with no profile.

**Acceptance Scenarios**:

1. **Given** a received database of unknown internal format, **When** discovery runs, **Then** it emits a format profile enumerating entities, record counts, encodings, and referential relationships, and identifies the export variant.
2. **Given** a database with no completed format profile, **When** normalization is attempted, **Then** it is blocked until a profile exists.
3. **Given** a profile that a known adapter cannot fully map, **When** discovery completes, **Then** unmapped entities/fields are flagged for review rather than silently dropped.

---

### User Story 3 — Normalize to the Canonical Practice Model with Full Lineage (Priority: P1)

Each profiled database is normalized into VetAgent's canonical practice model — providers, resources, appointment types, clients/households, patients, appointments, invoices/ledger/payments, inventory, client communications, attachments/documents, and product/service lists. **Every** normalized record carries `source_id`/`entity_ref` lineage back to its source export, so every fact Vera later states can be traced (claim discipline extended to runtime). Ingest is deterministic, re-runnable, and idempotent.

**Why this priority**: The canonical model is what Vera reasons over and what continuously populates the native practice model (the migration, amortized invisibly). Without lineage, no insight is verifiable; without idempotency, a re-run corrupts the store.

**Independent Test**: Normalize a database twice; verify identical output (no duplicates), and that every canonical record resolves back to a specific source record via its `entity_ref`/`source_id`.

**Acceptance Scenarios**:

1. **Given** a profiled database, **When** normalization runs, **Then** source entities map to the canonical model and each canonical record persists a `source_id`/`entity_ref` to its origin.
2. **Given** a database that has already been ingested, **When** ingest runs again, **Then** the result is idempotent — no duplicate records and stable identifiers.
3. **Given** a source field with no canonical mapping, **When** normalization runs, **Then** it is preserved/flagged as unmapped, never silently discarded.

---

### User Story 4 — Completeness and Quality Verification, Financials Included (Priority: P1)

Before a practice is called ready, the pipeline verifies the ingested data is **complete** (all requested categories present, record counts and referential integrity intact) and assesses **quality** (dirty-data signals — shared phones, duplicate owners, deceased pets, malformed records). Completeness explicitly covers **financial, AR, and inventory history**, not just clinical and scheduling. A per-practice completeness-and-quality result gates readiness.

**Why this priority**: "Dirty data → Vera confidently wrong" is the likeliest near-term killer, and the data-quality audit is the pilot week-1 ground-truth gate. Financial completeness is the specific bar that beats Digitail's open-balance failure.

**Independent Test**: Run verification on a practice's ingested data; verify it reports category coverage (including financial/AR/inventory), record counts vs the source profile, referential-integrity gaps, and a dirty-data quality assessment, and that a practice below the data-quality floor is not marked shadow-ready.

**Acceptance Scenarios**:

1. **Given** a normalized practice, **When** verification runs, **Then** it confirms presence and counts for every requested category — clinical, scheduling, client communications, **and financial/AR/inventory** — and flags any missing or short category.
2. **Given** ingested financial data, **When** verification runs, **Then** AR balances, invoice counts, and payment totals are computed for reconciliation against the source's own reported figures (User Story 5).
3. **Given** dirty-data signals (shared phones, duplicate owners, deceased pets, orphaned references), **When** verification runs, **Then** they are quantified into a per-practice quality assessment.
4. **Given** a practice whose usable-record share is below the data-quality floor `[NEEDS CLARIFICATION: the completeness/quality floor that gates shadow-readiness — board kill-criterion suggests >20% of sampled records unusable = stop; confirm the per-practice activation threshold]`, **When** activation is evaluated, **Then** the practice is held out of shadow-mode with the gap itemized.

---

### User Story 5 — A Reconciliation Report the Owner Can Trust (Priority: P1)

For each practice, the pipeline produces an **owner/manager-facing reconciliation report**: what was requested vs delivered vs ingested; record counts by category; and — the trust centerpiece — **financial reconciliation** (AR balance totals, invoice and payment totals) tied back to the source system's own reported figures, with any variance itemized. This is the artifact that lets the owner trust the envelope without living through a migration.

**Why this priority**: Reviewability sells (Digitail markets "AI Interaction Audit"), and the reconciliation report is the owner's proof that nothing was lost — directly answering the failure that cost a competitor's customers thousands in dropped open balances. It is also the only trust surface allowed to exist during onboarding (owner-only).

**Independent Test**: Generate the report for a practice; verify it shows requested-vs-delivered-vs-ingested counts per category and a financial reconciliation (AR/invoices/payments) with variances itemized, and that it is surfaced only to owner/manager audiences.

**Acceptance Scenarios**:

1. **Given** a verified practice, **When** the report is generated, **Then** it presents per-category requested-vs-delivered-vs-ingested counts and a financial reconciliation (AR balances, invoice totals, payment totals) against the source's reported figures.
2. **Given** a financial variance, **When** it exceeds the acceptable tolerance `[NEEDS CLARIFICATION: acceptable financial-reconciliation variance/tolerance before a practice is blocked vs merely flagged]`, **Then** it is surfaced as a blocking discrepancy, not buried.
3. **Given** the report, **When** it is delivered, **Then** it reaches only owner/manager surfaces — never staff — and requires owner acknowledgment before the practice is activated `[NEEDS CLARIFICATION: is reconciliation sign-off per-practice or a single group-level approval across all 23+ practices?]`.

---

### User Story 6 — Identity Bootstrapping That Hands Off to 011 (Priority: P2)

Onboarding bootstraps identity: it seeds `entity_ref`/`source_id` lineage, runs initial household/party resolution **proposals** over the real export, and produces the **real-export identity audit corpus** that spec 011's resolver and verification tiers consume. It never auto-merges — collisions and probable duplicates are queued for review, and automatic identification is deferred to 011's runtime tiers. **Consistent with the invisible-adoption constraint, the review queue surfaces to owner/manager during onboarding (or defers to 011's runtime resolution through existing channels) — onboarding creates no staff-facing queue.**

**Why this priority**: 011's resolver is explicitly *gated on a real-export identity audit before it is trusted for auto-ID*. This story produces that audit and the initial groupings; it is the substrate handoff, not the runtime identity engine.

**Independent Test**: Run identity bootstrapping over a practice's ingested clients; verify it emits household/party grouping proposals with lineage, routes collisions/probable-duplicates to the staff review queue, performs zero silent merges, and produces an identity audit corpus in the shape 011 consumes.

**Acceptance Scenarios**:

1. **Given** ingested client/patient data, **When** identity bootstrapping runs, **Then** it proposes household/party groupings with full lineage and produces an identity audit corpus for 011.
2. **Given** colliding or probable-duplicate records (shared phones, ex-spouses, duplicate owners), **When** they are detected, **Then** they are routed to the review queue (owner/manager-surfaced during onboarding, or deferred to 011's runtime channels) and **never** silently merged.
3. **Given** the bootstrap output, **When** 011's resolver/verification tiers consume it, **Then** the handoff is via the agreed audit-corpus/`entity_ref` shape — this spec does not implement runtime auto-ID, soft-confirm, or the verification bar (those are 010/011).

---

### User Story 7 — Multi-Practice Batching and a Pluggable Per-PIMS Port (Priority: P2)

The 23 practices are processed as a batch of independent units, each with its own receipt, discovery, normalization, verification, reconciliation, and activation state. A group-level rollup shows every practice's progress. Practice N inherits group-level mappings/priors so marginal onboarding cost trends toward config reuse. The ingest path is a **pluggable per-PIMS adapter port** — ezyVet is the first adapter — so the same core generalizes to the mixed-PIMS estates of the 100–400-practice ICP.

**Why this priority**: The ICP decision (2026-07-18) is large multi-site operators with heterogeneous PIMS. What works for 23 ezyVet clinics must scale to N practices across many PIMS without forking the core.

**Independent Test**: Run a batch of multiple practice databases; verify each advances independently through the pipeline stages, a group rollup reflects per-practice state, a blocked practice does not stall the others, and normalization is driven through a per-PIMS adapter behind a stable port.

**Acceptance Scenarios**:

1. **Given** a batch of practice databases, **When** the pipeline runs, **Then** each practice progresses independently and a group-level rollup shows every practice's stage/status.
2. **Given** one practice blocked (partial delivery or quality-floor failure), **When** the batch proceeds, **Then** unblocked practices still reach shadow-ready — the batch is not held to its slowest member.
3. **Given** the normalization core, **When** a new PIMS is targeted, **Then** support is a new adapter behind the stable port — no fork of the orchestration/verification core. `[NEEDS CLARIFICATION: which second PIMS adapter is built first, and on what timeline, to prove the port for the mixed-PIMS ICP — discovery's cycle no-go was "design the port, build one adapter"; the ICP shift may bring a second adapter forward.]`

---

### User Story 8 — Partial or Failed Delivery Never Passes as Complete (Priority: P2)

ezyVet partial exports (e.g., missing attachments/imaging) are a known risk. When delivery is incomplete against the §5 request, the pipeline **detects** the gap, produces an owner-facing gap notice suitable for the paper-trail reply to ezyVet (per the letter's internal notes), proceeds with what did arrive, and re-ingests the remainder as a delta when it lands — never marking an incomplete practice as fully complete.

**Why this priority**: Silently treating a partial export as complete is exactly the failure that loses financial history. Detection + paper trail + graceful partial-then-delta is the disciplined response the pilot's legal posture requires.

**Independent Test**: Deliver an export missing a requested category (e.g., attachments); verify the gap is detected against the §5 scope, an owner-facing gap notice is produced, the practice proceeds with the delivered categories but is not marked fully complete, and a later delta delivery of the missing category is ingested and reconciled without duplicating existing records.

**Acceptance Scenarios**:

1. **Given** a delivery missing a requested category, **When** receipt/verification runs, **Then** the gap is detected against the §5 scope and an owner-facing gap notice (paper-trail-ready) is produced.
2. **Given** a partial delivery, **When** the pipeline proceeds, **Then** the practice is processed on the delivered data but is **not** marked complete, and its reconciliation report shows the outstanding gap.
3. **Given** a later delta delivery of the missing data, **When** it is ingested, **Then** it merges idempotently (no duplicates) and the reconciliation report updates.

---

### Edge Cases

- **Duplicate or overlapping deliveries** (the same practice sent twice, or an export superseding an earlier one) → resolved by chain-of-custody + idempotent ingest; the later export is reconciled against the earlier, not blindly re-loaded.
- **Corrupt, truncated, or unreadable export** → fails at receipt/discovery with a specific error; never partially normalized into the canonical store.
- **Schema drift between practices** (the 23 databases are not byte-identical; per-practice config differences) → each database is profiled independently; a group mapping is a prior, not an assumption.
- **A practice's financials reconcile but clinical data is thin** (or vice versa) → readiness is category-aware; a practice can be financially reconciled yet held for a clinical-completeness gap.
- **Delivered format is not the expected ezyVet complete-export variant** → discovery flags an unrecognized variant for adapter work rather than forcing a wrong mapping.
- **Counsel gate not yet cleared when data arrives** → data may be received into the clinic-owned vault (backup/§6.3), but **no normalization into the native canonical model** begins until counsel sign-off is recorded.
- **A staff-facing artifact would be produced as a side effect** (e.g., an auto-provisioned login for a clinician found in the export) → suppressed; onboarding provisions no staff identities or surfaces.

---

## Requirements *(mandatory)*

### Functional Requirements

**Data Receipt & Chain of Custody**
- **FR-001**: The system MUST receive each delivered practice database into a **clinic-owned, encrypted-at-rest vault** and persist a chain-of-custody record (source, delivery timestamp, byte-count, checksum) before any parsing or normalization.
- **FR-002**: The system MUST record a **scope-vs-request** result for each delivery, comparing delivered contents against the §5 letter's enumerated categories (patient/client records, scheduling, invoicing/billing/payments, client communications, attachments/imaging, configuration).
- **FR-003**: Any extraction subprocessor that touches raw source PII (e.g., Gemini) MUST operate under a **no-retention** posture (no raw content or screen frames retained), consistent with the DPA obligations.
- **FR-004**: No normalization into the native canonical model MUST begin until **counsel sign-off on the clinic-owned-data structure** is recorded — a hard gate (§3.2(h) posture). Receipt into the vault (a §6.3 backup) is permitted before the gate.

**Format Discovery**
- **FR-005**: The system MUST **profile** each received database (entities, record counts, encodings, referential relationships, export variant) and emit a machine-readable format profile before normalizing it.
- **FR-006**: Normalization MUST be **blocked** for any database lacking a completed format profile.
- **FR-007**: Entities or fields a known adapter cannot map MUST be **flagged for review**, never silently dropped.

**Ingest & Normalization (Canonical Model)**
- **FR-008**: The system MUST normalize each profiled database into the canonical practice model: providers, resources, appointment types, clients/households, patients, appointments, invoices/ledger/payments, inventory, client communications, attachments/documents, and product/service lists.
- **FR-009**: Every normalized record MUST carry `source_id`/`entity_ref` **lineage** back to its source record (runtime claim-discipline).
- **FR-010**: Ingest MUST be **deterministic and idempotent** — re-running against the same source produces no duplicates and stable identifiers.
- **FR-011**: Normalization MUST populate the native canonical practice model such that the migration is amortized continuously; this spec covers the **initial bulk load only** — continuous delta sync, dual-path writes, and cutover are out of scope (010/011/envelope-MVP).

**Completeness & Quality Verification**
- **FR-012**: The system MUST verify **completeness** per practice — category coverage and record counts vs the format profile, and referential integrity — and flag any missing or short category.
- **FR-013**: Completeness verification MUST explicitly cover **financial, AR, and inventory** history, computing AR balance totals, invoice counts, and payment totals for reconciliation.
- **FR-014**: The system MUST assess **data quality** per practice, quantifying dirty-data signals (shared phones, duplicate owners, deceased pets, malformed/orphaned records) into a quality result.
- **FR-015**: A practice below the data-quality floor MUST NOT be marked shadow-ready `[NEEDS CLARIFICATION: the exact completeness/quality floor gating shadow-readiness]`.

**Reconciliation Reporting (owner-facing)**
- **FR-016**: The system MUST produce a per-practice **reconciliation report** showing requested-vs-delivered-vs-ingested counts by category and a **financial reconciliation** (AR balances, invoice totals, payment totals) against the source system's own reported figures, with variances itemized.
- **FR-017**: A financial variance exceeding tolerance MUST be surfaced as a **blocking discrepancy** `[NEEDS CLARIFICATION: acceptable financial-reconciliation tolerance]`.
- **FR-018**: The reconciliation report MUST reach **owner/manager surfaces only** and MUST require owner acknowledgment before a practice is activated `[NEEDS CLARIFICATION: per-practice vs group-level sign-off granularity]`.

**Identity / entity_ref Bootstrapping (handoff to 011)**
- **FR-019**: The system MUST seed `entity_ref`/`source_id` identity lineage and produce initial **household/party grouping proposals** over the real export.
- **FR-020**: The system MUST produce the **real-export identity audit corpus** in the shape spec 011's resolver and verification tiers consume; this spec MUST NOT implement runtime auto-ID, soft-confirm, or the verification bar (011).
- **FR-021**: Colliding or probable-duplicate records MUST be routed to a **review queue** and MUST NEVER be silently merged. During onboarding the queue MUST surface to owner/manager only (or defer to 011's runtime resolution through existing channels) — creating a staff-facing queue would violate FR-028.

**Shadow-Mode Activation**
- **FR-022**: A practice MUST be marked **shadow-ready** only when: counsel gate cleared, format discovery complete, normalization idempotent, completeness/quality above the floor, reconciliation report produced and acknowledged, and identity bootstrap corpus produced.
- **FR-023**: Shadow-readiness MUST be tracked as an explicit per-practice state; this spec defines the **readiness criteria**, not the shadow operation itself (advise-mode receipts are downstream).

**Multi-Practice Batching & Per-PIMS Adapters**
- **FR-024**: Each practice MUST be an **independent** unit through every stage, with a **group-level rollup** of per-practice status.
- **FR-025**: A blocked practice MUST NOT stall the batch — unblocked practices MUST still reach shadow-ready.
- **FR-026**: Practice N MUST be able to **inherit group-level mappings/priors** so marginal onboarding cost trends to config reuse.
- **FR-027**: Ingest MUST be structured as a **pluggable per-PIMS adapter behind a stable port**; ezyVet is the first adapter and the core MUST NOT be forked per PIMS `[NEEDS CLARIFICATION: first non-ezyVet adapter + timeline]`.

**Invisible Adoption Constraint**
- **FR-028**: Onboarding MUST produce **zero staff-facing artifacts** — no staff logins, training, dashboards, or notifications. It MUST provision no staff identities even when clinicians appear in the export.
- **FR-029**: All onboarding surfaces (reconciliation reports, readiness rollups) MUST be **owner/manager-only**.

**Failure / Partial-Delivery Handling**
- **FR-030**: Partial or incomplete deliveries MUST be **detected** against the §5 scope and MUST NEVER be marked fully complete.
- **FR-031**: On a detected gap, the system MUST produce an **owner-facing gap notice** suitable for the paper-trail reply to the vendor (per the letter's internal notes).
- **FR-032**: The pipeline MUST **proceed on delivered data** while a gap is outstanding, and MUST ingest a later **delta** delivery idempotently, updating the reconciliation report.
- **FR-033**: Corrupt, truncated, or unreadable exports MUST fail at receipt/discovery with a specific error and MUST NOT be partially normalized into the canonical store.

### Key Entities

- **Delivery**: One received export bundle — source, timestamp, checksum, byte-count, and the practices it contains; the chain-of-custody anchor.
- **PracticeDatabase**: One practice's export within a delivery — its receipt state and processing state through the pipeline.
- **FormatProfile**: The machine-readable result of discovery for a database — entities, counts, encodings, referential structure, export variant.
- **CanonicalRecord**: A normalized entity in the practice model (provider, client/household, patient, appointment, invoice/payment, inventory item, communication, document, product/service) carrying `source_id`/`entity_ref` lineage.
- **CompletenessResult**: Per-practice category coverage, counts vs profile, referential-integrity findings — including the financial/AR/inventory checks.
- **QualityAssessment**: Per-practice dirty-data quantification (shared phones, duplicates, deceased pets, orphans) and usable-record share.
- **ReconciliationReport**: The owner-facing artifact — requested/delivered/ingested counts by category and financial reconciliation (AR/invoices/payments) with itemized variances; requires owner acknowledgment.
- **IdentityAuditCorpus**: The real-export identity output (household/party grouping proposals + collisions) handed to 011; the input to its gated resolver.
- **ReviewItem**: A collision/probable-duplicate routed for human review (owner/manager-surfaced during onboarding); never auto-merged (011 mechanism at runtime).
- **GapNotice**: The owner-facing, paper-trail-ready record of a partial-delivery gap against the §5 request.
- **PracticeReadiness**: The explicit per-practice shadow-ready state and the criteria satisfied to reach it.
- **BatchRollup**: The group-level view of every practice's stage/status.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of delivered practice databases are received into the clinic-owned vault with a complete chain-of-custody record (source, timestamp, checksum, scope-vs-request) before any parsing.
- **SC-002**: 100% of received databases are profiled (format profile emitted) before normalization; 0 databases are normalized without a profile.
- **SC-003**: 100% of canonical records carry `source_id`/`entity_ref` lineage, and re-running ingest produces 0 duplicate records (idempotency proven).
- **SC-004**: Completeness verification covers clinical, scheduling, communications, **and financial/AR/inventory** for 100% of practices; financial totals are reconciled to the source's reported figures or the variance is itemized in the report.
- **SC-005**: A reconciliation report is produced and delivered to owner/manager for 100% of practices before each is marked shadow-ready.
- **SC-006**: **0** staff-facing artifacts (logins, training, dashboards, notifications) are produced by onboarding — the invisible-adoption bar, verified.
- **SC-007**: **First practice shadow-ready within ~1 week of data receipt** (meeting/beating Digitail's ~1-week Test Playground), and the full batch reconciled within the ~4–6-week hypercare-equivalent window — **with no cutover at the end**.
- **SC-008**: Identity bootstrapping produces the real-export identity audit corpus 011 consumes, with **0 auto-merges** (100% of collisions/duplicates routed to staff review).
- **SC-009**: 100% of partial/incomplete deliveries are detected (0 silently accepted as complete) and produce an owner-facing gap notice.
- **SC-010**: Per-practice marginal onboarding effort decreases across the batch as practice N reuses group-level mappings/priors (measured: setup/mapping steps per practice trending down; target approaching config-reuse only).

---

## Non-Goals (this cycle)

- **Ongoing envelope operations** — continuous delta sync, dual-path writes, the shadow-receipt/advise engine, verb promotion, and the Phase-D cutover/Replace event (010/011/envelope-MVP). This spec ends at *shadow-ready*.
- **Runtime identity** — auto-ID, soft-confirm, the tiered verification bar, and consent/opt-out (011). This spec only produces the audit corpus and groupings it consumes.
- **Any write verb** to the source PIMS; anything touching diagnostics ordering or controlled substances; browser automation as a primary receipt path (the §5 request is the front door, not the API).
- **Building multiple PIMS adapters this cycle** — the port MUST be pluggable and the second adapter is scoped, but only ezyVet is built here (pending the clarification above).
- **Marketing the integration** publicly or writing the replacement endgame into client-facing material (ToS §4.1 posture / Working Rules 1–2).
- **Staff-facing onboarding UI** of any kind.

---

## Assumptions & Dependencies

- **Counsel sign-off** on the clinic-owned-data structure is a **hard gate** before the first record is normalized into the canonical model (D2/§3.2(h) posture). Vault receipt (§6.3 backup) may precede it.
- **§5 delivery**: complete data copies for 23 practice databases arrive by secure file transfer within 10 business days of the 2026-07-18 request (~Aug 3), in ezyVet's standard complete-export format — **format unknown until delivery**; the pipeline is format-discovery-driven for exactly this reason.
- **ICP (2026-07-18)**: large multi-site operators (100–400-practice, PE-owned, mixed-PIMS estates). Requirements are written so the ezyVet path generalizes via the pluggable adapter port; the 23-practice batch is the first instance, not the ceiling.
- **Invisible Adoption Doctrine (Working Rule 0)** is a binding constraint, not a preference: staff must never experience "new software"; owner/manager surfaces only.
- **Extraction subprocessors** (Gemini for parsing/vision) require a DPA with a no-retention posture for raw PII; the vault is clinic-owned (§6.3).
- **Handoff contracts**: the `entity_ref`/identity audit-corpus shape to 011, and the canonical model shape that the shadow/advise engine (010/011/envelope-MVP) reads, must be agreed at the seam — coordinate, don't fork.
- **Competitive bar**: Digitail's public migration marketing (~1-week sandbox, 4–6-week hypercare) sets the time bar; its unaddressed financial/AR history is the gap this spec's reconciliation closes.
- Reuses shipped mechanisms: the 008/032/044 extraction pipeline and streaming extract-narrate-confirm UX, the FarmAgent *fixed* provisioning/RLS patterns (wrap the full transaction; FORCE-RLS on onboarding tables), and the 048 job-router/session-log seams — extract, don't fork.

---

## Marketing Output
**Produced by**: speckit-specify — 2026-07-18

### Feature Brief

**Consumer-Friendly Feature Name**: Vera's First Day — She Arrives Already Knowing Your Practice

**Key Benefits** (in customer language):
1. No migration, no cutover, no training — Vera reads your group's own records and is useful within days, while your staff keep working exactly as they do today.
2. Trust that nothing was lost — you get a reconciliation report on every practice, including financials, AR, and inventory, tying back to your own numbers.
3. It scales the way your group does — every practice onboards independently, the next one inherits what the last one learned, and the same process works across whatever systems your practices run.

**One-Line Description** (≤25 words): Vera turns your group's own data copies into a working assistant that already knows each practice — verified down to the financials, with nothing for staff to learn.

**Guidance note**: Sell "she already knows your practice, and here's the proof your numbers all reconcile" — never "a data migration" and never the replacement endgame.
</content>
</invoke>
