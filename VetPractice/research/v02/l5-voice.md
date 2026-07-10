# Lane 5 — Voice AI for the Front Desk: Landscape, Feasibility, and the Emergency-Routing Bar

**Date:** 2026-07-09 · **Analyst:** Lane 5 · **Scope:** V0.2 F1 (Vera Voice — phone scheduling + emergency routing, after-hours first)
**Method:** 5 parallel web-research threads (~120 searches/fetches) + adversarial re-verification of load-bearing pricing and legal claims. Tags: **[V]** verified on primary/official source · **[U]** vendor-claim or secondary source · **[EST]** derived estimate · **[INTERP]** analyst interpretation.

---

## Executive framing

Voice AI receptionists crossed from demo to deployed category in 2025–26: PolyAI raised $86M at $750M (Dec 2025), Slang.ai $36M Series B (Feb 2026), and healthcare patient-access player Assort Health hit a **$1.2B valuation two weeks ago** (June 24, 2026) [V]. **Veterinary specifically is early but no longer empty**: exactly two vet-native autonomous voice agents exist with real traction signals (Dodo, Scritch), the incumbents (Weave, PetDesk, Otto, Digitail, ezyVet/IDEXX, Covetrus) have all stopped at scribe + call-recording + *text* automation — none answers the vet phone autonomously today — and GuardianVets remains fundamentally human-tech triage with a probable AI intake front-layer. The after-hours wedge is technically feasible at **~$0.03–0.04/min all-in** on our Gemini stack, the legal bar for routing-not-diagnosis is real but well-marked, and the window for Vera to own this before Dodo or Weave closes it is roughly 12–18 months [INTERP].

---

## 1. The market: voice AI receptionists, July 2026

### 1a. General SMB

| Product | Segment | Pricing (2026) | Performance | Integration | Traction |
|---|---|---|---|---|---|
| **Slang.ai** | Restaurants/hospitality | Flat monthly per location, sales-gated; third-party est. $399–$599/mo [U] | 96%+ guest CSAT claimed [U]; no published containment | Native OpenTable, SevenRooms, Tripleseat [V] | $36M Series B Feb 2026, $68M total; 25M calls, 2,000+ locations [V] |
| **Loman.ai** | Restaurants | $299/mo (500 min) / $529/mo (1,000 min, 3 locations) [U] | Claims +26% phone-order revenue [U] | ~30 POS: Square, Toast, Clover, Olo; OpenTable write-back Dec 2025 [V] | $3.5M seed Aug 2025 [V] |
| **Goodcall** | Home services/SMB | Per-unique-caller: $79/$129/$249/mo (100/250/500 callers), unlimited minutes, $0.50 overage [V] | None published | Zapier, Google Calendar, Housecall Pro [V] | ~$4–8M raised [U] |
| **Smith.ai** | SMB/legal, **hybrid AI+human** | AI tier ~$95–800/mo ($1.60–2.40/call); human hybrid ~$9.75–11/call; new flat "Done-for-You AI" $500–2,000/mo [U — pricing now sales-gated] | None published | CRM/calendar breadth | ~$26.7M revenue 2024, ~3,000 customers, only $13M raised [U] |
| **Rosie (heyrosie)** | Home services/SMB | $49/mo (250 min) / $149 (1,000) / $299 (2,000); overage $0.25/min; **EN/ES bilingual included** [V] | 2,000+ businesses, 3.1M+ calls [V vendor] | Calendar booking + warm transfer from $149 tier | Bootstrapped-scale |
| **PolyAI** | Enterprise call center | Custom per-ASR-minute; est. ~$150K/yr entry [U] | **50–87% containment**; PG&E 67% across ~16M calls/yr; Golden Nugget 87% [V] | Enterprise CCaaS | $86M Series D at $750M, Dec 2025; ARR → >$40M [V] |

Also: **Dialzara** ($29–349/mo, $0.35–0.48/min overage) [V]; **Synthflow** (dev platform, ~$0.09/min + LLM, $30M raised) [V]; **Air.ai is dead** — FTC settlement March 2026 bans its owners from marketing business opportunities [V — the category's cautionary tale on hype-selling].

**Pricing-model read:** the market splits into flat-monthly-per-location (restaurant vertical), minute buckets + $0.25–0.50/min overage (SMB horizontal), per-unique-caller (Goodcall), per-call ($1.60 AI → $9.75+ human hybrid, Smith.ai), and enterprise contracts. **Nobody serious in a vertical prices per-minute raw** — they price against the alternative (staff time, answering service), which supports R8's per-clinic-flat + voice usage tier.

### 1b. Human-healthcare front desk (the maturity preview for vet)

| Product | What | Metrics | Traction |
|---|---|---|---|
| **Assort Health** | Patient-access voice: 24/7 scheduling, routing-to-provider, refills, intake | 190M+ interactions; +5% appt volume; 4.3/5 CSAT (344K reviews); ~$3.3M annual revenue per 100 providers [U vendor]; est. $1.5K–10K+/mo [U] | **$120M Series C at $1.2B, June 24 2026** (Menlo); 5,000 providers, 15+ EHRs incl. Epic/Athena [V] |
| **Hyro** | Enterprise IDN voice+chat | Inova: **50% of appointment calls AI-resolved**, 4,272 staff-hrs/mo saved; Intermountain: 44% resolved w/o agents, 91% routed correctly, 27% handled after-hours [V case studies] | $95M total; Intermountain, Inova, Tampa General; est. $10K+/mo [U] |
| **Infinitus** | Outbound payer calls (benefit verification, prior auth) — not front desk | 8M+ calls, 200M+ min automated; 98% call success [V vendor] | $102.9M; a16z-led Series C [V] |
| **Notable** | Digital-first patient access + voice layer | ~12,000 sites; Montage: −11% no-shows [V vendor] | $100M Series B 2021; no raise since [V] |
| **Hippocratic AI** | Non-diagnostic clinical voice (post-discharge, adherence) | 115M+ interactions, "no safety issues" [U vendor]; est. **$9/agent-hour** (= $0.15/min) [U] | $3.5B valuation Nov 2025, $404M total [V] |

Also: Cedar "Kora" (billing calls, built on Twilio, 27% handle-time cut) [V]; Zocdoc "Zo" (May 2025); Talkdesk Autopilot; **Arini** (dental receptionist, YC W24 — Weave's AI Receptionist also currently supports *only dental PIMS*).

**The healthcare lesson:** the winning pattern is administrative automation + route-everything-clinical-to-humans; the winners integrate deep with the system of record (Assort's "most robust Athena integration" claim is its moat pitch); containment of 44–50% on appointment-type calls is the realistic published bar. All performance numbers are vendor-reported — none independently audited.

### 1c. Veterinary — the actual competitive set

| Product | What it does | Voice-autonomous? | PIMS depth | Pricing | Traction |
|---|---|---|---|---|---|
| **Dodo (dodo.ai/vet)** | 24/7 answering, routes by species/urgency, **emergency detection → ER info + on-call alert**, books by provider availability, refills, intake | **Yes** | Cornerstone, ezyVet, Avimark, Digitail, DaySmart; claims "sub-second reads/writes," 99.9% uptime [V vendor] | Undisclosed | Claims "1 in 3 of the largest vet ER clinics"; one group 14K+ appts in 4 months [U vendor] |
| **Scritch "Emily"** | Front-desk voice: book/reschedule/cancel, symptom-based urgency triage + escalation, after-hours, cancellation-fill, refills | **Yes** | PIMS integration claimed, names not listed [U] | Undisclosed | YC W24, 2 founders (ex-Tesla Autopilot / ex-Amazon), $500K seed on record (likely stale); one clinic: −50% human-handled calls [U] |
| **GuardianVets** | After-hours teletriage by **live credentialed vet techs** on the clinic's own protocols; books; PIMS sync | No (human); "AI Voice & Chat" intake layer indexed but page 404s — probable hybrid front-layer [U] | PIMS outcome sync | Not public (our stack model: $200–300/mo line item) | 2.5M+ after-hours cases, "thousands of practices" [U vendor]; founded 2017 |
| **VetRec (vetrec.io)** | Scribe company expanding into AI phone receptionist: 24/7 answer, book into PIMS calendar, route urgent to staff, explicitly no medical advice | **Yes** (new) | PIMS calendar write claimed | Undisclosed | Scribe base; voice product early [U] |
| **Weave AI Receptionist** | Autonomous AI voice answering + booking via Weave calendar — **but supported PIMS today are Dentrix/Eaglesoft/Open Dental (all dental)**; vet page sells phone system + Call Pop only [V] | Yes, not for vet yet | Dental only | Not public | Public company; the moment they flip vet PIMS on, distribution is instant |

Incumbents verified **negative** for autonomous vet voice answering: **Otto** (scribe + call recording + *Agentic Confirmations = text*, Jan 2026; 5,000+ clinics) [V], **PetDesk** (vet VoIP + AI call summaries, merged into PetDesk Communications June 2026 — no answering agent) [V], **Digitail** (VoIP + post-call AI only) [V], **ezyVet/IDEXX** (AI-Assisted Notes = scribe; no phone agent) [V], **Covetrus** (Pulse scribe) [V], Vetsource/Vetcove (n/a) [V]. Low-end horizontal resellers with vet landing pages: AgentZap ($109/mo, "2,500 clinics" [U]), NextPhone ($199/mo), PupPilot — marketing claims, not vet-native depth.

**Competitive read [INTERP]:** (1) The vet-native field is 2–3 startups deep with opaque pricing, no published containment rates, and shallow funding — beatable, but **Dodo's ER-clinic positioning and 5-PIMS write-back is exactly our wedge and they're 12+ months ahead on it**. (2) The structural threat is Weave extending its dental AI Receptionist to vet PIMS, and GuardianVets bolting AI intake onto its trusted human-triage brand. (3) Nobody — including Dodo — bundles voice into a broader practice-operations Chief of Staff; standalone phone-answering is a feature Vera absorbs, which is our differentiation and our pricing cover.

---

## 2. The tech stack, mid-2026

### Realtime model options (verified 2026 pricing)

| Option | Audio pricing | $/min math | Latency | Notes |
|---|---|---|---|---|
| **Gemini 3.1 Flash Live** (`gemini-3.1-flash-live-preview`) | $3/1M tok in, $12/1M out — **Google's own per-min figures: $0.005 in / $0.018 out** [V, ai.google.dev/gemini-api/docs/pricing, updated 2026-06-30] | **$0.014–0.023/min** (50–100% agent talk duty) [EST on V rates] | ~320–800ms TTFA [U]; native speech-to-speech 160–400ms class | Server VAD + barge-in first-class (`interrupted` flag, tunable `silenceDurationMs`); parallel+compositional function calling [V]; **no async/NON_BLOCKING tools on 3.1 Live** (2.5 Native Audio has it) [V]; 15-min session cap without `contextWindowCompression`, ~10-min WS lifetime with resumption [V]; **still Preview-labeled**; no first-party PSTN — bridge via Twilio Media Streams with μ-law 8kHz ↔ PCM 16/24kHz transcoding [V] |
| **OpenAI Realtime (gpt-realtime-2.1 / -mini)** | $32/$64 per 1M audio tok (mini $10/$20) [V] | ~$0.10/min naive; **$0.05–0.10/min with prompt caching**; mini ~$0.03–0.10 [EST] | mini 212ms TTFA [U]; ~800ms voice-to-voice | **Native SIP endpoint** (no OpenAI charge for the SIP leg) [V]; semantic VAD; native remote-MCP tool support [V] |
| **Composed: Deepgram Nova-3 + LLM + ElevenLabs Flash** | STT $0.0048–0.0058/min [V]; TTS $0.05/1K chars ≈ $0.045/min speech [V rate]; LLM ~$0.003–0.01/min | **~$0.05–0.08/min** incl. telephony [EST] | **800ms–2s typical** — cascade latency is the killer [U] | Max control per component; Nova-3 multilingual has code-switching |

**Gemini Live is the cheapest realtime speech-to-speech by ~4x on audio-out** ($12 vs $64/1M) and matches our stack — but carries Preview risk, session-limit engineering, the context-rebilling trap on long calls (mitigate with compression), and reported latency creep in long sessions.

### Infra platforms vs Twilio-direct

| Layer | Cost | What you get |
|---|---|---|
| **Twilio direct** | Inbound $0.0085/min + Media Streams $0.0044/min + number $1.15/mo + recording $0.0025/min [V] | Raw pipes. You build endpointing, barge-in, warm transfer (Conference+Dial), voicemail detection (AMD $0.0075/call), transcoding, session management |
| **Vapi** | **$0.05/min platform** + providers at cost ($0 markup on BYO keys); $10/line/mo concurrency [V] | Managed turn-taking, backchannel-aware barge-in, 7 transfer modes incl. warm-with-AI-summary, voicemail detection, dashboards. Warm transfer = conference model, Twilio/Vapi numbers only [V] |
| **Retell** | $0.055/min infra + itemized; headline $0.07–0.31/min, typical ~$0.125 [V/EST] | Endpointing widely cited best-in-class |
| **Bland** | Bundled $0.11–0.14/min [V] | Simplest, least granular |

### Bill of materials (US inbound, per minute)

- **(a) Gemini Live + Twilio direct: ~$0.027–0.036/min** (≈ **$0.03**; +recording ≈ $0.03–0.04 hardened) [V rates / EST duty-cycle]
- **(b) Vapi + Gemini BYO + Twilio: ~$0.077–0.086/min**; Retell typical ~$0.125 [V/EST]
- (c) OpenAI Realtime + SIP: ~$0.06–0.12/min cached [EST]; (d) composed cascade: $0.05–0.08/min at 2–4x latency [EST]

At an after-hours call profile (say 300 calls/mo/clinic × 4 min avg = 1,200 min), direct build ≈ **$36–48/clinic/mo COGS** vs $92–150 managed — against a GuardianVets line item of $200–300/mo. Gross margin works at any plausible price point either way; the direct build matters more for control than for cost [INTERP].

### Cross-cutting engineering facts

- **Barge-in bar (2026):** detection <400ms from speech onset, full handle <150ms, false-barge-in <2%; the #1 failure is backchannels ("uh-huh," "okay") triggering false interrupts — test explicitly [V, futureagi/hamming runbooks].
- **Latency reality vs marketing:** measured production across 4M+ calls: **P50 1.4–1.7s, P90 3.3–3.8s, P99 8.4s+** [V, hamming.ai Jan 2026]. Native speech-to-speech (Gemini/OpenAI) at 160–400ms vs 1–2s cascaded is the single biggest lever — an argument for Gemini Live over a composed stack.
- **Spanish (R6):** Gemini Live: 70+ languages with mid-call auto language switching [V]. But **code-switched ES-EN degrades STT to 15–20% WER vs ~5% monolingual, and no vendor publishes phone-grade 8kHz Spanish WER** — benchmark on our own call audio before promising bilingual [V, coval.ai Jun 2026].
- **Voicemail deflection:** Twilio AMD or LLM-based detection (don't double-bill by enabling both) [V].

---

## 3. The emergency-routing bar (legal/compliance)

### How the incumbent human version works
GuardianVets: live credentialed vet techs (3–5 yrs ER experience) triage on **the client hospital's own protocols**, route (ER / morning appointment / resolve), sync notes to PIMS [U vendor]. Industry framing: after-hours is a routing problem — ~85% of after-hours calls don't require a veterinarian [U]. Tech telephone-triage standards exist as training/CE (rapid ABC assessment; **always offer to see the animal; never dismiss a concern; log every call**), not as codified law. **Correction to our design brief:** RECOVER is an in-hospital CPR guideline body (major 2024 update) and explicitly does **not** cover telephone triage — do not cite it as the phone-triage standard; the right anchors are AVMA teletriage policy + VTS(ECC)-style protocols + the deployment state's practice act [V].

### What routing-not-diagnosis legally requires
- **AVMA teletriage definition** (our safe harbor): "assessment and management (immediate referral to a veterinarian or not)… **A diagnosis is not rendered.**" Teletriage requires no VCPR; telemedicine does; a VCPR **cannot be established solely by telephonic/electronic means** (AVMA MVPA; FDA concurs for prescribing) [V].
- Without a VCPR the agent MAY: assess urgency, route to care, give generic first-aid/education. It may NOT: diagnose, give prognosis, recommend treatment, or recommend/dose **any** drug including OTC [V/INTERP, VVCA].
- **The "representation" trap:** TX Occ. Code §801.002 and Fla. Stat. §474.202 define practicing to include *representing an ability/willingness* to diagnose — an AI that merely *sounds* clinical can violate the act without rendering a diagnosis. Never let Vera claim or imply she is (or sounds like) a tech or vet [V statutes / INTERP].

### Liability precedent (all from human-health/AI, none vet yet)
- **Pennsylvania v. Character Technologies (filed May 1, 2026)** — first state action for **unauthorized practice of medicine by a chatbot**; disclaimers did not deter the regulator [V]. **Garcia v. Character Technologies** (M.D. Fla. 2025, settled Jan 2026) — chatbot treated as a **product** for design-defect liability; disclaimers didn't defeat the claim [V]. **Moffatt v. Air Canada** (2024) — you own your bot's words [V]. **NEDA "Tessa"** (2023) — the reputational template for a bot replacing a human helpline badly [V]. No public case yet of a healthcare **voice** agent causing documented patient harm [V, absence]. FTC "Operation AI Comply": unsubstantiated triage-accuracy marketing is FTC exposure [V].
- Net posture [INTERP]: liability attaches at (a) clinical assessment, (b) implied credentials, (c) **under-triage of a true emergency**. The deploying clinic is defendant #1 (vicarious); the vendor faces product liability. Design must always err toward escalation.

### Disclosure + recording (state patchwork, July 2026)
- **Utah AI Policy Act** is the binding template: affirmative AI disclosure **at the start** for regulated occupations / high-risk interactions (medical decisions + sensitive info); safe harbor if disclosed; up to $2,500/violation [V]. CA SB 1001 is online-only (not voice) [V]; CA AB 2905 covers prerecorded robocalls (relevant only for outbound callbacks) [V]; CA SB 243 companion-bot law's "reasonable person misled" trigger is the doctrine courts will reach for [V/INTERP]; **Colorado is in a gap** — SB 24-205 repealed/replaced, new act effective Jan 1, 2027 [V]; NJ A4730 (verbal AI notice at interaction start — would squarely cover us) pending [V]. Healthcare-specific CA laws (AB 3030 GenAI-communication disclaimers, AB 489 no-licensure-terms) are human-health but signal direction [V].
- **Recording consent:** all-party states = CA, CT, DE, FL, IL, MD, MA, MT, NH, PA, WA, + NV (case law) + MI (treat as all-party) [V]. **AI transcription is the live exposure**: *In re Otter.AI* (N.D. Cal., ruling pending) treats transcription vendors as third-party eavesdroppers, with a "capability test" where vendor ability to train on call data can itself create CIPA liability ($5,000/violation) [V case status].
- **The compliant first utterance** [INTERP]: *"You've reached [clinic] after-hours. This is Vera, an AI assistant — this call is recorded and transcribed. If your pet is having an emergency, say 'emergency' at any time."* One line satisfies Utah's affirmative prong, implied all-party consent, and the misled-person test. Contractually prohibit STT/LLM vendors from training on call audio; keep consent logs.

---

## 4. Failure modes + benchmarks

**Documented failure classes:**
1. **Booking errors** — wrong provider/slot/location writes into the system of record; the healthcare deployment literature ranks this the #1 practical failure of AI receptionists [U, medlaunch]. Mitigation: read-back confirmation before write + idempotent booking + post-call audit.
2. **Hallucinated policy/info** — Air Canada precedent: the business eats the bot's false statements [V]. Mitigation: closed-book answers only from clinic config (hours, prep, pricing), never model priors.
3. **False barge-in / turn-taking failures** — backchannels cut the agent off mid-sentence; caller frustration compounds at P90 latency (3.3–3.8s measured) [V].
4. **Under-triage** — the catastrophic one (R3's "missed emergency call"). No vet incident yet on record; NEDA Tessa and Babylon's missed-MI demo are the adjacent cautionary cases [V].
5. **Demo-vs-production gap sold as magic** — Air.ai's FTC ban shows the regulatory endpoint of over-claiming [V].

**What "good" looks like (published bars):** PolyAI 50–87% containment at enterprise; Hyro/Inova 50% of appointment-management calls fully AI-resolved; Intermountain 44% overall, 91% routing accuracy; Talkdesk "up to 45%" [V/U]. **No vet-specific containment or booking-rate percentages are published anywhere** — only anecdotes (Scritch −50% human-handled calls; Otto −⅓ call volume; Dodo 14K appts/4 mo) [U]. Realistic V0.2 targets [INTERP]: after-hours **containment 50–60%** of non-emergency calls (book/answer/message), **100% of emergency-flagged calls escalated** with zero silent drops, booking-accuracy ≥99% audited, disclosure delivered on 100% of calls.

**Human-fallback patterns:** warm transfer with AI summary handed to the human (Vapi's `summaryPlan` pattern — replicate in-house); overflow to a human answering service on failure/SLO breach (R3 — GuardianVets itself is the natural overflow partner: "AI answers first, credentialed tech on escalation" is *their* probable roadmap and could be our partnership instead); graceful degradation to voicemail-with-callback-promise as last resort, never dead air. Smith.ai's whole business proves the hybrid pattern prices at $9.75+/call — the human layer is the expensive part, which is exactly why containment economics work.

---

## 5. Build-vs-buy recommendation

**Recommendation: BUILD, Twilio + Gemini Live direct — with a 2–3 week Vapi throwaway prototype allowed for discovery, and GuardianVets(-class) human overflow behind it.**

| Option | All-in $/min | Control / Expert Firewall fit | Verdict |
|---|---|---|---|
| **Twilio Media Streams + Gemini Live direct** | **~$0.03–0.04** | Full: our autonomy gate, protocol-driven triage state machine, Thoth memory, audit trail all in-loop; native s2s latency (160–400ms class) | **Target architecture** |
| Vapi/Retell managed | ~$0.08–0.13 | Good BYO-key flexibility, but the pipeline is theirs; Gemini Live *speech-to-speech* doesn't slot cleanly into their cascaded STT→LLM→TTS shape; our gate sits outside their turn loop | Prototype/demo only |
| White-label / partner (Dodo, Scritch, VetRec) | opaque | None: triage protocol, escalation logic, and data would live in a competitor's product that is *itself* the standalone version of our wedge | **No** — strategically incoherent with the envelope |
| OpenAI Realtime + SIP | ~$0.06–0.12 | Good (native SIP is genuinely simpler), off-stack | Fallback if Gemini Live Preview instability bites |

**Why direct:** (1) **The Expert Firewall is the product.** Emergency routing must be a deterministic, vet-approved protocol state machine that the realtime model *narrates* but does not control — with our autonomy gate deciding every write and every escalation. That's an architecture we can only guarantee owning the loop. (2) **Cost and latency both favor Gemini Live** (~4x cheaper audio-out than OpenAI; native s2s beats cascades by ~1s). (3) The platforms' real value (endpointing, barge-in, warm transfer, AMD) is 4–8 weeks of engineering we'd mostly have to re-verify anyway for the emergency path; reference Twilio↔Gemini bridges exist. (4) Voice gateway is Vera-core (per the F1 split) — it amortizes across FarmAgent and every future vertical; renting it caps the platform.

**Engineering caveats to carry into spec 010:** Gemini Live is Preview (re-check pricing before volume; keep an OpenAI Realtime adapter behind the gateway port); enable `contextWindowCompression` (context re-billing inflates long calls); 3.1 Flash Live lacks async function calling — either use 2.5 Native Audio where slow PIMS lookups matter or design tools to be fast/pre-fetched; build the μ-law↔PCM bridge and 10-min WS session resumption day 1; instrument $/call from call #1 (R7).

**Pricing implication (R8):** COGS ≈ $36–50/clinic/mo at after-hours volumes; the displaced GuardianVets line is $200–300/mo; Smith.ai's human-hybrid is $9.75+/call. A **$149–249/clinic/mo after-hours voice tier with a bundled minute allowance** undercuts the human service, carries 70%+ gross margin, and prices as a line-item replacement rather than per-minute novelty [INTERP].

---

## Key Risks

1. **Under-triage is existential** (R3): one missed emergency at a pilot clinic ends the voice program and taints the envelope story. Mitigate: deterministic escalation keywords, always-offer-to-escalate, 100%-escalation SLO on flagged calls, human overflow, call-audit review of every after-hours emergency for the first 6 months.
2. **Dodo closes the wedge first**: they already claim large ER clinics and 5-PIMS write-back. Our counter is bundle economics + the Goldsmith estate, not feature racing.
3. **Weave flips vet on**: dental AI Receptionist → vet PIMS is a config-scale move for a public company with installed phone lines.
4. **Gemini Live Preview instability** (latency creep, session limits, price changes) on a five-nines phone line — hence the adapter port and OpenAI fallback.
5. **CIPA/transcription litigation wave**: vendor training-rights and consent-script discipline are cheap now, class-action expensive later (R2).
6. **Bilingual over-promise**: code-switched ES phone audio at 15–20% WER can make R6 a trust-destroyer if shipped before benchmarking.

## Implications for V0.2 (feed program definitions)

1. **Spec 010-vera-voice: Twilio Media Streams + Gemini Live direct**, gateway behind a model-adapter port (OpenAI Realtime fallback); after-hours first, per the brief — the research confirms the wedge order.
2. **Triage = deterministic protocol state machine** authored/signed by a licensed vet (Goldsmith's group), inside the AVMA teletriage boundary: urgency classification + routing + generic first-aid only; hard-blocked verbs: diagnose, prognose, dose, name-a-drug; forbidden self-descriptions ("nurse," "tech," "doctor" — the TX/FL representation trap and CA AB 489 direction).
3. **Fixed first utterance** (AI + recording + transcription + "say emergency") as tenant-configurable but default-on everywhere; treat Utah's affirmative-disclosure standard as the national floor. Replace the RECOVER citation in the F1 brief with AVMA-teletriage + tech-triage CE standards.
4. **Contracts**: no-training clauses with every voice vendor (Google/Twilio DPAs) before the first pilot call; consent logs retained (extends R2).
5. **Human overflow from day 1**: warm-transfer + answering-service failover; explore GuardianVets as overflow partner rather than pure displacement — buys credibility and an incident backstop.
6. **Instrument the published-benchmark gap**: nobody in vet publishes containment/booking rates — our pilot numbers (target 50–60% after-hours containment, ≥99% booking accuracy, 100% emergency escalation) become marketing assets the moment they're real (feeds verified-claims corpus).
7. **R6 bilingual: gate on benchmark**, don't promise — run phone-grade ES/code-switch WER tests on real call audio in discovery.
8. **R8 pricing**: after-hours voice tier ~$149–249/clinic/mo with minute allowance; per-minute COGS telemetry (R7) from call #1.

## Open Questions

1. Dodo's actual pricing, funding, and true clinic count — worth direct intelligence (demo call) before positioning against them.
2. Has Scritch raised beyond the $500K YC seed? (Crunchbase blocked; a 2025–26 round would change their threat level.)
3. GuardianVets' AI Voice & Chat: real product or vaporware? (Page 404'd.) Determines partner-vs-displace.
4. Will Gemini Live audio models exit Preview (and hold pricing) before pilot voice go-live (~Q4 2026)?
5. What fraction of Goldsmith's 23 clinics' after-hours calls are emergencies vs bookings vs questions? (Sets the containment ceiling; get 2 weeks of GuardianVets/voicemail logs.)
6. *In re Otter.AI* ruling (pending) — if the CIPA capability test survives, vendor-contract language needs counsel review.
7. Does the on-call rota (F3 dependency) exist in any machine-readable form at pilot clinics today, or is that a manual-config prerequisite for 010?

## Where I expect other lanes disagree

- **Speed-vs-control**: an engineering-pragmatist lane will argue for shipping on Vapi/Retell permanently (~$0.05/min premium is trivial at pilot volume, and endpointing is hard). I hold that the emergency path and the Expert Firewall make the turn loop core IP, but the pilot-timeline argument is legitimate.
- **Risk appetite on emergencies**: a legal/strategy lane may say after-hours *emergency routing* is too hot for V0.2 and Vera should launch as after-hours *booking + message-taking only*, punting emergencies straight to the existing GuardianVets line. That's a defensible smaller wedge; it also surrenders the headline differentiator.
- **Competitive lane** may weight Dodo more heavily than I do and recommend partnering/acquiring rather than building — I read Dodo as validating the category while lacking our bundle, but "12 months behind a funded specialist" can be argued the other way.
- **Economics lane** may push per-minute usage pricing (marginal-cost transparency) against my flat-tier recommendation; the SMB comps mostly support flat-with-allowance.
- **Enterprise/F6 lane** may argue SOC 2 + reliability engineering must precede any phone answering (five-nines expectations), sequencing voice behind R1/R3 rather than parallel to the pilot.
- **Model-strategy lane** (ModelGarden) may prefer local STT/TTS on DGX for cost at scale; per Matt 2026-07-09 production stays cloud, and at $0.03/min the cloud economics don't force the issue for years.
