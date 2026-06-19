# Integration Batch 0 — API Contracts (Remediated)

**Feature**: integration-batch0
**Date**: 2026-06-19
> **Remediation applied**: B-01, B-02, B-04, W-02, W-03, W-04, W-09

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

> **B-01 remediation**: All lab result endpoints use the EXISTING `/api/labs/...` routes. No new `/api/patients/{id}/lab-results` route is created. Webhook-delivered results write to the existing `labs` table and are immediately visible via the existing `LabsPanel.tsx`.

> **B-02 remediation**: Analyte schema in all webhook payloads uses `low`/`high` (not `ref_low`/`ref_high`). Results JSON blob uses nested structure `{"panels": [{"name": ..., "analytes": [...]}]}` to match what `LabsPanel.tsx` reads as `lab.results?.panels`.

> **W-02 remediation**: Inbound webhooks do not include `clinic_id`. Lab Agent resolves clinic by looking up which clinic has a matching `practice_id` in `integration_credentials`. Repository method: `get_clinic_id_by_credential(integration_id='idexx', key_name='IDEXX_PRACTICE_ID', value=payload['practice_id'])`.

> **W-03 remediation**: All webhook endpoints must read raw bytes BEFORE JSON parsing for HMAC validation:
> ```python
> body_bytes = await request.body()
> validate_hmac(body_bytes, request.headers.get("X-IDEXX-Signature", ""), secret)
> data = json.loads(body_bytes)
> ```
> Webhook endpoints MUST be `async def` to use `await request.body()`.

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
        { "name": "WBC",  "value": 14.2, "unit": "K/uL",  "low": 6.0,  "high": 17.0, "flag": "H"  },
        { "name": "RBC",  "value": 7.1,  "unit": "M/uL",  "low": 5.5,  "high": 8.5,  "flag": ""   },
        { "name": "BUN",  "value": 85.0, "unit": "mg/dL", "low": 7.0,  "high": 27.0, "flag": "HH" }
      ]
    }
  ]
}
```

**Lab Agent normalises to existing `labs` table row**:
```json
{
  "id": "<uuid>",
  "patient_id": "pat-buddy-001",
  "timeblock_id": "tb-001",
  "panel_name": "Complete Blood Count",
  "provider": "idexx",
  "lab_order_id": "ORD-IDEXX-001",
  "status": "received",
  "ordered_at": "2026-06-19T10:30:00",
  "resulted_at": "2026-06-19T10:30:00",
  "results": {"panels": [{"name": "Complete Blood Count", "analytes": [
    {"name": "WBC", "value": 14.2, "unit": "K/uL", "low": 6.0, "high": 17.0, "flag": "H"},
    {"name": "BUN", "value": 85.0, "unit": "mg/dL", "low": 7.0, "high": 27.0, "flag": "HH"}
  ]}]},
  "is_critical": 1,
  "flagged_values": [{"name": "BUN", "value": 85.0, "flag": "HH"}]
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

### GET /api/labs/patient/{patient_id}
> **B-01 remediation**: EXISTING endpoint (main.py:862). No new route. Lab Agent writes webhook results to `labs` table; this endpoint returns them alongside manually-ordered labs.

**Response** (unchanged from existing):
```json
[
  {
    "id": "lr-001",
    "panel_name": "Complete Blood Count",
    "provider": "idexx",
    "status": "received",
    "is_critical": 1,
    "ordered_at": "2026-06-19T10:30:00",
    "resulted_at": "2026-06-19T10:30:00",
    "results": {
      "panels": [{
        "name": "Complete Blood Count",
        "analytes": [
          { "name": "WBC",  "value": 14.2, "unit": "K/uL",  "low": 6.0,  "high": 17.0, "flag": "H"  },
          { "name": "BUN",  "value": 85.0, "unit": "mg/dL", "low": 7.0,  "high": 27.0, "flag": "HH" }
        ]
      }]
    },
    "flagged_values": [{"name": "BUN", "value": 85.0, "flag": "HH"}]
  }
]
```

---

### GET /api/labs/timeblock/{timeblock_id}
> **B-01 remediation**: EXISTING endpoint (main.py:872). No new route.

---

### POST /api/labs/{id}/acknowledge
> **B-01 remediation**: Uses `labs` table ID (not `lab_results`). Replaces `/api/lab-results/{id}/acknowledge` from original spec.

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

**Response**: Same as `POST /api/webhooks/idexx/result` response + the created lab row object.

---

## Missing Endpoints Added by Remediation

### PATCH /api/labs/{id} (W-04 remediation)
Manually assign an unmatched lab result to a patient.

**Request**:
```json
{ "patient_id": "pat-buddy-001", "timeblock_id": "tb-001" }
```

**Response**: Updated lab row with `status='received'`.

---

### GET /api/patients/{patient_id}/images (W-09 remediation)
Return all images for a patient from the `owner_images` table, including clinical imaging (modality != NULL).

**Response**:
```json
[
  {
    "id": "img-001",
    "patient_id": "pat-luna-001",
    "timeblock_id": "tb-001",
    "filename": "thoracic_xray.jpg",
    "source": "xray",
    "modality": "CR",
    "report_text": "Mild cardiomegaly. Recommend echocardiogram.",
    "study_date": "2026-06-19",
    "caption": "Thoracic X-Ray",
    "submitted_at": "2026-06-19T10:00:00"
  },
  {
    "id": "img-002",
    "source": "owner",
    "modality": null,
    "caption": "Owner-submitted photo"
  }
]
```
