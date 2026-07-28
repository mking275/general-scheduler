# Discovery: Vera Notes — the opt-in ambient scribe (spec 012)

**Feature type**: new-surface — the **first deliberately DVM-facing surface** in the envelope era, and the platform's **first user-facing consumer of the Pattern-① evidence contract**. Also a **platform-common pattern candidate** (fleet brief row ④: vet proves it first, FarmAgent/MedWatchers adapt on their own substrate).
**Appetite**: Medium — cycle **12a** (opt-in capture → cited draft → existing channels) is the pilot deliverable; **12b** (ezyVet write-back) is gated behind write-verb promotion and is not this cycle.
**Passes run**: 0, 1, 2, 3, 4, 5, 6
**Artifact confidence**: **HIGH** on why-it-wins (Abridge corpus is peer-reviewed + first-hand; Digitail field intel is organic) and on the **competitive map** (fresh scan; note-to-source linking is verifiably unclaimed in veterinary, and IDEXX's free native scribe is confirmed shipping) · **MEDIUM-HIGH** on the **legal posture** (well-mapped from primary sources, but unratified by counsel and thin on veterinary-specific precedent — no AVMA policy, no state-board guidance, no on-point exam-room holding) · **MEDIUM** on transferability to the vet exam room (species/jargon/barking-dog acoustics unmeasured; **no independent accuracy benchmark exists for any veterinary scribe** [V]) · **LOW** on the capture surface (the iOS background-audio constraint is untested and is the single biggest build risk) and on client acceptance (**zero independent research exists**; all sentiment evidence is vendor-sourced).
**Date**: 2026-07-28

---

## Customer Artifacts

**Human-provided:**
- **Jay / Dr. Goldsmith** — the origin. His physician brother (large Greenville hospital system) said an ambient scribe "changed his life." Goldsmith runs **Synergy Vet**, the 23-clinic ezyVet **Enterprise** group that is the pilot (kickoff ~Aug 3). His standing strategy input: *he does not want to change software*, and his staff just absorbed an ezyVet Enterprise upgrade — a migration announcement is radioactive (Working Rule 0).
- **Matt's decisions, 2026-07-24 → 07-28** (the shaping constraints, all binding here):
  - **D5** of `StrategicStudy/abridge-design-transfer-2026-07-24.md` — proposes 012 as "opt-in ambient SOAP scribing from the DVM's own phone," two envelope-honest phases, Linked-Evidence-native.
  - **D3** — the NFR bar: draft **<60s** after interaction end; **zero new hardware**; **zero wake words**; **opt-in from the professional's own phone**.
  - **D1 → Ruling A (2026-07-28)** — **Pattern ① is platform-wide**: ONE evidence-reference contract (`claim → source-ref → resolver`), source-ref **intrinsic at generation time**, with the C6 compliance rail and the user-facing citation as two *consumers*. Vera-core's C6 port hold lifted; the contract is on the critical path and **012 is the user-facing consumer**.
  - **Products share patterns, not resources (2026-07-24)** — never a shared scribe service; every product runs the pattern on its own substrate.
  - **D4** — instrument feelings, and formalize **staff opt-in rate week-over-week** as the "beg for it" metric.
  - **§III declines** — no room hardware, no hours-saved headlines, no separate destination app for staff.

**Agent-sourced (persisted):**
- `VetPractice/research/abridge/report.md` — the what-wins corpus. Load-bearing facts: draft in **38–76s** median (peer-reviewed, PMC11843214) [V]; **zero behavior change** — no wake words, specialty/language/speakers auto-detected [V]; **Linked Evidence** — highlight a note phrase, see the transcript passage, replay the audio [V]; **the clinician always signs** [V]; **"Arrive prepared. Stay present. Leave finished."** [V]; the counter-finding — after-hours EHR time often does *not* drop; the work *feels* different [V, AMA]; and the errors are real (nitrofurantoin/nitroglycerin caught by a physician [V]; speaker-attribution failures in multi-person conversations [V]).
- `VetPractice/research/digitail/l3-field-intel.md` — the AI scribe (Tails) is **the most-cited reason people like the product** in the 2025–26 review wave [V/INTERP]; ~8 min saved per SOAP note [V]; and the crack: **"AI Scribe accuracy inconsistency on iPads"**, dictation "noticeably better on laptops/desktops than iPads" [V]. Digitail bolted on a "SOAP Verification" layer — [INTERP] they hit accuracy complaints and had to respond.
- `/home/matt/FarmAgent2-Workspace/context/what-wins-cross-product-brief.md` (Viz, 2026-07-28) — 012 is **row ④**: platform-common capability, **vet proves it first**, FarmAgent adapts for field notes, MedWatchers for pharmacist CMR documentation.
- `specs/009-vera-envelope-onboarding/known-issues.md` (KI-1/KI-2, found 2026-07-28) — the two lineage defects, **both of which name 012's note citations as blast radius**.
- Fresh field research for this discovery: **recording-consent law** (§ Consent) and the **veterinary AI-scribe competitive landscape** (§ Competitive Context), both WebSearch/WebFetch-sourced, [V]/[U]-tagged inline.

**Overall confidence**: MEDIUM-HIGH. The *category* proof is as strong as anything in our corpus. What is unvalidated is (a) that vet exam-room audio is tractable, (b) that a client in the room accepts recording, and (c) that a phone can capture it without an app.

---

## System Reality

### Files / components read

**The note already exists — in the wrong place, in the wrong shape.**
- `backend/agents/soap.py` (T005/T030, spec 002) — `SoapDraftAgent` generates a SOAP draft from **procedure type + pre-exam brief**, via Gemini with a template fallback. There is no audio anywhere near it.
- `backend/models.py::SoapNote` — `subjective / objective / assessment / plan / signed / signed_at / signed_by`. **Zero lineage fields.** No `source_id`, no `entity_ref`, no citation set. It is a flat text blob with a signature.
- `backend/repository.py` — `soap_notes` table on **demo-track SQLite**, keyed to `timeblock_id`.
- Spec 002 FR-023–FR-028 — the SOAP workspace lives in the **staff-facing web UI** (Vet role view), and **signing freezes the note read-only** and triggers the follow-up draft. The signature semantics are right; the surface is exactly what Working Rule 0 forbids pushing at staff.

**The 010 voice stack — what actually transfers.**
- `backend/voice/` — 2,967 LOC, **43/43 tasks complete (2026-07-10)**, 116 tests, **sim-only, zero live telephony or LLM-audio calls**. Live-mode is a config swap deferred to a Pilot-Activation section.
- **Reusable for 012 (the governance half, and it is genuinely valuable):**
  - `adapter_guarantees.py` — disclosure-as-first-utterance enforced *in the adapter, not the model*; append-only transcript + turn log; `finalize_transcript()` persists the **consent record + vendor no-training attestation** on the transcript row. This is the consent-plumbing pattern 012 needs, re-pointed at an in-room notice.
  - `autonomy_gate.py` — deterministic advise/propose/do/reject; the model narrates outcomes, it never decides them.
  - `voice_repository.py` — append-only enforcement on `call_turn` / `call_transcript` at the repository layer.
  - `telemetry.py` + `config/pricing.yml` — per-provider `$/audio-min` and `$/1k tokens`, cost-per-call from call #1. 012 needs cost-per-note from note #1 on the same machinery.
  - `sim.py` + the dual-mode `is_live()` resolver — the build-without-live-vendors discipline. 012 should inherit it wholesale.
  - `morning_briefing.py` — the existing-channel delivery path.
- **NOT reusable — and this is the load-bearing correction:** the 010 media path is a **telephony realtime conversational** pipeline: Twilio Media Streams **μ-law 8 kHz** ↔ `transcode.py` ↔ **speech-to-speech realtime models** (`gemini_live_adapter.py`, `openai_realtime_adapter.py`), turn-taking, barge-in, session resumption. A scribe is the opposite shape: **long-form, multi-speaker, in-room, high-fidelity capture → ASR → diarization → structured summarization**, with no turn-taking and no model speaking. There is **no ASR component, no diarization, no speaker-role model, and no long-form audio store** anywhere in the repo.

**Lineage and identity.**
- `specs/009` FR-009/SC-003 — **100% of canonical records carry `source_id`/`entity_ref`** back to their source export. This is the reference implementation named in the fleet brief, and it is the substrate a note citation resolves *into*.
- `specs/011` — household/party model, KNOW≠REVEAL default-deny scoping, tiered verification, consent registry. Spec'd, **not built**; ≥90% auto-ID on real pilot data is a Pilot-Activation gate.
- `domains/vet/clinical/README.md` — the **Tier-1/Tier-2 line**, enforced in code by a denylist grep and by 010's refusal to run an unsigned protocol. Dosing, drug interactions, treatment plans, triage content = Tier-2, gated on a named DVM signature.
- `marketing/what-vera-will-never-do.md` — published, client-facing, and three lines constrain 012 directly: *never sign a medical record*; *never diagnose, prescribe, or alter a treatment plan*; ***never state a fact it cannot source*** ("a line in a draft note" is called out by name).

### DB Tables

| Table | Exists? | Shape matches 012? | Surprise |
|---|---|---|---|
| `soap_notes` (demo SQLite) | yes | **no** — no lineage, no citations, no audio, no capture session | the artifact exists but must be superseded or re-homed onto the platform plane |
| `call_transcript` (voice PG) | yes | partial | has `audio_ref` (whole-file pointer) + `full_text` + `consent_record` + `vendor_no_training_attestation` + `retained_until` — **but no time offsets** |
| `call_turn` (voice PG) | yes | partial | `started_at`, `latency_ms`, `seq` — **no audio offsets**; turn boundaries are conversational, not spans into a recording |
| capture/encounter session | **no** | — | 012's session lifecycle (opt-in → consent → record → finalize) is greenfield |
| note claim / citation set | **no** | — | **the central new entity**; blocked on the Pattern-① contract shape |
| audio object store | **no** | — | `audio_ref` points nowhere today; retention policy undecided (§ Consent) |
| canonical practice model (`entity_ref`) | yes (009) | yes | the resolve target for non-audio citations |

### External Dependencies

| Dependency | Built? | Live? | Verdict for 012 |
|---|---|---|---|
| **Pattern-① evidence contract + port** (Vera-core) | **no — ruled, not built** | no | **Hard dependency.** Ruling A lifted the C6 hold 2026-07-28; the contract is on the critical path *now*. 012 must file its span requirements before v1 freezes (§ Citation Model). |
| **010 voice stack** | yes (sim) | **no** — 0 live calls | **Partial dependency, honestly stated**: the governance half transfers; the media half does not. 012 must **not** be sequenced behind 010 going live. |
| **009 lineage** | yes, shipped | pilot-pending | Resolve target. **KI-1 blocks** citing any record a delta delivery can rewrite; **KI-2 blocks** citing derived figures. Both must sequence with the contract, not around it. |
| **011 identity** | spec only | no | **Soft dependency** — 012 needs *which patient this note is for*, which the DVM's own day-schedule already answers. This is why 012 is far less 011-coupled than 010. |
| **ASR + diarization vendor** | **not selected** | no | New subprocessor → new DPA + no-training clause + counsel. Veterinary lexicon (drug names, breeds, species-specific units) is the accuracy risk. |
| **iOS/Android in-browser long-form capture** | **untested** | no | **Highest technical risk.** Background/lock-screen audio capture in mobile Safari is the constraint that decides the capture surface (§ Capture Modalities). |
| VP-1 Postgres + RLS plane | in progress | no | Notes + audio + consent records cannot live in demo SQLite. |
| Counsel (recording consent, retention, vendor DPA) | queued | no | **Hard gate before the first real client is recorded.** |
| Vet-board / records-retention rules | pack scaffold only (`domains/vet/compliance/regulations.yaml`, confidence: low) | no | Retention periods are state-variable; the note becomes part of the legal medical record. |

### Data Volumes

No real numbers yet. Working estimate for scoping: a Synergy Vet GP DVM sees **~15–25 appointments/day**; a wellness appointment runs **~10–20 min** of in-room audio. One opted-in DVM ≈ **3–7 audio-hours/day**. At 3 pilot DVMs that is ~10–20 audio-hours/day — small enough that per-minute ASR pricing is not the constraint, large enough that an audio-retention decision has a real storage and discovery footprint. **Ground truth needed in pilot week 1**, alongside the existing after-hours call-log pull.

### Surprises

1. **"012 rides the 010 voice stack" is half true, and the false half is the expensive half.** 010 gives 012 its *governance* — disclosure-first adapter guarantees, append-only transcripts, consent records, no-training attestations, autonomy gating, cost telemetry, sim-mode discipline. It gives 012 **none of its media pipeline**: 8 kHz telephony speech-to-speech is the wrong shape for high-fidelity multi-speaker room capture. Planning 012 as "010 plus a prompt" would blow the estimate.
2. **Linked Evidence has nothing to link to.** `call_transcript.audio_ref` is a whole-file pointer; `call_turn` has wall-clock timestamps, not audio offsets; 009's `entity_ref`/`source_id` addresses whole records. **Nothing in the platform can currently express "this sentence came from that moment."** This is exactly the known-missing piece the tower flagged, and it is 012's #1 ask on the Pattern-① contract.
3. **A SOAP note already ships — with zero lineage.** `SoapNote` is a flat text blob with a signature, on demo SQLite, generated from procedure templates. It proves the sign-freeze semantics and nothing else. 012 either supersedes it on the platform plane or the product ends up with two note artifacts (open question Q7).
4. **Both fresh 009 defects land directly on 012.** KI-1 (re-ingest silently rewrites what a citation resolves to) is *worse* in a medical record than in a report: a note signed in September citing a record re-ingested in October would resolve to different content with no error and no warning — the audit trail retroactively lies about what the DVM saw when they signed. KI-2 (derived claims persist results without their input set) hits any note line summarizing a history rather than a single record.
5. **Working Rule 0 inverts here, and survives only because of pull.** W0 forbids pushing new software at staff. 012 is the first surface *aimed* at staff. It complies **only** because it is pure opt-in from the DVM's own phone, creates no login for anyone who doesn't want one, and — per D4 — the opt-in rate is not a side metric, it is the success condition. If 012 ever needs a rollout, a training session, or a dashboard, it has violated W0 and should be stopped.
6. **Spec-number drift.** The phase-4 brief seeded `011-vera-procurement` and `012-staff-scheduling`; the repo used 011 for relationship memory and 012 is now Vera Notes. **VP-5 staff scheduling and VP-7 procurement need fresh seed numbers** — flag to whoever owns the roadmap doc.
7. **The non-consumption alternative is not "status quo" — it is a $0–$99/month self-serve purchase, and one of the options is already inside ezyVet.** IDEXX's **AI-Assisted Notes is shipping free, in beta, to all US ezyVet customers** [V] — which includes Synergy Vet. Any DVM there can also buy Scribenote or CoVet for free, or HappyDoc for $149/clinic. That changes the wedge from *"we can do this"* to *"ours is the one you can catch"* (§ Competitive Context) and it is the biggest single change to this spec's risk profile.
8. **010's all-party-consent list does not transfer.** D9's CA/FL/IL/PA/WA list is a **telephone** list and is right for the phone channel; **in-person oral communication is governed differently** — Connecticut, Nevada, and Michigan are effectively one-party in person, while Delaware, Maryland, Massachusetts, Montana, New Hampshire, and Oregon join the strict list. Copying 010's list into 012 would be wrong in both directions (§ Consent).
9. **Speaker diarization is a biometric-law decision, not a free accuracy win.** Post-*Delgado v. Meta*, separating "DVM" from "client" by vocal characteristics — in a system where the recording is linked to a named client account — is a colorable **Illinois BIPA voiceprint** claim, with a private right of action and **$1,000–$5,000 per-violation** statutory damages [V]. And **the cloud ASR vendor is a non-party to the conversation**, which is the core theory in the April 2026 CIPA class actions [V] — meaning on-device processing shrinks exposure in a way no contract term does.

---

## JTBD

**Job statement**: *"When I finish an appointment, I want the record already written — in my words, checkable line by line — so that I leave when my last patient does, instead of charting until midnight and signing something I half-remember."*

- **Push**: VC-5 (verified) — owner-vets routinely chart after hours / until midnight and run 50–60-hour weeks. Documentation is the single most hated task in the profession, and (per Abridge's corpus) the one whose removal moves burnout in randomized trials.
- **Pull**: *Leave finished.* Not "save 8 minutes" — walk out the door done. The Abridge verbatims cluster on identity restoration ("this is why I went into pediatrics"), never on efficiency; the vet analogue to harvest is *"this is why I became a vet."*
- **Anxiety**: (a) an AI writing in a legal medical record I have to sign; (b) explaining to a client that I'm recording them; (c) getting blamed for a hallucination I didn't catch; (d) "is this how they replace me / how they audit me?"
- **Habit**: type during the visit (and lose eye contact), dictate to a tech, scribble on paper and rewrite after hours, or dictate into a general-purpose tool and clean it up.
- **Non-consumption alternative**: buy a vet scribe directly this afternoon — Scribenote and CoVet have permanent free tiers, VetRec is $99/DVM/mo, HappyDoc is $149/clinic unlimited — **or use the free one IDEXX is already rolling out inside ezyVet** [V]. There is no waiting involved; the alternative has already arrived.
- **Confidence**: **HIGH** on the job existing (VC-5 verified + the VIN adoption curve 3.5%→17.5% + the whole Abridge outcomes literature). **MEDIUM-LOW** on Vera being the one they hire for it *on documentation alone* — which is precisely why the citation layer is the spec, not a feature of it.

---

## Who It's For, and the Opt-In Path

### Personas (Synergy Vet, 23 clinics; hypothesis-level until staff discovery — see Q11)

| # | Persona | The felt problem | Why they opt in (or don't) |
|---|---|---|---|
| **P1** | **Associate GP DVM** (the primary user) — 15–25 appointments/day, salaried, charts after hours | Pajama time; notes written from memory hours later; the record is thinner than the visit | **Opts in fastest** if a colleague shows them the 30-second draft. Bounces if the first draft is wrong, if setup takes more than one text message, or if the client conversation is awkward |
| **P2** | **Owner-DVM / medical director** (Goldsmith-adjacent) — signs, buys, carries the liability | Record quality and completeness across 23 clinics; associate retention; missed charges | Buys on **defensibility + retention**, not minutes. Wants to know exactly how it can be wrong and who is on the hook. **This is the persona the citation model is for.** |
| **P3** | **Relief / locum DVM** — rotates clinics, no muscle memory for any PIMS | Charting in an unfamiliar system, often from a phone in a parking lot | Highest per-head value and the **best pilot cohort** (already phone-native, no habits to break) — but the worst **attribution** story (who signs, under which clinic's record) |
| **P4** | **Credentialed vet tech** — writes much of the record in practice | Doing the DVM's documentation without the authority to sign it | **Out of scope for 12a.** Techs are where the volume is, but they cannot sign, and the signature is the whole liability posture. Phase-2 with an explicit DVM-countersign flow |
| **P5** | **The client in the room** — not a user, but a **veto-holder** | "Why is that phone recording me?" | Must be able to decline in one sentence, with zero friction and zero social cost, and the visit proceeds exactly as before (§ Consent) |

### The opt-in path (this is the product, as much as the note is)

The invisible-adoption doctrine and the "opt-in from the DVM's own phone" NFR collapse into one design constraint: **the entire adoption path must fit inside channels the DVM already has, and produce nothing for anyone who doesn't opt in.**

1. **Seed** — one DVM (P3 or an eager P1), recruited by a colleague or by Goldsmith, not by a rollout. No announcement, no meeting.
2. **Enroll** — the DVM texts a number, or taps a link from a text. One screen: who you are, which clinic, and the consent script they'll read. **No login for anyone else. No account for the practice. No dashboard.**
3. **First capture** — one tap to start, one tap to stop. Nothing to configure per visit: no species picker, no appointment-type picker, no wake word (D3).
4. **The magic moment** — the draft lands **in the same thread** in under 60 seconds, with every sentence tappable to its source.
5. **Review and finish** — read, tap-check anything surprising, edit, mark done. The finished note goes wherever *they* already put notes: back to their phone/clipboard/email-to-self in 12a; into ezyVet in 12b, only after write verbs promote.
6. **Spread** — colleague sees the phone, asks. **Week-over-week opt-in rate is the instrumented success metric** (D4), reported per clinic. If it is flat, the product is wrong; if it climbs without a rollout, W0's success condition ("staff beg for it") is met literally.

**Kill criterion**: if a DVM needs a training session or a manual, 012 has failed its own thesis.

---

## Capture Modalities — honest tradeoffs

The NFR bar (zero hardware, zero wake words, opt-in from their own phone) narrows this hard, and the mobile-browser audio constraint decides it. **This must be bench-tested in week 1 before anything else is built.**

| Option | Zero install? | Fidelity | Zero-behavior-change? | Honest risk |
|---|---|---|---|---|
| **(a) Mobile web / PWA, phone in pocket or on the counter** | ✅ | Good (device mic, 16 kHz+) | ✅ | **The big unknown.** iOS Safari suspends media capture on screen lock / backgrounding. A recording that silently stops mid-consult is worse than no product. Needs an on-device bench test, per iOS version, before commitment |
| **(b) Native app via TestFlight** | ❌ (an install) | Good | ✅ once installed | Reliable background audio; but "install an app" brushes §III's *no separate destination app* and W0's *no new software*. Defensible as a pilot-only escape hatch, not as the shape of the product |
| **(c) Dial-in scribe (call a number, leave the line open)** | ✅ | **Poor — 8 kHz μ-law** | ❌ (dialing IS a wake word) | Tempting because the **entire 010 Twilio path already exists** and the disclosure guarantee is already enforced there. But telephony-grade audio on a multi-speaker room with a barking dog is Digitail's iPad complaint amplified, and it occupies the DVM's phone. **Reject as primary; keep as the zero-build fallback if (a) and (b) both fail** |
| **(d) Dictate-after (post-visit summary, DVM only)** | ✅ | Good | ❌ (it is a behavior, though a familiar one) | **Much easier problem**: one speaker, no client audio, consent question largely dissolves, accuracy far higher. Not the Abridge magic — but it is a real product that vets already pay for (Talkatoo's core motion), and it is the honest **degradation tier** when ambient fails or the client declines |
| **(e) Room hardware / always-on ambient** | — | Best | ✅ | **Declined** (board §III): Abridge proves software-only wins, and per-encounter opt-in is a much cleaner privacy posture than an always-listening room |

**Recommendation**: build the capture layer behind a **port** with (a) as the pilot adapter, (b) as the contingency, and **(d) shipped from day one as the always-available fallback** — it is also the graceful path when a client declines to be recorded. Decide (a) vs (b) on week-1 bench evidence, not on preference.

---

## Consent & the Recording Notice

> Fresh research, this discovery. Tags: **[V]** primary/multi-source · **[U]** single/secondary source · **[INTERP]** our read. **None of this is legal advice; counsel sign-off is a hard gate before the first real client is recorded**, exactly as it is for 010's FR-026/D9.

**Headline: the binding constraint is state wiretap/eavesdropping law, not health-privacy law — and the risk is not theoretical.** A class-action wave hit human-medicine ambient scribes in **April 2026** on exactly these theories.

### HIPAA does not apply — and four other regimes do

**HIPAA protects humans; animals are not "individuals" under the rule, and a vet practice is not a covered entity by virtue of practicing veterinary medicine** [V]. What governs instead: (1) **state practice acts / board rules** on record content and retention (CA 3 yrs, TX 5, NY 3, FL 3; OH no statute, AVMA recommends 5) [V]; (2) **state vet-record confidentiality statutes — 35 states have them** per AVMA [V]; (3) the **AVMA Principles of Veterinary Medical Ethics** ("information within veterinary medical records is confidential…") [V]; (4) **general consumer-privacy and biometric law**, because the client is a consumer and their **voice** is personal information.

> **Marketing trap to avoid:** vet scribe vendors sell "HIPAA compliant" as a trust badge (VetRec does exactly this [V]). It is a **category error** — HIPAA compliance is irrelevant to whether recording the client was lawful. We must not copy it; it answers a question nobody asked and none of the ones that matter.

### The correction that matters most: **in-person ≠ phone**

010's D9 all-party list (CA/FL/IL/PA/WA) is a **telephone-call** list and is correct *for the phone channel*. **Exam-room conversations are in-person oral communications, and several states treat the two categories oppositely.** Copy-pasting 010's list into 012 would be wrong in both directions.

**All-party consent/notice for IN-PERSON conversations — 11 states** [V]: **California** (Penal Code § 632), **Delaware** [U], **Florida** (§ 934.03 — *third-degree felony*, up to 5 yrs + $5,000, plus civil damages of $1,000 or $100/day under § 934.10) [V], **Illinois** (720 ILCS 5/14-2), **Maryland**, **Massachusetts**, **Montana** [U], **New Hampshire**, **Oregon**, **Pennsylvania** (18 Pa.C.S. § 5703), **Washington**.

**On the usual "two-party" lists but actually ONE-PARTY for in-person** — the DVM's own consent suffices: **Connecticut** (all-party rule is telephone-only) [V]; **Nevada** (inverse of the usual pattern — all-party for phone, one-party in person, with a judicial REP gloss) [U]; **Michigan** (participant exception, *Sullivan v. Gray* + Sixth Circuit; **the Michigan Supreme Court has never ruled** — the least stable "safe" state) [V].

**Two states where the bar is notice or non-secrecy, not affirmative consent** — materially easier: **Oregon** (ORS 165.540(1)(c) requires only that participants be "specifically informed"; Ninth Circuit upheld it Jan 2025) [V]; **Massachusetts** (§ 99 criminalizes only *secret* recording — *Curtatone v. Barstool Sports*, 2021: "affirmative consent is not necessary when all parties are aware of the recording") [V].

**The structural insight across CA, IL, and MA**: each hinges on an element that **clear, visible notice defeats** — California's "confidential communication" turns on an *objectively reasonable expectation* of non-recording (*Flanagan v. Flanagan*, 2002) [V]; Illinois's narrowed statute (post-*People v. Clark*, 2014) requires a **"private conversation"** recorded **surreptitiously** [V]. Openly disclosed recording is not surreptitious, and disclosure undercuts the expectation. **Notice quality, not just consent capture, is the defensive core.**

**Does a vet exam room carry a reasonable expectation of privacy? Assume yes.** Courts describe human medical exam rooms as private places with a reasonable expectation of informational privacy [V]; there is **no on-point veterinary holding** [U]. A vet exam room is weaker on the facts (no bodily exposure of the client, the patient is an animal, staff traffic in and out) — but no clinic should build a posture on winning that argument.

### The finding with the most architectural consequence: **the vendor is a third party**

The party exception protects **the DVM** from being an eavesdropper. It does **not** obviously protect a **cloud ASR vendor**, a non-party receiving the audio. **This is the core theory in the April 2026 CIPA class actions** [V, Alston & Bird]. Consequence: **on-device / edge processing with no third-party audio egress materially shrinks wiretap exposure; cloud processing does not, even in one-party states.** This is a real input to the ASR-vendor and capture-adapter decision, not a footnote — and it points at the DGX/ModelGarden local-inference asset as a strategically interesting option rather than merely a cost play (new Q13).

### Biometric law — Illinois BIPA is the largest quantified exposure, and **diarization is the trigger**

- **BIPA (740 ILCS 14)** covers "voiceprint," requires **written** notice + **written** release before capture, and has a **private right of action** with statutory damages of **$1,000 negligent / $5,000 reckless-or-intentional per violation**. The old defense — "speech-to-text creates no biometric template" — is eroding: in ***Delgado v. Meta Platforms*** the court held that **if a company can link a voice recording to a person's identity through other data, it can constitute a voiceprint**; courts increasingly look at *what is done with the audio* (recognition, verification, speaker analysis) rather than whether audio was merely captured [V].
- **Direct hazard for 012: speaker diarization.** Separating "DVM" from "client" is a speaker-recognition operation on vocal characteristics, in a system where the recording is inherently linked to a named client account. Under *Delgado*'s reasoning that is a **colorable voiceprint claim** — and per-scan statutory damages across a clinic group is what makes it dangerous, merits aside. **Diarization is a design decision with a price tag, not a free accuracy win.**
- **Texas CUBI** — same substantive rule (inform + consent before capturing a voiceprint for commercial purpose), up to $25,000/violation, but **AG-only enforcement, no private right of action** [V]. Lower operational priority.
- **Washington My Health My Data Act (RCW 19.373)** — two findings, and the second bites. (1) **Pet health data is not "consumer health data"** — the definition reaches the *consumer's* health status, not the animal's [V]. (2) **But "biometric data" is expressly included and the definition explicitly names "voice recordings, from which an identifier template can be extracted"** [V] — so MHMDA reaches 012 through the **client's own voice**, plus any incidental remark about the client's own health ("I can't lift him anymore, my back is shot"). And: **no revenue or volume threshold** (small clinics in scope), **the HIPAA exemption does not help a vet clinic** (vet data isn't PHI — the burden without the safe harbor), a **private right of action** via the WA CPA (actual damages, fees, treble up to $25,000), **no cure period, no scienter** [V]. Requires **separate, specific consent** — bundling into general intake consent is non-compliant [U].
- **CCPA/CPRA** — audio associable with an individual is personal information; biometric information used to identify a consumer is **sensitive** personal information; AB 1008 (eff. 2025-01-01) confirmed personal information includes data **embedded in AI models** — relevant to any vendor training on clinic audio [V]. Thresholds are revenue/volume-gated: a single clinic may fall outside, **a 23-clinic group plausibly does not**.

### What human medicine actually does — and the uncomfortable finding

- **Abridge's recommended script, in full**: *"I will be using a tool that records our conversation to help me write my clinical note, so I can pay more attention to our conversation and less time on the computer."* [V]. Medscape's critique is correct and pointed: it says nothing about where the audio goes, how long it is kept, which subprocessors touch it, or whether it trains a model [V].
- **The cleanest operational template in the corpus — UC Davis Health** (patient-facing page, verbatim) [V]: *"Abridge records your conversation with your clinician during the visit."* · *"If you do not want your clinician to use Abridge, just let them know. **Your care will not be affected.**"* · *"The recording will be started, stopped, and paused by your clinician."* · ***"All recordings are deleted after 30 days."*** — what it does, how to decline, no penalty, mid-visit pause, a stated deletion clock.
- **The uncomfortable finding [V, PMC12284739, NYU Langone]**: **brief disclosure → 81.6% consent; expanded disclosure (AI features, data storage, corporate involvement) → 55.3% consent.** The disclosure that is *more legally defensible* is the one that *loses a third of consents*. **[INTERP] This is the place where the business incentive and the ethical obligation point in opposite directions, and it must be named rather than optimized around.** The same study recommends **opt-in**, consent **separate from other technology consents**, disclosed **both before the visit and immediately prior to the encounter**, plus a **website** clients can read in advance.
- Kaiser reports **<0.5% patient refusal** with standardized notification [U, not traced to primary]. Counterpoint: Kaiser **mental-health** staff publicly raised that the consent process "does not include explanations about how the information is handled" [V, CalMatters].

### The litigation, and the contract term that should alarm a clinic group

- **April 7–8, 2026, N.D. Cal.** — putative class action against **Sutter Health**, **Memorial Health Services**, and **MemorialCare Medical Foundation** over Abridge deployment. Claims: **CIPA**, **CMIA**, **California UCL**, **Federal Wiretap Act**, intrusion upon seclusion [V]. A parallel action names **Sharp HealthCare** [V].
- Alleged defects, and they read as a design checklist: **no clear notice of AI recording; no notice of transmission outside the clinical setting or third-party processing; no system-wide uniform consent process; no reliable recording indicator; no deletion process.** Notice that *existed* but was "not specific, timely, and legally sufficient" [V].
- **The contract pattern:** Abridge's clinician terms make **users, not Abridge, "solely responsible" for obtaining patient consent** [V]; VetRec's privacy policy does the same ("ensure that everyone in the room during a recording consent to be recorded") [V]. **The liability sits entirely with the clinic; the vendor's compliance badges transfer nothing.** [INTERP] For 012 this is a **positioning choice, not a legal one**: every competitor disclaims consent onto the vet. Building the consent machinery — state-aware, per-encounter, logged — and *standing behind it* is a differentiator nobody has claimed, and it is the natural sibling of the won't-do list.
- **Rhode Island H 7538 (signed 2026-06-22)** — the **first state law aimed specifically at ambient AI scribes**: notify patients, permit **opt-out**, and **review AI-generated documentation for accuracy** after the visit [V]. It almost certainly does not reach veterinarians [U] — but **notice + opt-out + human-review is now the template a regulator or a plaintiff will cite as the standard of care.** 012's design already satisfies all three; say so.

### Veterinary-specific: a genuine guidance void

- **AVMA has no policy.** Its Task Force on Emerging Technologies and Innovation first met **late September 2025** to identify priorities [V]. An Iowa delegate explicitly asked the House for **guidance on client consent** [V]. Dr. Petra Harms, quoted by AVMA: *"When we put a surveillance tool into an exam room, we have to be sure that data isn't being used for something else."* [V]
- **No state veterinary board has issued AI-scribe-specific guidance** [U, across targeted searches]. What boards *do* enforce is record adequacy — "inadequate medical records" is reportedly the most common finding in board orders [U].
- **[INTERP] The asymmetry to internalize: the board risk is not "you recorded the client." It is "your record was wrong and you signed it."** The recording is merely the evidence. That is a direct argument for the citation model and for the no-unspoken-specifics rail, and it is the sharpest thing to say to persona P2.
- Vendor state of the art: **ezyVet hard-gates the record button on a consent checkbox** [V]; **ScribbleVet** generates consent posters and publishes a state-law table with suggested scripts [V]. **Every vendor recommends consent, none enforces it beyond a checkbox, all disclaim legal advice, and most are silent on retention.**

### The pet owner in the room — the evidence is thin and vendor-sourced

There is **no independent US consumer research, survey data, or documented client complaint corpus** on vet exam-room recording [V-absence]. Every "clients are fine with it" claim traces to a company selling the software (ScribbleVet: *"most clients are very receptive once they understand why"* [V as a quote, U as a claim]). AAHA publishes a client-facing "Benefits of Your Vet Using AI Scribing" page [U, 403'd] — its existence signals a professional body anticipating the question. A UK piece frames the duty as **awareness, not permission**, and reports no owner concerns [V as to content, GDPR-framed, not US-applicable].
**[INTERP] Plan for meaningfully more than 0.5% refusal once disclosure is genuinely informative** — the only two rigorous signals available (the NYU 81.6%→55.3% drop and the Kaiser mental-health pushback) both suggest acceptance is a function of how little people are told. **The client-decline rate is therefore a first-class pilot metric, not an edge case** — and the dictate-after tier is what makes a decline costless.

### Recommended posture for 012 (to be confirmed by counsel — this is a proposal, not a clearance)

**Design principle: one national posture at the level of the strictest state.** Per-state consent logic across 23 clinics will fail — staff move between sites and a single mis-flagged clinic is a felony exposure in Florida. Uniform compliance is cheaper than uniform litigation.

1. **Five-layer consent stack** — (i) a standing plain-language **web page** clients can read in advance (the NYU study found they want this); (ii) a **standalone intake checkbox**, physically separate from treatment consent and the privacy notice (bundling is precisely the pled defect in *Sutter/MemorialCare*), captured as a durable field; (iii) **exam-room signage** (this is what defeats the CA § 632 and IL "surreptitious" elements); (iv) **verbal notice at the start of every encounter** — the operative legal act, every visit, because consent must be timely; (v) a **visible recording indicator** while capture is active (its absence was pled as a defect).
2. **Suggested verbal script** (deliberately longer than Abridge's — and note that the NYU finding means this **will cost consents**, which is the correct trade):
   > *"Before we start — I use an AI assistant that records our conversation so it can draft the medical record for me. That means I can focus on [pet's name] instead of the computer. The recording goes to our documentation system, I review and approve every note, and the audio is deleted within [30] days. Is that okay with you?"*
   > *If declined:* *"No problem at all — I'll take notes the usual way. It won't affect [pet's name]'s care in any way."*
   > *If others are present:* address the notice to **everyone in the room**, not just the account holder — in all-party states they are parties too.
   It names AI explicitly (RI template), names external transmission (the *Sutter* defect), names human review (RI + AVMA ethics + board record-adequacy risk), names a deletion clock, and asks a **closed question producing a recordable yes/no**.
3. **Hard operational rules** — opt-in affirmatively **every visit**, never opt-out-by-signage; **log consent per encounter** (client, date, staff member, yes/no — an unlogged consent is an unprovable consent and the burden is on the clinic); **decline is frictionless and free** (drop to dictate-after; never condition care, scheduling, or price on consent; train staff never to re-ask after a "no"); **pause capability**, offered proactively when a client raises anything personal, financial, or about their own health; **never record by default**: euthanasia consultations, financial-hardship discussions, and client-complaint conversations (**this independently validates Q5 — make the exclusion structural**).
4. **Illinois: BIPA-grade formality or don't deploy ambient there.** Written notice + written release before capture; a published retention/destruction schedule; a **written vendor representation on whether diarization generates or stores any biometric template**. If unsatisfactory, the BIPA math can exceed the documentation savings across a group.
5. **Washington: treat client voice as regulated consumer health data** — separate, specific MHMDA consent, no bundling, no sale ever.
6. **Vendor terms must** bar training on clinic audio (or make it explicit opt-in — reuse 010's `vendor_no_training_attestation`), specify a retention ceiling, provide deletion + legal-hold controls, and supply a DPA.

### Audio retention — the sharpest decision, and the answer converges from two directions

**Recommendation: retain audio only through signature (target 7 days; 30 days maximum), then automatic hard delete, with a legal-hold override.**

- **The insurer's view is unambiguous** [V, ProAssurance, Jun 2025]: retained audio **"will undoubtedly be discoverable in litigation"**; the nightmare is **inconsistency between the note and the audio** — *"even a seemingly minor inconsistency could undermine the accuracy and reliability of the entire medical record… may also be used to suggest that the physician failed to review the AI-generated notes adequately. Negative optics of this nature can derail otherwise defensible cases."* And: **"there is scant justification for retaining these audio logs once the AI-assisted note has been accurately added to the electronic medical record."** Policy should state the audio/transcript **"is not part of the legal medical record… just transitory communications in draft form."**
- **Market benchmarks**: Abridge **30 days** then audio + transcripts auto-deleted [V]; ScribbleVet ~90 days cloud, transcripts longer [U]; VetRec unspecified ("as long as necessary") [V]; one vendor in the NYU study retained transcripts **a year** for algorithm improvement [V]. **ezyVet stores recordings inside the patient's clinical record** [V] — [INTERP] the worst posture available, and it is the incumbent's; a short-clock policy is a defensible thing to say out loud against it.
- **Deletion must be routine, automatic, and policy-driven** — deleting after notice of a claim is **spoliation**. Fixed clock + legal-hold override on any complaint, board inquiry, or preservation letter [V].
- **Name the retention mismatch in policy**: the record is kept 3–5 years by state law; the audio for days. These are different objects under different rules — say so, or someone later argues you destroyed part of the record.

**[INTERP] The design tension this creates, stated plainly:** Linked Evidence's **value is highest before signature** (it is a verification instrument) and its **liability is highest after signature** (it is discoverable impeachment material). The resolution is to treat citations as a **pre-signature verification instrument**: audio-backed replay lives inside the retention window, and when the window closes the citation must resolve to a **loud tombstone** — *"the source audio for this sentence was deleted on [date] per the practice's retention policy"* — never to silence and never to a dead link. **This is the same mechanism KI-1's fix direction demands (C-3/R5) and the same principle as C-5 ("absence must be loud"), arriving from an entirely independent direction.** That convergence is strong evidence the contract requirement is right.

**And it is unclaimed white space**: the competitive scan found **no vendor has staked out "audio retained only until the note is signed, then hard-deleted, with the alignment map preserved as proof of provenance."** Given the 2026 class actions and all-party criminal exposure, being the product with the **smallest legal surface that still offers verification** is both the safer posture and the better story. Proposed name for the pattern: **ephemeral verification**.

---

## Accuracy & Liability Posture

The category's errors are documented and unglamorous: a physician caught a **nitrofurantoin/nitroglycerin** substitution [V]; ambient scribes "fabricate plausible-sounding sentences that no one actually said" and "confuse speaker attribution" in multi-person conversations [V]; and even Abridge's own confabulation-detection claim (97% of unsupported claims caught vs GPT-4o's 82%) is self-reported and unreplicated [U]. **Design for errors occurring, and make them cheap to find.** That is the whole Linked Evidence thesis and it is why the citation model is the feature, not a trust badge.

**Posture for 012 (proposed, to be hardened in spec):**

1. **The DVM signs. Vera never signs.** Already published in `what-vera-will-never-do.md` — "If a note exists in your system with a doctor's name on it, that doctor put it there." Inherit spec 002's freeze-on-sign semantics; extend them so **signature freezes the citation set too**.
2. **No unspoken specifics.** *Vera Notes never emits a drug name, a dose, a numeric value, or a lab result that was not spoken in the encounter.* Anything heard-but-unclear becomes a visible `[unclear: …]` placeholder the DVM must resolve before signing — never a plausible guess. This is the vet transfer of Abridge's reported prohibition on generating medications/dosages [U], and it is the single highest-value safety rail because drug names, species-specific units, and mg/kg dosing are precisely where vet ASR will fail.
3. **S and O richly; A and P conservatively.** Subjective and Objective are transcription-shaped — quote the client, capture the exam findings as stated. Assessment and Plan are **clinical judgment**: draft only what the DVM verbalized, never inferred. This is what keeps 012 on the **Tier-1 side of the domain-pack line** — 012 *transcribes and structures what a licensed professional said*; it does not author clinical knowledge. The moment it adds a differential or a protocol the DVM didn't say, it is Tier-2 content and needs a named-DVM signature under `domains/vet/clinical/`.
4. **Absence is loud.** A sentence with no source must render as *having no source* — never as an empty or dead link (the KI-1/KI-2 lesson: the dangerous failure is the one that still resolves).
5. **Attribution is per-DVM, from the opt-in — never from a shared login.** Shared logins are a documented reality at these clinics (009 discovery, staff-discovery risk). A note attributed to the wrong DVM is a licensure problem, not a UX problem.
6. **Not a regulated device.** 012 stays on the documentation side of the line — no diagnosis, no CDS, no orders (Abridge precedent [INTERP]). The published won't-do list is the external expression of this and constrains behavior, not just copy.
7. **No autonomous write, ever, in 12a.** The draft goes to the DVM. Nothing reaches ezyVet until write verbs promote at the pilot-activation gate (009's non-goal stands).
8. **Publish "How Vera can be wrong, and how you'll catch her."** Abridge's most transferable trust move (lesson 8) and cheap: a one-page vet-facing companion to the won't-do list, shipped *with* 12a.

---

## The Citation Model — what 012 needs FROM the Pattern-① contract

**Framing (binding):** 012's citations are **the user-facing consumer of the one platform evidence contract**, not a parallel mechanism. `claim → source-ref → resolver`, source-ref **intrinsic at generation time**. The C6 compliance-audit rail and the Vera Notes citation are two consumers of the same contract, and if 012 ever needs its own evidence table, the design is wrong.

### What the vet actually does

Tap a sentence in the draft → the source passage highlights (with ~10s of audio replay, *if* audio is retained — see Q1) → confirm, or edit. **Target: under 2 seconds to check a sentence.** The value is not that the citation exists; it is that repeatedly failing to catch the AI converts skeptics (Abridge's mechanism, verbatim).

### Requirements 012 places on the contract (file these NOW, before v1 freezes)

| # | Requirement | Why 012 needs it | State today |
|---|---|---|---|
| **C-1** | **Span-granular locators.** A source-ref must address a *sub-record region*: `(transcript_id, char_start, char_end)` and `(audio_object, t_start_ms, t_end_ms)` | "This sentence came from that moment" is the entire feature | **Known-missing.** 009 addresses whole records; `call_transcript.audio_ref` is a whole-file pointer; `call_turn` has no audio offsets. **012's #1 ask** |
| **C-2** | **Reference *sets*** — one claim citing many sources cheaply | "Rex is overdue for his Lepto booster" cites a vaccine history, not one row | Accepted into the contract as **R2** (from KI-2). 012 depends on it landing |
| **C-3** | **Snapshot-versioned resolution** — a reference resolves to what existed at generation time, or to a **loud tombstone**; never silently to current state | A note signed in September citing a record re-ingested in October must not retroactively change what the DVM appears to have seen. In a legal medical record this is not a bug class, it is a **discovery liability** | Accepted as **R5** (from KI-1). **012 must not cite re-ingestible records until R5 lands** |
| **C-4** | **Heterogeneous source kinds under one contract** — audio span, transcript span, canonical PIMS record (009 `entity_ref`), and a prior signed note, all citable by one claim | A single note line legitimately mixes "what was said" with "what the chart says" | Resolver-kind plurality is implied by Ruling A; needs to be explicit |
| **C-5** | **Absence is a first-class value** — "no source" is representable and renders as such | The won't-do list already promises "never state a fact it cannot source"; the contract must let 012 *keep* that promise mechanically | Principle stated ("absence must be loud"); needs a representation |
| **C-6** | **Edit degradation** — when a human edits a cited sentence, the citation must degrade honestly (`human_edited`: span retained as *context*, not as *support*) | An edited sentence still carrying its original citation is a lie with a link on it | Not addressed anywhere. **012-specific ask** |
| **C-7** | **Signature freezes the citation set** immutably alongside the note | The signed note is the legal artifact; its evidence must be as frozen as its text | Spec 002 freezes note text only |
| **C-8** | **Retention-expiry tombstones** — when a source is deleted under a retention policy, its references must resolve to a **loud, dated tombstone** ("source audio deleted [date] per retention policy"), never to silence or a dead link | The recommended **ephemeral-verification** posture (§ Consent) deliberately deletes audio after signature. Citations must survive that deletion *honestly* | Not addressed. **Arrives independently at the same mechanism as C-3/R5 and C-5 — strong evidence the requirement is right** |

**Sequencing consequence:** 012 can begin on **audio/transcript-internal citations** (C-1) without waiting on 009's fixes, because those sources are 012's own and are immutable by construction. Citations **into the practice record** (prior visits, vaccine history, prior notes) are blocked on C-3/R5. That is a clean scope line for 12a and it is recommended below.

---

## Platform-Common From Day One: pattern layer vs vet layer

Per patterns-not-resources: **never a shared scribe service.** FarmAgent and MedWatchers vendor the *pattern* and run it on their own substrate, with their own DB and their own adapters.

**Pattern layer** (shape it here so it lifts cleanly; register back to COS-platform):
- **Opt-in capture session lifecycle** — enroll → consent record → capture → finalize → deliver → sign. Consent is a **port**, not a hardcoded script (see below — this is the sharpest reason).
- **Capture port** — long-form audio in, transcript + diarized turns out. Adapters: mobile-web, native, dial-in, dictate-after.
- **Draft artifact + citation set** — claims carrying intrinsic source-refs; the Pattern-① user-facing consumer, with C-1…C-7 above.
- **Review-and-sign loop** — professional signs, signature freezes text *and* evidence, no auto-write.
- **Delivery-through-existing-channels port** — SMS / email-to-self / clipboard, with a write-back **adapter slot** that stays empty until the vertical's write verbs promote.
- **The "never emit an unspoken specific" rail** — parameterized by the vertical's dangerous-specific classes (vet: drug/dose/lab value; ag: product/rate/REI; pharmacy: drug/dose/interaction).
- **The NFR bar + the metric set** — <60s, zero hardware, zero wake words; opt-in rate week-over-week, draft latency, edit distance, cost-per-draft.

**Vet-specific (stays here):**
- SOAP section grammar; veterinary lexicon (species, breeds, drug names, mg/kg conventions); appointment-type/species/speaker-role auto-detection.
- The **in-room client consent script** and the state-by-state recording posture.
- The ezyVet write-back adapter (12b only); vet-board records-retention and VCPR rules; DVM signature semantics; the vet won't-do list lines.

**Why consent must be a port, not a shared implementation:** the three verticals have genuinely different regimes. Vet: **no HIPAA**, state wiretap law with a client in the room. FarmAgent field notes: usually the agronomist alone or with the grower — a far lighter posture. MedWatchers pharmacist CMR: **HIPAA applies in full**, plus pharmacy-board rules. A shared consent *service* would be wrong in two of three verticals; a shared consent *shape* with per-vertical policy is right in all three.

---

## Shaping

### Solution Sketch (12a — the pilot cycle)

- **Phase A — bench the capture surface (week 1, before anything else).** On-device test of long-form mobile-web capture through screen-lock and backgrounding, on the actual iOS/Android versions Synergy Vet DVMs carry. **This decides the modality and it is allowed to kill the ambient scope.** Ship (d) dictate-after regardless — it is the fallback tier and the client-declines path.
- **Phase B — capture → transcript → draft, sim-first.** Capture port + ASR/diarization adapter behind a port (inherit 010's dual-mode `is_live()` discipline so the whole thing is buildable and testable with zero live vendor calls). Structured SOAP draft with **S/O rich, A/P conservative**, and the unspoken-specifics rail enforced deterministically — outside the model, in the adapter, exactly as 010 enforces disclosure.
- **Phase C — citations.** Every draft sentence carries an intrinsic source-ref into its own transcript/audio spans (C-1). Tap-to-check UI in the delivery surface. **No citations into the practice record until C-3/R5 lands.**
- **Phase D — consent as product, and the decline path.** Adopt **ezyVet's own enforced pattern and go past it**: capture cannot start until consent is affirmed (an adapter guarantee, exactly as 010 enforces the first-utterance disclosure — enforced in code, not asserted in copy). The script is surfaced to the DVM at capture start; the client's yes/no is **logged per encounter** (client, date, staff member, outcome) on the capture session, reusing 010's `consent_record` + `vendor_no_training_attestation` shape. A **visible recording indicator** runs for the duration (its absence was a pled defect in the 2026 class actions). **A one-tap decline drops instantly to dictate-after with no friction and no social cost**, and a **pause** is offered proactively when the conversation turns personal, financial, or to the client's own health. **Structural exclusion by appointment type** for euthanasia, financial-hardship, and complaint conversations. **Everything ships at the strictest-state bar nationally** — no per-clinic consent logic.
- **Phase E — review, sign, deliver through existing channels, then forget.** Draft back in the DVM's own thread <60s. Review/edit with honest citation degradation (C-6). "Done" freezes text + citations (C-7). Delivery: their phone / email-to-self / clipboard. **No PIMS write. No dashboard. No login for anyone else.** Then **ephemeral verification**: audio auto-deletes on a fixed clock (target 7 days, 30 max) with a **legal-hold override**, citations degrade to dated tombstones (C-8), and written policy states the signed note is the legal record while audio/transcripts are transitory draft material.
- **Phase F — instrument the feelings.** Per-DVM opt-in rate week-over-week (the D4 "beg for it" metric), draft latency p50/p95 against the <60s bar, edit distance per note, **client-decline rate (first-class, not an edge case)**, cost-per-draft from note #1 (reuse `telemetry.py` + `pricing.yml`), and a short fulfillment pulse. **Lead with "leave finished," never with hours-saved** (D4's counter-finding is load-bearing: after-hours time often doesn't drop).

### Rabbit Holes

- **Rebuilding the media pipeline inside 010's turn loop.** The realtime speech-to-speech stack is the wrong tool; forcing 012 through it to "reuse the voice stack" trades a 2-week ASR adapter for a 6-week fight with barge-in and session resumption that 012 does not need.
- **Inventing an evidence mechanism because the contract isn't ready.** Ruling A is explicit: ONE contract. If 012 ships its own citation table "temporarily," we get the parallel-mechanism failure the ruling exists to prevent. If the contract slips, 012 ships **sourceless drafts with the citation surface stubbed and visibly absent** — not a second mechanism.
- **Citing the practice record before KI-1 is fixed.** A medical-record citation that silently re-points is worse than no citation. Hold the line at own-transcript citations for 12a.
- **A/P cleverness.** Every attempt to make the Assessment smarter is a step toward Tier-2 clinical content and toward the confabulation the whole design is meant to catch.
- **Building for techs first because that's where the volume is.** They can't sign. The signature is the liability posture.
- **The euthanasia appointment.** Recording one is an ethical and human problem, not a feature-flag problem (Q5). Do not discover this in the field.
- **Chasing multilingual, charge capture, or discharge instructions in 12a.** All three are real and all three are next; the note has to be trusted first ("land documentation → expand to money").

### No-Gos (this cycle)

- **Any write into ezyVet or any PIMS.** 009's non-goal stands; 12b is gated on write-verb promotion at the pilot-activation gate.
- **Any login, dashboard, training session, or rollout for anyone who did not opt in** (Working Rule 0, binding).
- **Wake words, room hardware, always-on ambient, or a separate destination app** (D3 + board §III).
- **Emitting any drug name, dose, numeric value, or lab result not spoken in the encounter.**
- **Inferred Assessment/Plan content; any diagnosis, prognosis, or treatment recommendation** (won't-do list; Expert Firewall).
- **Vet-tech or CSR capture; multilingual; discharge-instruction generation; charge/code extraction** — all deliberately deferred.
- **A parallel evidence mechanism** (Ruling A).
- **Retaining audio past the signature window** without an explicit Matt + counsel decision, and **never** in the patient's clinical record (ezyVet's own posture — the one thing not to copy).
- **Per-clinic or per-state consent logic** — one national posture at the strictest bar; and **no ambient capture in Illinois** until the BIPA/diarization question is answered in writing.
- **Claiming "HIPAA compliant"** as a trust signal (category error; every competitor does it).
- **Recording euthanasia, financial-hardship, or client-complaint conversations** by default.
- **Marketing hours-saved** (D4 counter-finding), or marketing the ezyVet integration publicly (Working Rule 2).

### Cycle 12a — In / Out (the explicit scope line)

**IN**
- DVM opt-in and enrollment entirely through existing channels; no login, account, or dashboard for anyone else.
- **One** capture adapter (decided by the week-1 bench) **plus dictate-after** as the always-available fallback and decline path.
- ASR + speaker separation → structured SOAP draft, **<60s** after the encounter ends, **S/O rich, A/P conservative**.
- The **no-unspoken-specifics rail** with visible `[unclear: …]` placeholders, enforced deterministically outside the model.
- **Span-cited sentences into 012's own transcript/audio** (C-1), tap-to-check in the delivery surface.
- The **five-layer consent stack** with capture hard-gated on consent, a per-encounter consent log, a visible recording indicator, one-tap decline, proactive pause, and structural appointment-type exclusions.
- **Ephemeral verification**: fixed-clock audio deletion with legal hold; citations degrade to dated tombstones (C-8).
- Review → edit (with honest citation degradation, C-6) → sign (freezing text *and* citations, C-7) → deliver via phone/email-to-self/clipboard.
- Vendor **no-training attestation** + DPA; cost-per-draft telemetry from note #1; the opt-in-rate / latency / edit-distance / decline-rate metric set.
- A vet-facing **"How Vera can be wrong, and how you'll catch her"** page shipped with the cycle.

**OUT**
- Any PIMS write-back (that is **12b**, gated on write-verb promotion); any staff dashboard or rollout.
- Citations **into the practice record** (blocked on C-3/R5 — KI-1); any carry-forward of prior-visit content.
- Inferred Assessment/Plan; any drug name, dose, numeric value, or lab result not spoken.
- Vet-tech and CSR capture; multilingual; discharge instructions; charge/code extraction; clinical decision support.
- Ambient capture in **Illinois** pending the BIPA/diarization answer; per-state consent branching.
- Audio retention beyond the decided window, and audio in the clinical record.
- A second evidence mechanism of any kind.

### Appetite Assessment

**Medium.** 12a is roughly the size of 010's cycle 3a, with a different risk shape: less protocol/safety surface (no live caller, no triage, no emergency SLO), but a genuinely new media pipeline and a hard external dependency on a contract that is being designed right now. The week-1 capture bench is the cheap gate that decides whether the ambient scope survives; the dictate-after tier means **there is a shippable product even if ambient capture fails**, which is what makes the appetite defensible.

---

## Registry + Constitution

### COS-Platform Registry
- **Consumes**: the **Pattern-① evidence contract + port** (Vera-core, on the critical path — 012 is its first user-facing consumer); 009's `entity_ref`/`source_id` lineage as the non-audio resolve target; 010's adapter-guarantee / append-only-transcript / consent-record / cost-telemetry / dual-mode-sim patterns; 011's household-patient attachment (soft); the autonomy-gate and professional-signs primitives.
- **Registers back**: **`ambient-professional-scribe`** as a pattern candidate — *opt-in capture from the professional's own device → transcript → cited draft → professional signs → delivered through existing channels, with a write-back adapter slot that stays empty until write verbs promote.* Per the fleet brief this is the C8-scheduling precedent repeating: **vet proves it, FarmAgent and MedWatchers adapt on their own substrate.** Also registers the **C-1…C-7 citation-consumer requirements** back onto the Pattern-① contract.

### Constitution Check
- **KNOW/ADVISE/DECIDE**: 012 is pure KNOW→ADVISE. The draft is a proposal; the DVM DECIDEs and signs. No verb runs autonomously; nothing is written to a system of record without a human action.
- **Expert Firewall / licensed-act line**: 012 transcribes and structures what a licensed professional said. It authors no clinical knowledge, names no drug not spoken, and infers no assessment — keeping it Tier-1 under `domains/vet/`. Any drift into inferred clinical content requires a named-DVM signature under the Tier-2 gate.
- **Claim discipline extended to runtime**: every draft sentence is either sourced or visibly unsourced. This is the strongest form of the runtime claim-discipline rule the product has attempted, and it is the reason the citation model is the spec's spine rather than a feature.
- **Invisible adoption (W0)**: satisfied only by pull. No login, no dashboard, no training for anyone who did not opt in; the opt-in rate is the success condition, not a vanity metric.
- **Products share patterns, not resources**: shaped as a vendorable pattern with a per-vertical consent port; never a shared scribe service.

---

## Competitive Context

> Fresh field research, this discovery (~25 searches/fetches; Reddit blocked to the agent, so practitioner sentiment is secondhand via VIN News). Many vet "comparison" sites are vendor-operated content marketing — their exclusive claims are tagged [U].

### The market, in three numbers

- **VIN member polls (the only credible longitudinal series):** **3.5%** of members using AI scribing (Jul 2024, n=2,401) → **17.5%** (Sep 2025, n=2,387) — **5× in 14 months** [V, news.vin.com/doc/?id=12903793]. One industry estimate puts it near 20% now [U].
- **~44–50+ scribe products** have entered in 3–4 years [V/U]; the price band is **$0–$200/DVM/mo** with permanent free tiers (Scribenote, CoVet support tier) and flat unlimited-user clinic pricing (HappyDoc $119–149/clinic/mo; Otto $169) [V].
- **US ceiling at current pricing: ~$160M/yr** (133k DVMs × ~$100/mo) [INTERP]. That is a small pie for 50 vendors, which is why the price floor is $0.

**Read**: roughly a quarter penetrated and still in the steep part of the curve — early enough to enter, **far too late for "we do SOAP notes" to be a wedge**.

### The fact that must shape this spec: **IDEXX already ships a free native scribe inside ezyVet**

- **"AI-Assisted Notes"** — ambient recording → auto-drafted SOAP, listed under ezyVet **Pilot Features**; docs last updated 2026-02-18; **"release is in progress for all United States customers."** [V, docs.ezyvet.com + ezyvet.com/ai-assisted-notes]
- **Free during beta**, with 30 days' notice before any pricing change [V].
- Recording starts **inside the clinical record** (web); pause/resume; multiple team members contribute and each approves their own section [V].
- **Consent is hard-gated**: ezyVet "will not allow you to start recording until the consent option is selected" — but ezyVet does *not* notify the client; the practitioner must [V].
- Audio is **stored in the patient's clinical record**, user-deletable irreversibly [V].
- IDEXX admits it "may occasionally mislabel, omit, or misinterpret details," is **English-only**, is optimized for a standard SOAP layout, and that the clinician is "fully responsible" for record accuracy [V].
- **No evidence linking. No published latency. Cornerstone and Neo have no native scribe at all** [V/V-absence].
- *(Separately: **Vello is not a scribe** — it is IDEXX's pet-owner engagement/SMS product [V]. Do not model it as a scribe competitor; the phase-4 brief's assumption that ezyVet's native AI would be "scribe/engagement features, not an operating layer" is now half-obsolete: the scribe half shipped.)*

**Consequence for 012 (the single most important competitive fact):** Synergy Vet runs **ezyVet Enterprise**. Their DVMs are inside the rollout population for a **free, in-workflow, consent-gated native scribe**. A pilot DVM's honest question is not "should I try a scribe?" but **"why this one instead of the free one already in the record I'm typing into?"** 012 has exactly two answers, and they must both be true: **(1) you can check every sentence** (IDEXX cannot — no evidence linking), and **(2) it works from your phone in the room without leaving the chart open** (IDEXX's capture is web-in-record). Anything else is a losing argument against free-and-already-there.

### Best-in-class patterns (what to steal)

- **Abridge "Linked Evidence"** — highlight a generated line → source transcript span → **replay the original audio** [V, support.abridge.com]. The reference implementation for C-1.
- **DeepScribe "Clinical Moments"** — the same idea framed explicitly for **medico-legal review** [U]. That framing is the better one for veterinary (see below).
- **ezyVet's consent gate** — the record button is disabled until consent is affirmed [V]. Simple, enforced-not-promised, and exactly the shape of 010's adapter-guarantee pattern. **Adopt it directly.**
- **ScribbleVet's consent-poster generator + published all-party-consent state guide** [V] — consent treated as product surface, not paperwork.
- **HappyDoc's flat per-clinic unlimited-user pricing** [V] — the pricing shape that undercuts per-seat scribes and matches Vera's bundled posture (relevant to Q10).
- **VetRec's enterprise checklist** — SOC 2 Type II, HIPAA, GDPR, TX-RAMP L1, SSO, RBAC, custom retention, deploy-in-your-cloud, 99.99% SLA [V]. This is the procurement price of admission for the operator-network ambitions.

### Category gap — **the differentiator hypothesis holds**

**Nobody in veterinary maps a generated note sentence back to its source span and audio moment.** [V-absence, checked across 25+ sources including every major vendor site and three buyer's guides.]

| Capability | Who has it | Gap vs Abridge |
|---|---|---|
| Full transcript viewable | ScribbleVet, Otto, VetSkribe, most | — |
| **Transcript ↔ audio sync** (click transcript → audio jumps) | **ScribbleVet** (shipped 2024-12-30) [V]; **Otto** (playback from appointment view) [U] | Starts from the *transcript*, not the *note*. The vet must still hunt for the moment |
| **Note sentence → source span → audio** | **Nobody** [V-absence] | **The white space** |
| Literature citations (a different thing) | VetGeni (Wiley-licensed refs), ScribbleVet (Plumb's roadmap, LifeLearn cited differentials) | Cites *external literature*, not *the encounter*. Vendors will conflate these; we must not |

Corroborating: the category's own buyer's guides admit **"there is no independent, published accuracy benchmark for veterinary AI scribes, and any single percentage a vendor quotes is their own measurement on their own terms"** [V, vetsoftwarehub]. That is the market conceding that trust is currently unverifiable — precisely the hole Linked Evidence fills.

### What vets actually complain about (design input, not color)

From VIN News — the best-sourced sentiment in the category [V]: **drug names misspelled or fabricated**; **hallucinated details**; **veterinary terms misinterpreted**; **multi-pet appointments scrambling information / cross-patient data contamination**; **barking dogs breaking recognition**; **heavy accents degrading output**. Dr. Chiara Switzer, on the record: *"I won't use it… This technology is not good enough for these critical documents."* And the meta-complaint: as accuracy improves, vets **stop proofreading** — while the **AAVSB position is that responsibility for appropriate use of AI rests entirely with the licensee** [V].

Three of these map straight onto decisions already made above: the **no-unspoken-specifics rail** (§ Accuracy) is a direct answer to fabricated drug names; **speaker/patient attribution with citations as the proof mechanism** attacks multi-pet contamination and is marketed by *no* vendor [V-absence]; and Switzer's refusal is **a verifiability objection, not an accuracy objection** — which means the ~75–80% of the market not using a scribe contains a cohort the incumbents have stopped selling to and that only a catchable product can convert.

### Enterprise: the Abridge/Epic analogue is already underway

**VetRec** has the strongest public logo wall — **VCA Animal Hospitals, Ethos (140+ hospitals), Veterinary Emergency Group, Bond Vet, IndeVets** [V]. **Scribenote** claims the largest single rollout (an unnamed 300+ clinic group; 250 clinics live by day 180; 1.6M notes / 186k hours over 12 months) [V, vendor]. **Thrive (~400 clinics) owns Vetspire** and ships its own free scribe — vertically integrated and effectively closed [V]. **Mars (~2,500 hospitals)** and **Mission Pet Health (840+ locations)** have no public scribe deal [V-absence] — and both skew toward **Cornerstone/AVImark**, which IDEXX's native scribe does not cover. Relevant to Goldsmith's operator-network ambitions: the enterprise tier is being claimed *now*, and the entry ticket is a governance checklist, not a better draft.

### Consolidation vs commoditization — both, on different layers

Commoditized: **SOAP-note generation itself** (50 vendors, $0 floor, cost and quality explicitly uncorrelated [V]). Consolidating: **the platform layer** — Instinct Science **acquired ScribbleVet** (Jan 2026) [V]; IDEXX bundles AI-Assisted Notes free; Thrive→Vetspire and Covetrus Pulse include it at no extra cost; Nordhealth/Provet repositioned the entire PIMS as "built for AI agents" with an agent that captures **charges** spoken in consult [V]; Digitail raised a **$23M Series B** [V]. **Every PIMS is making the scribe free to defend the PIMS.** HappyDoc now markets *independence from acquisition* as a feature [U] — acquisition anxiety is a live objection in vet sales cycles.

**Strategic read for 012**: do not enter as a scribe. Enter as **the note you can check**, attached to an operating layer that already knows the practice. The Provet "captures charges spoken in consult" move also confirms the fleet brief's spine — documentation → money → judgment — and confirms it is a race.

---

## ICE Score

| Dimension | Score | Rationale |
|---|---|---|
| **Impact** | **8/10** | *(Marked down from 9 by the competitive scan.)* The strongest staff-pull wedge available — the most-loved feature in vet software [V] meeting the most-proven burnout intervention in clinical AI [V] — and the platform's first user-facing proof that Linked Evidence is a product surface rather than audit plumbing. But the commodity half of the value is **already free inside ezyVet** for exactly our pilot population, so 012's marginal impact rests entirely on the verification layer and the phone-native capture, not on "we have a scribe." |
| **Confidence** | **6/10** | Category proof is very strong and the **differentiator hypothesis survived the scan** (note-to-source linking is genuinely unclaimed in veterinary, [V-absence across 25+ sources]). *Our* execution risk is concentrated in four unvalidated places: mobile capture reliability, vet-lexicon ASR accuracy in a noisy exam room, a citation contract that does not exist yet, and a consent posture that is now well-mapped but unratified. |
| **Ease** | **5/10** | New media pipeline (no ASR/diarization in the repo), new vendor + DPA, an untested capture surface, a hard dependency on a contract being designed in parallel, and a consent stack that is a real build (five layers, enforced-not-asserted). The dictate-after fallback and the sim-first discipline are what keep this from a 4. |

**Low-confidence flags**: *Ease (5)* — validated or killed by the **week-1 capture bench**. *Confidence (6)* — validated by a **vet-lexicon ASR accuracy spike** on realistically noisy exam-room audio (barking, multi-speaker, drug names) before the draft generator is built, and by **counsel's read** on Synergy Vet's actual state footprint. *Impact (8)* — the honest test is whether a Synergy Vet DVM who has already been offered the free native ezyVet scribe still wants this one (Q11).

---

## Proceed Signal

**GO — with scope, and with three gates.**

**Scope of the GO**: **cycle 12a only** — opt-in capture from the DVM's own phone → cited SOAP draft in <60s → review and sign → delivered through existing channels. **12b (ezyVet write-back) is explicitly not in this GO** and is gated on write-verb promotion at the pilot-activation gate.

**The GO rests on one sentence, and it should be stress-tested before build**: *IDEXX gives Synergy Vet's DVMs a free ambient scribe inside the record they already use, so 012 is only worth building if it is **the note you can check** — and note-to-source verification is, verifiably, unclaimed in veterinary [V-absence across 25+ sources].* If that verification layer is descoped for schedule, **012 should be cancelled rather than shipped**, because what remains is a paid copy of something free.

**Gates (in order, before build commitment):**
1. **Week-1 capture bench** — long-form mobile-web capture through screen-lock/backgrounding on the DVMs' actual devices. If it fails and native-app is rejected, 12a **narrows to dictate-after**, which is still a real product and still proves the citation model.
2. **Counsel on the consent posture** — Synergy Vet's state footprint (**especially Illinois and Washington**, Q2), the notice script, the decline path, the **diarization/BIPA question**, and the **audio-retention decision** (Q1, which now has a recommended answer rather than an open one). This gates the first real recording, exactly as 010's D9 gates the first live call.
3. **Pattern-① contract alignment** — file C-1…C-8 with Vera-core *now*, while the contract is being designed. Span-granular locators (C-1) landing in v1 rather than v2 is the difference between 012 shipping Linked Evidence and 012 shipping a promise.

**Sequencing recommendation**: run the capture bench and the ASR-accuracy spike **in parallel with the Synergy Vet pilot kickoff (~Aug 3)**, and recruit **one relief/locum DVM (P3) plus one eager associate (P1)** as the seed cohort — two people, no announcement. Do **not** sequence 012 behind 010 going live; the two share governance, not a media path.

**Carried risks**: **IDEXX's free native scribe is already rolling out to the pilot population** and can bundle a verification feature at any time — assume ~12–24 months before evidence-linking is copied, and treat the durable moat as the operating layer underneath, not the feature; exam-room acoustics and vet lexicon are unmeasured (drug names, multi-pet cross-contamination, and barking dogs are the three named failure modes in the field evidence, and **no vendor markets against any of them**); the client-in-the-room consent moment has **no independent research behind it** — every "clients are fine with it" claim in the market is vendor-sourced, and the one rigorous data point (81.6% → 55.3% consent as disclosure improves) says honest disclosure costs consents; Illinois BIPA can make ambient capture uneconomic in that state; and both 009 defects must be fixed before any note cites the practice record.

---

## Open Questions (marked for `/clarify`)

| # | Question | Why it blocks | Shape of an answer |
|---|---|---|---|
| **Q1** | **Audio retention** — confirm the **ephemeral-verification** posture: retain through signature (target **7 days**, 30 max), then automatic hard delete with legal hold, citations degrading to dated tombstones? | Decides whether C-1 audio spans are meaningful, and sets the discoverable-evidence surface in a malpractice-exposed profession | **Research now recommends a specific answer** (insurer guidance + unclaimed market position converge). Needs Matt's call + counsel's blessing, not more research |
| **Q2** | **Which states does Synergy Vet operate in — and is Illinois or Washington among them?** | Illinois **BIPA** (diarization = colorable voiceprint claim, private right of action, $1–5k/violation) and Washington **MHMDA** (client voice = regulated consumer health data, no threshold, private right of action) are the two footprints that can make 012 uneconomic in those states | A state list from Goldsmith at kickoff. Default to the strictest posture nationally; be prepared to **exclude ambient capture in Illinois** |
| **Q3** | **Capture surface** — mobile web (PWA), native via TestFlight, or dictate-after only? | Decides the build and whether "ambient" survives contact with iOS | Week-1 bench evidence, not preference |
| **Q4** | **Is the client's consent/decline recorded in the medical record?** | Recording it is defensible; not recording it is privacy-minimal. Both are arguable | A per-encounter consent flag on the capture session, with counsel's read on whether it belongs in the chart |
| **Q5** | **Euthanasia and difficult-conversation appointments** — hard exclusion by appointment type, or DVM discretion? | An ethical failure here is unrecoverable with this pilot partner | **Independently validated by the legal research** (never record euthanasia, financial-hardship, or complaint conversations by default). Recommend **structural exclusion in 12a** — confirm the appointment-type list with a DVM |
| **Q6** | **Personal phone or practice-issued number?** | Personal is invisible-adoption-pure but puts practice data on a personal device; practice-issued is cleaner but is "new software" | Matt + Goldsmith; likely personal for the pilot with a documented data-handling posture |
| **Q7** | **Does 012 supersede the demo-track `SoapDraftAgent` (spec 002) or run beside it?** | Two note artifacts with different lineage guarantees is a trap | Recommend **supersede on the platform plane**; demo track keeps its own copy until the demo retires |
| **Q8** | **Attribution when a tech does the exam and the DVM never speaks** | A note attributed to the wrong professional is a licensure problem | Either exclude tech-led encounters from 12a, or require an explicit DVM countersign flow (P4, phase 2) |
| **Q9** | **Does the draft carry forward any prior-visit content in v1?** | The moment it does, KI-1 exposure is live and C-3/R5 becomes a hard blocker | Recommend **no** for 12a — own-transcript citations only |
| **Q10** | **Packaging** — inside the Vera subscription, or a per-DVM line? | Competitors are self-serve per-DVM; the WTP anchor and the sales motion differ sharply | Matt; note that bundling is also the anti-commoditization move |
| **Q11** | **Staff-discovery input** — none of the personas above have been validated with an actual Synergy Vet DVM | The whole adoption path is a hypothesis until one DVM reacts to it | Fold two DVM conversations into pilot week-1 ground truth, alongside the after-hours call-log pull. **Ask directly whether they have already been offered ezyVet's free AI-Assisted Notes, and what they made of it** |
| **Q12** | **Do we build the consent machinery and stand behind it, or disclaim it onto the practice like every competitor does?** | Abridge and VetRec both contractually push consent liability entirely to the clinic [V]. Standing behind it is unclaimed differentiation and the natural sibling of the won't-do list — but it is a real liability posture, not a marketing line | Matt + counsel. **This is a strategy question disguised as a legal one** |
| **Q13** | **Cloud ASR or on-device/edge inference?** | The cloud vendor is a **non-party** to the conversation — the core theory in the 2026 CIPA class actions. On-device processing shrinks wiretap, BIPA, and retention exposure simultaneously in a way no contract term can. It also makes ModelGarden's DGX assets strategically relevant rather than merely a cost play | Matt. Note Working Rule 4 ("production is cloud; DGX is a development/evaluation resource") — this may be the first case that argues for revisiting it |
| **Q14** | **Does 012 keep a transcript after the audio is deleted, or delete both?** | The insurer's guidance treats audio *and* transcripts as transitory draft material; Abridge deletes both at 30 days; ScribbleVet keeps transcripts longer. Keeping the transcript preserves cheaper citations but retains most of the discovery surface | Counsel. Affects whether C-8 tombstones fire once or twice |

---

## Marketing Output

### Positioning Message Seed
**"Leave finished."** — *Your notes are written before you leave the room, in your words, and you can check every sentence against what was actually said. You sign. Vera never does.*
(Per D4: never lead with hours-saved. The counter-evidence is explicit that after-hours time often doesn't drop — what changes is how the work feels. The quote to harvest from the pilot is the vet analogue of Abridge's testimonials: *"this is why I became a vet."*)

### Why-Now Angle
AI scribing in veterinary went from **3.5% to 17.5% of VIN members in 14 months** [V] and the draft itself is now free in half the PIMS on the market. What has *not* arrived is any way to check it — the category's own buyer's guides concede that **"there is no independent, published accuracy benchmark for veterinary AI scribes, and any single percentage a vendor quotes is their own measurement on their own terms"** [V]. Every vet scribe asks you to trust the draft. **Vera Notes hands you the receipts** — every sentence one tap from the moment it was said — and the signature stays where it has always been.
*[Claim-check: needs two `verified-claims.md` entries. **"First veterinary scribe with note-to-source linked evidence"** — supportable as a **[V-absence]** finding across 25+ sources (no vet vendor maps generated note text to its source span; ScribbleVet's transcript↔audio sync is the closest and runs the other direction), but it is a negative claim about competitors and should be filed as **PENDING** with the scan cited and a re-check cadence. **"Audio deleted on signature"** is a **PRODUCT-CLAIM** — true only once the retention machinery ships.]*

### Differentiation Source
Not the note — the **catchability**, sold as **defensibility rather than convenience**. The AAVSB position is that responsibility for AI use rests entirely with the licensee; VIN's general counsel notes it is unclear whether recordings are even part of the legal medical record and warns they are discoverable; and the sharpest recorded objection in the category — *"I won't use it… This technology is not good enough for these critical documents"* [V] — is a **verifiability** objection, not an accuracy one. A vet who can prove in three seconds that a dose came from an actual spoken sentence has a defense no competitor's product can produce. That aims 012 at the ~80% of the profession that has *refused* scribes on trust grounds — a cohort the incumbents have stopped selling to.
Second source of difference: **the smallest legal surface that still offers verification.** Nobody has claimed *"audio kept only until you sign, then hard-deleted, with the provenance map preserved"* — while the incumbent stores recordings **in the patient's clinical record**. Third: Vera Notes is the only scribe attached to an operating layer that already knows the practice. The note is the wedge; documentation → missed-charge capture → clinical reminders is the climb.
