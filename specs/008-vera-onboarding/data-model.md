# Feature 008 — Vera Onboarding: Data Model

## Overview

Six new SQLite tables. All use TEXT primary keys (UUIDs as strings) consistent with existing codebase patterns.

---

## Table 1: `onboarding_sessions`

Tracks the full lifecycle of a prospect from first visit through activation.

```sql
CREATE TABLE IF NOT EXISTS onboarding_sessions (
    id               TEXT PRIMARY KEY,
    session_token    TEXT UNIQUE NOT NULL,    -- httpOnly cookie value
    email_anchor     TEXT,                    -- set when magic link provided
    persona_role     TEXT,                    -- owner|manager|associate|proxy
    phase            INTEGER NOT NULL DEFAULT 0,  -- 0=WELCOME..6=LIVE
    track            TEXT DEFAULT 'greenfield',   -- greenfield|switcher|paper
    practice_name    TEXT,
    state_json       TEXT DEFAULT '{}',       -- accumulated context as JSON blob
    activation_timestamp TEXT,               -- ISO datetime of first real booking
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL
);
```

| Column | Type | Notes |
|---|---|---|
| `id` | TEXT (UUID) | Primary key |
| `session_token` | TEXT UNIQUE | UUID4; value stored in httpOnly cookie |
| `email_anchor` | TEXT | Optional; set when magic link email provided |
| `persona_role` | TEXT | `owner` \| `manager` \| `associate` \| `proxy` |
| `phase` | INTEGER | 0=WELCOME, 1=DEMO, 2=PIVOT, 3=OPEN_PROMPT, 4=DOCUMENT, 5=REPLACE, 6=LIVE |
| `track` | TEXT | `greenfield` \| `switcher` \| `paper` |
| `practice_name` | TEXT | Extracted from Q1 |
| `state_json` | TEXT | JSON blob of accumulated fields (address, hours, services, etc.) |
| `activation_timestamp` | TEXT | ISO datetime; set on first real client booking |
| `created_at` | TEXT | ISO datetime |
| `updated_at` | TEXT | ISO datetime; updated on every phase transition |

---

## Table 2: `magic_links`

Single-use time-limited tokens for cross-device session resume.

```sql
CREATE TABLE IF NOT EXISTS magic_links (
    id                TEXT PRIMARY KEY,
    session_id        TEXT NOT NULL REFERENCES onboarding_sessions(id),
    email             TEXT NOT NULL,
    token_hash        TEXT UNIQUE NOT NULL,  -- SHA-256 of raw token
    expires_at        TEXT NOT NULL,         -- ISO datetime; 30 days from creation
    used_at           TEXT,                  -- ISO datetime; set on first use
    device_fingerprint TEXT,                 -- UA+Accept-Language hash at issue time
    created_at        TEXT NOT NULL
);
```

| Column | Type | Notes |
|---|---|---|
| `id` | TEXT (UUID) | Primary key |
| `session_id` | TEXT (FK) | References `onboarding_sessions.id` |
| `email` | TEXT | Email address where link was sent |
| `token_hash` | TEXT UNIQUE | SHA-256 of the raw URL-safe token (never stored raw) |
| `expires_at` | TEXT | 30 days from `created_at` |
| `used_at` | TEXT | NULL until first use; single-use enforced |
| `device_fingerprint` | TEXT | Optional; `User-Agent + Accept-Language` concatenation |
| `created_at` | TEXT | ISO datetime |

---

## Table 3: `logo_assets`

Scraped or uploaded logo candidates associated with a session.

```sql
CREATE TABLE IF NOT EXISTS logo_assets (
    id           TEXT PRIMARY KEY,
    session_id   TEXT NOT NULL REFERENCES onboarding_sessions(id),
    source_type  TEXT NOT NULL,   -- og_image|favicon|header_img|upload|monogram
    source_url   TEXT,            -- original URL (null for uploads/monograms)
    local_path   TEXT,            -- server-side cached file path
    confirmed    INTEGER NOT NULL DEFAULT 0,  -- 0|1
    fallback_type TEXT,           -- 'image'|'monogram'
    initials     TEXT,            -- e.g. 'RAH'; populated for monogram type
    created_at   TEXT NOT NULL
);
```

| Column | Type | Notes |
|---|---|---|
| `id` | TEXT (UUID) | Primary key |
| `session_id` | TEXT (FK) | References `onboarding_sessions.id` |
| `source_type` | TEXT | `og_image` \| `favicon` \| `header_img` \| `upload` \| `monogram` |
| `source_url` | TEXT | Original scraped URL; NULL for uploads and monograms |
| `local_path` | TEXT | Server-cached copy path |
| `confirmed` | INTEGER | Boolean; 0 until user clicks "Yes, that's our logo" |
| `fallback_type` | TEXT | `image` \| `monogram` |
| `initials` | TEXT | Initials string for monogram type (e.g., `RAH`) |
| `created_at` | TEXT | ISO datetime |

---

## Table 4: `onboarding_documents`

Uploaded files in staging — not committed to live DB until confirmed.

```sql
CREATE TABLE IF NOT EXISTS onboarding_documents (
    id               TEXT PRIMARY KEY,
    session_id       TEXT NOT NULL REFERENCES onboarding_sessions(id),
    mime_type        TEXT NOT NULL,
    file_size_bytes  INTEGER NOT NULL,
    storage_path     TEXT NOT NULL,       -- absolute server path in uploads/
    classified_type  TEXT,                -- staff_roster|room_list|schedule|license|fee_schedule|unknown
    extraction_json  TEXT DEFAULT '{}',  -- cached extraction result
    streaming_status TEXT DEFAULT 'pending',  -- pending|in_progress|complete|timed_out
    created_at       TEXT NOT NULL
);
```

| Column | Type | Notes |
|---|---|---|
| `id` | TEXT (UUID) | Primary key |
| `session_id` | TEXT (FK) | References `onboarding_sessions.id` |
| `mime_type` | TEXT | IANA MIME type of uploaded file |
| `file_size_bytes` | INTEGER | Pre-validated < 26,214,400 (25MB) |
| `storage_path` | TEXT | Absolute path in `backend/uploads/` staging dir |
| `classified_type` | TEXT | Document type classification |
| `extraction_json` | TEXT | Full extraction cache (JSON); populated after streaming completes |
| `streaming_status` | TEXT | `pending` → `in_progress` → `complete` \| `timed_out` |
| `created_at` | TEXT | ISO datetime |

---

## Table 5: `extracted_entities`

Individual structured records parsed from a document. Not written to live DB until confirmed.

```sql
CREATE TABLE IF NOT EXISTS extracted_entities (
    id               TEXT PRIMARY KEY,
    document_id      TEXT NOT NULL REFERENCES onboarding_documents(id),
    entity_type      TEXT NOT NULL,       -- provider|room|service|hour|phone|address
    source_text      TEXT,                -- verbatim source text (for click-to-cite)
    source_position  TEXT,               -- JSON: {sheet, row, col} or {page, char_offset}
    confidence       REAL NOT NULL DEFAULT 0.5,  -- 0.0–1.0
    extracted_fields TEXT DEFAULT '{}',  -- JSON: the parsed field values
    has_conflict     INTEGER DEFAULT 0,  -- 1 if conflicting values found across tabs
    requires_input   INTEGER DEFAULT 0,  -- 1 if confidence < 0.7
    confirmed        INTEGER DEFAULT 0,  -- 1 when user confirms; triggers live DB write
    created_at       TEXT NOT NULL
);
```

| Column | Type | Notes |
|---|---|---|
| `id` | TEXT (UUID) | Primary key |
| `document_id` | TEXT (FK) | References `onboarding_documents.id` |
| `entity_type` | TEXT | `provider` \| `room` \| `service` \| `hour` \| `phone` \| `address` |
| `source_text` | TEXT | Verbatim text from source (click-to-cite) |
| `source_position` | TEXT | JSON: `{"sheet": "Staff", "row": 3, "col": 1}` |
| `confidence` | REAL | 0.0–1.0; ≥ 0.8 = ✅; 0.5–0.79 = ⚠️; < 0.5 = ❓ |
| `extracted_fields` | TEXT | JSON: e.g. `{"name": "Dr. Rivera", "role": "DVM", "days": ["Mon","Tue"]}` |
| `has_conflict` | INTEGER | Boolean; 1 if same entity appears with different values across tabs |
| `requires_input` | INTEGER | Boolean; 1 if confidence < 0.7 |
| `confirmed` | INTEGER | Boolean; triggers live DB write on transition to 1 |
| `created_at` | TEXT | ISO datetime |

---

## Table 6: `extraction_corrections`

Training signals logged when users correct Vera's extracted values.

```sql
CREATE TABLE IF NOT EXISTS extraction_corrections (
    id                    TEXT PRIMARY KEY,
    entity_id             TEXT NOT NULL REFERENCES extracted_entities(id),
    document_type         TEXT NOT NULL,     -- classified_type of parent document
    field_name            TEXT NOT NULL,     -- which field was corrected
    vera_value            TEXT NOT NULL,     -- Vera's original extracted value
    correct_value         TEXT NOT NULL,     -- user's correction
    confidence_at_correction REAL NOT NULL,  -- confidence score at time of correction
    corrected_at          TEXT NOT NULL      -- ISO datetime
);
```

| Column | Type | Notes |
|---|---|---|
| `id` | TEXT (UUID) | Primary key |
| `entity_id` | TEXT (FK) | References `extracted_entities.id` |
| `document_type` | TEXT | Inherited from parent document's `classified_type` |
| `field_name` | TEXT | Which specific field was corrected (e.g., `"name"`, `"role"`) |
| `vera_value` | TEXT | What Vera extracted |
| `correct_value` | TEXT | What the user said it should be |
| `confidence_at_correction` | REAL | Vera's confidence at the time of correction (for training signal quality) |
| `corrected_at` | TEXT | ISO datetime |
