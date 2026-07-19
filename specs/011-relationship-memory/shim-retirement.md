# 011 — Scoped-Recall Shim Retirement (switch plan)

**Feature**: 011 Relationship Memory · **Status**: PREP ONLY — nothing deleted, no
core import added. This document is the exact cutover plan for when the remaining
blockers (below) clear.

## 0. What this is / is not

Vera-core extracted our scoped-recall rail into core: `vera/memory.py`
`Memory.scoped_recall` (FarmAgent2 repo, branch `feat/c6-scoped-recall-rail`
@ `0515538`). This doc plans the retirement of our three shim modules —
`backend/relationship/scoping_policy.py`, `backend/relationship/scoped_recall.py`,
`backend/relationship/reveal_log.py` — in favor of that core rail.

**Do NOT, in this prep phase:**
- delete any of the three shim modules;
- add any `import vera...` / core dependency to `backend/`;
- change runtime behavior.

The **policy DATA** (the three-field `memory_scoping`) is already pack-shipped and
is UNCHANGED by the cutover — it moves with the vertical
(`domains/vet/comms/memory_scoping.yaml`). W10: content ours, rail core.

## 1. Gate status (revised 2026-07-19)

Per Vera-core's 2026-07-17 verification note (agent-commo board), two previously
assumed gates are **already cleared** — do not re-list them as blocking:

| Was assumed gated-on | Actual status (2026-07-17) |
|---|---|
| core branch `feat/c6-scoped-recall-rail` merge | **MERGED** to FarmAgent2 `origin/main`, deployed |
| migration 062 (RLS+FORCE, append-only reveal log) | **FULLY APPLIED + verified live** on `postgres-digital-twin` |

### Real remaining blockers (gated-on)

1. **Packaging / import path — UNDEFINED.** How does `General_Scheduler/backend`
   obtain core's `vera.memory` module? pip dependency (versioned release?),
   vendored copy, or monorepo path? Until this is decided and wired, `backend/`
   cannot import the rail. **Owner: platform + core.**
2. **Database topology — UNDECIDED.** Core's `reveal_decision_log` (the append-only
   audit the rail writes) lives on core's `postgres-digital-twin`; our 011 tier
   runs on our Postgres at `:5433` (container `vetagent-voice-pg`). Which DB the
   rail reads facts from and writes reveal decisions to **for a VetAgent tenant**
   must be settled with core (single shared DB? per-tenant DB? dual-write?).
   Reveal-audit continuity (FR-016) cannot regress across the move. **Owner: core.**
3. **Behavioral reconciliations** (§4) — two semantic divergences between our shim
   evaluator and core's rail that must be reconciled *before* cutover, else facts
   change visibility silently. **Owner: 011.**

Until **all three** clear, the shim stays. The identity-audit gate
(`backend/relationship/identity_audit_gate.py`) and the soft-confirm/verification
tiers are independent of this cutover and are unaffected.

## 2. Call-site inventory — `ScopedRecall.recall` / `.recall_by_kind`

The shim's client-facing surface is two coroutines. Every call site that must
switch to `Memory.scoped_recall`:

### Production (1)

| file:line | call | replacement |
|---|---|---|
| `backend/relationship/household_summary_provider.py:75` | `scoped_recall.recall_by_kind(summary_kind, audience=audience, entity_scope=entity_scope)` | `memory.scoped_recall(context=summary_kind, audience=audience, entity_ref_scope=entity_scope, kind=summary_kind)` — see §3 kind-filter note |

The provider is constructed at `backend/voice/prefetch.py:65`
(`real_household_provider(repo, scoped_recall, clinic_id, ...)`); that injection
seam changes from a `ScopedRecall` instance to a core `Memory` handle. `_run`
(sync→async bridge, `household_summary_provider.py:28`) is unaffected.

### Tests (16 call sites across 4 files)

These are the red-team / privacy proofs; each `recall(...)` must be re-pointed and
the `ScopedRecall(...)` fixture constructors swapped for a core `Memory` (or its
test double). They are the acceptance harness for the cutover — keep every
assertion, re-point the driver.

| file:line | note |
|---|---|
| `backend/tests/relationship/test_scoped_recall.py:50` | **API-shape guard** — `recall("anything")` with NO `audience` must stay a `TypeError` (unscoped recall unrepresentable). Confirm core's `scoped_recall` keeps `audience` a REQUIRED kw-only arg; if not, add a wrapper assertion. |
| `test_scoped_recall.py:71,80,86,95,100` | default-deny + own-household/own-clinic filters |
| `test_shared_line.py:85,97,111` | shared-line pre/post verification reveal boundary |
| `test_scoping_red_team.py:81,93,109,114,139` | audience matrix + unmapped-kind deny + reveal-log-on-every-fact |
| `test_shim_upgrades.py:180,194` | thread-continuity (single-channel) recall |

`ScopedRecall(...)` constructor fixtures to re-home: `test_scoped_recall.py:33`,
`test_scoping_red_team.py:60`, `test_shim_upgrades.py:123`, `test_shared_line.py:41`.

**Inventory size: 1 production + 16 test call sites (17 total); 4 fixture
constructors.**

## 3. The replacement mapping (per call)

Shim → core, argument by argument:

```
ScopedRecall.recall(query, *, audience, entity_scope, thread_id=None)
  → Memory.scoped_recall(context=query, audience=audience,
                         entity_ref_scope=entity_scope, thread_id=thread_id)

ScopedRecall.recall_by_kind(kind, *, audience, entity_scope, thread_id=None)
  → Memory.scoped_recall(context=kind, audience=audience,
                         entity_ref_scope=entity_scope, kind=kind, thread_id=thread_id)
```

- `entity_scope` (our name) → `entity_ref_scope` (core's name). Same value: the
  `[household_id, clinic_id]` ref list. **Confirm core applies `own_clinic_only`
  BEFORE `own_household_only`** (our order; a missing clinic ref must deny
  everything — `household_summary_provider.py:71-76` relies on this).
- `recall_by_kind`'s kind filter: our shim filters `f.fact_kind == kind` *inside*
  the (unscoped) Thoth stub, then scopes. Core pushes scope INTO recall (that is
  the whole point — it fixes the M3 access-count over-count). **Confirm core
  exposes a kind filter** on `scoped_recall`; if the parameter name differs
  (`kind` vs `fact_kind`), adjust the one production call.
- `thread_id` (single-channel voice continuity, our T029): confirm core carries a
  per-channel thread scope; if core has no equivalent, thread continuity is a
  follow-up, NOT a blocker (it degrades to unthreaded recall, never a leak).
- The reveal-decision audit (`reveal_log.py`) is written by core's rail post-move
  (blocker §1.2). Our `RevealLog.record(...)` and the `reveal_decision_log` reason
  vocabulary (`explicit_allow | default_deny_no_rule | wrong_household |
  unmapped_kind`) must map 1:1 onto core's; verify the reason strings match or add
  a translation at the boundary so FR-016 audit queries keep working.

## 4. Behavioral divergences to reconcile BEFORE cutover

Both are places where our shim and core's rail would give a fact a **different
visibility** — a silent reveal/withhold change if cut over unreconciled.

### 4a. Null-`entity_ref` under a scope predicate

Our evaluator (`scoping_policy.py:90-101`) guards each row predicate on
`subject_household is not None` / `subject_clinic is not None`:

```python
if pred == "own_household_only":
    if subject_household is not None and (
        entity_scope is None or subject_household not in entity_scope):
        return ScopeDecision("withheld", "wrong_household", fact_class)
```

⇒ a fact whose `subject_household` (or `subject_clinic`) is **null** is **NOT**
withheld by the predicate — a null-subject fact of an allowed class is **REVEALED**.
Core's rail keys scope on `entity_ref_scope`; a fact with a **null entity_ref**
under an active scope predicate may **DENY** (no ref to match ⇒ out of scope).

**Reconcile:** decide the intended semantics for a null-scoped fact and make both
agree. Recommended: **fail-closed** (a fact with no household/clinic ref should
NOT be revealed to an `own_household_only` / `own_clinic_only` audience) — align
our shim to core, and add a test fact with `subject_household=None` to the
red-team matrix asserting withhold. Audit any existing null-subject facts first
(a summary line with no household would flip from visible to hidden).

### 4b. Fail-OPEN on an unrecognized scope predicate (core-flagged hardening)

Our evaluator's predicate loop (`scoping_policy.py:90-101`) is `if / elif` over
the two known predicates with **no else** — an unrecognized predicate string is
**silently ignored** (no filter applied ⇒ **fail-OPEN**, the fact may reveal). A
typo'd or future predicate in policy data therefore *weakens* scoping instead of
tightening it. Core flagged this.

**Reconcile:** **fail-CLOSED** on an unrecognized predicate — an unknown predicate
must `withhold` (default-deny), never no-op. Add the `else: return
ScopeDecision("withheld", "unknown_predicate", fact_class)` branch (and the
matching reason to the closed vocabulary) so the rail and shim both deny. Add a
red-team test with a bogus predicate asserting withhold. This is safe to author in
the shim NOW as defensive hardening (it only ever tightens), but the *reason-code*
addition touches the closed vocabulary shared with core — coordinate the string.

## 5. Cutover checklist (execute only when §1 blockers clear)

1. Wire the packaging/import path (§1.1); add core `vera.memory` to `backend/` deps.
2. Settle DB topology (§1.2); point the rail's fact source + reveal-log sink;
   verify FR-016 audit continuity.
3. Land the two reconciliations (§4) in BOTH the shim (now) and core (confirm),
   with red-team tests green under the shim first.
4. Re-point the 1 production call (`household_summary_provider.py:75`) + injection
   seam (`prefetch.py:65`) to `Memory.scoped_recall`.
5. Re-point the 16 test call sites + 4 fixture constructors; keep every assertion.
6. Delete `scoping_policy.py`, `scoped_recall.py`, `reveal_log.py`.
   `domains/vet/comms/memory_scoping.yaml` (policy data) STAYS.
7. Full suite green; reveal-audit spot-check on real reveal decisions.
