# Feature 008 — Vera Onboarding: Technical Research

## 1. Logo Scraping

**Library stack**: `httpx` (async HTTP) + `BeautifulSoup4` (HTML parsing)

**Cascade strategy** (highest → lowest fidelity):
1. `og:image` — OpenGraph image tag; typically the highest-quality brand asset
2. `<link rel="icon" type="image/png">` — Apple touch icon or large favicon
3. Largest `<img>` in `<header>` or `<nav>` — brand logo in page chrome
4. `/favicon.ico` — fallback; low quality but universally present
5. SVG initials monogram — generated server-side if no image found

**Google Maps path**: Business cover photo → gallery first image (via Maps embed/structured data).  
**Fallback**: Extract initials from practice name (e.g., "Riverside Animal Hospital" → "RAH"), render as SVG with practice brand color.

**Constraints**: Server-side only (no client CORS); 5s timeout per request; cache in `logo_assets` table.

---

## 2. Document Parsing

| Format | Library | Notes |
|---|---|---|
| `.csv` | stdlib `csv` | No install needed; yields row dicts |
| `.xlsx` / `.xls` | `openpyxl` | Multi-sheet; iterate `wb.sheetnames` |
| `.pdf` | `pdfplumber` | Text extraction per page; layout-aware |
| `.png/.jpg/.jpeg/.webp/.gif/.heic` | `pytesseract` + `Pillow` | OCR confidence always capped at 0.5 |
| `.doc/.docx` | `python-docx` (P2) | Deferred; prompt user to save as PDF |

**Classification heuristics** (keyword matching on column headers + content):
- `staff_roster` — columns containing "name", "vet", "doctor", "role", "days"
- `room_list` — columns containing "room", "suite", "exam", "iso"
- `schedule` — columns containing "time", "slot", "appointment", "date"
- `license` — PDF keywords: "license number", "expires", "DVM", "veterinary"
- `fee_schedule` — columns containing "price", "fee", "cost", "service"
- `unknown` — default; extract whatever structured data is present

---

## 3. Server-Sent Events (SSE) Streaming

**Backend**: FastAPI `StreamingResponse` with `media_type="text/event-stream"`

```python
async def generate():
    yield "data: {\"type\": \"start\", \"message\": \"Reading your spreadsheet...\"}\n\n"
    for entity in parse_document(path):
        yield f"data: {json.dumps(entity)}\n\n"
    yield "data: {\"type\": \"done\"}\n\n"

return StreamingResponse(generate(), media_type="text/event-stream",
    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
```

**Frontend**: Native `EventSource` API (no library)

```typescript
const es = new EventSource(`/api/onboarding/extract-stream/${documentId}`);
es.onmessage = (e) => { const data = JSON.parse(e.data); appendEntity(data); };
es.onerror = () => es.close();
```

**30-second hard cap**: Backend generator tracks elapsed time; yields `{"type": "timeout"}` at 30s and closes. Frontend surfaces surfaced entities for confirmation.

---

## 4. Session Identity

| Mechanism | Scope | Duration | Notes |
|---|---|---|---|
| UUID `session_token` | All devices (same browser) | 30 days | Set as `httpOnly; SameSite=Lax` cookie |
| Magic link SHA-256 hash | Any device, any browser | 30 days | Email-anchored; single-use per resume |
| Device fingerprint | Optional | Session | User-Agent + Accept-Language; stored in `magic_links.device_fingerprint` |

**Magic link flow**:
1. `POST /api/onboarding/magic-link` → generate `secrets.token_urlsafe(32)` → SHA-256 hash stored → raw token returned in response body for demo console delivery
2. `GET /api/onboarding/resume/{magic_token}` → hash raw token → look up by hash → validate expiry → mark `used_at` → issue new session cookie → issue new magic link for next resume

**Demo delivery**: In demo scope, magic link is printed to server console + returned in API response. No email transport configured.

---

## 5. Replace Logic

**Trigger**: User clicks "Make it live →" → `POST /api/onboarding/go-live`

**Backend sequence**:
1. Retrieve all `confirmed` entities for session
2. Create `Clinic` record from `practice_name` + extracted fields
3. Create `Resource` records (VET type) for each confirmed provider entity
4. Create `Resource` records (ROOM type) for each confirmed room entity
5. Archive Harmony demo context: `UPDATE clinics SET is_active=false WHERE id='harmony-demo'`
6. Set `onboarding_sessions.phase = 6` (LIVE)
7. Return `{clinic_id, first_action_targets}` based on `persona_role`

**First action targets by role**:
```
OWNER    → ["Share your booking link with clients", "Set your availability", "Configure online booking"]
MANAGER  → ["Invite the vets to their accounts", "Set room schedules", "Configure notifications"]
ASSOCIATE→ ["Book a test appointment to see how it feels", "Review your schedule", "Set your availability"]
PROXY    → ["Send [Practice Name]'s owner a link to review and activate", "Preview the booking portal"]
```

---

## 6. Mobile Strategy

**Breakpoint**: `768px` (matches spec requirement)

**Two-panel → tabbed collapse**:
- Desktop (≥ 768px): `.onboarding-shell` is `flex-row`; `.live-panel` = 65%; `.chat-panel` = 35%
- Mobile (< 768px): `.onboarding-shell` is `flex-col`; `.tab-bar` appears at top; active tab is shown

**Touch file input**: `window.matchMedia('(pointer: coarse)')` or `'ontouchstart' in window` → hide drag overlay; show `<input type="file">` button styled as Vera's upload affordance.

**25MB pre-flight**: Read `file.size` before `fetch()`. If `file.size > 26_214_400` (25 × 1024²), show Vera error message inline and abort upload.
