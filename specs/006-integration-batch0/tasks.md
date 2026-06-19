# Integration Batch 0 — Tasks

**Feature**: integration-batch0
**Spec**: specs/006-integration-batch0/spec.md
**Date**: 2026-06-19
**Total tasks**: 59

---

## Phase 1 — Schema & Models

- [ ] T001 `repository.py`: Add `CREATE TABLE IF NOT EXISTS` for `integration_definitions`, `integration_credentials`, `integration_statuses` to `_init_db()`
- [ ] T002 `repository.py`: Add `CREATE TABLE IF NOT EXISTS` for `migration_runs`, `migration_flags` to `_init_db()`
- [ ] T003 `repository.py`: Add `CREATE TABLE IF NOT EXISTS` for `lab_results` to `_init_db()`
- [ ] T004 `repository.py`: Add `ALTER TABLE patient_images ADD COLUMN` migrations for `source`, `modality`, `report_text`, `dicom_study_uid`, `imaging_system`, `study_date` (each wrapped in `try/except`)
- [ ] T005 `models.py`: Add `IntegrationDefinition`, `IntegrationStatus`, `LabAnalyte`, `LabResult`, `MigrationRun`, `MigrationFlag` Pydantic models

## Phase 2 — Credentials & Health Agent (INT-001, INT-002)

- [ ] T006 `repository.py`: Add `save_integration_credential(clinic_id, integration_id, key_name, encrypted_value)`, `get_integration_credentials(clinic_id, integration_id)`, `delete_integration_credentials(clinic_id, integration_id)`
- [ ] T007 `repository.py`: Add `upsert_integration_status(status: IntegrationStatus)`, `get_integration_status(clinic_id, integration_id)`, `get_all_integration_statuses(clinic_id)`
- [ ] T008 `repository.py`: Add `seed_integration_definitions()` — INSERT OR IGNORE all 11 definitions; call from `on_startup` if table empty
- [ ] T009 Create `backend/agents/integration_health.py` — `CredentialsAgent` (encrypt/decrypt/test) + `HealthMonitor` (sweep all configured, update statuses)
- [ ] T010 `main.py`: `GET /api/settings/integrations` — list definitions + statuses for clinic
- [ ] T011 `main.py`: `POST /api/settings/integrations/{integration_id}/credentials` — encrypt + save + test + return status
- [ ] T012 `main.py`: `POST /api/settings/integrations/{integration_id}/test` — re-run connectivity test
- [ ] T013 `main.py`: `DELETE /api/settings/integrations/{integration_id}/credentials` — revoke credentials, set status unconfigured
- [ ] T014 `main.py`: `GET /api/settings/integrations/health` — summary: `any_disconnected`, statuses list

## Phase 3 — Migration Agent (INT-003, INT-004)

- [ ] T015 `repository.py`: Add `create_migration_run()`, `update_migration_run()`, `get_migration_run()`, `save_migration_flag()`
- [ ] T016 Create `backend/agents/migration.py` — `AvimarkMigrationAgent`: parse ZIP, import owners → patients → visits → care_events → prescriptions; idempotent (`INSERT OR IGNORE`); flag bad records
- [ ] T017 `migration.py`: `CornerstoneMigrationAgent` — subclass of Avimark with different field mapping; stub ezyVet placeholder
- [ ] T018 `main.py`: `POST /api/migration/upload` — accept multipart ZIP, create `MigrationRun`, run agent asynchronously (use `asyncio.create_task`)
- [ ] T019 `main.py`: `GET /api/migration/{run_id}/status` — return current run state + phase + counts
- [ ] T020 `main.py`: `GET /api/migration/{run_id}/report` — return completed run full report
- [ ] T021 `main.py`: `GET /api/migration/{run_id}/flagged.csv` — return CSV of flagged records (`Response` with `media_type="text/csv"`)

## Phase 4 — Lab Agent Core (INT-050)

- [ ] T022 `repository.py`: Add `save_lab_result()`, `get_lab_results_for_patient()`, `get_lab_results_for_timeblock()`, `get_lab_result()`, `acknowledge_lab_result()`
- [ ] T023 Create `backend/agents/lab_agent.py` — `LabAgent`: normalise → match patient (by `lab_order_id`, fallback name match) → parse analytes → classify flags (H/L/HH/LL) → compute `is_critical` → save → update risk score → push action queue item if critical → log via `_log1`
- [ ] T024 `main.py`: `POST /api/webhooks/idexx/result` — validate HMAC signature (skip gracefully if secret not configured) → call `LabAgent.process(payload, provider='idexx')`
- [ ] T025 `main.py`: `GET /api/patients/{patient_id}/lab-results` — return all lab results for patient, newest first
- [ ] T026 `main.py`: `GET /api/timeblocks/{timeblock_id}/lab-results` — return results linked to appointment
- [ ] T027 `main.py`: `POST /api/lab-results/{id}/acknowledge` — update status → `acknowledged`, record `acknowledged_by` + `acknowledged_at`
- [ ] T028 `main.py`: `POST /api/simulate/lab-result` — demo helper: generate realistic mock IDEXX payload → call `LabAgent.process()` → return result (seeded panel templates: `cbc`, `chemistry`, `urinalysis`; `include_critical` flag adds one HH analyte)

## Phase 5 — Additional Lab Providers (INT-051–054)

- [ ] T029 `main.py`: `POST /api/webhooks/antech/result` — Antech field mapping → normalise to VPMA format → call same `LabAgent.process(payload, provider='antech')`
- [ ] T030 `main.py`: `POST /api/webhooks/heska/result` — call `LabAgent.process(provider='heska')`
- [ ] T031 `main.py`: `POST /api/webhooks/vetscan/result` — call `LabAgent.process(provider='vetscan')`
- [ ] T032 `main.py`: `POST /api/webhooks/imaging/result` — `ImagingAgent`: create `PatientImage` with modality + report_text + source=modality; notify vet; log
- [ ] T033 `main.py`: `POST /api/lab-results/import` — accept multipart CSV; detect format (Vetscan/Abaxis by header row); parse; call `LabAgent.process(provider='imported')`

## Phase 6 — Frontend: Settings / Integrations (INT-001, INT-002)

- [ ] T034 Create `frontend/src/components/IntegrationsSettings.tsx` — grid of integration cards: name, emoji, module badge, status badge (`🟢/🟡/🔴/⚪`), "Configure" button; fetch from `GET /api/settings/integrations`
- [ ] T035 `IntegrationsSettings.tsx`: Configure modal — labelled input fields per `required_keys`; "Save & Test" button; spinner state; inline success/error message; close on success
- [ ] T036 `IntegrationsSettings.tsx`: connectivity test UX — loading spinner on card during test; animated badge transition on result
- [ ] T037 `IntegrationsSettings.tsx`: "Remove Credentials" button in modal (with confirmation) → calls DELETE endpoint
- [ ] T038 Add `/settings` route to `frontend/src/app/` with `IntegrationsSettings` as default view; add "Settings" link to nav header
- [ ] T039 Header component: add small `⚠️` warning dot when `any_disconnected: true` from health endpoint; clicking navigates to `/settings`

## Phase 7 — Frontend: Lab Results (INT-050–054)

- [ ] T040 `VetAppointmentCard.tsx` Labs tab: fetch `GET /api/timeblocks/{id}/lab-results`; render list of result panels with panel name, provider badge, received timestamp
- [ ] T041 Labs tab: analyte table — columns: Analyte, Value, Unit, Ref Range, Flag; amber row for `H`/`L`, red row for `HH`/`LL`; flag column shows emoji: `⬆` `⬇` `🔴⬆` `🔴⬇`
- [ ] T042 Labs tab: critical toast — if any result has `is_critical: true` and `status != 'acknowledged'`: show red toast `⚠️ CRITICAL — {analyte} {value}` with "Acknowledge" button
- [ ] T043 Labs tab: "Import Result" button → file picker → POST to `/api/lab-results/import` → result appears instantly
- [ ] T044 Labs tab: "Simulate Lab Result" button (visible in demo mode only) → POST to `/api/simulate/lab-result` → result appears with a brief animation
- [ ] T045 Action queue: add `critical_lab` card type — red border, patient name, panel name, critical analyte + value; "Acknowledge" button → POST acknowledge endpoint → card disappears
- [ ] T046 Action queue: add `unmatched_lab` card type — shows panel name + provider; "Assign" button → patient search modal → on assign: PATCH lab result with patient_id

## Phase 8 — Frontend: Imaging Tab (INT-053)

- [ ] T047 `VetAppointmentCard.tsx` Imaging tab: add modality filter bar — `All | 📷 Photos | 🦴 X-Ray | 🔊 Ultrasound | 🧠 CT/MRI`; filters `source` field client-side
- [ ] T048 Imaging tab: source badge on each image — `Owner Upload` (grey) vs `X-Ray` / `Ultrasound` etc. (blue clinical badge)
- [ ] T049 Imaging tab: if `report_text` present — show collapsible "📋 Radiologist Report" section below image thumbnail; collapsed by default

## Phase 9 — Frontend: Migration UI (INT-003)

- [ ] T050 Create `frontend/src/components/DataMigration.tsx` — dropzone for ZIP upload; source system selector (`Avimark` | `Cornerstone`); "Start Migration" button → POST upload → store `run_id`
- [ ] T051 `DataMigration.tsx`: phase progress bar — poll `GET /api/migration/{run_id}/status` every 2s during `running`; show phase label + running count per entity
- [ ] T052 `DataMigration.tsx`: completed state — show report card (counts per entity, flagged count); "Download Flagged Records" button → fetch CSV
- [ ] T053 Add Data Migration section to `/settings` route alongside Integrations

## Phase 10 — Seed Data & Demo Fixtures

- [ ] T054 `seed_data.py`: Add `seed_integration_definitions()` — INSERT OR IGNORE all 11 integration definitions; call from startup
- [ ] T055 `seed_data.py`: Add `lab_order_id` values to 3 seeded historical timeblocks (so simulated IDEXX result can match immediately in demo)
- [ ] T056 `seed_data.py`: Add `seed_lab_data()` — seed 1 pre-existing LabResult for Buddy: CBC panel with elevated WBC (`H`) and critical BUN (`HH`), `status='received'`; visible immediately in demo
- [ ] T057 Create `specs/006-integration-batch0/fixtures/avimark-sample.zip` — sample Avimark ZIP with 5 patients, 3 owners, 10 visits, 5 vaccines, 3 prescriptions; used for migration demo

## Phase 11 — Commit

- [ ] T058 `git add -A && git commit -m "feat(int-batch0): Core & cross-cutting integrations (INT-001/002/003/004/050-054)"`
- [ ] T059 `git push origin main`
