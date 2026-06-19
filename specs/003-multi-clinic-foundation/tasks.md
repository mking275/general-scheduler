# Tasks: Multi-Clinic Foundation — F007

**Feature**: `003-multi-clinic-foundation`  
**Plan**: [plan.md](plan.md) | **Spec**: [spec.md](spec.md) | **Data Model**: [data-model.md](data-model.md) | **API**: [contracts/api.md](contracts/api.md)  
**Generated**: 2026-06-19  
**Depends on**: Phase 2 tasks T001–T037 complete

> **US label mapping**: US1=Clinic-Aware Board, US2=Floating Vet, US3=Cross-Clinic Records, US4=Regional Manager View

---

## Dependencies

```
US1 (Clinic Board) ─────────────────────────────────────────┐
US2 (Floating Vet) ─────── depends on US1 (clinic context)  │
US3 (Cross-Clinic Records) ─── mostly independent of US2    │
US4 (Regional Manager) ─── depends on US1 (clinic data)     │
```

US1 must be complete before US2 and US4. US3 is independently buildable after the schema (Phase 1).

> **I2 — Build-order note**: plan.md build order maps to task IDs as: schema(T001)→models(T002)→repo CRUD(T003-T004)→seed(T006)→resolver(T005)→endpoints(T007)→solver extension(T011)→UI(T008-T010)→regional view(T016-T017). Task numbering diverges from plan.md diagram intentionally (parallel tasks grouped by phase).

---

## Phase 1 — Setup

- [x] T001 Extend SQLite schema in `backend/repository.py` — create `clinics` table (id, name, address, phone, email, timezone, color_hex, is_active) with a `UNIQUE` constraint on `name` (I1 — enforces data-model.md validation rule); create `vet_clinic_assignments` table (id, vet_id, clinic_id, schedule_days JSON, is_primary); add `clinic_id` column to `resources`, `timeblocks`, and `patients` tables via `ALTER TABLE … ADD COLUMN` wrapped in try/except
- [x] T002 Extend `backend/models.py` — add `Clinic` and `VetClinicAssignment` Pydantic models; extend `Resource` with `clinic_id: Optional[str]`; extend `TimeBlock` with `clinic_id: Optional[str]`; extend `Patient` with `home_clinic_id: Optional[str]`

---

## Phase 2 — Foundational

- [x] T003 [P] Add clinic CRUD to `backend/repository.py` — `get_all_clinics()` (sorted by name asc), `get_clinic(id)`, `create_clinic(clinic)`, `get_default_clinic()` (returns first alphabetically)
- [x] T004 [P] Add `VetClinicAssignment` CRUD to `backend/repository.py` — `get_assignments_for_vet(vet_id)`, `get_assignments_for_clinic(clinic_id)`, `save_assignment(assignment)`, `delete_assignment(id)`; add `get_vets_available_at_clinic(clinic_id, day_name)` using the SQL pattern from data-model.md
- [x] T005 Create `backend/agents/clinic_resolver.py` — implement `ClinicResolver` class with: `get_default_clinic_id()`, `is_vet_available_at_clinic(vet_id, clinic_id, date)` (checks day-of-week), `get_next_available_date(vet_id, clinic_id, from_date, lookahead_days=14)` (14-day scan), `format_conflict_message(vet_name, blocking_clinic, target_clinic, next_date)` (produces FR-013 message format)
- [x] T006 Extend `backend/seed_data.py` — add 2 `Clinic` records (Downtown: `#6C63FF`, Westside: `#00BFA6`); assign existing vets to Downtown; add 1 floating vet (Dr. Chen) with assignments: Downtown on Mon/Wed/Fri, Westside on Tue/Thu; assign existing rooms to Downtown; add 2 Westside rooms; distribute existing seeded appointments across both clinics; call seeding at startup if `clinics` table is empty

---

## Phase 3 — US1: Clinic-Aware Schedule Board

**Story goal**: Header shows selected clinic; switching clinic re-renders schedule with only that clinic's data.  
**Independent test**: 2 clinics seeded → switch clinic → board shows only that clinic's rooms and appointments → header colour accent changes.

- [x] T007 [US1] Add `GET /api/clinics` and `GET /api/clinics/summary` endpoints in `backend/main.py`; wire `get_all_clinics()` from repository; implement summary query from data-model.md SQL pattern; for `total_slots` in summary: compute as `COUNT(DISTINCT vet_clinic_assignments.vet_id) * floor(9 * 60 / 30)` per clinic (assumes 9-hour clinic day, 30-min average appointment) — this gives a fixed denominator appropriate for demo purposes (U1); add `clinic_id` query param to `GET /api/resources` (filter when present, return all when absent)
- [x] T008 [P] [US1] Create `frontend/src/components/ClinicSwitcher.tsx` — dropdown showing clinic name + colour dot for each clinic; currently selected clinic displayed in header; `onClinicChange(clinicId)` callback; apply `--clinic-color` CSS custom property on `document.body` on switch; hide component entirely when API returns only 1 clinic (FR-009 equivalent for clinics)
- [x] T009 [US1] Update `frontend/src/app/page.tsx` — fetch `/api/clinics` on load; set `clinicId` state to `clinics[0].id` (alphabetically first); pass `clinicId` and `onClinicChange` to Dashboard; pass `clinicColor` for CSS variable application
- [x] T010 [US1] Update `frontend/src/components/Dashboard.tsx` — accept `clinicId` prop; pass `clinicId` as query param to all data-fetching calls (appointments, rooms, resources); re-fetch when `clinicId` changes; schedule board re-render must complete in <1s (SC-001)

---

## Phase 4 — US2: Floating Vet Scheduling

**Story goal**: Booking respects vet-clinic-day assignments; conflict messages name the blocking clinic and next available date.  
**Independent test**: Book floating vet at their non-assigned clinic on their non-assigned day → receive specific conflict message with correct alternative.

- [x] T011 [US2] Extend `POST /api/schedule` in `backend/main.py` — accept optional `clinic_id` in request body; before running `HeuristicSolver`, call `ClinicResolver.is_vet_available_at_clinic()` for each candidate vet; remove unavailable vets from candidate list; if the explicitly requested vet is unavailable, call `format_conflict_message()` and return **HTTP 409** with body `{"error": "<formatted conflict message>", "logs": [...CLINIC RESOLVER steps]}` (U3 — HTTP status explicitly 409 per spec FR-013 and contracts/api.md)
- [x] T012 [P] [US2] Add `GET /api/resources/vets/available?clinic_id={id}&date=YYYY-MM-DD` endpoint in `backend/main.py` — calls `get_vets_available_at_clinic(clinic_id, day_name)`; adds `is_floating` and `visiting` fields to each vet in response
- [x] T013 [US2] Update `frontend/src/components/AppointmentCard.tsx` — when appointment card's assigned vet has `visiting: true`, show a 📍 pin icon next to vet name with tooltip "Visiting from [primary clinic name]"

---

## Phase 5 — US3: Cross-Clinic Patient Records

**Story goal**: Patient history visible at any clinic; home-clinic banner shown when patient is seen away from home clinic.  
**Independent test**: Patient with home_clinic_id=Downtown → book at Westside → card shows full history + "Home clinic: Downtown" banner.

- [x] T014 [P] [US3] Extend `GET /api/patients` response in `backend/main.py` — add `home_clinic_id` and `home_clinic_name` fields (join with clinics table); no clinic filter applied (global search)
- [x] T015 [US3] Update `frontend/src/components/PatientPanel.tsx` — when `patient.home_clinic_id` differs from the currently active `clinicId`, render a banner: "🏥 Home clinic: [home_clinic_name]. Viewing full cross-location history." — styled as a subtle info strip at top of panel

---

## Phase 6 — US4: Regional Manager View

**Story goal**: Regional Manager role shows side-by-side clinic columns with today's stats; zero-appointment clinics show "No appointments today".  
**Independent test**: Select Regional Manager role → 2 columns render within 2s → one column shows "No appointments today" → clicking column drills into that clinic's schedule.

- [x] T016 [P] [US4] Create `frontend/src/components/RegionalManagerView.tsx` — fetch `GET /api/clinics/summary` on mount; render one column per clinic; each column: clinic name (coloured header), appointment count, utilisation % bar, high-risk count (red if >0); empty state: "No appointments today" placeholder; click handler calls `onClinicSelect(clinicId)` to drill in; the <2s SC-004 target is measured from **role selection click** to all columns rendered with data — use a loading skeleton during fetch to keep UI responsive (A1)
- [x] T017 [US4] Update `frontend/src/components/RoleSelector.tsx` — add "Regional Manager" as 4th role option; update `frontend/src/components/Dashboard.tsx` to render `RegionalManagerView` when role = "regional_manager"; clicking a clinic column switches `clinicId` state and role to "front_desk" (drill-in behaviour per FR-019)

---

## Phase 7 — Polish & Cross-Cutting

- [x] T018 Extend appointment seeding in `backend/seed_data.py` — **appointments only** (clinics and vet_clinic_assignments are already seeded in T006; do not re-seed them here — D1): ensure at least 3 Downtown appointments and 1 Westside appointment; vary risk levels across appointments; ensure at least 1 patient with `home_clinic_id` = Westside is booked at Downtown (triggers cross-clinic banner in demo)
- [x] T019 [P] Update `frontend/src/components/VerboseLog.tsx` — add distinct styling for `CLINIC RESOLVER` steps (indigo); add clinic name to `DISPATCH` log step when `clinic_id` is present (e.g. "DISPATCH: Confirmed at Paws & Claws Westside")
- [x] T020 [P] Update `GEMINI.md` — update SPECKIT block to reference `specs/003-multi-clinic-foundation/plan.md`
- [x] T021 Smoke-test F007 demo flow — (a) **single-clinic backward-compat**: temporarily set seed to 1 clinic → verify `ClinicSwitcher` is hidden and Regional Manager column shows "Add a second clinic to unlock multi-clinic reporting" (SC-005); (b) **full 2-clinic flow**: load app → verify Downtown default → switch to Westside → book appointment → attempt to book Dr. Chen on wrong day → verify HTTP 409 conflict message names blocking clinic and next date → switch to Regional Manager role → verify both clinic columns render in <2s → verify zero-appointment column shows "No appointments today" → verify cross-clinic patient banner → confirm all CLINIC RESOLVER Verbose Log steps visible

---

## Parallel Execution Opportunities

| Group | Tasks |
|---|---|
| Schema + models | T001, T002 (sequential) |
| Repo CRUD | T003, T004 (parallel after T001) |
| Clinic endpoints + ClinicSwitcher | T007, T008 (parallel after T003/T004) |
| Cross-clinic patients + floating vet endpoint | T012, T014 (parallel) |
| Regional Manager + RoleSelector update | T016, T017 (parallel after T007) |
| VerboseLog update + GEMINI.md | T019, T020 (parallel) |

---

## Summary

| Phase | Tasks | User Story |
|---|---|---|
| Phase 1 — Setup | T001–T002 | — |
| Phase 2 — Foundational | T003–T006 | — |
| Phase 3 — Clinic-Aware Board | T007–T010 | US1 (P1) |
| Phase 4 — Floating Vet | T011–T013 | US2 (P1) |
| Phase 5 — Cross-Clinic Records | T014–T015 | US3 (P1) |
| Phase 6 — Regional Manager | T016–T017 | US4 (P2) |
| Phase 7 — Polish | T018–T021 | — |
| **Total** | **21 tasks** | |

**MVP scope**: Phases 1–3 (T001–T010) — clinic-aware schedule board with location switcher.  
**Full demo scope**: All 21 tasks.  
**Estimated parallelisable tasks**: 9 of 21 marked `[P]`.
