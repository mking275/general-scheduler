# Feature 010 — Vera Voice (VP-3, cycles 3a + 3b): Task List

**Branch**: `010-vera-voice` · **Target**: General_Scheduler repo (feature branch). Plan targets the VP-1 convergence platform; per the implementation-reality binding, **everything external runs in sim/dual-mode** (Twilio Media Streams bridge + both `RealtimeModelPort` impls get simulator counterparts mirroring `backend/sms_gateway.py`'s auto-detect pattern), so the entire list is completable and testable with **zero live telephony / LLM-audio calls**. Live-mode is a config swap, deferred to the Pilot-Activation section.

**Datastore for this build**: the 8 voice tables run on a **local PostgreSQL via `docker-compose`** (matching the data-model's "Postgres + RLS, not SQLite" mandate), app-level `clinic_id`/`party_id` scoping standing in for full RLS in the single-clinic build (per the plan's VP-1-slip degradation). The **demo repo's SQLite remains in use for the demo track only** — the voice/platform track does not regress to SQLite (external-LLM transcripts + consent records need the envelope plane).

**Coverage**: FR-001–FR-030 (all 30 have ≥1 owning task; the previously-gapped FR-004, FR-014, FR-019 are now owned by T042, T041, T043 respectively) · SC-001–SC-007 · data-model 8 tables · contracts A1–A3 (shimmed) + B1–B6 (built). **43 tasks total.**

**Path note (plan reconciliation)**: The plan's project structure lists the L3 tier as `voice/` at repo root. All existing Python (`models.py`, `agents/`, `sms_gateway.py`) lives under `backend/`, and the L3 modules import from it, so the plan's `voice/` package is rooted at **`backend/voice/`**; config stays at repo-root `config/voice/` as the plan specifies. Tests under `backend/tests/voice/`.

**Legend**: `[P]` parallelizable · `[US#]` maps to spec user story · `[MARKETING]` customer-visible / announcement-blocking · `[SHIM — extract post-pilot]` prototype stand-in for core L1/L2 (built here so the build never blocks on core's reply).

---

## Phase 1 — Setup

- [X] T001 [P] Create `backend/voice/` package (`backend/voice/__init__.py`) + `backend/voice/shims/__init__.py` + repo-root `config/voice/` dir; add realtime deps (`websockets`, `google-genai`, `openai`, `audioop-lts`, `PyYAML`; `twilio` already present) to `backend/requirements.txt`.
  - *Verify*: `python -c "import backend.voice"` succeeds and `pip install -r backend/requirements.txt` is clean.
- [X] T002 [P] Append the 8 voice entities + enums (`call_outcome` contained|booked|escalated|deflected + `containment_flag` boolean, `verification_state`, `gate_decision` advise|propose|do|reject, escalation `trigger`/`transfer_outcome`, `model_provider`) as Pydantic models to `backend/models.py` per `data-model.md`.
  - *Verify*: models import; the `RefillRequestDraft` status field type admits **only** `draft_vet_review`.
- [X] T003 [P] Create config fixtures: `config/voice/disclosure_script.en.txt` (FR-002 first utterance), `config/voice/clinic_voice_config.goldsmith.yaml` (hours, `after_hours_window`, on-call targets, ER directory, `max_hold_ms`, filler, `low_confidence_threshold: 0.6`, `slo_latency_ms: 3000`), `config/voice/triage_protocol.goldsmith.sample.yaml` (**unsigned** placeholder; VP-9 signs the real content), and `backend/voice/config/pricing.yml` (per-provider cost-rate fixture: `$/audio-min` in + out and `$/1k tokens` for `gemini_live` and `openai_realtime`; the cost-per-call source for T032/FR-030).
  - *Verify*: all four parse; disclosure text contains "AI", "recorded"/"transcribed", and "emergency"; `clinic_voice_config` carries `after_hours_window`, `low_confidence_threshold`, and `slo_latency_ms`; `pricing.yml` has audio-in/out and token rates for both providers.

---

## Phase 2 — Foundational (blocking prerequisites for all phases)

- [X] T004 `VoiceRepository` in `backend/voice/voice_repository.py` — CRUD + append-only ops for all 8 tables + `init_db()` targeting **local PostgreSQL via `docker-compose`** (NOT SQLite; matches data-model). RLS-ready with app-level `clinic_id`/`party_id` scoping standing in for full RLS in the single-clinic build (plan's VP-1-slip degradation). Enforce `CHECK (status = 'draft_vet_review')` on `refill_request_draft`. (deps: T002)
  - *Verify*: `init_db()` creates the 8 tables on the docker-compose Postgres instance; inserting a `refill_request_draft` with any non-`draft_vet_review` status raises the CHECK violation.
- [X] T005 Dual-mode env resolver + scripted **call simulator** in `backend/voice/sim.py`, mirroring `sms_gateway.py` auto-detect (`VOICE_LIVE` force flag + credential presence → `is_live()`); simulator feeds scripted caller audio/transcript + line events (silence, dtmf, hangup) into the bridge with zero live telephony.
  - *Verify*: `is_live()==False` with no creds; sim replays a scripted call and emits ordered turn events.
- [X] T006 [SHIM — extract post-pilot] `ChannelBinding` party-model shim in `backend/voice/shims/channel_binding_shim.py` per contract A1 (`candidate_parties` set + `verification_level` + `audience_scope`).
  - *Verify*: a shared inbound number returns >1 `candidate_parties`; an unknown number yields an ephemeral party at `caller_unverified` scope; the identity-safe disambiguation dialog matches an open "name on the account" answer against the candidate set and soft-confirms exactly one **without enumerating candidate names aloud** (FR-005) — an unmatched answer stays unverified.
- [X] T007 [SHIM — extract post-pilot] L2 `bridge_inbound()` → `converse_turn()` + `TurnHooks` **pre-speak interposition** shim in `backend/voice/shims/l2_bridge_shim.py` per contract A3, registry-marked `prototype`; `pre_speak` carries override authority over model output before render. (deps: T006)
  - *Verify*: a `pre_speak` returning `TurnDecision(action="replace", ...)` replaces the model's draft output before it is spoken (asserted in sim).
- [X] T008 [SHIM — extract post-pilot] `consent_check()` shim in `backend/voice/shims/consent_shim.py` per contract A2 (channel-scoped opt-out registry).
  - *Verify*: an opted-out party returns a deny `ConsentDecision`; default party returns allow.

---

## Phase 3 — Phase A: Bridge + Model Port (US1 / US2 foundation)

- [X] T009 [US1] μ-law 8 kHz ↔ PCM 16/24 kHz transcode in `backend/voice/transcode.py`.
  - *Verify*: round-trip 8 kHz μ-law → 16 kHz PCM → 8 kHz μ-law stays within amplitude tolerance on a fixture tone.
- [X] T010 [US1] `RealtimeModelPort` protocol in `backend/voice/realtime_model_port.py` per contract B1 (`connect`/`send`/`on`/`interrupt`/`resume`). (deps: T001)
  - *Verify*: protocol imports; both adapter classes typecheck as satisfying it.
- [X] T011 [P] [US1] `GeminiLiveAdapter` (primary) in `backend/voice/gemini_live_adapter.py` — live + **sim** dual-mode; sim emits scripted `partial`/`final`/`tool_call`/`interrupted` events. (deps: T005, T010)
  - *Verify*: sim mode drives a full turn with no live API call; `is_live()` gates real connect.
- [X] T012 [P] [US1] `OpenAIRealtimeAdapter` (fallback) in `backend/voice/openai_realtime_adapter.py` — same port, live + sim; selected by `model_provider_pref` config swap. (deps: T005, T010)
  - *Verify*: setting `model_provider_pref=openai_realtime` selects it; sim drives an equivalent turn.
- [X] T013 [US1] Twilio Media Streams WS bridge in `backend/voice/media_stream_bridge.py` — WS ↔ `RealtimeModelPort`, μ-law framing; live + **sim** (sim uses T005 harness, no Twilio). (deps: T009, T010, T005)
  - *Verify*: sim bridge streams audio frames port↔caller both directions; dual-mode flag honored.
- [X] T014 [US1] Transparent session resumption (`contextWindowCompression`; 10-min WS / 15-min cap) via `resume()` in adapters + bridge. (deps: T013)
  - *Verify*: an injected mid-call WS drop resumes without dropping the caller; `session_resume_count` increments and consent linkage is preserved (not re-disclosed).

---

## Phase 4 — Phase B: Turn loop + adapter guarantees (safety spine)

- [X] T015 [US1] `turn_loop.py` per contract B3 — per turn: `triage_protocol.step` → `autonomy_gate.classify` → `pre_speak` hook → speak; wires the T007 shim hooks + barge-in signaling. (deps: T007, T013)
  - *Verify*: every turn passes through `pre_speak` before render (asserted over a multi-turn sim call).
- [X] T016 [US1] [MARKETING] Disclosure-before-model guarantee in `backend/voice/adapter_guarantees.py` — first utterance = `disclosure_script`, played before the model engages, on 100% of calls (FR-002/FR-003). (deps: T013)
  - *Verify*: across 100 sim calls the disclosure is turn `seq=1` on every call; `consent_recorded_at` set = disclosure time (SC-001).
- [X] T017 [US2] [MARKETING] Escalation watchdog with **independent transfer authority** in `backend/voice/adapter_guarantees.py` — fires on `protocol_flag` | literal "emergency" | silence-threshold even if the model stalls or misroutes (FR-017). (deps: T015; **soft-dep T020** — the literal-"emergency"/silence branches are testable without the protocol engine, but the `protocol_flag` branch needs T020's engine to emit a flag; that path is fully validated in T035, which deps T021.)
  - *Verify*: with model-stall injection the watchdog triggers `warm_transfer` within SLO and records `watchdog_fired=true`; 0 silent drops.
- [X] T018 Append-only transcript + `call_turn` event logging on every session in `adapter_guarantees.py` (FR-021/FR-024). (deps: T004, T015)
  - *Verify*: every turn writes an immutable `call_turn` row; any UPDATE/DELETE attempt on a logged turn is rejected.
- [X] T019 [US2] Barge-in detection + backchannel filter in `backend/voice/barge_in.py` — server VAD, <400 ms detect; "emergency" always cuts through; backchannels ("uh-huh") do not misfire. (deps: T013)
  - *Verify*: sim "emergency" interrupts Vera within 400 ms; "uh-huh" injected mid-utterance does not trigger barge-in.

---

## Phase 5 — Phase C: Triage protocol engine (US2)

- [X] T020 [US2] Deterministic keyword/urgency state-machine **engine** + versioned YAML loader in `backend/voice/triage_protocol.py` (keywords → urgency class → routing target; `slo: {escalation_on_flag: 1.0}`). (deps: T002)
  - *Verify*: the sample protocol loads; "collapsed" and "not breathing" resolve to the emergency urgency class.
- [X] T021 [US2] Protocol **override authority** — engine `step()` output overrides model output inside `turn_loop` `pre_speak` (FR-011/FR-015/FR-016). (deps: T015, T020)
  - *Verify*: a model proposing a booking during a protocol-flagged turn is overridden to `escalate`; no write committed.
- [X] T022 [US2] Protocol regression harness + **signature gate** — an active `triage_protocol` requires `signed_by`/`signed_at`; unsigned blocks live emergency handling. (deps: T004, T020)
  - *Verify*: an unsigned protocol blocks live mode (allowed in sim only); the keyword regression set passes with zero misroutes.

---

## Phase 6 — Phase D: Verbs + prefetch/hold + autonomy gate + refill reconcile (US1 / US3)

- [X] T023 [US1] [MARKETING] `verbs.py` book / reschedule / availability into the existing pipeline (`booking_agent.confirm_booking`/`cancel_booking`, `availability_agent`) — read-back before write, **idempotent**, no bypass writes (FR-008/FR-009/FR-010). (deps: T015)
  - *Verify*: a booking flows Intake→Match→Solve→Dispatch and appears in the schedule; a retry carrying the same `booking_token` (= hash(clinic_id, slot_id, patient_ref, retry_nonce)) returns the original booking with no double-write; the `UNIQUE(clinic_id, slot_id, patient_ref)` active-booking constraint rejects a second active booking of the same slot for the same patient (including from a fresh call-back session); a **different** patient booking the same slot in the same call is **not** deduped.
- [X] T024 [US1] Unverified-scope enforcement in `verbs.py` — unverified callers limited to `availability` + `intake_capture`; never read/act on an existing client's records (FR-006). (deps: T023, T006)
  - *Verify*: an unverified party invoking `book()` against an existing-client record is rejected; `availability()` and `intake_capture()` succeed.
- [X] T025 [US1] `prefetch.py` `prefetch_context` (schedule slots, clinic config, VP-4a household summary @ `audience_scope`) fired at answer / soft-confirm; VP-4a household summary consumed via the **`HouseholdSummary` stub interface (contract A4)** — frozen fields `party_id`, `display_name_for_greeting`, `household_patients[{name, species}]`, `last_visit_summary_line`, `audience_scope`, `verification_level` (all nullable); the stub returns `None` when VP-4a is absent (parallel dependency). (deps: T006, T023)
  - *Verify*: after soft-confirm, slots + clinic config are cached and the next turn reads cache with no blocking lookup; with the VP-4a stub returning `None` the call proceeds in unverified scope with no greeting-name leak.
- [X] T026 [US1] Bounded hold pattern `hold(max_hold_ms, filler_script)` on cache miss in `backend/voice/prefetch.py` (D2 async-tool-gap mitigation). (deps: T025)
  - *Verify*: a cache-miss lookup emits the filler and returns within `max_hold_ms`; no dead air on the sim call.
- [X] T027 [US1] `autonomy_gate.py` — synchronous C4 `classify` authorizing every write and every escalation. **Live voice gate is restricted to `do` | `reject` | `escalate`**; `advise`/`propose` never act on-call — they map to post-call artifacts (`advise` → morning-briefing item, `propose` → draft for review) per contracts B3. Rejects any `auto_approved` disposition on the voice channel; `do`-class never enabled for clinical verbs (FR-011/FR-012). (deps: T015)
  - *Verify*: the live gate only ever acts on `do`/`reject`/`escalate`; a classification of `advise` or `propose` produces **no live spoken action** and is routed to a post-call artifact (briefing item / draft); the gate rejects any `auto_approved` disposition and blocks `do`-class for clinical/assessment verbs; the model narrates, never decides.
- [X] T028 [US3] [MARKETING] Refill-draft verb in `backend/voice/verbs.py` — writes `refill_request_draft` (`status='draft_vet_review'`) directly; **no code path to `PrescriptionAgent.request_refill`** (the `auto_approved` branch at `backend/agents/prescriptions.py:124`); gate guard rejects `auto_approved` (FR-022/FR-023, SC-005). (deps: T027, T004)
  - *Verify*: **0 refill auto-approvals via the voice path in the test suite** — refill requests with `refills_remaining > 0` still produce only a `draft_vet_review` record, and `request_refill` is never called (import/call-graph assertion).

---

## Phase 7 — Phase E: Warm transfer + overflow fallback (US2 / US5)

- [X] T029 [US2] [US5] [MARKETING] `warm_transfer.py` Twilio Conference + Dial with whisper summary to the highest-priority `on_call_target`; live + **sim** (FR-018). (deps: T004, T017)
  - *Verify*: sim transfer whispers the call summary to the human **before** the caller is connected; target chosen by `on_call_target.priority` order.
- [X] T030 [US2] [US5] ER-directory readout + callback guarantee on no-answer; voicemail-with-callback last resort — never dead air (FR-020). Reuses `sms_gateway` outbound leg for the callback promise. (deps: T029)
  - *Verify*: sim no-answer falls through to ER-directory readout + callback promise; the call is never silently dropped.
- [X] T031 [US2] Escalation-event persistence + **no-partial-write** on abandoned booking — a mid-booking emergency abandons the booking with zero rows written (FR-016 edge case). (deps: T021, T023, T029)
  - *Verify*: injecting "emergency" mid-booking leaves zero booking rows and records an `escalation_event` with the fallback path taken.

---

## Phase 8 — Phase F: Telemetry + logging + morning briefing (US4)

- [ ] T032 `telemetry.py` `CallTelemetry` per contract B6 — `cost_usd` (from call #1, computed from the `backend/voice/config/pricing.yml` per-provider rate fixture; see T003/FR-030), turn latency p50/p95, `call_outcome` label + `containment_flag` (the metric source; booked ⊆ contained per F2), escalation detail, `barge_in_false_rate`, `model_provider`, `session_resume_count` (FR-027–FR-030). (deps: T018)
  - *Verify*: a sim call emits `cost_usd` (priced from `pricing.yml`) and p50/p95 latency; `containment_flag` is true for both a contained and a booked non-emergency call, and the SC-004 rate computes as `count(containment_flag) / non-emergency calls`.
- [ ] T033 [US4] Consent + no-training attestation persistence on `call_transcript` — `consent_record` (disclosure text + timestamp) + `vendor_no_training_attestation`; 6-month `retained_until` for protocol-flagged calls (FR-021/FR-026). (deps: T004, T016)
  - *Verify*: every `call_transcript` carries a `consent_record`; a flagged call's `retained_until` is ≥ 6 months out.
- [ ] T034 [US4] [MARKETING] Morning-briefing overnight rollup — view/query over `call_session` (+ `escalation_event`, `refill_request_draft` joins) projecting outcome + flagged follow-ups (callbacks, pending refills, escalations) into the existing briefing surface; delivered via reused `sms_gateway` outbound leg (FR-025). (deps: T004, T032)
  - *Verify*: overnight calls of each `call_outcome` appear in the briefing with outcome and flagged callbacks/refills/escalations.

---

## Phase 9 — Phase G: Test + SLO verification + red-team (gates go-live)

- [ ] T035 [US2] 100%-escalation SLO harness in `backend/tests/voice/test_escalation_slo.py` — scripted call set trips every protocol keyword + literal "emergency" at every turn position (incl. mid-booking); asserts barge-in, zero assessment language, warm transfer + summary. (deps: T017, T021, T029, T031)
  - *Verify*: **100% of protocol-flagged calls escalate to a human with 0 silent drops** (SC-002).
- [ ] T036 [US2] Model-stall / disconnect injection layer in the SLO harness (`backend/tests/voice/test_stall_injection.py`) — watchdog transfers within SLO despite a stalled/disconnected model. (deps: T035, T014)
  - *Verify*: with a stall injected on every flagged call, escalation completion = 100% and `watchdog_fired` is asserted on each.
- [ ] T037 Red-team scripted call set in `backend/tests/voice/test_red_team.py` — clinical-question probes ("is chocolate toxic?"), "are you a nurse/vet?", refill-with-refills-remaining, multi-household shared-line, session-limit crossing. (deps: T024, T028, T014, T027)
  - *Verify*: zero assessment language / self-identification as clinician (FR-012/FR-013); unverified scope held on shared lines; transparent resume across the session limit.
- [ ] T038 [US1] Barge-in benchmark on real 8 kHz call audio in `backend/tests/voice/test_barge_in_benchmark.py`. (deps: T019)
  - *Verify*: false-barge-in rate **< 2%** and detect p95 **< 400 ms** on the audio set (SC-007).
- [ ] T039 [US1] Booking-accuracy audit harness in `backend/tests/voice/test_booking_accuracy.py` — post-call read-back vs written slot; idempotency under retry/latency. (deps: T023)
  - *Verify*: booking accuracy **≥ 99%** on the audit set; no double-booking under injected retry/latency — same `booking_token` dedupes to the original booking, and the `UNIQUE(clinic_id, slot_id, patient_ref)` constraint holds across a simulated call-back retry from a new session (SC-003).
- [ ] T040 Disclosure-100% assertion across all fixtures + degraded/stateless-mode fallback test in `backend/tests/voice/test_disclosure_and_degraded.py` — VP-4a unavailable → unverified scope, call still completes (FR-007). (deps: T016, T024)
  - *Verify*: 100% first-utterance disclosure across fixtures (SC-001); a `degraded_mode` call completes in unverified scope without failing the call.
- [ ] T041 Informational-answer grounding in `backend/voice/verbs.py` `info_answer()` — hours / prep / pricing answers are drawn **only** from `clinic_voice_config`, never model priors; when the config has no value Vera declines rather than inventing one (FR-014). Add a red-team assertion to `backend/tests/voice/test_red_team.py`. (deps: T027, T037)
  - *Verify*: an hours/pricing question with the value present returns the config value; with the value absent Vera declines and offers to escalate; the red-team set asserts Vera **never invents** hours or prices not in `clinic_voice_config`.
- [ ] T042 [US1] After-hours boundary gate in `backend/voice/verbs.py` (or bridge admission) — an app-side check consuming `clinic_voice_config.after_hours_window` decides whether the voice line handles the call (FR-004). For the pilot the line may be after-hours-only at the telephony layer, **but the runtime gate MUST exist and be tested** so daytime scope stays out of 3a/3b. (deps: T003, T013)
  - *Verify*: a call inside `after_hours_window` is handled; a call outside it is not routed to Vera (declined / passed through); the boundary is read from config, not hard-coded.
- [ ] T043 [US2] Always-offer-to-escalate assertion added to the red-team set in `backend/tests/voice/test_red_team.py` — across probe calls Vera always offers a path to a human and never dismisses a stated concern (FR-019). (deps: T037)
  - *Verify*: every red-team probe that states a concern receives an offer to escalate; no probe path dismisses or refuses the concern without an escalation offer.

---

## Pilot-Activation (config-only; **NOT in this build**)

These are live-mode flips + external hard gates, deferred per the implementation-reality binding:
- Set real `TWILIO_*` + Media Streams webhook + `GEMINI_*` / `OPENAI_*` credentials; flip `VOICE_LIVE=true` (config swap over the T011/T012/T013 sim seams — no code change).
- VP-9 vet-signed AVMA-teletriage protocol content loaded + `signed_at` set (gates T022 live path).
- Counsel sign-off on consent / no-training vendor DPA clauses (FR-026/D9).
- VP-1 platform (Postgres + RLS) provisioned, or the single-clinic app-scoped Postgres degradation.
- VP-4a caller identity + household memory live (removes the T025 stub; enables the continuity moat).
- Core delivers L1/L2 with the pre-speak hook → replace the T006/T007/T008 shims (`[SHIM — extract post-pilot]`).

---

## Dependencies & Critical Path

**Phase order (blocking)**: Setup → Foundational → A → B → C → D → E → F → G. Within a phase, `[P]` tasks may run concurrently.

**Critical path (existential escalation-safety spine)**:
`T001 → T004 → T007 → T010 → T013 → T015 → T017 → T020 → T021 → T029 → T030 → T035 → T036`

**Parallel opportunities**: T001/T002/T003 (setup); T011‖T012 (both adapters behind the port); T009 with T010–T012; the three shims T006→T007 (T008 independent); Phase F telemetry (T032) with late Phase G harnesses.

**MVP scope**: US1 (answer + disclose + identify + book) = Setup + Foundational + Phase A + T015/T016/T018 + Phase D booking (T023–T027) — demoable containment. US2 emergency (Phase B watchdog + Phase C + Phase E) ships alongside per spec P1.

---

## Marketing Output
**Produced by**: speckit-tasks — 2026-07-09

### Demoable Milestones

1. **First-ring answer + disclosure** (after T013 + T016): Vera picks up in sim on the first ring and delivers the AI + recording + "say emergency" disclosure before any exchange — the "we never miss a call" proof.
2. **Book against the live schedule** (after T023–T027): soft-confirmed caller books/reschedules with read-back, straight through the existing pipeline — the containment payoff.
3. **Refill as a draft, never approved** (after T028): refill-with-refills-remaining lands in the vet queue as `draft_vet_review`, provably bypassing the auto-approve path — the trust/legal proof.
4. **Emergency → human, every time** (after T017 + T029 + T030): "my dog collapsed" barges in, warm-transfers with a whisper summary, and — with the on-call line killed — falls through to ER directory + callback, never dead air.
5. **Morning briefing rollup** (after T034): every overnight call surfaces with outcome, cost-per-call, and flagged follow-ups — the owner-facing recovered-revenue payoff.

### [MARKETING] Tagged Tasks Summary

| Task ID | Description | Reason |
|---|---|---|
| T016 | Disclosure-before-model guarantee | Customer-visible: the first thing every caller hears; also announcement-blocking (SC-001 100% disclosure). |
| T017 | Escalation watchdog with independent transfer authority | Announcement-blocking: SC-002 100% escalation is the existential safety gate — cannot launch without it. |
| T023 | Book/reschedule via existing pipeline | Customer-visible: the core happy-path booking a caller experiences; the containment value story. |
| T028 | Refill-draft override (no auto-approve) | Announcement-blocking: SC-005 zero autonomous refills is a hard legal/clinical gate for launch. |
| T029 | Warm transfer with whisper summary | Customer-visible: how a caller reaches a real person in an emergency; part of the SC-002 spine. |
| T034 | Morning-briefing overnight rollup | Customer-visible: the owner/staff-facing surface where recovered-call value becomes visible. |

**Total [MARKETING] tasks**: 6 of 43 tasks.
**Milestone**: All [MARKETING] tasks must be ✅ before launching or announcing this feature.
