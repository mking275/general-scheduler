# Tasks: Vet Clinic Agentic Features — Phase 2

**Feature**: `002-vet-agentic-features`  
**Plan**: [plan.md](plan.md) | **Spec**: [spec.md](spec.md) | **Data Model**: [data-model.md](data-model.md) | **API**: [contracts/api.md](contracts/api.md)  
**Generated**: 2026-06-19  

## Implementation Strategy

MVP = Phase 3 (US1 — Patient Record Card) alone ships visible value to a demo viewer.  
Each phase after that adds a complete agentic loop. Build order strictly follows the dependency chain:
**F001 → F005 → F004 → F002 → F003 → F006**

> **I1 — US label mapping note**: Tasks are ordered by *build dependency*, not spec priority. The `[US#]` labels in tasks.md map to spec user stories as follows: US1=spec-US1 (Patient Cards), US2=spec-US4 (Role Split), US3=spec-US3 (Risk), US4=spec-US2 (Intake), US5=spec-US5 (Follow-Up), US6=spec-US6 (SOAP). Spec priority (P1/P2/P3) is preserved in the spec.md.

---

## Dependencies

```
US1 (Patient Cards) ──────────────────────────────┐
US2 (Role Split) ──────────────────────────────────┤── all independent of each other
US3 (No-Show Risk) ────────────────────────────────┤
US4 (Pre-Visit Intake) ────────────────────────────┤
  └── US5 (Follow-Up) depends on US4 (completion trigger)
  └── US6 (SOAP Note) depends on US4 (intake data for Subjective)
        └── US5 (Follow-Up) also triggered by US6 (SOAP sign)
```

US1, US2, US3, US4 are independently buildable.  
US5 and US6 should be built after US4 is complete.

---

## Phase 1 — Setup

- [ ] T001 Extend SQLite schema in `backend/repository.py` — add tables: `patients`, `owners`, `pre_exam_briefs`, `risk_scores`, `soap_notes`, `followup_drafts`; add columns to `timeblocks`: `patient_id`, `intake_status`, `followup_status`, `risk_level`; add `status` column to existing rooms table
- [ ] T002 Extend `backend/models.py` — add Pydantic models: `Patient`, `Owner`, `PreExamBrief`, `RiskScore`, `SoapNote`, `FollowUpDraft`, `RoomStatusUpdate`; extend `TimeBlock` with new fields
- [ ] T003 Create `backend/seed_data.py` — seed 10 mock patients across 4 species (dog/cat/bird/exotic), 10 owners, 3 flag types (alert/chronic/first_visit); wire seed call into app startup if `patients` table is empty

---

## Phase 2 — Foundational

- [ ] T004 [P] Add patient CRUD to `backend/repository.py` — `get_all_patients()`, `get_patient(id)`, `create_patient(patient)`, `get_owner(id)`, `get_all_owners()`
- [ ] T005 [P] Add new agent stubs in `backend/agents/` — create `risk.py` (RiskScoringAgent), `soap.py` (SoapDraftAgent), `followup.py` (FollowUpDraftAgent) with empty method signatures matching contracts/api.md
- [ ] T006 Extend `backend/agents/dispatch.py` — after TimeBlock creation, call `RiskScoringAgent.score(timeblock)` and persist result; attach `patient_id` to TimeBlock if provided in the schedule request
- [ ] T007 Create `frontend/src/components/AppointmentCard.tsx` — refactor inline appointment rendering from `Dashboard.tsx` into a standalone card component; props: `timeblock`, `patient`, `riskScore`, `role`; renders existing fields unchanged as baseline

---

## Phase 3 — US1: Patient Record Card

**Story goal**: Every appointment card shows patient name, species icon, flag badges, owner contact.  
**Independent test**: Book appointment → card renders patient name, breed, flag badge, owner phone with no extra clicks.

- [ ] T008 [US1] Implement `GET /api/patients` and `GET /api/patients/{id}` endpoints in `backend/main.py`; wire to repository functions from T004
- [ ] T009 [US1] Implement `GET /api/owners` endpoint in `backend/main.py`
- [ ] T010 [P] [US1] Create `frontend/src/components/PatientPanel.tsx` — species icon map (dog🐕/cat🐈/bird🦜/exotic🦎); flag badge components (red ALERT, yellow CHRONIC, green FIRST VISIT); support rendering multiple flags simultaneously on one patient (e.g. ALERT + CHRONIC); last visit date + procedure; owner name + phone display
- [ ] T011 [US1] Update `AppointmentCard.tsx` — fetch patient data on mount; render collapsed state (name + species icon + flags); render expanded state (full PatientPanel); CSS expand/collapse animation <300ms
- [ ] T012 [US1] Update `page.tsx` — fetch `/api/patients` on load; pass patient lookup map as prop to Dashboard; ensure all existing appointments in seed data have a `patient_id` assigned

---

## Phase 4 — US2: Role-Split UI

**Story goal**: Header toggle switches between Front Desk / Vet Tech / Vet views with distinct layouts per role.  
**Independent test**: Toggle all 3 roles → each renders distinct primary panel; role persists through card interactions.

- [ ] T013 [P] [US2] Create `frontend/src/components/RoleSelector.tsx` — three-tab toggle (Front Desk | Vet Tech | Veterinarian); active tab styling; emits `onRoleChange(role)` callback; session-persistent via `useState` in parent; implement view switch using CSS transitions (opacity + transform) with no React unmount/remount — target <500ms perceived switch to satisfy SC-004
- [ ] T014 [P] [US2] Add `PUT /api/rooms/{id}/status` endpoint in `backend/main.py`; add `update_room_status(id, status, timeblock_id)` to `backend/repository.py`
- [ ] T015 [US2] Create `frontend/src/components/RoomBoard.tsx` — Vet Tech view; grid of room cards showing name, status badge (available/prep/occupied/cleaning), next patient procedure; "Mark Ready" / "Mark Occupied" / "Mark Cleaning" action buttons; calls `PUT /api/rooms/{id}/status`
- [ ] T016 [US2] Create `frontend/src/components/VetView.tsx` — Vet role view; filters appointment list to current vet's appointments only (mock: show all, label with vet name); Pre-Exam Brief summary visible per card; "Open SOAP Note" button stub (wired in US6)
- [ ] T017 [US2] Update `Dashboard.tsx` — integrate `RoleSelector` into header; conditionally render: Front Desk → existing schedule grid + booking input; Vet Tech → `RoomBoard`; Vet → `VetView`; pass `role` prop down to `AppointmentCard`

---

## Phase 5 — US3: No-Show Risk Indicator

**Story goal**: Every appointment card shows a colour-coded risk dot; hover reveals contributing factors.  
**Independent test**: Book 3 appointments with different characteristics → each gets different risk level; hovering dot shows ≥2 factors.

- [ ] T018 [P] [US3] Implement `RiskScoringAgent.score()` in `backend/agents/risk.py` — weighted rules: lead time (<24h=+40, <72h=+20, ≥7d=0), visit type (emergency=-30, wellness=+20), patient status (first_visit=+15, >5 visits=-15), procedure urgency (elective=+15, sick=-10); return `RiskScore` with level + factors list
- [ ] T019 [US3] Add `GET /api/risk/{timeblock_id}` endpoint in `backend/main.py`; add `get_risk_score(timeblock_id)` and `save_risk_score(score)` to `backend/repository.py`
- [ ] T020 [US3] Create `frontend/src/components/RiskBadge.tsx` — coloured dot (green/yellow/red); CSS tooltip on hover showing factors list; accessible via `aria-label`; integrates into `AppointmentCard.tsx` top-right corner

---

## Phase 6 — US4: Pre-Visit Intake Agent

**Story goal**: Trigger intake questionnaire from card; submit mock owner response; receive structured Pre-Exam Brief.  
**Independent test**: Trigger intake → status changes to Pending → submit response → Brief renders with extracted symptoms.

- [ ] T021 [P] [US4] Implement symptom extraction in `backend/agents/intake.py` — add `extract_symptoms(text: str) -> PreExamBrief`; keyword dictionary: lethargy, vomiting, diarrhea, anorexia, coughing, limping, scratching, seizure, collapse, bleeding; duration regex: `(\d+)\s*(day|week|hour)s?\s*(ago|since)?`; severity heuristic: "severe"/"emergency" → high, "little"/"mild" → low, default → mild; `suggested_focus` map per symptom cluster
- [ ] T022 [US4] Add `POST /api/intake/send` endpoint in `backend/main.py` — updates timeblock `intake_status` to `pending`; logs INTAKE AGENT step to session; add `save_pre_exam_brief()` and `get_pre_exam_brief(timeblock_id)` to `backend/repository.py`
- [ ] T023 [US4] Add `POST /api/intake/parse` and `GET /api/intake/{timeblock_id}` endpoints in `backend/main.py` — parse calls `extract_symptoms()`; persists PreExamBrief; updates timeblock `intake_status` to `received`; emit a discrete `log_agent_step()` call to the session stream for each of these stages: (1) "Owner response received — extracting symptoms...", (2) "Parsed → {symptoms list}", (3) "Suggested focus areas: {areas}", (4) "Pre-Exam Brief saved" — satisfying FR-009 and SC-007
- [ ] T024 [P] [US4] Create `frontend/src/components/IntakePanel.tsx` — "Send Intake" button → calls `/api/intake/send` → status badge changes to ⏳ Pending; mock owner response textarea appears; "Submit Response" → calls `/api/intake/parse` → Pre-Exam Brief panel renders: chief complaint, symptom chips (name + duration + severity), owner verbatim quote (italicised), suggested focus tags
- [ ] T025 [US4] Wire `IntakePanel` into `AppointmentCard.tsx` — show in Front Desk role; show Pre-Exam Brief summary (chief complaint only) in Vet role card; intake status badge visible in all roles

---

## Phase 7 — US5: Post-Appointment Follow-Up Agent

**Story goal**: Mark appointment complete → follow-up draft auto-generated → approve with one click.  
**Independent test**: Complete appointment → draft appears in <3s with correct patient name and procedure-appropriate tone.

- [ ] T026 [P] [US5] Implement `FollowUpDraftAgent.generate()` in `backend/agents/followup.py` — 3 tone templates (wellness/surgery/emergency) with slot filling: `{patient_name}`, `{owner_name}`, `{vet_name}`, `{procedure}`, `{recheck_interval}`; tone selection based on procedure type; return `FollowUpDraft`
- [ ] T027 [US5] Add `POST /api/followup/draft`, `PUT /api/followup/{id}`, `POST /api/followup/{id}/approve` endpoints in `backend/main.py`; add `save_followup_draft()`, `update_followup_draft()`, `approve_followup_draft()` to `backend/repository.py`
- [ ] T028a [US5] Add `POST /api/appointments/{timeblock_id}/complete` endpoint in `backend/main.py` — marks timeblock `status` to `complete`; checks for unsigned SOAP note: if unsigned and `force=false`, return HTTP 409 `{"warning": "SOAP note is unsigned", "action_required": "sign_soap_or_force_complete"}`; if SOAP signed or `force=true`, proceed with completion
- [ ] T028b [US5] Wire follow-up trigger into completion flow in `backend/main.py` — on successful completion, call `FollowUpDraftAgent.generate(timeblock)`; persist draft via `save_followup_draft()`; emit FOLLOWUP AGENT log steps to session stream; return `followup_draft_id` in response body
- [ ] T029 [US5] Create `frontend/src/components/FollowUpPanel.tsx` — "Mark Complete" button on card (Front Desk + Vet roles); on HTTP 409 response (SOAP unsigned): display confirmation modal "SOAP note is unsigned — complete anyway?" with Cancel / Force Complete options; on successful completion: panel slides in with generated draft in editable textarea; tone selector (Wellness/Surgery/Emergency) → "Regenerate" re-fetches; "Approve & Send" → calls approve endpoint → shows ✅ Follow-up Sent badge; VerboseLog shows generation steps

---

## Phase 8 — US6: SOAP Note Draft Agent

**Story goal**: Vet opens SOAP workspace → pre-filled draft from intake + procedure template → fill vitals → sign.  
**Independent test**: Open SOAP for appointment with intake brief → Subjective contains chief complaint verbatim → Plan contains procedure-appropriate recommendations → signing marks appointment complete and triggers follow-up.

- [ ] T030 [P] [US6] Implement `SoapDraftAgent.generate()` in `backend/agents/soap.py` — 5 procedure templates (Wellness/Vaccination/Surgery/Dental/Grooming) each with: Subjective slot (filled from PreExamBrief chief_complaint + owner_verbatim), Objective schema (procedure-specific vitals fields + exam checklist keys), Plan standard text; return `SoapNote`
- [ ] T031 [US6] Add `POST /api/soap/draft`, `PUT /api/soap/{id}`, `POST /api/soap/{id}/sign` endpoints in `backend/main.py`; add `save_soap_note()`, `update_soap_note()`, `sign_soap_note()` to `backend/repository.py`; `PUT /api/soap/{id}` MUST return HTTP 409 with `{"error": "SOAP note is signed and read-only"}` if `signed=true` (enforces FR-028 at the API layer); signing calls `FollowUpDraftAgent.generate()` and returns `followup_draft_id`
- [ ] T032 [US6] Create `frontend/src/components/SoapWorkspace.tsx` — full-height right panel (slides in); 4 labelled sections (S/O/A/P); Subjective: pre-filled editable textarea; Objective: procedure-specific vitals form (temperature, HR, RR, weight) + dynamic exam checklist; Assessment: free text with ghost-text hint ("Enter diagnosis..."); Plan: pre-filled editable textarea; "Sign & Complete" button → calls sign endpoint → panel locks to read-only with signed timestamp; VerboseLog shows SOAP AGENT generation step
- [ ] T033 [US6] Wire `SoapWorkspace` into `VetView.tsx` — "Open SOAP Note" button per appointment card fetches/creates draft and opens workspace panel; workspace state (open/closed + which appointment) managed in VetView; signing closes workspace and refreshes appointment status

---

## Phase 9 — Polish & Cross-Cutting

- [ ] T034 Update `backend/seed_data.py` — ensure 8 seeded appointments link to patients; vary appointment characteristics to demonstrate all 3 risk levels; include at least 1 appointment per procedure type (Wellness, Surgery, Dental, Vaccination, Grooming)
- [ ] T035 [P] Update `VerboseLog.tsx` — add distinct styling for new agent steps: `INTAKE AGENT` (blue), `RISK AGENT` (amber), `SOAP AGENT` (purple), `FOLLOWUP AGENT` (green); maintain existing `DISPATCH`, `SOLVER`, `INTAKE` styles
- [ ] T036 Smoke-test full demo flow — book appointment → verify patient card renders → trigger intake → submit owner response → verify brief → switch to Vet Tech → mark room ready → switch to Vet → open SOAP → sign → verify follow-up draft generated → approve → verify all Verbose Log steps visible; confirm role switch completes in <500ms; confirm all 3 risk levels represented in seeded data
- [ ] T037 [P] Commit all changes to GitHub — `git add -A && git commit -m "feat: Phase 2 — agentic vet clinic features (F001-F006)" && git push origin main`

---

## Parallel Execution Opportunities

The following task groups have no inter-dependencies and can be built concurrently:

| Group | Tasks | Who |
|---|---|---|
| Backend models + seed | T001, T002, T003 | Backend |
| Frontend component scaffolds | T007, T013 | Frontend |
| Risk agent + badge | T018, T020 | Either |
| Intake agent + panel | T021, T024 | Either |
| Follow-up agent + panel | T026, T029 | Either |
| SOAP agent + workspace | T030, T032 | Either |

---

## Summary

| Phase | Tasks | User Story |
|---|---|---|
| Phase 1 — Setup | T001–T003 | — |
| Phase 2 — Foundational | T004–T007 | — |
| Phase 3 — Patient Cards | T008–T012 | US1 (P1) |
| Phase 4 — Role Split | T013–T017 | US2 (P2) |
| Phase 5 — Risk Indicator | T018–T020 | US3 (P2) |
| Phase 6 — Intake Agent | T021–T025 | US4 (P1) |
| Phase 7 — Follow-Up Agent | T026–T030 | US5 (P3) |
| Phase 8 — SOAP Note | T031–T034 | US6 (P3) |
| Phase 9 — Polish | T035–T037 | — |
| **Total** | **38 tasks** | |

**MVP scope**: Complete Phases 1–3 (T001–T012) for a shippable increment — patient-enriched appointment cards with full context.  
**Full demo scope**: All 38 tasks.  
**Estimated parallelisable tasks**: 17 of 38 marked `[P]`.
