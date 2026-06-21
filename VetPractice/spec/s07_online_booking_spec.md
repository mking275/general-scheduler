# S07 — VPMA Online Booking Portal: Phase 1 Engineering Specification

**Feature ID:** S07  
**Status:** Ready for Implementation  
**Spec Version:** 1.0  
**Date:** 2026-06-20  
**Based on Design Doc:** `VetPractice/design/online_booking_portal.md` v1.0  
**Author:** Engineering  

---

## Table of Contents

1. [Overview](#1-overview)
2. [New Database Tables](#2-new-database-tables)
3. [Modified Existing Tables](#3-modified-existing-tables)
4. [New API Routes — Public Booking Endpoints](#4-new-api-routes)
5. [New Pydantic Models](#5-new-pydantic-models)
6. [New Agent / Module Files](#6-new-agent--module-files)
7. [Security & Privacy Model](#7-security--privacy-model)
8. [Integration Points with Existing System](#8-integration-points-with-existing-system)
9. [Frontend Architecture (Phase 1)](#9-frontend-architecture-phase-1)
10. [Phase 1 Acceptance Criteria](#10-phase-1-acceptance-criteria)

---

## 1. Overview

### Feature ID
S07

### Description

S07 adds a public-facing, native online appointment booking portal to VPMA. Pet owners navigate to `https://book.vpma.app/{clinic_slug}` (or embed URL), complete a guided multi-step wizard to select a pet, choose an appointment type, pick an available slot, and confirm a booking — all without creating a staff account or using any third-party widget. On confirmation the system creates a durable booking token, fires an intake form via email (SMS if MOD-COM licensed), and arms the T-48h and T-2h reminder pipeline. A unique status URL (`/status/{booking_token}`) gives owners a live lifecycle view of their appointment from booking through post-visit follow-up.

### Phase 1 Scope Statement

**In scope (Phase 1):**

- Public booking wizard (Steps 0–5): clinic landing, owner identification, pet selection, appointment type selection, slot selection, review + confirm
- Returning client lookup via phone/email; session-token-gated data access
- New client registration (owner + first patient) during booking flow
- Slot availability: chronological list only — no AI ranking (Phase 2)
- Soft-hold mechanism (10-min TTL) to prevent race conditions
- Booking confirmation: atomic conversion of soft-hold to `timeblocks` record
- `booking_tokens` table: durable per-booking token for status page access
- `intake_tokens` table: 7-day delivery token; form delivery via email (SMS gated on MOD-COM)
- `intake_responses` table: structured Q&A storage
- Reminder pipeline auto-arm on booking confirmation (calls existing `ReminderAgent`)
- Status page (`GET /public/status/{booking_token}`): static poll-on-load, no SSE (Phase 2)
- Waitlist join (basic): owner/patient recorded; notification when slot opens; manual claim flow (no AI backfill — Phase 2)
- Staff admin config: `clinic_booking_config` — enable/disable booking, set bookable appointment types, scheduling rules
- All public routes rate-limited; verbose log entries for every portal action
- Frontend: React SPA in `/frontend/src/booking/` subdirectory of existing frontend

**Explicitly deferred to Phase 2:**
- AI slot ranking (`score_slot`, `rank_explanation`)
- Real-time SSE status updates (`GET /public/bookings/{token}/stream`)
- AI waitlist backfill (`waitlist.py` cancellation trigger → ranked offer)
- Risk agent integration at slot selection and intake submission
- Waitlist claim token SMS flow (`waitlist_claim_tokens`)

**Explicitly deferred to Phase 3:**
- Custom domain (CNAME) support
- MOD-FIN deposit collection at booking
- Embeddable shadow-DOM widget script
- Progressive Web App manifest + service worker
- Owner history portal (OTP login)

### Core Principles

1. **Public-facing:** No staff auth token required. Owner session is established via phone/email lookup and a server-side session cookie.
2. **Native:** All routes are on the VPMA FastAPI backend (`/public/*` prefix). Zero third-party booking widget dependencies.
3. **Mobile-first:** All UI components must meet 44×44px minimum touch target, 16px minimum body font, sticky CTA on mobile viewport.

---

## 2. New Database Tables

All SQL is SQLite-compatible. Use `TEXT` for UUIDs (SQLite has no native UUID type). All `DATETIME` fields store ISO 8601 strings (`YYYY-MM-DDTHH:MM:SS`). Use `ALTER TABLE ... ADD COLUMN` pattern (wrapped in try/except, matching existing `_init_db` style in `repository.py`) for additive migrations.

---

### 2.1 `clinic_booking_config`

Per-clinic configuration for the online booking portal. One row per clinic. Created when staff first visits booking settings page (or pre-seeded with defaults).

```sql
CREATE TABLE IF NOT EXISTS clinic_booking_config (
    id                          TEXT PRIMARY KEY,         -- UUID v4
    clinic_id                   TEXT NOT NULL UNIQUE,     -- FK → clinics.id
    
    -- Feature flags
    online_booking_enabled      INTEGER NOT NULL DEFAULT 0,  -- 0=false, 1=true
    same_day_booking_enabled    INTEGER NOT NULL DEFAULT 0,
    waitlist_enabled            INTEGER NOT NULL DEFAULT 1,
    -- auto_confirm=1: bookings go straight to 'booked'; 0: status='pending_review'
    auto_confirm                INTEGER NOT NULL DEFAULT 1,
    -- require_deposit is a MOD-FIN hook; always 0 in Phase 1
    require_deposit             INTEGER NOT NULL DEFAULT 0,
    deposit_amount_cents        INTEGER DEFAULT 0,
    
    -- Scheduling rules
    -- Max days in the future a client can book (default 30)
    advance_booking_days        INTEGER NOT NULL DEFAULT 30,
    -- Local hour (24h) after which same-day slots are hidden (default 14 = 2pm)
    same_day_cutoff_hour        INTEGER NOT NULL DEFAULT 14,
    -- Minimum hours of notice required; blocks booking < X hours from now
    min_booking_notice_hours    INTEGER NOT NULL DEFAULT 1,
    -- Buffer minutes required between consecutive appointments for the same vet
    buffer_minutes              INTEGER NOT NULL DEFAULT 10,
    
    -- Display settings
    show_vet_names              INTEGER NOT NULL DEFAULT 1,   -- 0: show "Dr. [Initial]." only
    show_vet_photos             INTEGER NOT NULL DEFAULT 0,
    
    -- Bookable appointment types: JSON array of objects
    -- Schema: [{"id": "wellness", "name": "Annual Wellness Exam",
    --           "duration_minutes": 45, "enabled": true,
    --           "intake_question_set": "wellness",
    --           "breed_duration_overrides": {"Persian": 60}}]
    bookable_appointment_types  TEXT NOT NULL DEFAULT '[]',
    
    -- Messaging customization
    booking_confirmation_msg    TEXT DEFAULT '',   -- Shown on Step 5 confirmation screen
    cancellation_policy         TEXT DEFAULT '',   -- Displayed inline at confirm step
    -- Custom SMS template (template vars: {pet_name}, {vet_name}, {date}, {time}, {intake_link})
    intake_sms_template         TEXT DEFAULT '',
    
    -- Hidden resource IDs: JSON array of resource UUIDs not shown to clients
    -- e.g. '["uuid1", "uuid2"]'
    hidden_resource_ids         TEXT NOT NULL DEFAULT '[]',
    
    -- Emergency info shown in portal header
    emergency_phone             TEXT DEFAULT '',
    emergency_message           TEXT DEFAULT '',
    
    -- Branding (hex strings: "#2E7D52")
    brand_color_primary         TEXT DEFAULT '#6C63FF',
    brand_color_accent          TEXT DEFAULT '#F0A500',
    
    created_at                  TEXT NOT NULL,
    updated_at                  TEXT NOT NULL,
    
    FOREIGN KEY (clinic_id) REFERENCES clinics(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_cbc_clinic_id ON clinic_booking_config(clinic_id);
```

**Notes:**
- `bookable_appointment_types` stores the full appointment type config as JSON because SQLite lacks JSONB; parsed by Python into a list of dicts.
- `hidden_resource_ids` JSON array: if a `resource.id` appears here, that vet's slots are excluded from availability results entirely.
- `same_day_cutoff_hour` is in the clinic's local timezone (use `clinic.timezone` for conversion).

---

### 2.2 `owner_sessions`

Ephemeral session records for the public booking flow. One row per active session. Linked to `owners` once identification succeeds (NULL for anonymous pre-registration state).

```sql
CREATE TABLE IF NOT EXISTS owner_sessions (
    id              TEXT PRIMARY KEY,         -- UUID v4; value placed in cookie
    owner_id        TEXT,                     -- FK → owners.id; NULL until identified
    clinic_id       TEXT NOT NULL,            -- FK → clinics.id (scopes the session)
    
    -- Network context for audit
    ip_address      TEXT NOT NULL DEFAULT '',
    user_agent      TEXT NOT NULL DEFAULT '',
    
    -- Ephemeral booking flow state stored as JSON
    -- Schema: {"selected_patient_id": null, "selected_slot_id": null,
    --          "selected_appt_type_id": null, "urgency": null, "notes": null}
    flow_state      TEXT NOT NULL DEFAULT '{}',
    
    -- Timing
    expires_at      TEXT NOT NULL,            -- ISO datetime; 30 min sliding window
    last_active_at  TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    
    -- Filled once booking is confirmed
    booking_token_id TEXT,                    -- FK → booking_tokens.id
    
    FOREIGN KEY (owner_id) REFERENCES owners(id),
    FOREIGN KEY (clinic_id) REFERENCES clinics(id),
    FOREIGN KEY (booking_token_id) REFERENCES booking_tokens(id)
);

CREATE INDEX IF NOT EXISTS idx_owner_sessions_owner_id   ON owner_sessions(owner_id);
CREATE INDEX IF NOT EXISTS idx_owner_sessions_expires_at ON owner_sessions(expires_at);
-- Cleanup query (run every 15 min via FastAPI background task):
-- DELETE FROM owner_sessions WHERE expires_at < datetime('now')
```

**Notes:**
- `flow_state` is intentionally thin — it stores booking wizard context only. Do **not** store PHI in this column (no diagnoses, no medical history, no full addresses).
- `expires_at` is extended by 30 minutes on every authenticated request. The session is validated against the DB on each request; self-contained JWTs are NOT used (design doc §13.2).

---

### 2.3 `booking_tokens`

Durable per-booking token. Created atomically with the `timeblocks` record. This token IS the "auth" for the status page — no additional login required.

```sql
CREATE TABLE IF NOT EXISTS booking_tokens (
    id              TEXT PRIMARY KEY,         -- UUID v4; appears in status URL
    timeblock_id    TEXT NOT NULL,            -- FK → timeblocks.id
    owner_id        TEXT NOT NULL,            -- FK → owners.id
    clinic_id       TEXT NOT NULL,            -- FK → clinics.id
    
    -- Token lifecycle
    -- active: normal; cancelled: owner/staff cancelled; expired: TTL passed; complete: appt done
    status          TEXT NOT NULL DEFAULT 'active'
                    CHECK (status IN ('active', 'cancelled', 'expired', 'complete')),
    -- 30 days after appointment date (not creation date)
    expires_at      TEXT NOT NULL,
    
    -- Mirrors appointment lifecycle (drives status page display)
    -- booked → intake_sent → intake_complete → confirmed → in_progress → complete → follow_up_sent
    lifecycle_state TEXT NOT NULL DEFAULT 'booked'
                    CHECK (lifecycle_state IN (
                        'booked', 'intake_sent', 'intake_complete',
                        'confirmed', 'in_progress', 'complete', 'follow_up_sent'
                    )),
    
    -- Audit
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    cancelled_at    TEXT,
    -- Reason code: 'owner_request' | 'staff_cancel' | 'no_show' | 'system'
    cancel_reason   TEXT,
    cancel_notes    TEXT,
    
    -- Booking source for analytics
    -- online_portal | staff_dashboard | waitlist_claim | phone | api
    booked_via      TEXT NOT NULL DEFAULT 'online_portal',
    
    FOREIGN KEY (timeblock_id) REFERENCES timeblocks(id),
    FOREIGN KEY (owner_id) REFERENCES owners(id),
    FOREIGN KEY (clinic_id) REFERENCES clinics(id)
);

CREATE INDEX IF NOT EXISTS idx_bt_timeblock_id ON booking_tokens(timeblock_id);
CREATE INDEX IF NOT EXISTS idx_bt_owner_id     ON booking_tokens(owner_id);
-- Partial index for expiry sweeps (active tokens only)
CREATE INDEX IF NOT EXISTS idx_bt_expires_at   ON booking_tokens(expires_at, status);
```

**Notes:**
- `expires_at` is set to `appointment_start_datetime + 30 days`, not creation time. This gives owners access to the status page and their intake responses for the full post-visit period.
- When `status = 'cancelled'` or `status = 'expired'`, all write actions (cancel, reschedule, intake submit) return 409.

---

### 2.4 `intake_tokens`

One-time delivery token for the pre-visit intake form. Created atomically with `booking_tokens`. Sent to owner via email (and SMS if MOD-COM licensed).

```sql
CREATE TABLE IF NOT EXISTS intake_tokens (
    id                  TEXT PRIMARY KEY,         -- UUID v4; appears in intake URL
    booking_token_id    TEXT NOT NULL,            -- FK → booking_tokens.id
    clinic_id           TEXT NOT NULL,            -- FK → clinics.id
    patient_id          TEXT NOT NULL,            -- FK → patients.id
    -- Determines which question set to load (wellness|sick|vaccines|dental|followup|other)
    appointment_type_id TEXT NOT NULL,
    
    -- Lifecycle
    -- pending: created; sent: delivery dispatched; in_progress: owner started;
    -- complete: all required questions answered; expired: TTL passed; skipped: owner opted out
    status              TEXT NOT NULL DEFAULT 'pending'
                        CHECK (status IN (
                            'pending', 'sent', 'in_progress', 'complete', 'expired', 'skipped'
                        )),
    -- 7 days from booking confirmation (design doc §13.2)
    expires_at          TEXT NOT NULL,
    sent_at             TEXT,                     -- when delivery was dispatched
    completed_at        TEXT,
    
    -- Delivery tracking
    -- sms | email | both
    delivery_method     TEXT DEFAULT 'email'
                        CHECK (delivery_method IN ('sms', 'email', 'both')),
    sms_sent_to         TEXT,                     -- E.164 phone used for SMS delivery
    email_sent_to       TEXT,                     -- email address used
    
    -- Structured responses and flags (JSON)
    -- responses: [{question_id, answer, answered_at}, ...]
    responses           TEXT NOT NULL DEFAULT '[]',
    -- flags set by intake_delivery_agent: {flag_name: true/false, ...}
    flags               TEXT NOT NULL DEFAULT '{}',
    
    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL,
    
    FOREIGN KEY (booking_token_id) REFERENCES booking_tokens(id) ON DELETE CASCADE,
    FOREIGN KEY (clinic_id) REFERENCES clinics(id),
    FOREIGN KEY (patient_id) REFERENCES patients(id)
);

CREATE INDEX IF NOT EXISTS idx_it_booking_token_id ON intake_tokens(booking_token_id);
CREATE INDEX IF NOT EXISTS idx_it_status           ON intake_tokens(status);
CREATE INDEX IF NOT EXISTS idx_it_expires_at       ON intake_tokens(expires_at, status);
```

**Notes:**
- **One-time submit:** After `status = 'complete'`, `POST /public/intake/{token}/submit` returns 409. GET remains available.
- If the owner requests a resend, the existing token is re-dispatched (no new token created). This prevents token proliferation.
- `responses` and `flags` are JSON blobs. In Phase 1, SQLite TEXT is used. In a future Postgres migration, these become JSONB with column-level encryption for `responses` (HIPAA §13.4).

---

### 2.5 `intake_responses`

Individual answer rows. These are stored both inline in `intake_tokens.responses` (JSON blob, for simplicity) and as discrete rows here (for queryability). Both are written atomically on submit.

```sql
CREATE TABLE IF NOT EXISTS intake_responses (
    id              TEXT PRIMARY KEY,     -- UUID v4
    intake_token_id TEXT NOT NULL,        -- FK → intake_tokens.id
    question_id     TEXT NOT NULL,        -- e.g. "q_appetite", "q_water"
    question_text   TEXT NOT NULL,        -- Denormalized for audit trail
    answer          TEXT NOT NULL,        -- Owner's answer (free text or choice label)
    answered_at     TEXT NOT NULL,        -- ISO datetime
    skipped         INTEGER DEFAULT 0,   -- 1 if owner clicked "Skip"
    
    FOREIGN KEY (intake_token_id) REFERENCES intake_tokens(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_ir_intake_token_id ON intake_responses(intake_token_id);
```

---

### 2.6 `slot_holds`

Soft-hold table. Prevents two concurrent sessions from booking the same slot. 10-minute TTL; expired holds are cleaned up by a background task.

```sql
CREATE TABLE IF NOT EXISTS slot_holds (
    id                  TEXT PRIMARY KEY,     -- UUID v4
    clinic_id           TEXT NOT NULL,        -- FK → clinics.id
    resource_id         TEXT NOT NULL,        -- FK → resources.id (the vet)
    -- ISO datetime of proposed appointment start
    start_datetime      TEXT NOT NULL,
    -- ISO datetime of proposed appointment end
    end_datetime        TEXT NOT NULL,
    owner_session_id    TEXT NOT NULL,        -- FK → owner_sessions.id
    held_at             TEXT NOT NULL,
    expires_at          TEXT NOT NULL,        -- held_at + 10 minutes
    
    -- Uniqueness: one hold per (clinic, vet, start_time) — first POST wins
    UNIQUE (clinic_id, resource_id, start_datetime),
    
    FOREIGN KEY (clinic_id) REFERENCES clinics(id),
    FOREIGN KEY (resource_id) REFERENCES resources(id),
    FOREIGN KEY (owner_session_id) REFERENCES owner_sessions(id)
);

CREATE INDEX IF NOT EXISTS idx_sh_expires ON slot_holds(expires_at);
-- Cleanup query (run every 5 min via FastAPI background task):
-- DELETE FROM slot_holds WHERE expires_at < datetime('now')
```

---

### 2.7 `waitlist_entries`

**Status check:** The existing `waitlist` table in `repository.py` exists with columns: `id, patient_id, clinic_id, procedure_type, preferred_vet_id, urgency, offer_status, join_date`. Phase 1 requires additional columns. The implementation adds these columns via `ALTER TABLE` (try/except pattern) and a rename of semantic fields. The table is NOT dropped and recreated — additive migration only.

The **full target schema** for the `waitlist` table after Phase 1 migrations:

```sql
-- Original columns (already exist, do not re-create):
-- id TEXT PRIMARY KEY
-- patient_id TEXT NOT NULL
-- clinic_id TEXT NOT NULL
-- procedure_type TEXT NOT NULL        (maps to appointment_type_id intent)
-- preferred_vet_id TEXT
-- urgency TEXT DEFAULT 'flexible'
-- offer_status TEXT DEFAULT 'waiting'
-- join_date TEXT NOT NULL

-- Phase 1 additions via ALTER TABLE (wrapped in try/except):
ALTER TABLE waitlist ADD COLUMN owner_id TEXT;
-- time_preferences: JSON array of strings e.g. ["weekday_morning", "weekday_afternoon"]
ALTER TABLE waitlist ADD COLUMN time_preferences TEXT NOT NULL DEFAULT '[]';
-- min_notice_hours: don't notify if slot is < X hours away
ALTER TABLE waitlist ADD COLUMN min_notice_hours INTEGER NOT NULL DEFAULT 3;
-- active: false when slot claimed or owner manually removed
ALTER TABLE waitlist ADD COLUMN active INTEGER NOT NULL DEFAULT 1;
-- pass_count: # of times owner skipped a notified slot
ALTER TABLE waitlist ADD COLUMN pass_count INTEGER NOT NULL DEFAULT 0;
-- flexibility_score: computed 0.0-1.0; wider time window = higher score
ALTER TABLE waitlist ADD COLUMN flexibility_score REAL NOT NULL DEFAULT 0.5;
ALTER TABLE waitlist ADD COLUMN phone_for_sms TEXT NOT NULL DEFAULT '';
ALTER TABLE waitlist ADD COLUMN sms_consent INTEGER NOT NULL DEFAULT 0;
ALTER TABLE waitlist ADD COLUMN last_notified_at TEXT;
ALTER TABLE waitlist ADD COLUMN removed_at TEXT;
-- remove_reason: accepted | passed_3x | manual | expired
ALTER TABLE waitlist ADD COLUMN remove_reason TEXT;
```

**New indexes to add:**
```sql
CREATE INDEX IF NOT EXISTS idx_waitlist_active
    ON waitlist(clinic_id, procedure_type, active);
CREATE INDEX IF NOT EXISTS idx_waitlist_urgency
    ON waitlist(urgency, join_date);
```

**`flexibility_score` computation logic** (run at join time, in `booking_agent.py`):
```python
def compute_flexibility_score(time_preferences: list[str]) -> float:
    """
    More time windows = higher score = easier to fill = higher priority in queue.
    Full flexibility (any time) → 1.0; single narrow window → 0.25.
    """
    all_windows = {"weekday_morning", "weekday_afternoon", "saturday_morning", "any"}
    if "any" in time_preferences:
        return 1.0
    return max(0.25, len(set(time_preferences) & all_windows) / len(all_windows))
```

---

## 3. Modified Existing Tables

All modifications use the `ALTER TABLE ... ADD COLUMN` pattern in `_init_db()` wrapped in try/except. This matches the existing pattern in `repository.py`.

### 3.1 `clinics` table — add `slug`

```sql
-- Add URL-safe human-readable clinic identifier
-- e.g. "meadow-pet-clinic" from clinic name "Meadow Pet Clinic"
ALTER TABLE clinics ADD COLUMN slug TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS idx_clinics_slug ON clinics(slug);
```

**Slug generation rule:** `slug = re.sub(r'[^a-z0-9]+', '-', clinic.name.lower()).strip('-')`. If collision, append `-2`, `-3`, etc. Slugs are set by staff at clinic creation/edit time; they cannot be changed without updating all existing booking URLs.

### 3.2 `timeblocks` table — add online booking columns

```sql
-- Source of the booking (for analytics; online bookings show 🌐 badge on scheduling board)
ALTER TABLE timeblocks ADD COLUMN source TEXT DEFAULT 'staff_dashboard';
-- CHECK: source IN ('staff_dashboard', 'online_portal', 'waitlist_claim', 'phone', 'api')

-- Clinical urgency as stated by owner at booking
ALTER TABLE timeblocks ADD COLUMN urgency TEXT DEFAULT 'routine';
-- CHECK: urgency IN ('wellness', 'routine', 'urgent', 'emergency')

-- Free-text notes from owner at booking (Step 3, 300 char max)
ALTER TABLE timeblocks ADD COLUMN client_notes TEXT;

-- Appointment type from bookable_appointment_types (e.g. "wellness", "sick")
ALTER TABLE timeblocks ADD COLUMN appointment_type_id TEXT;

-- FK to intake token for this appointment; populated on booking confirmation
ALTER TABLE timeblocks ADD COLUMN intake_token_id TEXT;

-- Numeric risk score from risk.py (0.0-1.0); populated post-intake in Phase 2
ALTER TABLE timeblocks ADD COLUMN risk_score REAL;
```

### 3.3 `owners` table — add portal-specific columns

```sql
-- Preferred vet resource UUID (used for slot ranking in Phase 2)
ALTER TABLE owners ADD COLUMN preferred_resource_id TEXT;

-- SMS opt-in consent captured at booking
ALTER TABLE owners ADD COLUMN sms_consent INTEGER DEFAULT 0;

-- Portal-specific fields
ALTER TABLE owners ADD COLUMN portal_opt_in INTEGER DEFAULT 0;
ALTER TABLE owners ADD COLUMN last_portal_login TEXT;

-- Counters for risk model
ALTER TABLE owners ADD COLUMN no_show_count INTEGER DEFAULT 0;
ALTER TABLE owners ADD COLUMN booking_count INTEGER DEFAULT 0;

-- Split existing `name` column into first/last for public display
-- NOTE: existing data has `name` as single field; new registrations split at creation.
-- Phase 1: store as JSON in a new column; do not alter existing `name` column.
ALTER TABLE owners ADD COLUMN first_name TEXT DEFAULT '';
ALTER TABLE owners ADD COLUMN last_name TEXT DEFAULT '';
ALTER TABLE owners ADD COLUMN email TEXT DEFAULT '';
-- NOTE: existing owners.email and owners.phone remain; these add null-safety defaults
```

**Implementation note:** The existing `owners` table has a single `name` TEXT column. For new clients registered via `POST /public/owners/register`, populate `first_name`, `last_name`, AND `name` (as `first_name + " " + last_name`) for backward compatibility with existing staff-side code that reads `owners.name`.

---

## 4. New API Routes

All public routes are prefixed `/public/`. They require **no staff JWT** auth header. Staff admin routes use the existing `/api/` prefix and require staff auth (same as all existing `/api/` routes).

Rate limiting is enforced at the FastAPI middleware layer using an in-process dictionary counter (Phase 1: no Redis dependency; acceptable for single-process deployment). Rate limit state is per IP address, tracked by `request.client.host`.

**CORS policy for `/public/*` routes:** Allow all origins (`*`) for GET requests; restrict POST/PUT to configured clinic domains + `book.vpma.app` domain (set `allow_origins` in middleware config per environment).

---

### Route 1: `GET /public/clinics/{clinic_slug}`

```
### GET /public/clinics/{clinic_slug}
Auth:       None (fully public)
Rate Limit: 60 requests per minute per IP
Purpose:    Fetch clinic metadata and booking configuration for portal landing page rendering.
```

**Path Parameters:**
- `clinic_slug` (string, required): URL-safe clinic identifier (e.g., `meadow-pet-clinic`)

**Response (200):**
```json
{
  "clinic_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "name": "Meadow Pet Clinic",
  "slug": "meadow-pet-clinic",
  "address": "45 Meadow Lane, Suite 200, Springfield, IL 62701",
  "phone": "(555) 123-4567",
  "email": "hello@meadowpetclinic.com",
  "timezone": "America/Chicago",
  "color_hex": "#2E7D52",
  "booking_config": {
    "online_booking_enabled": true,
    "advance_booking_days": 30,
    "same_day_cutoff_hour": 14,
    "same_day_booking_enabled": true,
    "emergency_phone": "(555) 911-0000",
    "emergency_message": "",
    "cancellation_policy": "Cancellations must be made at least 24 hours in advance.",
    "auto_confirm": true,
    "require_deposit": false,
    "show_vet_names": true,
    "brand_color_primary": "#2E7D52",
    "brand_color_accent": "#F0A500"
  }
}
```

**Error Responses:**
- `404`: `{"detail": "Clinic not found"}` — `clinic_slug` does not match any `clinics.slug`
- `429`: `{"detail": "Rate limit exceeded", "retry_after": 60}`

**Backend Logic:**
1. Query: `SELECT clinics.*, clinic_booking_config.* FROM clinics LEFT JOIN clinic_booking_config ON clinics.id = clinic_booking_config.clinic_id WHERE clinics.slug = ?`
2. If no row: return 404.
3. If `clinic_booking_config` row is NULL (config never created): return response with `booking_config.online_booking_enabled = false` and all other config fields at defaults.
4. Do **not** include `bookable_appointment_types`, `hidden_resource_ids`, or messaging templates in this response — those are returned by the appointment-types endpoint.
5. Log to verbose log: `{"action": "clinic_landing_viewed", "clinic_id": ..., "ip": ..., "result": "found"}`

---

### Route 2: `GET /public/clinics/{clinic_slug}/appointment-types`

```
### GET /public/clinics/{clinic_slug}/appointment-types
Auth:       None
Rate Limit: 30 requests per minute per IP
Purpose:    Return the list of appointment types enabled for online booking at this clinic.
```

**Response (200):**
```json
{
  "clinic_id": "a1b2c3d4-...",
  "appointment_types": [
    {
      "id": "wellness",
      "name": "Annual Wellness Exam",
      "duration_minutes": 45,
      "intake_question_set": "wellness",
      "description": "",
      "breed_duration_overrides": {}
    },
    {
      "id": "sick",
      "name": "Sick Visit",
      "duration_minutes": 30,
      "intake_question_set": "sick",
      "description": "",
      "breed_duration_overrides": {}
    }
  ]
}
```

**Error Responses:**
- `404`: Clinic not found
- `403`: `{"detail": "Online booking is disabled for this clinic"}` — when `online_booking_enabled = 0`

**Backend Logic:**
1. Fetch clinic by slug; 404 if not found.
2. Fetch `clinic_booking_config` for this clinic.
3. If `online_booking_enabled = 0`: return 403 with message.
4. Parse `clinic_booking_config.bookable_appointment_types` JSON; filter to items where `enabled = true`.
5. Return filtered list. If `bookable_appointment_types` is empty `[]`, return empty list (not 404).

---

### Route 3: `GET /public/clinics/{clinic_slug}/availability`

```
### GET /public/clinics/{clinic_slug}/availability
Auth:       None (slot list); session cookie extends slot detail in Phase 2
Rate Limit: 30 requests per minute per IP
Purpose:    Return available appointment slots for a given appointment type.
            Phase 1: chronological order only. Phase 2 adds AI ranking.
```

**Query Parameters:**
- `appointment_type_id` (string, required): e.g., `"wellness"`
- `days` (integer, optional, default 14, max 60): look-ahead window in days
- `patient_id` (string, optional): enables vet-continuity pre-filtering in Phase 2; ignored in Phase 1
- `urgency` (string, optional, default `"routine"`): `"routine"` | `"urgent"`; if `"urgent"`, today's slots shown first regardless of same-day cutoff

**Response (200):**
```json
{
  "slots": [
    {
      "slot_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
      "resource_id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
      "vet_name": "Dr. Emily Chen",
      "vet_display_name": "Dr. Chen",
      "start_datetime": "2026-06-26T10:30:00",
      "end_datetime": "2026-06-26T11:15:00",
      "duration_minutes": 45,
      "rank": 1,
      "rank_label": "Soonest Available",
      "rank_explanation": "Next available slot for this appointment type.",
      "no_show_risk_label": null
    }
  ],
  "total_available": 12,
  "showing_top": 10,
  "has_more": true,
  "waitlist_available": true
}
```

**Error Responses:**
- `404`: Clinic not found, or `appointment_type_id` not in bookable types
- `400`: `{"detail": "appointment_type_id is required"}`
- `429`: Rate limit exceeded

**Backend Logic:**
1. Fetch clinic and config; validate `appointment_type_id` is in `bookable_appointment_types`.
2. Resolve slot duration: look up duration from matching entry in `bookable_appointment_types`.
3. Compute search window: `start = now + min_booking_notice_hours`; `end = now + advance_booking_days * 24h`.
4. If `same_day_booking_enabled = 0` or current local hour ≥ `same_day_cutoff_hour`: set `start = tomorrow 00:00:00 local`.
5. Fetch all vets assigned to this clinic: `SELECT r.id, r.name FROM resources r JOIN vet_clinic_assignments vca ON r.id = vca.vet_id WHERE vca.clinic_id = ? AND r.type = 'Vet'`.
6. Exclude vets in `clinic_booking_config.hidden_resource_ids`.
7. For each vet, fetch existing `timeblocks` in the search window where `status NOT IN ('cancelled', 'no_show')`: these are occupied slots.
8. Also fetch active `slot_holds` in window (non-expired): these are temporarily unavailable.
9. Compute free slots: for each vet, each day in window, each possible start time at 30-min increments between `vet.availability_windows` start/end — check if the `[start, start+duration]` interval overlaps any occupied timeblock or active hold, and whether `≥ buffer_minutes` clearance exists before and after.
10. Collect all free slots from all vets; sort ascending by `start_datetime`.
11. In Phase 1: assign `rank` sequentially (1, 2, 3…), `rank_label = "Soonest Available"`, `rank_explanation` = static string.
12. Return first 10 slots; set `has_more = total > 10`.
13. Set `waitlist_available = (clinic_booking_config.waitlist_enabled == 1)`.

**Slot ID generation:** `slot_id = str(uuid5(NAMESPACE_URL, f"{resource_id}:{start_datetime}"))` — deterministic from (vet, time) pair, so the same slot always gets the same ID within a request cycle. This ID is only valid for the duration of the hold; it is NOT a PK in any table.

---

### Route 4: `POST /public/owners/lookup`

```
### POST /public/owners/lookup
Auth:       None
Rate Limit: 10 requests per 5 minutes per IP
Purpose:    Look up a returning owner by phone or email. Creates an owner session on success.
```

**Request:**
```json
{
  "clinic_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "phone": "5551234567",
  "email": "marcus@example.com"
}
```

**Validation:**
- At least one of `phone` or `email` must be non-empty; both empty → 400 `{"detail": "Provide phone or email"}`
- Phone: strip all non-digit characters; must be 10 or 11 digits after stripping → else 400 `{"detail": "Invalid phone format"}`
- Email: basic `@` and `.` presence check → else 400 `{"detail": "Invalid email format"}`
- `clinic_id`: must exist in `clinics` table → else 404

**Response (200, found):**
```json
{
  "found": true,
  "owner_id": "d4e5f6a7-b8c9-0123-defa-234567890123",
  "display_name": "Marcus",
  "pets": [
    {
      "id": "e5f6a7b8-c9d0-1234-efab-345678901234",
      "name": "Mochi",
      "species": "cat",
      "breed": "Domestic Shorthair",
      "age_years": 4,
      "last_visit_label": "14 months ago",
      "care_due": false,
      "care_due_reason": null
    }
  ]
}
```

**Response (200, not found):**
```json
{
  "found": false
}
```

**Response headers on found:**
```
Set-Cookie: vpma_session=<session_token>; HttpOnly; Secure; SameSite=Strict; Max-Age=1800; Path=/
```

**Error Responses:**
- `400`: Validation failure (see above)
- `404`: `clinic_id` not found
- `429`: Rate limit; include `Retry-After: 300` header

**Backend Logic:**
1. Normalize phone to 10-digit string (strip non-digits, strip leading `1` if 11 digits).
2. Query owners: `SELECT id, first_name, last_name, name FROM owners WHERE (phone = ? OR email = ?) AND home_clinic_id = ? AND portal_opt_in = 1`. If no results, fall back without `portal_opt_in` filter for newly migrated clinics (configurable flag).
3. If 0 results: return `{"found": false}`. Do NOT create a session.
4. If ≥ 1 result: use first match. If multiple matches (same phone, multiple owners), return all as array in `pets` flattened — the response always presents one identity. **Do not** return last name, address, DOB, or any medical records at this step.
5. Fetch non-deceased patients for owner: `SELECT id, name, species, breed, dob FROM patients WHERE owner_id = ? AND status != 'deceased'`.
6. Compute `age_years` from `dob` (if available, else null).
7. Compute `last_visit_label`: `SELECT MAX(start_time) FROM timeblocks WHERE patient_id = ? AND status = 'complete'`; format as relative string (e.g., "14 months ago", "2 weeks ago").
8. `care_due`: Phase 1 — always `false`. (Phase 2 wires care protocol check.)
9. Create `owner_sessions` row: `id=uuid4(), owner_id=owner.id, clinic_id=clinic_id, ip_address=request.client.host, user_agent=request.headers.get("user-agent"), flow_state="{}", expires_at=now+30min, last_active_at=now, created_at=now`.
10. Set `Set-Cookie` header with session token (= `owner_sessions.id`).
11. Log: `{"action": "owner_lookup", "result": "found", "clinic_id": ..., "owner_id": ...}`

---

### Route 5: `POST /public/owners/register`

```
### POST /public/owners/register
Auth:       None
Rate Limit: 5 requests per 5 minutes per IP
Purpose:    Create a new owner record and first patient record. Used for new clients.
```

**Request:**
```json
{
  "clinic_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "first_name": "Sarah",
  "last_name": "Johnson",
  "phone": "5559876543",
  "email": "sarah@example.com",
  "sms_consent": true,
  "pet": {
    "name": "Biscuit",
    "species": "dog",
    "breed": "Beagle",
    "dob_approx": "2023-01-01",
    "sex": "male",
    "neutered": true
  }
}
```

**Validation:**
- `first_name`: required, 1–100 chars, strip whitespace
- `last_name`: required, 1–100 chars, strip whitespace
- `phone`: required, same normalization as lookup; must be valid 10/11-digit US number
- `email`: required, must contain `@` and domain with `.`
- `pet.name`: required, 1–100 chars
- `pet.species`: required; must be one of `["dog", "cat", "bird", "rabbit", "reptile", "other"]`
- `pet.breed`: optional; empty string allowed
- `pet.dob_approx`: optional; if provided, must parse as ISO date `YYYY-MM-DD`; reject future dates

**Duplicate prevention:**
- Before creating, check: `SELECT id FROM owners WHERE (phone = ? OR email = ?) AND home_clinic_id = ?`.
- If found: return 409 `{"detail": "An account with this phone/email already exists. Please use the returning client flow.", "owner_id": "<existing_id>"}`.

**Response (201):**
```json
{
  "owner_id": "f6a7b8c9-d0e1-2345-fabc-456789012345",
  "patient_id": "a7b8c9d0-e1f2-3456-abcd-567890123456",
  "session_established": true
}
```

**Response headers:**
```
Set-Cookie: vpma_session=<session_token>; HttpOnly; Secure; SameSite=Strict; Max-Age=1800; Path=/
```

**Error Responses:**
- `400`: Validation failure
- `409`: Duplicate owner (see above)
- `429`: Rate limit

**Backend Logic:**
1. Normalize and validate all fields.
2. Duplicate check as above.
3. Create owner: `INSERT INTO owners (id, name, first_name, last_name, phone, email, patient_ids, sms_consent, portal_opt_in, home_clinic_id, booking_count, created_at) VALUES (...)`. Set `name = first_name + " " + last_name` for backward compatibility.
4. Create patient: `INSERT INTO patients (id, name, species, breed, dob, weight_kg, owner_id, home_clinic_id, visit_count, flags, flag_notes) VALUES (...)`. Set `weight_kg = 0.0` (unknown until visit), `dob = dob_approx or ""`, `flags = "[]"`.
5. Update `owners.patient_ids` JSON array to include new patient ID.
6. Create `owner_sessions` row (same as lookup flow).
7. Set `Set-Cookie` header.
8. Log: `{"action": "owner_registered", "clinic_id": ..., "owner_id": ..., "patient_id": ...}`

---

### Route 6: `GET /public/owners/{owner_id}/pets`

```
### GET /public/owners/{owner_id}/pets
Auth:       owner_sessions cookie (required; session must have owner_id matching path param)
Rate Limit: 60 requests per minute per IP
Purpose:    Return the list of live (non-deceased) pets for the session-authenticated owner.
```

**Session validation:**
1. Read `vpma_session` cookie; look up in `owner_sessions`.
2. If not found, expired (`expires_at < now`), or `owner_sessions.owner_id != path owner_id`: return 401 `{"detail": "Session invalid or expired"}`.
3. Extend session: `UPDATE owner_sessions SET last_active_at = now, expires_at = now + 30min WHERE id = ?`.

**Response (200):**
```json
{
  "owner_id": "d4e5f6a7-b8c9-0123-defa-234567890123",
  "display_name": "Marcus",
  "pets": [
    {
      "id": "e5f6a7b8-c9d0-1234-efab-345678901234",
      "name": "Mochi",
      "species": "cat",
      "breed": "Domestic Shorthair",
      "age_years": 4,
      "last_visit_label": "14 months ago",
      "care_due": false,
      "care_due_reason": null
    }
  ]
}
```

**Error Responses:**
- `401`: Session invalid, expired, or owner mismatch
- `404`: `owner_id` not found in owners table

**Backend Logic:**
1. Validate session (see above).
2. `SELECT id, name, species, breed, dob, last_visit_date FROM patients WHERE owner_id = ? AND (status IS NULL OR status != 'deceased')`.
3. Return enriched pet list (same as lookup response).

---

### Route 7: `POST /public/bookings/hold`

```
### POST /public/bookings/hold
Auth:       owner_sessions cookie (required)
Rate Limit: 20 requests per minute per session
Purpose:    Create a soft-hold on a slot. Reserves the slot for 10 minutes to prevent
            concurrent bookings. Must be called before POST /public/bookings.
```

**Request:**
```json
{
  "clinic_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "resource_id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
  "start_datetime": "2026-06-26T10:30:00",
  "end_datetime": "2026-06-26T11:15:00",
  "appointment_type_id": "wellness",
  "patient_id": "e5f6a7b8-c9d0-1234-efab-345678901234"
}
```

**Validation:**
- Session valid and active (401 if not).
- `resource_id` must exist in `resources` and belong to `clinic_id`.
- `start_datetime` must be in the future by at least `min_booking_notice_hours`.
- `start_datetime` must be within `advance_booking_days` window.
- `appointment_type_id` must be in `bookable_appointment_types` for this clinic.

**Response (200):**
```json
{
  "hold_id": "b8c9d0e1-f2a3-4567-bcde-678901234567",
  "slot_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "expires_at": "2026-06-26T10:40:00",
  "resource_id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
  "vet_name": "Dr. Emily Chen",
  "start_datetime": "2026-06-26T10:30:00",
  "end_datetime": "2026-06-26T11:15:00"
}
```

**Error Responses:**
- `401`: Session invalid
- `409`: `{"detail": "Slot already held or booked"}` — UNIQUE constraint on `(clinic_id, resource_id, start_datetime)` violated
- `400`: Validation failure
- `429`: Rate limit

**Backend Logic:**
1. Validate session; resolve `owner_session_id`.
2. Expire any previously active hold for this session (DELETE from `slot_holds` WHERE `owner_session_id = ?`). Owner can only hold one slot at a time.
3. Clean up globally expired holds: `DELETE FROM slot_holds WHERE expires_at < datetime('now')`.
4. Verify slot is still free: check `timeblocks` and active `slot_holds` for overlap with `[start_datetime, end_datetime]` for this `resource_id`.
5. Attempt INSERT into `slot_holds`. If UNIQUE constraint fails: return 409.
6. Update `owner_sessions.flow_state` with `{"selected_slot_id": slot_id, "selected_appt_type_id": appointment_type_id, "selected_patient_id": patient_id}`.
7. Log: `{"action": "slot_held", "resource_id": ..., "start_datetime": ..., "hold_expires_at": ...}`

---

### Route 8: `POST /public/bookings`

```
### POST /public/bookings
Auth:       owner_sessions cookie (required)
Rate Limit: 5 requests per hour per session
Purpose:    Confirm a booking. Atomically converts the soft-hold to a confirmed timeblock,
            creates booking_token and intake_token, arms the reminder pipeline, and
            triggers intake form delivery asynchronously.
```

**Request:**
```json
{
  "hold_id": "b8c9d0e1-f2a3-4567-bcde-678901234567",
  "patient_id": "e5f6a7b8-c9d0-1234-efab-345678901234",
  "appointment_type_id": "wellness",
  "urgency": "routine",
  "notes": "Mochi has been scratching her ears more than usual",
  "sms_consent": true,
  "cancellation_policy_accepted": true
}
```

**Validation:**
- Session valid (401).
- `hold_id` must exist in `slot_holds`, belong to this session, and not be expired.
- `cancellation_policy_accepted` must be `true`; else 400 `{"detail": "Must accept cancellation policy"}`.
- `urgency` must be one of `["wellness", "routine", "urgent", "emergency"]`.
- `notes`: if provided, max 300 chars; trim silently if exceeded.

**Response (201):**
```json
{
  "booking_id": "c9d0e1f2-a3b4-5678-cdef-789012345678",
  "booking_token": "d0e1f2a3-b4c5-6789-defa-890123456789",
  "status": "booked",
  "status_url": "https://book.vpma.app/status/d0e1f2a3-b4c5-6789-defa-890123456789",
  "intake_url": "https://book.vpma.app/intake/e1f2a3b4-c5d6-7890-efab-901234567890",
  "appointment": {
    "date": "2026-06-26",
    "time": "10:30",
    "duration_minutes": 45,
    "vet_name": "Dr. Emily Chen",
    "clinic_name": "Meadow Pet Clinic",
    "address": "45 Meadow Lane, Suite 200, Springfield, IL 62701"
  }
}
```

**Error Responses:**
- `401`: Session invalid
- `404`: `hold_id` not found
- `409`: Hold expired or slot double-booked (race condition)
- `400`: Validation failure

**Backend Logic (atomic SQLite transaction):**

```python
# All steps run inside a single BEGIN...COMMIT block.
# On any error, ROLLBACK and return 409.

# Step 1: Re-validate hold
hold = SELECT * FROM slot_holds WHERE id = ? AND owner_session_id = ? AND expires_at > now()
if not hold: return 409

# Step 2: Final availability check (second check in case hold expired between validation and write)
conflict = SELECT id FROM timeblocks WHERE resource_ids LIKE '%<resource_id>%'
           AND start_time < end_datetime AND end_time > start_datetime
           AND status NOT IN ('cancelled', 'no_show')
if conflict: return 409

# Step 3: Create timeblock (the actual appointment record)
timeblock_id = uuid4()
INSERT INTO timeblocks (
    id, job_id, resource_ids, start_time, end_time,
    patient_id, intake_status, status, clinic_id,
    source, urgency, client_notes, appointment_type_id
) VALUES (
    timeblock_id,
    uuid4(),                          -- job_id (stub job for online bookings)
    json([resource_id]),
    start_datetime,
    end_datetime,
    patient_id,
    'not_started',                    -- intake_status; updated to 'pending' when intake fired
    'scheduled',
    clinic_id,
    'online_portal',
    urgency,
    notes[:300],
    appointment_type_id
)

# Step 4: Create booking token
booking_token_id = uuid4()
expires_at = appointment_datetime + timedelta(days=30)
INSERT INTO booking_tokens (
    id, timeblock_id, owner_id, clinic_id,
    status, lifecycle_state, expires_at, booked_via,
    created_at, updated_at
) VALUES (booking_token_id, timeblock_id, owner_id, clinic_id,
          'active', 'booked', expires_at, 'online_portal', now, now)

# Step 5: Create intake token
intake_token_id = uuid4()
intake_expires_at = now + timedelta(days=7)
INSERT INTO intake_tokens (
    id, booking_token_id, clinic_id, patient_id,
    appointment_type_id, status, expires_at,
    delivery_method, responses, flags,
    created_at, updated_at
) VALUES (intake_token_id, booking_token_id, clinic_id, patient_id,
          appointment_type_id, 'pending', intake_expires_at,
          'email', '[]', '{}', now, now)

# Step 6: Link intake token to timeblock
UPDATE timeblocks SET intake_token_id = intake_token_id WHERE id = timeblock_id

# Step 7: Update owner session
UPDATE owner_sessions SET booking_token_id = booking_token_id WHERE id = session_id

# Step 8: Delete soft-hold
DELETE FROM slot_holds WHERE id = hold_id

# Step 9: Update owner booking count
UPDATE owners SET booking_count = booking_count + 1 WHERE id = owner_id

COMMIT
```

**Post-commit async tasks (use FastAPI `BackgroundTasks`, non-blocking):**
1. Call `intake_delivery_agent.schedule_delivery(intake_token_id, appointment_datetime)` — computes send delay and queues email/SMS.
2. Call `booking_agent.arm_reminders(timeblock_id, booking_token_id, owner_id, appointment_datetime)` — arms T-48h and T-2h reminders via existing `ReminderAgent`.
3. Log: `{"action": "booking_confirmed", "timeblock_id": ..., "booking_token": ..., "clinic_id": ..., "owner_id": ..., "patient_id": ...}`

---

### Route 9: `GET /public/status/{booking_token}`

```
### GET /public/status/{booking_token}
Auth:       Token (booking_token IS the auth — no cookie required)
Rate Limit: 60 requests per minute per IP
Purpose:    Fetch appointment status for the public status tracker page.
            Phase 1: static snapshot; client polls every 60 seconds.
```

**Path Parameters:**
- `booking_token` (string, required): UUID v4 booking token

**Response (200):**
```json
{
  "booking_id": "c9d0e1f2-a3b4-5678-cdef-789012345678",
  "booking_token": "d0e1f2a3-b4c5-6789-defa-890123456789",
  "status": "intake_sent",
  "clinic_name": "Meadow Pet Clinic",
  "clinic_phone": "(555) 123-4567",
  "clinic_address": "45 Meadow Lane, Suite 200, Springfield, IL 62701",
  "pet_name": "Mochi",
  "owner_display_name": "Marcus",
  "appointment_type": "Annual Wellness Exam",
  "vet_name": "Dr. Emily Chen",
  "start_datetime": "2026-06-26T10:30:00",
  "duration_minutes": 45,
  "lifecycle": [
    {"state": "booked",           "label": "Appointment Confirmed",    "completed": true,  "completed_at": "2026-06-19T20:23:00"},
    {"state": "intake_sent",      "label": "Pre-Visit Form Sent",      "completed": true,  "completed_at": "2026-06-19T20:24:00"},
    {"state": "intake_complete",  "label": "Pre-Visit Form Complete",  "completed": false, "completed_at": null},
    {"state": "confirmed",        "label": "Appointment Confirmed",    "completed": false, "completed_at": null},
    {"state": "in_progress",      "label": "In Progress",              "completed": false, "completed_at": null},
    {"state": "complete",         "label": "Visit Complete",           "completed": false, "completed_at": null},
    {"state": "follow_up_sent",   "label": "Follow-Up Sent",          "completed": false, "completed_at": null}
  ],
  "intake_token": "e1f2a3b4-c5d6-7890-efab-901234567890",
  "intake_status": "sent",
  "intake_url": "https://book.vpma.app/intake/e1f2a3b4-c5d6-7890-efab-901234567890",
  "cancellable": true,
  "reschedulable": false,
  "calendar_url": "/public/status/d0e1f2a3-b4c5-6789-defa-890123456789/calendar.ics"
}
```

**Error Responses:**
- `404`: Booking token not found in `booking_tokens` table
- `410`: `{"detail": "This booking has been cancelled"}` — `booking_tokens.status = 'cancelled'`
- `410`: `{"detail": "This booking link has expired"}` — `booking_tokens.expires_at < now`

**Backend Logic:**
1. Query: `SELECT bt.*, t.start_time, t.end_time, t.status as appt_status, t.appointment_type_id, p.name as pet_name, o.first_name as owner_first_name, r.name as vet_name, c.name as clinic_name, c.address as clinic_address, c.phone as clinic_phone, it.id as intake_token_id, it.status as intake_status FROM booking_tokens bt JOIN timeblocks t ON bt.timeblock_id = t.id JOIN patients p ON t.patient_id = p.id JOIN owners o ON bt.owner_id = o.id LEFT JOIN resources r ON json_extract(t.resource_ids, '$[0]') = r.id JOIN clinics c ON bt.clinic_id = c.id LEFT JOIN intake_tokens it ON t.intake_token_id = it.id WHERE bt.id = ?`
2. If not found: 404.
3. If `bt.status = 'cancelled'`: 410 with cancelled message.
4. If `bt.expires_at < now`: 410 with expired message.
5. `cancellable = (bt.status = 'active' AND t.start_time > now)`.
6. `reschedulable = false` in Phase 1 (Phase 2 feature).
7. Build `lifecycle` array: map `bt.lifecycle_state` to completed states.

---

### Route 10: `GET /public/intake/{intake_token}`

```
### GET /public/intake/{intake_token}
Auth:       Token (intake_token IS the auth)
Rate Limit: 60 requests per minute per IP
Purpose:    Fetch intake form questions and any previously saved responses.
```

**Response (200):**
```json
{
  "intake_id": "e1f2a3b4-c5d6-7890-efab-901234567890",
  "appointment_type": "wellness",
  "pet_name": "Mochi",
  "vet_name": "Dr. Emily Chen",
  "appointment_date": "2026-06-26",
  "clinic_name": "Meadow Pet Clinic",
  "status": "in_progress",
  "questions": [
    {
      "id": "q_appetite",
      "order": 1,
      "text": "How has Mochi's appetite been over the past month?",
      "type": "single_choice",
      "options": ["Great", "Normal", "Reduced", "Not eating"],
      "answer": null,
      "required": true,
      "skippable": false
    }
  ],
  "total_questions": 10,
  "completed_questions": 0,
  "estimated_minutes": 3
}
```

**Question sets** are defined as static Python dictionaries in `intake_delivery_agent.py` (one dict per appointment type; see Section 6). Pet name and vet name are interpolated into question text at response time (not stored in DB).

**Error Responses:**
- `404`: Token not found
- `410`: `{"detail": "This intake form has expired"}` — `intake_tokens.expires_at < now`
- `409`: `{"detail": "Intake form already submitted"}` — `intake_tokens.status = 'complete'`

**Backend Logic:**
1. Query `intake_tokens` by `id`; join to `patients`, `booking_tokens`, `timeblocks`, `resources`.
2. Check status and expiry; return appropriate error codes.
3. Update `intake_tokens.status = 'in_progress'` if current status is `'sent'`.
4. Load question set for `appointment_type_id`; interpolate `{pet_name}` and `{vet_name}`.
5. Load any existing responses from `intake_responses` for this token; populate `answer` fields.

---

### Route 11: `POST /public/intake/{intake_token}/submit`

```
### POST /public/intake/{intake_token}/submit
Auth:       Token
Rate Limit: 3 requests per hour per token (prevents re-submission spam)
Purpose:    Submit all intake form answers. Runs flag logic. Triggers risk rescore (Phase 2).
```

**Request:**
```json
{
  "answers": [
    {"question_id": "q_appetite", "answer": "Normal", "skipped": false},
    {"question_id": "q_water",    "answer": "Normal", "skipped": false},
    {"question_id": "q_weight",   "answer": "Seems lighter", "skipped": false},
    {"question_id": "q_energy",   "answer": "Less active", "skipped": false}
  ],
  "submitted_at": "2026-06-20T09:45:00"
}
```

**Validation:**
- Token valid, not expired, not already `complete`.
- `answers`: array of objects; each must have `question_id` (string) and either `answer` (string) or `skipped: true`.
- `question_id` must exist in the appointment type's question set.
- All `required: true` questions must have an answer (not skipped); else 400 with list of missing question IDs.
- Answer text max 500 chars for free-text questions.

**Response (200):**
```json
{
  "status": "complete",
  "flags_raised": 2,
  "flag_names": ["flag_weight_loss_energy", "flag_monitor_appetite"],
  "message": "Thank you! Dr. Emily Chen will review this before your visit.",
  "booking_status_url": "https://book.vpma.app/status/d0e1f2a3-b4c5-6789-defa-890123456789"
}
```

**Error Responses:**
- `404`: Token not found
- `409`: Already submitted (`status = 'complete'`); body: `{"detail": "Intake already submitted"}`
- `410`: Token expired
- `400`: Validation failure; body includes `{"detail": "...", "missing_questions": ["q_weight"]}`

**Backend Logic:**
1. Validate token and answers.
2. **Insert response rows:** For each answer, `INSERT INTO intake_responses (id, intake_token_id, question_id, question_text, answer, answered_at, skipped) VALUES (...)`.
3. **Run flag logic** (defined in `intake_delivery_agent.py`):
   - `flag_weight_loss_energy`: `q_weight == "Seems lighter" AND q_energy IN ["Less active", "Lethargic"]`
   - `flag_anesthesia_risk`: `appointment_type == "dental" AND q_cardiac_meds answer contains a medication name`
   - `flag_potential_toxin`: `appointment_type == "sick" AND q_ingested != "No"`
   - `flag_vaccine_reaction`: `q_vaccine_reaction != "No"` (vaccines appointment type)
   - `flag_no_food_water`: `appointment_type == "sick" AND q_eating == "No"`
4. Write `flags` JSON to `intake_tokens.flags`.
5. Write all responses as JSON blob to `intake_tokens.responses`.
6. Update `intake_tokens.status = 'complete'`, `completed_at = now`.
7. Update `booking_tokens.lifecycle_state = 'intake_complete'`, `updated_at = now`.
8. Update `timeblocks.intake_status = 'received'`.
9. If `len(raised_flags) > 0`: log staff-facing alert entry; in Phase 2 this triggers push notification.
10. Log: `{"action": "intake_submitted", "intake_token_id": ..., "flags_raised": N}`

---

### Route 12: `POST /public/waitlist`

```
### POST /public/waitlist
Auth:       owner_sessions cookie (preferred) OR anonymous (owner_id + patient_id provided explicitly)
Rate Limit: 3 requests per 10 minutes per IP
Purpose:    Add owner/patient to waitlist for a clinic + appointment type.
            Phase 1: records the entry and enables notification when slot opens.
            No AI backfill in Phase 1.
```

**Request:**
```json
{
  "clinic_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "patient_id": "e5f6a7b8-c9d0-1234-efab-345678901234",
  "owner_id": "d4e5f6a7-b8c9-0123-defa-234567890123",
  "appointment_type_id": "wellness",
  "urgency": "routine",
  "time_preferences": ["weekday_morning", "weekday_afternoon"],
  "min_notice_hours": 3,
  "phone": "5551234567",
  "sms_consent": true
}
```

**Validation:**
- `clinic_id`: must exist; `waitlist_enabled` must be `1` in `clinic_booking_config`.
- `appointment_type_id`: must be in bookable types for clinic.
- `urgency`: one of `["wellness", "routine", "urgent"]`.
- `time_preferences`: array of strings; valid values: `"weekday_morning"`, `"weekday_afternoon"`, `"saturday_morning"`, `"any"`.
- `phone`: required for SMS notification; same normalization as lookup.
- `min_notice_hours`: 1, 3, or 24 only.
- Duplicate check: `SELECT id FROM waitlist WHERE clinic_id = ? AND patient_id = ? AND appointment_type_id = ? AND active = 1`; if found: return 409 `{"detail": "Already on waitlist for this appointment type"}`.

**Response (201):**
```json
{
  "waitlist_id": "f2a3b4c5-d6e7-8901-fabc-012345678901",
  "position": 3,
  "message": "You're on the waitlist. We'll notify you at (555) 123-4567 when a slot opens.",
  "manage_url": null
}
```

**Note:** `position` is computed as `SELECT COUNT(*) FROM waitlist WHERE clinic_id = ? AND appointment_type_id = ? AND active = 1 AND urgency >= ?` — higher urgency entries ahead of same-urgency entries sorted by `join_date` ASC. `manage_url` is null in Phase 1.

**Error Responses:**
- `400`: Validation failure
- `404`: Clinic not found, or waitlist not enabled
- `409`: Already on waitlist
- `429`: Rate limit

**Backend Logic:**
1. Validate all fields.
2. Compute `flexibility_score` (see §2.7).
3. `INSERT INTO waitlist (id, patient_id, clinic_id, procedure_type, preferred_vet_id, urgency, offer_status, join_date, owner_id, time_preferences, min_notice_hours, active, flexibility_score, phone_for_sms, sms_consent) VALUES (...)`.
4. Compute position.
5. Log: `{"action": "waitlist_joined", "clinic_id": ..., "patient_id": ..., "urgency": ..., "position": N}`

---

### Route 13: `GET /api/clinics/{clinic_id}/booking-config`

```
### GET /api/clinics/{clinic_id}/booking-config
Auth:       Staff JWT (same as all /api/ routes)
Rate Limit: Standard staff API limits
Purpose:    Fetch current booking configuration for a clinic (staff admin view).
```

**Response (200):** Full `clinic_booking_config` row as JSON object, including `bookable_appointment_types` list, `hidden_resource_ids` list, and all scheduling rule fields.

**Backend Logic:**
1. Verify staff auth (existing `Depends(require_auth)` pattern if present, else read-only endpoint — spec to confirm with auth implementation).
2. `SELECT * FROM clinic_booking_config WHERE clinic_id = ?`.
3. If not found: return default config object (all fields at defaults, `online_booking_enabled = false`).
4. Parse JSON fields (`bookable_appointment_types`, `hidden_resource_ids`) into lists.

---

### Route 14: `PUT /api/clinics/{clinic_id}/booking-config`

```
### PUT /api/clinics/{clinic_id}/booking-config
Auth:       Staff JWT
Rate Limit: Standard staff API limits
Purpose:    Create or update clinic booking configuration (upsert).
```

**Request:** `ClinicBookingConfigUpdate` Pydantic model (see Section 5).

**Response (200):** Updated `clinic_booking_config` row.

**Backend Logic:**
1. Validate all fields (see model in Section 5).
2. `INSERT OR REPLACE INTO clinic_booking_config (...) VALUES (...)` with `updated_at = now`.
3. If `online_booking_enabled` toggled to `1` and `clinics.slug IS NULL`: auto-generate slug from clinic name; `UPDATE clinics SET slug = ? WHERE id = ?`.
4. Log staff action to verbose log.

---

## 5. New Pydantic Models

Add the following to `backend/models.py`. All imports are from the existing header (`from pydantic import BaseModel, Field`, etc.).

```python
# ---------------------------------------------------------------------------
# S07 — Online Booking Portal Models
# ---------------------------------------------------------------------------

class BookableAppointmentType(BaseModel):
    id: str                                    # e.g. "wellness", "sick", "vaccines"
    name: str                                  # Display name: "Annual Wellness Exam"
    duration_minutes: int                      # Default duration for this type
    intake_question_set: str = "wellness"      # Key into INTAKE_QUESTION_SETS dict
    description: str = ""                      # Optional client-facing description
    enabled: bool = True                       # Whether online booking is active for this type
    breed_duration_overrides: dict = {}        # e.g. {"Persian": 60, "Maine Coon": 60}


class ClinicBookingConfig(BaseModel):
    """Full booking config for a clinic. Used for GET /api/.../booking-config response."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    clinic_id: str
    online_booking_enabled: bool = False
    same_day_booking_enabled: bool = False
    waitlist_enabled: bool = True
    auto_confirm: bool = True
    require_deposit: bool = False              # Phase 3 / MOD-FIN
    deposit_amount_cents: int = 0
    advance_booking_days: int = 30
    same_day_cutoff_hour: int = 14             # 0-23; local to clinic timezone
    min_booking_notice_hours: int = 1
    buffer_minutes: int = 10
    show_vet_names: bool = True
    show_vet_photos: bool = False
    bookable_appointment_types: List[BookableAppointmentType] = Field(default_factory=list)
    booking_confirmation_msg: str = ""
    cancellation_policy: str = ""
    intake_sms_template: str = ""
    hidden_resource_ids: List[str] = Field(default_factory=list)
    emergency_phone: str = ""
    emergency_message: str = ""
    brand_color_primary: str = "#6C63FF"
    brand_color_accent: str = "#F0A500"
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class ClinicBookingConfigUpdate(BaseModel):
    """Request body for PUT /api/clinics/{clinic_id}/booking-config."""
    online_booking_enabled: Optional[bool] = None
    same_day_booking_enabled: Optional[bool] = None
    waitlist_enabled: Optional[bool] = None
    auto_confirm: Optional[bool] = None
    advance_booking_days: Optional[int] = None  # 7-90 range enforced in route handler
    same_day_cutoff_hour: Optional[int] = None  # 0-23
    min_booking_notice_hours: Optional[int] = None
    buffer_minutes: Optional[int] = None        # 0-60
    show_vet_names: Optional[bool] = None
    bookable_appointment_types: Optional[List[BookableAppointmentType]] = None
    booking_confirmation_msg: Optional[str] = None
    cancellation_policy: Optional[str] = None
    hidden_resource_ids: Optional[List[str]] = None
    emergency_phone: Optional[str] = None
    emergency_message: Optional[str] = None
    brand_color_primary: Optional[str] = None   # Must be valid hex: #RRGGBB
    brand_color_accent: Optional[str] = None


class OwnerLookupRequest(BaseModel):
    clinic_id: str
    phone: Optional[str] = None                # 10-digit US number (formatting stripped)
    email: Optional[str] = None                # at least one of phone/email required


class PetSummary(BaseModel):
    """Minimal pet info returned at lookup time. No medical history."""
    id: str
    name: str
    species: str
    breed: str
    age_years: Optional[float] = None          # Calculated from dob; null if dob unknown
    last_visit_label: Optional[str] = None     # e.g. "14 months ago"; null if never visited
    care_due: bool = False                     # Phase 2: populated from care_protocols
    care_due_reason: Optional[str] = None


class OwnerLookupResponse(BaseModel):
    found: bool
    owner_id: Optional[str] = None
    display_name: Optional[str] = None         # First name only; never full name at lookup
    pets: List[PetSummary] = Field(default_factory=list)


class OwnerRegisterRequest(BaseModel):
    clinic_id: str
    first_name: str                            # 1-100 chars
    last_name: str                             # 1-100 chars
    phone: str                                 # 10-digit US number; required
    email: str                                 # Valid email; required
    sms_consent: bool = False
    pet: "NewPetRequest"


class NewPetRequest(BaseModel):
    name: str                                  # 1-100 chars
    species: str                               # dog|cat|bird|rabbit|reptile|other
    breed: str = ""                            # Optional; empty string allowed
    dob_approx: Optional[str] = None           # ISO date YYYY-MM-DD; past dates only
    sex: Optional[str] = None                  # male|female|unknown
    neutered: Optional[bool] = None


class SlotAvailabilityItem(BaseModel):
    """A single available appointment slot returned by GET /public/clinics/.../availability."""
    slot_id: str                               # Deterministic UUID5 from (resource_id, start_datetime)
    resource_id: str                           # Vet resource UUID
    vet_name: str                              # e.g. "Dr. Emily Chen"; masked if show_vet_names=False
    vet_display_name: str                      # Shorter form: "Dr. Chen"
    start_datetime: str                        # ISO datetime in clinic's local timezone
    end_datetime: str
    duration_minutes: int
    rank: int                                  # 1=first; Phase 1 is chronological only
    rank_label: str                            # "Soonest Available"; Phase 2: "Best Match"
    rank_explanation: str                      # Human-readable rationale; Phase 2: AI-generated
    no_show_risk_label: Optional[str] = None   # Phase 2: "Low" | "Medium" | "High"


class BookingHoldRequest(BaseModel):
    clinic_id: str
    resource_id: str
    start_datetime: str                        # ISO datetime
    end_datetime: str                          # ISO datetime
    appointment_type_id: str
    patient_id: str


class BookingHoldResponse(BaseModel):
    hold_id: str
    slot_id: str
    expires_at: str                            # ISO datetime; 10 minutes from now
    resource_id: str
    vet_name: str
    start_datetime: str
    end_datetime: str


class BookingConfirmRequest(BaseModel):
    hold_id: str
    patient_id: str
    appointment_type_id: str
    urgency: str = "routine"                   # wellness|routine|urgent|emergency
    notes: Optional[str] = None               # Max 300 chars
    sms_consent: bool = False
    cancellation_policy_accepted: bool         # Must be True


class BookingConfirmResponse(BaseModel):
    booking_id: str
    booking_token: str
    status: str                                # "booked"
    status_url: str
    intake_url: str
    appointment: dict                          # {date, time, duration_minutes, vet_name, clinic_name, address}


class LifecycleStep(BaseModel):
    state: str
    label: str
    completed: bool
    completed_at: Optional[str] = None


class BookingStatusResponse(BaseModel):
    """Response for GET /public/status/{booking_token}."""
    booking_id: str
    booking_token: str
    status: str                                # booking_tokens.status
    clinic_name: str
    clinic_phone: str
    clinic_address: str
    pet_name: str
    owner_display_name: str
    appointment_type: str
    vet_name: str
    start_datetime: str
    duration_minutes: int
    lifecycle: List[LifecycleStep]
    intake_token: Optional[str] = None
    intake_status: Optional[str] = None
    intake_url: Optional[str] = None
    cancellable: bool
    reschedulable: bool = False                # Phase 2
    calendar_url: str


class IntakeSubmitRequest(BaseModel):
    answers: List["IntakeAnswer"]
    submitted_at: str                          # ISO datetime from client


class IntakeAnswer(BaseModel):
    question_id: str
    answer: Optional[str] = None              # None only if skipped=True
    skipped: bool = False


class WaitlistJoinRequest(BaseModel):
    clinic_id: str
    patient_id: str
    owner_id: str
    appointment_type_id: str
    urgency: str = "routine"                   # wellness|routine|urgent
    time_preferences: List[str] = Field(default_factory=list)
    min_notice_hours: int = 3                  # 1 | 3 | 24
    phone: str
    sms_consent: bool = False


# Update forward references
OwnerRegisterRequest.model_rebuild()
IntakeSubmitRequest.model_rebuild()
```

---

## 6. New Agent / Module Files

### 6.1 `backend/agents/booking_agent.py`

**File path:** `/home/matt/SMB_Hunt/General_Scheduler/backend/agents/booking_agent.py`

**Responsibilities:**
- Orchestrate the booking confirmation transaction (soft-hold → confirmed timeblock → booking_token → intake_token)
- Arm the reminder pipeline via existing `ReminderAgent`
- Compute `flexibility_score` for waitlist entries
- Expose `cancel_booking` for `POST /public/bookings/{token}/cancel`
- **Does NOT** do: AI slot ranking (Phase 2), risk scoring (Phase 2), SMS/email delivery (delegated to `intake_delivery_agent.py`)

**Key functions:**

```python
"""
booking_agent.py — Booking confirmation, cancellation, and hold management.
Handles the atomic transaction that converts a soft-hold into a confirmed booking.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4


class BookingAgent:
    def __init__(self, db, log_fn=None):
        """
        Args:
            db: Repository instance (InMemoryRepository from repository.py)
            log_fn: Callable(str) for verbose log entries; defaults to no-op
        """
        self._db = db
        self._log = log_fn or (lambda msg: None)

    def confirm_booking(
        self,
        session_id: str,
        hold_id: str,
        patient_id: str,
        appointment_type_id: str,
        urgency: str,
        notes: Optional[str],
        sms_consent: bool,
    ) -> dict:
        """
        Atomically confirm a booking from a soft-hold.

        Steps:
          1. Validate hold exists, belongs to session, not expired.
          2. Final slot availability double-check.
          3. Create timeblock, booking_token, intake_token in one SQLite transaction.
          4. Delete soft-hold.
          5. Return booking_token and intake_token IDs.

        Returns:
            dict with keys: booking_token_id, intake_token_id, timeblock_id,
                            start_datetime, end_datetime, resource_id, clinic_id, owner_id

        Raises:
            ValueError: If hold not found, expired, or slot taken.
        """
        ...

    def cancel_booking(
        self,
        booking_token_id: str,
        reason: str,
        notes: Optional[str] = None,
    ) -> dict:
        """
        Cancel a confirmed booking.

        Steps:
          1. Validate booking_token is active.
          2. Set booking_tokens.status = 'cancelled', cancelled_at = now, cancel_reason = reason.
          3. Set timeblocks.status = 'cancelled'.
          4. Phase 1: log waitlist trigger (actual backfill in Phase 2).
          5. Return cancellation summary.

        Returns:
            dict with keys: status, cancelled_at, fee_applied (always False in Phase 1)
        """
        ...

    def arm_reminders(
        self,
        timeblock_id: str,
        booking_token_id: str,
        owner_id: str,
        appointment_datetime: datetime,
    ) -> None:
        """
        Register T-48h and T-2h reminders with the existing ReminderAgent.
        Called async (BackgroundTasks) after booking confirmation.

        Integration point: instantiates ReminderAgent with self._db and self._log,
        then calls run_reminder_sweep() — the sweep will pick up this appointment
        on its next run within the look-ahead window.

        See Section 8.1 for full reminder arming detail.
        """
        ...

    def compute_flexibility_score(self, time_preferences: list[str]) -> float:
        """
        Compute waitlist flexibility score (0.25-1.0).
        Higher score = wider time window = higher priority for slot filling.
        See §2.7 for scoring formula.
        """
        all_windows = {"weekday_morning", "weekday_afternoon", "saturday_morning", "any"}
        if "any" in time_preferences:
            return 1.0
        return max(0.25, len(set(time_preferences) & all_windows) / len(all_windows))
```

**Dependencies:**
- `from ..repository import _get_conn` (raw SQLite connection for transaction)
- `from .reminders import ReminderAgent`
- Standard library: `datetime`, `uuid`, `json`

---

### 6.2 `backend/agents/intake_delivery_agent.py`

**File path:** `/home/matt/SMB_Hunt/General_Scheduler/backend/agents/intake_delivery_agent.py`

**Responsibilities:**
- Define static intake question sets for each appointment type
- Compute delivery delay based on appointment timing
- Dispatch intake form link via email (always) and SMS (if MOD-COM licensed)
- Run flag logic on submitted answers
- **Does NOT** do: SOAP note generation (that's `soap.py`), risk scoring (Phase 2), reminder scheduling (`booking_agent.py`)

**Intake question sets (static dict — source of truth in Python, not DB):**

```python
# INTAKE_QUESTION_SETS maps appointment_type_id → list of question dicts
# Each question: {id, order, text, type, options, required, skippable}
# Text may contain {pet_name} and {vet_name} template vars (interpolated at serve time)

INTAKE_QUESTION_SETS = {
    "wellness": [
        {"id": "q_appetite", "order": 1, "text": "How has {pet_name}'s appetite been over the past month?",
         "type": "single_choice", "options": ["Great", "Normal", "Reduced", "Not eating"],
         "required": True, "skippable": False},
        {"id": "q_water", "order": 2, "text": "Any changes in water intake?",
         "type": "single_choice", "options": ["More than usual", "Normal", "Less than usual"],
         "required": False, "skippable": True},
        {"id": "q_weight", "order": 3, "text": "Any changes in weight that you've noticed?",
         "type": "single_choice", "options": ["Seems heavier", "Same", "Seems lighter"],
         "required": False, "skippable": True},
        {"id": "q_energy", "order": 4, "text": "How is {pet_name}'s energy and activity level?",
         "type": "single_choice", "options": ["More active", "Same", "Less active", "Lethargic"],
         "required": False, "skippable": True},
        {"id": "q_gi", "order": 5, "text": "Any vomiting or diarrhea in the past 2 weeks?",
         "type": "single_choice", "options": ["Yes (how often?)", "Occasionally", "No"],
         "required": False, "skippable": True},
        {"id": "q_skin", "order": 6, "text": "Any lumps, bumps, or skin changes you've noticed?",
         "type": "single_choice", "options": ["Yes (describe)", "No"],
         "required": False, "skippable": True},
        {"id": "q_meds", "order": 7, "text": "Is {pet_name} on any medications or supplements currently?",
         "type": "single_choice", "options": ["Yes (list)", "No"],
         "required": False, "skippable": True},
        {"id": "q_concerns", "order": 8, "text": "Any concerns or questions you'd like Dr. {vet_name} to address?",
         "type": "free_text", "options": [], "required": False, "skippable": True},
        {"id": "q_vaccines", "order": 9, "text": "Does {pet_name} need any vaccine boosters today?",
         "type": "single_choice", "options": ["Not sure", "Yes", "No"],
         "required": False, "skippable": True},
        {"id": "q_exposure", "order": 10, "text": "Has {pet_name} been to boarding, dog parks, or around other pets in the past 30 days?",
         "type": "single_choice", "options": ["Yes", "No"],
         "required": False, "skippable": True},
    ],
    "sick": [
        # 9 questions — see design doc §6.2
    ],
    "vaccines": [
        # 5 questions — see design doc §6.2
    ],
    "dental": [
        # 7 questions — see design doc §6.2
    ],
    "followup": [
        # 4 questions — see design doc §6.2
    ],
    "other": [
        {"id": "q_reason", "order": 1, "text": "Please describe the reason for your visit.",
         "type": "free_text", "options": [], "required": True, "skippable": False},
    ],
}
```

**Key functions:**

```python
class IntakeDeliveryAgent:
    def __init__(self, db, log_fn=None, sms_gateway=None):
        """
        Args:
            db: Repository instance
            log_fn: Callable(str)
            sms_gateway: SMSGateway instance from sms_gateway.py; if None, SMS skipped
        """
        ...

    def schedule_delivery(
        self,
        intake_token_id: str,
        appointment_datetime: datetime,
    ) -> None:
        """
        Compute send delay and dispatch intake form link.

        Delay logic (design doc §6.1):
          - appointment > 48h away → send immediately (delay_minutes = 0)
          - appointment 24-48h away → delay 15 minutes
          - appointment < 24h away (same-day) → delay 5 minutes

        Phase 1 implementation: use FastAPI BackgroundTasks with asyncio.sleep()
        for the delay. In Phase 2, replace with a proper task queue (Celery/ARQ).

        Calls: self.send_intake_email() and (if sms_gateway available) self.send_intake_sms()
        Updates: intake_tokens.status = 'sent', sent_at = now
        """
        ...

    def send_intake_email(
        self,
        intake_token_id: str,
        owner_email: str,
        owner_first_name: str,
        pet_name: str,
        vet_name: str,
        clinic_name: str,
        appointment_date: str,
        intake_url: str,
    ) -> bool:
        """
        Send intake form link via email.

        Phase 1 implementation: log the email content to verbose log (simulation).
        In Phase 2: wire to SendGrid via MOD-COM email channel.

        Message format (plain text + HTML):
          Subject: "[Pet]'s pre-visit health check for [Date] at [Clinic]"
          Body: "Hi [Name], please complete [Pet]'s pre-visit health check before
                 your appointment on [Date] with [Vet] at [Clinic]. This takes ~3 min:
                 [intake_url]. This link expires in 7 days."

        Returns: True on success (or simulated success), False on error.
        """
        ...

    def send_intake_sms(
        self,
        intake_token_id: str,
        owner_phone: str,
        owner_first_name: str,
        pet_name: str,
        appointment_date: str,
        intake_url: str,
    ) -> bool:
        """
        Send intake form link via SMS using sms_gateway.send_intake_link().

        Only called if self.sms_gateway is not None AND sms_consent = True on owner.
        Uses the existing SMSGateway.send_intake_link() method (already implemented
        in sms_gateway.py).

        PHI note: SMS body contains ONLY owner first name, pet name, appointment date,
        and the HTTPS intake link. No diagnoses, no medical info in the body.
        """
        ...

    def run_flag_logic(
        self,
        appointment_type_id: str,
        answers: dict,  # {question_id: answer_text}
    ) -> dict:
        """
        Evaluate submitted answers against predefined flag rules.

        Returns: dict of {flag_name: bool}
        Flag definitions (Phase 1):
          flag_weight_loss_energy:  q_weight == "Seems lighter" AND q_energy in ["Less active","Lethargic"]
          flag_anesthesia_risk:     appointment_type == "dental" AND q_cardiac_meds is not "No"
          flag_potential_toxin:     appointment_type == "sick" AND q_ingested not in ["No","Not sure"]
          flag_vaccine_reaction:    appointment_type == "vaccines" AND q_reaction != "No"
          flag_no_food_water:       appointment_type == "sick" AND q_eating == "No"
          flag_monitor_appetite:    q_appetite == "Reduced" OR q_appetite == "Not eating"
        """
        ...

    def get_question_set(
        self,
        appointment_type_id: str,
        pet_name: str = "",
        vet_name: str = "",
    ) -> list[dict]:
        """
        Return the question list for a given appointment type with template vars interpolated.
        Falls back to "other" question set if appointment_type_id not recognized.
        """
        questions = INTAKE_QUESTION_SETS.get(appointment_type_id, INTAKE_QUESTION_SETS["other"])
        return [
            {**q, "text": q["text"].format(pet_name=pet_name, vet_name=vet_name)}
            for q in questions
        ]
```

**Check for existing `intake.py`:** The existing `backend/agents/intake.py` handles staff-side free-text intake parsing (via `IntakeAgent.extract_symptoms()`). This is a different concern. **Do not modify or replace `intake.py`**. `intake_delivery_agent.py` is a new file alongside it for the online portal structured intake flow.

**Dependencies:**
- `from ..sms_gateway import sms as _sms_gateway` (module-level singleton)
- `from ..repository import _get_conn`
- Standard library: `datetime`, `json`, `uuid`

---

### 6.3 `backend/agents/availability_agent.py`

**File path:** `/home/matt/SMB_Hunt/General_Scheduler/backend/agents/availability_agent.py`

**Responsibilities:**
- Compute free appointment slots for a given clinic, appointment type, and date range
- Exclude hidden vets, expired holds, and buffer conflicts
- Return sorted `SlotAvailabilityItem` list (Phase 1: chronological; Phase 2: ranked)
- **Does NOT** do: AI ranking (Phase 2), no-show risk scoring (Phase 2), slot booking or holding

**Key functions:**

```python
"""
availability_agent.py — Computes available appointment slots from the schedule.
Phase 1: returns chronological list. Phase 2 will add score_slot() ranking.
"""
from __future__ import annotations

from datetime import datetime, timedelta, date
from typing import List, Optional


class AvailabilityAgent:
    def __init__(self, db, log_fn=None):
        """
        Args:
            db: Repository instance
            log_fn: Callable(str) for verbose log
        """
        ...

    def get_available_slots(
        self,
        clinic_id: str,
        appointment_type_id: str,
        duration_minutes: int,
        days: int = 14,
        urgency: str = "routine",
        patient_id: Optional[str] = None,  # Reserved for Phase 2 vet-continuity ranking
        preferred_time: Optional[str] = None,  # Reserved for Phase 2
        hidden_resource_ids: list[str] = None,
        same_day_enabled: bool = False,
        same_day_cutoff_hour: int = 14,
        min_notice_hours: int = 1,
        advance_booking_days: int = 30,
        buffer_minutes: int = 10,
    ) -> List[dict]:
        """
        Compute all free slots within the booking window.

        Algorithm:
          1. Fetch all vets for clinic (via vet_clinic_assignments); exclude hidden_resource_ids.
          2. Compute search_start and search_end datetimes (factoring same_day_cutoff, notice, advance).
          3. For each vet, fetch existing timeblocks and active slot_holds in window.
          4. For each vet, iterate candidate times (step = 30 min) within vet's
             availability_windows each day.
          5. A candidate is FREE if:
             - [candidate_start, candidate_end] has zero overlap with any booked timeblock
               (status NOT IN ('cancelled', 'no_show'))
             - [candidate_start, candidate_end] has zero overlap with any active slot_hold
               (expires_at > now)
             - buffer_minutes gap exists before and after (no adjacent appointment < buffer away)
          6. Collect free candidates; sort ascending by start_datetime.
          7. Return as list of dicts matching SlotAvailabilityItem schema.

        Returns:
            List of slot dicts (SlotAvailabilityItem-compatible), sorted ascending by start_datetime.
            Phase 1: rank=index+1, rank_label="Soonest Available", rank_explanation=static.
        """
        ...

    def _get_vet_timeblocks(
        self,
        resource_id: str,
        start: datetime,
        end: datetime,
    ) -> List[dict]:
        """
        Fetch all non-cancelled timeblocks for a vet in the given window.
        Returns list of {start_time, end_time} dicts.
        """
        ...

    def _get_active_holds(
        self,
        resource_id: str,
        start: datetime,
        end: datetime,
    ) -> List[dict]:
        """
        Fetch non-expired slot_holds for a vet in the given window.
        Returns list of {start_datetime, end_datetime} dicts.
        """
        ...

    def _overlaps(
        self,
        candidate_start: datetime,
        candidate_end: datetime,
        blocks: List[dict],
        buffer_minutes: int = 0,
    ) -> bool:
        """
        Return True if [candidate_start, candidate_end] (optionally with buffer)
        overlaps any block in blocks.
        Overlap condition: block_start < candidate_end + buffer AND block_end > candidate_start - buffer
        """
        ...
```

**Dependencies:**
- `from ..repository import _get_conn`
- Standard library: `datetime`, `uuid`

---

## 7. Security & Privacy Model

### 7.1 Session Token Design

| Property | Value |
|---|---|
| Type | UUID v4 (`str(uuid4())`) — 128 bits of cryptographic randomness |
| Storage | `owner_sessions.id` (primary key in DB; server-side validation on every request) |
| Transmission | `Set-Cookie: vpma_session=<token>; HttpOnly; Secure; SameSite=Strict; Max-Age=1800; Path=/` |
| TTL | 30 minutes sliding window; extended by `+30 min` on every authenticated request |
| Rotation | Not rotated during a session (complexity not warranted for 30-min TTL) |
| Revocation | Set `expires_at = now - 1` in DB; subsequent requests validate against DB so revocation is instant |
| Self-contained? | **No** — JWT is explicitly rejected (design doc §13.2). Session is validated against DB on every request. |
| Cleanup | Background task: `DELETE FROM owner_sessions WHERE expires_at < datetime('now')` every 15 minutes |

### 7.2 Booking Token Design

| Property | Value |
|---|---|
| Type | UUID v4 |
| Storage | `booking_tokens.id` (primary key) |
| Transmission | URL path parameter only: `/status/{booking_token}` — never in cookie |
| TTL | 30 days after appointment date (`appointment_start_datetime + 30 days`) |
| Rotation | No rotation — token is read-mostly after creation |
| Write operations allowed | Cancel (`POST /public/bookings/{token}/cancel`) only |
| Revocation | `status = 'cancelled'` or `status = 'expired'` blocks all actions |
| PHI exposure | Token grants access to: pet name, appointment type, vet name, appointment datetime, clinic name/address. **Never** grants access to: diagnosis, medication history, lab results, intake responses (those require intake token). |

### 7.3 Intake Token Design

| Property | Value |
|---|---|
| Type | UUID v4 |
| Storage | `intake_tokens.id` |
| Transmission | URL path parameter only: `/intake/{intake_token}` |
| TTL | 7 days from booking confirmation |
| One-time submit | After `status = 'complete'`, `POST /public/intake/{token}/submit` returns 409. GET allowed (owner can review their responses). |
| Resend | If owner requests resend (future UX), existing token is re-dispatched. **No new token** is generated. |
| PHI exposure | Token grants access to: intake questions (personalized by pet/vet name), owner's own submitted responses. No access to other patients' data. |

### 7.4 Rate Limits Table

| Endpoint | Limit | Window | Key | Response |
|---|---|---|---|---|
| `GET /public/clinics/{slug}` | 60 req | 1 min | IP | 429 + `Retry-After: 60` |
| `GET /public/clinics/{slug}/appointment-types` | 30 req | 1 min | IP | 429 |
| `GET /public/clinics/{slug}/availability` | 30 req | 1 min | IP | 429 |
| `POST /public/owners/lookup` | 10 req | 5 min | IP | 429 + `Retry-After: 300` |
| `POST /public/owners/register` | 5 req | 5 min | IP | 429 |
| `POST /public/bookings/hold` | 20 req | 1 min | session | 429 |
| `POST /public/bookings` | 5 req | 1 hour | session | 429 |
| `GET /public/status/{token}` | 60 req | 1 min | IP | 429 |
| `GET /public/intake/{token}` | 60 req | 1 min | IP | 429 |
| `POST /public/intake/{token}/submit` | 3 req | 1 hour | token | 409 (already submitted) |
| `POST /public/waitlist` | 3 req | 10 min | IP | 429 |

**Phase 1 implementation:** In-process Python dict keyed by `(endpoint_key, identifier)`. Accepts slight count drift under concurrent load (no Redis lock). Sufficient for single-process FastAPI deployment. Replace with Redis in Phase 2 if multi-worker.

**Rate limit middleware:**
```python
# In main.py — add before route handlers
_rate_limit_store: dict = {}  # {(endpoint, identifier): (count, window_start)}

def check_rate_limit(endpoint: str, identifier: str, max_requests: int, window_seconds: int):
    now = datetime.utcnow().timestamp()
    key = (endpoint, identifier)
    count, window_start = _rate_limit_store.get(key, (0, now))
    if now - window_start > window_seconds:
        _rate_limit_store[key] = (1, now)
        return True
    if count >= max_requests:
        raise HTTPException(status_code=429, detail="Rate limit exceeded",
                           headers={"Retry-After": str(window_seconds)})
    _rate_limit_store[key] = (count + 1, window_start)
    return True
```

### 7.5 Data Minimization Table

| Step | Data Returned | Data Withheld |
|---|---|---|
| Clinic landing (`GET /public/clinics/{slug}`) | Name, address, phone, email, timezone, booking config | Internal IDs not useful to client, hidden resource IDs |
| Owner lookup (`POST /public/owners/lookup`) | Owner first name, pet names, species, breed, age, last visit label | Full last name (display name only), address, DOB, medical history, diagnoses |
| Pet list (`GET /public/owners/{id}/pets`) | Same as lookup; session-gated | Same withheld fields |
| Availability (`GET /public/.../availability`) | Slot times, vet name (if show_vet_names=true), duration | Vet personal contact info, full schedule, other patients' appointments |
| Booking status (`GET /public/status/{token}`) | Appointment details for THIS booking only | Risk score, medical history, SOAP notes, other bookings |
| Intake form (`GET /public/intake/{token}`) | Questions for THIS appointment type + own submitted answers | Other patients' intake data, staff notes |

### 7.6 HIPAA Considerations (Phase 1)

1. **Minimum Necessary:** Public API returns only data required for the specific step. No bulk owner/patient exports via public endpoints.
2. **PHI in SMS:** SMS message body contains ONLY: owner first name, pet name, appointment date, and an HTTPS link. No diagnoses, no medications, no symptoms in the SMS body.
3. **PHI in Email:** Confirmation email contains appointment date and clinic name. Full intake link (HTTPS, served over TLS) is where PHI is accessed.
4. **Audit Trail:** Every public API request logs: timestamp, IP, user agent, endpoint, session/token ID (if applicable), action, result. Stored in `_SESSION_LOG` (existing pattern) and structured dict for Verbose Log UI.
5. **No PHI in URLs:** Booking token and intake token are UUID v4 — they are opaque identifiers, not PHI-bearing. The data they grant access to is served over HTTPS.
6. **At-rest encryption:** Phase 1 uses SQLite with plaintext storage (dev/staging). Production Postgres migration must use column-level encryption for `intake_tokens.responses` and `intake_responses.answer` before any live PHI is stored.
7. **Access control:** Patient medical records (SOAP notes, risk scores, lab results) are inaccessible from all `/public/` routes — they require staff JWT.

### 7.7 Soft-Hold TTL and Expiry Behavior

| Scenario | Behavior |
|---|---|
| Owner takes < 10 min on slot selection screen | Hold valid; proceeds to confirm |
| Owner takes > 10 min on confirm page | Hold expired; `POST /public/bookings` returns 409; frontend redirects to slot selection with message: "Your held slot has expired. Please select again." |
| Two owners attempt same slot simultaneously | First POST to `/public/bookings/hold` wins (UNIQUE constraint); second gets 409 immediately |
| Owner abandons browser (no confirm) | Hold expires at `expires_at`; cleanup task deletes row |
| Staff books the same slot (via dashboard) | Staff booking creates `timeblocks` row; hold remains but availability check in `POST /public/bookings` will catch the conflict and return 409 to the owner |

---

## 8. Integration Points with Existing System

### 8.1 `reminders.py` — Reminder Pipeline Arming

**Existing `ReminderAgent`** (in `backend/agents/reminders.py`):
- `run_reminder_sweep(clinic_id)` — finds timeblocks within `window_hours` (default 48h) and dispatches reminders
- `confirm_appointment(timeblock_id)` — marks confirmed
- Uses `sms_gateway.send_reminder()` for SMS, falls back to email simulation

**How Phase 1 wires in:**

After `POST /public/bookings` transaction commits, `booking_agent.arm_reminders()` is called as a `BackgroundTask`. It does NOT call `run_reminder_sweep()` immediately (that's the existing sweep mechanism). Instead it ensures the `timeblock` record is present and `confirmation_status = 'not_sent'` — the existing sweep will pick it up.

```python
# booking_agent.py — arm_reminders implementation
def arm_reminders(
    self,
    timeblock_id: str,
    booking_token_id: str,
    owner_id: str,
    appointment_datetime: datetime,
) -> None:
    """
    Ensure the timeblock is ready for the reminder sweep.
    The existing ReminderAgent.run_reminder_sweep() will pick it up
    when it runs (via POST /api/reminders/sweep or scheduled cron).

    For online bookings, the T-48h reminder includes an intake nudge if intake is incomplete.
    This is implemented by the sweep checking intake_tokens.status != 'complete' for
    timeblocks where source = 'online_portal', and appending the intake_url to the message.

    This method:
    1. Logs that reminders are armed.
    2. Verifies confirmation_status = 'not_sent' on timeblock (set by default in INSERT).
    3. Stores booking_token_id in timeblocks (for intake_url resolution at sweep time).
    """
    self._log(
        f"BOOKING AGENT: Reminders armed for timeblock {timeblock_id[:8]} "
        f"— appointment at {appointment_datetime.isoformat()}"
    )
```

**Intake nudge in T-48h reminder (modification to `reminders.py`):**

Add to `run_reminder_sweep()` sweep logic:
```python
# After building reminder body, check if this is an online booking with pending intake
if row.get("source") == "online_portal":
    intake_status = conn.execute(
        "SELECT it.status, it.id FROM intake_tokens it "
        "JOIN timeblocks t ON t.intake_token_id = it.id WHERE t.id = ?",
        (tb_id,)
    ).fetchone()
    if intake_status and intake_status["status"] not in ("complete", "skipped"):
        intake_url = f"https://book.vpma.app/intake/{intake_status['id']}"
        body += f" Complete {patient_name}'s pre-visit form: {intake_url}"
```

**T-2h reminder:** Standard sweep — no intake nudge (too close to appointment).

### 8.2 `sms_gateway.py` — SMS Delivery

The existing `SMSGateway` singleton is imported by `intake_delivery_agent.py`:
```python
from ..sms_gateway import sms as _sms_gateway
```

**Existing method used:**
- `sms.send_intake_link(to, owner_name, patient_name, intake_url)` — already implemented in `sms_gateway.py` (line 162)

**Phase 1 behavior:** If `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and `TWILIO_FROM_NUMBER` env vars are set: live SMS sent. Otherwise: simulation mode (logged, not sent). This matches existing gateway behavior — no code change needed in `sms_gateway.py`.

**MOD-COM gate:** Before calling `sms.send_intake_link()`, check:
```python
account = db.get_default_account()
mod_com_active = db.account_has_module(account["id"], "MOD-COM") if account else False
if mod_com_active and owner.sms_consent:
    _sms_gateway.send_intake_link(...)
```

### 8.3 `risk.py` — Risk Scoring

**Phase 1: Minimal integration.** Risk agent is NOT called during the booking flow in Phase 1. The `timeblocks.risk_score` column is written as NULL.

**Phase 2 integration points** (documented here for awareness):
- **Point 1 (slot selection):** `risk.get_slot_no_show_rates(resource_id, weekday, hour)` — returns `no_show_probability`; used to populate `no_show_risk_label` on SlotAvailabilityItem.
- **Point 2 (intake submission):** After `POST /public/intake/{token}/submit` completes, call `risk_agent.score(patient_id, appointment_type, intake_answers)` → write result to `timeblocks.risk_score` and `intake_tokens.flags`.

**No changes to `risk.py` required in Phase 1.**

### 8.4 Waitlist Table Integration

**Existing `waitlist` table fields** (from `repository.py`): `id, patient_id, clinic_id, procedure_type, preferred_vet_id, urgency, offer_status, join_date`.

**Phase 1 additions** (via ALTER TABLE, documented in §2.7): `owner_id, time_preferences, min_notice_hours, active, pass_count, flexibility_score, phone_for_sms, sms_consent, last_notified_at, removed_at, remove_reason`.

**Phase 1 waitlist behavior:**
- `POST /public/waitlist` creates a new row with `active = 1`, `offer_status = 'waiting'`.
- When a booking is cancelled (via `booking_agent.cancel_booking()`), log a waitlist trigger event (no automated backfill in Phase 1; staff manually checks waitlist).
- Staff can view active waitlist entries in the existing dashboard.
- **Phase 2** adds the `waitlist.py` agent that automatically notifies the top-ranked waitlist candidate and creates a `waitlist_claim_tokens` entry.

### 8.5 Verbose Log Format for Portal Events

All portal actions emit verbose log entries using the existing `log_agent_step()` / `_log1()` pattern in `main.py`. Format:

```python
_SESSION_LOG.append(
    f"BOOKING PORTAL [{action}]: "
    f"clinic={clinic_id[:8] if clinic_id else 'none'} "
    f"owner={owner_id[:8] if owner_id else 'anon'} "
    f"patient={patient_id[:8] if patient_id else 'none'} "
    f"token={booking_token[:8] if booking_token else 'none'} "
    f"ip={ip_address} result={result}"
)
```

**Action values:** `clinic_landing_viewed`, `owner_lookup`, `owner_registered`, `slot_held`, `booking_confirmed`, `booking_cancelled`, `intake_delivered`, `intake_submitted`, `waitlist_joined`.

### 8.6 `timeblocks` Table — Field Mapping for Online Bookings

When `POST /public/bookings` creates a timeblock, the following field values are set:

| Field | Value | Notes |
|---|---|---|
| `id` | `uuid4()` | Primary key |
| `job_id` | `uuid4()` | Stub job — no semantic scheduling job needed for online bookings |
| `resource_ids` | `json.dumps([resource_id])` | Single vet; matches existing format |
| `start_time` | ISO datetime from hold | e.g., `"2026-06-26T10:30:00"` |
| `end_time` | ISO datetime from hold | e.g., `"2026-06-26T11:15:00"` |
| `patient_id` | From booking request | FK → `patients.id` |
| `intake_status` | `"not_started"` | Updated to `"pending"` when intake dispatched; `"received"` when submitted |
| `followup_status` | `"not_started"` | Managed by existing followup agent post-visit |
| `risk_level` | `NULL` | Set by risk agent (Phase 2) |
| `status` | `"scheduled"` | Existing value for active appointments |
| `clinic_id` | From booking context | FK → `clinics.id` |
| `source` | `"online_portal"` | **New column** — drives 🌐 badge on scheduling board |
| `urgency` | From owner selection | `"wellness"` \| `"routine"` \| `"urgent"` \| `"emergency"` |
| `client_notes` | From booking request | Owner's free-text notes (max 300 chars) |
| `appointment_type_id` | From booking request | e.g., `"wellness"` |
| `intake_token_id` | Created atomically | FK → `intake_tokens.id` |
| `confirmation_status` | `"not_sent"` | Existing column; managed by `ReminderAgent` |
| `lab_order_id` | `NULL` | Existing column; not applicable at booking time |

---

## 9. Frontend Architecture (Phase 1)

### 9.1 Technology and Location

**Technology:** React 18 + React Router v6. No framework (no Next.js) — all data is fetched from public APIs; no server-side rendering needed. Bundled with Vite.

**Location:** New subdirectory within the existing frontend: `frontend/src/booking/`. This isolates portal code from the staff dashboard. The booking portal is a separate React root mounted at `/book/` URL prefix.

**Reasoning:** Separate directory (not separate Next.js app) because:
1. The existing frontend may already be Vite/React — reuse the build pipeline
2. Avoids managing two separate dev servers and build outputs
3. Staff auth context is not needed; booking routes use their own `BookingContext` (no staff token)

### 9.2 URL Structure

All URLs are under `/book/` in the main app or served from `https://book.vpma.app/`:

```
/book/[clinic_slug]               → Step 0: Landing
/book/[clinic_slug]/identify      → Step 1: Owner identification
/book/[clinic_slug]/pet           → Step 2: Pet selection
/book/[clinic_slug]/type          → Step 3: Appointment type + urgency
/book/[clinic_slug]/slot          → Step 4: Slot selection
/book/[clinic_slug]/confirm       → Step 5: Review + confirm
/book/status/[booking_token]      → Status tracker page
/book/intake/[intake_token]       → Intake form
/book/[clinic_slug]/waitlist      → Waitlist join
/book/[clinic_slug]/new           → New client shortcut (skips identify)
```

React Router v6 handles all routes client-side. Server must serve `index.html` for all `/book/*` paths.

### 9.3 State Management

No external state library (no Redux, no Zustand). State flows via:
1. **URL params:** `clinic_slug`, `booking_token`, `intake_token` come from the URL.
2. **React Context (`BookingContext`):** Stores in-memory booking flow state: `{clinicData, ownerData, selectedPet, appointmentType, urgency, holdData}`. Context is cleared on page refresh — this is intentional; the session cookie (HttpOnly, not readable by JS) handles auth, and the user is redirected to the correct step if flow state is missing.
3. **Server-side session cookie:** The `vpma_session` HttpOnly cookie is sent automatically on all fetch requests to the same origin. Frontend code never reads or writes this cookie.

**No localStorage for PHI.** The design doc mentions offline-aware localStorage draft state (§12.4) — in Phase 1, this is deferred. No localStorage usage for booking flow state.

### 9.4 Pages Required

| Page | URL | Purpose | Key Components |
|---|---|---|---|
| Clinic Landing | `/book/[slug]` | Step 0: orient owner | `<ClinicHeader>`, clinic info card, primary CTA button |
| Owner Identification | `/book/[slug]/identify` | Step 1: phone/email lookup | `<OwnerIdentifyForm>`, `<ProgressBar>` |
| Pet Selection | `/book/[slug]/pet` | Step 2: select pet | `<PetGrid>`, `<PetCard>`, add-new-pet modal |
| Appointment Type | `/book/[slug]/type` | Step 3: type + urgency | `<AppointmentTypePicker>`, urgency chips, notes field |
| Slot Selection | `/book/[slug]/slot` | Step 4: pick a time | `<SlotCard>` list, "Show more times" expander, waitlist CTA |
| Confirm | `/book/[slug]/confirm` | Step 5: review + confirm | `<ConfirmationSummary>`, policy checkbox, spinner on submit |
| Status | `/book/status/[token]` | Post-booking tracker | `<StatusTracker>`, `<LifecycleTimeline>`, action buttons |
| Intake | `/book/intake/[token]` | Pre-visit form | `<IntakeForm>`, one-question-per-screen layout |
| Waitlist Join | `/book/[slug]/waitlist` | Join waitlist | `<WaitlistForm>` |

### 9.5 Component List

| Component | Props | Key States | Notes |
|---|---|---|---|
| `<ClinicHeader>` | `clinicName, phone, emergencyPhone, brandColor` | `normal, emergency` | Sticky top; phone is `<a href="tel:...">` |
| `<ProgressBar>` | `currentStep, totalSteps, labels` | — | Animated fill; collapses to "Step N of M" on mobile |
| `<OwnerIdentifyForm>` | `clinicId, onFound, onNotFound` | `idle, loading, found, not_found, rate_limited` | Inline phone format `(555) 123-4567` |
| `<PetCard>` | `pet, onSelect, selected` | `default, selected, adding` | Species emoji icon; 44px min tap target |
| `<PetGrid>` | `pets, onSelect, onAddPet` | — | 2 cols mobile, 3 cols tablet+ |
| `<AppointmentTypePicker>` | `types, onSelect` | — | Card buttons; urgency `role="radiogroup"` |
| `<UrgencySelector>` | `value, onChange` | — | Color-coded chips; emergency opens modal |
| `<SlotCard>` | `slot, rank, onBook` | `default, loading, selected, expired, taken` | Scale-in animation on mount |
| `<ConfirmationSummary>` | `booking, owner, onConfirm, onEditStep` | `idle, submitting, error` | Sticky confirm CTA on mobile |
| `<StatusTracker>` | `token` | — | Polls `GET /public/status/{token}` every 60s |
| `<LifecycleTimeline>` | `lifecycle[]` | — | Step checkmarks; current step animated |
| `<IntakeForm>` | `token` | per-question states | One question per screen; progress `Q 3 of 8` |
| `<WaitlistForm>` | `clinicId, preFilledContext` | — | Checkbox group for time preferences |

### 9.6 Mobile-First Requirements

| Requirement | Implementation |
|---|---|
| Minimum touch target | 44×44px on all buttons, cards, links (`min-height: 44px; min-width: 44px`) |
| Body font size | `font-size: 16px` minimum on all inputs (prevents iOS auto-zoom) |
| Viewport meta | `<meta name="viewport" content="width=device-width, initial-scale=1">` |
| Safe area insets | `padding-bottom: env(safe-area-inset-bottom)` on sticky footer |
| Sticky CTA | Primary CTA button is `position: sticky; bottom: 0` within scroll container on mobile |
| No hover-only interactions | All interactive state changes triggered by click/tap, not hover alone |

---

## 10. Phase 1 Acceptance Criteria

```
AC-001: Given a valid clinic_slug, GET /public/clinics/{slug} returns HTTP 200 with
        clinic name, address, phone, timezone, and booking_config.online_booking_enabled.

AC-002: Given an unknown clinic_slug, GET /public/clinics/{slug} returns HTTP 404.

AC-003: Given online_booking_enabled=false in clinic_booking_config, 
        GET /public/clinics/{slug}/appointment-types returns HTTP 403.

AC-004: Given a valid clinic_slug and at least one enabled appointment type,
        GET /public/clinics/{slug}/appointment-types returns HTTP 200 with a non-empty list
        containing id, name, and duration_minutes for each enabled type.

AC-005: Given a valid clinic_slug, appointment_type_id, and days=7,
        GET /public/clinics/{slug}/availability returns HTTP 200 with a `slots` array
        containing only future slots within the next 7 days.

AC-006: Given a soft-hold exists for slot X by session A,
        GET /public/clinics/{slug}/availability does NOT include slot X in the available list
        until the hold expires.

AC-007: Given a returning owner's phone number (matching owners.phone after normalization),
        POST /public/owners/lookup returns found=true, display_name (first name only),
        and a list of non-deceased pets with name, species, and age_years.
        Response does NOT include last name, address, DOB, or medical history.

AC-008: Given an unknown phone number,
        POST /public/owners/lookup returns {"found": false} with HTTP 200.

AC-009: Given 11 calls to POST /public/owners/lookup from the same IP within 5 minutes,
        the 11th call returns HTTP 429 with a Retry-After header set to 300.

AC-010: Given a new client submitting valid first_name, last_name, phone, email, and pet data,
        POST /public/owners/register creates owners and patients records, returns HTTP 201 with
        owner_id and patient_id, and sets the vpma_session HttpOnly cookie.

AC-011: Given a duplicate phone number on POST /public/owners/register,
        returns HTTP 409 with a message directing the user to the returning client flow.

AC-012: Given a valid session cookie and available slot,
        POST /public/bookings/hold returns HTTP 200 with hold_id and expires_at 10 minutes
        from request time.

AC-013: Given two concurrent POST /public/bookings/hold requests for the same slot,
        exactly one returns HTTP 200 and the other returns HTTP 409.

AC-014: Given a valid hold_id and cancellation_policy_accepted=true,
        POST /public/bookings returns HTTP 201 with booking_token, status_url, and intake_url.
        A timeblocks record is created with source='online_portal'.
        A booking_tokens record is created with lifecycle_state='booked'.
        An intake_tokens record is created with status='pending'.
        The slot_holds record for the hold_id is deleted.

AC-015: Given cancellation_policy_accepted=false,
        POST /public/bookings returns HTTP 400.

AC-016: Given a hold whose expires_at has passed,
        POST /public/bookings returns HTTP 409 with a message indicating the hold expired.

AC-017: After POST /public/bookings succeeds, within 60 seconds,
        intake_tokens.status for the created intake_token is 'sent', and
        a verbose log entry with action='intake_delivered' is present.

AC-018: After POST /public/bookings succeeds, the timeblock's confirmation_status is 'not_sent',
        making it eligible for the next ReminderAgent sweep.

AC-019: Given a valid booking_token,
        GET /public/status/{booking_token} returns HTTP 200 with lifecycle array containing
        all 7 states, with 'booked' showing completed=true and the rest completed=false.

AC-020: Given a cancelled booking_token (booking_tokens.status='cancelled'),
        GET /public/status/{booking_token} returns HTTP 410.

AC-021: Given a valid intake_token and all required questions answered,
        POST /public/intake/{intake_token}/submit returns HTTP 200,
        intake_tokens.status is set to 'complete', intake_responses rows are created,
        and booking_tokens.lifecycle_state is updated to 'intake_complete'.

AC-022: Given POST /public/intake/{intake_token}/submit is called a second time on a
        completed intake, returns HTTP 409 with "Intake already submitted".

AC-023: Given q_weight='Seems lighter' and q_energy='Less active' in a wellness intake,
        POST /public/intake/{token}/submit sets flag_weight_loss_energy=true in
        intake_tokens.flags and response includes flags_raised >= 1.

AC-024: Given a valid clinic with waitlist_enabled=true and a valid owner session,
        POST /public/waitlist returns HTTP 201 with waitlist_id and position >= 1.

AC-025: Given the same patient submitting POST /public/waitlist twice for the same
        clinic and appointment_type, the second call returns HTTP 409.

AC-026: Given staff sets online_booking_enabled=false via PUT /api/clinics/{id}/booking-config,
        subsequent GET /public/clinics/{slug} returns booking_config.online_booking_enabled=false,
        and GET /public/clinics/{slug}/appointment-types returns HTTP 403.

AC-027: Given a clinics record without a slug,
        PUT /api/clinics/{id}/booking-config with online_booking_enabled=true
        auto-generates clinics.slug from the clinic name (lowercase, hyphenated).

AC-028: Given a valid session,
        GET /public/owners/{owner_id}/pets returns HTTP 200.
        Given a mismatched session (session.owner_id != path owner_id),
        returns HTTP 401.

AC-029: Given a session cookie with expires_at in the past,
        GET /public/owners/{owner_id}/pets returns HTTP 401.
```

---

## Appendix A: Key Ambiguities Resolved During Spec Writing

Three ambiguities from the design doc were resolved with explicit engineering decisions:

1. **`owners` table schema mismatch:** The design doc specifies `first_name` and `last_name` as separate fields, but the existing `owners` table has a single `name` TEXT column. This spec resolves this by: (a) adding `first_name` and `last_name` as additive columns via ALTER TABLE, (b) populating both the new columns AND the legacy `name` column (as `first_name + " " + last_name`) for backward compatibility with all existing staff-side code that reads `owners.name`. No existing code breaks.

2. **Slot ID stability vs. database backing:** The design doc references `slot_id` as a field in availability responses and hold requests, but does not specify whether slots are pre-computed and stored, or generated on-the-fly. This spec resolves this by: using deterministic `UUID5(NAMESPACE_URL, "{resource_id}:{start_datetime}")` as slot IDs — they are computed at API response time, not stored in DB. The `slot_holds` table stores `(resource_id, start_datetime)` as the canonical slot identifier. This avoids a "pre-computed slots" table that would require a complex availability pre-generation job.

3. **Phase 1 waitlist notification trigger:** The design doc describes `waitlist.py` triggering on cancellation but defers AI backfill to Phase 2. This spec resolves this by: Phase 1 logs a waitlist trigger event on cancellation (`action=waitlist_backfill_triggered`) but does NOT implement automated SMS notification to waitlist members. Staff manually reviews the waitlist view and contacts the next owner. The data model (including `phone_for_sms`, `sms_consent`, `time_preferences`) is fully populated so Phase 2 can immediately implement the automated flow without data migration.

---

## Appendix B: Open Questions Requiring Human Input Before Implementation

1. **Staff auth mechanism:** All existing `/api/` routes in `main.py` have no auth middleware — they are currently unprotected (appropriate for internal/demo use). The new `GET/PUT /api/clinics/{clinic_id}/booking-config` routes are staff-only. Before implementing, confirm: is there a planned auth system (JWT, API key, OAuth) for staff routes, or should these routes use the same "no auth" approach as all existing `/api/` routes for Phase 1?

2. **Email delivery for intake forms:** Phase 1 defers SendGrid integration. The current spec simulates email delivery (logs to verbose log). Confirm: is simulated email delivery acceptable for Phase 1 demo/testing, or does a real email (even via a basic SMTP relay) need to be sent? If real email is needed, provide SMTP credentials or confirm SendGrid as the provider.

3. **Frontend repository location:** The spec places the booking portal React code in `frontend/src/booking/`. Confirm the existing frontend structure — is there an existing `frontend/` directory with a Vite/React setup, and what is its entry point URL? If the existing frontend is a different technology or structure, the integration path changes.

---

*End of S07 Phase 1 Engineering Specification — v1.0*
