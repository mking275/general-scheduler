# Feature 010 — Vera Voice (VP-3, cycles 3a + 3b): Implementation Plan

**Branch**: `010-vera-voice` · **Target**: VP-1 convergence platform (Postgres + RLS envelope plane + external realtime LLM) — **NOT** the demo SQLite scaffold. **Scope**: 3a (after-hours line, 1 Goldsmith clinic) + 3b (emergency routing). **Pilot**: Phase 3 (~Oct 2026); build starts at pilot kickoff (Aug).

---

## Technical Context

### Runtime stack (platform, not demo repo)
- **Python 3.11 + FastAPI** service on the VP-1 platform; **Postgres + RLS** (party-scoped rows), not SQLite.
- **Telephony**: Twilio Voice + **Media Streams** (bidirectional μ-law 8 kHz over WebSocket). Greenfield — only `sms_gateway.py` exists (outbound SMS leg reused for callbacks/report delivery).
- **Realtime model**: **Gemini 3.1 Flash Live** primary (`gemini-3.1-flash-live-preview`, native speech-to-speech, ~$0.03–0.04/min all-in); **OpenAI Realtime** fallback — both behind a provider-agnostic `RealtimeModelPort` (config swap, not rewrite).
- **Transcode**: μ-law 8 kHz ↔ PCM 16/24 kHz bridge, day-1.
- **Booking verbs (reused, no bypass)**: `booking_agent.confirm_booking` / `cancel_booking`, `availability_agent` slot enumeration, `waitlist` slot-offer — voice is a new **intake channel** into the existing Intake→Match→Solve→Dispatch pipeline.

### Layer ownership (per C3 negotiation, accepted 2026-07-09)
| Layer | Owner | This plan |
|---|---|---|
| **L1** ChannelBinding registry + router, consent | Vera-core (Program #3) | consume; requires party-model + consent conditions |
| **L2** unified session bridge `bridge_inbound()`→`converse_turn()` | Vera-core (Program #3) | consume; **requires pre-speak interposition hook** (our condition 1) |
| **L3** realtime streaming (Media Streams bridge, turn loop, barge-in, adapter guarantees) | **VetAgent / VP-3 (OURS)** | **build here**; extract to core C3 post-pilot |

L3 being ours **removes C3-monolith from the critical path**. The real external dependency is L2's voice-capable turn contract (see Conflicts).

### Realtime constraints (verified, l5-voice.md)
- Gemini Live 3.1 has **no async / NON_BLOCKING function calling** → slow lookups block the turn. Mitigation: `prefetch_context` at answer time + bounded hold patterns (see Phase D).
- 15-min session cap w/o `contextWindowCompression`, ~10-min WS lifetime → **transparent session resumption** required.
- Barge-in bar: <400 ms detect, <2% false-barge-in on real audio; backchannels ("uh-huh") are the #1 turn-taking failure.
- Preview-labeled → OpenAI Realtime adapter behind the port from day 1.

### Performance / SLO goals
| Metric | Target | Method |
|---|---|---|
| Answer latency (ring→disclosure) | first-ring, no dead air | Twilio answer + pre-rendered disclosure asset |
| Turn latency p50 / p95 | ≤1.5 s / ≤3.8 s | native s2s + prefetch; instrumented per turn |
| Barge-in detect | <400 ms, <2% false | server VAD tuning + backchannel filter |
| Escalation completion | **100%** (hard SLO) | adapter watchdog w/ independent transfer authority |
| Booking accuracy | ≥99% | read-back confirm + idempotent write + post-call audit |
| Disclosure delivery | 100% | adapter plays disclosure before model engages |
| Cost/call | captured from call #1 | telemetry (R7) |

---

## Constitution Check

> **Complexity Tracking** (Governance-mandated section — this "Constitution Check" *is* the plan's Complexity Tracking section; named "Constitution Check" per the speckit-plan template, aliased here to satisfy the Governance clause literally). The single tracked deviation is Principle III (below), justified in-place.

GS constitution is now **v1.1.0**: Principle III carries a **Platform-track exception** (added 2026-07-09) permitting PostgreSQL+RLS and external LLM/realtime services for platform-track specs (VP-1 convergence and dependents, incl. 010) whose plan declares the departure. 010 targets the pilot/convergence platform and declares that departure here. Principles apply in spirit; III departs **by design, under the v1.1.0 exception**.

| Principle | Status | Notes |
|---|---|---|
| I Demo-First / Verbose Log | ✅ (exceeds) | every call + every gate/protocol/escalation decision is an append-only event; full transcript retained |
| II Agentic Pipeline Integrity | ✅ | bookings still flow Intake→Match→Solve→Dispatch; voice is a new intake channel, **no bypass writes** |
| III Data Simplicity (SQLite, no external LLM) | ✅ **departure permitted under v1.1.0 Platform-track exception** | realtime external LLM + Postgres/RLS envelope required; the v1.1.0 constitution amendment scopes this exception to platform-track specs whose plan declares the departure — this plan declares it. No longer an unresolved violation. |
| IV Role-Aware UI | ✅ | owner morning-briefing rollup, staff escalation handoff, client-scoped voice persona |
| V Incremental Buildability | ✅ | 3a independently deployable; does not break the existing demo |

**Binding vet "constitution" preserved architecturally**: no clinical verbs at any autonomy level; triage is pure routing (zero assessment language); refills draft-for-approval only (see reconcile below).

### Code-level reconcile — `prescriptions.py` auto-approve bypass (FR-022/023, SC-005)
`backend/agents/prescriptions.py::request_refill()` today sets `status = "auto_approved"` when `refills_remaining > 0` (line 124). The voice channel **MUST NOT** reach this branch. Plan: the voice refill verb writes a **`refill_request_draft`** row directly (`status = 'draft_vet_review'`, always) and **never calls `PrescriptionAgent.request_refill`**. Enforced two ways: (1) voice verb has no code path to `request_refill`; (2) an assertion/guard in the autonomy gate rejects any `auto_approved` disposition on the voice channel. Surfaced in the morning briefing as "awaiting vet action."

---

## Project Structure — New Files (on VP-1 platform)

```
backend/voice/                          # L3 — VetAgent-owned realtime tier (rooted under backend/; see tasks.md Path note)
├── media_stream_bridge.py             # Twilio Media Streams WS ↔ RealtimeModelPort; μ-law↔PCM
├── realtime_model_port.py             # provider-agnostic port
│   ├── gemini_live_adapter.py         #   primary (Preview)
│   └── openai_realtime_adapter.py     #   fallback (config swap)
├── turn_loop.py                       # per-turn: protocol.step → gate.classify → speak; barge-in
├── adapter_guarantees.py              # disclosure-before-model, escalation watchdog, append-only log
├── triage_protocol.py                 # deterministic state-machine ENGINE (config-driven)
├── prefetch.py                        # prefetch_context at answer + bounded hold patterns
├── verbs.py                           # book/reschedule/refill-draft/intake — into existing pipeline
├── warm_transfer.py                   # Twilio Conference+Dial; whisper summary; ER-directory + voicemail fallback
├── voice_repository.py                # Postgres/RLS ops for the 8 voice tables
└── telemetry.py                       # cost/call, latency p50/p95, containment, escalation detail

config/voice/
├── triage_protocol.<clinic>.yaml      # VP-9 vet-signed CONTENT (engine consumes; we own format+engine)
├── disclosure_script.<locale>.txt     # FR-002 first utterance
└── clinic_voice_config.<clinic>.yaml  # hours, on-call targets, ER directory, voice params

specs/010-vera-voice/
├── plan.md                            # this file
├── research.md                        # Phase 0 — decisions + rationale
├── data-model.md                      # 8 tables
└── contracts/
    └── voice-channel.md               # L2 pre-speak hook (ask to core) + RealtimeModelPort + telemetry
```
*(Note: the skill's AGENTS.md pointer update is deferred — this task is scoped to the spec directory only.)*

---

## Implementation Phases & Effort (honest; greenfield realtime)

Effort in engineer-weeks (ew). Calendar shorter with parallelism. Total **~13–18 ew**.

| Phase | Scope | Effort | Notes / risk |
|---|---|---|---|
| **A — Bridge + Model Port** | Media Streams WS ↔ `RealtimeModelPort`; μ-law↔PCM transcode; Gemini Live primary + OpenAI Realtime fallback; **session resumption** (10-min WS / 15-min cap). | **3–4 ew** | Highest greenfield risk; validate against the throwaway prototype first. |
| **B — Turn loop + adapter guarantees** | Per-turn interposition; disclosure-before-model; **escalation watchdog w/ independent transfer authority**; append-only transcript + event log; barge-in + backchannel filter. | **2.5–3 ew** | Safety spine. Barge-in tuning is the hard part. |
| **C — Triage protocol engine** | Config-driven deterministic keyword/urgency state machine (ENGINE + YAML format only; VP-9 signs content). Override authority over model output. | **1.5–2 ew** | Blocked on VP-9 for *content*, not engine. |
| **D — Verbs + prefetch/hold + autonomy gate + refill reconcile** | Book/reschedule via existing pipeline (idempotent, read-back); `prefetch_context` (slots, clinic config, VP-4a household summary) + bounded hold; C4 autonomy gate synchronous; `refill_request_draft` override. | **2.5–3 ew** | Async-tool gap mitigation lives here. |
| **E — Warm transfer + overflow fallback** | Conference+Dial warm transfer w/ whisper summary to manual on-call target; ER-directory readout + callback guarantee; voicemail-with-callback last resort (never dead air). | **1.5–2 ew** | Staff-rota-only (no answering service in pilot). |
| **F — Telemetry + logging + briefing** | cost/call, latency p50/p95, containment enum, escalation detail; consent + no-training attestation; morning-briefing rollup with follow-up flags. | **1.5 ew** | Reuses SMS outbound leg for report delivery. |
| **G — Test + SLO verification + red-team** | 100%-escalation SLO harness (incl. model-stall injection); scripted red-team call set; barge-in benchmark on real audio; booking-accuracy audit. | **2 ew** | Gates go-live. |

**Hard gates before first live call**: VP-9 vet-signed AVMA-teletriage protocol; counsel sign-off on consent / no-training vendor clauses; L2 pre-speak hook (or shim) available; VP-1 platform available (see Dependencies).

---

## Dependencies & Fallbacks

- **VP-1 cycles 1a/1b (Postgres + RLS convergence platform) — HARD dependency.** All 8 tables are RLS-scoped. **Fallback if VP-1 slips**: run L3 against a single-clinic Postgres instance with app-level scoping (RLS deferred) for the 1-clinic pilot only; do **not** regress to SQLite (external-LLM transcripts + consent records need the envelope plane). Documented as pilot-only degradation.
- **Core L2 `bridge_inbound()` with pre-speak interposition (condition 1) — pending core reply.** Fallback: build L3 against our own `converse_turn` shim matching the contract in `contracts/voice-channel.md`, marked `prototype` in the registry; extract post-pilot. This keeps voice on the shared brain rather than forking.
- **VP-4a caller identity + household memory — parallel (October).** Fallback: stateless unverified-scope operation (FR-007 graceful degradation only, not baseline).
- **VP-9 vet-signed protocol + ER directory** — content gate on any live emergency call.
- **VP-5 machine-readable rota** — deferred; pilot uses manual `on_call_target` config.

---

## Test Strategy (summary; detail in Phase G)

1. **100%-escalation SLO** — automated call set trips every protocol keyword + literal "emergency" at every turn position (incl. mid-booking); assert barge-in, zero assessment language, warm transfer + summary, and — with **model-stall / disconnect injection** — the adapter watchdog still transfers within SLO. Assert no partial write on abandoned bookings.
2. **Scripted red-team call set** — clinical-question probes ("is chocolate toxic?"), "are you a nurse/vet?", refill-with-refills-remaining (assert no `auto_approved`), multi-household shared-line (assert unverified scope), backchannel false-barge-in (<2%), session-limit crossing (transparent resume).
3. **Booking accuracy ≥99%** — post-call audit comparing read-back to written slot; idempotency under retry/latency.
4. **Disclosure 100%** — first-utterance assertion on every call fixture.
5. **Cost/latency** — telemetry captured from call #1; p50/p95 reported.

---

## Top 3 Technical Risks

1. **In-turn-loop autonomy gate over a Preview model with no async tool calls** (feasibility, HIGH). A slow slot/household lookup blocks the speech turn. *Mitigation*: `prefetch_context` at answer time + bounded hold patterns (`max_hold_ms` + filler); OpenAI Realtime fallback behind the port; route lookup-heavy turns to a fast/cached path (or Gemini 2.5 Native Audio) if latency creeps.
2. **Under-triage / watchdog depending on model compliance** (existential). *Mitigation*: escalation watchdog lives in the adapter with **independent transfer authority** — fires on deterministic keyword/silence even if the model stalls or misroutes; protocol state machine overrides model output; 100%-SLO harness with stall injection + red-team set + 6-month audit of every flagged call.
3. **L2 pre-speak interposition not delivered as accepted** (integration; condition 1 pending). If core ships L2 as "model decides, adapter relays," voice must bypass the shared brain (silo) or fork. *Mitigation*: concrete interface in `contracts/voice-channel.md` as the ask; build against our own `converse_turn` shim if L2 slips, extract post-pilot.

---

## Conflict: spec vs. C3-accepted architecture

The spec (Assumptions & Dependencies) still frames **C3 — the realtime-LLM bridge with fallback adapter — as an external "hard pilot gate" / "pacing dependency" that "must land before go-live."** Per the **accepted C3 negotiation (2026-07-09)**, **L3 realtime streaming is VetAgent-owned** and built inside VP-3 (extracted to core C3 only post-pilot). This **removes C3-monolith from VP-3's critical path** — we are not waiting on core to deliver the bridge; we build it. The genuine external dependency is narrower: **core's L1 `ChannelBinding` (party-model + consent) and L2 `bridge_inbound()` with the pre-speak interposition hook** (our three conditions, still pending core's reply). The spec's dependency language has now been updated (F1 remediation) from "C3 tier must land" to "L1/L2 conditions accepted + L3 built in-stream," so the plan, spec, and the board agree. No functional conflict in scope — only in what is owned/gated.

---

## Marketing Output
**Produced by**: speckit-plan — 2026-07-09

### Demo Flow Sketch

**Audience**: Goldsmith clinic owner + operations manager (and, as an asset, prospective clinics / investors).
**Estimated runtime**: ~5 minutes.
**Pre-demo setup**: 1 clinic loaded with `clinic_voice_config` + a manual `on_call_target`; VP-9 triage protocol signed; a known client (`Mrs. Alvarez` + pet `Rex`) in VP-4a; morning-briefing view open.

**Step 1 — The Setup**: It's "9 pm." The clinic line normally rolls to voicemail. We call the pilot number from Mrs. Alvarez's known mobile.

**Step 2 — The Action**: Vera answers on the first ring and, in her first sentence, discloses she is an AI assistant, that the call is recorded and transcribed, and that you can say "emergency" at any time. She soft-confirms "Is this Mrs. Alvarez?", then books a follow-up for Rex against the live schedule — reading date, time, provider, and reason back before anything is written.

**Step 3 — The Refill**: Mrs. Alvarez asks for a refill. Vera captures it, says a vet will review it, and logs a draft — never "approved." On screen, it lands in the vet's queue, **not** the auto-approve path.

**Step 4 — The Emergency (the proof)**: A second call: "my dog just collapsed." Vera interrupts mid-flow, uses zero clinical language, and warm-transfers to the on-call vet with a spoken summary. We kill the on-call line to show the fallback: ER directory read out + guaranteed callback — never dead air, never a silent drop.

**Step 5 — The Payoff**: The next-morning briefing shows every overnight call — booked, drafted, escalated — with follow-ups flagged and a cost-per-call figure. Three calls that would have been three voicemails are now one booking, one vet task, and one safely-handled emergency.

**Key talking point**: The same Vera who runs the schedule now answers the phone after hours — and the safety guarantees (disclosure, 100% escalation, no autonomous refills) live in the adapter, below the model, not in a prompt we hope it follows.
