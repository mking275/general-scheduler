# Feature Specification: Vera Notes — The Note You Can Check

**Feature Branch**: `012-vera-notes`

**Created**: 2026-07-28

**Status**: Draft

**Input**: User description: "Cycle 12a. A DVM opts in from their own phone — no login, no rollout, no new software for anyone who didn't ask. They read a consent line, tap record, and finish the appointment. Under 60 seconds after the visit ends, a SOAP draft lands back in the thread they already use, with every sentence one tap from the exact moment it was said. They read it, check what surprises them, edit, and sign. Vera never signs. The audio expires on a short clock and the citations turn into dated tombstones rather than dead links. Nothing is written into the PIMS."

---

## Problem Statement

Documentation is the most hated task in the profession and the one whose removal moves burnout in randomized trials. Owner-vets chart until midnight; associates write notes from memory hours after the visit; the record ends up thinner than the appointment was.

That problem is already being solved — badly, and for free. Roughly 44–50+ veterinary scribe products entered the market in three years, VIN-member adoption went 3.5% → 17.5% in fourteen months, the price floor is **$0**, and **IDEXX now ships a free ambient scribe ("AI-Assisted Notes") inside ezyVet to all US customers — which includes Synergy Vet, our pilot group.** "We have a scribe" is not a wedge. It is table stakes that someone else is already giving away inside the record our pilot DVMs are typing into.

What no vendor in veterinary ships is **verification**. Nobody maps a generated note sentence back to its source span and the audio moment it came from ([V-absence] across 25+ sources). The category's own buyer's guides concede there is no independent accuracy benchmark for any veterinary scribe and that every quoted percentage is a vendor measuring itself. The sharpest recorded objection in the field — *"I won't use it… This technology is not good enough for these critical documents"* — is a **verifiability** objection, not an accuracy one. And the board risk that actually bites a DVM is not "you recorded the client," it is **"your record was wrong and you signed it."**

So 12a is not a scribe. It is **the note you can check**: the platform's first user-facing consumer of the one evidence contract (Pattern ①), where every sentence is either sourced to a span of what was actually said, or is visibly marked as having no source. The signature stays exactly where it has always been.

### Standing Condition (binding, whole-spec)

**If the citation/verification layer is descoped for schedule, cancel 012 — do not ship it.** A scribe without citations is a paid copy of something the pilot customer already has for free. Verification *is* the product; everything else in this spec is the delivery vehicle for it.

---

## Clarifications

### Session 2026-07-28

**Matt-directed and confirmed, 2026-07-28 (board mirror `a3f3ae3`). These three are binding constraints on this spec's content and are not re-opened here.**

- Q: Audio retention posture? → A (Matt-directed and confirmed, 2026-07-28, R-1): **Ephemeral verification, adopted.** Retain through signature, then hard-delete. **7-day default, 30-day ceiling, legal-hold override.** A practice may *shorten* freely; *lengthening* requires an explicit recorded acknowledgment of discovery risk — a deliberate bet, never an accidental default. Citations degrade to loud, dated tombstones (C-8). Retention is a **customer-visible term**, not an internal default. *Rationale: the value curve and the liability curve cross at signature — before it the audio is a verification instrument, after it the signed note is the legal record and the audio's remaining use is impeaching it in discovery.*
- Q: State/jurisdiction exposure and speaker diarization? → A (Matt-directed and confirmed, 2026-07-28, R-2): **No pre-emptive state carve-outs; state is a per-practice property from day one; NO speaker diarization in cycle one.** Geography is a week-1 discovery question, but the up-market ICP (100–400-practice groups) certainly spans IL/WA, so `state` is modeled from the start. Diarization is dropped from 12a: it is the entire Illinois BIPA voiceprint exposure (private right of action, $1–5k per violation across a clinic group) and a SOAP note needs *what was said* far more than perfect speaker labels. Accepted cost: rougher multi-speaker transcripts.
- Q: Do we build the consent machinery, or disclaim it onto the practice like every competitor does? → A (Matt-directed and confirmed, 2026-07-28, R-3): **Stand behind the mechanism, scoped.** We build and warrant the machinery — per-state rules, the disclosure script, the recorded consent artifact, per-practice configuration, and **visible gaps when it is not followed**. We do **not** warrant the practice's operational behavior. The system makes skipping the script hard and *visible*, which is what a practice needs to defend itself. *Rationale: disclaiming consent onto the customer contradicts the posture the product is built on, it is genuinely unclaimed (Abridge and VetRec both push it entirely to the clinic), and multi-state compliance burden is what a PE-owned operator's operating partners actually worry about. The scope limit exists because unlimited liability for another party's operational behavior is uninsurable.*

**Resolved this session (evidence, shipped code, or an existing spec answers it):**

- Q: Capture surface — mobile web (PWA), native via TestFlight, or dictate-after only? (Q3) → A: **Product answer settled; adapter selection is a bench gate, not an open product question.** Capture is a **port** (long-form audio in, timestamped transcript out) with three adapter kinds; **dictate-after ships in 12a unconditionally** as the always-available tier and the client-decline path. Which ambient adapter is the pilot adapter is decided by week-1 on-device bench evidence on the DVMs' actual handsets, recorded as a named gate — not by preference. *Basis: discovery § Capture Modalities recommendation + Phase A; the dictate-after tier is what makes a shippable product exist even if ambient capture fails on iOS.*
- Q: Is the client's consent/decline recorded in the medical record? (Q4) → A: **No — it is recorded on the capture session, not in the chart, for 12a.** The per-encounter consent artifact (client/party, timestamp, professional, script version served, outcome) is durable and outlives the audio, but 12a has **no PIMS write verb of any kind**, so nothing 012 produces can reach the practice record by construction. Whether a signed note should carry a consent line into the chart is a 12b question, folded into the existing counsel gate. *Basis: 12a No-Go on all PIMS writes (009's non-goal stands) + R-1's "the audio/transcript is not part of the legal medical record."*
- Q: Euthanasia and difficult conversations — hard exclusion or DVM discretion? (Q5) → A: **Structural exclusion, no override in 12a.** Excluded encounter classes cannot start ambient capture at all. Initial list: **euthanasia / end-of-life, financial-hardship or payment-plan discussions, and client-complaint conversations.** The list is a per-practice property confirmed with a DVM at kickoff; a one-tap "not this one" is always available for encounters the appointment type mislabels. *Basis: independently validated by the legal research (§ Consent hard operational rules) and by the discovery's own rabbit-hole warning — "do not discover this in the field."*
- Q: Personal phone or practice-issued number? (Q6) → A: **The professional's own phone.** D3's NFR bar states it directly ("opt-in from the professional's own phone"), and a practice-issued device *is* the "new software" Working Rule 0 forbids. The cost is paid with a documented data-handling posture: no client-identifying content persists on the device beyond the in-flight capture buffer, audio is never written to the device's own photo/file library, and delivery is to a channel the professional already uses. *Basis: D3 (binding NFR) + Working Rule 0.*
- Q: Does 012 supersede the demo-track `SoapDraftAgent` (spec 002), or run beside it? (Q7) → A: **Neither — 012's note is a new artifact on the platform plane and does not touch the demo one.** Shipped code confirms `SoapNote` (`backend/models.py`) is a flat text blob with a signature on demo-track SQLite (`soap_notes`, keyed to `timeblock_id`), with zero lineage fields, generated from a procedure template, surfaced in the staff-facing web UI that Working Rule 0 forbids pushing at staff (spec 002 FR-023–FR-028). 012 MUST NOT read or write `soap_notes`. The demo track keeps its copy until the demo retires; there is no shared table and no cross-plane lineage claim. *Basis: `backend/models.py::SoapNote`, `backend/repository.py`, spec 002 FR-023–028.*
- Q: Attribution when a tech does the exam and the DVM never speaks? (Q8) → A: **Tech-led encounters are out of 12a.** Capture and signing authority bind to one enrolled, named, licensed DVM at enrollment; attribution derives from the **enrollment**, never from a shared login and never from voice characteristics (there is no diarization — R-2). A vet-tech countersign flow is phase 2. *Basis: discovery persona P4 + the 12a No-Go on tech/CSR capture + R-2.*
- Q: Does the draft carry forward any prior-visit content in v1? (Q9) → A: **No.** Own-transcript/own-audio citations only. Citations into the practice record are blocked on the contract's C-3/R5 snapshot-versioned resolution, because KI-1 means a note signed in September citing a record re-ingested in October would silently resolve to different content — the audit trail retroactively lying about what the DVM saw when they signed. In a legal medical record that is a discovery liability, not a bug class. *Basis: `specs/009-vera-envelope-onboarding/known-issues.md` KI-1 + discovery § Citation Model sequencing consequence.*
- Q: Staff-discovery input — the personas are unvalidated hypotheses (Q11)? → A: **Not a spec question; folded into pilot week-1 ground truth**, alongside the after-hours call-log pull, following 010's provisional-target pattern. Two DVM conversations in week 1, and the honest test question asked directly: *"have you already been offered ezyVet's free AI-Assisted Notes, and what did you make of it?"* The persona set stays labelled hypothesis-level until then; nothing in the requirements depends on which persona seeds first. *Basis: discovery Q11 + 010 SC-004 precedent for provisional pilot-measured targets.*
- Q: Does 012 keep the transcript after the audio is deleted, or delete both? (Q14) → A: **Both expire on the same clock; C-8 fires once.** What survives an expiry is the frozen note text, the frozen citation set (claim → span locator + a cryptographic digest of the cited span), and a dated tombstone — provenance provable without the content being retained. *Basis: this extends R-1's own rationale rather than adding to it — the insurer guidance treats audio **and** transcripts as transitory draft material, retaining transcripts preserves nearly all of the note-vs-source impeachment surface that R-1 exists to eliminate while keeping none of its benefit, and a single expiry event is the honest shape ("audio kept only until you sign, then hard-deleted, with the alignment map preserved as proof of provenance"). Ratification rides the existing counsel gate; it does not block the build.*

**Still open (real product questions, tracked as `[NEEDS CLARIFICATION]` in the body):**

- **Q10 — Packaging.** Bundled inside the Vera subscription, or a per-DVM line? Competitors are self-serve per-DVM ($0–$200/DVM/mo) or flat per-clinic unlimited (HappyDoc $119–149); bundling is also the anti-commoditization move against a free in-PIMS scribe. Does not block the 12a build (there is no billing surface in 12a); **does** block the first commercial quote. Owner: Matt.
- **Q13 — Cloud ASR or on-device/edge inference.** The spec is written to be indifferent (ASR is a port; both adapter kinds must meet the same guarantees), but the choice is **customer-visible**: the disclosure script must truthfully state whether audio leaves the practice, and the cloud vendor being a **non-party** to the conversation is the core theory in the April 2026 CIPA class actions. It also touches Working Rule 4 ("production is cloud; DGX is a development/evaluation resource"). Must be decided before the first real client is recorded. Owner: Matt (+ counsel).

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Opt In From Your Own Phone, and Nobody Else Learns Anything (Priority: P1)

A DVM hears about it from a colleague — not from a rollout, a meeting, or an announcement. They text a number or tap a link from a text. One screen: who you are, which practice, and the consent script you'll read. That is the whole enrollment. No login is created for the practice, no account for anyone else, no dashboard, no notification to staff who didn't ask.

**Why this priority**: Working Rule 0 is binding and 012 is the first surface deliberately *aimed* at staff. It survives W0 only because it is pure pull: opt-in from the professional's own device, producing nothing for anyone who didn't opt in. Per D4, the opt-in rate is not a side metric — it is the success condition. If 012 ever needs a rollout, a training session, or a dashboard, it has violated its own thesis and should be stopped.

**Independent Test**: Enroll one DVM end-to-end from a text message on their own phone, unaided and with no manual, and reach a first signed note. Verify that no login, account, dashboard, notification, or artifact of any kind was created for any other person at that practice.

**Acceptance Scenarios**:

1. **Given** a DVM who has received only a link from a colleague, **When** they complete enrollment, **Then** capture and signing authority are bound to that one named licensed DVM, with their practice and its state recorded, and **no** login, account, dashboard, or notification exists for anyone else.
2. **Given** an enrolled DVM, **When** they capture and sign their first note, **Then** they reach it without a training session, a manual, or support contact.
3. **Given** a person who is not an enrolled, licensed DVM, **When** they attempt to enroll or capture, **Then** they cannot — tech and CSR capture is out of 12a.

---

### User Story 2 — Consent Before Capture, Every Time, and Gaps Are Visible (Priority: P1)

Before the visit starts, the DVM reads the disclosure script the app puts in front of them — it names that it is AI, that the conversation is recorded, where the audio goes, that the DVM reviews and signs every note, and when the audio is deleted — and asks a closed question. The client says yes, and only then does the record button work. A visible indicator runs the whole time. If the client says no, one tap drops to dictate-after and the visit continues exactly as it would have. If the script is skipped or the consent isn't logged, the resulting note carries a gap flag that cannot be dismissed.

**Why this priority**: This is the R-3 differentiator made mechanical. Every competitor contractually pushes consent liability onto the clinic; ezyVet is the state of the art and it is a checkbox. The pled defects in the April 2026 class actions read as a design checklist — no clear notice of AI recording, no notice of third-party processing, no uniform consent process, no reliable recording indicator, no deletion process — and this story answers all five. It is also a criminal-exposure surface (Florida: third-degree felony), so it is enforced in the capture adapter, not asserted in copy.

**Independent Test**: Attempt to start ambient capture without an affirmed consent — verify it is impossible and that no audio buffer is retained. Then run a consented encounter and verify the per-encounter consent artifact, the running indicator, a working mid-visit pause, and a one-tap decline that drops to dictate-after with no re-ask. Finally, force a skipped-script path and verify the resulting note carries a persistent, non-dismissible gap flag that appears in the practice's consent record and cannot be repaired after the fact.

**Acceptance Scenarios**:

1. **Given** no affirmed consent for this encounter, **When** the DVM attempts to start ambient capture, **Then** capture does not start, no audio is buffered or retained, and the gate is enforced in the capture adapter rather than in UI copy.
2. **Given** consent is affirmed, **When** capture runs, **Then** a per-encounter consent artifact is persisted (client/party, timestamp, professional, script version served, outcome), a visible recording indicator runs for the full duration, and pause is available at any moment and reflected in both the indicator and the artifact.
3. **Given** the client declines, **When** the DVM taps decline, **Then** ambient capture is prevented instantly, the encounter drops to dictate-after, the decline is logged, the client is not re-asked for that encounter, and nothing about the visit's service, scheduling, or price changes.
4. **Given** an encounter captured without a recorded consent affirmation or without the script being served, **When** the note is produced, **Then** the encounter and the note carry a persistent, non-dismissible consent-gap flag, the gap is surfaced in the practice's own consent record, and it cannot be silently repaired after the fact.
5. **Given** an encounter class on the excluded list (euthanasia/end-of-life, financial-hardship, client-complaint), **When** ambient capture is attempted, **Then** it is structurally impossible in 12a — there is no override.

---

### User Story 3 — A Cited Draft in Under 60 Seconds (Priority: P1)

The DVM taps stop when the appointment ends. Under 60 seconds later, a structured SOAP draft is in the same thread. Subjective and Objective are rich — the client's words, the exam findings as stated. Assessment and Plan contain only what the DVM actually verbalized. No drug name, dose, number, or lab result appears unless it was spoken; anything heard-but-unclear is a visible `[unclear: …]` placeholder, never a plausible guess.

**Why this priority**: This is the felt product and the whole latency promise (D3's <60s bar, benchmarked against a 38–76s peer-reviewed median). The no-unspoken-specifics rail is the single highest-value safety rail in the design: fabricated and misspelled drug names are the #1 field complaint in the category, and drug names, species-specific units, and mg/kg dosing are exactly where veterinary ASR will fail.

**Independent Test**: Run a realistic multi-speaker exam-room recording containing spoken drug names and doses plus deliberately garbled ones. Verify the draft arrives under 60 seconds, that S/O carry the spoken content, that A/P contain nothing the DVM did not say, that **zero** unspoken specifics appear anywhere, and that every garbled specific renders as `[unclear: …]`.

**Acceptance Scenarios**:

1. **Given** a completed capture, **When** the draft is generated, **Then** it is available to the DVM in under 60 seconds from capture end, structured as SOAP.
2. **Given** content the DVM did not verbalize, **When** the draft is generated, **Then** Assessment and Plan contain none of it — no differential, no diagnosis, no prognosis, no treatment recommendation, no inferred clinical content.
3. **Given** a drug name, dose, numeric measurement, or lab result that was **not** spoken in the encounter, **When** the draft is generated, **Then** it does not appear — the rail is enforced deterministically outside the model, in the adapter.
4. **Given** a specific that was spoken but not clearly heard, **When** the draft is generated, **Then** it renders as a visible `[unclear: …]` placeholder, and the note cannot be signed until it is resolved.
5. **Given** a capture that terminated abnormally (screen lock, backgrounding, an incoming call, network loss), **When** processing runs, **Then** the truncation is detected and surfaced to the DVM as a failure — a draft is never silently produced from a partial recording as if it were complete.

---

### User Story 4 — Tap Any Sentence, See Exactly Where It Came From (Priority: P1)

The DVM reads the draft. A line surprises them. They tap it, and the passage of the transcript it came from highlights — with the audio moment replayable, while the audio still exists. Under two seconds, one interaction. A sentence with no source says so, loudly, rather than pretending.

**Why this priority**: **This is the product.** It is the only answer to "why this instead of the free one already inside my chart," it is verifiably unclaimed in veterinary, and it is what converts the ~80% of the profession that refused scribes on verifiability grounds. It is also the platform's first user-facing consumer of the Pattern-① evidence contract — the mechanism by which the published promise *"Vera will never state a fact it cannot source"* is kept mechanically rather than asserted.

**Independent Test**: For a generated draft, tap each sentence and verify it resolves in one interaction to a span-level location in *this encounter's own* transcript/audio, with audio replay while retained. Verify any unsourced sentence renders as visibly unsourced — never as an empty or dead link. Verify that no citation resolves into the practice record.

**Acceptance Scenarios**:

1. **Given** any sentence in a draft, **When** the DVM taps it, **Then** it either resolves to a span-granular source location (transcript character range and audio millisecond offsets) in under two seconds, or is visibly marked as having no source. There is no third state.
2. **Given** audio still inside the retention window, **When** a cited sentence is checked, **Then** the corresponding audio span can be replayed.
3. **Given** a claim that draws on more than one part of the encounter, **When** it is generated, **Then** it can carry a **set** of source references, not just one.
4. **Given** any source reference in 12a, **When** it is resolved, **Then** it points only into this encounter's own transcript/audio — never into the practice record, prior visits, or a prior note.
5. **Given** the platform evidence contract is unavailable at build time, **When** 012 ships, **Then** it ships **sourceless drafts with the citation surface visibly stubbed and absent** — never a second, local evidence mechanism.

---

### User Story 5 — Review, Edit, Sign — and the Evidence Freezes With the Text (Priority: P1)

The DVM edits a sentence. Its citation immediately stops claiming to *support* the new text and is relabeled as *context* — the span is still there, it just no longer pretends to back a sentence the human rewrote. When they mark it done, the note is signed by them, and the signature freezes the text **and** the citation set together, immutably. Vera never signs.

**Why this priority**: The signed note is the legal artifact and its evidence must be as frozen as its text. An edited sentence still carrying its original citation is a lie with a link on it — the exact failure shape both 009 defects share ("invisible when broken: the reference still resolves"). This story is where the liability posture lives.

**Independent Test**: Edit a cited sentence and verify its citation is degraded to *context* and labeled as such. Sign the note and verify both text and citation set are frozen; attempt to mutate either and verify it is impossible and that any post-signature change produces a separately signed amendment.

**Acceptance Scenarios**:

1. **Given** a human edits a cited sentence, **When** the edit is saved, **Then** the citation degrades from *support* to *context*, is labeled as such, and no longer presents itself as backing the sentence.
2. **Given** any unresolved `[unclear: …]` placeholder, **When** signature is attempted, **Then** it is blocked until resolved.
3. **Given** the DVM signs, **When** signature completes, **Then** the note text and its citation set are frozen together and immutably; Vera never signs, and no note becomes a record without the DVM's own signing action.
4. **Given** a signed note, **When** a change is needed, **Then** it is captured as an amendment with its own signature — the signed artifact is never mutated.

---

### User Story 6 — Delivered Through the Channel You Already Use (Priority: P2)

The finished note goes back to the DVM — the same thread on their phone, email-to-self, or clipboard — as plain, paste-able text. It goes nowhere else. Nothing is written into ezyVet or any PIMS.

**Why this priority**: Delivery through existing channels is what makes 012 compatible with Working Rule 0 and with the envelope posture — 009's no-write non-goal stands, and the write-back adapter slot stays empty until write verbs promote at the pilot-activation gate. It is P2 only because it is mechanically simple, not because it is optional.

**Independent Test**: Complete and sign a note; verify it arrives in the DVM's existing channel as paste-able text, and verify **zero** writes to any PIMS and zero artifacts created in any staff-facing surface.

**Acceptance Scenarios**:

1. **Given** a signed note, **When** delivery runs, **Then** it is delivered to a channel the DVM already uses (their thread / email-to-self / clipboard) as plain paste-able text, with no dashboard, no destination app, and no login.
2. **Given** any point in the 12a flow, **When** the system acts, **Then** it performs no write to ezyVet or any other system of record; the write-back adapter slot exists and is empty.

---

### User Story 7 — Ephemeral Verification: the Audio Expires, the Provenance Doesn't (Priority: P2)

The audio and transcript live only as long as they are useful for checking the note — a 7-day default, 30-day ceiling — then they are hard-deleted automatically. Afterwards, tapping a sentence doesn't fail silently or hit a dead link: it says, in plain words, that the source audio for this sentence was deleted on a stated date under the practice's retention policy. A practice can shorten the clock freely; lengthening it requires someone to explicitly acknowledge the discovery risk in writing. A legal hold suspends deletion.

**Why this priority**: R-1, adopted. The insurer guidance is unambiguous — retained audio *"will undoubtedly be discoverable"* and a minor note/audio inconsistency *"could derail otherwise defensible cases."* Nobody in the market has claimed "audio kept only until you sign, then hard-deleted, with the provenance map preserved," while the incumbent stores recordings **inside the patient's clinical record**. It is simultaneously the smaller legal surface and the better story. It arrives at the same tombstone mechanism as KI-1's fix direction from an entirely independent direction, which is strong evidence the requirement is right.

**Independent Test**: Sign a note, advance past the practice's retention clock, and verify audio and transcript are hard-deleted and the deletion logged. Then tap a previously cited sentence and verify it resolves to a loud, dated tombstone naming what was deleted, when, and under which policy — never silence, never a dead link, never current content. Separately, apply a legal hold and verify deletion is suspended and the hold recorded.

**Acceptance Scenarios**:

1. **Given** a practice retention clock (7-day default, 30-day maximum) and no legal hold, **When** the clock expires, **Then** the encounter's audio **and** transcript are hard-deleted automatically, routinely, and with the deletion logged.
2. **Given** a deleted source, **When** any reference to it is resolved, **Then** it renders a loud, dated tombstone stating what was deleted, on what date, under which policy — and never silence, a dead link, or current state.
3. **Given** a practice wants a shorter clock, **When** they set it, **Then** it applies freely; **given** a practice wants a longer clock (up to the ceiling), **When** they set it, **Then** a named person must record an explicit acknowledgment of the discovery risk first.
4. **Given** a complaint, board inquiry, or preservation notice, **When** a legal hold is applied, **Then** deletion is suspended for the held material and the hold itself is recorded.
5. **Given** any point in the lifecycle, **When** audio is stored, **Then** it is never stored in the patient's clinical record, and the practice's written policy states that the signed note is the legal medical record while audio and transcripts are transitory draft material.

---

### User Story 8 — Dictate-After: a Real Product When Ambient Isn't Available (Priority: P2)

After the visit, the DVM taps once and talks — a summary, in their own words, with no client audio at all. It becomes the same structured, cited, signable draft. This is what happens when a client declines, when the excluded-encounter list applies, and if the ambient capture surface turns out not to work on the phones our DVMs actually carry.

**Why this priority**: It is what makes the decline path **costless**, which is the ethical requirement in US2, and it is the reason a shippable product exists even if the week-1 capture bench kills the ambient scope. It is a far easier problem — one speaker, no client audio, the consent question largely dissolves, accuracy is materially higher — and vets already pay for exactly this shape elsewhere.

**Independent Test**: With ambient capture unavailable (declined, excluded encounter type, or adapter failure), produce a dictate-after note end-to-end and verify it carries the same citation, review, signature-freeze, retention, and delivery guarantees as an ambient note.

**Acceptance Scenarios**:

1. **Given** the dictate-after tier, **When** a note is produced from it, **Then** every guarantee in US3–US7 applies identically — the same rail, the same span citations, the same freeze-on-sign, the same retention clock.
2. **Given** a client declines or an excluded encounter class applies, **When** the DVM proceeds, **Then** dictate-after is available immediately with no additional setup and no re-prompt about consent for that encounter.

---

### User Story 9 — Instrument the Feelings, and the Adoption Curve (Priority: P2)

From note #1: per-DVM opt-in rate week over week per site (the "beg for it" metric), draft latency p50/p95 against the 60-second bar, edit distance per note, client-decline rate, consent-gap rate, and cost-per-draft. Nothing here is a hours-saved headline.

**Why this priority**: D4 makes opt-in rate the success condition rather than a vanity metric — if it is flat, the product is wrong; if it climbs with no rollout, Working Rule 0's "staff beg for it" bar is met literally. The client-decline rate is first-class because the only rigorous evidence available (81.6% → 55.3% consent as disclosure gets honest) says truthful disclosure costs consents, and that trade must be measured rather than optimized around.

**Independent Test**: After a week of pilot use, verify all six metrics are reported per site from note #1, that cost-per-draft derives from an auditable per-provider rate source, and that no hours-saved figure appears in any customer-facing surface.

**Acceptance Scenarios**:

1. **Given** any pilot week, **When** metrics are reported, **Then** per-DVM opt-in rate week-over-week, latency p50/p95, edit distance, client-decline rate, consent-gap rate, and cost-per-draft are all present per site.
2. **Given** the first note ever produced, **When** it completes, **Then** cost-per-draft is computed and reported for it, from a per-provider rate source that is auditable and provider-swap-safe.

---

### Edge Cases

- **Multiple pets in the room.** One capture session yields one note for one explicitly selected patient. If content about a second patient is present, it is not silently merged into the first note — cross-patient contamination is a named field complaint in the category and citations are the proof mechanism against it.
- **The client raises something personal, financial, or about their own health mid-visit.** Pause is offered proactively and is one tap; the pause is reflected in the indicator and recorded in the consent artifact.
- **A third person is in the room** (a partner, an adult child, a friend). The notice is addressed to everyone present, not just the account holder — in all-party states they are parties too.
- **A client says yes, then changes their mind mid-visit.** Capture stops immediately, the withdrawal is logged, and the encounter drops to dictate-after; anything already captured for that encounter is subject to the withdrawal, not to the default clock.
- **The appointment type is mislabeled** and an excluded conversation happens anyway (a wellness visit becomes an end-of-life conversation). The DVM has a one-tap "not this one" that stops capture and discards, available at any moment.
- **Capture silently stops** (screen lock, backgrounding, incoming call, network loss). The truncation is detected and surfaced as a failure; a draft is never presented as complete when its source wasn't. *A recording that silently stops mid-consult is worse than no product.*
- **The DVM signs late** — after a weekend or a sick day. The 7-day default exists precisely to survive this; the note is still checkable when they get to it.
- **The evidence contract's span locators aren't ready.** 012 ships the citation surface visibly stubbed and absent. It never ships a local evidence table "temporarily."
- **Barking dog / heavy accent / an unfamiliar drug name.** Degrades into `[unclear: …]` placeholders that block signature, never into a plausible guess — the three named failure modes in the field evidence all land in the same safe state.

---

## Requirements *(mandatory)*

**Layer legend** — per *products share patterns, not resources*: **[P]** = pattern layer, shaped here to lift cleanly into the `ambient-professional-scribe` pattern (adoptable by FarmAgent field notes and MedWatchers pharmacist CMR, each on its own substrate). **[V]** = vet-specific, stays in VetAgent. A shared *shape*, never a shared service.

### Enrollment & Opt-In (Working Rule 0)

- **FR-001** **[P]**: Enrollment MUST complete entirely inside channels the professional already has (a text or a link from a text), in one screen, and MUST NOT create a login, account, dashboard, notification, or artifact of any kind for any person who did not opt in.
- **FR-002** **[P]**: Enrollment MUST bind capture and signing authority to exactly one named, licensed professional. Attribution MUST derive from the enrollment — never from a shared login, and never from voice characteristics.
- **FR-003** **[V]**: Only a licensed DVM may enroll in 12a; enrollment MUST record the DVM's license identity, their practice, and that practice's state.
- **FR-004** **[P]**: A practice MUST be a first-class entity carrying its jurisdiction (state) from day one, even though 12a applies **one national posture at the strictest-state bar**. No per-clinic or per-state consent branching ships in 12a.
- **FR-005** **[P]**: No training session, manual, or support contact may be required to reach a first signed note. *(Kill criterion: if a professional needs training, the feature has failed its own thesis.)*

### Consent — the mechanism we build and warrant (R-3)

- **FR-006** **[P]**: Ambient capture MUST be hard-gated on an affirmed consent for that specific encounter, enforced **in the capture adapter** — not in the model and not in UI copy. Absent an affirmation, no capture starts and no audio is buffered or retained.
- **FR-007** **[V]**: The in-room disclosure script MUST be surfaced to the DVM at capture start and MUST name: that it is an AI assistant; that the conversation is recorded; **whether and where the audio is transmitted outside the practice** (derived from the ASR adapter actually in use — never hardcoded); that the DVM reviews and signs every note; and the active deletion clock. It MUST ask a closed question producing a recordable yes/no, and MUST be addressed to everyone present, not only the account holder.
- **FR-008** **[P]**: A per-encounter consent artifact MUST be persisted — client/party, timestamp, professional, script version served, outcome (affirmed / declined / withdrawn / paused) — durable, and outliving the audio it authorized.
- **FR-009** **[P]**: A visible recording indicator MUST run for the entire duration of capture. Pause MUST be available at any moment, reflected in the indicator, and recorded on the consent artifact.
- **FR-010** **[P]**: A one-tap decline MUST be available at any time and MUST cost nothing: capture stops or never starts, the encounter drops to the dictate-after tier, service/scheduling/price are never conditioned on consent, and the client MUST NOT be re-asked for that encounter.
- **FR-011** **[P]** *(the warranted mechanism)*: When an encounter is captured without a recorded consent affirmation, or without the script being served, or with an incomplete consent artifact, the system MUST attach a **persistent, non-dismissible consent-gap flag** to the encounter and to the resulting note, and MUST surface it in the practice's own consent record. Gaps MUST NOT be silently repairable after the fact. *(We warrant the mechanism and its visibility; we do not warrant the practice's operational behavior — R-3.)*
- **FR-012** **[P]**: Configured excluded encounter classes MUST make ambient capture structurally impossible, with **no override in 12a**. **[V]** The initial excluded list is euthanasia / end-of-life, financial-hardship or payment-plan discussions, and client-complaint conversations; the list is a per-practice property confirmed with a DVM at kickoff. A one-tap "not this one" MUST additionally be available for any encounter at any moment.
- **FR-013** **[P]**: ASR and any audio-processing vendor MUST be bound by a no-training attestation persisted alongside the transcript (reusing 010's `vendor_no_training_attestation` shape) and by a DPA. The disclosure script (FR-007) MUST reflect the actual audio-egress posture of the adapter in use.
- **FR-014** **[P]**: A standing plain-language client-facing explanation page MUST exist and be readable in advance of a visit. **[V]** Practices MUST additionally be supplied exam-room signage and a standalone intake consent artifact, physically separate from treatment consent and from any privacy notice (bundling is the pled defect in the 2026 class actions).
- **FR-015** **[P]**: No speaker diarization, voiceprint extraction, speaker identification, or speaker-verification operation may be performed on captured audio in 12a (R-2).

### Capture

- **FR-016** **[P]**: Capture MUST be a port — long-form audio in, timestamped transcript out — with pluggable adapters (mobile-web, native, dictate-after). Adapter selection is decided by on-device bench evidence, not preference.
- **FR-017** **[P]**: The **dictate-after** adapter MUST ship in 12a and be available at all times as the fallback tier and the decline path, carrying every guarantee an ambient note carries.
- **FR-018** **[P]**: Capture MUST require zero new hardware, zero wake words, and zero per-encounter configuration (no species, appointment-type, or speaker picker): one tap to start, one tap to stop.
- **FR-019** **[P]**: An abnormally terminated capture (screen lock, backgrounding, interrupting call, network loss) MUST be detected and surfaced to the professional as a failure. A draft MUST NEVER be presented as complete when it was generated from a truncated recording.
- **FR-020** **[P]**: No client-identifying content may persist on the professional's device beyond the in-flight capture buffer, and audio MUST NEVER be written to the device's own photo or file library.

### Draft Generation

- **FR-021** **[V]**: The draft MUST be structured as a SOAP note.
- **FR-022** **[P]**: **S/O rich, A/P conservative.** Subjective and Objective are transcription-shaped; Assessment and Plan MUST contain only what the professional verbalized, never anything inferred.
- **FR-023** **[P]** *(the no-unspoken-specifics rail)*: The system MUST NEVER emit a value in the vertical's dangerous-specific classes that was not spoken in the encounter. The rail MUST be enforced deterministically **outside the model**, in the adapter. **[V]** The vet classes are: drug name, dose / route / frequency, numeric measurement, and lab result. *(Pattern parameterization: ag = product / rate / REI; pharmacy = drug / dose / interaction.)*
- **FR-024** **[P]**: A specific that was spoken but not clearly heard MUST render as a visible `[unclear: …]` placeholder — never as a plausible guess.
- **FR-025** **[P]**: The draft MUST be available to the professional in under 60 seconds from capture end.
- **FR-026** **[V]**: The draft MUST NOT contain diagnosis, prognosis, differential, treatment recommendation, or any Tier-2 clinical content the DVM did not speak. 012 transcribes and structures what a licensed professional said; it authors no clinical knowledge, and any drift into inferred clinical content requires a named-DVM signature under the Tier-2 gate in `domains/vet/clinical/`.
- **FR-027** **[P]**: Patient/encounter attachment MUST come from the professional's own day schedule or an explicit selection — never inferred from audio. One capture session produces one note for one named patient; content concerning another patient MUST NOT be silently merged.

### Citations — the user-facing consumer of the Pattern-① evidence contract

- **FR-028** **[P]**: Every draft sentence MUST carry **either** an intrinsic source reference generated at generation time **or** an explicit "no source" value. There is no third state.
- **FR-029** **[P]**: Source references MUST be obtained from the **one** platform evidence contract (`claim → source-ref → resolver`, source-ref intrinsic at generation time). 012 MUST NOT create a parallel evidence mechanism. If the contract is unavailable, 012 ships sourceless drafts with the citation surface **visibly stubbed and absent** — never a second mechanism, not even temporarily (Ruling A).
- **FR-030** **[P]** *(C-1)*: Source references MUST be **span-granular** — addressing a sub-record region as a transcript character range and as audio millisecond offsets.
- **FR-031** **[P]** *(C-2)*: A single claim MUST be able to cite a **set** of source references cheaply.
- **FR-032** **[P]**: In 12a, source references MUST resolve **only** into this encounter's own transcript and audio — sources that are 012's own and immutable by construction. Citations into the practice record (prior visits, vaccine history, prior notes) are prohibited until the contract's snapshot-versioned resolution (C-3 / contract R5) lands, because KI-1 means a re-ingested record resolves silently to new content.
- **FR-033** **[P]** *(C-5)*: "No source" MUST be a first-class value that renders as *visibly unsourced* — never as an empty link, a dead link, or a silent omission.
- **FR-034** **[P]**: Checking a sentence MUST take one interaction and reach the highlighted source span in under two seconds; while audio is retained, the cited audio span MUST be replayable.
- **FR-035** **[P]** *(C-6)*: When a human edits a cited sentence, its citation MUST degrade from **support** to **context**, be labeled as such, and MUST NOT continue to present itself as backing the edited text.
- **FR-036** **[P]** *(C-7)*: Signature MUST freeze the note text **and** its citation set together, immutably.
- **FR-037** **[P]**: 012 MUST file requirements C-1 … C-8 against the Pattern-① contract and consume the result. Any requirement the contract cannot yet satisfy MUST appear as a **visible gap in 012**, never as a local workaround.

### Signature & the Licensed Act

- **FR-038** **[V]**: Only the enrolled DVM may sign. Vera never signs. No note becomes a record without the DVM's own signing action.
- **FR-039** **[P]**: Signature MUST be blocked while any `[unclear: …]` placeholder is unresolved.
- **FR-040** **[P]**: A signed artifact MUST NEVER be mutated. Post-signature changes produce an **amendment** carrying its own signature and its own frozen citation set.
- **FR-041** **[P]**: No autonomous write to any system of record, ever, in 12a. The draft goes to the professional; the professional decides.

### Delivery

- **FR-042** **[P]**: Delivery MUST be to a channel the professional already uses — their existing thread, email-to-self, or clipboard — as plain, paste-able text. No dashboard, no separate destination app, no login.
- **FR-043** **[P]**: The delivery port MUST carry a **write-back adapter slot that stays empty** until the vertical's write verbs promote. **[V]** The ezyVet write-back adapter is 12b, gated on write-verb promotion at the pilot-activation gate.

### Retention — Ephemeral Verification (R-1)

- **FR-044** **[P]**: Audio **and** transcript MUST be retained only through signature on a fixed clock — **7-day default, 30-day ceiling** — then automatically hard-deleted.
- **FR-045** **[P]**: A practice MAY shorten the clock freely. Lengthening it (up to the ceiling) MUST require a named person to record an explicit acknowledgment of the discovery risk first — never an accidental default.
- **FR-046** **[P]**: Deletion MUST be routine, automatic, policy-driven, and logged. A **legal hold** MUST suspend deletion on any complaint, board inquiry, or preservation notice, and the hold itself MUST be recorded. *(Deleting after notice of a claim is spoliation; a fixed clock plus a hold is the defensible shape.)*
- **FR-047** **[P]** *(C-8)*: On expiry, every reference into a deleted source MUST resolve to a **loud, dated tombstone** naming what was deleted, when, and under which policy — never to silence, a dead link, or current state. A cryptographic digest of the cited span MUST be retained so provenance stays provable without the content being retained.
- **FR-048** **[P]**: Retention MUST be a **customer-visible term** — stated in the disclosure script, on the client-facing page, and in the practice's own terms.
- **FR-049** **[V]**: Written policy MUST state that the signed note is the legal medical record while audio and transcripts are transitory draft material, and MUST name the mismatch explicitly (the record is retained for years under state law; the audio for days). Audio MUST NEVER be stored in the patient's clinical record.

### Metrics (first-class)

- **FR-050** **[P]**: Per-professional **opt-in rate week over week**, reported per site, MUST be captured as the primary success condition (D4) — not a side metric.
- **FR-051** **[P]**: Draft latency p50/p95 against the 60-second bar MUST be measured from note #1.
- **FR-052** **[P]**: Edit distance per note MUST be measured.
- **FR-053** **[P]**: **Client-decline rate** MUST be measured per site from encounter #1 and reported alongside opt-in rate as a first-class metric.
- **FR-054** **[P]**: **Consent-gap rate** (FR-011) MUST be measured and reported to the practice.
- **FR-055** **[P]**: Cost-per-draft MUST be captured from note #1, computed from an auditable, provider-swap-safe per-provider rate source (the `pricing.yml` shape from 010's `telemetry.py`).

### Artifact Boundary

- **FR-056** **[V]**: 012's note is a **new artifact on the platform plane**. 012 MUST NOT read or write the demo-track `soap_notes` table or the `SoapDraftAgent` artifact (spec 002). The demo track keeps its own copy until the demo retires; there is no shared table and no cross-plane lineage claim.

---

## Key Entities

- **EnrolledProfessional**: One named, licensed DVM who opted in from their own device — license identity, practice, signing authority. The sole source of note attribution.
- **Practice**: The practice/site, carrying its **state/jurisdiction** as a first-class property from day one, plus its retention clock, excluded-encounter list, and consent configuration.
- **CaptureSession**: The lifecycle unit — enroll → consent → capture → finalize → deliver → sign → expire. Carries the capture adapter used, start/stop/pause events, termination status (clean / truncated), and the encounter class.
- **ConsentArtifact**: Per-encounter, durable, outliving the audio — client/party, timestamp, professional, script version served, outcome (affirmed / declined / withdrawn / paused).
- **ConsentGap**: A persistent, non-dismissible flag on an encounter and its note when the consent mechanism was not followed. The visible half of R-3.
- **Transcript**: The append-only, span-addressable text of the encounter with the vendor no-training attestation. Expires on the retention clock.
- **AudioObject**: The captured audio, span-addressable by millisecond offset. Expires on the retention clock. Never stored in the patient's clinical record.
- **NoteDraft**: The structured SOAP draft — sentences/claims, `[unclear: …]` placeholders, edit state, the patient it is attached to.
- **Claim (draft sentence)**: The unit that carries evidence — either a source-reference set or an explicit "no source."
- **SourceRef**: A span-granular locator obtained from the Pattern-① contract — `(transcript_id, char_start, char_end)` and `(audio_object, t_start_ms, t_end_ms)` — with a support/context role and a content digest.
- **SignedNote**: The frozen legal artifact — text and citation set frozen together at signature, with the signing DVM's identity. Amendments are separate signed artifacts.
- **RetentionPolicy / ExpiryEvent / Tombstone**: The clock (default, ceiling, shorten-freely / lengthen-with-acknowledgment), the logged deletion, and the dated tombstone every dangling reference resolves to.
- **LegalHold**: A recorded suspension of deletion triggered by a complaint, board inquiry, or preservation notice.
- **DeliveryReceipt**: Confirmation the signed note reached the professional's existing channel. Carries the empty write-back adapter slot.
- **AdoptionMetric**: The per-site, per-week metric set — opt-in rate, latency p50/p95, edit distance, decline rate, consent-gap rate, cost-per-draft.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: **100%** of draft sentences carry either a resolvable span-level source reference or an explicit, visibly-rendered "no source" — **0** sentences in any third or silent state.
- **SC-002**: **0** ambient captures start without a recorded consent affirmation; **100%** of captured encounters have a per-encounter consent artifact; **100%** of encounters where the mechanism was not followed carry a persistent, non-dismissible gap flag (**0** silent gaps, **0** after-the-fact repairs).
- **SC-003**: Draft delivered in **under 60 seconds p50** and **under 90 seconds p95**, measured from capture end, from note #1.
- **SC-004**: **0** drug names, doses, numeric measurements, or lab results appear in any draft that were not spoken in the encounter (verified against an adversarial corpus); **100%** of heard-but-unclear specifics render as `[unclear: …]`, and **0** notes are signed with one unresolved.
- **SC-005**: **0** signed notes mutate after signature; **100%** of signed notes carry an immutably frozen citation set alongside their frozen text; **100%** of post-signature changes are separately signed amendments.
- **SC-006**: **100%** of human-edited cited sentences have their citation degraded to *context* and labeled; **0** edited sentences present an original citation as *support*.
- **SC-007**: **100%** of audio and transcripts are hard-deleted by the practice's clock (7-day default, 30-day ceiling) absent a legal hold, with the deletion logged; **100%** of references into deleted sources resolve to a dated tombstone and **0** resolve to silence, a dead link, or current state.
- **SC-008**: **0** writes to ezyVet or any PIMS; **0** logins, dashboards, notifications, or artifacts of any kind produced for anyone who did not opt in.
- **SC-009**: A DVM goes from a draft sentence to its highlighted source span in **one interaction**, in **under 2 seconds at p50**.
- **SC-010**: Per-DVM opt-in rate is reported week over week per site from week 1 and **rises without any announcement, rollout, or training session**; a newly enrolled DVM reaches a first signed note **unaided within 10 minutes**, with no manual and no support contact. *(The Working Rule 0 success condition, tested rather than asserted. The rate target itself stays provisional until pilot week-1 ground truth — see 010 SC-004 precedent.)*
- **SC-011**: Client-decline rate is measured per site from encounter #1; **100%** of declines drop to dictate-after with no re-ask for that encounter and **0** change to service, scheduling, or price.
- **SC-012**: **0** speaker-diarization, voiceprint, or speaker-identification operations are performed on captured audio (R-2), verified by an automated build-time check.
- **SC-013**: **0** truncated or abnormally terminated captures produce a draft without a visible failure notice.
- **SC-014**: Cost-per-draft is reported from note #1 from an auditable, provider-swap-safe rate source; **0** hours-saved figures appear in any customer-facing surface.

---

## Non-Goals *(cycle 12a)*

- **Any write into ezyVet or any PIMS.** 009's non-goal stands; **12b write-back is gated on write-verb promotion** at the pilot-activation gate.
- **Citations into the practice record** — prior visits, vaccine history, prior notes — and any carry-forward of prior-visit content. Blocked on C-3 / contract R5 (KI-1). 12a cites only its own transcript and audio.
- **Any login, dashboard, training session, or rollout** for anyone who did not opt in (Working Rule 0, binding).
- **Wake words, room hardware, always-on ambient capture, or a separate destination app** (D3 + board §III declines).
- **Speaker diarization, voiceprints, or any speaker-identification operation** (R-2).
- **Emitting any drug name, dose, numeric value, or lab result not spoken in the encounter**; any inferred Assessment or Plan content; any diagnosis, prognosis, or treatment recommendation (won't-do list; Expert Firewall; the Tier-1/Tier-2 line).
- **Vet-tech and CSR capture** (they cannot sign, and the signature is the liability posture — phase 2 needs an explicit DVM-countersign flow); **multilingual**; **discharge-instruction generation**; **charge/code extraction**; **clinical decision support**. All deliberately deferred — the note has to be trusted first.
- **A parallel evidence mechanism of any kind** (Ruling A). If the contract slips, the citation surface ships visibly stubbed and absent.
- **Retaining audio past the signature window** without an explicit Matt + counsel decision, and **never** in the patient's clinical record.
- **Per-clinic or per-state consent branching** — one national posture at the strictest-state bar.
- **Claiming "HIPAA compliant" as a trust signal** — a category error (HIPAA does not reach veterinary practice) that every competitor makes and that answers none of the questions that matter.
- **Marketing hours-saved** (D4 counter-finding: after-hours EHR time often does not drop; what changes is how the work *feels*), or marketing the ezyVet integration publicly (Working Rule 2).

---

## Platform-Common: `ambient-professional-scribe`

Registered back to COS-platform as a **pattern**, per *products share patterns, not resources* — **never a shared scribe service**. FarmAgent (field notes) and MedWatchers (pharmacist CMR documentation) vendor the pattern and run it on their own substrate, with their own database and their own adapters. This is the C8-scheduling precedent repeating: vet proves it first.

| Pattern layer (lifts) | Vet layer (stays) |
|---|---|
| Opt-in capture-session lifecycle: enroll → consent → capture → finalize → deliver → sign → expire | SOAP section grammar |
| **Consent as a port**, not a hardcoded script — per-vertical policy on a shared shape | The in-room client consent script; the US state recording posture; exam-room signage |
| Capture port (long-form audio in, timestamped transcript out) with pluggable adapters | Veterinary lexicon: species, breeds, drug names, mg/kg conventions |
| Draft artifact + citation set as the Pattern-① user-facing consumer (C-1 … C-8) | The dangerous-specific classes: drug / dose / numeric / lab result |
| Review-and-sign loop; signature freezes text **and** evidence; no auto-write | DVM signature semantics; vet-board record-retention rules; VCPR |
| Delivery-through-existing-channels port with an **empty write-back adapter slot** | The ezyVet write-back adapter (12b only) |
| The "never emit an unspoken specific" rail, parameterized by vertical | The vet won't-do-list lines and the Tier-1/Tier-2 domain-pack line |
| Ephemeral verification: fixed clock, legal hold, dated tombstones | State-variable records-retention periods (CA 3y, TX 5y, NY 3y, FL 3y…) |
| The NFR bar (<60s, zero hardware, zero wake words) and the metric set | — |

**Why consent must be a port and not a shared implementation**: the three verticals have genuinely different regimes. Vet has **no HIPAA** but state wiretap law with a client in the room. FarmAgent field notes are usually the agronomist alone or with a grower — a far lighter posture. MedWatchers pharmacist CMR is **HIPAA in full** plus pharmacy-board rules. A shared consent *service* would be wrong in two of three verticals; a shared consent *shape* with per-vertical policy is right in all three.

**Also registers back**: the **C-1 … C-8 citation-consumer requirements** onto the Pattern-① evidence contract, with **C-6 (edit degradation)** and **C-8 (retention-expiry tombstones)** as 012-originated asks.

---

## Assumptions & Dependencies

- **Pattern-① evidence contract (Vera-core) — hard dependency.** Ruling A (2026-07-28) made the contract platform-wide and lifted the C6 port hold; 012 is its **first user-facing consumer**. C-1 (span-granular locators) is the #1 ask and must land in v1, not v2 — that is the difference between shipping Linked Evidence and shipping a promise. C-1 … C-8 must be filed **now**, while the contract is being designed. **If the contract slips, 012 ships the citation surface visibly stubbed and absent — never a second mechanism.**
- **010 voice stack — partial dependency, honestly stated.** The **governance half transfers**: adapter guarantees (disclosure enforced in the adapter, not the model), append-only transcript persistence, the `consent_record` + `vendor_no_training_attestation` shape, the autonomy gate, `telemetry.py` + `pricing.yml` cost-per-unit machinery, and the dual-mode `is_live()` sim-first discipline (inherit wholesale). The **media half does not**: 010 is a telephony realtime speech-to-speech pipeline (μ-law 8 kHz, turn-taking, barge-in, session resumption); a scribe is long-form, high-fidelity, in-room capture → ASR → structured summarization. There is **no ASR, no diarization, and no long-form audio store** anywhere in the repo. **012 must NOT be sequenced behind 010 going live** — they share governance, not a media path. Planning 012 as "010 plus a prompt" would blow the estimate.
- **009 lineage — resolve target, with two blocking defects.** KI-1 (re-ingest silently rewrites what a reference resolves to) and KI-2 (derived claims persist results without their input set) both name 012's note citations as blast radius. Both must sequence **with** the contract (R5, R2), not around it. 12a avoids the exposure entirely by citing only its own immutable sources.
- **011 identity — soft dependency.** 012 needs *which patient this note is for*, which the DVM's own day schedule already answers. 012 is far less 011-coupled than 010 is.
- **VP-1 Postgres + RLS plane.** Notes, audio, consent artifacts, and citation sets cannot live on demo SQLite. Platform-track spec under the constitution's v1.1.0 Platform-track exception (Principle III), as with 010 and 011.
- **Gate 1 — week-1 capture bench** (before build commitment): long-form mobile-web capture through screen-lock and backgrounding on the DVMs' actual handsets. **This gate is allowed to kill the ambient scope.** If it fails and native is rejected, 12a narrows to dictate-after — still a real product, and it still proves the citation model.
- **Gate 2 — counsel on the consent posture** (hard gate before the first real client is recorded, exactly as 010's D9 gates the first live call): the state footprint, the notice script, the decline path, the audio/transcript retention decision, and Q13's audio-egress choice. **This is not legal advice and nothing here is cleared.** Note the correction that matters most: 010's D9 all-party list is a *telephone* list; **in-person oral communication is governed differently** (CT/NV/MI are effectively one-party in person; DE/MD/MA/MT/NH/OR join the strict list) — copying 010's list into 012 would be wrong in both directions.
- **Gate 3 — vet-lexicon ASR accuracy spike** on realistically noisy exam-room audio (barking, multi-speaker, drug names, accents) before the draft generator is built. Note: **no independent accuracy benchmark exists for any veterinary scribe**, so this is our own measurement and must be described as such.
- **ASR vendor is a new subprocessor** — new DPA, no-training clause, and counsel review. The veterinary lexicon (drug names, breeds, species-specific units) is the accuracy risk, and the vendor being a **non-party to the conversation** is the core theory in the April 2026 CIPA class actions.
- **Pilot week-1 ground truth**: appointment/audio volumes (working estimate: ~15–25 appointments/day per GP DVM, ~10–20 min per wellness visit, ≈3–7 audio-hours/day per opted-in DVM), the Synergy Vet state footprint, and two DVM conversations validating the persona set — including the honest question about ezyVet's free AI-Assisted Notes.
- **Carried competitive risk**: IDEXX's free native scribe is **already rolling out to the pilot population** and can bundle a verification feature at any time. Assume ~12–24 months before evidence-linking is copied; the durable moat is the operating layer underneath, not the feature.
- **Ships with the cycle**: a vet-facing **"How Vera can be wrong, and how you'll catch her"** page — the companion to `marketing/what-vera-will-never-do.md`, whose three relevant lines (*never sign a medical record*; *never diagnose, prescribe, or alter a treatment plan*; *never state a fact it cannot source* — "a line in a draft note" is named explicitly) constrain behavior here, not just copy.
- **Spec-number drift (flagged, not owned here)**: the phase-4 brief seeded `011-vera-procurement` and `012-staff-scheduling`; the repo uses 011 for relationship memory and 012 for Vera Notes. **VP-5 (staff scheduling) and VP-7 (procurement) need fresh seed numbers** — for whoever owns the roadmap doc. 012 does not collide with either.
- **Open, tracked**: **[NEEDS CLARIFICATION: Q10 — packaging.** Bundled in the Vera subscription vs a per-DVM line. Does not block the 12a build (no billing surface in 12a); blocks the first commercial quote. Owner: Matt.**]** · **[NEEDS CLARIFICATION: Q13 — cloud ASR vs on-device/edge inference.** The spec is architecturally indifferent (ASR behind a port, identical guarantees either way), but the choice is customer-visible because FR-007 requires the script to state truthfully whether audio leaves the practice, and it touches Working Rule 4. Must be decided before the first real client is recorded. Owner: Matt + counsel.**]**

---

## Constitution Check

- **KNOW / ADVISE / DECIDE**: 012 is pure KNOW→ADVISE. The draft is a proposal; the DVM DECIDEs and signs. No verb runs autonomously and nothing reaches a system of record without a human action.
- **Expert Firewall / the licensed act**: 012 transcribes and structures what a licensed professional said. It authors no clinical knowledge, names no drug not spoken, and infers no assessment — Tier-1 under `domains/vet/`. Any drift into inferred clinical content requires a named-DVM signature under the Tier-2 gate.
- **Claim discipline extended to runtime**: every draft sentence is either sourced or visibly unsourced (FR-028). This is the strongest form of the runtime claim-discipline rule the product has attempted, and it is why the citation model is the spine of this spec rather than a feature in it.
- **Invisible adoption (Working Rule 0)**: satisfied only by pull. No login, no dashboard, no training for anyone who did not opt in; the opt-in rate is the success condition (SC-010), not a vanity metric.
- **Products share patterns, not resources**: shaped as a vendorable pattern with a per-vertical consent port; never a shared scribe service.

---

## Marketing Output
**Produced by**: speckit-specify — 2026-07-28

### Feature Brief

**Consumer-Friendly Feature Name**: Vera Notes — Leave Finished

**Key Benefits** (in customer language):
1. **Walk out when your last patient does.** Your note is drafted before you leave the room, in your words — not written from memory at 11pm.
2. **Check every sentence in one tap.** Every line points back to the exact moment it was said. You are not asked to trust a draft; you are handed the receipts.
3. **You sign. Vera never does.** And the recording doesn't linger — audio is deleted on a short, stated clock, and every citation turns into a dated record of what was there rather than a dead link.

**One-Line Description** (≤25 words): The veterinary scribe you can check — every sentence one tap from the moment it was said, signed by you, with the audio gone in days.

**Positioning Message Seed**: **"Leave finished."** — *Your notes are written before you leave the room, in your words, and you can check every sentence against what was actually said. You sign. Vera never does.*

**Why-Now Angle**: AI scribing in veterinary went from **3.5% to 17.5% of VIN members in 14 months**, and the draft itself is now free in half the PIMS on the market. What has *not* arrived is any way to check it — the category's own buyer's guides concede there is no independent, published accuracy benchmark for veterinary AI scribes and that any percentage a vendor quotes is their own measurement on their own terms. Every vet scribe asks you to trust the draft. Vera Notes hands you the receipts.

**Differentiation Source**: Not the note — the **catchability**, sold as **defensibility, not convenience**. The AAVSB position is that responsibility for AI use rests entirely with the licensee, and the board risk that actually bites is *"your record was wrong and you signed it"* — not *"you recorded the client."* A vet who can prove in three seconds that a dose came from an actual spoken sentence has a defense no competitor's product can produce. Second source: **the smallest legal surface that still offers verification** — nobody has claimed *"audio kept only until you sign, then hard-deleted, with the provenance map preserved,"* while the incumbent stores recordings inside the patient's clinical record. Third: Vera Notes is the only scribe attached to an operating layer that already knows the practice.

**Guidance note**: Sell **"leave finished"** and **"the note you can check"** — never hours-saved (the counter-evidence is explicit that after-hours time often does not drop; what changes is how the work feels), never "an AI writes your notes," and never "HIPAA compliant" (a category error every competitor makes — HIPAA does not reach veterinary practice, and it answers none of the questions that matter). Do not market the ezyVet integration publicly (Working Rule 2). The quote to harvest from the pilot is the vet analogue of Abridge's testimonials: *"this is why I became a vet."*

**Claim-check**: two `verified-claims.md` entries required before external use. **"First veterinary scribe with note-to-source linked evidence"** — supportable as a **[V-absence]** finding across 25+ sources, but it is a negative claim about competitors: file as **PENDING** with the scan cited and a re-check cadence. **"Audio deleted on signature"** is a **PRODUCT-CLAIM** — true only once the retention machinery ships (FR-044 … FR-049).
