# Feature Specification: Vera Onboarding — Conversational Practice Setup

**Feature Branch**: `008-vera-onboarding`

**Created**: 2026-06-21

**Status**: Draft

**Input**: User description: "Vera Onboarding Design — a six-phase agentic onboarding experience that guides a new veterinary practice from a demo to a fully live, configured practice instance through conversational Q&A, document intelligence, logo scraping, and an invisible activation event. Governed by the Vera Constitution (Chief of Staff persona, not a vet, not a lawyer). Practice context becomes Vera's persistent working memory."

---

## Clarifications

### Session 2026-06-21

- Q: Who is the primary onboarding persona and does role affect first-action targets? → A: Either — the flow adapts based on role self-identification. Vera asks "Are you the practice owner, or setting this up for the practice?" after the pivot and adjusts post-Replace first-action targets accordingly.
- Q: What is the acceptable wait time for document extraction and what does Vera show during the wait? → A: Progressive streaming with a 30-second hard cap. Vera narrates extraction in real time ("Found Staff tab — reading 5 providers..."); after 30 seconds she surfaces what she has and continues in background.
- Q: Is mobile browser support required for v1 onboarding? → A: Fully responsive — two-panel layout collapses to tabbed single-column on screens narrower than 768px; file drag-and-drop degrades to a file picker button on touch devices.
- Q: What is the maximum file size Vera will accept for document upload? → A: 25MB per file.
- Q: At what point does account creation occur and how is session recovery handled if the cookie is lost? → A: Magic link offered after Q1 (practice name). Vera asks for email to save progress before the open prompt; session is email-anchored from that point, resumable on any device. No password required until billing activation.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Demo to Live Practice in One Session (Priority: P1)

A veterinary practice owner (or practice manager, or designated implementer) visits VetAgent for the first time, watches Vera run a demo morning at Harmony Animal Hospital, is prompted to "build their own," self-identifies their role, answers one open question about their practice (or pastes a Google Maps link / drops a spreadsheet), provides an email for progress-saving, sees their schedule, rooms, and staff populate in real time, confirms their logo, and goes live — all within 20 minutes, without creating a password.

**Why this priority**: This is the entire onboarding product. Every other story depends on this flow completing. It is the proof-of-intelligence moment that distinguishes VetAgent from every PIMS competitor. Failure here means zero conversion.

**Independent Test**: Can be fully tested by opening `/welcome`, watching the demo, clicking "Let's build it →", entering a practice name and a one-sentence description of the practice, and verifying that a schedule with at least one provider and one appointment slot appears — without ever filling out a form.

**Acceptance Scenarios**:

1. **Given** a new visitor lands on `/welcome`, **When** the page loads, **Then** Vera's introduction message appears character-by-character with no signup gate, no email prompt, and no form.
2. **Given** the demo is running, **When** 8 minutes elapse or the demo sequence completes, **Then** Vera presents the pivot message and a "Let's build it →" button.
3. **Given** the user clicks "Let's build it →", **When** Vera presents the role question, **Then** the user selects one of: Practice Owner / Practice Manager / Associate Vet / Setting this up for someone else — and Vera acknowledges their role before proceeding.
4. **Given** the user types a practice name, **When** they submit it, **Then** the header of the live panel updates to their practice name within 1 second AND Vera immediately offers a magic link ("Save your progress — where should I send a link?").
5. **Given** the user types a free-text response to "Tell me a little about [Practice Name]," **When** Vera processes it, **Then** she reads back a structured summary (practice type, team, facilities, hours) and the schedule panel populates with corresponding provider columns and room tabs.
6. **Given** the practice context has at minimum a name, one provider, and one appointment type, **When** the user clicks "Make it live →", **Then** the demo clinic data dissolves and the real practice data is the active context.
7. **Given** the Replace animation completes, **When** Vera presents the first real action, **Then** the action targets are role-appropriate: owner sees "Share your booking link"; practice manager sees "Invite the vets"; associate vet sees "Book a test appointment."

---

### User Story 2 — Open Prompt: Document Intelligence Path (Priority: P1)

A practice manager drops a staff roster spreadsheet (or Excel file with staff + rooms tabs) in response to Vera's open question. Vera reads it, extracts provider names, roles, working days, and room names, reads them back in a structured confirmation, allows inline correction of any field, and writes confirmed records to the practice model.

**Why this priority**: The document drop is Vera's signature capability — "the magic trick." A prospect who sees Vera correctly parse their actual staff list and read it back is converted. This must work perfectly for CSV, Excel (.xlsx), and PDF at launch.

**Independent Test**: Can be fully tested by uploading a two-tab Excel file (Staff, Rooms) and verifying that the schedule populates with named provider columns and named room tabs matching the file content, with any ambiguous entries (e.g., "Iso") surfaced as inline confirmation prompts.

**Acceptance Scenarios**:

1. **Given** a user drops an Excel file on the conversation panel, **When** the file is received, **Then** Vera displays "Reading your spreadsheet..." within 2 seconds AND begins streaming partial results (e.g., "Found Staff tab — reading 5 providers...") as they are extracted.
2. **Given** the spreadsheet has a "Staff" tab and a "Rooms" tab, **When** extraction completes, **Then** Vera reads back each provider with name, role, and days — and each room with its name — in a structured checklist format with ✅ / ⚠️ / ❓ indicators.
3. **Given** a field has low confidence (e.g., "Iso"), **When** Vera presents it, **Then** an inline confirmation button appears ("isolation ward? [Yes] [Rename]") — not a modal, not a form.
4. **Given** the user confirms all fields, **When** they click confirm, **Then** provider and room records are written to the practice model and appear in the schedule.
5. **Given** the user corrects a field (e.g., "Iso" → "Isolation Ward"), **When** they submit the correction, **Then** the corrected value is used and the correction is logged as a training signal.
6. **Given** the spreadsheet has only one tab (staff only, no rooms), **When** extraction completes, **Then** Vera acknowledges what she found and asks specifically for room information — not a generic "upload another file" prompt.

---

### User Story 3 — Logo Scraping and Confirmation (Priority: P1)

When a practice provides a website URL or Google Maps link, Vera scrapes the best available logo candidate, displays it in the conversation thread AND in the practice header simultaneously, and asks "Is that it?" The user confirms, tries another candidate, or uploads their own.

**Why this priority**: The logo confirmation is the single strongest "this is actually mine" moment in the entire flow. It must always be an explicit confirmation — never silently placed. It is the identity moment.

**Independent Test**: Can be fully tested by pasting a Google Maps business URL into the open prompt and verifying that (a) a logo candidate appears in the conversation panel, (b) the same logo appears in the header of the live panel, and (c) the confirmation prompt has three choices: Yes / Try another / Upload mine.

**Acceptance Scenarios**:

1. **Given** a user pastes a website or Google Maps URL, **When** Vera parses it, **Then** logo extraction runs in parallel with data extraction — logo confirmation fires before the team/rooms read-back.
2. **Given** Vera finds a logo candidate, **When** she presents it, **Then** it appears inline in the conversation AND in the practice header, with "Is that it? [Yes, that's our logo] [Try another] [I'll upload mine]."
3. **Given** the user clicks "Try another," **When** there is another candidate, **Then** Vera presents the next best candidate. When no more candidates exist, **Then** she offers "want to upload yours?"
4. **Given** the user clicks "I'll upload mine," **When** they select a PNG/SVG/JPG/WebP file, **Then** it appears in the header immediately and Vera confirms placement.
5. **Given** no logo is found and the user declines to upload, **When** Vera responds, **Then** she generates a clean initials monogram (e.g., "RAH" for Riverside Animal Hospital) and places it in the header with a note that they can upload from Settings.
6. **Given** the logo is confirmed, **When** Phase 5 (Replace) fires, **Then** the confirmed logo is already in place — the Replace animation removes demo branding, not the user's logo.

---

### User Story 4 — Open Prompt: Link Intelligence Path (Priority: P2)

A practice owner pastes their Google Maps listing URL or their practice website URL in response to Vera's open question. Vera scrapes the listing/website, extracts practice name, address, hours, phone, services, and any team member names — reads back what she found, notes what she couldn't find (typically rooms), and asks targeted follow-up questions for only the gaps.

**Why this priority**: The link paste path is a trust-building shortcut for practices with established online presence. It signals that Vera already knows them — she's not starting from scratch. Critical for conversion of tech-comfortable owners.

**Independent Test**: Can be fully tested by pasting a live Google Maps business URL and verifying that hours, address, phone, and any services listed on the Maps profile appear in Vera's read-back — without the user having typed any of that information.

**Acceptance Scenarios**:

1. **Given** a user pastes a Google Maps URL, **When** Vera detects it, **Then** she immediately responds "Reading your Google Maps listing..." and begins scraping.
2. **Given** the Maps listing has hours, phone, and services, **When** extraction completes, **Then** Vera reads back each field with its source noted ("from listing") and the schedule populates with those hours.
3. **Given** the Maps listing mentions a vet's name in reviews, **When** Vera finds it, **Then** she acknowledges it conversationally ("Clients mention Dr. Rivera by name — I'll surface her availability in your booking portal").
4. **Given** a user pastes a practice website URL, **When** Vera scrapes it, **Then** she extracts name, address, hours, services, and any team page members — presenting each with confirmation inline.
5. **Given** extraction completes but rooms are not found, **When** Vera responds, **Then** she asks specifically about rooms — not a generic "what else should I know?"

---

### User Story 5 — Session Resume (Priority: P2)

A user starts onboarding, provides their practice name and open prompt response, but closes the browser before completing the Replace step. When they return within 30 days, Vera greets them by name, summarizes what was captured, and offers to continue from exactly where they stopped.

**Why this priority**: Onboarding dropout between sessions is a primary conversion killer. Progress persistence eliminates the penalty for not finishing in one sitting and respects the time invested.

**Independent Test**: Can be fully tested by completing through Phase 3 (open prompt confirmed), closing the browser, reopening the URL, and verifying that Vera's greeting references the practice name and the data already captured — without requiring re-entry.

**Acceptance Scenarios**:

1. **Given** a user provided their email (magic link) after Q1 and closes the browser, **When** they click the magic link from any device or browser, **Then** Vera greets them with their practice name and summarizes the session state — no re-entry required.
2. **Given** a user skipped the magic link and closes the browser, **When** they return to the same browser within 30 days, **Then** Vera resumes via session cookie with the same greeting and summary.
3. **Given** a user skipped the magic link and returns on a different device, **When** they land on `/welcome`, **Then** Vera starts a fresh session (cookie not portable) and does not reference the prior session.
4. **Given** the user's magic link or session is older than 30 days, **When** they return, **Then** Vera starts a fresh session but notes any account-level data already saved.

---

### User Story 6 — Vera Introduces Her Professional Boundaries (Priority: P2)

After the Replace event (Phase 5), Vera proactively introduces her clinical and regulatory boundaries — unprompted — before describing what she'll do tomorrow morning. This is a professional self-introduction, not a disclaimer.

**Why this priority**: DVMs who understand Vera's boundaries before encountering them trust her clinical briefs more deeply. This sets the professional relationship correctly from day one, prevents staff from being surprised when Vera declines a diagnosis question, and frames the boundary as identity, not limitation.

**Independent Test**: Can be fully tested by completing the Replace step and verifying that Vera's post-Replace message includes an explicit statement that she is the Chief of Staff (not a veterinarian, not an attorney) and that clinical decisions remain with the licensed DVMs.

**Acceptance Scenarios**:

1. **Given** the Replace animation completes, **When** Vera sends her first post-Replace message, **Then** it includes her professional identity statement ("I'm your Chief of Staff. Not a veterinarian. Not your attorney.") before any operational description.
2. **Given** a user or staff member asks Vera for a clinical opinion at any point, **When** Vera responds, **Then** she acknowledges the urgency, redirects to the licensed vet, and immediately offers what she CAN do (book the slot, pull the literature, flag for review).
3. **Given** a user asks Vera a regulatory question, **When** she responds, **Then** she cites the specific statute with citation, states what it requires, and explicitly defers compliance determination to the practice owner or qualified attorney.

---

### Edge Cases

- What happens when a dropped file is password-protected or corrupted? → Vera reports it cannot read the file and offers alternatives (different file, manual entry).
- What happens when a dropped file exceeds 25MB? → Vera displays: "That file is [X]MB — I can handle up to 25MB. Can you export a smaller version, or paste the key columns as text?"
- What happens when a Google Maps URL returns no business data (e.g., a pin with no listing)? → Vera reports what she found ("I found a location but no business listing") and proceeds to the manual open prompt.
- What happens when the website has no detectable logo? → Vera generates an initials monogram and tells the user where to upload their logo later.
- What happens when two tabs of a spreadsheet have conflicting provider names? → Vera flags the conflict with both values and asks which is correct before proceeding.
- What happens when a user drops an image (whiteboard, floor plan, printed schedule)? → Vera runs OCR, reads back what she could parse, flags unclear lines with ❓, and lets the user fill gaps.
- What happens when a user drops a file that is not staff/rooms/schedule data? → Vera identifies the document type, extracts whatever is relevant (e.g., a license PDF → DVM name, license number, expiry), and routes it to the appropriate context field.
- What happens when the user says "I don't have anything to upload" or "just ask me"? → Vera shifts to the guided build track: two questions at a time, always updating the UI visibly after each answer.
- What happens if the practice name is ambiguous or contains a location (e.g., "Riverside Animal Hospital, Sacramento CA")? → Vera extracts both name and location from the single input and skips the location follow-up.
- What happens when a user is mid-onboarding and their browser crashes? → Session state is persisted to the database on every phase transition; no more than one phase of data is lost.
- What happens when document extraction reaches the 30-second hard cap mid-parse? → Vera surfaces all results extracted so far with a note ("I got most of it — still working on the rest in the background. You can confirm what's here and I'll add the rest shortly."). Background extraction continues and results are streamed in as completed.
- What happens when the magic link email bounces or is not delivered? → The session remains cookie-based until a valid email is provided. Vera offers to resend or use a different address on next visit.
- What happens when a user on mobile tries to drag-and-drop a file? → The drag target is suppressed on touch devices; a standard file picker button appears instead. All file types and size limits remain identical.
- What happens when the role self-identification doesn't match one of the four options (e.g., "I'm the receptionist")? → Vera maps it to the closest role ("Front desk — I'll set your first action as inviting the vets and getting the booking link ready") and confirms.

---

## Requirements *(mandatory)*

### Functional Requirements

**Phase 0 — Welcome**
- **FR-001**: The `/welcome` route MUST display Vera's introduction with no authentication gate, no email capture, and no form before the demo begins.
- **FR-002**: The introduction text MUST appear character-by-character at approximately 15ms/character with a user-accessible "skip" option.
- **FR-003**: A "Watch the demo →" button MUST appear after the introduction completes, initiating Phase 1.

**Phase 1 — Demo**
- **FR-004**: The demo MUST run using Harmony Animal Hospital's pre-seeded practice context (18 months of operational history, 3 providers, 4 rooms, active patient population).
- **FR-005**: The demo MUST complete within 8 minutes OR offer a "fast-forward" option; it MUST NOT run indefinitely without offering a pivot.
- **FR-006**: The demo log panel (right side) MUST display Vera's real-time actions in the `VERA (Module): action` format throughout the demo.

**Phase 2 — Pivot**
- **FR-007**: Upon demo completion, Vera MUST present the pivot message and a "Let's build it →" CTA without any intermediate form or account creation.

**Phase 2B — Role Identification**
- **FR-007a**: Immediately after the user clicks "Let's build it →", Vera MUST ask: "Are you the practice owner, or setting this up for the practice?" with four selectable options: Practice Owner / Practice Manager / Associate Vet / Setting this up for someone else.
- **FR-007b**: Vera MUST acknowledge the selected role conversationally before proceeding to Q1 (e.g., "Got it — I'll make sure the first things I show you are most useful for a Practice Manager.").
- **FR-007c**: The selected role MUST be stored in the OnboardingSession and used to determine post-Replace first-action targets (FR-032).

**Phase 3 — Open Prompt (Q1: Practice Name + Magic Link)**
- **FR-008**: Vera MUST ask for the practice name as a single text input. Upon submission, the live panel header MUST update to the practice name within 1 second.
- **FR-008a**: Immediately after the practice name is confirmed, Vera MUST offer to save progress via email: "Where should I send a link so you can pick this up on any device?" with options [Send me a link] and [Skip for now — I'll finish today].
- **FR-008b**: If the user provides an email, the system MUST send a magic link within 60 seconds. The magic link MUST resume the session from the exact saved state on any device and browser.
- **FR-008c**: The magic link MUST be valid for 30 days. No password is required to use it; password creation is deferred until billing activation.
- **FR-008d**: If the user skips the magic link, the session remains cookie-anchored. The offer MUST NOT be repeated more than once per session.
- **FR-009**: If the user includes city/state in the practice name input, Vera MUST extract both without asking separately for location.

**Phase 3 — Open Prompt (Q2: Tell Me About [Practice Name])**
- **FR-010**: Vera MUST present the open question with three sub-bullet suggestions (services, team, facilities) and three simultaneous input affordances: free text, file drop, and link paste.
- **FR-011**: The drag-target overlay MUST be active over the entire right panel whenever a file is being dragged over the browser window, regardless of cursor position.
- **FR-012**: Any URL pasted into the text input MUST be auto-detected as a link and routed to the web/maps scraping pipeline — not treated as text.
- **FR-013**: Free-text responses MUST be parsed for: practice type/species, provider names and count, room names and count, and working hours. Each extracted field MUST trigger a visible update in the live panel as it is confirmed.
- **FR-014**: After any response type, Vera MUST check for gaps and ask AT MOST two targeted follow-up questions before offering the file drop as the faster path.
- **FR-015**: The system MUST reach Phase 4 readiness with a minimum viable context of: practice name + at least 1 provider + at least 1 appointment type.

**Phase 3 — Logo Scraping**
- **FR-016**: When a website or Maps URL is provided, Vera MUST attempt logo extraction in parallel with data extraction using this cascade: `og:image` → `<link rel="icon">` → largest header/nav image → favicon (for website); business cover photo → gallery image (for Maps).
- **FR-017**: When a logo candidate is found, Vera MUST display it in BOTH the conversation thread and the live panel header simultaneously before asking confirmation.
- **FR-018**: The logo confirmation MUST always include three choices: [Yes, that's our logo] / [Try another] / [I'll upload mine]. It MUST NEVER be silently placed without explicit confirmation.
- **FR-019**: If no logo is found and the user declines to upload, Vera MUST generate a clean initials monogram and place it in the header.
- **FR-020**: A confirmed logo MUST survive the Phase 5 Replace animation unchanged — the Replace does not reset the logo.

**Phase 4 — Document Magic**
- **FR-021**: The document upload zone MUST accept: CSV, XLSX, XLS, PDF, DOC, DOCX, PNG, JPG, JPEG, WEBP, GIF, HEIC.
- **FR-021a**: The system MUST reject any file exceeding 25MB before upload begins, with the message: "That file is [X]MB — I can handle up to 25MB. Can you export a smaller version, or paste the key columns as text?"
- **FR-021b**: On touch/mobile devices, the drag-and-drop target MUST be replaced with a standard file picker button. All accepted formats and size limits remain identical.
- **FR-022**: For spreadsheet files, the extraction pipeline MUST support multi-tab documents and classify each tab's content type independently.
- **FR-022a**: Vera MUST begin streaming partial extraction results within 2 seconds of file receipt, narrating progress (e.g., "Found Staff tab — reading 5 providers...") rather than waiting for full extraction to complete.
- **FR-022b**: If extraction has not completed within 30 seconds, Vera MUST surface all results extracted so far, present them for confirmation, and continue background extraction — streaming additional results into the conversation as they complete.
- **FR-023**: Every extracted field MUST be presented with a confidence indicator (✅ high / ⚠️ medium / ❓ needs input) and the original source text available on request ("click to cite").
- **FR-024**: Fields with medium confidence MUST present inline confirmation options (buttons in the conversation thread) — NOT a separate form or modal.
- **FR-025**: No extracted data MUST be written to the practice database until the user explicitly confirms it.
- **FR-026**: User corrections to extracted fields MUST be logged as training signals with: document type, field name, Vera's value, correct value, and confidence at time of correction.
- **FR-027**: Vera's corrections response MUST be: "Got it — updating to [corrected value]." Never sycophantic affirmations.

**Phase 5 — Replace**
- **FR-028**: The Replace event MUST be explicitly triggered by the user clicking "Make it live →" or equivalent — never automatic.
- **FR-029**: The Replace animation MUST visibly dissolve demo clinic data (Harmony Animal Hospital) and replace it with the real practice data within 3 seconds.
- **FR-030**: After Replace, all subsequent Vera actions MUST operate on the real practice context — never the demo context.
- **FR-031**: The demo context MUST be archived (not deleted) for comparison and training purposes.

**Phase 6 — First Real Action**
- **FR-032**: After Replace, Vera MUST present role-appropriate first-action targets based on the role identified in FR-007a:
  - Practice Owner → "Share your booking link with clients"
  - Practice Manager → "Invite the vets to their accounts"
  - Associate Vet → "Book a test appointment to see how it feels"
  - Setting up for someone else → "Send [Practice Name]'s owner a link to review and activate"
- **FR-033**: The activation event (first real appointment booked by a real client) MUST be tracked and timestamped in the practice context.

**Session Persistence**
- **FR-034**: Onboarding session state MUST be persisted to the database on every phase transition.
- **FR-035**: A session anchored by magic link email MUST be resumable within 30 days from any device or browser. A cookie-only session MUST be resumable within 30 days from the same browser.
- **FR-036**: On resume (magic link or cookie), Vera MUST greet the user with their practice name and a summary of captured data — no re-entry required.
- **FR-036a**: A magic link MUST be single-use per session resume event. After use, a new magic link MUST be issued for the next resume if needed.

**Vera's Professional Boundaries**
- **FR-037**: After the Replace event, Vera MUST proactively introduce her professional boundaries (not a vet, not a lawyer) before describing operational capabilities.
- **FR-038**: When asked for a clinical opinion at any point, Vera MUST follow the three-step response: Acknowledge urgency → Redirect to licensed vet → Offer what she CAN do.
- **FR-039**: When responding to regulatory questions, Vera MUST cite the specific statute with jurisdiction, state what it requires, and defer compliance determination to the practice owner or qualified attorney.

**Vera's Voice**
- **FR-040**: Vera MUST NEVER use sycophantic affirmations ("Great!", "Awesome!", "Fantastic!") in any onboarding message.
- **FR-041**: Vera MUST NEVER say "As an AI language model..." or any equivalent AI disclaimer.
- **FR-042**: Every Vera message that describes an action she took MUST use first person active voice ("I sent", "I found", "I built") — never passive voice ("was sent", "was found").

---

### Key Entities

- **OnboardingSession**: Tracks the prospect from first visit through activation. Holds current phase, accumulated state JSON, track classification (greenfield/switcher/paper), session token, email anchor (optional, set when magic link provided), persona role (owner/manager/associate/proxy), and activation timestamp.
- **MagicLink**: A single-use time-limited token tied to an OnboardingSession. Holds hashed token, session ID, email address, expiry (30 days), used-at timestamp, and issuing device fingerprint.
- **VeraPracticeContext**: The practice's full operational model — initialized during onboarding, continuously updated in operation. Contains identity, services, team, facilities, schedule model, patient population, operational patterns, financial health, and Vera's performance metrics. This IS Vera's working memory, not a separate data store.
- **LogoAsset**: Scraped or uploaded logo with source, confirmation status, and fallback type (initials monogram vs. image).
- **OnboardingDocument**: An uploaded file in staging — not committed to the live database until confirmed. Holds mime type, file size, storage path, classified type, extraction JSON, and streaming status (in-progress / complete / timed-out).
- **ExtractedEntity**: A single structured record parsed from a document. Holds entity type, source text, source position (for click-to-cite), confidence score, extracted fields, conflicts, and requires-input flags.
- **ExtractionCorrection**: A training signal logged when a user corrects Vera's extraction. Holds document type, field name, Vera's value, correct value, and confidence at correction.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 45% or more of visitors who watch the demo click "Let's build it →" (demo-to-pivot conversion).
- **SC-002**: 95% or more of users who click "Let's build it →" successfully submit an answer to the open prompt (Q1 + Q2 completion).
- **SC-003**: 60% or more of onboarding sessions include at least one file upload or link paste (document magic engagement).
- **SC-004**: 80% or more of document extractions are confirmed without any corrections (extraction accuracy target).
- **SC-005**: 70% or more of users who submit the open prompt reach the Replace step (Phase 5 completion).
- **SC-006**: 40% or more of practices that complete the Replace step book their first real client appointment within 7 days (activation rate).
- **SC-007**: The complete onboarding journey from `/welcome` to a live practice MUST be completable in under 20 minutes for a typical small animal practice (2–4 vets, 3–5 rooms).
- **SC-008**: Session resume rate — 60% or more of users who drop off mid-session return and complete within 30 days (persistence effectiveness).
- **SC-009**: Logo extraction finds a usable candidate (confirmed or user-accepted monogram) in 95% or more of sessions where a URL is provided.
- **SC-010**: Zero instances of Vera silently placing a logo without explicit user confirmation (logo confirmation compliance — must be 100%).
- **SC-011**: Document extraction streaming MUST begin (first partial result visible) within 2 seconds of file receipt in 99% or more of uploads under 25MB.
- **SC-012**: Magic link email MUST be delivered within 60 seconds of the user providing their email address in 95% or more of cases.
- **SC-013**: Magic link resume MUST restore full session state (practice name, role, captured data) correctly in 99% or more of link clicks within the 30-day window.
- **SC-014**: The onboarding layout on mobile (screen width < 768px) MUST achieve a task-completion rate within 10 percentage points of the desktop rate for the same flows.

---

## Assumptions

- The demo clinic (Harmony Animal Hospital) context is fully pre-seeded and maintained as a static fixture — it is not dynamically generated per session.
- Session identity is anchored by magic link email (provided after Q1) or browser cookie (if skipped). Cookie-only sessions are portable within the same browser for 30 days; email-anchored sessions are portable across any device for 30 days. No password is required until billing activation.
- Google Maps scraping uses the Maps public API or structured data extraction — not browser automation. If the Maps API is unavailable, the link paste path degrades gracefully to the manual free-text path.
- Website logo scraping is best-effort and runs server-side; client-side CORS restrictions do not apply.
- The Vera Constitution (Chief of Staff persona, clinical boundary, legal boundary) governs all onboarding dialogue — the VERA_PROFESSIONAL_BOUNDARIES system prompt fragment is wired into every agent module that processes onboarding conversation.
- Document extraction for Phase 1 launch prioritizes: staff roster CSV/XLSX (P0), state veterinary license PDF (P0), appointment schedule CSV/XLSX (P0), PIMS export CSV (P1). Handwritten photo OCR is Phase 2.
- Session persistence uses server-side storage (database), not browser localStorage — so resume works across devices and browsers for email-anchored sessions.
- The onboarding UI is fully responsive. The two-panel layout (65% live panel / 35% conversation) collapses to a tabbed single-column layout on screens narrower than 768px. File drag-and-drop is replaced with a file picker button on touch devices.
- Multi-location practices (5+ locations) go through the same flow per location; the first location is the primary. Additional locations are noted as "coming soon" and queued for a follow-up session.
- The activation event is defined as: first appointment booked by a real client (not a test booking) and confirmed through VetAgent's system. This is the primary business KPI for onboarding success.
- The VetAgent booking portal (S07) is implemented and operational — it is the target for the "first real appointment" activation event.
- The four onboarding persona roles (Practice Owner, Practice Manager, Associate Vet, Setting up for someone else) are self-reported and not verified. They are used only to personalize post-Replace first-action targets.
