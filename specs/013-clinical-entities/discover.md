# Discovery: Clinical Entities — "Vera Learns the Medicine"

**Feature type**: capability extension on a shipped surface (009's envelope ingest) — not a new product surface. Customer-visible through the *capabilities it unlocks*, not through a screen.
**Appetite**: medium (~4–6w for the recommended subset; large if scoped to all 44 entities, which is the recommendation this doc argues against)
**Passes run**: 0, 1, 2 (repo read · real-export schema/relationship verification · regulatory + audience binding)
**Artifact confidence**: **HIGH** on the entity graph, volumes, and data-quality findings (every number below is computed from Coastal Creek Animal Hospital's real delivery, 2026-07-29, not assumed); **MEDIUM** on cross-practice generalization (n=1 practice profiled of 23); **MEDIUM** on the regulatory line (AAVSB whitepaper read first-hand in-repo; state-by-state record law is a patchwork)
**Date**: 2026-07-29

---

## Customer Artifacts

**Human-provided:**
- Dr. Goldsmith / Synergy Vets §5 delivery — 23 practice databases; Coastal Creek is the first profiled. The clinical files are *in the delivery already*. Nobody has to ask for them again (subject to Q2 below).
- Matt's ruling 2026-07-29 (recorded in `ezyvet_mapping.complete_v1.yaml`): where a figure is derived rather than sourced, **say so in the report**. That ruling generalizes directly to clinical facts and is treated as binding here.
- The published won't-do list (`marketing/what-vera-will-never-do.md`) — client-facing, four of whose eight commitments are load-bearing on this spec.

**Agent-sourced (persisted):**
- AAVSB, *Regulatory Considerations of the Use of AI in Veterinary Medicine* (March 2025), read first-hand and summarized in `VetPractice/research/v02/l0-firsthand-regulatory.md`. The administrative/clinical line is the regulators' own line, quoted.
- AVMA Model Veterinary Practice Act + state record rules: the practice owns the record; amendments must be marked with date and author; entries are not retroactively deleted; retention 1–7+ years, no federal baseline. ([AVMA MVPA](https://www.avma.org/resources-tools/avma-policies/model-veterinary-practice-act), [state survey](https://co.vet/post/veterinary-medical-records-laws/), [FL 474.2165](https://www.lawserver.com/law/state/florida/statutes/florida_statutes_474-2165))
- Envelope strategy board §VCPR: "the Expert Firewall handles *don't prescribe*; it does **not** obviously handle *don't give advice that implies a VCPR*" — state-by-state, multiplied across a 23-clinic group.

---

## System Reality

### Files / components read
- `specs/009-vera-envelope-onboarding/{spec,data-model,known-issues}.md` — the on-ramp, its canonical spine, and the two defects that bind here.
- `config/envelope/ezyvet_mapping.complete_v1.yaml` — the 9-entity map, the `source_files` real-filename aliases, and the `source_absent` block (note: `source_files` is **declared twice** in the file; the second wins — harmless today, a trap when 013 adds ~20 more entries).
- `config/envelope/section5_scope.yaml` — six §5 categories. **None of them is clinical.** See Surprise 5.
- `backend/envelope/{normalizer,completeness,quality}.py`, `backend/envelope/pims/ezyvet_adapter.py` — what 013 must extend, and the exact places where 013's volume breaks it.
- `specs/011-relationship-memory/spec.md` — five audiences, default-deny, `memory_scoping` policy data.
- `specs/012-vera-notes/spec.md` (worktree `/tmp/wt-vetagent-012`) — FR-032 and clarification Q9: citations into the practice record are **prohibited** in 12a, explicitly because of 009's KI-1. 013 is the spec that either lifts that or leaves it permanently in place.
- `/home/matt/Downloads/coastalcreek_backup/` (read-only) — 45 CSVs, 618,109 rows, schema + relationships computed directly.

### The real export, by the numbers

| | rows | share |
|---|---:|---:|
| Whole delivery (45 files) | **618,109** | 100% |
| The 9 entities 009 ingests | 176,755 | 28.6% |
| The 22 clinical files 009 flags-not-drops | **392,516** | **63.5%** |

**The medicine is the majority of the export by volume, and it is the part that was skipped.** `DiagnosticResultItemExport` alone (262,370 rows) is 1.5× everything 009 currently ingests.

### Verified entity relationship graph

Computed from the real columns, not assumed. Percentages are resolution rates against the parent key's actual universe.

```
Animal (2,658)  ─────────────────── THE SPINE. 100% resolvable from every clinical file.
  │
  ├─ Medication (16,520)  →Animal 100% · →Consult 65.3% · →Product 100%
  ├─ Vaccination (7,949)  →Animal 100% · →Consult 43.3%
  ├─ HealthStatus (6,779) →Animal 100% · →Consult 55.0%
  ├─ Event (32,014)       →Animal 100% · →EventGroup 100%     [the due/recall engine]
  ├─ PlanTherapeutic      →Animal 100% · →Consult 100%
  └─ AnimalMasterProblem (48) →Consult 70.8%

Consult (8,243)  ────────────────── THE EPISODE. Patient Id →Animal Id 100%.
  ├─ VisitHistory (5,510)      →Consult 100%   [S]
  ├─ VisitExam (4,295)         →Consult 100%   [O]
  ├─ ConsultAssessment (4,226) →Consult 100%   [A]
  ├─ ConsultPlan (5,480)       →Consult 100%   [P]
  ├─ Revisit (391)             →Consult 100%
  └─ DiagnosticRequest (5,029) →Consult 100%
        └─ DiagnosticResult (7,081) →Request 98.2%
              └─ DiagnosticResultItem (262,370) →Result 100%, mean 42 items/result, max 648

Catalogs (join targets, not events):
  Diagnostic (10,776 — test definitions, 16 suppliers) · MasterProblem (3,722)
  PresentingProblem (621) · Therapeutic (653) · EventGroup (91) · Breed (769)
  Species (18) · AnimalColour (117) · ClinicalTemplating (85) · User (156)
```

**Three graph facts that change the design:**

1. **The patient is the spine; the consult is not.** 34.7% of medications, 45% of vitals and **56.7% of vaccinations carry no Consult Id at all** — they were entered outside a visit (historical records, walk-in boosters, back-entered history). Any clinical model rooted in the consult loses roughly half the medicine. `Animal Id` resolves 100% everywhere.
2. **The clinical child files key on `Patient Code` / `Contact Code`, not `Patient Id` / `Contact Id`.** Every clinical export except `ConsultExport` carries the same denormalized 11-column header block using *Codes*. 009's `patient` `entity_ref` is keyed on **`Animal Id`**. Both resolve 100% against `AnimalExport` (ids=2,658, codes=2,658), so the join is available — but only through a Code→Id index that does not exist today. Without it, every clinical record's patient lineage is silently wrong.
3. **`DiagnosticExport` is a catalog, not results.** 10,776 rows, 10,776 distinct ids, 10,573 distinct names, 16 suppliers. It was listed in the brief as clinical volume; it is the test-definition dictionary. The actual result chain is Request → Result → ResultItem.

### Surprises

1. **Soft deletes are 77% of the biggest table, and the current normalizer ingests them all.** `DiagnosticResultItemExport`: 201,233 of 262,370 rows are `Is Active = NO`. Only **61,137 are live**. `Is Active` is also NO on 817 consults, 1,284 medications, and 135 animals. The adapter has no concept of it. Ingesting a deleted lab value as a citable fact is the medical-record form of KI-1 — the practice deleted it, and Vera would quote it back.
2. **The structured clinical fields the schema promises are mostly empty.** `HealthStatusExport` looks like a vitals table (BCS, pain score, dental score, HR, RR, weight, BP, temp, CRT, MM). Actual fill: **Weight 98%, BCS 0%, PainScore 0%, DentalScore 0%, BloodPressure 0%**, Attitude 25%, MM 24%, HeartRate 20%, CRT 19%, Temperature 16%. It is a weight-tracking table with sporadic TPR. Likewise `VisitExamExport.Body System Number` is **100% empty**, and `DiagnosticResultExport.Interpretation Outcome` is **100% empty** (Outcome 88.9% empty). *There is no captured clinician interpretation anywhere in the export.* Anything resembling interpretation would have to be generated — which is precisely the forbidden act.
3. **The problem list is effectively unused.** `MasterProblemExport` has a 3,722-entry catalog; `AnimalMasterProblemExport` has **48 rows across 38 animals** out of 2,658. Chief complaint is free text too: 4,529 distinct `Presenting Description` strings across 8,243 consults, of which **18** match the 621-entry `PresentingProblem` catalog. "Vera knows the chronic conditions" is not a capability at this practice, and pricing/marketing must not assume it.
4. **The due/overdue engine is fully populated and nobody is using it.** `EventExport` (32,014 rows, 100% →Animal, 100% →EventGroup, 91 groups): **8,303 overdue, 7,862 future-dated**. `VaccinationExport`: **4,325 overdue, 3,624 future**. `EventGroupAssociationExport` (in `Products/`) maps product → event group → next-due-in-seconds. And `CommunicationExport` already shows what was chased: `For Class` = Vaccination 3,197 / Medication 2,785. Vera can see who is overdue, for what, and whether they were already contacted — the highest-value clinical capability in the delivery, and it sits entirely inside the AAVSB-blessed administrative lane.
5. **§5 scope-check has no clinical category, so a delivery with zero clinical files would pass as complete.** `section5_scope.yaml` enumerates six categories (`patient_client`, `scheduling`, `invoicing_billing_payments`, `communications`, `attachments_imaging`, `configuration`) and none of them names a clinical source entity. Spec 009 SC-004 asserts completeness "covers clinical, scheduling, communications, and financial/AR/inventory." It does not. This is a live gap in a shipped gate, independent of whether 013 proceeds.
6. **Nothing in the export is signed.** `DocumentExport`: 2,294 documents, 2,294 with content, **`Document Is Signed` = YES on zero of them**. Whatever "the veterinarian's signed legal record" means for the pilot, the export does not carry the signature evidence.
7. **Dates are US `MM-DD-YYYY` with three renderings and no timezone** (`… 9:99:99p` 3,463 · `… 99:99:99` 2,420 · `… 9:99:99a` 2,360). Booleans are `YES`/`NO` strings — except `DOB estimated`, which is `0`/`1`. `AttachmentExport.Record Type` carries both `DiagnosticResult` (3,447) and `diagnosticresult` (3,068). The adapter copies raw strings; there is no coercion layer. Every "overdue" computation in this spec depends on one that does not exist yet.
8. **689 consults (8.4%) are dated 2027** — future. ezyVet appears to create consult rows for booked-but-not-yet-happened visits. `MAX(Consult DateTime)` = 2027-12-13. "Last visit" is wrong for ~1 in 12 patients unless future-dated shells are filtered.
9. **Controlled substances are already in the data.** 31 products flagged `Product Is Controlled Drug`; **883 medication rows (5.3%) sit on them**; 1,222 products require a prescription. The Expert Firewall's "no controlled-substance verb" is currently a statement about the tool catalog. Once 013 lands, it is also a statement about a *data class that exists in the store* and must be fenced, not filtered.

### External Dependencies
- **Vera-core evidence contract, requirement R5** (snapshot-versioned reference resolution) — the hard gate on clinical *citability*. R2 (claim cites a **set** of references) is the gate on clinical *derived* claims.
- 011's `memory_scoping` policy data — 013 extends it, and must not fork it.
- 012's citation surface — 013 is the only path by which 012's FR-032 prohibition is ever lifted.
- Counsel: the §5 clinical-scope question (Q2) and the AAVSB decision-involvement threshold (Q3).

---

## JTBD

**Job statement**: *"When my staff or my client asks Vera something about an animal, I want her to answer from my own records — what we gave it, what it's due for, what we found, and when — with the source one tap away, and I want her to stop dead at the line where answering becomes practicing. Right now she can tell me what they owe and when they're booked, but not what's wrong with the dog, which makes her a receptionist with a calendar instead of a chief of staff."*

**Push**: 63.5% of the delivered data — the part the practice actually cares about — is sitting flagged-not-ingested. Every clinical question routes to a human today. 8,303 overdue events and 4,325 overdue vaccinations at *one* practice are unworked revenue.
**Pull**: a Chief of Staff who can run the recall list, answer "when is Rex due," hand a DVM the last visit's plan, and never once cross into judgment.
**Anxiety**: this is the veterinarian's legal record. An AI that mis-states a lab value, quotes a deleted result, or reminds the owner of a dead dog is not a bug report — it is a board complaint, a lost client, or a discovery exhibit.
**Habit**: staff open ezyVet and read it; recall lists are run manually or not at all.
**Non-consumption alternative**: keep the clinical entities flagged forever and sell Vera as a scheduling/billing layer — which is the "receptionist with a calendar" outcome, and which is exactly the ground Dodo/Otto/Weave already occupy.
**Confidence**: **HIGH** on the job, **MEDIUM** on the safe answer — the medicine is unambiguously where the value is; the open question is how much of it can be *stated* rather than merely *held*.

---

## Opportunity

**Product outcome**: Vera can answer patient-level clinical questions from the practice's own record, with a resolvable source on every fact, partitioned so that the administrative half reaches clients and the record half never does. Measurable: overdue-recall list generated per practice (baseline: 8,303 events + 4,325 vaccinations at Coastal Creek); % of clinical facts carrying a resolvable reference (target 100%); **0** reveals of a `clinical_record`-class fact to a client audience across a red-team suite; **0** outbound clinical reminders for deceased patients (175 flagged `Dead`); ingest wall-clock per practice at 3× current row volume.

**Opportunity**: this is the difference between an envelope that holds the *business* of the practice and one that holds the *practice*. It is also the unlock for 012's prior-visit citations, for 010's triage routing with real patient context, and for the first genuinely clinical shadow receipts.

**Top 3 assumptions**:
1. **The due/overdue engine is trustworthy enough to act on.** Testable now: 8,303 overdue events include deceased animals, closed accounts, and stale rows. The overdue list must be cross-filtered against `Dead` (175), `Is Active = NO` (135 animals), and already-sent `CommunicationExport` rows before it is a list anyone would send. Validate before building the outreach half.
2. **Clinical facts can be ingested and held before they are citable.** If holding-without-citing turns out to be a distinction the product cannot maintain, 013 collapses into "wait for R5," and the whole cycle sequences behind Vera-core.
3. **Coastal Creek's fill rates generalize.** n=1. If another practice actually populates BCS, pain scores, and problem lists, the capability ranking below changes materially. Per-practice profiling (009 FR-026 already treats the group map as a prior) is the check.

---

## Clinical Capability Ranking

Ranked by product value **net of risk and net of what the data actually contains** — not by row count.

| # | Capability | Entities (rows) | What Vera can do that she cannot today | Risk lane |
|---|---|---|---|---|
| **1** | **Due / overdue recall** | Event 32,014 · EventGroup 91 · EventGroupAssociation 528 · Vaccination 7,949 · Medication refill fields | "Rex is due for his rabies booster; you were last reminded in March." Generate the practice's overdue list, deduplicated against what was already sent. 8,303 + 4,325 overdue at one practice. | **Administrative** — AAVSB explicitly blesses reminder generation. Client-speakable. No citability dependency. |
| **2** | **Medication & vaccination history** | Medication 16,520 (100%→Product) · Vaccination 7,949 | Answer a refill request against the actual prescription on file (qty, refills left, expiry); confirm vaccine status; recognize a controlled-substance request and refuse it structurally rather than by prompt. | Staff-audience. Controlled class (883 rows) fenced. |
| **3** | **Visit / episode context** | Consult 8,243 · Revisit 391 | Turn 009's appointments into *visits*: who saw the patient, when, for what (free-text complaint), what the case owner was. The join target everything else hangs from. 10 distinct case owners → closes 009's `providers: derive_from_consults` gap. | Staff-audience. |
| **4** | **Weight & trend** | HealthStatus 6,779 (Weight 98%) | Weight trajectory across visits — a real clinical signal, honestly the *only* structured vital in this export. | Staff-audience. Must not be marketed as "vitals." |
| **5** | **Diagnostic status (not values)** | DiagnosticRequest 5,029 · DiagnosticResult 7,081 | "The bloodwork was ordered on the 12th and came back on the 14th." Status, timing, and whether a result is outstanding — no numbers. | Administrative-adjacent; the status is speakable, the value is not. |
| **6** | **Procedures / therapeutics** | Therapeutic 653 · PlanTherapeutic 8,339 (approver + approval time) | Procedure history with who approved it and when. | Staff-audience. |
| **7** | **Diagnostic result values** | DiagnosticResultItem 262,370 → **61,137 live** → **29,402 with a reference range** | "Rex's last three creatinine values." 405 distinct analytes. | **Highest.** Only 48% of live items carry a range, so abnormal-flagging is partial. Stating or characterizing a value is the nearest thing to practicing. |
| **8** | **Prior-visit narrative (SOAP)** | VisitHistory 5,510 · VisitExam 4,295 · ConsultAssessment 4,226 · ConsultPlan 5,480 | Reconstruct the full SOAP note per consult — the thing 012 wants to cite. | **Highest.** Verbatim clinician narrative, containing diagnoses and plans in the vet's own words. Citability strictly gated on R5. |
| **9** | **Problem lists** | MasterProblem 3,722 catalog · AnimalMasterProblem **48** | Nothing, at this practice. Ingest the catalog as vocabulary; do not build a capability on 48 rows. | n/a |
| **10** | **Documents / memos** | Document 2,294 (0 signed) · Memo 12,323 | Staff-internal correspondence and generated documents. | Staff-only, no client path. Out this cycle. |

---

## Regulatory Posture: STATE vs CITE vs NEVER TOUCH

The AAVSB's own line is **decision-involvement**, not data-sensitivity: routine administrative AI ("generating reminder emails") is explicitly fine and may not even require client notification; anything "involved in any part of the decision-making process or direct Patient interaction" should carry **written informed consent each time**. That single sentence is why the clinical corpus must be architecturally partitioned rather than governed by a policy toggle.

**NEVER TOUCH — not a verb at any autonomy level, on any channel, for any audience:**
diagnosis · prognosis · differential · treatment plan · dose calculation or adjustment · drug selection · **interpretation or characterization of a result** ("that creatinine is high", "that's within normal limits") · any controlled-substance action (883 rows, 31 products) · euthanasia and end-of-life content · any statement to a client that would imply a VCPR. Also — and this is new for 013 — **no write and no correction into the clinical record, permanently.** The practice owns the record; state rules require amendments to be marked with date and author and forbid retroactive deletion. A Vera-authored amendment is not a feature we can build safely, so the correction verb should not exist rather than be gated.

**MAY CITE — staff audience only, always with a resolvable reference:**
consult narrative, exam and history text, assessments and plans, diagnostic values with their ranges, medication and vaccination history, problem entries, therapeutic records. *Citing* here means surfacing the practice's own record verbatim with a one-tap source. Vera is a retrieval surface **over** the veterinarian's record, never an author **on** it. This is exactly the posture the won't-do list already publishes ("Vera drafts, summarizes, and organizes; a licensed professional reviews and signs") — 013 makes it mechanical.

**MAY STATE — administrative projection, client audience permitted:**
due / overdue status · appointment and visit dates · whether a diagnostic has come back (status, never value) · that a prescription exists and has N refills remaining · that a reminder was previously sent. This is the AAVSB-blessed lane and it is where capability #1 lives entirely.

**Binding to the published won't-do list** — four of the eight commitments are load-bearing here:
- *"never diagnose, prescribe, or alter a treatment plan"* → the NEVER-TOUCH list above, enforced as absent verbs.
- *"never sign a medical record"* → reinforced by read-only-forever into the clinical record.
- *"never give a client medical advice over the phone"* → enforced by the STATE/CITE partition, not by prompt.
- *"never state a fact it cannot source"* → **this is the one 013 threatens most**, because KI-1 means a clinical reference can silently resolve to different content after a delta ingest. See below.

---

## Memory & Audience Implications (011)

011 gives five audiences (`owner` · `manager` · `staff` · `client_verified` · `caller_unverified`) with default-deny reveal policy, and FR-015 already withholds *financial* detail from verified clients. Clinical detail is a stricter case and is not named anywhere in 011.

**The finding**: clinical facts do not need a sixth audience — they need a **sensitivity class orthogonal to audience**, because "Rex is due for rabies" and "Rex's creatinine was 3.8" concern the same patient in the same household and must land on opposite sides of the client line.

Proposed extension to the `memory_scoping` policy data (an extension, not a fork):

| Class | Contents | `caller_unverified` | `client_verified` | `staff`+ |
|---|---|---|---|---|
| `clinical_administrative` | due/overdue, visit dates, result-arrived status, refills-remaining count, reminder-sent history | deny | **allow** (own household) | allow |
| `clinical_record` | narrative S/O/A/P, diagnostic values & ranges, medication/vaccination detail, problems, weights | deny | **deny** | allow |
| `clinical_restricted` | controlled-substance records (883) · euthanasia / end-of-life · `Resuscitate` status (16 DNR, 5 ALS) · `Cause Of Death` · staff memos (12,323) | deny | deny | **staff surface only — Vera never speaks it on any channel** |

**Consequences that must be designed, not discovered:**
- **Deceased patients are a hard suppression filter, not a soft flag.** 175 animals are `Dead`, with `Date Of Death` and `Cause Of Death` present. 011's edge case only excludes them from soft-confirm *reason guesses*. An overdue-vaccine reminder to a bereaved owner is not a defect report; it is the end of the relationship. Every outbound clinical projection filters on `Dead` + `Is Active` + account status.
- **The red-team suite must be re-run.** 011 SC-001 ("0 scoping violations") was written against a corpus that did not contain the answer to *"what's wrong with the dog."* The leak surface is categorically worse after 013.
- **The won't-do list already promises the test**: *"an unverified caller can book a routine appointment; they cannot hear a diagnosis."* 013 is what makes that promise testable — and falsifiable.
- **Staff memos are not clinical records but read like them.** `MemoExport` (12,323; contexts Animal 3,290 / Consult 2,410) is internal correspondence about clients. Default `clinical_restricted`, no client-audience path, ever.

---

## Volume & Performance Reality

**Per practice** (Coastal Creek, a ~2,658-patient practice with only ~2.5 years of exported history: 2023-12-05 → present):

| | rows |
|---|---:|
| Current ingest (9 entities) | 176,755 |
| All 22 clinical files | +392,516 |
| Of which `DiagnosticResultItem` | 262,370 |
| **Recommended 013 subset (below)** | **+~96,000** |

**Across 23 practices**: ~14.2M rows total, ~9.0M clinical, ~6.0M diagnostic result items — for the *all-in* scope. The recommended subset is ~2.2M additional rows across the group. Both numbers are floors: Coastal Creek is small-to-mid and its export covers 2.5 years. A 10-year archive at a larger practice scales linearly.

**What breaks at that volume — verified in the code, not speculated:**

1. **Three full in-memory copies of the export.** `EzyVetAdapter._entities()` parses *every* CSV member of the ZIP into `list(csv.DictReader(...))` — all 618,109 rows, regardless of what the entity map covers. `normalize()` then accumulates every `CanonicalRecord` (each carrying a `payload` dict **and** an `unmapped_fields` dict) in one list. `Normalizer.normalize()` builds a parallel `generic_rows` list of dicts and hands the whole thing to `upsert_canonical` in a single call. Adding clinical to `_entity_map` triples copies 2 and 3. This pipeline has already been bitten once by exactly this class of problem — the per-row unmapped-field accumulation fixed in `1b05899`.
2. **`canonical_record` is a JSON-payload spine, and 262k clinical rows per practice is not a recall structure.** "Rex's last three creatinine values" over a JSON blob column is a scan. 009 solved this for financials by giving them typed read models (`InvoiceRecord`, `PaymentRecord`, `LedgerEntry`). Clinical needs the same treatment — typed tables plus an index on `(practice_id, patient_ref, occurred_at)` — or recall latency makes the capability unusable regardless of correctness.
3. **`batch.py` chunks by practice, not by entity.** One practice's clinical load is now the unit that must be streamed, and nothing streams it.
4. **The date-coercion layer that does not exist** (Surprise 7) is on the critical path: every overdue computation, every "last visit," every time-ordered recall depends on parsing `MM-DD-YYYY` in three renderings with no timezone.
5. **77% of the biggest table is soft-deleted** (Surprise 1). Honoring `Is Active` cuts `DiagnosticResultItem` from 262,370 to 61,137 — a 4.3× reduction that is simultaneously the correctness fix and the largest single performance win available.

---

## The KI-1 Dependency (and KI-2)

009's idempotent upsert is **delete-then-insert on `(practice_id, entity_ref)`**. A reference persisted before a delta ingest still resolves afterward — to different content. Nothing errors, nothing warns.

For financial data that is bad. **For a clinical citation in a legal medical record it is a discovery liability.** 012 already reached this conclusion independently and quarantined itself: FR-032 prohibits citations into the practice record, and clarification Q9 names KI-1 by file and line as the reason. 013 is the spec that either lifts that prohibition or leaves it permanently in place.

**Therefore the sequencing rule for this cycle:**

> **013 may ingest clinical records before R5 lands. It may not make them citable.**

Every clinical canonical record ships with an explicit non-citable marker until snapshot-versioned resolution (Vera-core contract **R5**) is in place. Non-citable facts are still useful — they drive the due/overdue list, triage routing context, and internal ranking — they simply cannot appear as a sourced claim in a note, a briefing, or a client-facing statement. When R5 lands, citability is flipped on per class, not per record.

The alternative (sequence all of 013 behind R5) is defensible but wastes the cycle: capability #1, the highest-value one, quotes nothing and needs no citation at all.

**KI-2 binds harder here than it did for financials.** "Three of your patients are overdue for rabies" is a derived claim over a set of records. The reconciliation report's AR variance at least has a number an owner can eyeball against their own books; nobody can eyeball a recall list. Clinical derived claims need contract **R2** (a claim cites a *set* of references, cheaply) with the contributing reference set persisted — otherwise the recall list is exactly the shape both 009 defects share: *invisible when broken*.

---

## Shaping

### Solution Sketch (phased)

- **Phase A — Substrate (the unglamorous half, and the whole reason the rest works).** Extend, do not fork: add clinical entities to `ezyvet_mapping.complete_v1.yaml` (consolidating the duplicated `source_files` block); add the **Code→Id resolution index** so clinical children key to the same `patient` `entity_ref` as 009's `Animal Id`; add a **type-coercion layer** (dates, YES/NO + 0/1 booleans, numerics); **honor `Is Active`** as a first-class soft-delete rather than ingesting deleted records; add a `clinical` category to `section5_scope.yaml` and to `SCOPE_CANONICAL` so completeness can actually measure it; stream/chunk ingest by entity; add typed clinical read models with `(practice_id, patient_ref, occurred_at)` indices.
- **Phase B — The administrative projection (ship this first, it is the product).** Event + EventGroup + EventGroupAssociation + Vaccination + Medication-refill fields → a per-practice **due/overdue view**, cross-filtered against `Dead`, `Is Active`, and prior `CommunicationExport` outreach. Client-speakable, no citability dependency, immediate revenue meaning.
- **Phase C — The clinical corpus, held not spoken.** Consult, Medication, Vaccination, HealthStatus(weight), PlanTherapeutic, DiagnosticRequest/Result headers, plus the catalogs. Ingested with lineage, marked **non-citable**, classified `clinical_record`, staff-audience only.
- **Phase D — Citability, on R5.** Flip clinical classes to citable as snapshot-versioned resolution lands; this is what unblocks 012's prior-visit citations and closes the loop on the published *"never state a fact it cannot source."*

### Rabbit Holes
- **Ingesting all 44 entities because they are there.** 262,370 result-item rows and 19,511 rows of verbatim clinician narrative are the two highest-risk, highest-cost, lowest-immediate-value groups in the delivery. They are also the two most tempting.
- **Building a clinical interpretation layer to fill the empty `Interpretation Outcome` column.** The column is 100% blank. Filling it *is* the forbidden act. It will look like an obvious gap to fill and it must be named as a no-go before someone fills it.
- **Treating `HealthStatus` as a vitals table** because the schema says so, then marketing "Vera tracks your patients' vitals" on a table that is 98% weight and 0% BCS.
- **A "clinical correction" verb.** A field defect (wrong species on a record, a typo'd weight) will make this feel humane. State record law makes it uninsurable.
- **Assuming Coastal Creek's fill rates.** n=1 of 23. The capability ranking is a prior, not a fact.

### No-Gos (this cycle)
- Any write, correction, or amendment into the clinical record — permanently, not just this cycle.
- Any clinical *interpretation* output at any autonomy level; any controlled-substance verb.
- `DiagnosticResultItem` (262k), the SOAP narrative quartet (~19.5k), `DocumentExport`, `MemoExport`, `TagExport` — see IN/OUT below.
- Citable clinical facts before R5.
- Any client-audience reveal of a `clinical_record`-class fact.
- Marketing "Vera knows your patients' medical history" before the audience partition is red-teamed.

### Recommended Scope — IN / OUT

**IN (~96k rows/practice, ~2.2M across 23):**

| Group | Entities | Rows | Why |
|---|---|---:|---|
| Vocabulary layer | Species 18 · Breed 769 · AnimalColour 117 · AppointmentType 56 · EventGroup 91 · EventGroupAssociation 528 · MasterProblem 3,722 · PresentingProblem 621 · Therapeutic 653 · Diagnostic 10,776 · ClinicalTemplating 85 · User 156 | ~17.6k | Tiny, cheap, and it makes every other entity legible. `User` + consult case owners also close 009's `providers: derive_from_consults_and_appointments` gap. |
| Due/overdue engine | Event 32,014 · Vaccination 7,949 | ~40k | Capability #1. Administrative lane. Ships value with zero citability dependency. |
| Episode spine | Consult 8,243 · Revisit 391 | ~8.6k | The join target; turns appointments into visits. |
| Medication history | Medication 16,520 | 16.5k | Capability #2; controlled class fenced at ingest. |
| Weight series | HealthStatus 6,779 | 6.8k | Capability #4, ingested honestly. |
| Problem / therapeutic links | AnimalMasterProblem 48 · PlanTherapeutic 8,339 | 8.4k | Cheap; PlanTherapeutic carries approver + approval time. |
| Diagnostic headers | DiagnosticRequest 5,029 · DiagnosticResult 7,081 | 12.1k | Capability #5 — status and timing, no values. |

**OUT (this cycle):**
- **`DiagnosticResultItemExport` (262,370)** — 67% of all clinical volume, 77% soft-deleted, 100%-empty interpretation, only 48% of live items carrying a reference range, and the single hardest thing to reveal safely. Deferred to cycle two behind streaming ingest + typed read models + R5. The Request/Result *headers* stay IN so Vera can speak to status without touching a number.
- **The SOAP narrative quartet** — VisitHistory 5,510 · VisitExam 4,295 · ConsultAssessment 4,226 · ConsultPlan 5,480 (~19.5k). This is the verbatim clinician record, containing diagnoses and plans in the vet's own words; it is precisely what 012 wants to cite; and citing it is blocked on R5. *(This is the one scope call I would most like Matt to overrule or confirm — see Q1.)*
- **`DocumentExport`** (2,294 with full content, 0 signed), **`MemoExport`** (12,323, staff-internal), **`TagExport`** (28,479 — verified to be a config taxonomy here: Product 16,366 / MasterProblem 3,994 / Breed 1,982, not a patient-flag system), `InClinicExport` (0 rows), Wellness (0 rows).

### Appetite Assessment
**Medium** for the recommended subset: Phase A is the real work (coercion, soft-deletes, Code→Id keying, streaming, typed read models, the §5 clinical category) and is largely mechanical; Phases B–C are mapping plus policy. ~4–6w. The all-in scope is a different spec with a different appetite and should not be smuggled in.

### COS-Platform Registry
- **Consumes**: 009's adapter port / canonical spine / completeness+quality gates; 011's `entity_ref` builders and `memory_scoping` policy shape; the Expert Firewall (absent-verb enforcement); the Vera-core evidence contract (R2, R5).
- **Registers back**: **`sensitivity-classed memory scoping`** — the finding that per-audience default-deny is insufficient once a corpus contains facts of categorically different sensitivity about the *same* subject, and that the fix is a class dimension orthogonal to audience rather than more audiences. Generalizes to any vertical ingesting a regulated record (FarmAgent herd-health, and any future professional vertical).
- **Registers back**: **`ingest soft-deletes are correctness, not hygiene`** — 77% of the largest table being `Is Active = NO` is the strongest available evidence for making source-system deletion a first-class concept in the adapter port rather than a per-adapter afterthought.

### Constitution Check
- **KNOW/ADVISE/DECIDE**: 013 is pure KNOW. It adds no verbs. Every clinical capability it unlocks is retrieval or a due-list; the licensed acts remain absent from the catalog.
- **Expert Firewall**: strengthened — the controlled-substance and interpretation prohibitions move from "not in the tool catalog" to "a fenced data class with no reveal path."
- **Claim discipline**: the reason clinical facts ship non-citable until R5. Shipping citable-but-rewritable clinical references would break the published *"never state a fact it cannot source"* in the one place where breaking it is a legal event.
- **Invisible adoption (Working Rule 0)**: 013 produces no staff-facing artifact. The due/overdue view is an owner/manager surface, consistent with 009 FR-029.

---

## Competitive Context

### Best-in-Class Patterns
Epic/Abridge-class provenance-on-every-fact (the pattern 012 is already importing); the classic veterinary recall/reminder engine that every PIMS ships and almost no practice fully works; 009's own financial reconciliation as the template for "derived figure, disclosed as derived."

### Category Gap
Every competitor with clinical data has it because they *are* the PIMS. The overlay players (Dodo, Otto, Weave) have a calendar and a phone line and no medicine. Nobody in veterinary holds the practice's clinical record **as a cross-PIMS envelope with per-fact sensitivity classing and a resolvable source on every statement** — because that requires having ingested the record from outside the PIMS, which is the envelope strategy's whole point. The published won't-do list is the marketing surface for this, and it is the only one a PIMS-bound AI structurally cannot copy: they cannot promise not to write into a record they *are*.

---

## ICE Score

| Dimension | Score | Rationale |
|---|---|---|
| Impact | 9/10 | 63.5% of the delivered data; unlocks the top-value clinical capability (recall) plus 012's prior-visit citations; converts Vera from calendar-and-billing to actual chief of staff |
| Confidence | 7/10 | Graph, volumes, and quality findings are computed from the real export, not assumed; the unknowns are cross-practice generalization (n=1) and the citability sequencing with Vera-core |
| Ease | 5/10 | Phase A is real: coercion layer, soft-delete semantics, Code→Id keying, streaming ingest, typed read models, the §5 clinical category — plus a memory-scoping extension that is a security boundary and must be red-teamed |

**Low-confidence flags**: Ease (5) — the ingest architecture demonstrably does not survive this volume unmodified, and four of the six Phase-A items are defects in shipped 009 code rather than new construction. Validation: run the recommended subset against Coastal Creek end-to-end before committing to the full spec.

---

## Open Questions

- **[NEEDS CLARIFICATION] Q1 — The SOAP narrative quartet: ingest-now-non-citable, or defer entirely?** ~19.5k rows of verbatim clinician narrative (VisitHistory/VisitExam/ConsultAssessment/ConsultPlan). Ingesting it early means 012's prior-visit citations light up the day R5 lands; it also means the highest-sensitivity text in the delivery sits in the store for a cycle with no citable use. This doc recommends **defer**, but it is a close call and it is Matt's. *Owner: Matt (+ Vera-core R5 sequencing).*
- **[NEEDS CLARIFICATION] Q2 — Does the §5 letter's enumerated scope actually cover clinical records?** `section5_scope.yaml` has six categories and none names a clinical entity — yet the clinical files arrived. Either the letter covered them under "patient records" and the config is simply wrong (fix the config), or they arrived outside the request (which is a different conversation with counsel before we normalize them). This is unresolved and it gates Phase A. *Owner: Matt + counsel.*
- **[NEEDS CLARIFICATION] Q3 — Is `clinical_administrative` speakable to a verified client without per-use written informed consent?** The AAVSB blesses reminder generation explicitly, but its decision-involvement threshold is broad. "Rex is due for rabies" is a reminder; "Rex is due for rabies **and his last bloodwork was three months ago**" starts to look like clinical judgment about what the patient needs. The line inside capability #1 needs drawing before it is built. *Owner: Matt + counsel.*
- **[NEEDS CLARIFICATION] Q4 — Do Coastal Creek's fill rates generalize?** BCS/pain/dental/BP at 0%, problem list at 48 rows, `Body System Number` 100% empty. If two or three other practices populate these, capabilities #4 and #9 change rank materially. Cheapest test: profile 2–3 more of the 23 databases before finalizing scope. *Owner: pilot week-1 profiling.*
- **[NEEDS CLARIFICATION] Q5 — What is the retention and deletion posture for clinical facts in the vault?** State retention runs 1–7+ years with no federal baseline, and a 23-practice group spans states. 012 settled a retention posture for *audio*; nothing has settled one for ingested clinical records, and "the clinic owns the vault" does not by itself answer what we delete and when. *Owner: Matt + counsel.*

---

## Proceed Signal

**GO — with a materially reduced scope.**

Proceed on the recommended subset (~96k rows/practice) with four binding conditions:

1. **Phase A first, and it is mostly defect repair.** Soft-delete semantics, type coercion, Code→Id patient keying, the §5 clinical category, and streamed/typed ingest are prerequisites, not polish. Two of them (`Is Active`, the missing clinical scope category) are live correctness gaps in shipped 009 code today and should be fixed whether or not 013 proceeds.
2. **Clinical facts ship non-citable until Vera-core R5.** Sequence *with* the evidence contract, never around it — the same rule 012 adopted for the same reason. KI-2/R2 applies to every derived clinical claim, starting with the recall list.
3. **The memory-scoping extension is a security boundary and is red-teamed before any client-facing reveal**, including the deceased-patient suppression filter. 011's existing red-team corpus does not contain clinical facts and must be regenerated.
4. **`DiagnosticResultItem` and the SOAP narrative are explicitly out**, revisited in cycle two once R5 has landed and streaming ingest is proven. Ingesting them "since we're in there" is the failure mode this discovery exists to prevent.

**NO-GO conditions** (any one of these should stop the spec rather than reshape it): Q2 resolves to "the clinical files were not within the §5 request"; or the product cannot maintain a held-but-not-citable distinction, in which case 013 sequences wholesale behind R5.

---

## Marketing Output

### Positioning Message Seed
"Vera knows when your patients are due — and she knows where she stops. She reads your practice's own records to run your recall list; she will never read you a diagnosis, and she will never write a word into your chart." *(The stopping point is the message. Keep ezyVet unnamed — ToS §4.1 posture.)*

### Why-Now Angle
Every overlay competitor answers the phone; none of them holds the medicine, because holding it requires being outside the PIMS and getting the record honestly. The published won't-do list becomes provable rather than promised at exactly the moment Vera *could* say the forbidden thing and structurally does not. [Needs a `verified-claims.md` entry before external use — the "will never write into your chart" line is a PRODUCT-CLAIM, true only once the absent-verb enforcement ships.]

### Differentiation Source
Per-fact sensitivity classing over an ingested clinical record: the same Vera who tells a client their dog is due for a booster cannot tell them the creatinine, and the reason is a database rule, not a prompt. A PIMS-bound AI cannot make that promise, because it *is* the record.
