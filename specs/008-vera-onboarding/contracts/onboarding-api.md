# Feature 008 — Vera Onboarding: API Contracts

All endpoints prefixed `/api/onboarding/`. All requests/responses are JSON unless noted.

---

## POST `/api/onboarding/session`

Create a new onboarding session. Called on first page load if no session cookie exists.

**Request body**:
```json
{
  "device_fingerprint": "string (optional)"
}
```

**Response**:
```json
{
  "session_id": "uuid",
  "session_token": "uuid",
  "phase": 0,
  "created_at": "ISO datetime",
  "verbose_log": ["VERA (Onboarding): Session created — welcome flow initiated"]
}
```

**Cookie set**: `onboarding_session=<session_token>; HttpOnly; SameSite=Lax; Max-Age=2592000`

---

## GET `/api/onboarding/session/{session_token}`

Retrieve session state by cookie token. Used on page load to restore state.

**Response**:
```json
{
  "session_id": "uuid",
  "session_token": "uuid",
  "phase": 0,
  "persona_role": "owner|manager|associate|proxy|null",
  "practice_name": "string|null",
  "track": "greenfield|switcher|paper",
  "state_json": {},
  "email_anchor": "string|null",
  "created_at": "ISO datetime",
  "updated_at": "ISO datetime"
}
```

**404** if token not found or expired.

---

## GET `/api/onboarding/resume/{magic_token}`

Resume session from a magic link click. Validates token, creates new cookie, issues new magic link.

**Path param**: `magic_token` — raw URL-safe token from the magic link URL

**Response**:
```json
{
  "session_id": "uuid",
  "session_token": "uuid",
  "practice_name": "string",
  "phase": 3,
  "state_summary": "string (human-readable summary of captured data)",
  "verbose_log": ["VERA (Onboarding): Session resumed via magic link — Phase 3 restored"]
}
```

**Cookie set**: New `onboarding_session` cookie (replaces old).  
**410 Gone** if token already used. **404** if not found. **403** if expired.

---

## PATCH `/api/onboarding/session/{session_id}`

Update session fields (phase, persona_role, practice_name, state_json, track).

**Request body** (all fields optional):
```json
{
  "phase": 3,
  "persona_role": "owner",
  "practice_name": "Riverside Animal Hospital",
  "track": "greenfield",
  "state_json": { "address": "123 Main St", "hours": "Mon-Fri 8am-6pm" }
}
```

**Response**:
```json
{
  "session_id": "uuid",
  "updated_at": "ISO datetime",
  "verbose_log": ["VERA (Onboarding): Role set to owner — post-Replace targets updated"]
}
```

---

## POST `/api/onboarding/magic-link`

Send a magic link to the given email. Issues a 30-day single-use token.

**Request body**:
```json
{
  "session_id": "uuid",
  "email": "user@example.com"
}
```

**Response**:
```json
{
  "sent": true,
  "email": "user@example.com",
  "expires_at": "ISO datetime (30 days)",
  "magic_token": "raw-token-for-demo-console",
  "verbose_log": ["VERA (Onboarding): Magic link issued — expires 2026-07-21"]
}
```

**Note**: In demo scope, `magic_token` is returned in the response body and printed to server console. No email transport.

---

## POST `/api/onboarding/upload`

Upload a document for extraction. Pre-validates size (max 25MB) and MIME type.

**Request**: `multipart/form-data`
- `file`: The file binary
- `session_id`: string (form field)

**Response**:
```json
{
  "document_id": "uuid",
  "mime_type": "text/csv",
  "file_size_bytes": 12340,
  "classified_type": "staff_roster",
  "streaming_status": "pending",
  "verbose_log": ["VERA (Onboarding): File received — staff_roster (CSV, 12KB)"]
}
```

**400** if file exceeds 25MB: `{"detail": "That file is 28.3MB — I can handle up to 25MB."}`  
**400** if unsupported MIME type.

---

## GET `/api/onboarding/extract-stream/{document_id}`

**SSE stream** — Server-Sent Events. Opens extraction pipeline for the document.

**Media type**: `text/event-stream`

**Event types** (each is a JSON `data:` field):

```
data: {"type": "start", "message": "Reading your spreadsheet..."}

data: {"type": "tab_found", "message": "Found Staff tab — reading 5 providers..."}

data: {"type": "entity", "entity_id": "uuid", "entity_type": "provider",
       "display": "Dr. Rivera", "confidence": 0.95,
       "confidence_label": "high", "source_text": "Rivera, Maria DVM",
       "extracted_fields": {"name": "Dr. Maria Rivera", "role": "DVM", "days": ["Mon","Tue","Wed"]}}

data: {"type": "entity", "entity_id": "uuid", "entity_type": "room",
       "display": "Iso", "confidence": 0.45,
       "confidence_label": "low", "source_text": "Iso",
       "extracted_fields": {"name": "Iso"}}

data: {"type": "timeout", "message": "I got most of it — still working in the background."}

data: {"type": "done", "entity_count": 8}
```

Stream closes after `done` or `timeout` event.

---

## POST `/api/onboarding/confirm-entity/{entity_id}`

Confirm (or correct) an extracted entity. Triggers live DB write if confidence is high, or logs correction signal.

**Request body**:
```json
{
  "confirmed": true,
  "correction": {
    "field_name": "name",
    "correct_value": "Isolation Ward"
  }
}
```
`correction` is optional. If omitted, entity is confirmed as-is.

**Response**:
```json
{
  "entity_id": "uuid",
  "confirmed": true,
  "corrected": true,
  "verbose_log": ["VERA (Onboarding): Entity confirmed — room 'Isolation Ward' (correction logged)"]
}
```

---

## POST `/api/onboarding/scrape-logo`

Trigger logo scraping from a URL. Returns the best candidate (or initiates cascade).

**Request body**:
```json
{
  "session_id": "uuid",
  "url": "https://www.example.com or https://maps.google.com/..."
}
```

**Response**:
```json
{
  "logo_asset_id": "uuid",
  "source_type": "og_image",
  "image_url": "/api/onboarding/logo-asset/uuid",
  "fallback_type": "image",
  "initials": null,
  "verbose_log": ["VERA (Onboarding): Logo found via og:image — pending confirmation"]
}
```

If no logo found:
```json
{
  "logo_asset_id": "uuid",
  "source_type": "monogram",
  "image_url": null,
  "fallback_type": "monogram",
  "initials": "RAH",
  "verbose_log": ["VERA (Onboarding): No logo found — initials monogram 'RAH' generated"]
}
```

---

## POST `/api/onboarding/confirm-logo/{logo_asset_id}`

Confirm or replace the logo asset.

**Request body**:
```json
{
  "action": "confirm|try_next|upload",
  "uploaded_file_path": "string (only for action=upload)"
}
```

**Response**:
```json
{
  "logo_asset_id": "uuid",
  "confirmed": true,
  "source_type": "upload",
  "verbose_log": ["VERA (Onboarding): Logo confirmed — placed in practice header"]
}
```

---

## POST `/api/onboarding/go-live`

Trigger the Replace event. Creates live Clinic + Resource records from confirmed entities.

**Request body**:
```json
{
  "session_id": "uuid"
}
```

**Response**:
```json
{
  "clinic_id": "uuid",
  "practice_name": "Riverside Animal Hospital",
  "first_action_targets": [
    "Share your booking link with clients",
    "Set your availability",
    "Configure online booking"
  ],
  "verbose_log": [
    "VERA (Onboarding): Replace triggered — Harmony demo archived",
    "VERA (Onboarding): Clinic 'Riverside Animal Hospital' created",
    "VERA (Onboarding): 3 providers written to live DB",
    "VERA (Onboarding): 4 rooms written to live DB"
  ]
}
```

---

## POST `/api/onboarding/activation`

Record activation event (first real client appointment booked).

**Request body**:
```json
{
  "session_id": "uuid",
  "booking_id": "uuid"
}
```

**Response**:
```json
{
  "activated_at": "ISO datetime",
  "session_id": "uuid",
  "verbose_log": ["VERA (Onboarding): Activation recorded — first real appointment booked"]
}
```
