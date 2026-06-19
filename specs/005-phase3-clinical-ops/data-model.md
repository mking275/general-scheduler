# Data Model: Phase 3 Clinical Operations

**Feature**: specs/005-phase3-clinical-ops  
**Date**: 2026-06-19  
**SQLite tables**: 6 new + 1 extended

---

## New Tables

### `breed_protocols`

```sql
CREATE TABLE IF NOT EXISTS breed_protocols (
    id          TEXT PRIMARY KEY,
    breed_pattern      TEXT NOT NULL,         -- partial match string, case-insensitive
    flag_type          TEXT NOT NULL,         -- brachycephalic | oncology | cardiac | ortho | renal
    title              TEXT NOT NULL,         -- short label e.g. "Anaesthesia Risk"
    detail             TEXT NOT NULL,         -- full protocol detail shown to vet
    age_threshold_years REAL DEFAULT 0,       -- 0 = applies at any age
    severity           TEXT DEFAULT 'info'    -- info | warning | critical
);
```

**Seed entries (12)**:

| breed_pattern | flag_type | title | severity | age_threshold_years |
|---|---|---|---|---|
| Bulldog | brachycephalic | Anaesthesia Risk | critical | 0 |
| Pug | brachycephalic | Anaesthesia Risk | critical | 0 |
| Boston Terrier | brachycephalic | Anaesthesia Risk | critical | 0 |
| Shih Tzu | brachycephalic | Anaesthesia Risk | warning | 0 |
| Golden Retriever | oncology | Oncology Screening | warning | 6 |
| Labrador | oncology | Oncology Screening | info | 7 |
| Cavalier King Charles | cardiac | Cardiac Monitoring | warning | 4 |
| Doberman | cardiac | DCM Screening | warning | 5 |
| German Shepherd | ortho | Hip Dysplasia Protocol | info | 1 |
| Dachshund | ortho | IVDD Risk | warning | 3 |
| Maine Coon | cardiac | HCM Screening | warning | 3 |
| Persian | renal | PKD Monitoring | warning | 2 |

**Match logic**: `lower(patient.breed) LIKE '%' || lower(breed_pattern) || '%'`

---

### `waitlist`

```sql
CREATE TABLE IF NOT EXISTS waitlist (
    id                TEXT PRIMARY KEY,
    patient_id        TEXT NOT NULL,
    clinic_id         TEXT NOT NULL,
    procedure_type    TEXT NOT NULL,
    preferred_vet_id  TEXT,                -- nullable
    urgency           TEXT DEFAULT 'flexible',  -- flexible | within_week | asap
    offer_status      TEXT DEFAULT 'waiting',   -- waiting | offered | accepted | expired
    join_date         TEXT NOT NULL        -- ISO datetime
);
```

**Scoring logic** (BackfillAgent):
- `exact procedure + vet match` → 100 pts
- `same procedure, any vet` → 80 pts  
- `same category (e.g. Surgery)` → 40 pts
- Tiebreaker: `urgency DESC (asap > within_week > flexible)`, then `join_date ASC`

---

### `care_protocols`

```sql
CREATE TABLE IF NOT EXISTS care_protocols (
    id              TEXT PRIMARY KEY,
    species         TEXT NOT NULL,          -- dog | cat | all
    protocol_name   TEXT NOT NULL,
    interval_months INTEGER NOT NULL
);
```

**Seed entries (8)**:

| species | protocol_name | interval_months |
|---|---|---|
| dog | DHPP | 12 |
| all | Rabies | 12 |
| dog | Bordetella | 6 |
| cat | FVRCP | 12 |
| cat | FeLV | 12 |
| dog | Leptospirosis | 12 |
| dog | Heartworm Test | 12 |
| all | Dental | 12 |

---

### `care_events`

```sql
CREATE TABLE IF NOT EXISTS care_events (
    id               TEXT PRIMARY KEY,
    patient_id       TEXT NOT NULL,
    protocol_id      TEXT NOT NULL REFERENCES care_protocols(id),
    timeblock_id     TEXT,                  -- nullable FK; null = historical/standalone
    administered_date TEXT NOT NULL,        -- ISO date
    next_due_date     TEXT NOT NULL,        -- ISO date; computed = administered_date + interval_months
    batch_number      TEXT DEFAULT '',
    administered_by   TEXT DEFAULT ''       -- vet name string
);
```

**Overdue logic**: `next_due_date < date('now')` → flag patient with 🔴 OVERDUE  
**Due-soon logic**: `next_due_date BETWEEN date('now') AND date('now', '+30 days')`

**Seed**: Include care_events for 3+ existing patients with:
- At least 2 events where `next_due_date` is in the past (overdue)
- At least 2 events where `next_due_date` is within 30 days (upcoming)

---

### `prescriptions`

```sql
CREATE TABLE IF NOT EXISTS prescriptions (
    id               TEXT PRIMARY KEY,
    patient_id       TEXT NOT NULL,
    timeblock_id     TEXT,                  -- nullable; links to issuing appointment
    drug_name        TEXT NOT NULL,
    dose             TEXT NOT NULL,         -- e.g. "25mg"
    frequency        TEXT NOT NULL,         -- e.g. "BID" (twice daily)
    duration_days    INTEGER NOT NULL,
    refills_remaining INTEGER DEFAULT 0,
    supply_ends_at   TEXT NOT NULL,         -- ISO date; issued_date + duration_days
    issued_by        TEXT NOT NULL,         -- vet name
    issued_date      TEXT NOT NULL          -- ISO date
);
```

**Drug list** (seeded in `prescription.py` — 20 drugs):
`Carprofen, Meloxicam, Amoxicillin, Cephalexin, Metronidazole, Prednisone, Enalapril, Furosemide, Phenobarbital, Tramadol, Gabapentin, Apoquel, Cytopoint, Doxycycline, Clindamycin, Trazodone, Acepromazine, Maropitant, Omeprazole, Onsior`

**Drug-class allergy map** (hardcoded in `prescription.py`):

```python
DRUG_CLASS_MAP = {
    "penicillin":    ["amoxicillin", "ampicillin"],
    "nsaid":         ["carprofen", "meloxicam", "onsior"],
    "sulfa":         ["sulfamethoxazole"],
    "cephalosporin": ["cephalexin", "cefpodoxime"],
}
```

**Conflict check**: patient `flag_notes` (lowercased) searched for drug class keywords → triggers warning if match found. Buddy (Golden Retriever) has `flag_notes: "penicillin allergy"` → conflict on Amoxicillin.

---

### `refill_requests`

```sql
CREATE TABLE IF NOT EXISTS refill_requests (
    id               TEXT PRIMARY KEY,
    prescription_id  TEXT NOT NULL REFERENCES prescriptions(id),
    initiated_by     TEXT NOT NULL,         -- "vet" | "front_desk"
    status           TEXT DEFAULT 'pending', -- pending | auto_approved | vet_review | approved | declined
    requested_at     TEXT NOT NULL,         -- ISO datetime
    reviewed_by      TEXT,                  -- nullable; vet name if reviewed
    reviewed_at      TEXT                   -- nullable ISO datetime
);
```

**Auto-approval logic** (PrescriptionAgent):
- `refills_remaining > 0` **AND** most recent completed appointment for patient within 12 months → `auto_approved`
- Otherwise → `vet_review`

---

## Extended Tables

### `timeblocks` (extended)

**New columns** (added via `ALTER TABLE … ADD COLUMN … DEFAULT … `):

| Column | Type | Default | Notes |
|---|---|---|---|
| `confirmation_status` | TEXT | `not_sent` | `not_sent \| sent \| confirmed \| unconfirmed \| reschedule_requested` |
| `confirmed_at` | TEXT | NULL | ISO datetime |
| `reminder_sent_at` | TEXT | NULL | ISO datetime |

---

## Entity Relationships

```
patients ──< care_events >── care_protocols
patients ──< prescriptions >── refill_requests
patients ──< waitlist
patients ── breed_protocols  (via breed string match, no FK)

timeblocks ─── confirmation_status columns (extended in place)
timeblocks ──< care_events (nullable FK)
timeblocks ──< prescriptions (nullable FK)
```

---

## State Machines

### `confirmation_status` transitions
```
not_sent → sent → confirmed
                → unconfirmed   (T-24h passes without reply)
                → reschedule_requested → (slot freed, backfill triggered)
```

### `offer_status` transitions (WaitlistEntry)
```
waiting → offered → accepted  (slot booked, entry removed from active)
                  → expired   (declined or timeout; next match tried)
```

### `refill_requests.status` transitions
```
pending → auto_approved  (criteria met; front desk approves in 1 click)
        → vet_review     (criteria not met; waits for vet)
vet_review → approved | declined
```
