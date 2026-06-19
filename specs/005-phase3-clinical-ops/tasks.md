# Tasks: Phase 3 Clinical Operations (VPMA v1.1)

**Feature**: specs/005-phase3-clinical-ops  
**Input**: plan.md · spec.md · data-model.md · contracts/api.md · research.md · quickstart.md  
**Constitution**: .specify/memory/constitution.md

---

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel with other [P] tasks in same phase (different files)
- Tasks marked `[P]` have no intra-phase file conflicts

---

## Phase 1 — Schema & Models (Shared Infrastructure)

⚠️ **BLOCKING**: All subsequent phases depend on these tables existing.

- [ ] T001 In `backend/repository.py` `_init_db()`: add `CREATE TABLE IF NOT EXISTS` for `breed_protocols`, `waitlist`, `care_protocols`, `care_events`, `prescriptions`, `refill_requests` (exact DDL in data-model.md)
- [ ] T002 In `backend/repository.py` `_init_db()`: add `ALTER TABLE timeblocks ADD COLUMN confirmation_status TEXT DEFAULT 'not_sent'`, `confirmed_at TEXT`, `reminder_sent_at TEXT` — each wrapped in try/except
- [ ] T003 [P] In `backend/models.py`: add Pydantic models `BreedProtocol`, `WaitlistEntry`, `CareProtocol`, `CareEvent`, `Prescription`, `RefillRequest`, `ForecastWeek`, `ForecastResult`
- [ ] T004 [P] In `backend/repository.py`: add CRUD method stubs for each new table — `get/create/update` for breed_protocols, waitlist, care_protocols, care_events, prescriptions, refill_requests (see plan.md Phase 1)

**Checkpoint**: `python3 -c "from backend.repository import db; print('schema OK')"` passes with no errors

---

## Phase 2 — Seed Data (All Features)

⚠️ **BLOCKING**: Agents need seeded data; SC-P3-004 requires ≥2 overdue care items on startup.

- [ ] T005 In `backend/seed_data.py`: add `seed_phase3_data()` function — seeds `breed_protocols` (12 entries per data-model.md), `care_protocols` (8 entries), `waitlist` (3 entries with varied urgency for existing patients), `care_events` (events for Buddy/Rex/Luna with ≥2 where `next_due_date < today`), `prescriptions` (2 active Rx on existing patients)
- [ ] T006 In `backend/seed_data.py`: add seeding of 8 weeks of historical completed timeblocks for forecast linear regression (use clinic-downtown; vary appointment counts realistically — slight upward trend). **G02**: All historical dates MUST use `datetime.today() - timedelta(weeks=N)` — no hardcoded dates, otherwise regression data will be stale on run.
- [ ] T007 In `backend/main.py` startup handler: call `seed_phase3_data()` after existing seed calls, guarded by `IF NOT EXISTS` check on breed_protocols table

**Checkpoint**: Fresh DB start → `GET /api/care/due-this-month` returns count ≥ 2 with overdue items

---

## Phase 3 — F013: Appointment Reminder & Confirmation (US1)

- [ ] T008 [P] Create `backend/agents/reminder.py` with `ReminderAgent` class: `compose_message(patient, owner, vet, appt_time) -> str`; `process_reply(timeblock_id, reply: str) -> dict` (maps yes/confirm/ok → confirmed, reschedule/cancel/no → reschedule_requested); `log_steps(action)` writes to VerboseLog session
- [ ] T009 [P] In `backend/repository.py`: add `update_confirmation_status(timeblock_id, status, timestamp)` method; add `get_action_queue(clinic_id=None) -> list` (returns timeblocks where confirmation_status IN ('unconfirmed','reschedule_requested'))
- [ ] T010 In `backend/main.py`: add `POST /api/timeblocks/{id}/reminder/send` → calls `ReminderAgent.compose_message()`, sets `reminder_sent_at + confirmation_status='sent'`, returns composed message + verbose_log
- [ ] T011 In `backend/main.py`: add `POST /api/timeblocks/{id}/reminder/reply` → body `{reply: str}`, calls `ReminderAgent.process_reply()`, recalculates risk score delta (−10 to −15 on confirm), returns new status + risk_delta + verbose_log
- [ ] T012 In `backend/main.py`: add `GET /api/timeblocks/action-queue` → returns unconfirmed + reschedule_requested appointments with patient/owner/vet details
- [ ] T013 In `frontend/src/components/AppointmentCard.tsx`: add confirmation status badge (coloured pill); add "Send Reminder" button with dynamic label — `daysOut > 2 ? 'Send Reminder (Early — T-48h+)' : 'Send Reminder (Due — T-24h)'` computed from appointment date vs today
- [ ] T014 Create `frontend/src/components/ReminderPanel.tsx`: slides in below Send Reminder button; shows composed message bubble; preset [YES] [RESCHEDULE] buttons + free-text area; on submit (both preset and free-text) → relay text value to `POST /api/timeblocks/{id}/reminder/reply` as `{reply: string}` → badge updates; Verbose Log streams. **G03**: Free-text input must be wired to the same endpoint as preset buttons — do not silently discard user-typed replies.
- [ ] T015 In `frontend/src/components/Dashboard.tsx`: add "Action Queue" collapsible panel (Front Desk role only) with count badge in header; lists unconfirmed appointments from `GET /api/timeblocks/action-queue`; "Mark Confirmed" manual override button per row

**Checkpoint**: SC-P3-001 — full reminder → confirm flow completable in <90s

---

## Phase 4 — F014: Waitlist & Smart Cancellation Backfill (US3)

- [ ] T016 [P] Create `backend/agents/backfill.py` with `BackfillAgent` class: `score_match(slot: TimeBlock, entry: WaitlistEntry) -> int` (100/80/40 scoring per FR-P3-005); `find_matches(slot) -> list[ScoredMatch]` (sorted by score DESC, urgency DESC, join_date ASC); `make_offer(match) -> dict`; all steps logged via VerboseLog session
- [ ] T017 [P] In `backend/repository.py`: add `get_active_waitlist(clinic_id=None)`, `add_waitlist_entry(entry)`, `update_waitlist_status(id, status)`, `remove_waitlist_entry(id)` methods
- [ ] T018 In `backend/main.py`: add `POST /api/timeblocks/{id}/cancel` → frees slot (set status='cancelled'), calls `BackfillAgent.find_matches()`, returns matches + verbose_log chain
- [ ] T019 In `backend/main.py`: add `GET /api/waitlist`, `POST /api/waitlist`, `POST /api/waitlist/{id}/accept` (books slot, removes entry), `POST /api/waitlist/{id}/decline` (marks expired, returns next match)
- [ ] T020 Create `frontend/src/components/WaitlistPanel.tsx`: cancel confirmation → "Run Backfill Agent?" → Verbose Log streams match chain in real time → top match displayed (patient, score, urgency) → [Accept] [Decline] buttons
- [ ] T021 In `frontend/src/components/Dashboard.tsx`: add waitlist count badge to Front Desk header; "Add to Waitlist" accessible from appointment cards

**Checkpoint**: SC-P3-003 — full cancel → backfill → accept chain, Verbose Log visible <5s

---

## Phase 5 — F018: Breed-Specific Clinical Intelligence (US2)

- [ ] T022 [P] Create `backend/agents/breed.py` with `BreedIntelligenceAgent` class: `get_flags(breed: str, age_years: float) -> list[BreedProtocol]` — case-insensitive partial match (`lower(breed_pattern) in lower(patient.breed)`); filters by `age_threshold_years`; returns all matching protocols
- [ ] T023 [P] In `backend/main.py`: add `GET /api/patients/{id}/breed-flags` → calls BreedIntelligenceAgent, returns flags list (empty list for no match — no errors)
- [ ] T024 In `frontend/src/components/VetAppointmentCard.tsx`: on card open, fetch `/api/patients/{id}/breed-flags`; render amber `🧬 Breed Protocol` banner below patient name if flags exist; render persistent red strip in card header for critical severity flags (brachycephalic) when procedure is Surgery or Dental
- [ ] T025 In `frontend/src/components/VetAppointmentCard.tsx` History tab: render breed flags section above visit list (only if flags.length > 0)
- [ ] T026 In `frontend/src/components/SoapWorkspace.tsx`: add "Breed Considerations" collapsible section pre-populated with flag details from breed-flags API; visible only when patient has active flags

**Checkpoint**: SC-P3-002 — brachycephalic warning visible without extra clicks for Surgery/Dental

---

## Phase 6 — F015: Preventive Care Tracking (US4)

- [ ] T027 [P] Create `backend/agents/care.py` with `CareTrackerAgent` class: `compute_next_due(protocol_id, administered_date) -> date` (administered_date + interval_months); `get_overdue_patients() -> list`; `get_due_this_month() -> list`; all events logged via VerboseLog
- [ ] T028 [P] In `backend/repository.py`: add `get_care_events_for_patient(patient_id)`, `create_care_event(event)`, `get_overdue_care()`, `get_care_due_within_days(days=30)`, `get_all_care_protocols()` methods
- [ ] T029 In `backend/main.py`: add `GET /api/patients/{id}/care-events`, `POST /api/patients/{id}/care-events` (timeblock_id optional), `GET /api/care/due-this-month`, `GET /api/care-protocols`, `GET /api/care/overdue` → returns patients where any `next_due_date < date('now')` (used by Front Desk overdue badge and seeded SC-P3-004 validation). **G01**: endpoint was in contracts/api.md but missing from tasks — now included.
- [ ] T030 In `frontend/src/components/VetAppointmentCard.tsx`: add "Care Plan" tab — fetches `/api/patients/{id}/care-events`; renders care timeline (date, protocol, batch, vet); "Log Care Event" form (protocol dropdown, batch number, date); "Log Historical Care Event" form (same fields, timeblock_id omitted); `🔴 OVERDUE` badge on patient name row if any item overdue. **G05**: VetAppointmentCard.tsx is already 27 KB — extract tab body into `frontend/src/components/CarePlanTab.tsx` to avoid unmanageable file size.
- [ ] T031 In `frontend/src/components/Dashboard.tsx`: add "📋 Care Due This Month (N)" collapsible panel (Front Desk role); each row: patient name, protocol, days until/overdue, status badge, "Book" button that pre-populates quick-book

**Checkpoint**: SC-P3-004 — ≥2 overdue in Care panel on fresh seed; SC-P3-008 Care Plan tab only in Vet role

---

## Phase 7 — F016: Prescription Management (US5)

- [ ] T032 [P] Create `backend/agents/prescription.py`: `DRUG_LIST` (20 drugs), `DRUG_CLASS_MAP` dict; `PrescriptionAgent` class with `check_allergy_conflict(drug_name, patient_flags) -> dict|None`; `compute_supply_ends(issued_date, duration_days) -> date`; `assess_refill_eligibility(prescription_id, patient_id) -> str` ('auto_approve'|'vet_review') — checks `refills_remaining > 0 AND last completed appt within 12mo`
- [ ] T033 [P] In `backend/repository.py`: add `get_prescriptions_for_patient(patient_id)`, `create_prescription(rx)`, `create_refill_request(req)`, `get_pending_refill_requests()`, `approve_refill(id)`, `flag_refill_for_vet(id)` methods
- [ ] T034 In `backend/main.py`: add `GET /api/patients/{id}/prescriptions`, `POST /api/patients/{id}/prescriptions` (runs allergy check; returns conflict without saving if unacknowledged; re-submit with `acknowledged:true` saves), `POST /api/prescriptions/{id}/refill-request` (both roles use same endpoint; `initiated_by` in body), `GET /api/refill-requests`, `POST /api/refill-requests/{id}/approve`, `POST /api/refill-requests/{id}/flag-vet`
- [ ] T035 In `frontend/src/components/VetAppointmentCard.tsx`: add "Rx" tab — fetches active prescriptions; renders list with drug, dose, frequency, refills_remaining, supply_ends_at; issue form with drug typeahead (client-side filter from DRUG_LIST); allergy conflict red banner blocking submit until "Acknowledge & Proceed" clicked; "Request Refill" button per active Rx. **G05**: Extract tab body into `frontend/src/components/RxTab.tsx` sub-component to keep VetAppointmentCard.tsx manageable.
- [ ] T036 In `frontend/src/components/Dashboard.tsx`: add "💊 Refill Requests (N)" collapsible panel (Front Desk role); rows show green `✓ Auto-approve` or amber `⚠ Vet Review`; one-click Approve button decrements refills_remaining and logs action

**Checkpoint**: SC-P3-005 — Amoxicillin on Buddy triggers red allergy conflict banner immediately

---

## Phase 8 — F019: Capacity & Revenue Forecasting (US6)

- [ ] T037 [P] Create `backend/agents/forecast.py`: `FEE_SCHEDULE` dict (≥5 procedures with avg fees); `ForecastAgent` class: `compute_weekly_history(clinic_id, weeks=8) -> list[WeekData]`; `linear_regression(data) -> tuple[float, float]` (pure Python stdlib — no numpy); `classify_trend(slope, pace) -> str` (on_track|action_needed|strong_growth); `generate_insight(clinic_name, trend, weeks) -> str` (2-3 sentence plain English); `forecast(clinic_id) -> ForecastResult`
- [ ] T038 [P] In `backend/repository.py`: add `get_historical_weekly_counts(clinic_id, weeks=8) -> list[dict]` — counts completed timeblocks per week for past N weeks. **G04**: Bucket by ISO week of `start_time` WHERE `status='complete'` (timeblocks has no `completed_at` column). Use `strftime('%Y-%W', start_time)` in SQLite for week grouping.
- [ ] T039 In `backend/main.py`: add `GET /api/clinics/{clinic_id}/forecast` → calls `ForecastAgent.forecast()`, returns `ForecastResult` with 4-week projection + insight + verbose_log
- [ ] T040 Create `frontend/src/components/ForecastChart.tsx`: pure CSS bar chart; 4 bars per clinic; solid fill = booked (CSS background-color), hatched = projected (CSS repeating-linear-gradient diagonal lines); `position: absolute` red dotted line at 90% height for capacity target; AI Insight card below with border-color based on trend (green/amber/blue); Verbose Log shows FORECAST AGENT steps on load
- [ ] T041 In `frontend/src/components/RegionalManagerView.tsx`: fetch `GET /api/clinics/{id}/forecast` for each active clinic on view mount; render `ForecastChart` per clinic below existing clinic summary cards; section loads within 2 seconds

**Checkpoint**: SC-P3-006 — Forecast section renders <2s; both clinics show 4 bars with distinct booked/projected fill

---

## Phase 9 — Polish & Cross-Cutting Concerns

- [ ] T042 [P] Backward compatibility check: run all 7 Scenario quickstart.md curl commands; confirm all v1.0.0 endpoints return 200 with no schema errors introduced by Phase 3 ALTER TABLE migrations
- [ ] T043 [P] Role-correctness audit: switch each role (Front Desk → Vet Tech → Vet → Regional Manager) and verify: Action Queue/Care Due/Refill panels only in Front Desk; Care Plan/Rx/Breed banner only in Vet; Forecast only in Regional Manager; no Phase 3 panels bleed into Vet Tech view
- [ ] T044 Verbose Log audit: manually trigger each agent (Reminder, Backfill, Care, Prescription, Forecast, Breed) and confirm all steps appear in VerboseLog panel with correct `AGENT_NAME: message` format
- [ ] T045 Git: `git add -A && git commit -m "feat(vpma-v1.1): Phase 3 Clinical Ops — F013+F014+F015+F016+F018+F019"`
- [ ] T046 Tag: `git tag v1.1.0 && git push origin main --tags`

---

## Dependencies & Execution Order

```
Phase 1 (T001–T004)   ← No deps. BLOCKS all phases.
Phase 2 (T005–T007)   ← Depends on Phase 1. BLOCKS Phase 3–8 (seed data required).
Phase 3 (T008–T015)   ← Depends on Phase 1+2. Enables Phase 4 (reschedule → backfill).
Phase 4 (T016–T021)   ← Depends on Phase 3 (cancellation flow).
Phase 5 (T022–T026)   ← Depends on Phase 1+2 only. Can run ∥ with Phase 4.
Phase 6 (T027–T031)   ← Depends on Phase 1+2 only. Can run ∥ with Phase 4+5.
Phase 7 (T032–T036)   ← Depends on Phase 6 (uses last-exam data from care events).
Phase 8 (T037–T041)   ← Depends on Phase 1+2 only. Can run ∥ with Phase 3–7.
Phase 9 (T042–T046)   ← Depends on all phases complete.
```

## Implementation Strategy

### MVP First (F013 → F018 → remainder)
1. Complete Phase 1 (schema) → Phase 2 (seed) — REQUIRED before anything
2. Complete Phase 3 (F013 Reminders) — highest demo impact, foundation for backfill
3. Complete Phase 5 (F018 Breed) — pure lookup, zero risk, strong visual wow
4. Validate both features independently → demo-ready checkpoint
5. Continue Phase 4 → 6 → 7 → 8 sequentially

### Parallel Team Strategy
- Dev A: Phase 3 (F013) + Phase 4 (F014)
- Dev B: Phase 5 (F018) + Phase 6 (F015)  
- Dev C: Phase 7 (F016) + Phase 8 (F019)
- All after Phase 1+2 complete

## Notes
- [P] tasks have no intra-phase file conflicts — safe to assign to separate devs
- All backend agents follow existing pattern: class with methods, `log_steps()` via session VerboseLog
- No new pip or npm packages at any task — constitution rule
- All ALTER TABLE migrations use try/except (existing project pattern from F007)
- Commit after each phase or logical group; don't batch all 46 tasks into one commit
