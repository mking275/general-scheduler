# Integration Batch 0 — Implementation Plan

**Feature**: integration-batch0
**Date**: 2026-06-19
**Status**: Ready for tasks

---

## Build Order

```
Phase 1 — Schema & Models
  T001  DB schema: integration_definitions, integration_credentials,
                   integration_statuses (INT-001, INT-002)
  T002  DB schema: migration_runs, migration_flags (INT-003/004)
  T003  DB schema: lab_results (INT-050–054)
  T004  DB schema: patient_images extensions (INT-053)
  T005  Pydantic models: IntegrationDefinition, IntegrationStatus,
                         LabResult, LabAnalyte, MigrationRun

Phase 2 — Backend: Credentials & Health (INT-001, INT-002)
  T006  repository.py: get/save/delete integration_credentials (encrypted)
  T007  repository.py: get/upsert integration_statuses
  T008  repository.py: seed integration_definitions at startup
  T009  agents/integration_health.py: CredentialsAgent + HealthMonitor
  T010  main.py: GET /api/settings/integrations
  T011  main.py: POST /api/settings/integrations/{id}/credentials
  T012  main.py: POST /api/settings/integrations/{id}/test
  T013  main.py: DELETE /api/settings/integrations/{id}/credentials
  T014  main.py: GET /api/settings/integrations/health

Phase 3 — Backend: Data Migration (INT-003, INT-004)
  T015  repository.py: save/get migration_runs + migration_flags
  T016  agents/migration.py: AvimarkMigrationAgent (CSV parser + importer)
  T017  agents/migration.py: CornerstoneMigrationAgent (shared base, diff mapping)
  T018  main.py: POST /api/migration/upload (file upload handler)
  T019  main.py: GET /api/migration/{run_id}/status
  T020  main.py: GET /api/migration/{run_id}/report
  T021  main.py: GET /api/migration/{run_id}/flagged.csv

Phase 4 — Backend: Lab Agent Core (INT-050)
  T022  repository.py: save/get/query lab_results
  T023  agents/lab_agent.py: LabAgent — normalise, match, flag, risk, alert
  T024  main.py: POST /api/webhooks/idexx/result (HMAC validation + async agent call)
  T025  main.py: GET /api/patients/{id}/lab-results
  T026  main.py: GET /api/timeblocks/{id}/lab-results
  T027  main.py: POST /api/lab-results/{id}/acknowledge
  T028  main.py: POST /api/simulate/lab-result (demo helper)

Phase 5 — Backend: Additional Lab Providers (INT-051–054)
  T029  main.py: POST /api/webhooks/antech/result (Antech field mapping)
  T030  main.py: POST /api/webhooks/heska/result
  T031  main.py: POST /api/webhooks/vetscan/result
  T032  main.py: POST /api/webhooks/imaging/result (imaging agent)
  T033  main.py: POST /api/lab-results/import (CSV upload, Vetscan/Abaxis parser)

Phase 6 — Frontend: Settings / Integrations Panel (INT-001, INT-002)
  T034  components/IntegrationsSettings.tsx — integration cards grid
  T035  components/IntegrationsSettings.tsx — Configure modal (credential form)
  T036  components/IntegrationsSettings.tsx — connectivity test UX (spinner → badge)
  T037  components/IntegrationsSettings.tsx — health status badges per card
  T038  Add Settings route to app routing; link from header/nav
  T039  Header warning indicator when any integration is disconnected

Phase 7 — Frontend: Lab Results UI (INT-050–054)
  T040  VetAppointmentCard Labs tab — result list with analyte table
  T041  VetAppointmentCard Labs tab — abnormal value highlighting (amber H/L, red HH/LL)
  T042  VetAppointmentCard Labs tab — critical result toast notification
  T043  VetAppointmentCard Labs tab — "Import Result" CSV upload button
  T044  VetAppointmentCard Labs tab — "Simulate Lab Result" demo button
  T045  Action queue — critical result card type + acknowledge flow
  T046  Action queue — unmatched result card + manual assignment modal

Phase 8 — Frontend: Imaging Tab Extension (INT-053)
  T047  VetAppointmentCard Imaging tab — modality filter (All|Photos|X-Ray|US|CT/MRI)
  T048  VetAppointmentCard Imaging tab — source badge (Owner Upload vs Clinical)
  T049  VetAppointmentCard Imaging tab — report text collapsible section

Phase 9 — Frontend: Migration UI (INT-003)
  T050  components/DataMigration.tsx — file upload dropzone
  T051  components/DataMigration.tsx — phase progress bar
  T052  components/DataMigration.tsx — migration report + flagged CSV download
  T053  Add Data Migration to Settings route

Phase 10 — Seed Data & Demo Fixtures
  T054  seed_data.py: seed integration_definitions (all 11 integrations)
  T055  seed_data.py: seed demo lab_order_ids on 3 existing historical timeblocks
  T056  seed_data.py: seed 1 pre-existing LabResult (critical BUN) for Buddy for demo
  T057  Create test fixtures: sample Avimark CSV ZIP for migration demo

Phase 11 — Git & Cleanup
  T058  git add -A && git commit -m "feat(int-batch0): Core & cross-cutting integrations"
  T059  git push origin main
```

---

## Key Technical Decisions

### Encryption
Use Python `cryptography` library (`Fernet` symmetric encryption). Key stored as env var `VPMA_ENCRYPTION_KEY`. If not set, fall back to base64 obfuscation with a logged warning (demo mode).

```python
from cryptography.fernet import Fernet
FERNET_KEY = os.environ.get("VPMA_ENCRYPTION_KEY") or Fernet.generate_key()
cipher = Fernet(FERNET_KEY)

def encrypt(value: str) -> str:
    return cipher.encrypt(value.encode()).decode()

def decrypt(encrypted: str) -> str:
    return cipher.decrypt(encrypted.encode()).decode()
```

### Lab Agent Architecture
```python
class LabAgent:
    def __init__(self, db, log_fn):
        self.db = db
        self.log_fn = log_fn

    def process(self, payload: dict, provider: str) -> LabResult:
        # 1. Normalise provider-specific format → LabResult
        result = self._normalise(payload, provider)
        # 2. Match to patient
        result = self._match_patient(result)
        # 3. Classify flags
        result = self._classify_flags(result)
        # 4. Save
        self.db.save_lab_result(result)
        # 5. Update risk score
        self._update_risk_score(result)
        # 6. Raise alerts if critical
        if result.is_critical:
            self._raise_critical_alert(result)
        # 7. Log
        self.log_fn(f"LAB AGENT: {result.panel_name} for {patient_name} · {flag_summary}")
        return result
```

### Webhook HMAC Validation
```python
def validate_idexx_signature(request_body: bytes, signature_header: str, secret: str) -> bool:
    expected = hmac.new(secret.encode(), request_body, hashlib.sha256).hexdigest()
    received = signature_header.replace("sha256=", "")
    return hmac.compare_digest(expected, received)
```
In demo mode (no secret configured): skip validation and log warning.

### Migration Agent Pattern
```python
class AvimarkMigrationAgent:
    PHASES = ["owners", "patients", "visits", "care_events", "prescriptions"]

    def run(self, zip_path: str, run_id: str, clinic_id: str):
        for phase in self.PHASES:
            self.db.update_migration_phase(run_id, phase)
            self._import_phase(phase, zip_path, run_id, clinic_id)
        self.db.complete_migration(run_id)
```

---

## Dependencies

| Dependency | Reason | New? |
|---|---|---|
| `cryptography` | Fernet symmetric encryption for credentials vault | Yes (single new pip package) |
| `hmac`, `hashlib` | HMAC-SHA256 webhook signature validation | No (stdlib) |
| `zipfile`, `csv` | Migration file parsing | No (stdlib) |
| All existing | backend/frontend unchanged | No |
