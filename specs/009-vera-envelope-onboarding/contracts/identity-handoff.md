# Contract — Identity Handoff (the 009→011 seam)

**Feature**: 009 Vera Envelope Onboarding · **Task**: T030 · **Status**: frozen (009-owned; **flagged for 011 sign-off**)
**Producer**: `backend/envelope/identity_bootstrap.py` (T028/T029)
**Reused verbatim**: `backend/relationship/entity_ref.py` (011 T005) · `backend/models.py` `HouseholdReviewQueue` + `backend/relationship/review_queue.py` (011 T012)

This **defines the 011 seam** (009-owned): the `entity_ref` keying + the identity-
audit-corpus + the `HouseholdReviewQueue` row shape that 009 produces, **proposed
as the hard input gate** for 011's gated resolver / verification tiers to adopt.
011 today specifies the audit as a gating *activity*, not yet a consumed *schema*
(finding F5); 009 owns the shape here. **Coordinate, don't fork** — this doc is the
authoritative seam definition until 011 adopts it.

---

## 1. `entity_ref` keying (reuse `entity_ref.py` verbatim — names never in the key)

`{type}:{stable_id}` — the byte-identical handoff keys 011's resolver consumes:

| Namespace | Builder | Shape | Producer |
|---|---|---|---|
| `client:ezyvet_c*` | `client_ref(id)` | `client:ezyvet_c{digits}` | adapter (T015) |
| `patient:ezyvet_p*` | `patient_ref(id)` | `patient:ezyvet_p{digits}` | adapter (T015) |
| `staff:*` | `staff_ref(id)` | `staff:{id}` | adapter (T015) |
| `household:vah_*` | `synth_household_ref(seed)` | `household:vah_{sha1[:12]}` | identity bootstrap (T028) |

`household:vah_*` is synthesized **downstream** by identity bootstrap, deterministic
from `{practice_id}:{source_id}` (reproducible; no name in the key), **not** by the
adapter.

---

## 2. `IdentityAuditCorpus` (append-only; `backend/models.py`)

The real-export audit corpus — the proposed 011 resolver input gate:

| Field | Shape |
|---|---|
| `practice_id` | per-practice attribution (the 23 practices are independent) |
| `proposals` | `[{practice_id, entity_ref, household_ref, source_id}]` — household groupings, each with full lineage |
| `collisions` | `[{practice_id, shared_phone, entity_refs, proposal_type, review_item_id}]` |
| `answer_key_scored_precision` | build-time scoring — `{flagged_phone_count, proposal_count, collision_count, duplicate_count, single_match_phones, multi_match_phones, true_positives, false_positives, precision}` |

`answer_key_scored_precision` is the **build-time** score against the T005 answer
key (single-match vs multi-match); it enumerates precision so a false-positive
auto-ID is detectable. At Pilot-Activation the same corpus is produced over the
real export (no answer key → the scoring fields are omitted).

---

## 3. `HouseholdReviewQueue` row shape (reused 011 model — **clinic-scoped**)

Every collision / probable-duplicate is written via
`ReviewQueue.propose_grouping(...)` (the **only** write path — never a merge):

| Column | 009 use |
|---|---|
| `clinic_id` | tenant scope (the model's only column-level scope) |
| `proposal_type` | `probable_duplicate` (same normalized name on a shared line) \| `collision` (distinct names on a shared line) |
| `subject_refs_json` | `[{practice_id, entity_ref}]` — **`practice_id` carried per subject** |
| `evidence_json` | `{practice_id, shared_phone, entity_refs, reason}` — **`practice_id` carried in evidence** |
| `status` | always `"pending"` (staff/owner approve/reject/defer later) |

**Practice-scoping on a clinic-scoped model (F6)**: `HouseholdReviewQueue` has **no
`practice_id` column**. 009 is practice-scoped and **does not fork** the model —
it carries `practice_id` inside `evidence_json` **and** each `subject_refs_json`
entry (both open JSON), so per-practice attribution + reconciliation drill-down
work without a schema change.

---

## 4. Hard guarantees (proposed input gate for 011)

- **Zero auto-merge**: the only identity write path is `propose_grouping` (a
  *pending* proposal). No `merge` / `auto_merge` function exists in
  `identity_bootstrap.py` or `review_queue.py` (AST-asserted, T028/T042).
- **Owner/manager-surfaced**: onboarding creates **no** staff-facing queue.
- **No runtime resolution here**: 009 produces the corpus + candidate-set; it
  implements **no** runtime auto-ID / soft-confirm / verification bar — those are
  011's gated tiers, which adopt this corpus as their input gate.

---

## 5. Conformance

T029's output conforms to §2; every collision row conforms to §3; the
`entity_ref` keys conform to §1. **This doc is flagged for 011 sign-off at the
seam** — until then it is the authoritative 009→011 identity contract.
