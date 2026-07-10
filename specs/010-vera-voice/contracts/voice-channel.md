# Feature 010 — Vera Voice: Interface Contracts

Two contracts: (A) the **ask to Vera-core** — the L1/L2 shape voice needs (the concrete form of our three accepted C3 conditions); (B) the **L3 interface we own** — `RealtimeModelPort`, adapter guarantees, turn contract, telemetry. Shapes are Python-typed sketches; iterate with core on A, freeze B in-stream.

---

## A. Ask to Vera-core (L1 + L2)

### A1 — ChannelBinding: party model, not a user string (condition 2)
One phone ↔ many household members is a live privacy case. Binding must resolve to a **candidate-party set + verification level + audience scope**, not `verified: bool` + `user_id`.

```python
class ChannelBinding:
    customer_id: str
    channel: Literal["voice", "sms", "whatsapp", "email", "web"]
    channel_address: str                       # E.164 for voice
    candidate_parties: list[PartyRef]           # 0..n — shared line = many
    verification_level: Literal["none", "soft_confirmed", "strong"]
    audience_scope: Literal["caller_unverified", "client_verified", ...]  # from C1 memory_scoping
    # unverified caller → ephemeral party, caller_unverified scope
```

### A2 — Consent first-class in L1 (condition 3)
`route_message` / `deliver` MUST consult the channel-scoped, TCPA-grade opt-out registry before send — not a `preferences` dict convention.

```python
async def consent_check(party: PartyRef, channel: str, purpose: str) -> ConsentDecision: ...
```

### A3 — L2 voice-capable turn contract with **pre-speak interposition** (condition 1 — the one non-negotiable)
`bridge_inbound()` routes voice into the shared `converse_turn()`. For voice, the turn must expose a hook where our deterministic protocol machine + C4 gate run **with override authority before output is rendered**, plus streaming partials and barge-in signaling within realtime budgets.

```python
async def bridge_inbound(channel: str, raw: Any) -> VeraTurn:
    binding = await resolve_binding(channel, raw)          # A1
    session = await get_or_create_session(binding)
    return await converse_turn(session, raw, hooks=turn_hooks)

class TurnHooks:                                            # what voice needs L2 to accept
    # runs on the model's proposed output BEFORE it is spoken; may REPLACE/BLOCK it
    async def pre_speak(self, draft: ModelOutput, ctx: TurnContext) -> TurnDecision: ...
    async def on_partial(self, partial: str) -> None: ...   # streaming
    async def on_barge_in(self, at_ms: int) -> None: ...    # caller interrupt

class TurnDecision:
    action: Literal["speak", "replace", "escalate", "hold", "hangup"]
    text: str | None
    override_reason: str | None                             # audited
```

If L2 cannot accept `TurnHooks.pre_speak` with override authority, voice bypasses the shared brain — unacceptable. **Fallback**: our own `converse_turn` shim implementing this contract, registry-marked `prototype`, extracted post-pilot.

### A4 — VP-4a household summary (stubbed interface; parallel dependency)
The frozen shape `prefetch_context` (T025) consumes for greeting + continuity. VP-4a lands in parallel; until then the **stub returns `None`** and Vera operates in unverified/stateless scope. **All fields nullable.**

```python
class HouseholdSummary:
    party_id: str | None                       # resolved VP-4a party
    display_name_for_greeting: str | None       # e.g. "Mrs. Alvarez" — soft-confirm/greeting only
    household_patients: list[PatientRef] | None # [{name, species}, ...]
    last_visit_summary_line: str | None         # one-line continuity ("Rex's follow-up")
    audience_scope: Literal["caller_unverified", "client_verified", ...] | None  # gates what may be spoken
    verification_level: Literal["none", "soft_confirmed", "strong"] | None
    # stub returns None (whole object) when VP-4a is absent → unverified/stateless operation

class PatientRef:
    name: str | None
    species: str | None
```

---

## B. L3 — VetAgent-owned (built here, extracted to core C3 post-pilot)

### B1 — RealtimeModelPort (provider-agnostic; fallback = config swap)
```python
class RealtimeModelPort(Protocol):
    async def connect(self, system: str, tools: list[Tool], voice: str, locale: str) -> None: ...
    async def send(self, chunk: AudioChunk | str) -> None: ...
    def on(self, event: Literal["partial", "final", "tool_call", "error", "interrupted"], cb) -> None: ...
    async def interrupt(self) -> None: ...
    async def resume(self) -> None: ...                     # transparent session resumption

# impls: GeminiLiveAdapter (primary, Preview) · OpenAIRealtimeAdapter (fallback)
```

### B2 — Adapter guarantees (NON-NEGOTIABLE, enforced below the model)
```python
class AdapterGuarantees:
    # 1. first_utterance = disclosure_script — plays before model engages (FR-002, 100%)
    # 2. escalation_watchdog: protocol_flag | "emergency" | silence → warm_transfer within SLO
    #    with INDEPENDENT transfer authority, even if the model stalls or misroutes (FR-017, 100%)
    # 3. append-only transcript + call_turn event log, every session (FR-021/024)
    # 4. do-class never enabled for clinical verbs; refill → draft only (FR-022)
```

### B3 — Turn contract (runs EVERY turn, before Vera's reply is spoken)
```
1. triage_protocol.step(transcript_delta)      # deterministic; OVERRIDES model output
2. autonomy_gate.classify(pending_tool_calls)  # LIVE VOICE GATE: do | reject | escalate only
3. slow-tool handling (no async fn-calling on Gemini Live 3.1):
     prefetch_context(slots, clinic_config, household_summary@audience_scope)  # at answer time
     hold(max_hold_ms, filler_script)          # bounded, on cache miss
```

**C4 autonomy-ladder mapping + live-voice collapse (F3, C2).** The discover-doc ladder **KNOW → ADVISE → DECIDE** maps to the C4 gate verbs as: KNOW ↔ (read-only, no gate write) · ADVISE ↔ `advise` · (ADVISE→DECIDE boundary) ↔ `propose` · DECIDE ↔ `do`; `reject` is the deny across the ladder. On a **synchronous live voice turn there is no mid-call human-approval loop**, so the ladder **collapses**: the live gate is restricted to **`do` | `reject` | `escalate`** (act now / deny / hand to a human). The `advise` and `propose` classes do **not** speak on-call — they are deferred to **post-call artifacts**: an `advise` maps to a **morning-briefing item**, a `propose` maps to a **draft** for staff/vet review (e.g. the refill draft). `do` is never enabled for clinical verbs. This is why the four-value `gate_decision` is persisted (audit of intent) while only three act live.

### B4 — Session commands / events
```
events → harness:  utterance(partial|final) · barge_in · dtmf · silence(ms) · line_event
commands ← harness: speak(text|ssml, interruptible=True) · hold(max_ms, filler)
                    warm_transfer(target, whisper_summary) · hangup(reason) · play(asset)
failure_modes: model_disconnect → scripted apology + warm_transfer; emit degraded_mode
```

### B5 — Verbs (into existing pipeline, no bypass)
```python
book(slot, party, booking_token) -> Booking   # → booking_agent.confirm_booking; read-back + idempotent
                                       #   booking_token = hash(clinic_id, slot_id, patient_ref, retry_nonce);
                                       #   UNIQUE(clinic_id, slot_id, patient_ref) on active bookings + token dedupe (FR-010)
                                       #   NOT keyed on call_session_id (would misdedupe 2nd patient / miss call-back retry)
reschedule(...)   -> Booking          # → booking_agent (cancel + confirm)
availability(...) -> list[Slot]       # → availability_agent (unverified callers: availability only)
refill_draft(...) -> RefillDraft      # writes refill_request_draft; NEVER request_refill()
intake_capture(...) -> NewClientDraft # unverified new-client capture
```

### B6 — Telemetry (from call #1)
```python
class CallTelemetry:
    cost_usd: float                    # COGS per call (R7 / FR-030)
    turn_latency_p50_ms: int
    turn_latency_p95_ms: int
    call_outcome: Literal["contained", "booked", "escalated", "deflected"]   # descriptive label, NOT the metric
    containment_flag: bool                # single source of the containment metric (booked ⊆ contained; F2)
    escalation: EscalationDetail | None   # trigger, target, outcome, watchdog_fired
    barge_in_false_rate: float            # against <2% bar
    model_provider: str
    session_resume_count: int
```
