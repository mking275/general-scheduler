# Discovery: Vera Voice — "the Front Door" (VP-3)

**Feature type**: new-product-surface (net-new client-facing channel — Vera answers the clinic phone; the same "person" who runs the waitlist and the briefing)
**Appetite**: Large across the program (4 cycles); **cycle 3a Medium** — after-hours line, 1 Goldsmith clinic, pilot Phase 3 (~Oct)
**Passes run**: 0, 1, 2, 3, 4, 5, 6 (via the 2026-07-09 V0.2 research corpus L0/L3/L5 + synthesis + backend audit)
**Artifact confidence**: MEDIUM — tech/legal/competitive facts verified HIGH (L5 ~120 searches, adversarial re-verification; L0 AAVSB first-hand); the containment ceiling depends on Goldsmith's after-hours call mix, which is **unmeasured** (Open Q5)
**Date**: 2026-07-09

---

## Customer Artifacts

**Human-provided:**
- Goldsmith phase-4 brief **F1** (Vera Voice — phone scheduling + emergency routing, after-hours first) + R-items: R2 consent, R3 missed-emergency, R6 bilingual, R7 cost telemetry, R8 pricing.
- Matt's 2026-07-09 sharpening (L0 §4): **identity continuity IS the voice moat** — "the receptionists answer calls; Vera knows the family." Plus the benefits-not-feature-parity doctrine.

**Agent-sourced (persisted in `VetPractice/research/v02/`):**
- `l5-voice.md` — market, tech stack (Gemini Live vs OpenAI Realtime BOM), emergency-routing legal bar, build-vs-buy. Load-bearing pricing/legal claims adversarially re-verified.
- `l3-competitors.md` — front-desk voice is vet's fastest-moving agentic beachhead (Dodo/Otto/Weave/Scritch).
- `l0-firsthand-regulatory.md` — AAVSB whitepaper first-hand; Dodo confirmed as a **sanctioned ezyVet integration partner** with emergency routing + refill generation shipping today.
- `synthesis.md` — the two surviving theses (continuity moat; benefits over parity).

Overall confidence: **MEDIUM** — facts HIGH; the one gap that sets scope (after-hours emergency-vs-booking ratio) has no first-party data yet.

## System Reality

### Files / components read
- `sms_gateway.py` — real dual-mode Twilio wrapper (live REST `messages.create` / simulation fallback). **SMS only.** No Voice, no Media Streams, no bidirectional audio. Reusable for the outbound leg (warm-transfer callback, morning-report delivery), not the voice channel itself.
- `agents/booking_agent.py` — atomic hold→confirm SQLite transaction + lifecycle states + reminder arm: the **book/reschedule** verbs the voice channel calls into.
- `agents/availability_agent.py`, `waitlist.py` — slot enumeration + slot-offer matching (the **slot-recovery** verb).
- `agents/prescriptions.py` — refill workflow: `pending → auto_approved (if refills_remaining>0) | vet_review`. **An autonomous auto-approve path exists.**
- `clinic_resolver.py`, `dispatch.py` — availability + response formatting.
- `.specify/memory/constitution.md` — demo-scoped (SQLite, no external LLM, pure-Python heuristics). See Constitution Check.

### DB Tables
| Table | Exists? | Schema matches? | Surprise? |
|---|---|---|---|
| timeblocks / slot_holds / waitlist / prescriptions | yes (SQLite `scheduler.db`) | for booking verbs, yes | no — voice reuses booking pipeline |
| call / transcript / consent-log / caller-identity | **no** | n/a | yes — all greenfield |

### External Dependencies
| Dependency | Built? | Deployed? | Notes |
|---|---|---|---|
| Twilio SMS | yes | dev | outbound leg only |
| Twilio Media Streams (μ-law 8kHz bridge) | **no** | — | greenfield; reference bridges exist |
| Gemini Live realtime (speech-to-speech) | **no** | — | `google.genai` SDK in venv; Preview-labeled |
| OpenAI Realtime fallback | **no** | — | behind the C3 port |
| **C3 realtime channel tier** | **no** | — | board ask — **the pacing dependency** |
| VP-4a caller identity + memory scoping | **no** | — | required for the differentiation |
| VP-5 on-call rota (machine-readable) | unknown at pilot clinics | — | Open Q7 |
| VP-9 vet-signed protocol + ER directory | **no** | — | gate on any live emergency call |

### Data Volumes
Proxy: L5 EST after-hours profile ≈ 300 calls/mo/clinic × 4 min ≈ 1,200 min/mo → ~$36–50/clinic/mo COGS. Real Goldsmith after-hours volume + emergency fraction: **not yet obtained** (Open Q5).

### Surprises
1. **The voice channel is entirely greenfield.** Only SMS exists; the realtime pipe (Media Streams bridge, transcoding, session management, barge-in, warm transfer) is 4–8 wks of new engineering. `sms_gateway.py` is not a starting point beyond the outbound SMS leg.
2. **`prescriptions.py` has an autonomous `auto_approved` refill path** — directly at odds with "refills never autonomous." The voice refill-request verb must produce **draft-for-approval only** and must not touch that branch.
3. **The demo constitution is not the pilot architecture.** SQLite / no-external-LLM / pure-Python is the demo scaffold; voice runs on the VP-1 convergence platform (Postgres/RLS envelope plane + external realtime LLM). 010 targets the platform, not this repo — a deliberate scope departure (see Constitution Check).
4. **"Same Vera" is not buildable in 3a alone.** It needs VP-4a caller identity + Thoth memory scoping (separate programs). Cycle 3a can ship a competent but **stateless** after-hours line; the moat lands only when VP-4a lands in parallel.

## JTBD
**Job statement**: *"When a client calls my clinic — 2pm or 2am — I want them answered immediately by the same Vera who knows their family and my schedule, who books them, handles the routine, and gets true emergencies to a vet fast — so we never lose a client to a missed call and my staff never drown in the phones."*
**Push**: after-hours calls go to voicemail or a $200–300/mo human service; missed calls = lost clients; daytime staff drown in the phones.
**Pull**: a 24/7 front door that books, deflects, and escalates — and remembers the caller.
**Anxiety**: an AI mishandling a real emergency (existential); an AI "sounding clinical" and creating liability; clients rejecting a bot.
**Habit**: voicemail + GuardianVets-class after-hours line + morning callback triage by staff.
**Non-consumption alternative**: voicemail; GuardianVets human triage; or a stateless competitor (Dodo/Otto/Weave) that answers but does not know the family.
**Confidence**: MEDIUM-HIGH — grounded in F1 + Matt's continuity thesis; the call-mix that sets the achievable containment is unmeasured.

## Opportunity
**Product outcome**: after-hours **containment 50–60%** of non-emergency calls (book/answer/message); **100% of emergency-flagged calls escalated, zero silent drops**; booking accuracy ≥99% audited; AI+recording disclosure on 100% of calls; **$/call telemetry from call #1** (R7). Owner-felt benefits: recovered missed-call revenue, staff off the phones. Pilot numbers become marketing assets — no vet voice competitor publishes containment or pricing.
**Opportunity**: the front door is the most-contested agentic beachhead in vet and the channel on which the continuity moat is proven; owning it before Dodo/Weave close it (12–18 mo window) is the wedge.
**Top 3 assumptions**:
1. **Desirability**: owners (and their clients) accept an AI answering after-hours given first-utterance disclosure + always-offer-to-escalate. MED risk.
2. **Usability**: callers navigate the voice flow and escalation reliably at production latency (P90 3.3–3.8s measured) with barge-in that doesn't misfire on backchannels. MED-HIGH risk.
3. **Feasibility**: a deterministic emergency state machine + in-turn-loop autonomy gate runs on a five-nines line over a **Preview** realtime model that lacks async function calling. HIGH risk.

## Shaping
### Solution Sketch (program cycles; 3a is the pilot-Phase-3 deliverable)
- **3a — After-hours line (Medium, 1 clinic, ~Oct):** Twilio Media Streams ↔ Gemini Live bridge **behind the C3 port** with an OpenAI Realtime fallback. Fixed first utterance (AI + recording + transcription + "say emergency"). Identify caller (VP-4a) → book/reschedule via `booking_agent`/`availability_agent` → voicemail deflection → **morning report of every call**. The vet-signed **protocol state machine + autonomy gate run INSIDE the turn loop** — the realtime model *narrates*, it does not decide any write or escalation.
- **3b — Emergency routing (M):** hard escalation keywords; warm transfer to on-call (VP-5) / ER partner directory (VP-9); 100% escalation SLO; full transcripts; audit every after-hours emergency for 6 months.
- **3c — Daytime overflow + continuity (M):** overflow rings Vera before voicemail; cross-channel thread pickup ("about Rex's follow-up?"); ES bilingual **gated on a phone-grade WER benchmark**.
- **3d — Scale + telemetry (M):** containment/booking/escalation dashboards; cost-per-call; number porting; overflow-to-human contract.

### Rabbit Holes
1. **Under-triage is existential (R3):** one missed emergency at the pilot ends the voice program and taints the envelope. Deterministic keywords + always-offer-to-escalate + human overflow behind everything + 6-month audit of every flagged call.
2. **Autonomy gate inside a speech-to-speech turn loop:** Gemini 3.1 Flash Live has **no async/NON_BLOCKING function calling** — a slow PIMS lookup blocks the turn. Use 2.5 Native Audio where lookups matter, or pre-fetch/fast tools. This is the load-bearing unknown for "gate in the loop."
3. **Gemini Live Preview on a five-nines line:** 15-min session cap, ~10-min WS lifecycle (needs resumption), context re-billing on long calls, latency creep — hence the OpenAI Realtime adapter behind the port from day 1.
4. **False barge-in on backchannels** ("uh-huh") — the #1 turn-taking failure; benchmark <400ms detect / <2% false on real audio.
5. **Bilingual code-switch WER 15–20%** — a trust-destroyer if shipped unbenchmarked (R6).
6. **"Same Vera" depends on VP-4a** — without it, 3a is stateless and undifferentiated vs Dodo.

### No-Gos (cycle 3a)
- Any clinical assessment / diagnosis / prognosis / dosing / drug-naming; forbidden self-descriptions ("nurse," "tech," "doctor" — the TX/FL representation trap, CA AB 489 direction).
- **Autonomous refills** — refill-request is draft-for-approval only; must not touch `prescriptions.py`'s `auto_approved` path.
- Daytime answering (after-hours first); bilingual GA (gate on WER); staff-rota build (consume VP-5); number porting.
- Managed platform (Vapi/Retell) as **production** — a 2–3 wk throwaway prototype for discovery is fine; the turn loop is core IP.
- Marketing "answers the phone" as the wedge; per-minute pricing gimmicks (flat $149–249/mo tier per R8).

### Appetite Assessment
Program Large; **3a Medium and hard-gated** on: C3 port availability, Goldsmith after-hours call-mix data, and a vet-signed protocol before any live call. Confirmed.

## Registry + Constitution
### COS-Platform Registry
- **Consumes**: chief-of-staff pattern (interaction loop, **KNOW→ADVISE→DECIDE** autonomy ladder, **person-like-memory / Thoth** — the continuity substrate); **General Scheduler Core** booking/availability/waitlist agents (the book/reschedule/slot-recovery verbs); `sms_gateway.py` (outbound SMS leg).
- **Registers back**: **realtime-voice-channel + protocol-state-machine-with-in-loop-autonomy-gate** as a pattern candidate — this IS the C3 realtime channel tier board ask; amortizes across FarmAgent and every future vertical.

### Constitution Check
The GS constitution is demo-scoped; 010 targets the pilot/convergence platform, so several principles apply in spirit while III departs by design.
| Principle | Applies? | Status |
|---|---|---|
| I Demo-First / Verbose Log | yes (spirit) | compliant — every call + every gate/escalation decision auditable (transcripts + audit log); exceeds the demo bar |
| II Agentic Pipeline Integrity | yes | compliant — bookings still flow Intake→Match→Solve→Dispatch; voice is a new intake channel, no bypass writes |
| III Data Simplicity (SQLite, no external LLM) | partial | **VIOLATION-by-design** — voice requires an external realtime LLM + the Postgres/RLS envelope plane. The demo constitution is superseded by the VP-1 platform for pilot; flag for scope note / amendment |
| IV Role-Aware UI | yes | compliant — owner morning report, staff escalation, client-scoped voice persona |
| V Incremental Buildability | yes | compliant — 3a independently deployable; does not break the existing demo |

**Violations**: III is a deliberate platform-scope departure, not a defect — surface to Matt. The binding vet "constitution" (AAVSB administrative/clinical line + Expert Firewall) is **preserved architecturally**: no clinical verbs at any autonomy level; triage is pure routing (zero assessment language); refills draft-for-approval.

## Competitive Context
### Best-in-Class Patterns
- **Dodo** — vet-native autonomous voice, emergency routing, 5-PIMS write-back, **sanctioned ezyVet partner**; ~12 mo ahead on features and the direct threat.
- **GuardianVets** ($7M) — human triage + probable AI front layer; the natural **overflow partner** (backstop + credibility), not merely a displaced line item.
- **Assort ($1.2B) / Hyro** — the human-healthcare maturity preview: 44–50% published containment, route-everything-clinical-to-humans, and deep system-of-record integration as the moat pitch.

### Category Gap
Nobody bundles voice into a whole-clinic Chief of Staff, and nobody has **identity continuity** — "Hi Mrs. Alvarez, is this about Rex's follow-up?" is something a stateless per-call receptionist structurally cannot say. That continuity + the operating layer is the wedge; a stateless overlay can only match it by building the entire memory/ops layer (i.e. becoming VetAgent). Nobody publishes containment/pricing → the pilot's numbers are unique marketing assets.

## ICE Score
| Factor | Score | Assumption |
|---|---|---|
| Impact | 9/10 | The most-contested beachhead; headline demo; recovered missed-call revenue + staff relief; the channel on which the continuity moat is proven |
| Confidence | 6/10 | Tech/legal/competitive facts verified HIGH, but the load-bearing unknowns (Goldsmith call-mix, Gemini Live Preview stability, in-loop async tools, unbuilt C3 + VP-4a) are unvalidated |
| Ease | 4/10 | Greenfield realtime channel; existential under-triage risk; deterministic protocol + in-turn-loop gate against a Preview model with no async tools; five-nines expectation; depends on 3 unbuilt programs (C3, VP-4a, VP-5/VP-9) |
| **ICE Score** | **216** | |

**Low-confidence flags**: Confidence (6) and **Ease (4)** both need validation → (a) 2–3 wk throwaway prototype of the Twilio↔Gemini Live bridge + in-loop gate before committing; (b) 2 weeks of Goldsmith after-hours logs to set the containment ceiling / emergency fraction; (c) vet-signed protocol + counsel sign-off before any live call; (d) prove the C3 port + OpenAI fallback.

## Proceed Signal
- [x] Ready to proceed to speckit-specify — **with caveats**
- [ ] Needs more discovery

**Recommendation**: **Proceed with caveats** (3a is hard-gated):
1. **C3 realtime channel tier is the pacing dependency** (board ask) — 010 cannot ship until the C3 port lands with the OpenAI Realtime fallback behind it.
2. **Vet-signed AVMA-teletriage protocol + counsel sign-off** on consent / no-training vendor clauses (*In re Otter.AI* CIPA exposure) **before the first live call.**
3. **Get 2 weeks of Goldsmith after-hours call logs** (GuardianVets/voicemail) to set the containment ceiling + emergency fraction (Open Q5) before final scoping.
4. **Reconcile `prescriptions.py`'s `auto_approved` path** — the voice refill verb must be draft-for-approval only.
5. **Differentiation needs VP-4a in parallel** — 3a alone is stateless-competitive, not the moat; sequence VP-4a with 3a.
6. Throwaway Vapi/Gemini prototype allowed for discovery; **production is Twilio + Gemini Live direct**, gate in the loop.

## Marketing Output
**Produced by**: speckit-discover — 2026-07-09

### Positioning Message Seed
"When a client calls — 2pm or 2am — they're answered immediately by the same Vera who knows their family and your schedule, who books them, handles the routine, and gets true emergencies to a vet fast — so you never lose a client to a missed call and your staff never drown in the phones." (Public copy sells benefits — slots filled, missed-call revenue recovered, staff-hours returned — never "we answer the phone.")
**Source**: JTBD statement. Use in: speckit-marketing brief.md (elevator pitch anchor).

### Why-Now Angle
The front door is filling fast — Dodo/Otto/Weave broaden front-desk→ops in 6–12 months — and no vet voice player publishes containment or pricing, so the Goldsmith pilot's measured after-hours numbers (50–60% containment, ≥99% booking accuracy, 100% escalation) become the category's only published benchmarks.
**Source**: OST product outcome + L3/L5 timeline. Use in: brief.md (Why Now).

### Differentiation Source
**Identity continuity** — the same Vera across calls, channels, and visits ("is this about Rex's follow-up?") bundled inside a whole-clinic Chief of Staff. A stateless per-call receptionist cannot say it; an overlay can only match it by building the entire memory + operating layer. NOT feature-parity with Dodo/Otto/GuardianVets.
**Source**: Competitive category gap + Matt's continuity thesis (L0 §4). Use in: brief.md (What Makes This Different).
