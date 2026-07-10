# Feature 011 — Relationship Memory & Consent ("Vera Knows the Family"): Task List

**Branch**: `011-relationship-memory` · **Scope**: VP-4a cycle 4a only (household/identity substrate, caller ID + tiered verification, per-audience KNOW≠REVEAL scoping, consent/opt-out registry + inbound seam, shared-phone fix). 4b cross-channel threads / 4c relationship signals are out of scope. Per the implementation-reality binding, **everything external runs in sim/dual-mode** — the net-new inbound webhook + STOP processing get a simulator mirroring `backend/sms_gateway.py`'s outbound auto-detect pattern, and the resolver's ezyVet-export identity audit runs against a **synthetic dirty-data fixture corpus** (built as T007). The entire list is completable and testable with **zero live telephony / SMS / Thoth calls**. Live-mode is a config swap, deferred to the Pilot-Activation section.

**Datastore for this build**: the 13 net-new 011 tables run on a **local PostgreSQL via `docker-compose`** (matching the data-model's "Postgres + RLS, not SQLite" mandate), app-level `clinic_id`/`party_id` scoping standing in for full RLS in the single-clinic build (per the plan's VP-1-slip degradation, same posture as 010). Core Thoth is **consumed, never forked** — read via the `ScopedRecall` wrapper; a Thoth stub (`recall`/`recall_by_kind`) backs the sim so no live substrate call is made.

**Coverage**: FR-001–FR-024 (all 24 owned by ≥1 task) · SC-001–SC-007 · data-model 13 tables + migration · contracts R1–R5 (identity/verification), A–D (ScopedRecall), I1–I3 (inbound/consent). **37 tasks total** (cap ~40).

**Path note (plan reconciliation)**: The plan's structure lists the 4a tier as `backend/relationship/`. All existing Python (`models.py`, `agents/`, `sms_gateway.py`, `voice/`) lives under `backend/`, so 011 code roots at **`backend/relationship/`**; config stays at repo-root **`config/relationship/`** as the plan specifies; tests under **`backend/tests/relationship/`**. Models extend the shared **`backend/models.py`** (010 precedent). Shim upgrades touch **`backend/voice/shims/`** and **`backend/voice/prefetch.py`** in place.

**Legend**: `[P]` parallelizable · `[US#]` maps to spec user story · `[MARKETING]` customer-visible / announcement-blocking · `[SHIM — extract to core, ask pending]` VetAgent-side rail that becomes core's once the mandatory-audience API lands (board ask #2) · `[SHIM upgrade]` formalizes a 010 prototype shim in place (no duplication; 010 keeps its API).

---

## Phase 1 — Setup

- [ ] T001 [P] Create `backend/relationship/` package (`backend/relationship/__init__.py`) + repo-root `config/relationship/` dir; confirm existing deps cover the build (`PyYAML`, `psycopg`/`asyncpg` already present for 010's Postgres) and add any missing to `backend/requirements.txt`.
  - *Verify*: `python -c "import backend.relationship"` succeeds; `pip install -r backend/requirements.txt` is clean.
- [ ] T002 [P] Append the 13 entities + enums as Pydantic models to `backend/models.py` per `data-model.md` (`Household`, `HouseholdContact`, `ContactIdentifier`, `PatientHouseholdLink`, `IdentityResolutionEvent`, `HouseholdReviewQueue`, `VerificationChallenge`, `MemoryScopingPolicy`, `RevealDecisionLog`, `ContactConsent`, `ConsentEvent`, `InboundMessage`, `ClinicStaffRole`; enums `household_role`, resolution `outcome`, `sensitivity_tier`, reveal `decision`, consent `action`, inbound `action_taken`, staff `role`). Party-scoped tables key on **`party_id`** (M4).
  - *Verify*: models import; the resolution `outcome` type admits only `resolved_single|ambiguous_multi|unmatched`; `reveal_decision_log.decision` admits only `revealed|withheld`.
- [ ] T003 [P] Create config fixtures: `config/relationship/memory_scoping.goldsmith.yaml` (**unsigned** placeholder — VP-9 signs the real content; the **three-field** shape per contract C — `allow_classes` + `scope_predicates` + `kind_to_class` — structural default-deny by absence), `config/relationship/verification_policy.goldsmith.yaml` (`sensitivity` action→tier map + `factors_required` low:1/high:2 + staff-callback deferral), `config/relationship/inbound_keywords.en.yaml` (TCPA `STOP`/`START`/`HELP` table).
  - *Verify*: all three parse; `memory_scoping` omits at least one (audience, fact_class) pair from `allow_classes` so default-deny is exercisable, and contains at least one `fact_kind` **not** present in `kind_to_class` so the unmapped-kind deny is exercisable; `verification_policy` maps `contact_edit`/`refill_request`→`high` and `reschedule`/`cancel`→`low`; keyword table contains `STOP`.

---

## Phase 2 — Foundational (blocking prerequisites for all phases)

- [ ] T004 `HouseholdRepository` in `backend/relationship/household_repository.py` — CRUD + append-only ops for all 13 tables + `init_db()` targeting **local PostgreSQL via `docker-compose`** (NOT SQLite; VoiceRepository pattern). Append-only enforcement on the 5 audit tables (`identity_resolution_event`, `verification_challenge`, `reveal_decision_log`, `consent_event`, `inbound_message`); `UNIQUE(party_id, channel)` on `contact_consent`; index `(clinic_id, id_type, value_normalized)` on `contact_identifier`; app-level `clinic_id`/`party_id` scoping standing in for full RLS. (deps: T002)
  - *Verify*: `init_db()` creates the 13 tables on the docker-compose Postgres; any UPDATE/DELETE on a logged `reveal_decision_log`/`consent_event` row is rejected; a second `contact_consent` row for the same `(party_id, channel)` violates the UNIQUE constraint.
- [ ] T005 [P] `entity_ref.py` PIMS stable-id → `{type}:{stable_id}` mapper in `backend/relationship/entity_ref.py` — `household:vah_*` (synthesized), `client:ezyvet_c*`, `patient:ezyvet_p*`; display names live in the payload, **never in the key**. (deps: T001)
  - *Verify*: a PIMS client id maps to `client:ezyvet_c<id>`; two contacts with the **same surname** produce distinct keys (no name in key); a PIMS name edit does not change the key.
- [ ] T006 [P] Dual-mode env resolver + inbound **simulator** in `backend/relationship/inbound_sim.py`, mirroring `sms_gateway.py` auto-detect (`INBOUND_LIVE` force flag + credential presence → `is_live()`); a test harness posts `InboundMessage`s into the same seam a live Twilio inbound webhook will slot behind — zero live SMS/telephony. (deps: T001)
  - *Verify*: `is_live()==False` with no creds; the harness posts a scripted `InboundMessage` and it flows through the seam with no network call.
- [ ] T007 Synthetic **dirty-data fixture corpus** generator in `backend/tests/relationship/fixtures/ezyvet_dirty_corpus.py` — the red-team's fuel: ≥1 phone **shared across two households**, ≥1 **surname collision**, ≥1 **PIMS name-edit** pair (same stable-id, changed display name), ≥1 **duplicate owner** record, an **ex-spouse** shared-history pair, and a **deceased pet**. Emits both the seed rows and the ground-truth answer key the audit/red-team harnesses assert against. (deps: T005)
  - *Verify*: the corpus contains at least one instance of each dirty pattern above; the answer key marks which lookups are single-match vs multi-match vs duplicate, so a false-positive auto-ID is detectable.

---

## Phase 3 — Phase A: Household & identity data model + migration (US1)

- [ ] T008 [US1] [MARKETING] Flat `owners`→household **migration** in `backend/relationship/migrate_households.py` — reads its source from the **platform Postgres `owners` table** (hydrated by VP-1/009 envelope ingestion; demo SQLite `owners` is demo-track only — M1); dev/test reads a synthetic flat-owner fixture via a small **SQLite→PG hydration helper** so the same code runs over a Postgres source in both paths. Each `owners` row → one `household` (`household:vah_*`) + one `household_contact` (`co_owner`) + `contact_identifier` rows for its phone and email; each existing owner→patient link → one `patient_household_link`. Hard assertion gate; **fails loudly, never silently drops**. (deps: T004, T005)
  - *Verify*: `count(patient_household_link) == count(prior owner→patient links)` and `count(distinct migrated patients) == count(patients)` — zero orphaned pets, zero lost contacts (SC-007 100% preservation); a deliberately-broken link count aborts the migration with a raised error.
- [ ] T009 [US1] Household read path in `household_repository.py` — resolve any contact identifier to the **same** household with its full patient roster; the resolution step exposes identity structure only, **no medical detail**. (deps: T004, T008)
  - *Verify*: a household with two co-owners (different phones) + three pets resolves to the same `household_id` and all three pets from **either** contact; adding an authorized contact creates no duplicate household; no clinical/medical field is returned at the resolution step (US1 independent test).

---

## Phase 4 — Phase B: Identity resolver + candidate sets + review queue (US4 / US2 / US1)

- [ ] T010 [US4] [MARKETING] **The `LIMIT 1` kill** — `identity_resolver.resolve()` in `backend/relationship/identity_resolver.py` returns the **full candidate set** (`ResolutionResult`, contract R1) and persists an append-only `identity_resolution_event` with the complete `candidate_set_json`; `resolved_single` is returned **only** on an exact normalized-phone match to exactly one contact. There is no code path that reduces a multi-match to one record. (deps: T004, T007)
  - *Verify* (**zero-tolerance**): across the entire shared-phone fixture corpus, a multi-match identifier **never** returns a single-candidate result — not once; `outcome=resolved_single` occurs only when `match_count==1` on an exact phone match; a fuzzy/partial or email match never yields `resolved_single`; the persisted `candidate_set_json` equals the full candidate set (SC-003).
- [ ] T011 [US4] `disambiguate()` (contract R2) in `identity_resolver.py` — matches an **open** "name on the account" answer against the candidate set; resolves to `resolved_single` only on exactly one match; zero or >1 matches stay unresolved. **Candidate names are never read back to the caller** (preserved from the 010 T006 shim). (deps: T010)
  - *Verify*: an open name matching exactly one candidate resolves; a name matching zero or two candidates stays `ambiguous_multi`/`unmatched`; no candidate `display_name` is ever emitted to the caller-facing channel (assertion over the disambiguation output).
- [ ] T012 [US1] `review_queue.propose_grouping()` (contract R3) in `backend/relationship/review_queue.py` — probable duplicates, shared-line collisions, and merge candidates write to `household_review_queue` with `status="pending"` + evidence; **no code path silently merges records** (FR-004). (deps: T004, T007)
  - *Verify*: the fixture's duplicate-owner and shared-phone-collision cases each land a `pending` `household_review_queue` row with `evidence_json`; a static/import assertion confirms no auto-merge call path exists; a probable-duplicate is **not** auto-identified.
- [ ] T013 [US2] [MARKETING] Auto-ID + soft-confirm gating in `identity_resolver.py` — auto-greet by name **only** on `resolved_single`; `audit_only` disabled-safe mode (records candidates, always returns neutral) for use until the real ezyVet-export audit clears; `ambiguous_multi`/`unmatched` → neutral "May I get the name on the account?". (deps: T010)
  - *Verify*: `resolved_single` produces a soft-confirm-by-name payload; `audit_only=True` records the `identity_resolution_event` but returns the neutral prompt with no name; a rejected soft-confirm re-opens neutrally and reveals nothing tied to the dropped identity (FR-007/009).
- [ ] T014 [US1] Resolver identity-audit harness in `backend/tests/relationship/test_identity_audit.py` — runs `resolve` across the full dirty corpus and scores against the T007 answer key (the resolver-trust gate the plan makes a hard input). (deps: T010, T011, T012, T007)
  - *Verify*: **zero false-positive auto-IDs** across the corpus; every shared-phone lookup → `ambiguous_multi`; every duplicate/collision → a review-queue row; the audit report enumerates precision on single-match vs multi-match lookups.

---

## Phase 5 — Phase C: Caller ID + tiered verification bar (US5 / US2)

- [ ] T015 [US5] [MARKETING] `verification.require_verification()` (contract R4) in `backend/relationship/verification.py` — tiered, config-driven bar (`verification_policy.<clinic>.yaml`): soft-confirm (`phone_match`) is **identification only, never authorizes a change**; low-sensitivity (reschedule/cancel) → **1** knowledge factor; high-sensitivity (contact-edit/refill) → **2** factors or `deferred_staff_callback`; each factor is **validated against its authoritative source** — `pet_name` against `patient_household_link` (normalized exact-or-first-token, active pets only), `appointment_day` against the 010 booking/schedule store — and passes only on a match (H3/FR-018); a failure blocks the change, leaves state unchanged, offers a staff callback, and logs the attempt. Persists an append-only `verification_challenge` (no raw secret factor values). (deps: T003, T004)
  - *Verify*: caller-ID/soft-confirm alone authorizes **0** changes (SC-005); a low-sensitivity action prompts 1 factor and a high-sensitivity action requires 2 or defers to staff callback; a failed challenge leaves state unchanged and writes a `failed` `verification_challenge` row.
- [ ] T016 [US5] Mid-call sensitivity-escalation re-gate in `verification.py` — a caller who cleared the low bar and then requests a high-sensitivity action has the **higher** bar re-applied before the sensitive action (edge case). (deps: T015)
  - *Verify*: a session that passed 1 factor for a reschedule is re-challenged to 2 factors (or staff callback) when it escalates to a contact-info edit; the sensitive action is blocked until the higher bar clears.
- [ ] T017 [US2] C3 ChannelBinding **non-mutating boundary adapter** (contract R5) in `backend/relationship/verification.py` — a one-way translator at the core-binding edge mapping **every value of BOTH 010 enums** onto core's tier: `VerificationState.unverified`→`unverified`, shim `none`→`unverified`, `soft_confirmed`→`phone_match`, shim `strong`→`identity_confirmed` (`code_verified`/`otp_verified` are **not** boundary targets — `code_verified` comes only from 011's own R4 factor progression). **010's shim/`VerificationState` strings are never rewritten** — the adapter reads a copy and emits a core value at the edge. `party_candidates` on the binding = the resolver's candidate set; audience scope derives from **tier + role, never caller-ID alone**. Also populates the staff-side audience from `clinic_staff_role` (see below); voice callers are always client-tier in 4a. (deps: T013, T015)
  - *Verify*: the adapter enumerates and maps **all** values of both `VerificationLevel` (`none|soft_confirmed|strong`) and `VerificationState` (`unverified|soft_confirmed`) to exactly one core tier per the R5 table; no code path assigns a 4-tier value back into either 010 enum; a `phone_match` binding authorizes only unverified-scope reveals; audience is computed without reading caller-ID as an authorizer.

---

## Phase 6 — Phase D: Per-audience scoping — policy + ScopedRecall + reveal log (US3)

- [ ] T018 [US3] `scoping_policy.py` in `backend/relationship/scoping_policy.py` — loads the three-field `memory_scoping` policy (`allow_classes` + `scope_predicates` + `kind_to_class`, versioned into `memory_scoping_policy`) and evaluates a recall `fact_kind` for an audience with **structural default-deny**: (1) resolve `fact_kind→fact_class` via `kind_to_class` — an **unmapped kind is denied** (`reason=unmapped_kind`); (2) the resolved class must be in `allow_classes[audience]` (audience absent, or class not listed → `default_deny_no_rule`); (3) each `scope_predicate` for the audience is applied as a row filter (`own_household_only`→`wrong_household`, `own_clinic_only`). (deps: T003, T004)
  - *Verify*: a mapped kind whose class is in `allow_classes[audience]` returns allow; a mapped kind whose class is absent returns deny; an audience entirely absent from `allow_classes` denies **all** classes; an **unmapped `fact_kind` is denied with `reason=unmapped_kind`** (never revealed by omission).
- [ ] T019 [US3] `reveal_log.py` append-only reveal-decision audit in `backend/relationship/reveal_log.py` — writes `reveal_decision_log` on **every** decision (`revealed`/`withheld` + `rule_matched` + `reason` ∈ `explicit_allow|default_deny_no_rule|wrong_household`), staff-visible (FR-016). (deps: T004)
  - *Verify*: a revealed fact and a withheld fact each write exactly one `reveal_decision_log` row with its reason; a withheld-by-default fact records `default_deny_no_rule`.
- [ ] T020 [US3] [MARKETING] [SHIM — extract to core, ask pending] `ScopedRecall` wrapper (contract B) in `backend/relationship/scoped_recall.py` — `recall`/`recall_by_kind` with a **mandatory keyword-only `audience`** and `entity_scope`; the raw Thoth handle is **private** to the wrapper; `_apply_policy` runs the T018 default-deny filter and writes the T019 audit; client-facing code holds only a `ScopedRecall`. Registry-marked `prototype` with an extraction note (deleted when core lands the mandatory-audience API). (deps: T018, T019)
  - *Verify* (**unrepresentable**): calling `recall()` without an `audience` is a construction/type error, not a runtime check (API-shape assertion — no unscoped overload exists); a red-team probe cannot obtain the raw Thoth handle from any client-facing surface (attribute is private / not exposed); every recall emits a reveal-decision audit.
- [ ] T021 [US3] `entity_scope` enforcement in `scoped_recall.py` — `client_verified` limited to **own household only** and **no financial detail**; **another household's detail is always withheld** regardless of query; `caller_unverified` limited to general schedule availability. (deps: T020)
  - *Verify*: a `client_verified` request for another household's detail returns nothing and logs `wrong_household`; the same audience's financial-detail request is withheld; a `caller_unverified` request beyond schedule availability is withheld (FR-015).
- [ ] T037 [US3] Fact-taxonomy config + **evaluator allow/deny proof** in `config/relationship/memory_scoping.goldsmith.yaml` (the `kind_to_class` table + `allow_classes`/`scope_predicates`) and `backend/tests/relationship/test_scoping_taxonomy.py` — a table-driven suite proving **both** the allow AND the deny paths of the T018 evaluator across the closed class vocabulary (`schedule|client_summary|patient_clinical|financial|contact_info|staff_notes`) and both scope predicates. (deps: T003, T018)
  - *Verify*: for every audience, an allowed (kind→class) pair returns **allow** with `reason=explicit_allow`; a not-allowed class returns **deny** (`default_deny_no_rule`); an **unmapped `fact_kind` returns deny** (`unmapped_kind`); `client_verified` reading another household is denied `wrong_household`; the proof spans at least one positive and one negative case per audience (allow AND deny both proven, incl. the unmapped-kind-denies case).

---

## Phase 7 — Phase E: Consent/opt-out registry + inbound webhook seam (US6)

- [ ] T022 [US6] [MARKETING] `inbound_gateway.handle_inbound()` (contract I1) in `backend/relationship/inbound_gateway.py` — the **net-new** inbound intake seam, sim/dual-mode over T006; matches the config keyword table; a non-keyword message → `routed_to_staff` (**never auto-actioned**); persists an append-only `inbound_message` (`received_at` = the SC-006 clock start). (deps: T003, T006, T010)
  - *Verify*: a sim-posted `STOP` yields `matched_keyword="STOP"`; a free-text message yields `action_taken="routed_to_staff"` and is not auto-actioned; every inbound writes one `inbound_message` row; no live webhook is registered (sim only).
- [ ] T023 [US6] `consent_registry.py` (contract I2) in `backend/relationship/consent_registry.py` — `consent_check`/`record_opt_out`/`record_opt_in`; writes current `contact_consent` **and** an append-only `consent_event` (revocable + reversible audit). The `ConsentDecision` shape is preserved from the 010 T008 shim. Current state is staff-visible (FR-024). (deps: T004)
  - *Verify*: `record_opt_out` then `consent_check` returns `allowed=False`; `record_opt_in` restores `allowed=True`; both write a `consent_event` row; the current `contact_consent` row reflects the latest state and is queryable for the staff surface.
- [ ] T024 [US6] STOP→suppression flow wiring (contract I3) across `inbound_gateway.py` + `consent_registry.py` — inbound STOP → resolve `from_identifier` → `record_opt_out(source="inbound_stop", keyword="STOP", inbound_message_id=…)` → confirm to sender + reflect in staff consent state; a STOP from an **unresolved multi-match** (shared line) routes to staff rather than opting out the wrong party. (deps: T022, T023, T010)
  - *Verify*: an inbound STOP is recorded + staff-visible **≤60 s** in the sim clock (SC-006); an opt-back-in later is recorded with the same audit trail; a shared-line STOP that stays ambiguous routes to staff and opts out **no** contact.
- [ ] T025 [US6] Outbound suppression enforcement **+ inbound-served disclosure wiring** — `consent_check()` is consulted **before any Vera-initiated outbound** (reusing the `sms_gateway` outbound leg); a recorded opt-out suppresses outbound on the covered channel(s) while inbound service is unaffected. When an **opted-out client initiates inbound** and is served, the interaction MUST emit/persist a **`consent_record`** disclosure via 010's existing path (010 T033 — disclosure text + timestamp), not merely assert it (M6, FR-023). (deps: T023)
  - *Verify*: after an opt-out, **100%** of Vera-initiated outbound attempts on the covered channel are suppressed (SC-002); the same opted-out contact calling/messaging **in** is still served **and a `consent_record` disclosure row is written via the 010 T033 path** (FR-023).

---

## Phase 8 — Phase F: 010 shim upgrade + Thoth binding (all shim upgrades must keep 010 green)

- [ ] T026 [SHIM upgrade] Back `backend/voice/shims/channel_binding_shim.py` (010 T006) with the real resolver over `contact_identifier` candidate sets — **API unchanged** (candidate-party set + identity-safe open-name disambiguation, never enumerates names aloud); `is_shared_line` becomes the `LIMIT 1`-kill primitive. Upgrade in place; no duplicate module. (deps: T010, T011)
  - *Verify*: the shim's existing public methods keep their signatures; a shared inbound number returns `is_shared_line=True` with >1 candidate; a single exact-phone match returns exactly one; disambiguation never enumerates names.
- [ ] T027 [SHIM upgrade] Back `backend/voice/shims/consent_shim.py` (010 T008) with `consent_registry` — the `ConsentDecision` shape is preserved; the channel-scoped `(party, channel)` set now reads/writes `contact_consent`/`consent_event`, fed by the new inbound STOP path. (deps: T023)
  - *Verify*: `consent_check` returns the same `ConsentDecision` shape 010 asserts; an opt-out recorded via the inbound path is visible through the shim; default party returns allow.
- [ ] T028 [SHIM upgrade] [MARKETING] Replace the `HouseholdSummary` stub (010 contract A4, in `backend/voice/prefetch.py`) with a real **audience-scoped projection** via `ScopedRecall` — the frozen A4 fields (`party_id`, `display_name_for_greeting`, `household_patients[{name,species}]`, `last_visit_summary_line`, `audience_scope`, `verification_level`) are now populated per audience/tier; the `None`-returning stub path is retired but the field contract is unchanged. (deps: T020, T009, T017)
  - *Verify*: a `resolved_single`/`phone_match` caller gets a populated greeting summary scoped to their own household; an unverified caller gets no greeting-name leak; the A4 field shape 010 consumes is unchanged (010's prefetch tests still bind).
- [ ] T029 Bind `thread_id` for **single-channel voice continuity** only (consume core Thoth `ThreadManager` via the wrapper) in `backend/relationship/scoped_recall.py`/prefetch path — the 4b cross-channel switching surface is **not** built (scope guard). (deps: T020)
  - *Verify*: a voice interaction binds a `thread_id` and recalls prior same-channel context through `ScopedRecall`; no cross-channel (SMS↔portal↔voice) switching code path exists.
- [ ] T030 [MARKETING] Full existing **010 voice suite stays green** after the shim upgrades — run `backend/tests/voice/` (the 116-test cumulative suite) against the upgraded shims. (deps: T026, T027, T028, T029)
  - *Verify*: **116/116** 010 voice tests pass with zero regressions after `channel_binding_shim`/`consent_shim`/`HouseholdSummary` are backed by real 011 components (the T017 boundary adapter does not break any 010 ChannelBinding consumer); **preserve-strings check** — the string values of `VerificationLevel` (`none|soft_confirmed|strong`) and `VerificationState` (`unverified|soft_confirmed`) are unchanged and the tests hard-asserting them (`== "none"`, `== "soft_confirmed"`, `VerificationState.SOFT_CONFIRMED.value == "soft_confirmed"`) still pass — the 4-tier translation lives only at the core-binding edge (H2).

---

## Phase 9 — Phase G: Test + red-team + verification (gates go-live; security boundary)

- [ ] T031 [US3] [MARKETING] Scoping **red-team** harness in `backend/tests/relationship/test_scoping_red_team.py` — for each audience (owner/manager/staff/client_verified/caller_unverified) request schedule availability, own-household pet detail, **another household's detail**, and financial detail, plus explicit wrong-person reveal attempts against the collision fixture. (deps: T020, T021, T007)
  - *Verify*: **wrong-person reveal = 0** across the entire collision fixture (SC-001); every fact with no explicit allow rule is refused (deny-on-missing-rule); every reveal/withhold decision is present in `reveal_decision_log`.
- [ ] T032 [US4] Shared-line collision red-team in `backend/tests/relationship/test_shared_line.py` — two households sharing one number; drives resolve → disambiguate → reveal. (deps: T010, T011, T028)
  - *Verify*: the full candidate set is returned (**0** silent single-picks, SC-003); Vera disambiguates neutrally; **no candidate name is ever spoken on a multi-candidate result**; zero household-specific detail is revealed until exactly one candidate is confirmed.
- [ ] T033 [US5] Spoofed-caller-ID / soft-confirm-as-auth red-team in `backend/tests/relationship/test_verification_red_team.py` — a matched (or spoofed-matching) number requests changes with no / insufficient knowledge factors. (deps: T015, T016, T017)
  - *Verify*: a spoofed caller-ID authorizes **0** changes; soft-confirm alone authorizes **0** changes; a high-sensitivity action always requires 2 factors or a staff callback; **an INCORRECT knowledge-factor value is rejected** — a wrong pet name (no match in `patient_household_link`) and a wrong appointment day (no match in the 010 schedule store) each fail the factor and block the change (red-team case proving the bar validates, not merely prompts — H3/FR-018); every attempt writes a `verification_challenge` row (SC-005 = 0).
- [ ] T034 Migration verification harness in `backend/tests/relationship/test_migration.py` — runs T008 against a fixture flat-owner set derived from the T007 corpus and asserts link preservation. (deps: T008, T007)
  - *Verify*: **100%** link preservation (SC-007) — zero orphaned pets, zero lost contacts; a seeded broken-link case makes the migration abort loudly rather than drop silently.
- [ ] T035 [US6] Consent timing + honor harness in `backend/tests/relationship/test_consent.py` — inbound STOP timing, outbound suppression, inbound-still-served, opt-back-in. (deps: T024, T025)
  - *Verify*: STOP recorded + staff-visible **≤60 s in ≥99%** of sim cases (SC-006); **100%** outbound suppression on covered channels (SC-002); an opted-out inbound call is still served **and persists a `consent_record` disclosure via the 010 T033 path** (asserting the disclosure record exists, not just that service continued — M6/FR-023); opt-back-in is audited.
- [ ] T036 [US2] Auto-ID + soft-confirm **rate** audit in `backend/tests/relationship/test_auto_id_rate.py` — the **build-time proxy** for SC-004: measures the auto-identify+soft-confirm rate on matched single-contact numbers across the synthetic fixture (the ≥90% figure on *real* audited pilot data is a Pilot-Activation gate, not this build — M2). (deps: T013, T014)
  - *Verify*: **every** exact single-contact-match inbound number in the fixture auto-identifies + soft-confirms (build-time proxy passes; single-match IDs by construction), and every non-single-match correctly falls back to neutral with no name spoken (SC-004 build-time proxy; real-data ≥90% deferred to Pilot-Activation).

---

## Pilot-Activation (config-only; **NOT in this build**)

Live-mode flips + external hard gates, deferred per the implementation-reality binding:
- Register the **real Twilio inbound webhook** behind the T022 `handle_inbound` seam; flip `INBOUND_LIVE=true` (config swap over the T006 sim seam — no code change).
- Run the resolver's **real ezyVet-export identity audit** (T014 against production exports, not the synthetic corpus); only on a clean audit does auto-ID leave `audit_only` mode and enable live soft-confirm (T013).
- **SC-004 real-data gate (M2)**: confirm the **≥90% auto-ID + soft-confirm rate on audited real pilot data** — the field figure SC-004 defers as a Pilot-Activation gate (T036 measures only the build-time synthetic proxy; the real rate is verified here against pilot/ezyVet data alongside the identity audit).
- VP-9 **vet-signed `memory_scoping` policy** content loaded + `signed_by`/`active` set (T003 ships unsigned; gates live client-facing reveal).
- **Counsel sign-off** on the TCPA consent-state matrix + no-training voice/STT vendor DPA clauses (In re Otter.AI) before any live outbound suppression relies on it.
- **Core confirms the mandatory-audience recall rail** → delete the T020 `ScopedRecall` shim and switch callers to core `scoped_recall` (policy data C is unchanged); until then the shim holds the rail.
- **VP-1 Postgres + RLS** provisioned, or the single-clinic app-scoped Postgres degradation (same posture as 010).

---

## Dependencies & Critical Path

**Phase order (blocking)**: Setup → Foundational → A → B → C → D → E → F → G. Within a phase, `[P]` tasks may run concurrently.

**Critical path (existential privacy-boundary spine)**:
`T001 → T004 → T007 → T010 → T011 → T018 → T019 → T020 → T021 → T031 → T032`

**Second load-bearing chain (migration correctness, SC-007)**:
`T001 → T004 → T005 → T008 → T034`

**Parallel opportunities**: T001/T002/T003 (setup); T005‖T006 (entity_ref vs inbound sim); Phase B resolver (T010→T011→T013) with review-queue T012 alongside; verification Phase C (T015→T016→T017) parallel with scoping Phase D (T018→T019→T020) once T004 lands; the four Phase-F shim upgrades T026‖T027‖T028‖T029 before the T030 green-suite gate; Phase-G red-team harnesses T031/T032/T033/T034/T035/T036 largely parallel once their targets exist.

**MVP scope**: US1–US4 (read-only recognition + non-leak) = Setup + Foundational + Phase A + Phase B + Phase D — the demoable, red-teamed identity-and-scoping moat. US5 (verification bar) and US6 (consent/inbound) ship alongside per spec (P1 read-only value lands first; P2 change/consent follows).

---

## Marketing Output
**Produced by**: speckit-tasks — 2026-07-10

### Demoable Milestones

1. **The Recognition** (after T010 + T013 + T028): a call from a number matching exactly one contact — Vera opens "Hi Mrs. Alvarez — is this about Rex's follow-up?", soft-confirm, identification only; the reveal log shows every fact she chose to share and why. The continuity moat, made felt.
2. **The Non-Leak — the proof** (after T010 + T011 + T012 + T032): a call from the *shared* household number — Vera never guesses a name, disambiguates neutrally without reading names aloud, reveals nothing household-specific until one caller resolves; the old `LIMIT 1` silent-pick is gone and a probable-duplicate lands in the staff review queue, never auto-merged.
3. **The Bar & the Wrong Person** (after T015 + T020 + T031): a soft-confirmed caller asking to change a contact email hits the higher (two-factor / staff-callback) bar and is blocked when it isn't cleared; a red-team caller asking another household's balance is default-denied, refused, and logged.
4. **Opt Out, Honored Everywhere** (after T022 + T024 + T025): a client texts "STOP" — recorded, confirmed, staff-visible in seconds; every Vera-initiated outbound to that channel stops, yet when that client calls in they're still served, with disclosure.
5. **The Migration Proof** (after T008 + T034): the flat owner→patient model lifts into households with 100% link preservation — zero orphaned pets, zero lost contacts — the substrate every recognition moment stands on.

### [MARKETING] Tagged Tasks Summary

The following tasks are customer-visible or announcement-blocking:

| Task ID | Description | Reason |
|---|---|---|
| T008 | Flat owners→household migration (100% link preservation) | Announcement-blocking: SC-007 — no recognition is representable until the family substrate exists and every link survives. |
| T010 | The `LIMIT 1` kill — full candidate set, never a silent single-pick | Announcement-blocking: SC-003 — this is the live privacy bug; it cannot ship leaking. |
| T013 | Auto-ID + soft-confirm recognition (name greeting) | Customer-visible: the first thing a recognized caller hears; the differentiator VP-3 ships on. |
| T015 | Tiered verification bar before any change | Announcement-blocking: SC-005 — zero changes on caller-ID/soft-confirm alone is a hard security gate. |
| T020 | ScopedRecall rail (mandatory audience, default-deny) | Announcement-blocking: SC-001 — the privacy boundary; unscoped client-facing recall must be unrepresentable before any reveal. |
| T022 | Inbound STOP webhook seam | Customer-visible: how a client's opt-out is even received; the TCPA/trust surface. |
| T028 | HouseholdSummary audience-scoped projection | Customer-visible: the recognition/continuity payoff surface Vera greets from. |
| T030 | 010 voice suite stays green after shim upgrades | Announcement-blocking: the 010 Voice pilot cannot regress when 4a lights up its shims. |
| T031 | Scoping red-team (wrong-person reveal = 0) | Announcement-blocking: the security-boundary gate — red-teamed to zero before any client-facing reveal. |

**Total [MARKETING] tasks**: 9 of 37 tasks.
**Milestone**: All [MARKETING] tasks must be ✅ before launching or announcing this feature.
