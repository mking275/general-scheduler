# Feature 011 — Relationship Memory & Consent: Data Model

Thirteen net-new tables on the **VP-1 platform (Postgres + RLS)** — not SQLite. All rows tenant-scoped via RLS on `clinic_id`; party-scoped tables also filter `party_id` (the seam vocabulary standardized on `party_id` throughout, deliberately aligned with 010/C3's `PartyRef`/`party_id` and the A4 frozen field — M4). TEXT/UUID PKs, ISO-8601 (TIMESTAMPTZ) timestamps, consistent with the 010 `VoiceRepository` conventions. Resolution, reveal-decision, verification, consent-event, and inbound-message tables are **append-only** (the auditable spine — Constitution I).

Entity → table map (spec Key Entities): Household→`household`; Contact/Party→`household_contact`(+`contact_identifier`); Patient→existing `patients` + `patient_household_link`; Identity Resolution→`identity_resolution_event`; Verification Challenge→`verification_challenge`; Memory-Scoping Policy→`memory_scoping_policy`(+append-only `reveal_decision_log`); Consent Record→`contact_consent`(+append-only `consent_event`); Inbound Message/Opt-Out Event→`inbound_message`. Staff review→`household_review_queue`. Staff-role/audience source→`clinic_staff_role` (M5).

`entity_ref` columns everywhere use `{type}:{stable_id}` (`household:vah_*`, `client:ezyvet_c*`, `patient:ezyvet_p*`) — never names (research D2).

---

## Table 1: `household`
The family unit; anchor of shared relationship memory.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `clinic_id` | UUID FK | RLS scope |
| `entity_ref` | TEXT UNIQUE | synthesized `household:vah_*` |
| `display_name` | TEXT | e.g. "Alvarez household" — payload, not a key |
| `review_status` | TEXT | `confirmed` \| `proposed` (from review queue) |
| `created_at` / `updated_at` | TIMESTAMPTZ | |

## Table 2: `household_contact` (Party)
A person in a household. Replaces the flat single-owner record.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `clinic_id` | UUID FK | RLS |
| `household_id` | UUID FK | |
| `pims_client_id` | TEXT NULL | ezyVet stable id → `entity_ref` |
| `entity_ref` | TEXT | `client:ezyvet_c*` |
| `display_name` | TEXT | matching/greeting only, never spoken until confirmed |
| `household_role` | TEXT | `co_owner` \| `authorized_caller` \| `emergency_contact` |
| `active` | BOOLEAN | former co-owner → inactive (edge case) |
| `created_at` | TIMESTAMPTZ | |

## Table 3: `contact_identifier`
Multi-phone / multi-email per contact — the lookup index. **This is what the resolver queries; the `LIMIT 1` bug lived on the single-phone-per-owner assumption this table removes.**

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `party_id` | UUID FK | |
| `clinic_id` | UUID FK | RLS |
| `id_type` | TEXT | `phone` \| `email` |
| `value_normalized` | TEXT | 10-digit phone / lowercased email (indexed) |
| `value_raw` | TEXT | as stored in PIMS |
| `is_primary` | BOOLEAN | |
| `source` | TEXT | `pims` \| `inbound` |
| `created_at` | TIMESTAMPTZ | |

*Index*: `(clinic_id, id_type, value_normalized)` — a lookup returns **all** matching rows (candidate set), never `LIMIT 1`.

## Table 4: `patient_household_link`
Pet ↔ household (multi-pet native). Migration preserves every owner→patient link (SC-007).

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `patient_id` | UUID FK | existing `patients` |
| `household_id` | UUID FK | |
| `clinic_id` | UUID FK | RLS |
| `pims_patient_id` | TEXT NULL | → `entity_ref` |
| `entity_ref` | TEXT | `patient:ezyvet_p*` |
| `status` | TEXT | `active` \| `deceased` \| `rehomed` — deceased excluded from soft-confirm reason guesses (edge case), flagged for staff, never volunteered |
| `created_at` | TIMESTAMPTZ | |

## Table 5: `identity_resolution_event` (append-only)
A match event from an inbound identifier to a candidate set.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `clinic_id` | UUID FK | RLS |
| `channel` | TEXT | `voice` \| `sms` \| ... |
| `inbound_identifier_normalized` | TEXT | |
| `identifier_type` | TEXT | `phone` \| `email` \| `name` |
| `candidate_set_json` | JSONB | `[{party_id, household_id, score}]` — **full set, never reduced** |
| `match_count` | INT | 0 / 1 / >1 |
| `outcome` | TEXT | `resolved_single` \| `soft_confirmed` \| `ambiguous_multi` \| `unmatched` |
| `confirmed_party_id` | UUID NULL FK | set only after neutral disambiguation resolves to exactly one |
| `resolved_at` | TIMESTAMPTZ | |

## Table 6: `household_review_queue`
Never-auto-merge staff queue for probable duplicates / collisions (FR-004).

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `clinic_id` | UUID FK | RLS |
| `proposal_type` | TEXT | `probable_duplicate` \| `collision` \| `merge_candidate` |
| `subject_refs_json` | JSONB | the entity_refs / party_ids involved |
| `evidence_json` | JSONB | why flagged (shared phone, name similarity, …) |
| `status` | TEXT | `pending` \| `approved` \| `rejected` \| `deferred` |
| `reviewed_by` | TEXT NULL | staff id |
| `reviewed_at` | TIMESTAMPTZ NULL | |
| `created_at` | TIMESTAMPTZ | |

## Table 7: `verification_challenge` (append-only)
A knowledge-factor challenge for a voice-initiated change (FR-017–019).

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `clinic_id` | UUID FK | RLS |
| `call_session_id` | UUID NULL FK | → 010 `call_session` |
| `party_id` | UUID NULL FK | soft-confirmed party |
| `action_requested` | TEXT | `reschedule` \| `cancel` \| `contact_edit` \| `refill_request` |
| `sensitivity_tier` | TEXT | `low` \| `high` |
| `factors_required` | INT | 1 (low) / 2 (high) |
| `factors_presented_json` | JSONB | which factors offered + pass/fail (no secret values stored raw) |
| `outcome` | TEXT | `passed` \| `failed` \| `deferred_staff_callback` |
| `created_at` | TIMESTAMPTZ | |

## Table 8: `memory_scoping_policy`
Per-audience reveal rules as C1 policy data (default-deny). Versioned like 010's `triage_protocol`.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `clinic_id` | UUID FK | RLS |
| `version` | TEXT | semver |
| `policy_yaml` | TEXT | three fields (contract C, H1): `allow_classes{audience: [fact_class]}` (positive content classes) + `scope_predicates{audience: [own_household_only\|own_clinic_only]}` (row filters) + `kind_to_class{fact_kind: fact_class}` (recall-kind → class bridge). **Absence of an audience from `allow_classes`, a class not listed, or an unmapped kind all = deny** |
| `signed_by` | TEXT | VP-9 policy owner |
| `active` | BOOLEAN | one active version per clinic |
| `created_at` | TIMESTAMPTZ | |

## Table 9: `reveal_decision_log` (append-only)
Every reveal decision, staff-visible (FR-016, SC-001 audit spine).

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `clinic_id` | UUID FK | RLS |
| `interaction_ref` | TEXT | `call_session:*` / `thread:*` |
| `audience` | TEXT | `owner` \| `manager` \| `staff` \| `client_verified` \| `caller_unverified` |
| `fact_kind` | TEXT | the recall `kind` requested (raw Thoth kind) |
| `fact_class` | TEXT NULL | class resolved via `kind_to_class`; NULL when the kind is unmapped (H1) |
| `entity_ref` | TEXT NULL | subject of the fact |
| `decision` | TEXT | `revealed` \| `withheld` |
| `rule_matched` | TEXT NULL | policy rule id, or NULL |
| `reason` | TEXT | `explicit_allow` \| `default_deny_no_rule` \| `wrong_household` \| `unmapped_kind` |
| `created_at` | TIMESTAMPTZ | |

## Table 10: `contact_consent`
Current channel-aware AI-contact preference (FR-021/024).

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `clinic_id` | UUID FK | RLS |
| `party_id` | UUID FK | |
| `channel` | TEXT | `voice` \| `sms` \| `email` \| `portal` |
| `ai_contact_allowed` | BOOLEAN | current state (default true) |
| `source` | TEXT | `inbound_stop` \| `staff` \| `portal` |
| `changed_at` | TIMESTAMPTZ | |
| `changed_by` | TEXT | party/staff/system |

*Unique*: `(party_id, channel)` — one current row per channel; history in `consent_event`.

## Table 11: `consent_event` (append-only)
Audit trail of every consent change (revocable + reversible, FR-021).

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `party_id` | UUID FK | |
| `clinic_id` | UUID FK | RLS |
| `channel` | TEXT | |
| `action` | TEXT | `opt_out` \| `opt_in` |
| `keyword` | TEXT NULL | `STOP` / `START` / … |
| `inbound_message_id` | UUID NULL FK | provenance |
| `created_at` | TIMESTAMPTZ | |

## Table 12: `inbound_message` (append-only)
The net-new inbound intake path (`sms_gateway.py` is outbound-only today).

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `clinic_id` | UUID FK | RLS |
| `channel` | TEXT | `sms` \| `voice_dtmf` \| ... |
| `from_identifier_normalized` | TEXT | feeds the resolver |
| `body` | TEXT | raw inbound content |
| `matched_keyword` | TEXT NULL | `STOP` \| `START` \| `HELP` \| NULL |
| `action_taken` | TEXT | `opt_out_recorded` \| `opt_in_recorded` \| `routed_to_staff` \| `none` — a non-keyword message routes to staff, never auto-actioned (edge case) |
| `received_at` | TIMESTAMPTZ | SC-006 clock start |

## Table 13: `clinic_staff_role`
Per-user staff role — the **source of the owner/manager/staff audience** (M5, FR-012). Audience for a staff-side interaction is derived from this role (via the R5 adapter / T017), never from a shared login identity (edge case: shared staff login → audience inferred from role). Voice callers are always client-tier in 4a; this table only classifies staff-side interactions.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `clinic_id` | UUID FK | RLS |
| `staff_user_id` | TEXT | staff/login id (→ `staff:*` entity_ref) |
| `role` | TEXT | `owner` \| `manager` \| `staff` — maps 1:1 to the staff-side reveal audiences |
| `active` | BOOLEAN | |
| `created_at` | TIMESTAMPTZ | |

---

## Migration (SC-007 — 100% link preservation)
**Source (M1)**: the production run reads the **platform Postgres `owners` table** (hydrated by VP-1/009 envelope ingestion from ezyVet); the demo SQLite `owners` is demo-track only, and dev/test uses a synthetic fixture via a SQLite→PG hydration helper so the migration always reads a Postgres source.

One-time forward migration from the flat model:
- each `owners` row → one `household` (`household:vah_*`) + one `household_contact` (`co_owner`) + `contact_identifier` rows for its phone and email;
- each existing owner→patient link → one `patient_household_link`.
- **Assertion gate**: `count(patient_household_link) == count(prior owner→patient links)` and `count(distinct migrated patients) == count(patients)` — zero orphaned pets, zero lost contacts. Fails the migration loudly rather than silently dropping.

## Consumed (not owned here)
- **Core Thoth**: `dt_vera_memory` (recall/recall_by_kind, temporal `valid_from/until`, `entity_ref`, access tracking), `dt_vera_thread` (`thread_id` binding). 011 reads via the `ScopedRecall` wrapper; it does not migrate or own these.
- **010 `call_session` / `call_turn`**: verification challenges and reveal decisions reference the voice call; not duplicated here.
