# Feature 010 — Vera Voice: Phase 0 Research

Decisions below resolve the Technical Context unknowns. Facts are verified in `VetPractice/research/v02/l5-voice.md` (tags [V]/[EST]) and the 2026-07-09 C3 negotiation board.

---

## D1 — Realtime model + telephony
- **Decision**: Twilio Media Streams + **Gemini 3.1 Flash Live** direct (native speech-to-speech), **OpenAI Realtime** as config-swap fallback, both behind `RealtimeModelPort`.
- **Rationale**: ~$0.03–0.04/min all-in (~4× cheaper audio-out than OpenAI), native s2s latency (160–400 ms class) beats cascades by ~1 s, and owning the turn loop is required for the in-loop autonomy gate / Expert Firewall. Managed platforms (Vapi/Retell) put our gate outside their turn loop → prototype/discovery only.
- **Alternatives**: Vapi/Retell (rejected as production — pipeline is theirs); composed Deepgram+LLM+ElevenLabs (rejected — cascade latency 800 ms–2 s); white-label Dodo/Scritch (rejected — strategically incoherent, data in a competitor).

## D2 — Async-tool gap (the load-bearing unknown)
- **Decision**: `prefetch_context` at answer time (fetch schedule slots, clinic config, and VP-4a household summary the instant identity soft-confirms) + **bounded hold patterns** (`max_hold_ms` + filler script) for cache misses.
- **Rationale**: Gemini Live 3.1 has no async/NON_BLOCKING function calling — a synchronous PIMS/slot lookup would block the speech turn. Prefetch converts most lookups into cache reads; hold covers the rest. Escalate lookup-heavy turns to a fast/cached path or Gemini 2.5 Native Audio if latency creeps.
- **Alternatives**: block-and-wait (rejected — dead air, SLO breach); speculative model narration then correct (rejected — violates "model narrates, does not decide").

## D3 — Session limits
- **Decision**: Transparent session resumption with `contextWindowCompression`; adapter re-establishes the WS and replays minimal state without dropping the caller.
- **Rationale**: 15-min session cap w/o compression, ~10-min WS lifetime; long calls also hit context re-billing. Preview status makes this a day-1 requirement.

## D4 — Barge-in / turn-taking
- **Decision**: Server VAD + backchannel filter; detect <400 ms, target <2% false-barge-in on real 8 kHz audio; benchmark in Phase G.
- **Rationale**: backchannels ("uh-huh") are the #1 turn-taking failure. "emergency" must always cut through (barge-in → escalation).

## D5 — Safety guarantees location
- **Decision**: Disclosure-before-model, escalation watchdog (independent transfer authority), and append-only logging live in **`adapter_guarantees.py`**, below the model — not in the model prompt.
- **Rationale**: Escalation cannot depend on model compliance (100% SLO is existential). This is C3-proposal condition 2 (watchdog authority) realized in our L3.

## D6 — Layer split (C3 accepted)
- **Decision**: Consume core L1 (ChannelBinding+router, consent) and L2 (`bridge_inbound`→`converse_turn`); **build L3 (realtime streaming) in-stream**, extract to core C3 post-pilot.
- **Rationale**: Accepted 2026-07-09. Conditions on core (pending reply): L2 pre-speak interposition hook; ChannelBinding party-model (one phone ↔ many household members); first-class consent in L1. `prefetch_context` resolves to L3 (ours), not C2/C3, since L3 is VetAgent-owned.
- **Fallback**: if L2 lands without the pre-speak hook, build against our own `converse_turn` shim (registry `prototype`), extract later.

## D6a — C4 autonomy gate collapses on the live voice turn (C2)
- **Decision**: The live voice gate is restricted to **`do` | `reject` | `escalate`**. Because a synchronous speech turn has no mid-call human-approval loop, the `advise` and `propose` rungs of the C4 ladder do not act on-call — they resolve to **post-call artifacts**: `advise` → a morning-briefing item, `propose` → a draft for staff/vet review (e.g. the refill draft). The four-value `gate_decision` is still persisted for audit; only three classes act live.
- **Rationale**: preserves "model narrates, does not decide" without inventing a synchronous approval handshake the channel cannot support; keeps advisory/proposal intent auditable and routed to the surfaces that can action it. Ladder mapping (KNOW/ADVISE/DECIDE ↔ advise/propose/do/reject) documented in `contracts/voice-channel.md` B3.

## D7 — Refill auto-approve reconcile
- **Decision**: Voice refill verb writes `refill_request_draft` (`status='draft_vet_review'`, always) and **never** calls `PrescriptionAgent.request_refill` (which auto-approves when `refills_remaining>0`, `prescriptions.py:124`). Autonomy gate additionally rejects any `auto_approved` disposition on the voice channel.
- **Rationale**: FR-022/023, SC-005 — autonomous refills are a hard legal/clinical no-go.

## D8 — Warm transfer + overflow
- **Decision**: Twilio Conference + Dial; whisper a spoken summary to the human before connecting; on no-answer → ER-directory readout + callback guarantee; last resort voicemail-with-callback. Manual per-clinic `on_call_target` (static contact/schedule); staff-rota-only, **no answering service** in pilot; GuardianVets explicitly excluded (competitor — call data must not flow to them).
- **Rationale**: FR-018/020; VP-5 machine-readable rota deferred. Evaluate a VetTriage-class backstop with real call-mix data before scale.

## D9 — Consent / no-training
- **Decision**: First-utterance disclosure is the affirmative consent record (all-party posture); vendor DPAs contractually prohibit training on call audio; consent + attestation stored per call.
- **Rationale**: Utah AI Policy Act as national floor; *In re Otter.AI* CIPA capability-test exposure. Counsel sign-off is a hard gate.

## D10 — Triage protocol representation
- **Decision**: Build the deterministic state-machine **engine** + a versioned YAML config format (keywords → urgency class → routing target, `slo: {escalation_on_flag: 1.0}`). VP-9 authors and vet-signs the **content**; we own engine + format + regression harness.
- **Rationale**: keeps the medical content out of code and under vet signature; keyword-first, no classifier in v0.

---

## Open items carried to build
- Goldsmith 2-week after-hours call-log pull (week-1 ground truth) sets the provisional 50–60% containment ceiling + emergency fraction.
- Bilingual (EN/ES) gated on a phone-grade WER benchmark — no promise until measured (3c, out of scope here).
