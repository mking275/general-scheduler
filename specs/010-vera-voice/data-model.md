# Feature 010 — Vera Voice: Data Model

Eight new tables on the **VP-1 platform (Postgres + RLS)** — not SQLite. All rows are tenant/party-scoped via RLS (`clinic_id`; party-scoped tables also filter on `party_id`). TEXT/UUID primary keys, ISO-8601 timestamps, consistent with platform conventions. The transcript + event log are **append-only**.

Entity → table map (spec Key Entities): Call→`call_session`; Transcript→`call_transcript`; CallerIdentity→resolved via VP-4a `ChannelBinding` (referenced, not owned here); EscalationEvent→`escalation_event`; RefillRequestDraft→`refill_request_draft`; TriageProtocol→`triage_protocol`; MorningBriefingEntry→derived view over `call_session`.

---

## Table 1: `call_session`
One inbound after-hours call.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `clinic_id` | UUID FK | RLS scope |
| `inbound_number` | TEXT | E.164 |
| `party_id` | UUID NULL FK | VP-4a resolved party; NULL = unverified/ephemeral |
| `verification_state` | TEXT | `unverified` \| `soft_confirmed` |
| `channel_binding_id` | TEXT NULL | core L1 binding ref |
| `started_at` / `answered_at` / `ended_at` | TIMESTAMPTZ | `answered_at` proves first-ring answer |
| `call_outcome` | TEXT | descriptive outcome label: `contained` \| `booked` \| `escalated` \| `deflected`. **Not the containment metric** — a labelling field only (renamed from `disposition` so it is not read as the metric; F2). `booked` is a contained outcome. |
| `containment_flag` | BOOLEAN | **single source of the containment metric** — true whenever a non-emergency call is resolved without a human, **including bookings** (FR-027). SC-004 rate = `count(containment_flag = true) / non-emergency calls`. Independent of `call_outcome`. |
| `model_provider` | TEXT | `gemini_live` \| `openai_realtime` (which port impl served the call) |
| `degraded_mode` | BOOLEAN | set on fallback/stateless operation |
| `session_resume_count` | INT | transparent-resumption events |
| `cost_usd` | NUMERIC(8,4) | per-call COGS from call #1 (FR-030) |
| `consent_recorded_at` | TIMESTAMPTZ | = time disclosure delivered |
| `created_at` | TIMESTAMPTZ | |

## Table 2: `call_turn` (append-only)
One conversational turn; the auditable spine.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `call_session_id` | UUID FK | |
| `seq` | INT | monotonic within call |
| `role` | TEXT | `caller` \| `vera` \| `system` |
| `text` | TEXT | final transcript text |
| `is_final` | BOOLEAN | partial vs final |
| `started_at` | TIMESTAMPTZ | |
| `latency_ms` | INT NULL | turn latency (feeds p50/p95) |
| `barge_in` | BOOLEAN | caller interrupted Vera |
| `protocol_flag` | TEXT NULL | urgency class if the state machine tripped |
| `gate_decision` | TEXT NULL | `advise` \| `propose` \| `do` \| `reject` (C4) |
| `tool_calls_json` | JSONB | verbs invoked + prefetch/hold detail |

## Table 3: `call_transcript` (append-only)
Full recorded/transcribed content + consent attestation; retained for audit.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `call_session_id` | UUID FK | |
| `full_text` | TEXT | assembled transcript |
| `audio_ref` | TEXT | pointer to stored audio |
| `consent_record` | JSONB | disclosure text served + timestamp |
| `vendor_no_training_attestation` | TEXT | DPA reference (FR-026) |
| `retained_until` | TIMESTAMPTZ | ≥ 6 months for protocol-flagged calls (FR-021) |
| `created_at` | TIMESTAMPTZ | |

## Table 4: `escalation_event`
A protocol-flagged escalation and its outcome.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `call_session_id` | UUID FK | |
| `trigger` | TEXT | `explicit_emergency` \| `protocol_keyword` \| `low_confidence` (fires below `clinic_voice_config.low_confidence_threshold`) \| `human_request` \| `slo_breach` (fires above `clinic_voice_config.slo_latency_ms`) |
| `protocol_state` | TEXT | urgency class from the state machine |
| `triggered_at` | TIMESTAMPTZ | |
| `transfer_target_id` | UUID NULL FK | `on_call_target` used |
| `whisper_summary` | TEXT | summary handed to the human before connect |
| `transfer_outcome` | TEXT | `answered` \| `no_answer` \| `fallback_er_directory` \| `voicemail_callback` |
| `fallback_path` | TEXT NULL | path taken when no human answered |
| `watchdog_fired` | BOOLEAN | escalation forced by adapter watchdog (model stalled) |
| `resolved_at` | TIMESTAMPTZ | |
| `audit_retained_until` | TIMESTAMPTZ | 6-month audit window |

## Table 5: `refill_request_draft`
Captured refill request routed to vet review. **Never auto-approved; never touches `prescriptions.py::request_refill`.**

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `call_session_id` | UUID FK | |
| `party_id` | UUID FK | verified caller only |
| `patient_ref` | TEXT | pet identifier |
| `drug_name_asserted` | TEXT | as stated by caller (no dosing, no naming by Vera) |
| `status` | TEXT | **always `draft_vet_review`** (CHECK constraint) |
| `refills_remaining_at_capture` | INT NULL | recorded for the vet, does NOT gate approval |
| `created_at` | TIMESTAMPTZ | surfaced in morning briefing as awaiting vet action |

*Guard*: `CHECK (status = 'draft_vet_review')` — the auto-approve status is unrepresentable on this table.

## Table 6: `clinic_voice_config`
Per-clinic voice configuration (setup-time).

| Column | Type | Notes |
|---|---|---|
| `clinic_id` | UUID PK | |
| `after_hours_window` | JSONB | schedule defining "after hours" (3a scope) |
| `disclosure_script` | JSONB | per-locale first-utterance text (FR-002, default-on) |
| `triage_protocol_id` | UUID FK | → `triage_protocol` (versioned) |
| `er_directory_ref` | TEXT | ER directory readout source (VP-9) |
| `voice_params` | JSONB | voice, locale, VAD/barge-in tuning |
| `model_provider_pref` | TEXT | `gemini_live` default; `openai_realtime` fallback |
| `max_hold_ms` | INT | bounded hold ceiling |
| `filler_script` | TEXT | hold-pattern filler |
| `low_confidence_threshold` | NUMERIC | overflow trigger: confidence below this → `low_confidence` escalation (default `0.6`; B1) |
| `slo_latency_ms` | INT | overflow trigger: turn latency above this → `slo_breach` escalation (default `3000`; B1) |
| `vendor_no_training_attestation` | TEXT | active DPA reference |
| `updated_at` | TIMESTAMPTZ | |

## Table 7: `on_call_target`
Manual per-clinic escalation targets (VP-5 rota deferred). Ordered by priority.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `clinic_id` | UUID FK | |
| `label` | TEXT | e.g. "On-call DVM" |
| `phone` | TEXT | E.164 |
| `type` | TEXT | `on_call_vet` \| `er_partner` \| `overflow` |
| `priority` | INT | transfer attempt order |
| `active_window` | JSONB | static schedule when this target is live |
| `active` | BOOLEAN | |
| `created_at` | TIMESTAMPTZ | |

## Table 8: `triage_protocol`
Versioned vet-signed routing content (engine ours; content from VP-9).

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `clinic_id` | UUID FK | |
| `version` | TEXT | semver |
| `config_yaml` | TEXT | keywords → urgency class → routing target; `slo: {escalation_on_flag: 1.0}` |
| `signed_by` | TEXT | licensed vet (Goldsmith group) |
| `signed_at` | TIMESTAMPTZ | gate on any live emergency call |
| `active` | BOOLEAN | one active version per clinic |
| `created_at` | TIMESTAMPTZ | |

---

## Booking idempotency (FR-010)

Voice bookings write through the **existing booking pipeline** (`booking_agent.confirm_booking`), not a new voice table, so the idempotency guarantees live on the booking/schedule table the pipeline owns:

- **UNIQUE constraint** `(clinic_id, slot_id, patient_ref)` **for active bookings** (partial/filtered on active status so a later re-book of a cancelled slot is allowed). This makes a double-book of the same slot for the same patient impossible even across separate calls or a call-back.
- **`booking_token` TEXT column** on the booking record — client-generated `hash(clinic_id, slot_id, patient_ref, retry_nonce)`. The retry nonce is stable across retries and across a fresh call-back session (derived from party/patient + slot + date, **not** the volatile `call_session_id`). A repeated confirm with the same `booking_token` returns the original booking (dedupe), rather than erroring or double-writing.

The voice verb layer carries `booking_token` into `confirm_booking`; the `call_turn.tool_calls_json` records the token for audit. A session-scoped key (`call_session_id + slot`) is explicitly **not** used — it would wrongly dedupe a second patient booked into the same slot within one call and would fail to dedupe a caller retrying from a new session.

---

## Derived: Morning Briefing Entry
Not a table — a view/query over `call_session` (+ joins to `escalation_event`, `refill_request_draft`) for the overnight window, projecting outcome + flagged follow-ups (callbacks, pending refills, escalations) into the existing briefing surface (FR-025).
