# Integration Batch 0 — Tasks (Remediated)

**Feature**: integration-batch0
**Spec**: specs/006-integration-batch0/spec.md
**Date**: 2026-06-19
**Total tasks**: 63 (4 added by remediation)

---

## Phase 1 — Schema & Models

- [ ] T001 `repository.py`: Add `CREATE TABLE IF NOT EXISTS` for `integration_definitions`, `integration_credentials`, `integration_statuses` to `_init_db()`
- [ ] T002 `repository.py`: Add `CREATE TABLE IF NOT EXISTS` for `migration_runs`, `migration_flags` to `_init_db()`
- [ ] T003 `repository.py` **(B-01/B-02 fix)**: Do NOT create a new `lab_results` table. Instead, extend the existing `labs` table via `ALTER TABLE` (each wrapped in `try/except`): add `provider TEXT DEFAULT 'manual'`, `lab_order_id TEXT`, `clinic_id TEXT`, `flagged_values TEXT DEFAULT '[]'`, `is_critical INTEGER DEFAULT 0`, `acknowledged_by TEXT`, `acknowledged_at TEXT`
- [ ] T004 `repository.py` **(B-04 fix)**: Extend `owner_images` table (NOT `patient_images` — that table does not exist) via `ALTER TABLE owner_images ADD COLUMN` for `modality TEXT`, `report_text TEXT`, `dicom_study_uid TEXT`, `imaging_system TEXT`, `study_date TEXT` (each wrapped in `try/except`)
- [ ] T005 `models.py`: Add `IntegrationDefinition`, `IntegrationStatus`, `LabAnalyte` (fields: `name`, `value`, `unit`, `low`, `high`, `flag` — **NOT** `ref_low`/`ref_high`), `MigrationRun`, `MigrationFlag` Pydantic models. `LabResult` maps to existing `labs` table shape.

## Phase 2 — Credentials & Health Agent (INT-001, INT-002)

- [ ] T006 `repository.py`: Add `save_integration_credential(clinic_id, integration_id, key_name, encrypted_value)`, `get_integration_credentials(clinic_id, integration_id)`, `delete_integration_credentials(clinic_id, integration_id)`. **W-07**: `required_keys` in `integration_definitions` is stored as JSON TEXT — use `json.dumps()` on write, `json.loads()` on read.
- [ ] T007 `repository.py`: Add `upsert_integration_status(status: IntegrationStatus)`, `get_integration_status(clinic_id, integration_id)`, `get_all_integration_statuses(clinic_id)`
- [ ] T008 `repository.py`: Add `seed_integration_definitions()` — INSERT OR IGNORE all 11 definitions (with `required_keys` serialised via `json.dumps()`); call from `on_startup` if table empty
- [ ] T009 Create `backend/agents/integration_health.py` — `CredentialsAgent` (uses persisted key from `.vpma_key` — **W-01 fix**, see plan.md) + `HealthMonitor`. Also add `get_clinic_id_by_credential(integration_id, key_name, value)` to `repository.py` **(W-02 fix)** used by Lab Agent to resolve clinic from webhook payload.
- [ ] T010 `main.py`: `GET /api/settings/integrations` — list definitions + statuses for clinic
- [ ] T011 `main.py`: `POST /api/settings/integrations/{integration_id}/credentials` — encrypt + save + test + return status
- [ ] T012 `main.py`: `POST /api/settings/integrations/{integration_id}/test` — re-run connectivity test
- [ ] T013 `main.py`: `DELETE /api/settings/integrations/{integration_id}/credentials` — revoke credentials, set status unconfigured
- [ ] T014 `main.py`: `GET /api/settings/integrations/health` — summary: `any_disconnected`, statuses list

## Phase 3 — Migration Agent (INT-003, INT-004)

- [ ] T015 `repository.py`: Add `create_migration_run()`, `update_migration_run()`, `get_migration_run()`, `save_migration_flag()`
- [ ] T016 Create `backend/agents/migration.py` — `AvimarkMigrationAgent`: parse ZIP, import owners → patients → visits → care_events → prescriptions; idempotent (`INSERT OR IGNORE`); flag bad records. **W-05**: agent opens its OWN `sqlite3.connect(_DB_PATH)` connection (not the shared `db` singleton) for thread safety in background task.
- [ ] T017 `migration.py`: `CornerstoneMigrationAgent` — subclass of Avimark with different field mapping; stub ezyVet placeholder
- [ ] T018 `main.py` **(B-03 fix)**: `POST /api/migration/upload` — accept multipart ZIP, create `MigrationRun`, run agent using `BackgroundTasks.add_task()` (NOT `asyncio.create_task` — incompatible with sync route context). Add `background_tasks: BackgroundTasks` parameter.
- [ ] T019 `main.py`: `GET /api/migration/{run_id}/status` — return current run state + phase + counts
- [ ] T020 `main.py`: `GET /api/migration/{run_id}/report` — return completed run full report
- [ ] T021 `main.py`: `GET /api/migration/{run_id}/flagged.csv` — return CSV of flagged records (`Response` with `media_type="text/csv"`)

## Phase 4 — Lab Agent Core (INT-050)

- [ ] T022 `repository.py` **(B-01 fix)**: Add `save_lab(lab_dict)` (writes to existing `labs` table, not a new table), `get_labs_for_patient()` (extend EXISTING method to return new fields), `acknowledge_lab(lab_id, vet_id)` **(W-04)**, `patch_lab(lab_id, updates)` **(W-04)**, `get_clinic_id_by_credential(integration_id, key_name, value)` **(W-02)**
- [ ] T023 Create `backend/agents/lab_agent.py` — `LabAgent`: resolve clinic (W-02) → normalise **(B-02: write analytes as `{"panels":[{"name":...,"analytes":[{name,value,unit,`low`,`high`,flag}]}]}` matching LabsPanel.tsx)** → match patient (by `lab_order_id`, fallback name) → classify flags (H/L/HH/LL) → compute `is_critical` → save to `labs` table → update risk score → push action queue item if critical → log via `_log1`
- [ ] T024 `main.py` **(W-03 fix)**: `POST /api/webhooks/idexx/result` — MUST be `async def`; read `await request.body()` BEFORE JSON parsing; validate HMAC; call `background_tasks.add_task(lab_agent.process, data, 'idexx')`
- [ ] T025 `main.py` **(B-01 fix)**: Do NOT create new `/api/patients/{id}/lab-results` route. The existing `GET /api/labs/patient/{patient_id}` (main.py:862) already serves this purpose — verify it returns the new fields (`provider`, `is_critical`, `flagged_values`) and extend if needed.
- [ ] T026 `main.py` **(B-01 fix)**: Do NOT create new `/api/timeblocks/{id}/lab-results` route. Existing `GET /api/labs/timeblock/{timeblock_id}` (main.py:872) serves this — verify it returns new fields.
- [ ] T027 `main.py`: `POST /api/labs/{id}/acknowledge` — update status → `acknowledged`, record `acknowledged_by` + `acknowledged_at` (note: route uses `labs` table ID, not `lab_results`)
- [ ] T028 `main.py`: `POST /api/simulate/lab-result` — demo helper: generate realistic mock IDEXX payload → call `lab_agent.process()` → return result (seeded panel templates: `cbc`, `chemistry`, `urinalysis`; `include_critical` flag adds one HH analyte)

## Phase 5 — Additional Lab Providers (INT-051–054)

- [ ] T029 `main.py` **(W-03 fix)**: `POST /api/webhooks/antech/result` — MUST be `async def`; read raw body first; Antech field mapping → normalise to same `results` JSON structure → call `lab_agent.process(data, provider='antech')`
- [ ] T030 `main.py`: `POST /api/webhooks/heska/result` — `async def`; call `lab_agent.process(provider='heska')`
- [ ] T031 `main.py`: `POST /api/webhooks/vetscan/result` — `async def`; call `lab_agent.process(provider='vetscan')`
- [ ] T032 `main.py`: `POST /api/webhooks/imaging/result` — `async def`; `ImagingAgent`: create `owner_images` row **(B-04: table is `owner_images`, not `patient_images`)** with `source=modality_code`, `modality`, `report_text`, `study_date`, `patient_id`; notify vet; log
- [ ] T033 `main.py`: `POST /api/lab-results/import` — accept multipart CSV; detect format (Vetscan/Abaxis by header row); parse; call `lab_agent.process(provider='imported')`
- [ ] T033b `main.py` **(W-04)**: `PATCH /api/labs/{id}` — update `patient_id` and optionally `timeblock_id` for unmatched results; set `status='received'`
- [ ] T033c `main.py` **(W-09)**: `GET /api/patients/{patient_id}/images` — return all `owner_images` rows for a patient (both `source='owner'` and clinical sources)

## Phase 6 — Frontend: Settings / Integrations (INT-001, INT-002)

- [ ] T034 Create `frontend/src/components/IntegrationsSettings.tsx` — grid of integration cards: name, emoji, module badge, status badge (`🟢/🟡/🔴/⚪`), "Configure" button; fetch from `GET /api/settings/integrations`
- [ ] T035 `IntegrationsSettings.tsx`: Configure modal — labelled input fields per `required_keys`; "Save & Test" button; spinner state; inline success/error message; close on success
- [ ] T036 `IntegrationsSettings.tsx`: connectivity test UX — loading spinner on card during test; animated badge transition on result
- [ ] T037 `IntegrationsSettings.tsx`: "Remove Credentials" button in modal (with confirmation) → calls DELETE endpoint
- [ ] T038 Add `/settings` route to `frontend/src/app/` with `IntegrationsSettings` as default view; add "Settings" link to nav header
- [ ] T039 Header component **(W-06 fix)**: add small `⚠️` warning dot when `any_disconnected: true` from health endpoint; clicking navigates to `/settings`. Pass `clinic_id` from the active clinic in `Dashboard.tsx` state via prop or React context — clarify prop-drilling path before implementing.

## Phase 7 — Frontend: Lab Results (INT-050–054)

- [ ] T040 `VetAppointmentCard.tsx` Labs tab: fetch `GET /api/labs/patient/{id}` **(B-01: uses EXISTING endpoint)**; render list of result panels with panel name, provider badge, received timestamp. Detect webhook results by `provider != null && provider != 'manual'`.
- [ ] T041 Labs tab: analyte table — columns: Analyte, Value, Unit, Ref Range, Flag; amber row for `H`/`L`, red row for `HH`/`LL`; flag column shows emoji: `⬆` `⬇` `🔴⬆` `🔴⬇`. **(B-02: read from `lab.results?.panels[].analytes[]` — matches existing LabsPanel shape exactly. Analyte fields are `a.low` / `a.high`.)**
- [ ] T042 Labs tab: critical toast — if any result has `is_critical: 1` and `status != 'acknowledged'`: show red toast `⚠️ CRITICAL — {analyte} {value}` with "Acknowledge" button
- [ ] T043 Labs tab: "Import Result" button → file picker → POST to `/api/lab-results/import` → result appears instantly
- [ ] T044 Labs tab: "Simulate Lab Result" button (visible in demo mode only) → POST to `/api/simulate/lab-result` → result appears with a brief animation
- [ ] T045 Action queue: add `critical_lab` card type — red border, patient name, panel name, critical analyte + value; "Acknowledge" button → POST `/api/labs/{id}/acknowledge` → card disappears
- [ ] T046 Action queue: add `unmatched_lab` card type — shows panel name + provider; "Assign" button → patient search modal → on assign: `PATCH /api/labs/{id}` with patient_id **(W-04)**

## Phase 8 — Frontend: Imaging Tab (INT-053)

- [ ] T047 `VetAppointmentCard.tsx` Imaging tab **(W-09 fix)**: add `useEffect` to fetch `GET /api/patients/{patient_id}/images`; store clinical images in state alongside existing owner photos. Add modality filter bar — `All | 📷 Photos | 🦴 X-Ray | 🔊 Ultrasound | 🧠 CT/MRI`; filters `source` field client-side
- [ ] T048 Imaging tab **(B-04 fix)**: source badge on each image reads `source` field from `owner_images` row: `source='owner'` → grey `Owner Upload` badge; `source='xray'`/`'ultrasound'`/`'ct'`/`'mri'` → blue clinical badge
- [ ] T049 Imaging tab: if `report_text` present — show collapsible "📋 Radiologist Report" section below image thumbnail; collapsed by default

## Phase 9 — Frontend: Migration UI (INT-003)

- [ ] T050 Create `frontend/src/components/DataMigration.tsx` — dropzone for ZIP upload; source system selector (`Avimark` | `Cornerstone`); "Start Migration" button → POST upload → store `run_id`
- [ ] T051 `DataMigration.tsx`: phase progress bar — poll `GET /api/migration/{run_id}/status` every 2s during `running`; show phase label + running count per entity
- [ ] T052 `DataMigration.tsx`: completed state — show report card (counts per entity, flagged count); "Download Flagged Records" button → fetch CSV
- [ ] T053 Add Data Migration section to `/settings` route alongside Integrations

## Phase 10 — Seed Data & Demo Fixtures

- [ ] T054 `seed_data.py`: Add `seed_integration_definitions()` — INSERT OR IGNORE all 11 integration definitions (with `required_keys` as `json.dumps(list)` — **W-07**); call from startup
- [ ] T055 `seed_data.py`: Add `lab_order_id` values to 3 seeded historical timeblocks (so simulated IDEXX result can match immediately in demo)
- [ ] T056 `seed_data.py`: Add `seed_lab_data()` — seed 1 pre-existing lab row for Buddy: CBC panel with elevated WBC (`H`) and critical BUN (`HH`) stored in `results` JSON as `{"panels":[{"name":"CBC","analytes":[{"name":"WBC","value":14.2,"unit":"K/uL","low":6.0,"high":17.0,"flag":"H"},{"name":"BUN","value":85.0,"unit":"mg/dL","low":7.0,"high":27.0,"flag":"HH"}]}]}`, `is_critical=1`, `status='received'`; visible immediately in demo **(B-02: uses `low`/`high` not `ref_low`/`ref_high`)**
- [ ] T057 **(W-08 fix)**: Create `backend/scripts/generate_avimark_fixture.py` — script that programmatically generates `specs/006-integration-batch0/fixtures/avimark-sample.zip` containing `clients.csv` (3 owners), `patients.csv` (5 patients), `visits.csv` (10 visits), `vaccinations.csv` (5), `prescriptions.csv` (3). Run once: `python -m backend.scripts.generate_avimark_fixture`

## Phase 11 — Commit

- [ ] T058 `git add -A && git commit -m "feat(int-batch0): Core & cross-cutting integrations (INT-001/002/003/004/050-054)"`
- [ ] T059 `git push origin main`
