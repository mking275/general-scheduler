# Feature Specification: Clinical Entities — Vera Learns the Medicine

**Feature Branch**: `013-clinical-entities`

**Created**: 2026-07-29

**Status**: Draft

**Input**: Cycle one of the clinical envelope. "When my staff or my client asks Vera something about an animal, I want her to answer from my own records — what we gave it, what it's due for, what we found, and when — and I want her to stop dead at the line where answering becomes practicing. Right now she can tell me what they owe and when they're booked, but not what's wrong with the dog, which makes her a receptionist with a calendar instead of a chief of staff." Scope: ingest the clinical majority of the §5 delivery onto the patient spine, class every clinical fact by sensitivity, ship the due/overdue recall engine, hold the record without quoting it, and make the administrative/clinical speech line mechanical.

---

## Problem Statement

The §5 delivery arrived and **63.5% of it was skipped**. Coastal Creek Animal Hospital's export is 618,109 rows across 45 files; spec 009 ingests 176,755 of them (28.6%). The other 392,516 rows — the medicine — are flagged-not-dropped and sitting in the vault. Vera holds the *business* of the practice and none of the *practice*.

That is not an academic gap. At **one** practice there are **8,303 overdue events and 4,325 overdue vaccinations**, with `CommunicationExport` already recording what was chased and what was not. That is unworked revenue the PIMS has been computing and nobody has been running. It is also, per the AAVSB's own reading, the safest thing an AI can do in a veterinary practice: reminder generation is explicitly administrative.

Meanwhile every clinical question routes to a human, and the alternative — leaving the clinical entities flagged forever and selling Vera as a scheduling and billing layer — is precisely the ground Dodo, Otto and Weave already occupy.

But this is the veterinarian's legal record. An assistant that mis-states a lab value, quotes a result the practice deleted, or reminds an owner that their dead dog is due for a booster is not a bug report — it is a board complaint, a lost client, or a discovery exhibit. So 013 is not "ingest the rest of the CSVs." It is **the spec that decides what Vera may hold, what she may say, and to whom** — and encodes all three as data and tests rather than as prompt instructions.

### Standing Condition (binding, whole-spec)

**If the sensitivity-classing layer is descoped for schedule, cancel the clinical ingest — do not ship it unclassed.** A clinical corpus without a per-fact class is a leak surface with a database behind it, and 011's default-deny was written against a corpus that did not contain the answer to *"what's wrong with the dog."* The classing **is** the feature; the recall engine is the value it makes safe to ship.

---

## Clarifications

### Session 2026-07-29

**Matt-directed and confirmed, 2026-07-29. These three are binding constraints on this spec's content and are not re-opened here.**

- Q: The SOAP narrative quartet (VisitHistory 5,510 · VisitExam 4,295 · ConsultAssessment 4,226 · ConsultPlan 5,480) — ingest now, or defer to cycle two? → A (Matt, R-1): **INGEST in cycle one.** This *reverses* the discovery's defer recommendation, and the reasoning is load-bearing: it is **Synergy Vet's own data, delivered at their own §5 request**, and a Vera that knows the billing but not the medicine is a weak proof for an operator planning 400 practices. Two conditions, both binding: (a) **the strictest audience class** — veterinarians and practice owners only, never a client, never an unverified caller, never a CSR; and (b) **non-citable until Vera-core's versioned-snapshot contract (R5) lands**, exactly as for every other clinical fact.
- Q: Where exactly does the administrative lane end and clinical advice begin, for a client audience? → A (Matt, R-2): **Vera may state schedule facts** — what is due, when, per the practice's own protocol. She may **not** supply **clinical context** — why it matters, what a value indicates, what else is relevant. **The test to encode: if removing the clause changes nothing about what the client should do, it is context and does not belong.** *"Rex is due for his booster"* ships. *"…and his last bloodwork was three months ago"* does not, to a client. To staff and owners it is permitted.
- Q: Final ingest scope for cycle one? → A (Matt, R-3): **The discovery's recommended subset stands, plus the SOAP narrative per R-1.** `DiagnosticResultItemExport` stays **OUT** (262,370 rows, 77% soft-deleted, 100%-empty interpretation, only 48% of live items carrying a reference range).

**Resolved this session (evidence from the real export, shipped code, or an existing spec answers it):**

- Q: Does the §5 letter's enumerated scope actually cover clinical records? (discovery Q2) → A: **Yes — and the config, not the delivery, is what is wrong.** The clinical files arrived inside the group's own §5 delivery, which R-1 states directly as the basis for ingesting the narrative. The legal basis is unchanged from 009: the **clinic's statutory ownership of its own records**, exercised via the §5 request, with counsel sign-off on the clinic-owned-data structure already a hard gate before any normalization (009 FR-004). What is defective is `config/envelope/section5_scope.yaml`, whose six categories name **no clinical source entity** — so a delivery containing zero clinical files would pass completeness as complete today, and 009 SC-004's claim to cover "clinical" is currently false. That is a live gap in a shipped gate; 013 closes it (FR-011). *Basis: Matt R-1 + 009 clarification 2026-07-18 (statutory ownership / §6.3) + `section5_scope.yaml` and `completeness.py::SCOPE_CANONICAL` read directly.*
- Q: Is `clinical_administrative` speakable to a verified client without per-use written informed consent? (discovery Q3) → A: **Yes, at the schedule-fact bar and no further** — R-2 draws the line and the removal test makes it testable. The AAVSB explicitly blesses reminder generation as routine administrative use; its decision-involvement threshold is what the removal test operationalizes. *Basis: Matt R-2 + AAVSB March 2025 whitepaper (read first-hand, `VetPractice/research/v02/l0-firsthand-regulatory.md`).*
- Q: Do Coastal Creek's fill rates generalize? (discovery Q4) → A: **Not a spec question — it is a profiling requirement.** n=1 of 23. Rather than betting either way, the spec forbids designing on assumed fill: no capability may be enabled on a field below a measured fill threshold, and each practice is profiled independently with the group map as a prior. If another practice populates BCS or its problem list, the capability lights up there without a spec change. *Basis: 009 FR-026 (group mapping is a prior, not an assumption) + 012's Q11 precedent for folding unvalidated priors into pilot week-1 ground truth.*
- Q: Does Vera decide what a patient is due for? → A: **No, never — she reads what the practice's own system already recorded as due.** Due status comes from `EventExport` / `VaccinationExport` due dates and `EventGroupAssociationExport`'s product → event-group → next-due-in-seconds mapping. Vera performs no protocol computation, applies no vaccination guideline, and adds no interval of her own. This is what keeps the entire recall engine inside the administrative lane rather than making it a clinical judgment with a calendar attached. *Basis: the real export's own due fields (verified) + the won't-do list's "never alter a treatment plan."*
- Q: Does 013 send the recall outreach, or produce the list? → A: **Produce the list; send nothing.** 013 is pure KNOW and adds no verbs. The overdue view is an owner/manager artifact and Vera may answer administrative due questions when asked; autonomous outbound recall campaigns require write/outreach verb promotion at the pilot-activation gate and are a separate spec. *Basis: discovery Constitution Check ("013 is pure KNOW; it adds no verbs") + 009 FR-029 + Working Rule 0.*
- Q: May a DVM read the verbatim SOAP narrative before R5 lands, given it is non-citable? → A: **Yes, as a live read — never as a captured quote.** Pre-R5 the narrative may be surfaced to a veterinarian or owner as current-state-at-read-time, explicitly labeled as such, and MUST NOT be persisted into a note, briefing, receipt, or any artifact that outlives the read. KI-1 means a quote captured today can silently resolve to different content after the next delta ingest; a live read carries no such promise and makes none. *Basis: `specs/009-vera-envelope-onboarding/known-issues.md` KI-1 + Matt R-1 condition (b) + 012 FR-032's identical reasoning.*
- Q: Which existing defects must 013 fix rather than route around? → A: **Four, all in shipped 009 code, all correctness rather than polish**: `Is Active` soft-deletes are ingested as live records; there is no type-coercion layer (dates, `YES`/`NO` vs `0`/`1`); the clinical children key on `Patient Code` while 009's `patient` `entity_ref` keys on `Animal Id`; and `section5_scope.yaml` has no clinical category. The first three are silent-wrongness of exactly the shape both 009 known issues share. *Basis: `ezyvet_adapter.py`, `normalizer.py`, `completeness.py`, `section5_scope.yaml` read directly + the real export.*
- Q: Does 013 inherit 009's hard-won ingest lessons or re-learn them? → A: **Inherit, and extend them per entity.** Parse only mapped entities; aggregate unmapped-field tracking per `(entity, column)` never per row (the `1b05899` fix); dedupe on the lineage key; and the empty-yield guard — which must become **per-entity**, because a run where the 9 original entities map and the 20 clinical ones map nothing passes the current whole-run guard while reporting success. *Basis: `normalizer.py::NormalizationYieldError`, `ezyvet_adapter.py::_unmapped_agg`, and the 2026-07-29 basename/path incident recorded in the code comments.*

**Still open (real product questions, tracked as `[NEEDS CLARIFICATION]` in the body):**

- **NC-1 — Retention and return posture for the ingested clinical corpus** (discovery Q5, partially resolved). The mechanical half is settled here as requirements: our copy is not the legal record, source deletion propagates (FR-008), and nothing outlives the customer relationship. What is *not* settled is the customer-visible term — whether a per-state retention floor applies to a clinic-owned vault copy across a 23-practice, multi-state group, and what the deletion/return commitment says in the contract. Does not block the cycle-one build; **does** block the first clinical contract language. Owner: Matt + counsel.
- **NC-2 — May a credentialed veterinary technician be admitted to the `clinical_narrative` class, per practice?** Cycle one ships Matt's strictest reading — licensed veterinarians and practice owners only — and default-deny means shipping behavior is correct either way. But a tech who ran the exam being unable to read back the note they helped produce is the friction a pilot will surface in week 1. Owner: Matt (+ pilot DVM/tech conversation). Does not block the build.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Every Clinical Fact Lands on the Right Patient (Priority: P1)

A medication row, a vaccination, a weight, a consult: each carries `Patient Code`, not `Animal Id`. Spec 009's canonical `patient` lineage key is built from `Animal Id`. Both resolve 100% against `AnimalExport` (2,658 ids, 2,658 codes) — but only through an index that does not exist today. Without it, every clinical record's patient lineage is silently wrong: the join succeeds against nothing, the record persists, and Vera answers confidently about the wrong dog.

**Why this priority**: This is the single highest-consequence defect available in this cycle, and it is invisible when broken — the same shape as KI-1 and KI-2. It is also the precondition for every other story here. Additionally, the patient is the spine and the consult is not: **56.7% of vaccinations, 45% of vitals and 34.7% of medications carry no consult id at all**, so a model rooted in the episode loses roughly half the medicine.

**Independent Test**: Ingest the real Coastal Creek export and assert that every clinical record resolves to the same `patient` `entity_ref` 009 produced from `Animal Id` for the same animal; assert that a clinical row whose `Patient Code` does not resolve is **rejected and flagged**, never persisted with a synthesized or partial reference; and assert that vaccination, medication and health-status rows with an empty consult id ingest successfully and are recallable by patient.

**Acceptance Scenarios**:

1. **Given** a clinical row keyed on `Patient Code`, **When** it is normalized, **Then** it carries the identical `patient` `entity_ref` as 009's `Animal Id`-keyed patient record for that animal — resolved through an explicit Code→Id index, not by string coincidence.
2. **Given** a clinical row whose `Patient Code` resolves to no animal, **When** normalization runs, **Then** the row is flagged as an unresolvable-lineage failure and is **not** persisted as a clinical fact.
3. **Given** a vaccination, medication, or health-status row with no `Consult Id`, **When** it is normalized, **Then** it ingests against the patient and is fully recallable; consult association is optional metadata, never a required key.
4. **Given** the same export ingested twice, **When** ingest re-runs, **Then** clinical records dedupe on the lineage key with zero duplicates.

---

### User Story 2 — What the Practice Deleted, Vera Never Says (Priority: P1)

The practice deleted a lab value, voided a consult, removed a medication row. `Is Active = NO` marks **817 consults, 1,284 medications, and 135 animals** in one export — and 201,233 of 262,370 diagnostic result items. The adapter today has no concept of a source-system deletion: it ingests every row as live. Quoting back a record the practice deleted is the medical-record form of KI-1.

**Why this priority**: It is simultaneously the correctness fix and the largest single performance win available, and it must be true before the corpus is classed rather than after. It is also the finding that registers back to the platform: source-system deletion belongs in the adapter port, not in each adapter's judgment.

**Independent Test**: Ingest an export containing `Is Active = NO` rows; verify none is recallable, quotable, or counted in any derived figure or overdue list, and that the deleted-row count is reported in the practice profile. Then deliver a delta in which a previously live row has become `Is Active = NO`, and verify the record becomes non-recallable without deleting the lineage evidence that it existed.

**Acceptance Scenarios**:

1. **Given** a source row marked `Is Active = NO`, **When** it is ingested, **Then** it is recorded as source-deleted and is excluded from recall, quotation, the overdue list, and every derived clinical figure.
2. **Given** a delta delivery in which a live record has become `Is Active = NO`, **When** the delta ingests, **Then** the deletion propagates — the fact becomes non-recallable — and the change is logged.
3. **Given** any clinical count reported to an owner, **When** it is computed, **Then** live and source-deleted rows are counted separately and the report states which it used.

---

### User Story 3 — The Overdue List Nobody Has Been Working (Priority: P1)

The practice's own PIMS already computed who is due and who is overdue: **32,014 events across 91 event groups (8,303 overdue, 7,862 future-dated)** and **7,949 vaccinations (4,325 overdue, 3,624 future)**, with `EventGroupAssociation` mapping product → event group → next-due interval and `CommunicationExport` recording exactly who was already chased (Vaccination 3,197 / Medication 2,785). Vera produces the list, cross-filtered against the dead, the inactive, and the already-contacted — the owner decides what to do with it.

**Why this priority**: Highest product value net of risk in the entire delivery. It quotes nothing, so it has **no citability dependency and can ship before R5**; it lives entirely in the AAVSB-blessed administrative lane; and it converts a number the owner has never seen into revenue they can act on this week.

**Independent Test**: Generate the overdue view for Coastal Creek and verify it reproduces the practice's own overdue counts from the practice's own due dates (no Vera-computed intervals); verify **zero** entries for animals flagged `Dead` or `Is Active = NO` or on closed accounts; verify entries already chased per `CommunicationExport` are marked as previously contacted with the date; and verify the derived list persists the contributing reference set for every figure it states.

**Acceptance Scenarios**:

1. **Given** a practice's ingested events and vaccinations, **When** the overdue view is generated, **Then** due and overdue status derives **only** from the practice's own recorded due dates and event groups — Vera computes no interval, applies no guideline, and adds no protocol of her own.
2. **Given** the overdue candidate set, **When** the view is produced, **Then** deceased animals, source-deleted animals, and closed accounts are filtered out before the list exists, not marked afterwards.
3. **Given** a patient already contacted about a due item, **When** they appear in the list, **Then** the prior outreach and its date are shown so the same client is not chased twice.
4. **Given** any total stated in the view ("N patients overdue for rabies"), **When** it is produced, **Then** the contributing reference set is persisted alongside the figure (contract R2) — a derived clinical claim with no traceable input set is not published.
5. **Given** the finished view, **When** it is surfaced, **Then** it reaches owner/manager surfaces only and produces no staff-facing artifact, and Vera sends nothing to anyone on her own initiative.

---

### User Story 4 — Vera States What Is Due; She Never Says Why It Matters (Priority: P1)

A client calls. Vera can tell them Rex is due for his booster and when the practice's record says it was due. She cannot tell them his last bloodwork was three months ago, that his weight is trending down, what a value means, or what else the practice might want to look at — even though she now knows all of it. The line is not a tone-of-voice instruction; it is a class check with a test.

**Why this priority**: This is R-2 made mechanical and it is the promise the published won't-do list already makes — *"an unverified caller can book a routine appointment; they cannot hear a diagnosis."* 013 is what makes that promise testable and falsifiable, and the leak surface after this cycle is categorically worse than the one 011's red-team suite was written against.

**Independent Test**: Run an adversarial client-audience corpus against the classed corpus and apply the **removal test** to every clause of every response: *if removing the clause changes nothing about what the client should do, it is context.* Verify **zero** context clauses survive to a client audience, zero `clinical_record`, `clinical_narrative` or `clinical_restricted` facts reach any client audience, and that the same corpus run at a staff or owner audience does return the withheld detail.

**Acceptance Scenarios**:

1. **Given** a verified client asking about their own pet, **When** Vera answers, **Then** she may state schedule facts — what is due, when, per the practice's own record — and nothing else.
2. **Given** any candidate clause in a client-facing response, **When** it is evaluated, **Then** a clause whose removal would not change what the client should do is classified as context and is withheld.
3. **Given** the same question from a staff, manager, or owner audience, **When** Vera answers, **Then** the clinical context is permitted, subject to that audience's class permissions.
4. **Given** an unverified caller, **When** they ask anything clinical at all, **Then** nothing clinical is revealed — including administrative clinical facts about a household they have not been verified into.
5. **Given** a client-audience response, **When** it is generated, **Then** it contains no value, trend, finding, interpretation, or recommendation drawn from any clinical class.

---

### User Story 5 — The Record, Held for Staff, Quoted to Nobody (Priority: P1)

The medication and vaccination history, the visits, the weights, the diagnostic requests and their status: ingested with full lineage, classed `clinical_record`, available to staff-and-above, and **explicitly marked non-citable** until Vera-core's snapshot-versioned resolution lands. Non-citable facts still work — they drive the overdue list, triage routing context, and internal ranking. They simply cannot appear as a sourced claim in a note, a briefing, or a client-facing statement.

**Why this priority**: This is the sequencing rule the whole cycle rests on — *013 may ingest clinical records before R5 lands; it may not make them citable.* Shipping citable-but-rewritable clinical references would break the published *"never state a fact it cannot source"* in the one place where breaking it is a legal event, and 012 reached the identical conclusion independently and quarantined itself for the same reason.

**Independent Test**: Verify every ingested clinical record carries an explicit non-citable marker; attempt to publish a sourced clinical claim in a note, briefing, or client statement and verify it is refused at the mechanism, not by prompt; verify a non-citable clinical fact still contributes to the overdue view and to routing; and verify citability is flippable **per class**, not per record, when R5 lands.

**Acceptance Scenarios**:

1. **Given** any ingested clinical record, **When** it is persisted, **Then** it carries an explicit citability state whose value pre-R5 is non-citable, and there is no per-record override.
2. **Given** a non-citable clinical fact, **When** any surface attempts to publish it as a sourced claim, **Then** the attempt is refused by the evidence mechanism itself.
3. **Given** the same fact, **When** the overdue view or a routing decision consults it, **Then** it is usable — held-and-useful is the whole point of the distinction.
4. **Given** R5 lands, **When** citability is enabled, **Then** it is enabled per sensitivity class as a policy change, and no local or parallel evidence mechanism was ever created in the meantime.
5. **Given** a diagnostic order, **When** Vera speaks about it, **Then** she may state that it was ordered, when, and whether a result has arrived — and never a value.

---

### User Story 6 — The Narrative, at the Strictest Class (Priority: P1)

The SOAP quartet — 19,511 rows of the veterinarian's own words: history, exam, assessment, plan. It comes in this cycle (R-1), classed `clinical_narrative`, readable by **licensed veterinarians and practice owners only** — not a CSR, not a manager who is not the owner, not a verified client, not an unverified caller — and, pre-R5, readable only as a **live read** labeled current-at-read-time, never captured into an artifact that outlives the read.

**Why this priority**: It is the difference between an envelope that holds the business of the practice and one that holds the practice, and it is the reason the operator planning 400 practices takes the pilot seriously. It is also the single most sensitive text in the delivery — verbatim diagnoses and plans in the vet's own words — so it ships at the strictest class the product has, and the class is enforced in policy data rather than in a prompt.

**Independent Test**: For each of the five audiences plus a licensed-veterinarian audience, request narrative content and verify it is returned **only** to the licensed veterinarian and the owner; verify a narrative read produces no persisted quote, note, or briefing line pre-R5; and verify an unclassed narrative row is treated as deny-all rather than as staff-visible.

**Acceptance Scenarios**:

1. **Given** SOAP narrative content, **When** any audience other than a licensed veterinarian or a practice owner requests it, **Then** it is withheld and the withholding is logged with its reason.
2. **Given** a licensed veterinarian reading a prior visit's narrative pre-R5, **When** it is rendered, **Then** it is labeled as a live read of current record state and no part of it is persisted into a note, briefing, receipt, or claim.
3. **Given** narrative content, **When** Vera speaks on any client channel, **Then** none of it appears in any form — including paraphrase, summary, or inference drawn from it.
4. **Given** narrative content and 012's note surface, **When** 012 generates a draft, **Then** 012 FR-032 remains in force — 013 makes lifting it possible at R5 and does not lift it here.

---

### User Story 7 — Nobody Hears From Vera About a Dead Patient (Priority: P1)

**175 animals are flagged `Dead`**, with dates and causes of death recorded. They also have overdue vaccinations. An overdue-vaccine reminder to a bereaved owner is not a defect report; it is the end of the relationship.

**Why this priority**: 011's existing handling excludes deceased patients only from soft-confirm *reason guesses*. After 013 the corpus contains due dates for animals that will never be due again. This is a hard suppression filter on every clinical projection — inbound answers included, not just outbound lists — and it is the failure a pilot practice would never forgive.

**Independent Test**: Load the practice with its 175 deceased animals and run every clinical surface — overdue view, client answer, staff answer, routing context — verifying **zero** clinical projections reference a deceased or source-deleted patient, and that end-of-life content (`Cause Of Death`, `Resuscitate` status — 16 DNR, 5 ALS) is classed `clinical_restricted` and never spoken on any channel.

**Acceptance Scenarios**:

1. **Given** a patient flagged `Dead`, **When** any clinical projection is generated, **Then** the patient is excluded before the projection exists, on every channel and in both directions.
2. **Given** a client of a deceased patient contacting the practice, **When** Vera responds, **Then** nothing due-related, clinical, or end-of-life is stated.
3. **Given** `Cause Of Death`, `Resuscitate`/DNR status, euthanasia and end-of-life content, controlled-substance records (883 rows across 31 products), or staff memos, **When** any audience requests them, **Then** they are `clinical_restricted` — a staff surface may hold them; **Vera never speaks them on any channel**.

---

### User Story 8 — The Export Tells Us What It Actually Has (Priority: P2)

`HealthStatusExport` looks like a vitals table. Its real fill is **Weight 98%, BCS 0%, PainScore 0%, DentalScore 0%, BloodPressure 0%**, Attitude 25%, MM 24%, HeartRate 20%, CRT 19%, Temperature 16%. `VisitExamExport.Body System Number` is **100% empty**. `DiagnosticResultExport.Interpretation Outcome` is **100% empty**. The problem list is **48 rows across 38 of 2,658 animals**. Each practice is profiled for what it actually populated, and nothing is built on a field that is not there.

**Why this priority**: n=1 of 23 practices. The capability ranking is a prior, not a fact — but the failure mode is asymmetric: designing on assumed fill produces a feature that silently answers nothing, and *filling* an empty interpretation column is the forbidden act itself. Profiling makes generalization a measurement rather than a bet, and lets a practice that does populate BCS light that capability up without a spec change.

**Independent Test**: Run the profile across the delivered practices and verify a per-practice clinical fill report exists; verify a capability gated on a field below the fill threshold is disabled for that practice with the reason recorded; and verify the pipeline emits no value into any field the source left empty.

**Acceptance Scenarios**:

1. **Given** a practice database, **When** it is profiled, **Then** a per-field clinical fill profile is produced and the group map is treated as a prior, not an assumption.
2. **Given** a field below the fill threshold at a practice, **When** capabilities are enabled, **Then** any capability depending on it is disabled there with the measured reason recorded.
3. **Given** `Interpretation Outcome`, `Body System Number`, or any other empty structured field, **When** the pipeline runs, **Then** it stays empty — generating clinician interpretation to fill it is prohibited permanently, at every autonomy level.
4. **Given** the weight series, **When** it is described anywhere — product, report, or marketing — **Then** it is described as weight with sporadic TPR, never as "vitals."

---

### User Story 9 — The Pipeline Survives the Volume, and Completeness Can See Clinical (Priority: P2)

Cycle-one clinical ingest is roughly **+129,000 rows per practice** on top of 009's 176,755 — about **3.0M additional rows across the 23-practice group**. The current path parses *every* CSV in the ZIP into memory, accumulates every canonical record with two dicts each, builds a parallel row list, and hands the whole thing to a single upsert. And `section5_scope.yaml` has no clinical category, so today a delivery with zero clinical files passes as complete.

**Why this priority**: Four of the substrate items are defects in shipped 009 code rather than new construction, and two of them (the missing clinical scope category, `Is Active`) are live correctness gaps whether or not 013 proceeds. Recall latency matters too: "Rex's last three weights" over a JSON payload column is a scan, which is why financials got typed read models in 009 and clinical needs the same.

**Independent Test**: Ingest the real Coastal Creek export end-to-end with the clinical subset enabled and verify: peak memory is bounded per entity rather than by total export size; only mapped entities are parsed; per-entity yield is asserted (an entity that profiles rows and normalizes none fails loudly); typed clinical read models exist with a `(practice_id, patient_ref, occurred_at)` index; the completeness result reports a clinical category; and a delivery stripped of its clinical files is reported **incomplete**.

**Acceptance Scenarios**:

1. **Given** a real export ZIP, **When** ingest runs, **Then** only entities present in the mapping are parsed, and no stage holds a full copy of the export in memory.
2. **Given** any mapped clinical entity that profiled rows but normalized zero, **When** ingest runs, **Then** it fails loudly per entity — a run where the original nine entities map and the clinical ones map nothing MUST NOT report success.
3. **Given** ingested clinical data, **When** a patient-scoped clinical recall is performed, **Then** it is served from a typed read model with a patient/time index, not by scanning a JSON payload column.
4. **Given** a delivery containing no clinical files, **When** completeness runs, **Then** the practice is reported incomplete against a clinical §5 category and a gap notice is produced.
5. **Given** dates in `MM-DD-YYYY` across three renderings with no timezone, `YES`/`NO` booleans, `0`/`1` booleans, and mixed-case enumerations (`DiagnosticResult` / `diagnosticresult`), **When** they are ingested, **Then** they are coerced through one layer with an explicit per-practice timezone, and anything unparseable is flagged rather than guessed.
6. **Given** 689 consults dated in 2027, **When** "last visit" or any time-ordered clinical recall is computed, **Then** future-dated rows are treated as scheduled, never as history.

---

### Edge Cases

- **A `Patient Code` resolves to two animals** (or an animal is source-deleted while its clinical children are live) → the clinical rows are flagged unresolvable and withheld; a clinical fact with ambiguous lineage is never persisted as fact.
- **A live clinical record hangs off a source-deleted consult** → the record survives on the patient spine (the consult was never the key); the deleted episode is not quoted.
- **An animal is marked `Dead` between deliveries** → the delta suppresses every projection for it immediately; suppression is not a scheduled job.
- **A practice populates BCS and pain scores** → the fill profile detects it and the capability enables for that practice only; the group prior is not rewritten from n=1 in either direction.
- **A DVM asks for a value Vera holds but cannot cite pre-R5** → she may confirm the record exists and its status, as a live read, and says plainly that she cannot yet source the value — never a silent omission and never an unsourced assertion.
- **A verified client asks a question whose honest answer is clinical** ("is Rex okay?") → routed to the practice's own triage protocol and to a human; routing is not diagnosis, and the refusal is a class check, not a tone choice.
- **A controlled-substance record is the direct answer to a staff question** → it is `clinical_restricted`; a staff surface may display it, Vera does not speak it, and no controlled-substance verb exists to act on it.
- **A field defect in the record** (wrong species, a typo'd weight) that a human asks Vera to fix → there is no correction verb, permanently. State record law requires amendments to carry date and author and forbids retroactive deletion; a Vera-authored amendment is not a feature that can be built safely.
- **A delta delivery re-ingests a record a prior claim referenced** → KI-1's blast radius; this is exactly why clinical facts are non-citable until R5 and why nothing quotes them in the meantime.
- **The mapping file's duplicated `source_files` block** (declared twice; the second wins) → harmless at 9 entities, a trap at ~30; consolidated as part of this cycle.

---

## Requirements *(mandatory)*

**Layer legend** — per *products share patterns, not resources*: **[P]** = pattern layer, shaped to lift cleanly into the platform pattern library (adoptable by FarmAgent herd-health and any future regulated-record vertical, each on its own substrate). **[V]** = vet-specific, stays in VetAgent. A shared *shape*, never a shared service.

### Substrate — Keying, Coercion, Deletion

- **FR-001** **[P]**: A **source-key resolution index** MUST exist such that clinical child records keyed on a denormalized code (`Patient Code` / `Contact Code`) resolve to the **same** canonical `entity_ref` that 009 builds from the primary id (`Animal Id` / `Contact Id`). This is a requirement with a test, not an implementation note.
- **FR-002** **[P]**: A clinical record whose subject cannot be resolved through that index MUST be flagged and MUST NOT be persisted as a clinical fact — no synthesized reference, no partial lineage, no best guess.
- **FR-003** **[V]**: The **patient is the spine**. Clinical facts MUST key on the patient; consult association MUST be optional metadata. Ingest MUST NOT require a consult id (56.7% of vaccinations, 45% of health-status rows, and 34.7% of medications have none).
- **FR-004** **[P]**: A single **type-coercion layer** MUST parse source values before persistence: US `MM-DD-YYYY` dates in all three delivered renderings, `YES`/`NO` booleans, `0`/`1` booleans, numerics, and case-variant enumerations. Unparseable values MUST be flagged, never guessed or silently defaulted.
- **FR-005** **[P]**: Every practice MUST carry an explicit **timezone** property; the source dates carry none, and every overdue computation depends on it.
- **FR-006** **[V]**: Future-dated source rows (689 consults dated 2027; 7,862 future events; 3,624 future vaccinations) MUST be treated as **scheduled**, never as history. "Last visit" and every time-ordered clinical recall MUST exclude them.
- **FR-007** **[P]**: **Source-system deletion MUST be a first-class concept in the adapter port.** A row marked `Is Active = NO` MUST be recorded as source-deleted and MUST NOT be recalled, quoted, counted in any derived figure, or included in any projection.
- **FR-008** **[P]**: Deletion MUST **propagate on delta**: a record that becomes source-deleted (or disappears) in a later delivery becomes non-recallable, with the change logged. Our copy is not the legal record and MUST NOT outlive the source record's live state. **[NEEDS CLARIFICATION: NC-1 — the customer-visible retention/return term for the clinical corpus (per-state floor across a multi-state group; deletion and return commitments). Blocks the first clinical contract, not this build. Owner: Matt + counsel.]**
- **FR-009** **[P]**: Ingest MUST parse **only mapped entities**, MUST aggregate unmapped-field tracking per `(entity, column)` rather than per row, MUST dedupe on the lineage key, and MUST enforce the empty-yield guard **per entity** — a mapped entity that profiles rows and normalizes zero MUST fail loudly rather than let a partially-successful run report success.
- **FR-010** **[P]**: Clinical ingest MUST be streamed/chunked **by entity**, with peak memory bounded per entity rather than by total export size, and MUST persist into **typed clinical read models** indexed on `(practice_id, patient_ref, occurred_at)` — never recalled by scanning a JSON payload column.
- **FR-011** **[V]**: A **clinical category** MUST be added to the §5 scope configuration and to the completeness scope map, such that a delivery containing no clinical files is reported **incomplete** and produces a gap notice. (009 SC-004 asserts clinical coverage that does not exist today.)
- **FR-012** **[V]**: The mapping file's duplicated `source_files` declaration MUST be consolidated as part of this cycle's mapping extension.

### Ingest Scope (cycle one)

- **FR-013** **[V]**: The cycle-one clinical ingest scope is exactly:

| Group | Entities | Rows (Coastal Creek) |
|---|---|---:|
| Vocabulary layer | Species 18 · Breed 769 · AnimalColour 117 · AppointmentType 56 · EventGroup 91 · EventGroupAssociation 528 · MasterProblem 3,722 · PresentingProblem 621 · Therapeutic 653 · Diagnostic 10,776 · ClinicalTemplating 85 · User 156 | 17,592 |
| Due/overdue engine | Event 32,014 · Vaccination 7,949 | 39,963 |
| Episode spine | Consult 8,243 · Revisit 391 | 8,634 |
| Medication history | Medication 16,520 | 16,520 |
| Weight series | HealthStatus 6,779 | 6,779 |
| Problem / therapeutic links | AnimalMasterProblem 48 · PlanTherapeutic 8,339 | 8,387 |
| Diagnostic headers | DiagnosticRequest 5,029 · DiagnosticResult 7,081 | 12,110 |
| **SOAP narrative (R-1)** | VisitHistory 5,510 · VisitExam 4,295 · ConsultAssessment 4,226 · ConsultPlan 5,480 | 19,511 |
| **Total** | | **129,496** |

- **FR-014** **[V]**: `DiagnosticResultItemExport` (262,370 rows) is **OUT**. No diagnostic result **value** may be ingested this cycle. The Request/Result **headers** are in, so Vera can speak to order and arrival status without touching a number.
- **FR-015** **[V]**: `DocumentExport`, `MemoExport`, `TagExport`, `InClinicExport` and Wellness are **OUT** as capabilities; `MemoExport` content, if ever ingested, is `clinical_restricted` with no client path, ever.
- **FR-016** **[V]**: `User` plus consult case owners MUST close 009's `providers: derive_from_consults_and_appointments` gap — 10 distinct case owners exist in the real export.
- **FR-017** **[P]**: The system MUST NEVER generate clinician **interpretation**. `Interpretation Outcome` is 100% empty in the source and MUST remain empty; deriving, inferring, or characterizing an interpretation is prohibited permanently, at every autonomy level. The same applies to `Body System Number` and every other structurally empty field.
- **FR-018** **[P]**: There MUST be **no write, correction, or amendment verb into the clinical record — permanently, not just this cycle.** The verb does not exist rather than being gated.

### Sensitivity Classing (extends 011, does not fork it)

- **FR-019** **[P]**: Reveal policy MUST gain a **sensitivity class dimension orthogonal to audience**, expressed as an extension of 011's `memory_scoping` policy data. Four classes ship:

| Class | Contents | `caller_unverified` | `client_verified` | `staff` / `manager` | `owner` | licensed **veterinarian** |
|---|---|---|---|---|---|---|
| `clinical_administrative` | due/overdue, visit dates, result-arrived status, refills-remaining count, prior-reminder history | deny | **allow** (own household, schedule facts only — FR-024) | allow | allow | allow |
| `clinical_record` | medication & vaccination detail, weights, problems, diagnostic headers, visit/episode detail | deny | deny | allow | allow | allow |
| `clinical_narrative` | verbatim S/O/A/P narrative (R-1) | deny | deny | **deny** | **allow** | **allow** |
| `clinical_restricted` | controlled-substance records (883 rows / 31 products) · euthanasia & end-of-life · `Resuscitate`/DNR status (16 DNR, 5 ALS) · `Cause Of Death` · staff memos | deny | deny | staff surface only | staff surface only | staff surface only — **Vera never speaks it on any channel** |

- **FR-020** **[P]**: Every ingested clinical record MUST carry **exactly one** sensitivity class, assigned at ingest. An unclassed clinical fact MUST be treated as `clinical_restricted` (deny-all) — never as default-allow.
- **FR-021** **[V]**: The `clinical_narrative` class MUST reveal only to a **licensed-veterinarian** or **practice-owner** audience. The licensed-veterinarian distinction MUST derive from the staff role record (011's `clinic_staff_role` shape), never from a shared login. **[NEEDS CLARIFICATION: NC-2 — whether a credentialed veterinary technician may be admitted to `clinical_narrative` per practice. Cycle one ships DVM+owner only; default-deny makes shipping behavior correct either way. Owner: Matt.]**
- **FR-022** **[P]**: Every reveal **and** every withholding of a clinical fact MUST be logged with its audience, class, and reason (extending 011's existing logging, not forking it).
- **FR-023** **[P]**: 011's red-team suite MUST be **regenerated against the clinical corpus** and MUST pass with zero scoping violations **before any client-facing clinical reveal ships**. The existing corpus does not contain the answer to "what's wrong with the dog" and is not evidence for this cycle.

### The Speech Line (R-2)

- **FR-024** **[V]**: To a client audience, Vera MAY state **schedule facts** — what is due, when, per the practice's own recorded protocol — and nothing further.
- **FR-025** **[P]** *(the removal test)*: A candidate clause in a client-facing response whose removal would **not change what the client should do** is **clinical context** and MUST be withheld. The test MUST be applied mechanically to generated client-facing responses, not left to phrasing judgment.
- **FR-026** **[V]**: Vera MUST NOT compute, infer, or supply what a patient is due for. Due status MUST derive solely from the practice's own recorded due dates and event-group intervals. No guideline, no interval of Vera's own, no protocol reasoning.
- **FR-027** **[V]**: No client-audience response may contain a diagnostic value, a trend, an exam finding, an interpretation, a characterization ("that's high", "that's normal"), a differential, a prognosis, a treatment plan, a dose, a drug selection, or any statement that would imply a VCPR — drawn from any class, in any form, including paraphrase and summary.
- **FR-028** **[V]**: Deceased-patient suppression MUST be a **hard filter applied before any clinical projection exists** — outbound and inbound, every channel. Every clinical projection filters on `Dead`, source-deleted, and account status.

### Citability (Vera-core R5 / R2)

- **FR-029** **[P]**: Every clinical canonical record MUST carry an explicit **citability state**, whose value is **non-citable** until snapshot-versioned reference resolution (contract **R5**) lands. There is no per-record override.
- **FR-030** **[P]**: A non-citable clinical fact MUST NOT appear as a **sourced claim** in a note, briefing, receipt, report, or client-facing statement — enforced by the evidence mechanism, not by prompt. It MAY inform the overdue view, routing, and internal ranking.
- **FR-031** **[P]**: Pre-R5, `clinical_narrative` content MAY be surfaced to a permitted audience only as a **live read**, explicitly labeled as current record state at read time, and MUST NOT be persisted into any artifact that outlives the read.
- **FR-032** **[P]**: When R5 lands, citability MUST flip **per sensitivity class** as a policy change, never per record.
- **FR-033** **[P]**: Every **derived** clinical claim (the overdue counts first among them) MUST persist its **contributing reference set** alongside the figure (contract **R2**). A derived clinical figure without a traceable input set MUST NOT be published.
- **FR-034** **[P]**: 013 MUST NOT create a parallel or local evidence mechanism. If R5 or R2 slip, the affected capability ships with the sourced-claim surface **visibly absent**, never with a second mechanism.
- **FR-035** **[V]**: 012's FR-032 (no citations into the practice record) **remains in force**. 013 makes lifting it possible at R5; it does not lift it here.

### The Recall Engine (capability #1)

- **FR-036** **[V]**: The system MUST produce a per-practice **due/overdue view** from Event, EventGroup, EventGroupAssociation, Vaccination and medication-refill fields, using the practice's own recorded due dates.
- **FR-037** **[V]**: The view MUST be cross-filtered against deceased patients, source-deleted records, closed accounts, and **prior outreach already recorded in the communications export** — showing what was already chased and when.
- **FR-038** **[P]**: The view MUST reach **owner/manager surfaces only** and MUST produce zero staff-facing artifacts (Working Rule 0; 009 FR-029).
- **FR-039** **[P]**: 013 adds **no verbs**. No autonomous outbound recall, campaign, or client contact ships this cycle; the list is a KNOW artifact and Vera answers administrative due questions when asked.

### Honesty About the Data

- **FR-040** **[P]**: Each practice MUST be profiled for **per-field clinical fill**, with the group map treated as a prior (009 FR-026). A capability depending on a field below the fill threshold MUST be disabled for that practice with the measured reason recorded.
- **FR-041** **[V]**: `HealthStatus` MUST be modeled, described, and marketed as a **weight series with sporadic TPR** (Weight 98%; BCS/PainScore/DentalScore/BloodPressure 0%) — never as "vitals."
- **FR-042** **[V]**: The problem list MUST be ingested as **vocabulary only**. `MasterProblem` (3,722) is a catalog; `AnimalMasterProblem` is **48 rows across 38 of 2,658 animals**. No capability, claim, or price may assume Vera knows a patient's chronic conditions.
- **FR-043** **[V]**: Controlled substances MUST be a **fenced data class** (883 medication rows on 31 flagged products; 1,222 prescription-required products), not a filter — the prohibition moves from "no such verb in the catalog" to "a data class with no reveal path."
- **FR-044** **[P]**: Any figure derived rather than sourced MUST **say so where it is stated** (the standing 2026-07-29 ruling recorded in the mapping config, generalized to clinical facts).

---

## Key Entities

- **ClinicalFact**: Any ingested clinical record — medication, vaccination, event, health status, consult, therapeutic, diagnostic header, narrative section. Carries `entity_ref` lineage, patient reference, occurrence timestamp, sensitivity class, citability state, and source-deleted state.
- **SourceKeyIndex**: The Code→Id resolution index that makes a clinical child's patient reference identical to 009's `Animal Id`-keyed `patient` `entity_ref`. Without it every clinical lineage is silently wrong.
- **SensitivityClass**: `clinical_administrative` · `clinical_record` · `clinical_narrative` · `clinical_restricted` — a dimension **orthogonal to** 011's five audiences, expressed in the same `memory_scoping` policy data.
- **SourceDeletion**: The first-class record that the source system marked a row inactive — the state that makes a fact unrecallable without erasing the evidence that it existed.
- **CoercionResult**: The parsed value plus its parse disposition (parsed / flagged-unparseable) for dates, booleans, numerics and enumerations. The layer every overdue computation depends on.
- **ClinicalFillProfile**: Per-practice, per-field measured fill — the artifact that turns "do Coastal Creek's fill rates generalize?" into a measurement and gates capability enablement.
- **DueEvent / RecallItem**: One patient-and-item due or overdue per the practice's own record, with its prior-outreach history, suppression disposition, and (for any derived total) its contributing reference set.
- **OverdueView**: The per-practice owner/manager artifact — the recall list, cross-filtered, with derived figures carrying their input sets.
- **NarrativeSection**: One S/O/A/P section of a consult, `clinical_narrative`-classed, DVM/owner-only, live-read-only pre-R5.
- **CitabilityState**: Per-record marker (non-citable pre-R5), flipped per class when snapshot-versioned resolution lands.
- **ClinicalScopeCategory**: The §5 category that makes clinical completeness measurable — and makes a clinical-free delivery fail rather than pass.
- **RevealDecision**: The logged reveal-or-withhold with audience, class, and reason — the audit surface the red-team suite is scored against.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: **100%** of ingested clinical records resolve to the same `patient` `entity_ref` 009 builds from `Animal Id`; **0** clinical records are persisted with an unresolved, synthesized, or partial subject reference.
- **SC-002**: **0** source-deleted (`Is Active = NO`) rows are ever recalled, quoted, projected, or counted in a derived figure — verified against the export's real deleted population (817 consults, 1,284 medications, 135 animals), and **100%** of deletions arriving in a delta propagate to non-recallable.
- **SC-003**: **100%** of ingested clinical records carry exactly one sensitivity class at ingest; **0** unclassed clinical facts are revealed to any audience.
- **SC-004**: **0** scoping violations across the **regenerated** clinical red-team suite, at the 011 SC-001 bar — including **0** reveals of `clinical_record`, `clinical_narrative`, or `clinical_restricted` facts to any client audience, and **0** `clinical_narrative` reveals to any audience other than a licensed veterinarian or practice owner.
- **SC-005**: **0** clinical-context clauses survive to a client audience under the removal test, measured on an adversarial corpus; **100%** of the same withheld details are returned at staff/owner audiences (the partition is a line, not a mute button).
- **SC-006**: **100%** of clinical records carry a non-citable marker pre-R5; **0** sourced clinical claims are published before R5; **0** parallel evidence mechanisms exist.
- **SC-007**: **100%** of derived clinical claims — the overdue counts first — persist their contributing reference set; **0** derived clinical figures are published without one.
- **SC-008**: An overdue view is produced for **100%** of ingested practices (Coastal Creek baseline: 8,303 overdue events + 4,325 overdue vaccinations), with **0** entries for deceased, source-deleted, or closed-account patients and **100%** of already-chased items showing their prior outreach date.
- **SC-009**: **0** clinical projections of any kind — inbound answer or outbound list, on any channel — reference a deceased patient (175 at Coastal Creek); **0** `clinical_restricted` facts are spoken by Vera on any channel.
- **SC-010**: Completeness reports a **clinical** category for **100%** of practices; **0** deliveries containing no clinical files pass as complete, and each produces a gap notice.
- **SC-011**: **100%** of ingested date fields are parsed through the coercion layer into timezone-explicit timestamps with an explicit per-practice timezone; **0** values are silently defaulted or guessed; **0** future-dated rows appear in any "last visit" or historical computation.
- **SC-012**: The cycle-one clinical subset (~129,500 rows/practice; ~3.0M across 23) ingests within the existing onboarding window (009 SC-007 unchanged: first practice shadow-ready within ~1 week of receipt), with peak memory bounded per entity rather than by export size, and **0** unmapped entities parsed.
- **SC-013**: Patient-scoped clinical recall (e.g. a patient's medication history or weight series) returns at **p95 under 2 seconds** from a typed read model; **0** clinical recalls scan a JSON payload column.
- **SC-014**: **0** clinician interpretations are generated (`Interpretation Outcome` remains 100% empty); **0** writes, corrections, or amendments into the clinical record exist as capabilities; **0** controlled-substance verbs exist.
- **SC-015**: **100%** of practices have a clinical fill profile, and **0** capabilities are enabled at a practice on a field below the measured fill threshold.

---

## Non-Goals (this cycle)

- **`DiagnosticResultItemExport` and every diagnostic result value** — 262,370 rows, 77% source-deleted, only 48% of live items carrying a reference range, and the single hardest thing to reveal safely. Revisited in cycle two behind streaming ingest, typed read models, and R5. Status and timing ship; numbers do not.
- **Any clinical interpretation, characterization, diagnosis, prognosis, differential, treatment plan, dose calculation, drug selection, or controlled-substance action** — at any autonomy level, on any channel, for any audience. Not deferred: **absent**.
- **Any write, correction, or amendment into the clinical record** — permanently, not just this cycle. The practice owns the record.
- **Autonomous outbound recall, campaigns, or client contact.** 013 produces the list; verb promotion is a separate gate and a separate spec.
- **Citable clinical facts before R5**, and any lift of 012's FR-032. 013 makes the lift possible; it does not perform it.
- **"Vera knows your patients' chronic conditions."** The problem list is 48 rows across 38 of 2,658 animals. This is not a capability this data supports, and it must not be sold, priced, or demoed as one.
- **"Vera tracks your patients' vitals."** BCS, pain score, dental score and blood pressure are 0% populated. It is a weight series with sporadic TPR.
- **`DocumentExport`, `MemoExport`, `TagExport`** as capabilities; any client-audience path to staff-internal correspondence, ever.
- **Any client-audience reveal of a `clinical_record`, `clinical_narrative`, or `clinical_restricted` fact**, and any marketing of clinical knowledge before the regenerated red-team suite passes.
- **A second PIMS clinical adapter**, clinical decision support, triage-rule changes (010), and any staff-facing clinical UI (Working Rule 0).

---

## Platform-Common

Registered back to COS-platform as **patterns**, per *products share patterns, not resources* — vendored as source, never as a shared service or a shared store.

- **`sensitivity-classed memory scoping`** — the finding that per-audience default-deny becomes insufficient once a corpus contains facts of categorically different sensitivity about the *same* subject, and that the fix is a **class dimension orthogonal to audience** rather than more audiences. "Rex is due for rabies" and "Rex's creatinine was 3.8" concern the same patient in the same household and must land on opposite sides of the client line. Generalizes to any vertical ingesting a regulated record (FarmAgent herd-health; any future professional vertical). The vertical supplies the classes and the audience map; the pattern supplies the shape and the default-deny-on-unclassed rule.
- **`ingest soft-deletes are correctness, not hygiene`** — 77% of the largest table in a real delivery being `Is Active = NO` is the strongest available evidence for making **source-system deletion a first-class concept in the adapter port**, rather than a per-adapter afterthought. Deletion must propagate on delta, and a deleted fact must become unrecallable without erasing the evidence that it existed.
- **Filed against the Vera-core evidence contract**: clinical use of **R5** (snapshot-versioned resolution — the gate on citability) and **R2** (a claim cites a *set* of references — the gate on every derived clinical claim, starting with the recall list). No new contract requirements are originated here; 013 consumes and reports.

| Pattern layer (lifts) | Vet layer (stays) |
|---|---|
| Sensitivity class × audience reveal policy, default-deny on unclassed | The four vet classes and what falls in each |
| Source-deletion as an adapter-port concept, propagating on delta | `Is Active` / `YES`-`NO` ezyVet semantics |
| Source-key resolution index (denormalized code → canonical id) | `Patient Code` → `Animal Id` |
| Type-coercion layer with flag-don't-guess and explicit tenancy timezone | US `MM-DD-YYYY` three-rendering parsing |
| Per-entity yield guard, mapped-entities-only parsing, aggregated unmapped tracking | — |
| Measured fill profiling gating capability enablement | The vet fill findings (BCS 0%, problem list 48 rows) |
| The removal test for regulated-context speech | The administrative/clinical line, AAVSB decision-involvement, VCPR |
| Held-not-citable state pending versioned evidence | Clinical record law, amendment rules, retention patchwork |

---

## Assumptions & Dependencies

- **Every number in this spec is computed from Coastal Creek Animal Hospital's real §5 delivery (2026-07-29)** — 45 CSVs, 618,109 rows — not assumed. Confidence is **HIGH** on the entity graph, volumes and data-quality findings, **MEDIUM** on cross-practice generalization (**n=1 of 23**, which is why FR-040 exists).
- **Scope arithmetic, flagged**: the discovery's headline of "~96k rows/practice" **undercounts its own enumerated groups**, which sum to **109,985**; with the SOAP quartet added per R-1 the cycle-one total is **129,496 rows/practice** (~3.0M across 23 practices, a floor — Coastal Creek is small-to-mid with only ~2.5 years of exported history). The entity table in FR-013 is authoritative, not the headline.
- **Vera-core evidence contract — hard dependency, but not a blocker for the cycle's highest-value capability.** **R5** gates clinical *citability*; **R2** gates every derived clinical claim. The recall engine quotes nothing and needs neither, which is why it ships first. If either slips, the affected surface ships visibly absent (FR-034).
- **009 is the substrate and it has two known defects that bind here.** KI-1 (re-ingest silently rewrites what a reference resolves to) is the entire reason clinical facts ship non-citable; KI-2 (derived claims persist results without their input set) is why the recall list needs R2. Both must sequence **with** the contract, never around it. Four further correctness gaps in shipped 009 code (soft deletes, coercion, code-keying, missing clinical scope category) are fixed here and are worth fixing regardless of 013.
- **011 is extended, not forked.** Same five audiences, same `memory_scoping` policy data, same default-deny, plus a class dimension and a licensed-veterinarian distinction derived from `clinic_staff_role`.
- **012 is downstream.** 013 is the only path by which 012's FR-032 prohibition on practice-record citations is ever lifted, and it is not lifted this cycle.
- **Counsel gate**: 009 FR-004's hard gate on the clinic-owned-data structure covers normalization of the clinical entities; the legal basis is unchanged (the clinic's statutory ownership of its own records, exercised via the §5 request). NC-1's retention/return term rides the same counsel channel and does not block the build.
- **Regulatory posture** is the AAVSB's own line — **decision-involvement**, not data-sensitivity. Routine administrative use (reminder generation) is explicitly blessed; anything involved in decision-making or direct patient interaction carries a much higher bar. Source: AAVSB, *Regulatory Considerations of the Use of AI in Veterinary Medicine* (March 2025), read first-hand. State record law is a patchwork: the practice owns the record, amendments carry date and author, entries are not retroactively deleted, retention runs 1–7+ years with no federal baseline.
- **The published won't-do list is binding product behavior**, not copy. Four of its eight commitments are load-bearing here: never diagnose/prescribe/alter a treatment plan; never sign a medical record; never give a client medical advice over the phone; **never state a fact it cannot source** — the one this cycle threatens most, and the reason for FR-029.
- **Nothing in the export is signed** (`Document Is Signed` = YES on 0 of 2,294 documents). Whatever "the veterinarian's signed legal record" means for the pilot, the export does not carry the signature evidence — do not claim it does.
- **Pilot week-1 ground truth**: profile 2–3 more of the 23 databases against Coastal Creek's fill rates before capability ranking is treated as fact; validate the overdue list with a practice before anyone believes 8,303 is actionable rather than merely true.
- **Appetite**: medium (~4–6 weeks). The substrate half is largely mechanical defect repair; the classing half is a **security boundary** and must be red-teamed, not reviewed.

---

## Constitution Check

- **KNOW / ADVISE / DECIDE**: 013 is **pure KNOW**. It adds no verbs. Every capability it unlocks is retrieval or a due-list; the licensed acts remain absent from the catalog rather than gated in it.
- **Expert Firewall**: strengthened. The controlled-substance and interpretation prohibitions move from "not in the tool catalog" to "a fenced data class with no reveal path" — a statement about the store, not just the verbs.
- **Claim discipline**: the reason clinical facts ship non-citable until R5 and the reason every derived clinical figure carries its input set. Shipping citable-but-rewritable clinical references would break the published *"never state a fact it cannot source"* in the one place where breaking it is a legal event.
- **Invisible adoption (Working Rule 0)**: 013 produces no staff-facing artifact. The overdue view is an owner/manager surface (009 FR-029).
- **Products share patterns, not resources**: two patterns registered back as shapes; VetAgent keeps its own substrate, its own classes, and its own adapters.

---

## Marketing Output
**Produced by**: speckit-specify — 2026-07-29

### Feature Brief

**Consumer-Friendly Feature Name**: Vera Knows When They're Due — and Knows Where She Stops

**Key Benefits** (in customer language):
1. **The recall list your PIMS has been computing and nobody has been running.** At one practice: 8,303 overdue reminders and 4,325 overdue vaccinations, already cross-checked against who you contacted and who has passed away, so the list is one you would actually send.
2. **She reads your records; she never writes in them.** Nothing Vera does can add, change, or amend a line in your chart — not because we promise it, because the ability does not exist.
3. **The same Vera who tells a client their dog is due for a booster cannot tell them the lab result** — and the reason is a database rule, not a prompt.

**One-Line Description** (≤25 words): Vera reads your practice's own records to run your recall list — and stops, mechanically, at the line where answering would become practicing.

**Positioning Message Seed**: **"She knows where she stops."** — *Vera reads your practice's own records to run your recall list. She will never read a client a diagnosis, and she will never write a word into your chart.*

**Why-Now Angle**: Every overlay competitor answers the phone; none of them holds the medicine, because holding it requires being outside the PIMS and getting the record honestly. The published won't-do list becomes **provable rather than promised** at exactly the moment Vera *could* say the forbidden thing and structurally does not.

**Differentiation Source**: **Per-fact sensitivity classing over an ingested clinical record.** A PIMS-bound AI structurally cannot make this promise, because it *is* the record — it cannot promise not to write into itself. Second source: the recall engine runs on the practice's *own* recorded due dates, so it is the practice's protocol being worked, not a vendor's opinion about what a patient needs.

**Guidance note**: Sell the **stopping point** and the **recall list**. Keep ezyVet unnamed (ToS §4.1 posture, Working Rule 2). Never say "Vera knows your patients' medical history" until the regenerated red-team suite passes; never say "vitals" (it is a weight series); never imply Vera knows chronic conditions (48 problem-list rows across 38 of 2,658 animals).

**Claim-check**: two `verified-claims.md` entries required before external use. **"Vera will never write into your chart"** is a **PRODUCT-CLAIM** — true only once absent-verb enforcement and FR-018 ship. **"The only veterinary assistant with per-fact clinical sensitivity classing"** is a **negative claim about competitors** — file as PENDING with the competitive scan cited and a re-check cadence.
