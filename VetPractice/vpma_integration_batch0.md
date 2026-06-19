# VPMA Integration Batch 0 — Core & Cross-Cutting
## Speckit Feature Batch

**Batch ID**: INT-BATCH-0  
**Batch name**: Core Platform + All-Module Integrations  
**Date**: 2026-06-19  
**Feed into**: `speckit.specify`  
**Scope**: Integrations classified as `Core` or `All Clinical` in the Integration Map — not tied to any single add-on module; must exist before module-specific integrations can run.

---

## Why These 9 First

Every other integration in the registry depends on at least one of these:
- **INT-001** — Without a credentials vault, no integration can store API keys
- **INT-002** — Without health monitoring, failures are silent
- **INT-003 / INT-004** — Without migration, no existing practice can switch to VPMA
- **INT-050 / INT-051** — Lab results feed patient records, SOAP notes, risk scores, and care timelines across every clinical module
- **INT-052 / INT-053 / INT-054** — In-house diagnostics and imaging complete the clinical data picture

---

## INT-001 — Credentials & Secrets Manager

### Problem It Solves
Every integration requires API keys, OAuth tokens, or secrets. Without a secure, per-clinic vault, credentials would be hardcoded, shared across clinics, or stored in plaintext — a security and operational failure.

### User Story
> As a practice administrator, I want to enter my API credentials once in a secure settings panel, so that all VPMA integrations activate automatically without my staff ever seeing a raw API key.

### Agentic Pipeline
```
Admin enters credential → Credentials Agent
  → encrypts value at rest (AES-256)
  → stores per-clinic, per-integration
  → immediately calls INT-002 Health Monitor to test connectivity
  → sets integration status: 🟢 Connected | 🔴 Failed
  → Verbose Log: CREDENTIALS AGENT: Twilio configured · connectivity test passed
```

### UI Spec
- **Settings → Integrations panel** (new top-level settings section)
- Integration cards: one per integration, showing name, logo, status badge, "Configure" button
- Configure modal: labelled fields per credential (e.g. "Account SID", "Auth Token")
- On save: spinner → connectivity test → result shown inline
- Status badges: `🟢 Connected` | `🟡 Degraded` | `🔴 Disconnected` | `⚪ Not Configured`

### Backend Requirements
- `POST /api/settings/integrations/{integration_id}/credentials` — save encrypted credential
- `GET /api/settings/integrations` — list all integrations with status per clinic
- `POST /api/settings/integrations/{integration_id}/test` — trigger connectivity test
- `DELETE /api/settings/integrations/{integration_id}/credentials` — revoke

### New Entities
```
IntegrationCredential {
  id, clinic_id, integration_id, key_name,
  encrypted_value,  // AES-256 encrypted
  last_verified_at, created_at
}

IntegrationDefinition {
  id,              // e.g. "twilio", "stripe", "idexx"
  name,            // display name
  module,          // "MOD-COM" | "MOD-FIN" | "core" | etc.
  tier,            // "native" | "webhook" | "export"
  required_keys[], // e.g. ["ACCOUNT_SID", "AUTH_TOKEN", "FROM_NUMBER"]
  test_endpoint    // internal endpoint to call for health check
}
```

### Demo Talking Point
> *"Every integration is zero-touch once configured. The practice owner enters credentials once — the agent tests them, confirms connectivity, and from that moment every outbound action just works."*

---

## INT-002 — Integration Health Monitor

### Problem It Solves
Integration failures are silent by default. A Twilio outage means owners stop getting reminders — nobody notices until a no-show. A QuickBooks token expiry means payments aren't syncing — the accountant finds out at month-end.

### User Story
> As a practice manager, I want to see the live status of every connected integration on a single panel, and get an immediate alert in my action queue if any integration goes down.

### Agentic Pipeline
```
Every 15 minutes → Health Monitor Agent
  → for each configured integration:
    → calls integration test_endpoint
    → records: status, latency, error_message
    → if status changed from 🟢 → 🔴:
      → push alert to manager action queue
      → Verbose Log: HEALTH AGENT: QuickBooks connection lost — token may have expired
    → if status changed 🔴 → 🟢:
      → auto-clear alert, log recovery
      → Verbose Log: HEALTH AGENT: QuickBooks reconnected ✓

On demand → "Test Connection" button in Settings triggers single integration test
```

### UI Spec
- **Settings → Integrations** — status badge updates in real time via polling
- **Manager action queue** — new card type: `🔴 Integration Down — QuickBooks` with "Reconnect" CTA
- **Dashboard header** — small warning dot if any integration is degraded/down

### Backend Requirements
- `GET /api/settings/integrations/health` — current status of all integrations
- `POST /api/settings/integrations/{id}/test` — on-demand test
- Background task: runs health sweep every 15 minutes
- `IntegrationStatus` updated on each sweep

### New Entities
```
IntegrationStatus {
  id, clinic_id, integration_id,
  status,           // "connected" | "degraded" | "disconnected" | "unconfigured"
  latency_ms,
  error_message,
  last_checked_at,
  last_connected_at
}
```

---

## INT-003 — Avimark Data Migration

### Problem It Solves
The majority of independent vet practices in North America run Avimark (Covetrus). VPMA cannot acquire these customers without a migration path — asking them to re-enter 847 patients manually is a dealbreaker.

### User Story
> As a practice owner migrating from Avimark, I want to upload my Avimark data export and have VPMA automatically import all my patients, owners, visit history, and prescription records — so I can be fully operational on day one.

### Agentic Pipeline
```
Admin uploads Avimark export ZIP → Migration Agent
  → validates ZIP structure (expected CSV files present)
  → phase 1: import Owners → create Owner records
  → phase 2: import Patients → link to owners
  → phase 3: import Visit History → create historical TimeBlocks + SOAP stubs
  → phase 4: import Vaccines → create CareEvents
  → phase 5: import Rx History → create Prescriptions (historical)
  → phase 6: quality check — flag records with missing required fields
  → generates: MigrationReport (counts + flagged items)
  → Verbose Log: MIGRATION AGENT: 847 patients · 621 owners · 4,203 visits · 12 records flagged
```

### Field Mapping (Avimark → VPMA)

| Avimark field | VPMA entity | VPMA field |
|---|---|---|
| Client ID | Owner | id (mapped) |
| Client First/Last Name | Owner | name |
| Client Phone | Owner | phone |
| Client Email | Owner | email |
| Patient Name | Patient | name |
| Patient Species | Patient | species |
| Patient Breed | Patient | breed |
| Patient DOB | Patient | dob |
| Patient Weight | Patient | weight_kg |
| Visit Date | TimeBlock | start_time (historical) |
| Visit Reason | TimeBlock | job.procedure |
| Diagnosis | SoapNote | assessment (stub) |
| Vaccine Type | CareEvent | protocol_name |
| Vaccine Date | CareEvent | administered_date |
| Drug Name | Prescription | drug_name |
| Drug Dose | Prescription | dose |

### UI Spec
- **Settings → Data Migration** — upload dropzone for Avimark ZIP
- Progress bar showing each phase (Owners → Patients → Visits → Vaccines → Rx)
- Migration report: counts per entity, flagged records list, "Download flagged records CSV"
- Option to re-run migration (idempotent — uses `INSERT OR IGNORE`)

### Backend Requirements
- `POST /api/migration/upload` — accepts multipart ZIP upload, returns `migration_run_id`
- `GET /api/migration/{run_id}/status` — polling endpoint for progress + phase
- `GET /api/migration/{run_id}/report` — final report with counts and flagged items
- `GET /api/migration/{run_id}/flagged.csv` — download flagged records

### New Entities
```
MigrationRun {
  id, clinic_id, source_system,  // "avimark" | "cornerstone" | "ezyvet"
  status,           // "pending" | "running" | "complete" | "failed"
  phase,            // current phase name
  imported_owners, imported_patients, imported_visits,
  imported_care_events, imported_prescriptions,
  flagged_count, completed_at
}

MigrationFlag {
  id, migration_run_id, record_type, source_row, reason
}
```

---

## INT-004 — Cornerstone / ezyVet Migration

### Problem It Solves
IDEXX Cornerstone is the other dominant legacy PMS, used by many AAHA-accredited practices. ezyVet is the fastest-growing cloud PMS in the market. Both represent large addressable pools of switchable practices.

### User Story
> As a practice migrating from Cornerstone or ezyVet, I want the same seamless migration experience as Avimark — one upload, fully imported, ready to go.

### Agentic Pipeline
```
Cornerstone: same as INT-003 (CSV export upload)
ezyVet:      Migration Agent calls ezyVet REST API directly (no file upload needed)
  → authenticates with ezyVet credentials
  → paginates through: contacts, animals, consultations, vaccinations, prescriptions
  → maps to VPMA entities
  → same quality check + MigrationReport output
```

### Field Mapping Notes
- Cornerstone uses similar CSV structure to Avimark (same Covetrus lineage) — field mapping largely shared
- ezyVet uses "Animal" (= Patient), "Contact" (= Owner), "Consultation" (= TimeBlock/SOAP)
- ezyVet live API migration can be done without practice downtime

### New Config
```
ezyVet live migration:
  EZYVET_SUBDOMAIN, EZYVET_CLIENT_ID, EZYVET_CLIENT_SECRET
  (stored in INT-001 credentials vault)
```

### Additional Entities
```
MigrationRun.source_system: adds "cornerstone" | "ezyvet"
```

---

## INT-050 — IDEXX Laboratories (Reference Lab + In-House)

### Problem It Solves
Lab results currently live in a separate IDEXX portal. Vets must switch tabs, find the result, read it, then manually update the patient record. Critical abnormal values can be missed in the tab-switching. Zero automation.

### User Story
> As a veterinarian, when a lab result comes back from IDEXX, I want it to automatically appear in the patient's record, flag any abnormal values, and notify me immediately if any value is critical — without me checking the IDEXX portal.

### Agentic Pipeline
```
IDEXX POST to /api/webhooks/idexx/result
  → Lab Agent:
    → authenticates webhook signature
    → matches: lab_order_id → patient_id → timeblock_id
    → parses: panel_name, analytes[], each with value + ref_range + flag
    → saves LabResult record
    → if any flag = 'H' or 'L': appends to patient.flags
    → if any flag = 'HH' or 'LL' (critical): pushes immediate alert to vet action queue
    → attaches result to SOAP note (Assessment section) and Care Timeline
    → recalculates patient risk score
    → drafts follow-up message to owner if result warrants it (queued, not auto-sent)
    → Verbose Log: LAB AGENT: CBC for Buddy — WBC 14.2 (H, ref 6-17) · BUN elevated · Risk updated to HIGH
```

### In-House Instruments (same webhook)
- **Catalyst One** — chemistry panel
- **ProCyte Dx** — hematology (CBC)
- **SediVue Dx** — urinalysis
- All instruments configured in IDEXX VetConnect Plus to push results to VPMA webhook

### UI Spec
**VetAppointmentCard — Labs tab** (already exists):
- Lab results appear with panel name, date/time, analyte table
- Abnormal values highlighted in amber (H/L) or red (HH/LL)
- Critical badge: `⚠️ CRITICAL — BUN 85 (ref 7-27)` with timestamp
- "View in IDEXX" link for full report

**Patient panel** — result history timeline
**Vet action queue** — critical result cards with patient name + flagged analytes

### Backend Requirements
- `POST /api/webhooks/idexx/result` — inbound result webhook (no auth header; HMAC signature validation)
- `GET /api/patients/{patient_id}/lab-results` — all lab results for patient
- `GET /api/timeblocks/{timeblock_id}/lab-results` — results for specific appointment
- `POST /api/lab-results/{id}/acknowledge` — vet acknowledges critical alert

### New Config
```
IDEXX_PRACTICE_ID     (from IDEXX VetConnect Plus)
IDEXX_WEBHOOK_SECRET  (for HMAC signature validation)
```

### New Entities
```
LabResult {
  id, patient_id, timeblock_id,
  provider,          // "idexx" | "antech" | "heska"
  lab_order_id,      // provider's order reference
  panel_name,        // e.g. "Complete Blood Count", "Chemistry Panel"
  analytes[],        // [{name, value, unit, ref_low, ref_high, flag}]
  flagged_values[],  // subset with H/L/HH/LL flags
  is_critical,       // true if any HH/LL
  received_at,
  acknowledged_by,   // vet_id
  acknowledged_at
}
```

### API Contract
```
POST /api/webhooks/idexx/result
Header: X-IDEXX-Signature: <hmac-sha256>
Body: {
  "order_id": "ORD-12345",
  "practice_id": "PRAC-001",
  "patient_name": "Buddy",
  "client_name": "John Smith",
  "panels": [{
    "name": "CBC",
    "analytes": [{
      "name": "WBC", "value": 14.2, "unit": "K/uL",
      "ref_low": 6.0, "ref_high": 17.0, "flag": "H"
    }]
  }]
}

GET /api/patients/{patient_id}/lab-results
Response: { "patient_id": "...", "results": [LabResult, ...] }
```

### Demo Talking Point
> *"The moment IDEXX releases that CBC, the agent reads it, flags the elevated WBC, and puts a card in Dr. Smith's action queue before she even finishes the next appointment. No portal. No tab switching. No missed critical values."*

---

## INT-051 — Antech Diagnostics

### Problem It Solves
Same as INT-050. Practices are on either IDEXX or Antech — rarely both. Antech (Mars Petcare) is the second-largest reference lab and must be supported for market coverage.

### User Story
> As a vet practice using Antech instead of IDEXX, I want exactly the same automatic result delivery and critical alert experience.

### Agentic Pipeline
```
Antech POST to /api/webhooks/antech/result
  → Lab Agent (same as INT-050, different field mapping):
    → Antech uses: "ACNO" (accession number), "TESTS[]", "RESULT_VALUE", "RANGE", "ABNORMAL_FLAG"
    → normalised to VPMA LabResult model
    → same downstream: patient update, SOAP attach, risk score, vet alert
```

### Field Mapping (Antech → VPMA LabResult)

| Antech field | VPMA field |
|---|---|
| ACNO | lab_order_id |
| CLIENT_ID | (matched to owner) |
| PATIENT_NAME | (matched to patient) |
| TEST_NAME | analytes[].name |
| RESULT_VALUE | analytes[].value |
| UNITS | analytes[].unit |
| REFERENCE_RANGE | analytes[].ref_low/ref_high |
| ABNORMAL_FLAG | analytes[].flag |

### New Config
```
ANTECH_PRACTICE_CODE
ANTECH_WEBHOOK_SECRET
```

### Backend Requirements
- `POST /api/webhooks/antech/result` — inbound webhook
- All other endpoints shared with INT-050 (`/api/patients/{id}/lab-results` etc.)

---

## INT-052 — Heska In-House Diagnostics

### Problem It Solves
Many practices run Heska in-house analyzers (Element DC, HT5) for rapid point-of-care results before a patient leaves. These results never make it into the patient record — they're read off the instrument and verbally communicated.

### User Story
> As a vet tech, after running a Heska panel, I want the result to automatically appear in the patient's record in VPMA — no manual transcription.

### Agentic Pipeline
```
Heska instrument completes analysis
  → Heska VetLink software pushes result to VPMA webhook
    POST /api/webhooks/heska/result
  → Lab Agent processes same as INT-050/051
  → result appears in Labs tab within seconds
```

### New Config
```
HESKA_WEBHOOK_SECRET
(Configured in Heska VetLink: set VPMA webhook URL as result destination)
```

### Notes
- Heska VetLink software acts as the bridge between instrument and webhook
- No VPMA agent needs to poll — Heska pushes on result completion
- Same `LabResult` entity, `provider='heska'`

---

## INT-053 — Sound / Diagnostic Imaging & DICOM

### Problem It Solves
Radiology reports and DICOM images (X-rays, ultrasounds) live in a separate PACS (Picture Archiving and Communication System). Vets view images in one system, type notes in another, and the two never talk. Images don't live in the patient record.

### User Story
> As a veterinarian, when a radiology report comes in or I take an in-house X-ray, I want the image and the radiologist's report to automatically appear in the patient's Imaging tab in VPMA.

### Agentic Pipeline
```
Imaging study complete → PACS/Imaging system sends result
  → Option A (REST): POST /api/webhooks/imaging/result with report + image URL
  → Option B (DICOM): VPMA acts as DICOM C-STORE destination; receives DICOM files
  → Imaging Agent:
    → stores image reference (URL or DICOM UID)
    → attaches report text to patient record
    → creates PatientImage record with modality + study metadata
    → notifies vet: new imaging result available
    → Verbose Log: IMAGING AGENT: Thoracic X-ray received for Luna · 2 views · report attached
```

### UI Spec
**VetAppointmentCard — Imaging tab** (already built, currently shows owner photos):
- Extend existing tab to show:
  - Owner-submitted photos (existing)
  - Clinical imaging: X-Ray, Ultrasound, CT, MRI — with modality badge
  - Report text (collapsible)
  - Thumbnail grid → click to open full resolution
- Modality filter: `All | Photos | X-Ray | Ultrasound | CT/MRI`

### Backend Requirements
- `POST /api/webhooks/imaging/result` — inbound REST result
- Extend `PatientImage` entity with imaging fields
- `GET /api/timeblocks/{id}/images` — already exists; extend to return imaging modality

### New Entities
Extend existing `PatientImage`:
```
PatientImage {
  // existing fields...
  source,           // "owner_upload" | "xray" | "ultrasound" | "ct" | "mri"
  dicom_study_uid,
  modality,         // "CR" | "US" | "CT" | "MR"
  report_text,
  imaging_system,   // "sound" | "idexx_pacs" | "other"
  study_date
}
```

### New Config
```
IMAGING_WEBHOOK_SECRET
DICOM_AE_TITLE        (if using DICOM C-STORE)
DICOM_SERVER_PORT     (default 11112)
```

---

## INT-054 — Zoetis Vetscan / Abaxis Point-of-Care

### Problem It Solves
Zoetis Vetscan and Abaxis analyzers are used for rapid in-house chemistry results. Results print on paper or display on screen — never enter the patient record.

### User Story
> As a vet tech using a Vetscan analyzer, I want the chemistry result to appear in VPMA automatically — or at minimum, be importable with one click.

### Agentic Pipeline
```
Option A — Webhook (Vetscan newer models):
  Vetscan pushes to /api/webhooks/vetscan/result
  → Lab Agent processes same as INT-052

Option B — CSV Import (Abaxis / older Vetscan):
  Tech exports result CSV from instrument
  → uploads via Labs tab "Import Result" button
  → Lab Agent parses CSV → creates LabResult → same downstream pipeline
```

### UI Spec
**VetAppointmentCard — Labs tab**:
- "Import Result" button → file picker → accepts Vetscan/Abaxis CSV
- Parsed result displayed immediately in analyte table format

### Backend Requirements
- `POST /api/webhooks/vetscan/result` — inbound webhook (newer instruments)
- `POST /api/lab-results/import` — CSV import endpoint (multipart)
- CSV parser: handles Vetscan 2 / Abaxis Piccolo export format

### New Config
```
VETSCAN_WEBHOOK_SECRET  (optional; only for webhook-capable models)
```

---

## Batch Summary

| INT | Name | Phase | Depends on | Key new entity |
|---|---|---|---|---|
| INT-001 | Credentials Manager | P0 | — | `IntegrationCredential` |
| INT-002 | Health Monitor | P0 | INT-001 | `IntegrationStatus` |
| INT-003 | Avimark Migration | P3 | INT-001 | `MigrationRun` |
| INT-004 | Cornerstone / ezyVet Migration | P3 | INT-001 | `MigrationRun` (shared) |
| INT-050 | IDEXX Laboratories | P0 | INT-001 | `LabResult` |
| INT-051 | Antech Diagnostics | P1 | INT-001, INT-050 schema | `LabResult` (shared) |
| INT-052 | Heska | P2 | INT-001, INT-050 schema | `LabResult` (shared) |
| INT-053 | Sound / DICOM Imaging | P2 | INT-001 | Extends `PatientImage` |
| INT-054 | Zoetis Vetscan / Abaxis | P2 | INT-001, INT-050 schema | `LabResult` (shared) |

### Build Order Within Batch
```
INT-001 → INT-002    (credentials must exist before health monitoring)
INT-001 → INT-050    (credentials + IDEXX webhook — most critical clinical integration)
INT-050 → INT-051    (Antech uses same LabResult schema; build after IDEXX proven)
INT-050 → INT-052    (Heska same)
INT-050 → INT-054    (Vetscan same)
INT-001 → INT-053    (imaging independent of lab; can build in parallel with INT-051+)
INT-001 → INT-003    (migration independent; build when onboarding pipeline ready)
INT-003 → INT-004    (Cornerstone/ezyVet migration shares Migration Agent)
```
