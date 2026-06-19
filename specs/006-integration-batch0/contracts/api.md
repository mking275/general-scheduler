# Integration Batch 0 — API Contracts

**Feature**: integration-batch0
**Date**: 2026-06-19

---

## Settings / Credentials (INT-001)

### GET /api/settings/integrations
Returns all integration definitions with current status for the active clinic.

**Response**:
```json
{
  "clinic_id": "clinic-downtown",
  "integrations": [
    {
      "id": "idexx",
      "name": "IDEXX Laboratories",
      "module": "core",
      "tier": "native",
      "logo_emoji": "🧪",
      "required_keys": ["IDEXX_PRACTICE_ID", "IDEXX_WEBHOOK_SECRET"],
      "status": "connected",
      "last_checked_at": "2026-06-19T05:00:00"
    },
    {
      "id": "twilio",
      "name": "Twilio SMS",
      "module": "MOD-COM",
      "tier": "native",
      "required_keys": ["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_FROM_NUMBER"],
      "status": "unconfigured",
      "last_checked_at": null
    }
  ]
}
```

---

### POST /api/settings/integrations/{integration_id}/credentials
Save credentials for an integration and immediately run a connectivity test.

**Request**:
```json
{
  "clinic_id": "clinic-downtown",
  "credentials": {
    "IDEXX_PRACTICE_ID": "PRAC-001",
    "IDEXX_WEBHOOK_SECRET": "whsec_abc123"
  }
}
```

**Response (success)**:
```json
{
  "integration_id": "idexx",
  "status": "connected",
  "latency_ms": 142,
  "message": "IDEXX connected successfully"
}
```

**Response (failure)**:
```json
{
  "integration_id": "idexx",
  "status": "disconnected",
  "error": "IDEXX returned 401 Unauthorized — check Practice ID"
}
```
HTTP 200 in both cases — status field indicates result. Credentials only persisted on success.

---

### POST /api/settings/integrations/{integration_id}/test
Re-run connectivity test for an already-configured integration.

**Response**: Same shape as POST credentials response.

---

### DELETE /api/settings/integrations/{integration_id}/credentials
Remove credentials for an integration. Sets status to `unconfigured`.

**Response**:
```json
{ "integration_id": "idexx", "status": "unconfigured" }
```

---

### GET /api/settings/integrations/health
Returns summary health status for all configured integrations.

**Response**:
```json
{
  "clinic_id": "clinic-downtown",
  "any_disconnected": true,
  "statuses": [
    { "integration_id": "idexx", "status": "connected", "last_checked_at": "..." },
    { "integration_id": "twilio", "status": "disconnected", "error_message": "401 Unauthorized" }
  ]
}
```

---

## Data Migration (INT-003, INT-004)

### POST /api/migration/upload
Upload a migration file. Returns `migration_run_id` immediately; processing is async.

**Request**: `multipart/form-data`
- `file`: ZIP file (Avimark/Cornerstone) or leave empty for ezyVet live pull
- `source_system`: `"avimark"` | `"cornerstone"` | `"ezyvet"`
- `clinic_id`: string

**Response**:
```json
{
  "migration_run_id": "mig-abc123",
  "source_system": "avimark",
  "status": "pending",
  "message": "Migration queued — processing will begin shortly"
}
```

---

### GET /api/migration/{run_id}/status
Poll for migration progress.

**Response**:
```json
{
  "migration_run_id": "mig-abc123",
  "status": "running",
  "phase": "patients",
  "imported_owners": 621,
  "imported_patients": 412,
  "imported_visits": 0,
  "imported_care_events": 0,
  "imported_prescriptions": 0,
  "flagged_count": 3,
  "started_at": "2026-06-19T05:30:00"
}
```

---

### GET /api/migration/{run_id}/report
Final report once status is `complete`.

**Response**:
```json
{
  "migration_run_id": "mig-abc123",
  "status": "complete",
  "imported_owners": 621,
  "imported_patients": 847,
  "imported_visits": 4203,
  "imported_care_events": 1840,
  "imported_prescriptions": 392,
  "flagged_count": 12,
  "completed_at": "2026-06-19T05:32:14"
}
```

---

### GET /api/migration/{run_id}/flagged.csv
Download flagged records as CSV. Returns `Content-Type: text/csv`.

**CSV columns**: `record_type, source_row_json, reason`

---

## Lab Results (INT-050–054)

### POST /api/webhooks/idexx/result
Inbound webhook from IDEXX Laboratories.

**Headers**: `X-IDEXX-Signature: sha256=<hmac>`

**Request body** (IDEXX format — normalised internally):
```json
{
  "order_id": "ORD-IDEXX-001",
  "practice_id": "PRAC-001",
  "patient_name": "Buddy",
  "client_name": "Sarah Johnson",
  "panels": [
    {
      "name": "Complete Blood Count",
      "analytes": [
        { "name": "WBC", "value": 14.2, "unit": "K/uL", "ref_low": 6.0, "ref_high": 17.0, "flag": "H" },
        { "name": "RBC", "value": 7.1,  "unit": "M/uL", "ref_low": 5.5, "ref_high": 8.5, "flag": "" },
        { "name": "BUN", "value": 85.0, "unit": "mg/dL","ref_low": 7.0, "ref_high": 27.0,"flag": "HH" }
      ]
    }
  ]
}
```

**Response**: `HTTP 200 { "received": true }` — always fast; processing is async.

---

### POST /api/webhooks/antech/result
Inbound webhook from Antech Diagnostics.

**Headers**: `X-Antech-Signature: <hmac>`

**Request body** (Antech format — different field names, same downstream):
```json
{
  "ACNO": "ANC-20260619-001",
  "CLIENT_ID": "C-621",
  "PATIENT_NAME": "Rex",
  "TESTS": [
    {
      "TEST_NAME": "GLUCOSE",
      "RESULT_VALUE": "245",
      "UNITS": "mg/dL",
      "REFERENCE_RANGE": "70-143",
      "ABNORMAL_FLAG": "H"
    }
  ]
}
```

**Response**: `HTTP 200 { "received": true }`

---

### POST /api/webhooks/heska/result
Same pattern as IDEXX; Heska VetLink posts in similar JSON format.

---

### POST /api/webhooks/vetscan/result
Same pattern for Vetscan webhook-capable instruments.

---

### POST /api/webhooks/imaging/result
Inbound imaging result (REST path; DICOM is a production extension).

**Request**:
```json
{
  "patient_name": "Luna",
  "patient_id": "pat-luna-001",
  "timeblock_id": "tb-001",
  "modality": "CR",
  "study_date": "2026-06-19",
  "image_url": "https://pacs.example.com/images/study-001.jpg",
  "report_text": "Thoracic radiograph — mild cardiomegaly noted. Recommend echocardiogram.",
  "imaging_system": "sound"
}
```

**Response**: `HTTP 200 { "received": true }`

---

### POST /api/lab-results/import
CSV upload for Vetscan/Abaxis point-of-care import.

**Request**: `multipart/form-data`
- `file`: CSV file
- `patient_id`: string
- `timeblock_id`: string (optional)
- `provider`: `"vetscan"` | `"abaxis"`

**Response**:
```json
{
  "lab_result_id": "lr-abc123",
  "panel_name": "Chemistry Panel",
  "analyte_count": 12,
  "flagged_count": 1,
  "is_critical": false
}
```

---

### GET /api/patients/{patient_id}/lab-results
All lab results for a patient.

**Response**:
```json
{
  "patient_id": "pat-buddy-001",
  "results": [
    {
      "id": "lr-001",
      "panel_name": "Complete Blood Count",
      "provider": "idexx",
      "received_at": "2026-06-19T10:30:00",
      "is_critical": true,
      "status": "received",
      "flagged_values": [
        { "name": "BUN", "value": 85.0, "unit": "mg/dL", "ref_low": 7, "ref_high": 27, "flag": "HH" }
      ],
      "analytes": [ /* full list */ ]
    }
  ]
}
```

---

### GET /api/timeblocks/{timeblock_id}/lab-results
Lab results linked to a specific appointment.

**Response**: Same shape as patient lab results, filtered by `timeblock_id`.

---

### POST /api/lab-results/{id}/acknowledge
Vet acknowledges a critical lab result, clearing the action queue card.

**Request**:
```json
{ "acknowledged_by": "vet-chen" }
```

**Response**:
```json
{
  "lab_result_id": "lr-001",
  "status": "acknowledged",
  "acknowledged_by": "vet-chen",
  "acknowledged_at": "2026-06-19T10:45:00"
}
```

---

## Demo Simulation Endpoint

### POST /api/simulate/lab-result
For demo use only — simulates an IDEXX result arriving for a given patient without needing a real IDEXX connection.

**Request**:
```json
{
  "patient_id": "pat-buddy-001",
  "timeblock_id": "tb-001",
  "panel": "cbc",         // "cbc" | "chemistry" | "urinalysis"
  "include_critical": true // if true, seeds one HH flag for demo impact
}
```

**Response**: Same as `POST /api/webhooks/idexx/result` response + the created `LabResult` object.
