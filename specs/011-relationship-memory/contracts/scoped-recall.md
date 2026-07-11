# 011 Contract — ScopedRecall Rail & `memory_scoping` Policy

Two parts: (A) the **ask to Vera-core** — a scoped recall API where `audience` is mandatory, so an unscoped client-facing recall is *unrepresentable* (default-deny); (B) the **VetAgent `ScopedRecall` shim** we build now, over shipped Thoth, marked `prototype` for extraction when core lands the rail. This is board ask #2 ("if core builds only one thing this month, build this").

---

## A. Ask to Vera-core — the mandatory-audience rail

Core's shipped Thoth exposes `recall(query)` / `recall_by_kind(kind)` with **no audience parameter** — an unscoped surface. VetAgent's binding position (FR-013/014, SC-001=0): the enforcement point must be core.

```python
# Requested core API — audience is REQUIRED; there is no unscoped overload.
async def scoped_recall(query: str, *, audience: Audience, entity_scope: list[str]) -> list[Fact]: ...
async def scoped_recall_by_kind(kind: str, *, audience: Audience, entity_scope: list[str]) -> list[Fact]: ...
# Audience = Literal["owner","manager","staff","client_verified","caller_unverified"]
```

**Why core, not the domain pack**: a query-time filter in the vertical makes the privacy boundary a per-vertical opt-in in the least-audited, most-bug-prone layer; FarmAgent needs the identical rail. The FR set (default-deny, deny-on-missing-rule, audit-on-reveal) *is* the C1 rail spec. **Status: pending core confirmation.**

## B. VetAgent `ScopedRecall` shim (`backend/relationship/scoped_recall.py`)

Until core confirms A, wrap Thoth so unscoped client-facing recall cannot be written.

```python
# [SHIM — extract to core rail post-confirmation]
class ScopedRecall:
    def __init__(self, thoth, policy: ScopingPolicy, reveal_log): ...

    async def recall(self, query: str, *, audience: Audience,
                     entity_scope: list[str]) -> list[Fact]:
        # audience is a REQUIRED kw-only arg — no unscoped overload exists.
        raw = await self._thoth.recall(query)                 # core engine (unscoped)
        return self._apply_policy(raw, audience, entity_scope)  # default-deny filter + audit

    async def recall_by_kind(self, kind: str, *, audience: Audience,
                             entity_scope: list[str]) -> list[Fact]: ...
```

- The raw Thoth handle is **private** — client-facing code holds only a `ScopedRecall`, so `recall()` without an `audience` is a construction error, not a runtime check.
- `_apply_policy` resolves each fact's `fact_kind` through `kind_to_class` (§C), checks the resolved class against `allow_classes[audience]`, then applies the audience's `scope_predicates` against the caller's `entity_scope` (`own_household_only` for `client_verified`); **any fact whose kind is unmapped, whose class is not allowed, or that fails a scope predicate is dropped** (default-deny, FR-014).
- Every decision (revealed / withheld + reason ∈ `explicit_allow|default_deny_no_rule|wrong_household|unmapped_kind`) is written to `reveal_decision_log` (FR-016) — the staff-visible audit spine.
- **Access-count caveat (shim-era, M3)**: in the shim, filtering happens **after** Thoth's `recall()`, which has **already incremented `access_count`** on every candidate fact — including facts this wrapper then withholds. So `access_count` here **over-counts**: a default-denied fact is counted as accessed though it was never revealed. This shim-era `access_count` **MUST NOT drive salience or sleep-agent consolidation decisions**, and it leaks nothing to the caller (withheld facts never reach the response). The core-rail extraction (§A) resolves this properly by pushing `audience`/`entity_scope` **into** recall, so a withheld fact is never touched and **withheld ≠ accessed**. *(A one-line note flagging this to the board is tracked outside this contract.)*

## C. `memory_scoping` policy shape (C1 vertical data)

Loaded from `config/relationship/memory_scoping.<clinic>.yaml` into `memory_scoping_policy` (versioned, VP-9-signed).

The policy is **three distinct fields** — allow-classes and scope-predicates are no longer conflated in one list (H1). Recall returns facts keyed by Thoth `fact_kind`; the policy allow-lists per-audience **fact classes**; `kind_to_class` is the bridge that maps every recall `fact_kind` onto a fact class before the allow-check. This makes the evaluator's input well-defined and keeps positive content-classes separate from row-level scope filters.

```yaml
memory_scoping:
  audiences: [owner, manager, staff, client_verified, caller_unverified]

  # (1) Positive fact CLASSES an audience MAY be revealed. Closed vocabulary:
  #     schedule | client_summary | patient_clinical | financial | contact_info | staff_notes
  #     ABSENCE of an audience here = deny everything (structural default-deny).
  allow_classes:
    owner:            [schedule, client_summary, patient_clinical, financial, contact_info, staff_notes]
    manager:          [schedule, client_summary, patient_clinical, financial, contact_info]
    staff:            [schedule, client_summary, patient_clinical, contact_info]
    client_verified:  [schedule, client_summary, patient_clinical]
    caller_unverified:[schedule]                       # availability only

  # (2) Row-level SCOPE PREDICATES applied AFTER the class allow-check (filters, not classes).
  #     Closed vocabulary: own_household_only | own_clinic_only
  #     Empty list = no additional row filter beyond the class allow.
  scope_predicates:
    owner:            [own_clinic_only]
    manager:          [own_clinic_only]
    staff:            [own_clinic_only]
    client_verified:  [own_household_only]
    caller_unverified:[]

  # (3) Thoth fact_kind -> fact class bridge. Every recalled fact_kind MUST resolve here.
  #     An UNMAPPED kind is DENIED and logged (reason=unmapped_kind) — never revealed.
  kind_to_class:
    identity:          client_summary
    schedule:          schedule
    appointment:       schedule
    clinical:          patient_clinical
    patient_clinical:  patient_clinical
    financial:         financial
    contact_info:      contact_info
    staff_note:        staff_notes
```

Evaluator (T018 / T037) algorithm — allow only when **all** hold, else deny + log:
1. Resolve the recall `fact_kind` via `kind_to_class`; an unmapped kind → **deny**, `reason=unmapped_kind` (H1 fail-closed).
2. The audience must appear in `allow_classes` **and** the resolved class must be in that audience's list, else → **deny**, `reason=default_deny_no_rule`.
3. Apply every `scope_predicate` for the audience as a row filter: `own_household_only` withholds any fact whose subject household ≠ the caller's confirmed household (`reason=wrong_household`); `own_clinic_only` withholds cross-clinic facts. A predicate that fails → **deny**.

- `caller_unverified` → allow `[schedule]` (general availability only), scope `[]` (formalizes today's hand-coded first-name-only lookup as the default, FR-015).
- `client_verified` → allow `[schedule, client_summary, patient_clinical]`, scope `[own_household_only]`; **financial** is simply not in its `allow_classes` and **another household's detail is filtered by `own_household_only`** — always withheld (FR-015, red-team target).
- Default-deny is structural in **both** directions: a class not in the audience's `allow_classes`, an audience absent from `allow_classes`, and an unmapped `fact_kind` all deny; nothing is revealed by omission.

## D. Enforcement fallback posture

If core lands the mandatory-audience API (A), the shim (B) is deleted and callers switch to core `scoped_recall`; the policy data (C) is unchanged and moves with the vertical. If C1 slips, the policy ships as a `prototype`-marked vertical shim per the split rule. Either way the **rail is never bypassed** — client-facing surfaces never hold an unscoped Thoth handle.
