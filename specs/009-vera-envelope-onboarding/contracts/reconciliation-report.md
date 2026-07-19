# Contract — `ReconciliationReport` (the owner-facing trust artifact)

**Feature**: 009 Vera Envelope Onboarding · **Task**: T027 · **Status**: frozen
**Producer**: `backend/envelope/reconciliation.py` (T024) + `backend/envelope/owner_surface.py` (T026)
**Model**: `backend/models.py` `ReconciliationReport` · **Table**: `reconciliation_report` (append-only)

This freezes the requested/delivered/ingested-by-category + financial-reconciliation
shape (the owner-facing artifact) so the downstream owner surface and any
advise-engine consumer read a **stable** shape. It is the Digitail-beating trust
surface: the owner's proof that nothing was lost (SC-005), with the financials
tied to the practice's own numbers and any AR gap surfaced **red and blocking**.

---

## 1. Per-category counts

`category_counts: {scope_category: {requested, delivered, ingested}}` — one line
per §5 `scope_category` (`patient_client`, `scheduling`,
`invoicing_billing_payments`, `communications`, `attachments_imaging`,
`configuration`):

| Field | Meaning |
|---|---|
| `requested` | count the §5 letter asked for (the profiled/delivered count when present; `0` when the category is absent — an outstanding gap) |
| `delivered` | records that arrived in the export (profile entity counts for the category's source entities) |
| `ingested` | canonical records loaded (from the generic `canonical_record` spine) |

`outstanding_gap: [scope_category]` — every category that is **absent** or
**short** (delivered/ingested below the profile). A partial practice's report
lists its missing categories here; the practice proceeds but is **not** complete.

---

## 2. Financial reconciliation (the zero-tolerance core)

Three `FinancialVariance` blocks — `ar_variance`, `invoice_variance`,
`payment_variance` — each:

| Field | Meaning |
|---|---|
| `amount` | `ingested − reported` (the source system's own reported figure) |
| `disposition` | `explained` \| `blocking` (`variance_disposition` enum) |
| `attributed_cause` | the itemized reason, or `null` |

**Zero-AR-tolerance (FR-017)**: an `ar_variance` with `amount ≠ 0` and **no**
`attributed_cause` is `blocking`. Invoice/payment variances are likewise
`blocking` when nonzero-and-unattributed, `explained` when zero or attributed.

`blocking: bool` — **true** iff any of the three variances is `blocking`. The
state-machine `ar_variance` guard reads the latest report's `blocking` to hold the
practice out of `reconciled`/`shadow_ready`. **0 silent AR discrepancies pass.**

---

## 3. Owner-facing surface + group acknowledgment

`audience: owner | manager` — the report is **owner/manager-audience-only**; no
staff audience is reachable (`OwnerSurface.latest_report` raises on any other
audience — FR-029, the invisible-adoption guard).

`owner_acknowledged: bool` — the **group-level** activation ack. Recorded as an
**append** (a fresh report version with `owner_acknowledged=True`), never an
in-place update (the table is append-only). A **blocking** practice is never
acknowledged — the group ack (`OwnerSurface.acknowledge_group`) acknowledges only
the non-blocking practices and returns `{acknowledged, held}`.

**Drill-down** (`OwnerSurface.group_report`): the group rollup carries a
`drill_down: {practice_id: latest_report}` map plus `blocking` / `acknowledged`
practice lists — from the group report down to each individual practice's
reconciliation (FR-018). A practice `is_activatable` only once its latest report
is `owner_acknowledged` **and** not `blocking`.

---

## 4. Conformance

`Reconciler.reconcile(...)`'s output conforms to §1–§2; `OwnerSurface`'s
group-ack/drill-down conforms to §3. The report is append-only: the ack path adds
a version, so a report's history is the full audit trail (received → acknowledged).
