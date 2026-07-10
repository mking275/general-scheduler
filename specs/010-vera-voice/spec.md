# Feature Specification: Vera Voice — The After-Hours Front Door

**Feature Branch**: `010-vera-voice`

**Created**: 2026-07-09

**Status**: Draft

**Input**: User description: "Vera Voice (VP-3, cycles 3a+3b) — the same Vera who runs the waitlist and the morning briefing now answers the clinic phone after hours. She answers immediately, discloses she is AI, identifies the caller, books and reschedules, takes refill requests as drafts for the vet, gets true emergencies to a human fast, transcribes and logs every call, and reports it all in the morning briefing — so the clinic never loses a client to a missed call and staff never drown in the phones."

---

## Clarifications

### Session 2026-07-09

- Q: For the 3a pilot, is VP-4a caller identity landing in parallel (continuity moat live) or does 3a ship stateless with identity as a fast-follow? → A: Parallel — VP-4a caller identity + household memory ships alongside 3a for the October pilot demo, with soft-confirm live at pilot. Stateless operation is the documented graceful-degradation fallback only. (Matt, 2026-07-09)
- Q: Does a machine-readable on-call rota exist at the pilot clinic, or is on-call routing a manual per-clinic configuration prerequisite? → A: Manual per-clinic configuration for the pilot — a static on-call contact/schedule entered at clinic setup; machine-readable rota integration deferred to VP-5.
- Q: Is the human overflow backstop a staff-only on-call rota, or a contracted answering service (GuardianVets/VetTriage-class partner) behind the rota? → A: Staff on-call rota only for the pilot; no contracted answering service. Evaluate a VetTriage-class backstop with real call-mix data before scale. GuardianVets explicitly excluded (funded direct competitor — call data must not flow to them). (Matt, 2026-07-09)
- Q: Is the 50–60% after-hours containment target final or provisional? → A: 50–60% stays provisional, finalized after the 2-week Goldsmith after-hours call-log pull (now a pilot week-1 ground-truth item). Escalation 100%, booking-accuracy ≥99%, and disclosure 100% SLOs are firm regardless.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — After-Hours Call: Answer, Disclose, Identify, Book (Priority: P1)

A client calls the clinic at 9pm. Instead of voicemail, Vera answers on the first ring, discloses in her first sentence that she is an AI assistant, that the call is recorded and transcribed, and that the caller can say "emergency" at any time. She matches the inbound number to a client record, soft-confirms ("Is this Mrs. Alvarez?"), and — for a routine request — books or reschedules an appointment against the live schedule, reading the details back for confirmation before anything is written.

**Why this priority**: This is the containment engine and the entire 3a pilot deliverable. Without a reliable answer-and-book flow there is no product, no recovered missed-call revenue, and nothing to measure. Every other story hangs off this one.

**Independent Test**: Place an after-hours call from a known client number; verify the first utterance carries the full AI + recording + transcription + "say emergency" disclosure, that Vera soft-confirms the caller's identity, and that a booked appointment appears in the schedule matching the details read back on the call.

**Acceptance Scenarios**:

1. **Given** an inbound after-hours call, **When** Vera answers, **Then** before any other exchange the first utterance discloses she is an AI assistant, the call is recorded and transcribed, and the caller may say "emergency" at any time; where the number matches one client record she then soft-confirms identity by name and enters that client's scope only after confirmation.
3. **Given** a verified caller requests a booking, **When** Vera finds a slot, **Then** she reads back date, time, provider, and reason, books only after explicit confirmation, and the booking appears in the schedule through the normal pipeline (idempotent on retry), logged as contained.
4. **Given** the caller's number matches no record (or identity cannot be confirmed), **When** Vera proceeds, **Then** she is limited to schedule-availability and new-client intake capture and never reads back any existing client's records.

---

### User Story 2 — Emergency Detected, Human on the Line Every Time (Priority: P1)

A caller says "my dog just collapsed" or says "emergency." Vera does not assess, diagnose, or reassure clinically — she runs the vet-signed routing protocol, tells the caller she is connecting them to a person, and warm-transfers to the on-call vet or ER partner, handing over a call summary. If no human is immediately reachable, the caller is given the ER directory and a callback is guaranteed — never dead air, never a silent drop.

**Why this priority**: Under-triage is the one existential failure. A single mishandled emergency ends the voice program and taints the whole envelope. Safe escalation is non-negotiable and ships alongside answering, not after it.

**Independent Test**: Place a call that trips a protocol keyword (or say "emergency"); verify Vera immediately stops the current flow, uses zero assessment language, warm-transfers to a human with a summary, and — if the transfer target does not answer — falls through to the ER-directory-plus-callback path with a full transcript retained.

**Acceptance Scenarios**:

1. **Given** the caller says "emergency" or trips a protocol flag at any point, **When** Vera detects it, **Then** she interrupts whatever is in progress (barge-in) and moves to the escalation path immediately.
2. **Given** an escalation is triggered, **When** Vera responds, **Then** she uses routing language only — no diagnosis, prognosis, treatment, or drug naming/dosing — and never describes herself as a nurse, tech, or vet.
3. **Given** a warm transfer to the on-call human, **When** the human answers, **Then** they receive a call summary before the caller is connected.
4. **Given** no human answers the transfer, **When** the fallback fires, **Then** the caller receives the ER directory and a callback promise, the call is never dropped silently, and its full transcript is retained for the 6-month audit.

---

### User Story 3 — Refill Request as a Draft for the Vet, Never Autonomous (Priority: P2)

A client calls to ask for a refill of their pet's medication. Vera captures the request, confirms she has logged it, and tells the caller a vet will review it — she never states the refill is approved or filled, and she never triggers the system's existing auto-approve path even when refills remain.

**Why this priority**: Refill-request is a table-stakes floor verb, but autonomous approval is a hard legal and clinical no-go. This story exists specifically to override the platform's existing auto-approve behavior for the voice channel.

**Independent Test**: On an after-hours call, request a refill for a medication that has refills remaining; verify a draft-for-approval record is created for vet review and that the auto-approve path is not invoked.

**Acceptance Scenarios**:

1. **Given** a caller requests a refill, **When** Vera captures it, **Then** a draft-for-vet-approval record is created regardless of refills remaining, she confirms it was logged for vet review (never approved/filled), and it appears in the morning briefing as awaiting vet action.

---

### User Story 4 — Every Call Transcribed, Logged, and in the Morning Briefing (Priority: P2)

Every after-hours call — contained, booked, escalated, or deflected — is recorded, transcribed, and logged with its outcome, and surfaced in the practice's morning briefing so the owner and staff start the day knowing exactly what happened overnight and what needs follow-up.

**Why this priority**: Auditability is the trust and safety spine (it satisfies the verbose-log principle and the emergency audit) and the morning briefing is where the recovered-missed-call value becomes visible to the owner.

**Independent Test**: Place several after-hours calls of different outcomes; verify each produces a transcript and a log entry with caller, timestamp, and outcome, and that all appear in the next morning briefing with follow-up items flagged.

**Acceptance Scenarios**:

1. **Given** any completed call, **When** it ends, **Then** a transcript and a log entry (caller, timestamp, call outcome, containment flag) are persisted with the vendor no-training constraint and consent record honored.
2. **Given** the overnight call set, **When** the morning briefing is generated, **Then** every call appears with its outcome and any staff follow-up items (callbacks, pending refills, escalations) flagged.

---

### User Story 5 — Warm Human Overflow, Never Dead Air (Priority: P2)

When Vera cannot safely or confidently handle a call — a service-level breach, low confidence, or the caller simply asks for a person — she warm-transfers to a human overflow line with a summary; if no human is reachable, she takes a voicemail with a guaranteed callback. The caller is never met with silence or an abrupt hang-up.

**Why this priority**: The human backstop is what makes autonomy safe to ship and is the graceful-degradation guarantee behind both containment and escalation.

**Independent Test**: Force a low-confidence or human-requested condition; verify Vera offers and performs a warm transfer with summary, and that when the overflow target is unavailable she captures a voicemail with a callback promise rather than dropping the call.

**Acceptance Scenarios**:

1. **Given** the caller asks for a human, or confidence/SLO thresholds are breached (confidence below `clinic_voice_config.low_confidence_threshold`, default 0.6; or turn latency above `slo_latency_ms`, default 3000 ms), **When** Vera responds, **Then** she warm-transfers to the overflow line with a call summary.
2. **Given** the overflow line does not answer, **When** the fallback fires, **Then** Vera takes a voicemail with a callback promise — never dead air.

---

### User Story 6 — Daytime Overflow and Cross-Channel Continuity (Priority: P3)

*(Declared, thin — cycle 3c, post-pilot.)* When the daytime desk is saturated, overflow calls ring Vera before voicemail, and she recognizes the caller across channels ("Is this about Rex's follow-up?") — this is where the identity-continuity moat becomes visible. Bilingual (EN/ES) handling is gated on a phone-grade word-error-rate benchmark before any promise. Independent test deferred to 3c scoping.

---

### User Story 7 — Operations Dashboard and Cost-per-Call Telemetry (Priority: P3)

*(Declared, thin — cycle 3d, post-pilot.)* The containment, booking-accuracy, escalation, and cost metrics that are mandatory now (FR-027–FR-030) are surfaced in an operations dashboard, and the clinic's own number is ported in. Independent test deferred to 3d scoping.

---

### Edge Cases

- Caller's number matches multiple households or is uncertain → Vera runs the identity-safe disambiguation dialog (open "name on the account?" prompt, matched against the candidate set, **never enumerating candidate names aloud**) and stays in unverified scope until exactly one candidate is soft-confirmed. If the caller says "emergency" mid-booking, the in-progress booking is abandoned with no partial write and escalation takes over immediately.
- Caller asks a clinical question ("is chocolate toxic?") or whether Vera is a nurse/vet → Vera gives only generic non-diagnostic framing, offers to escalate, and states she is an AI assistant, not a veterinarian or tech.
- Realtime session exceeds the provider limit mid-call → it resumes transparently without dropping the caller; backchannels ("uh-huh") do not misfire barge-in.
- No on-call human and no ER directory configured for an emergency → the call is held open with a callback guarantee and flagged top-priority in the morning briefing; never silently ended.

---

## Requirements *(mandatory)*

### Functional Requirements

**Answering & Disclosure**
- **FR-001**: Vera MUST answer every inbound after-hours call immediately, before voicemail — no dead air on pickup.
- **FR-002**: The first utterance MUST disclose, on 100% of calls, that Vera is an AI assistant, that the call is recorded and transcribed, and that the caller may say "emergency" at any time — before any other exchange. The wording is tenant-configurable but default-on everywhere. A **transparently resumed session** (same `call_session_id`, WebSocket re-established within the configured resume window) is the **same call**, not a new one: the disclosure is NOT repeated on resume.
- **FR-003**: Recording and transcription MUST be handled to satisfy an all-party-consent posture; the first-utterance disclosure MUST stand as the affirmative consent record. Because a resumed session is the same call (FR-002), **consent persists across the resume** — the original consent record carries over and is not re-collected.
- **FR-004**: This feature covers after-hours calls only; daytime answering is out of scope for cycles 3a/3b.

**Caller Identity & Scope (VP-4a)**
- **FR-005**: Vera MUST attempt caller identification by inbound-number match and MUST soft-confirm ("Is this [Name]?") before entering that client's scope. When the number matches **multiple candidate parties** (a shared household line), Vera MUST use an **identity-safe** disambiguation dialog — an open prompt such as "May I get the name on the account?" — and match the caller's answer against the candidate set. Vera MUST NEVER enumerate the candidate names aloud (no "Is this Alice or Bob?"), as that would leak who is associated with the line. If the answer matches exactly one candidate she soft-confirms and enters that party's scope; otherwise she remains in unverified scope.
- **FR-006**: An unverified caller MUST be limited to schedule-availability information and new-client intake capture; Vera MUST NOT read back or act on any existing client's records for an unverified caller.
- **FR-007**: VP-4a caller identity + household memory is the **intended parallel baseline** for 3a — shipping alongside it so the continuity moat is live for the October pilot demo, with soft-confirm operating at pilot. If VP-4a caller identity is unavailable at runtime, Vera MUST operate statelessly in unverified scope rather than fail the call — **stateless operation is the documented graceful degradation**, not the pilot's baseline scope.

**Booking**
- **FR-008**: Vera MUST book and reschedule through the existing booking/availability pipeline (Intake→Match→Solve→Dispatch) with no bypass writes to the schedule.
- **FR-009**: Vera MUST read back the full appointment details and obtain explicit caller confirmation before any booking is written.
- **FR-010**: Booking writes MUST be idempotent so that retries or latency never produce a double-booking. Idempotency has two layers: (1) a database **UNIQUE constraint on `(clinic_id, slot_id, patient_ref)` for active bookings** guarantees the same slot cannot be double-booked for the same patient even across separate calls or callbacks; (2) a client-generated **`booking_token`** — `hash(clinic_id, slot_id, patient_ref, retry_nonce)`, where the retry nonce is carried across retries and even across a fresh call-back session (keyed on party/patient + slot + date, not the volatile `call_session_id`) — dedupes retries so a repeated confirm returns the original booking rather than erroring. The token, not `call_session_id + slot`, is the idempotency key (a session-scoped key would wrongly dedupe a second patient booking the same slot in one call, and would fail to dedupe a caller who calls back to retry).

**Autonomy Gate / Expert Firewall**
- **FR-011**: A deterministic protocol/autonomy gate — not the realtime language model — MUST authorize every write and every escalation; the model narrates outcomes, it does not decide them.
- **FR-012**: Vera MUST NEVER render clinical assessment, diagnosis, prognosis, treatment recommendation, or name or dose any drug (including OTC). Triage is pure routing with zero assessment language.
- **FR-013**: Vera MUST NEVER describe or imply she is a nurse, tech, doctor, or veterinarian.
- **FR-014**: Informational answers (hours, prep, pricing) MUST come only from clinic configuration, never from model priors.

**Emergency Routing (3b)**
- **FR-015**: A vet-signed, AVMA-teletriage-anchored protocol state machine MUST classify urgency by deterministic keywords/signals and drive routing only.
- **FR-016**: When the caller says "emergency" or a protocol flag trips at any point, Vera MUST interrupt the current flow (barge-in) and enter escalation immediately; no in-progress write is committed.
- **FR-017**: 100% of protocol-flagged calls MUST be escalated to a human with zero silent drops (hard SLO).
- **FR-018**: Escalation MUST warm-transfer to the on-call human or ER partner directory and hand the human a call summary. For the pilot, the on-call contact/schedule is a manual per-clinic configuration entered at clinic setup (a static on-call contact/schedule); machine-readable rota integration is deferred to VP-5.
- **FR-019**: Vera MUST always offer to escalate and never dismiss a stated concern.
- **FR-020**: If no human answers the transfer, Vera MUST fall through to an ER-directory readout plus a callback guarantee — never dead air, never a silent drop. For the pilot, the human overflow backstop is the staff on-call rota only; no contracted answering service is used in the pilot. A VetTriage-class backstop MUST be evaluated with real call-mix data before scale; GuardianVets is explicitly excluded as a backstop (funded direct competitor — call data must not flow to them).
- **FR-021**: Every protocol-flagged call transcript MUST be retained and available for the 6-month emergency audit.

**Refills (overrides existing auto-approve)**
- **FR-022**: A voice refill request MUST produce a draft-for-vet-approval record ONLY; it MUST NOT invoke the platform's existing auto-approve path, regardless of refills remaining.
- **FR-023**: Vera MUST confirm the refill request was captured for vet review and MUST NEVER state or imply it is approved or filled.

**Transcription, Logging & Reporting**
- **FR-024**: Every call MUST be transcribed and logged with caller, timestamp, call outcome (contained / booked / escalated / deflected) and containment flag, and full transcript.
- **FR-025**: Every call MUST appear in the practice's morning briefing with its outcome and any staff follow-up items (callbacks, pending refills, escalations) flagged.
- **FR-026**: Voice/transcription vendors MUST be bound by no-training constraints and consent records MUST be retained.

**Metrics (first-class)**
- **FR-027**: Containment (a non-emergency call resolved without a human) MUST be measured per call and reported. **A booking is a contained outcome** — `booked` calls count as contained. The single source of the containment metric is the boolean `containment_flag` on the call record (set true whenever a non-emergency call is resolved without a human, including bookings), independent of the call-outcome label. The containment rate reported for SC-004 is `count(containment_flag = true) / non-emergency calls`.
- **FR-028**: Booking accuracy MUST be measured and auditable at the per-call level.
- **FR-029**: Escalation completion (flagged calls successfully handed to a human) MUST be measured against the 100% target.
- **FR-030**: Cost-per-call telemetry MUST be captured from the first call (R7), computed from a per-provider cost-rate source (`backend/voice/config/pricing.yml` — `$/audio-min` in + out and `$/1k tokens` per provider) so the figure is auditable and provider-swap-safe.

### Key Entities

- **Call**: One inbound after-hours call — inbound number, matched caller (or unverified), start/end time, call outcome label, containment flag (the metric source), cost, linked transcript.
- **ConversationalTurn (call_turn)**: One turn within a call — role, text, latency, barge-in flag, protocol flag, gate decision, and tool calls. The append-only auditable spine of the conversation.
- **Transcript**: The recorded/transcribed content of a call, with consent record and vendor no-training attestation; retained for audit.
- **CallerIdentity**: Result of the VP-4a number-match + soft-confirm — verified/unverified state and the memory scope it unlocks.
- **EscalationEvent**: A protocol-flagged escalation — trigger, transfer target, summary handed over, transfer outcome, fallback path taken.
- **RefillRequestDraft**: A captured refill request routed to vet review; never auto-approved.
- **TriageProtocol**: The vet-signed AVMA-teletriage routing state machine (keywords, urgency classes, routing targets) — authored per clinic.
- **MorningBriefingEntry**: The overnight-call rollup surfaced to owner/staff with follow-up items.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Vera answers 100% of inbound after-hours calls with the full disclosure delivered before any other exchange.
- **SC-002**: 100% of protocol-flagged (emergency) calls are escalated to a human with zero silent drops.
- **SC-003**: Booking accuracy is 99% or higher, verified by post-call audit.
- **SC-004**: After-hours containment of non-emergency calls reaches 50–60% (provisional), where the containment rate is defined as `count(containment_flag = true) / non-emergency calls` (bookings count as contained; see FR-027). This target stays provisional and is finalized after the 2-week Goldsmith after-hours call-log pull, now a pilot week-1 ground-truth item that sets the achievable ceiling and emergency fraction. The escalation (100%), booking-accuracy (≥99%), and disclosure (100%) SLOs are firm regardless.
- **SC-005**: 0 refill requests are auto-approved via the voice channel; 100% are routed as drafts for vet review.
- **SC-006**: 100% of calls are transcribed, logged, present in the next morning briefing, and have cost-per-call reported from call #1.
- **SC-007**: Callers can interrupt Vera and reach the escalation path mid-turn with a false-barge-in rate under 2% on real call audio.

---

## Non-Goals *(cycle 3a/3b)*

- Any clinical assessment, diagnosis, prognosis, dosing, or drug-naming; any self-description as nurse/tech/doctor/vet.
- Autonomous refills — refill-request is draft-for-approval only and must not touch the existing auto-approve path.
- Daytime answering (after-hours first); bilingual GA (gated on a phone-grade WER benchmark); building the staff rota (consumes VP-5); number porting (3d).
- A managed voice platform (Vapi/Retell) as production — a short throwaway discovery prototype is fine; the turn loop and autonomy gate are core IP. Marketing the wedge as "we answer the phone" or per-minute pricing gimmicks.

---

## Assumptions & Dependencies

- **Platform, not demo repo**: This feature targets the VP-1 convergence platform (external realtime LLM + Postgres/RLS envelope plane), not the demo scaffold. This is a deliberate departure from the demo constitution's SQLite/no-external-LLM principle, now permitted under the constitution's **v1.1.0 Platform-track exception** (Principle III) for platform-track specs whose plan declares the departure — not a defect.
- **Layer split (C3 negotiation accepted 2026-07-09)**: L1/L2 conditions accepted + L3 built in-stream (extract to core C3 post-pilot). The realtime streaming tier (L3 — realtime-LLM bridge with a fallback adapter behind the port) is **VetAgent-owned and built inside VP-3**, not an external gate; it is extracted to core C3 only post-pilot. The genuine external dependencies are core's L1 (`ChannelBinding` party-model + consent) and L2 (`bridge_inbound()` with the pre-speak interposition hook) conditions. A vet-signed AVMA-teletriage protocol plus counsel sign-off on consent / no-training vendor clauses remain hard gates required before the first live call.
- **Differentiation depends on VP-4a**: Cycle 3a alone is a competent but stateless after-hours line; the identity-continuity moat lands only when VP-4a caller identity + scoped memory land in parallel. Risks carried from discovery: under-triage is existential (mitigated by deterministic keywords, always-offer-to-escalate, human overflow, 6-month audit); the autonomy gate must run inside a speech-to-speech turn loop whose model may lack async tool calls (pre-fetch/fast tools required); Preview-model session limits require transparent resumption; false barge-in on backchannels is the top turn-taking failure; bilingual code-switch WER makes any bilingual promise a trust risk until benchmarked.

---

## Marketing Output
**Produced by**: speckit-specify — 2026-07-09

### Feature Brief

**Consumer-Friendly Feature Name**: Vera After-Hours — Your Phone, Always Answered

**Key Benefits** (in customer language):
1. Never lose a client to a missed after-hours call — every after-hours call is answered in one ring by the same Vera who already knows your schedule.
2. Get your team off the phones and out of morning callback triage — routine bookings and questions are handled overnight and waiting for you in the briefing.
3. Sleep knowing a real emergency always reaches a real person — fast, every time, with a full record of who called and why.

**One-Line Description** (≤25 words): Your clinic's after-hours phone, answered by someone who already knows the family — booking the routine and getting true emergencies to a vet fast.

**Guidance note**: Sell the outcome (recovered revenue, staff hours returned, safe escalation), never "an AI answers the phone."
