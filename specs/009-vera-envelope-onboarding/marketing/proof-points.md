# Proof Points: Vera's First Day (009 Envelope Onboarding)

**Purpose**: The claim-to-evidence ledger behind the 009 marketing copy. Every customer-facing claim in `brief.md` and `one-pager.md` must trace to a row here. This is the "type system" for the on-ramp story — what the build proves, what is a design target, and what is deferred to the pilot.
**Generated**: 2026-07-19 · **Build state**: T045 final checkpoint green — **111 envelope tests** inside the **411-test** project suite, zero regressions to the cumulative 010/011 suites.
**Discipline**: build-suite results are stated as *build-proven* (green in the engineering harness), never as live-clinic performance. Live figures are measured on audited pilot data. Customer copy never uses "migration", "cutover", or "conversion", and never names a competitor or a client.

---

## The five load-bearing proof points (strongest first)

| # | Claim (customer-facing) | Status | Evidence (FR / SC / test) |
|---|---|---|---|
| 1 | **"Your accounts receivable reconcile exactly, or the practice doesn't activate."** Any unexplained AR variance is a blocking discrepancy; invoice/payment variances are itemized and must be attributed to a cause or they block. | **Build-proven gate** | FR-016/FR-017 · SC-004 · `test_financial_recon.py`, `test_reconciliation.py` — planted AR variance blocks; 0 silent AR discrepancies; state machine's AR-variance transition guard (T026) holds a practice out of `reconciled`/`shadow_ready` |
| 2 | **Nothing your staff will ever see** — zero logins, training, dashboards, or notifications; even a clinician in the export gets a schedule entry, never an account. | **Build-proven (red-team)** | FR-028/FR-029 · SC-006 · `test_invisible_adoption.py` — batch-wide red-team scan finds 0 staff-facing artifacts and 0 provisioned staff identities; the readiness gate rejects any run that emitted one |
| 3 | **A re-run can't corrupt the store** — load the same data twice and get a zero-row diff: 0 duplicates, stable IDs, 100% of records trace to source. | **Build-proven (go-live gate)** | FR-009/FR-010 · SC-003 · `test_idempotency_lineage.py` — second ingest produces a 0-row diff; 100% lineage coverage; re-run as the go-live gate at T045 |
| 4 | **A quality floor holds bad data back** — a practice with >20% of sampled records unusable is held out of activation with its gap itemized. | **Build-proven gate** | FR-015 · `test_quality_floor.py` — the >20%-unusable fixture practice transitions to `held` and never reaches `shadow_ready`; a category-lopsided practice is held on a clinical-completeness gap despite reconciled financials |
| 5 | **A partial delivery never passes as complete** — the gap is detected, an owner-facing paper-trail-ready gap notice is produced, the practice proceeds on what arrived, and a later delta folds in with no duplicates. | **Build-proven gate** | FR-030/FR-031/FR-032 · SC-009 · `test_partial_delta.py` — 100% of partial deliveries detected, 0 silently accepted; delta merges with 0 duplicates and updates the reconciliation report |

---

## Supporting proof points

| Claim | Status | Evidence |
|---|---|---|
| **A legal sign-off gate before normalize** — not one record is read into the practice model until a counsel sign-off on the clinic-owned-data structure is recorded; provable across the whole batch. | **Build-proven gate** | FR-004 · `test_counsel_gate.py`; T045 checkpoint — 0 databases reach `profiled`/`normalized` without a recorded `counsel_signoff` row (the whole-spec legal gate) |
| **Profile-before-normalize** — each database is profiled (entities, counts, encodings, relationships) before any mapping; normalization is blocked without a profile, so the schema is never guessed. | **Build-proven gate** | FR-005/FR-006 · SC-002 · `test_format_discovery.py`, `test_profile_gate.py` — 0 databases normalized without a `FormatProfile` |
| **Chain-of-custody receipt** — every practice database received into a clinic-owned encrypted vault, fingerprinted/timestamped/scope-checked before anything is interpreted. | **Build-proven** | FR-001/FR-002 · SC-001 · `test_vault.py`, `test_chain_of_custody.py`, `test_scope_check.py` — 100% carry a full chain-of-custody record before parsing; 0 pre-receipt parses |
| **Reconciliation covers financials** — requested vs delivered vs loaded by category, AR/invoices/payments tied to the source's own reported figures, variances itemized; owner/manager-only. | **Build-proven** | FR-016/FR-018 · SC-004/SC-005 · `test_reconciliation.py`, `test_financial_recon.py` — financial completeness covered for 100% of practices; report reaches owner/manager surfaces only |
| **Group rollup + per-practice drill-down; one blocked practice never stalls the batch; the next practice reuses the last one's mappings.** | **Build-proven** | FR-024/FR-025/FR-026 · SC-010 · `test_batch.py` — independent per-practice advance; held/blocked practice doesn't stop others reaching `shadow_ready`; marginal mapping steps trend down across the batch (build-time proxy for SC-010) |
| **Every fact is traceable** — every loaded record carries `source_id`/`entity_ref` lineage back to its origin record. | **Build-proven** | FR-009 · SC-003 · `test_normalizer.py`, `test_idempotency_lineage.py` — 100% lineage coverage |
| **Pluggable per-PIMS adapter port** — a new system is a new adapter behind one stable port, not a forked core (one adapter built this cycle). | **Build-proven (architecture)** | FR-027 · `test_port.py`, `test_ezyvet_adapter.py`, `test_extraction_port.py` — normalization driven through an adapter behind a stable port; core not forked per system |
| **Identity groundwork, no silent merges** — household/party grouping proposals with lineage; collisions/duplicates routed to review; 0 auto-merges. | **Build-proven** | FR-019/FR-020/FR-021 · SC-008 · `test_identity_bootstrap.py`, `test_identity_handoff.py` — every collision routed to a pending review row; 0 auto-merges across the corpus |
| **111 envelope tests inside a 411-test suite, all green at the final checkpoint**, with zero regressions to prior suites. | **Build-proven** | T045 final checkpoint — full `backend/tests/envelope/` suite green (111 tests); all SC-001–SC-010 build-time gates green |

---

## Design target — not yet proven (pilot-homed)

| Claim | Status | Why not build-proven / where it's proven |
|---|---|---|
| **"First practice ready within about a week of receiving your data,"** full group reconciled inside a several-week window, **with nothing to switch over at the end.** | **DESIGN TARGET** ⚠️ | SC-007 — the build has **no wall-clock proxy**; only its enablers are build-proven (idempotent ingest T038, batch/rollup T033, prior inheritance T044). The calendar figure is **measured live at the pilot**. Copy must say "designed to" / "a design target the pilot will confirm", never "achieved". |
| **Per-practice marginal effort trends to config-reuse only** as the batch runs. | **Build-time proxy; live at pilot** | SC-010 — measured as setup/mapping steps trending down in the build (`test_batch.py`); the real-estate figure is a pilot measurement |

---

## Framing guardrails (binding, from the brief's claim discipline)

- **Never** "migration" / "cutover" / "conversion" in customer copy. The frame: VetAgent reads the practice's own records and Vera arrives already knowing it; staff experience nothing new.
- **Naming**: VetAgent is the product (bought); Vera is the differentiator (experienced). "VetAgent reads your records; Vera arrives already knowing the practice."
- **The AR line is the lead trust claim**: "your accounts receivable reconcile exactly, or the practice doesn't activate."
- **No** competitor names, no ToS/legal-clause mechanics, no client names (the open-balance failure is "the worst story on record in this category"; the legal gate is "a counsel sign-off gate — your data stays your data").
- Category context (VC-9 overlay-layer framing, VC-1 displacement wave) is available for *why-now* only, never as an on-ramp performance claim.

---

*This ledger is internal. Build-proven figures are engineering-harness results at the T045 checkpoint; they are re-verified live on audited pilot data before any external use, and the SC-007 timing target remains a design target until the pilot measures it.*
