# 011 Contract — Identity Resolution, Review Queue & Verification Bar

VetAgent-owned (backend/relationship/). Formalizes and replaces 010's `shims/channel_binding_shim.py` (T006). The identity-safe disambiguation contract (never enumerate candidate names aloud) is preserved from the shim.

---

## R1 — Resolver: candidate sets, never `LIMIT 1`

```python
@dataclass
class Candidate:
    party_id: str
    household_id: str
    entity_ref: str            # client:ezyvet_c*
    display_name: str          # MATCHING only — never spoken until confirmed
    score: float               # match confidence (exact-phone == 1.0)

@dataclass
class ResolutionResult:
    candidates: list[Candidate]                 # FULL set — 0..n, never reduced to one silently
    outcome: Literal["resolved_single", "ambiguous_multi", "unmatched"]
    # resolved_single ONLY when exactly one candidate on an EXACT normalized-phone match

def resolve(clinic_id: str, identifier: str, id_type: Literal["phone","email","name"]) -> ResolutionResult: ...
```

- `resolved_single` is the **only** state permitting auto-ID + soft-confirm (FR-007, SC-004). It requires exactly one candidate from an **exact normalized-phone** match — fuzzy/partial matches never auto-greet.
- `ambiguous_multi` (the shared-line case, `is_shared_line`) and `unmatched` → neutral "May I get the name on the account?"; no guessed name is ever spoken (FR-007/010/011, SC-003).
- Every call persists an `identity_resolution_event` with the full `candidate_set_json` (append-only audit).
- **Auto-ID is disabled-safe**: until the real ezyVet-export identity audit is complete, `resolve` may run in `audit_only` mode (records candidates, always returns neutral) — degrades US2, does not break it.

## R2 — Disambiguation (open answer, never enumerate)

```python
def disambiguate(result: ResolutionResult, spoken_name: str) -> ResolutionResult: ...
```
Matches an **open** "name on the account" answer against the candidate set; resolves to `resolved_single` only on exactly one match. Zero or >1 matches stay unresolved. **Candidate names are never read back to the caller** (preserved from the T006 shim). No household-specific detail is revealed until exactly one candidate is confirmed.

## R3 — Review queue (never auto-merge)

```python
def propose_grouping(clinic_id: str, evidence: dict,
                     proposal_type: Literal["probable_duplicate","collision","merge_candidate"]) -> str: ...
```
Probable duplicates, shared-line collisions, and merge candidates are written to `household_review_queue` with `status="pending"` and evidence. **No code path silently merges records** (FR-004). Staff approve/reject/defer; automatic identification proceeds only on unambiguous single matches.

## R4 — Verification bar (tiered, config-driven policy)

```python
@dataclass
class VerificationPolicy:                       # from config/relationship/verification_policy.<clinic>.yaml
    sensitivity: dict[str, Literal["low","high"]]   # action -> tier
    factors_required: dict[str, int]                # low: 1, high: 2

@dataclass
class ChallengeResult:
    outcome: Literal["passed","failed","deferred_staff_callback"]
    factors_presented: list[str]

def require_verification(action: str, party_id: str,
                         binding_level: VerificationLevel) -> ChallengeResult: ...
```

- Soft-confirm (`phone_match`) is **identification only** — never authorizes a change (FR-008/017).
- Low-sensitivity (reschedule/cancel) → **1** knowledge factor (e.g. pet name + appointment day). High-sensitivity (contact-info edit, refill request) → **2** factors or `deferred_staff_callback` (FR-018).
- **Factor validation sources & match logic (FR-018, H3)** — a factor passes **only** on a match against its authoritative source, never on being merely prompted:
  - `pet_name` → validated against the caller's confirmed household roster (`patient_household_link` for that `household_id`), normalized **exact-or-first-token** match (case/whitespace-folded; `"Rex"` matches `"Rex Alvarez"`). Only `status='active'` patients count; deceased/rehomed pets never satisfy the factor.
  - `appointment_day` → validated against the **010 booking/schedule store** for the household's upcoming/recent appointments; the spoken day must match a real scheduled day.
  - A value that resolves to **no match** in the source **fails** the factor (`outcome="failed"`); a wrong value can never clear the bar. `factors_presented_json` records which factor and pass/fail, never the raw secret value.
- Failure → block the change, leave state unchanged, offer staff callback, log the attempt (FR-019, SC-005).
- **Mid-call escalation** of sensitivity re-applies the higher bar before the sensitive action (edge case).
- Every challenge persists a `verification_challenge` row (append-only; secret factor values are never stored raw).

## R5 — C3 ChannelBinding tier reconcile (**non-mutating boundary adapter**, H2)

R5 is a **one-way translation adapter at the core-binding edge — it mutates nothing in 010.** 010 exposes **two** vocabularies and both keep their exact string values everywhere in 010 code and tests: the shim `VerificationLevel = none | soft_confirmed | strong` (`channel_binding_shim.py:19`) and `VerificationState = unverified | soft_confirmed` (`models.py`). The 116-green suite hard-asserts these strings (`== "none"`, `== "soft_confirmed"`, `VerificationState.SOFT_CONFIRMED.value == "soft_confirmed"`); the adapter never rewrites them — it only maps a copy onto core's tier at the moment 011 hands a binding to core.

**Boundary adapter — every value of BOTH 010 enums enumerated:**

| Source enum | 010 value (unchanged in 010) | core `verification_level` |
|---|---|---|
| `VerificationState` | `unverified` | `unverified` |
| `VerificationLevel` (shim) | `none` | `unverified` |
| `VerificationLevel` / `VerificationState` | `soft_confirmed` | `phone_match` |
| `VerificationLevel` (shim) | `strong` | `identity_confirmed` |

- The intermediate core tier (`code_verified`; `otp_verified` is **unused**) is **not** a target of this boundary translation — 010 carries no knowledge-factor state, so it never emits a value that maps there. `code_verified` is reached only through **011's own** verification progression (R4 `require_verification`: 1 factor → `code_verified`, 2 factors → `identity_confirmed`), which produces core tiers directly and does not pass through this adapter.
- Translation is total over both enums (every listed value has exactly one target) and one-way; there is no reverse mapping that writes a 4-tier value back into 010's 3-value/2-value enums.
- `party_candidates` on the binding = the resolver's candidate set (Thoth party IDs = `entity_ref`s). Audience scope derives from tier + role, never caller-ID alone.
