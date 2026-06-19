# Integration Batch 0 — Data Model

**Feature**: integration-batch0
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

### `lab_results`

```sql
CREATE TABLE IF NOT EXISTS lab_results (
    id                TEXT PRIMARY KEY,
    patient_id        TEXT NOT NULL REFERENCES patients(id),
    timeblock_id      TEXT REFERENCES timeblocks(id),  -- nullable
    clinic_id         TEXT NOT NULL,
    provider          TEXT NOT NULL,   -- 'idexx' | 'antech' | 'heska' | 'vetscan' | 'imported'
    lab_order_id      TEXT,            -- provider's reference; used for matching
    panel_name        TEXT NOT NULL,   -- e.g. "Complete Blood Count"
    analytes          TEXT NOT NULL DEFAULT '[]',
                      -- JSON: [{name, value, unit, ref_low, ref_high, flag}]
                      -- flag: '' | 'L' | 'H' | 'LL' | 'HH'
    flagged_values    TEXT NOT NULL DEFAULT '[]',
                      -- JSON: subset of analytes with non-empty flag
    is_critical       INTEGER NOT NULL DEFAULT 0,  -- 1 if any LL/HH flag present
    status            TEXT NOT NULL DEFAULT 'received',
                      -- 'received' | 'unmatched' | 'acknowledged'
    acknowledged_by   TEXT,            -- resource.id of acknowledging vet
    acknowledged_at   TEXT,
    received_at       TEXT NOT NULL DEFAULT (datetime('now'))
);
```

---

## Extended Tables

### `patient_images` extensions

```sql
-- Existing table; add columns via ALTER TABLE (wrap in try/except):
ALTER TABLE patient_images ADD COLUMN source TEXT DEFAULT 'owner_upload';
    -- 'owner_upload' | 'xray' | 'ultrasound' | 'ct' | 'mri'
ALTER TABLE patient_images ADD COLUMN modality TEXT;
    -- DICOM modality code: 'CR' | 'US' | 'CT' | 'MR' | NULL for owner uploads
ALTER TABLE patient_images ADD COLUMN report_text TEXT;
ALTER TABLE patient_images ADD COLUMN dicom_study_uid TEXT;
ALTER TABLE patient_images ADD COLUMN imaging_system TEXT;
    -- 'sound' | 'idexx_pacs' | 'heska' | 'other'
ALTER TABLE patient_images ADD COLUMN study_date TEXT;
```

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
    required_keys: List[str] = []

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
    name: str
    value: float
    unit: str
    ref_low: Optional[float] = None
    ref_high: Optional[float] = None
    flag: str = ""  # "" | "L" | "H" | "LL" | "HH"

class LabResult(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    patient_id: str
    timeblock_id: Optional[str] = None
    clinic_id: str
    provider: str  # idexx|antech|heska|vetscan|imported
    lab_order_id: Optional[str] = None
    panel_name: str
    analytes: List[LabAnalyte] = []
    flagged_values: List[LabAnalyte] = []
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
