# Spec 009 — Known Issues

Defects found after implementation, recorded so they are not rediscovered the
expensive way. Each names the trigger, the blast radius, and the sequencing.

---

## KI-1 — Re-ingest silently rewrites history (lineage integrity)

**Found:** 2026-07-28, while answering Vera-core's "where did it hurt" question
for the Pattern-① evidence contract. Verified in `backend/envelope/normalizer.py`.

**What:** the idempotent upsert is **delete-then-insert on the lineage key**. When
a delta delivery arrives and a practice is re-ingested, a claim Vera made earlier
still carries a `source_id`/`entity_ref` that **resolves — to the new content**.
Nothing errors and nothing warns.

**Why it matters more than a dangling reference:** a broken reference is visibly
broken. This is invisibly *wrong* — the audit trail retroactively lies, and the
reconciliation report a practice owner accepted last month may no longer be
reproducible from the same references. Partial/delta deliveries are an expected,
designed-for path (FR-032), so this triggers in normal operation, not an edge case.

**Blast radius:** any claim citing a re-ingested record — reconciliation figures,
briefing claims, and (once 012 lands) note citations.

**Fix direction:** snapshot-and-version the source rather than replacing it; a
reference whose snapshot no longer exists must resolve to a **loud tombstone**,
never to current state. This couples to Vera-core's evidence-reference contract
(requirement R5, accepted into that contract) — sequence the fix **with** the port
rather than inventing a second versioning scheme here.

**Pilot exposure:** low before first delta delivery; the initial Synergy Vets load
is a single ingest per practice. Must be fixed before recurring deltas or before
any customer-facing claim cites a record that a later delivery can rewrite.

---

## KI-2 — Derived claims persist results without their input set

**Found:** same review.

**What:** the reconciliation report states AR/invoice/payment totals and itemizes
variances, computed across many canonical records — but only the **result** is
persisted. Nobody can later answer *which records produced a given variance*.

**Why it matters:** the claims a customer cares most about are the derived ones,
so these are precisely the numbers with no traceable input set. A citation model
that only supports one-source-per-claim would push every vertical to quietly skip
citing its most important figures.

**Fix direction:** claims must be able to cite a **set** of references cheaply
(Vera-core contract requirement R2, accepted). Persist the contributing reference
set alongside each computed figure in the reconciliation report.

---

*Both defects share one shape — **invisible when broken**: the reference still
resolves, the total still displays, the log still has rows. That shape is the
common thread across the 2026-07-28 fleet incidents and is why the evidence
contract's "absence must be loud" principle is load-bearing rather than stylistic.*
