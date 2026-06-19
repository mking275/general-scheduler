# Integration Batch 0 — Data Model (Remediated)

**Feature**: integration-batch0
> **Remediation applied**: B-01, B-02, B-04, W-02, W-07, W-09 — aligned with live DB schema
**Date**: 2026-06-19

---

## New Tables

### `integration_definitions` (seeded, read-only)

```sql
CREATE TABLE IF NOT EXISTS integration_definitions (
    id          TEXT PRIMARY KEY,         -- e.g. "idexx", "twilio", "stripe"
    name        TEXT NOT NULL,            -- display name
    module      TEXT NOT NULL,            -- "core" | "MOD-COM" | "MOD-FIN" | etc.
    tier        TEXT NOT NULL,            -- "native" | "webhook" | "export"
    description TEXT DEFAULT '',
    logo_emoji  TEXT DEFAULT '🔌',
    required_keys TEXT NOT NULL DEFAULT '[]',  -- JSON array of key names
    test_endpoint TEXT DEFAULT ''         -- internal path for health test
);
```

**Seed data** (INSERT OR IGNORE at startup):
| id | name | module | tier |
|---|---|---|---|
| `idexx` | IDEXX Laboratories | core | native |
| `antech` | Antech Diagnostics | core | native |
| `heska` | Heska | core | webhook |
| `imaging` | Diagnostic Imaging | core | webhook |
| `vetscan` | Zoetis Vetscan / Abaxis | core | webhook |
| `twilio` | Twilio SMS | MOD-COM | native |
| `sendgrid` | SendGrid Email | MOD-COM | native |
| `stripe` | Stripe Terminal | MOD-FIN | native |
| `quickbooks` | QuickBooks Online | MOD-FIN | native |
| `covetrus` | Covetrus | MOD-INV | native |
| `mwi` | MWI Animal Health | MOD-INV | native |

---

> **W-07 note**: `required_keys` is stored as a JSON TEXT column. Repository methods MUST call `json.dumps(list)` on write and `json.loads(str)` on read for this field. Pydantic model handles this transparently but raw `sqlite3.Row` access does not.

---

### `integration_credentials`

```sql
CREATE TABLE IF NOT EXISTS integration_credentials (
    id                TEXT PRIMARY KEY,
    clinic_id         TEXT NOT NULL,
    integration_id    TEXT NOT NULL REFERENCES integration_definitions(id),
    key_name          TEXT NOT NULL,    -- e.g. "IDEXX_PRACTICE_ID"
    encrypted_value   TEXT NOT NULL,    -- AES-256 encrypted; never returned raw
    last_verified_at  TEXT,             -- ISO datetime of last successful connectivity test
    created_at        TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(clinic_id, integration_id, key_name)
);
```

---

### `integration_statuses`

```sql
CREATE TABLE IF NOT EXISTS integration_statuses (
    id                TEXT PRIMARY KEY,
    clinic_id         TEXT NOT NULL,
    integration_id    TEXT NOT NULL REFERENCES integration_definitions(id),
    status            TEXT NOT NULL DEFAULT 'unconfigured',
                      -- 'connected' | 'degraded' | 'disconnected' | 'unconfigured'
    latency_ms        INTEGER,
    error_message     TEXT,
    last_checked_at   TEXT,
    last_connected_at TEXT,
    UNIQUE(clinic_id, integration_id)
);
```

---

### `migration_runs`

```sql
CREATE TABLE IF NOT EXISTS migration_runs (
    id                       TEXT PRIMARY KEY,
    clinic_id                TEXT NOT NULL,
    source_system            TEXT NOT NULL,  -- 'avimark' | 'cornerstone' | 'ezyvet'
    status                   TEXT NOT NULL DEFAULT 'pending',
                             -- 'pending' | 'running' | 'complete' | 'failed'
    phase                    TEXT,           -- current phase name for progress display
    imported_owners          INTEGER DEFAULT 0,
    imported_patients        INTEGER DEFAULT 0,
    imported_visits          INTEGER DEFAULT 0,
    imported_care_events     INTEGER DEFAULT 0,
    imported_prescriptions   INTEGER DEFAULT 0,
    flagged_count            INTEGER DEFAULT 0,
    error_message            TEXT,
    started_at               TEXT,
    completed_at             TEXT,
    created_at               TEXT NOT NULL DEFAULT (datetime('now'))
);
```

---

### `migration_flags`

```sql
CREATE TABLE IF NOT EXISTS migration_flags (
    id                TEXT PRIMARY KEY,
    migration_run_id  TEXT NOT NULL REFERENCES migration_runs(id),
    record_type       TEXT NOT NULL,   -- 'owner' | 'patient' | 'visit' | 'care_event' | 'prescription'
    source_row        TEXT NOT NULL,   -- JSON of the raw source row
    reason            TEXT NOT NULL    -- human-readable reason for flag
);
```

---

### `labs` table extensions (B-01, B-02 remediation)

> **B-01 fix**: The spec originally defined a new `lab_results` table. The real table is `labs` (repository.py:131), already used by `LabsPanel.tsx` at `/api/labs/patient/{id}`. We EXTEND the existing table via ALTER TABLE instead of creating a new one.

> **B-02 fix**: Analyte schema changed from `ref_low`/`ref_high` (flat) to `low`/`high` stored nested inside `results` JSON blob as `{"panels": [{"name": str, "analytes": [{name, value, unit, low, high, flag}]}]}` — matching what `LabsPanel.tsx` already reads as `lab.results?.panels`.

```sql
-- REAL table name: labs (not lab_results)
-- Extend via ALTER TABLE (each wrapped in try/except):
ALTER TABLE labs ADD COLUMN provider TEXT DEFAULT 'manual';
    -- 'manual' (existing) | 'idexx' | 'antech' | 'heska' | 'vetscan' | 'imported'
ALTER TABLE labs ADD COLUMN lab_order_id TEXT;
    -- provider's reference; used for patient matching on inbound webhooks
ALTER TABLE labs ADD COLUMN clinic_id TEXT;
    -- resolved from credential vault on webhook receipt
ALTER TABLE labs ADD COLUMN flagged_values TEXT DEFAULT '[]';
    -- JSON: flat list of analytes with non-empty flag (for quick critical check)
ALTER TABLE labs ADD COLUMN is_critical INTEGER DEFAULT 0;
    -- 1 if any LL/HH flag present in results
ALTER TABLE labs ADD COLUMN acknowledged_by TEXT;
ALTER TABLE labs ADD COLUMN acknowledged_at TEXT;
```

**Existing columns already usable as-is**:
- `id`, `patient_id`, `timeblock_id`, `panel_name`, `status`, `ordered_by`, `ordered_at`, `resulted_at` — all present
- `results TEXT DEFAULT '{}'` — already stores JSON; Lab Agent writes `{"panels": [{"name": ..., "analytes": [{name, value, unit, low, high, flag}]}]}`

**Status field reuse**: existing `status` values (`pending`, `resulted`) extended with `received`, `unmatched`, `acknowledged` for webhook-sourced results.

```sql
-- No new table needed. All endpoints use the existing labs table.
-- GET /api/labs/patient/{patient_id} — already exists, will return webhook results too
-- GET /api/labs/timeblock/{timeblock_id} — already exists
-- POST /api/labs — already exists (manual order path unchanged)
```

---

## Extended Tables

### `owner_images` extensions (B-04 remediation)

> **B-04 fix**: The spec originally referenced a `patient_images` table that does not exist. The real table is `owner_images` (repository.py:142). Clinical imaging columns are added to this table via ALTER TABLE.

```sql
-- REAL table name: owner_images (not patient_images)
-- Add columns via ALTER TABLE (each wrapped in try/except):
ALTER TABLE owner_images ADD COLUMN modality TEXT;
    -- DICOM modality code: 'CR' | 'US' | 'CT' | 'MR' | NULL for owner uploads
    -- source column already exists: DEFAULT 'owner' → extend enum to include 'xray'|'ultrasound'|'ct'|'mri'
ALTER TABLE owner_images ADD COLUMN report_text TEXT;
ALTER TABLE owner_images ADD COLUMN dicom_study_uid TEXT;
ALTER TABLE owner_images ADD COLUMN imaging_system TEXT;
    -- 'sound' | 'idexx_pacs' | 'heska' | 'other'
ALTER TABLE owner_images ADD COLUMN study_date TEXT;
```

> Existing `source` column already present (`DEFAULT 'owner'`). Imaging webhooks write `source='xray'` etc. No ALTER needed for `source` — just use the new values.

---

## Pydantic Models (backend/models.py additions)

```python
class IntegrationDefinition(BaseModel):
    id: str
    name: str
    module: str
    tier: str
    description: str = ""
    logo_emoji: str = "🔌"
    required_keys: List[str] = []  # Stored as JSON TEXT in DB; json.dumps on write, json.loads on read

class IntegrationStatus(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    clinic_id: str
    integration_id: str
    status: str = "unconfigured"  # connected|degraded|disconnected|unconfigured
    latency_ms: Optional[int] = None
    error_message: Optional[str] = None
    last_checked_at: Optional[str] = None
    last_connected_at: Optional[str] = None

class LabAnalyte(BaseModel):
    # B-02 remediation: field names match existing LabsPanel.tsx (a.low, a.high)
    name: str
    value: float
    unit: str
    low: Optional[float] = None    # was ref_low in original spec — CHANGED to match frontend
    high: Optional[float] = None   # was ref_high in original spec — CHANGED to match frontend
    flag: str = ""  # "" | "L" | "H" | "LL" | "HH"

class LabResult(BaseModel):
    # B-01 remediation: extends existing `labs` table (not a new table)
    # B-02 remediation: results stored in existing labs.results JSON blob as:
    #   { "panels": [{ "name": str, "analytes": [{name,value,unit,low,high,flag}] }] }
    # This matches the nested structure LabsPanel.tsx already reads: lab.results?.panels
    id: str = Field(default_factory=lambda: str(uuid4()))
    patient_id: str
    timeblock_id: Optional[str] = None
    clinic_id: str
    provider: str  # idexx|antech|heska|vetscan|imported
    lab_order_id: Optional[str] = None
    panel_name: str
    # analytes stored NESTED under results JSON to match LabsPanel: lab.results.panels[].analytes[]
    results: dict = Field(default_factory=dict)  # {"panels": [{"name": str, "analytes": [LabAnalyte]}]}
    flagged_values: List[LabAnalyte] = []  # flat list for quick access
    is_critical: bool = False
    status: str = "received"  # received|unmatched|acknowledged
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[str] = None
    received_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class MigrationRun(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    clinic_id: str
    source_system: str  # avimark|cornerstone|ezyvet
    status: str = "pending"
    phase: Optional[str] = None
    imported_owners: int = 0
    imported_patients: int = 0
    imported_visits: int = 0
    imported_care_events: int = 0
    imported_prescriptions: int = 0
    flagged_count: int = 0
    error_message: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
```
