# Feature Specification: Vet Clinic Agentic Features — Phase 2

**Feature Branch**: `002-vet-agentic-features`  
**Created**: 2026-06-19  
**Status**: Draft  
**Input**: User description: "Phase 2 agentic features for the vet clinic scheduler demo: Patient Record Cards on appointments, Pre-Visit Intake Agent, Post-Appointment Follow-Up Agent, No-Show Risk Indicator, Role-Split UI (Front Desk / Vet Tech / Vet), and SOAP Note Draft Agent"

## Assumptions

- The system already has a working appointment scheduler (Phase 1) with Vets, Rooms, and TimeBlocks persisted in SQLite.
- Demo mode: no real SMS/email sending. All outbound communication is simulated within the UI.
- No real authentication/RBAC — role switching is a UI-level toggle for demo purposes.
- Patient and owner records are seeded mock data; no real patient import.
- SOAP notes are template-driven (procedure-based), not live audio transcription, for the demo scope.
- Risk scoring is rule-based (no ML model) for demo scope.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Patient Context at a Glance (Priority: P1)

A front desk worker opens the schedule board and immediately sees who is coming in — the patient's name, species, breed, flagged conditions, and owner contact — without opening any secondary system.

**Why this priority**: Foundational to all other Phase 2 features. Every other feature (intake, SOAP, follow-up) attaches to a patient record. Also the quickest visible improvement to the current demo.

**Independent Test**: Seed mock patient data. Book an appointment. Verify the appointment card renders the patient name, species icon, flag badges, and owner phone number without any additional clicks.

**Acceptance Scenarios**:

1. **Given** an appointment exists for a patient with an allergy flag, **When** the schedule board loads, **Then** the appointment card displays the patient name, breed, a red ALERT badge, and the owner's name.
2. **Given** an appointment for a first-time patient, **When** the card is rendered, **Then** a green FIRST VISIT badge is shown and no prior visit history is displayed.
3. **Given** an appointment card, **When** the user clicks to expand it, **Then** the patient's last visit date, last procedure, weight, and owner phone number are visible.

---

### User Story 2 — Pre-Visit Intake Agent (Priority: P1)

After an appointment is booked, the system automatically sends a pre-visit questionnaire to the pet owner. The owner's natural-language reply is parsed by the agent into a structured Pre-Exam Brief, which the vet can read before entering the exam room.

**Why this priority**: Directly addresses the two highest-ranked pain points from research — front desk phone burden and vets walking into exams without context. Highest "wow" factor for demo audiences.

**Independent Test**: Book an appointment. Trigger the intake flow. Enter a mock owner response ("He's been lethargic for 3 days and not eating"). Verify a structured Pre-Exam Brief appears on the appointment card with extracted symptoms, duration, and severity.

**Acceptance Scenarios**:

1. **Given** a newly booked appointment, **When** the intake agent is triggered, **Then** a simulated outbound questionnaire is logged in the Verbose panel and an "Intake: Pending" badge appears on the card.
2. **Given** the operator submits a mock owner response, **When** the Symptom Extraction Agent processes it, **Then** symptoms, duration, and severity are extracted and displayed in the Pre-Exam Brief panel.
3. **Given** a Pre-Exam Brief exists, **When** the vet opens their appointment view, **Then** the chief complaint and suggested focus areas are the first things visible.
4. **Given** an owner response containing no clear symptoms (e.g., "just a checkup"), **When** parsed, **Then** the brief notes "No specific concerns reported — routine visit" and no false symptoms are invented.

---

### User Story 3 — No-Show Risk Indicator (Priority: P2)

Each appointment card displays a colour-coded risk indicator. Hovering it reveals the specific factors that contributed to the risk score so the front desk can decide whether to make a proactive confirmation call.

**Why this priority**: Low build effort, high demo impact. Directly addresses the no-show revenue loss pain point from research. Adds immediate perceived intelligence to the schedule board.

**Independent Test**: Book appointments with different characteristics (same-day vs. 1 week out, wellness vs. emergency, first visit vs. returning). Verify each receives a different risk level and that hovering the indicator lists the contributing factors.

**Acceptance Scenarios**:

1. **Given** a same-day appointment for a first-time patient for a wellness procedure, **When** the card renders, **Then** a red HIGH risk indicator is shown.
2. **Given** an appointment booked 5 days in advance for an established patient for an emergency, **When** the card renders, **Then** a green LOW risk indicator is shown.
3. **Given** any risk indicator, **When** the user hovers it, **Then** a tooltip lists 2–4 specific contributing factors in plain English.

---

### User Story 4 — Role-Split UI (Priority: P2)

A role toggle in the dashboard header switches the entire view between Front Desk, Vet Tech, and Veterinarian perspectives. Each role sees a layout and action set optimised for their actual job — not a one-size-fits-all calendar.

**Why this priority**: Research finding that workflows designed for one role create bottlenecks for others. Demonstrates that the system understands clinical operations, not just scheduling. Differentiator from every incumbent PIMS.

**Independent Test**: Toggle to each of the three roles. Verify that: Front Desk shows the booking input and client communication queue; Vet Tech shows the room status board with prep states; Vet shows their personal appointment list with SOAP note access.

**Acceptance Scenarios**:

1. **Given** the user is in Front Desk view, **When** the dashboard loads, **Then** the primary panel shows today's appointment list with booking input, intake status badges, and follow-up approval queue.
2. **Given** the user switches to Vet Tech view, **When** the view renders, **Then** a room-by-room status board is shown, each room displaying its current state (Available / Prep / Occupied / Cleaning) and the next patient's procedure.
3. **Given** the user switches to Vet view, **When** the view renders, **Then** only their own appointments are listed, each with the Pre-Exam Brief accessible and a "Open SOAP Note" action.
4. **Given** the user marks a room as "Ready" in Vet Tech view, **When** they switch back to Front Desk view, **Then** the updated room status is reflected on the appointment card upon rendering the Front Desk view (fetched on role switch; real-time push not required for demo scope).

---

### User Story 5 — Post-Appointment Follow-Up Agent (Priority: P3)

When a vet marks an appointment as complete, the system instantly drafts a plain-English follow-up message tailored to the visit type and findings. The vet or front desk reviews the draft and approves it with one click.

**Why this priority**: Completes the full agentic loop (intake → visit → discharge). High emotional impact in demos — shows AI doing real clinical communication work, not just scheduling.

**Independent Test**: Mark an appointment as complete. Verify a follow-up draft is generated within 2 seconds, contains the correct patient name, procedure context, and care instructions matching the visit type. Verify tone changes between a wellness visit and a surgery.

**Acceptance Scenarios**:

1. **Given** a completed wellness appointment, **When** the follow-up draft is generated, **Then** the message is warm in tone, confirms the pet is healthy, and includes standard wellness reminders.
2. **Given** a completed surgery appointment, **When** the follow-up draft is generated, **Then** the message includes post-operative care instructions, warning signs to watch for, and a recheck recommendation.
3. **Given** a generated draft, **When** the user clicks "Approve & Send", **Then** the appointment card shows "Follow-up: Sent" and the Verbose Log records the action.
4. **Given** a generated draft, **When** the user clicks "Regenerate", **Then** a new draft is produced with different phrasing but the same core content.

---

### User Story 6 — SOAP Note Draft Agent (Priority: P3)

When a vet opens an appointment, a structured SOAP note is pre-drafted based on the procedure type and pre-exam brief. The vet fills in vitals and confirms the assessment rather than typing from scratch.

**Why this priority**: Addresses the #1 burnout driver in veterinary medicine (post-shift charting). Highest long-term commercial value of all Phase 2 features. Requires F001 and F002 to be meaningful.

**Independent Test**: Open an appointment with a Pre-Exam Brief. Open the SOAP workspace. Verify the Subjective section contains the extracted intake symptoms, the Objective section has a procedure-appropriate vitals form, and the Plan section has auto-suggested follow-up recommendations.

**Acceptance Scenarios**:

1. **Given** an appointment with a Pre-Exam Brief, **When** the vet opens the SOAP workspace, **Then** the Subjective section is pre-filled with the chief complaint and owner's own words (quoted).
2. **Given** a surgery appointment, **When** the SOAP draft is generated, **Then** the Objective section includes surgery-specific fields (pre-op weight, anaesthesia notes) and the Plan includes post-op care recommendations.
3. **Given** a wellness appointment, **When** the SOAP draft is generated, **Then** the Objective section includes a standard physical exam checklist and the Plan includes standard vaccination schedule reminders.
4. **Given** the vet clicks "Sign & Complete", **When** the action is processed, **Then** the appointment status changes to Complete and the Follow-Up draft (F003) is automatically triggered.
5. **Given** the SOAP note is signed, **When** the vet tries to edit it, **Then** the note is read-only with a clear "Signed" timestamp displayed.

---

### Edge Cases

- What if intake is triggered but the owner never responds? → Brief shows "No response received — proceed without intake data." Appointment remains bookable.
- What if a patient has no prior records (first visit)? → All history fields show "No record on file." SOAP Subjective relies entirely on intake response.
- What if the vet marks complete without signing the SOAP note? → System warns "SOAP note unsigned" but allows completion with a confirmation step.
- What if two staff members are viewing the same room status board simultaneously and one changes a room state? → Last write wins; no real-time sync required for demo scope.
- What if the follow-up draft is approved but the appointment type has no template? → A generic "Thank you for visiting" template is used as fallback.
- What if risk scoring receives an appointment with no patient history (new patient)? → Score defaults to Medium, with "New patient — no history available" as a factor.

---

## Requirements *(mandatory)*

### Functional Requirements

**F001 — Patient Record Card**
- **FR-001**: The system MUST display patient name, species, breed, and age on every appointment card.
- **FR-002**: The system MUST show colour-coded flag badges (Alert, Chronic, First Visit) based on patient record data.
- **FR-003**: The system MUST display the owner's name and phone number on the expanded appointment card.
- **FR-004**: The system MUST seed a minimum of 8 mock patients with varied species, breeds, flags, and visit histories.

**F002 — Pre-Visit Intake Agent**
- **FR-005**: The system MUST allow a user to trigger an intake questionnaire from any booked appointment card.
- **FR-006**: The system MUST accept a free-text mock owner response and extract structured symptom data from it.
- **FR-007**: The system MUST generate a Pre-Exam Brief containing: chief complaint, symptom list with duration, severity, and owner's verbatim words.
- **FR-008**: The system MUST display the intake status (Pending / Received / Not Started) on every appointment card.
- **FR-009**: The Verbose Log MUST show each step of the intake extraction pipeline.

**F003 — Post-Appointment Follow-Up Agent**
- **FR-010**: The system MUST provide a "Mark Complete" action on every appointment card.
- **FR-011**: Upon completion, the system MUST auto-generate a follow-up message draft within 3 seconds.
- **FR-012**: The draft MUST be editable before approval.
- **FR-013**: The system MUST provide at least 3 distinct tone/template variants (Wellness, Surgery, Emergency).
- **FR-014**: The system MUST track follow-up status per appointment (Not Started / Draft / Sent).

**F004 — No-Show Risk Indicator**
- **FR-015**: The system MUST calculate and display a risk level (Low / Medium / High) on every appointment card at booking time.
- **FR-016**: The risk calculation MUST consider at minimum: booking lead time, visit type, and new vs. returning patient status.
- **FR-017**: The system MUST display a human-readable list of contributing factors when the indicator is hovered or clicked.

**F005 — Role-Split UI**
- **FR-018**: The system MUST provide a role selector with three options: Front Desk, Vet Tech, Veterinarian.
- **FR-019**: Each role MUST have a distinct primary layout and action set.
- **FR-020**: The Vet Tech view MUST display a room-by-room status board with at least 4 room states.
- **FR-021**: Room status changes in the Vet Tech view MUST be reflected in the Front Desk view without a page reload.
- **FR-022**: Role selection MUST persist within the session (not reset on page interaction).

**F006 — SOAP Note Draft Agent**
- **FR-023**: The system MUST provide a SOAP note workspace accessible from the Vet role view.
- **FR-024**: The Subjective section MUST be pre-populated from the Pre-Exam Brief if one exists.
- **FR-025**: The Objective section MUST render a procedure-appropriate vitals and exam checklist.
- **FR-026**: The Plan section MUST include auto-suggested follow-up recommendations based on procedure type.
- **FR-027**: Signing the SOAP note MUST trigger the Follow-Up draft generation (FR-011).
- **FR-028**: Signed SOAP notes MUST be read-only.

### Key Entities

- **Patient**: Name, species, breed, date of birth, weight, medical flags, owner reference, visit history.
- **Owner**: Name, phone, email, linked patients.
- **PreExamBrief**: Chief complaint, extracted symptoms (with duration and severity), owner verbatim quote, suggested focus areas. Linked to one TimeBlock.
- **RiskScore**: Risk level, numeric score, contributing factor list. Linked to one TimeBlock.
- **SoapNote**: Subjective, Objective (vitals + exam findings), Assessment, Plan. Linked to one TimeBlock. Carries signed status and timestamp.
- **FollowUpDraft**: Generated message body, tone variant, approval status, linked to one TimeBlock.
- **RoomStatus**: Room identifier, current state (available / prep / occupied / cleaning), linked to the current TimeBlock if occupied.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A demo operator can take a viewer from "empty schedule board" to a fully enriched appointment with intake brief, risk score, and SOAP draft in under 4 minutes of interaction.
- **SC-002**: Patient context (name, species, flags) appears on every appointment card within 1 second of the schedule board loading.
- **SC-003**: Submitting a mock owner intake response produces a structured Pre-Exam Brief in under 2 seconds.
- **SC-004**: Switching between all three role views takes under 500ms with no full page reload.
- **SC-005**: A SOAP note draft appropriate to the procedure type is generated in under 2 seconds of opening the workspace.
- **SC-006**: A follow-up message draft is generated and displayed within 3 seconds of marking an appointment complete.
- **SC-007**: The Verbose Log captures and displays every agent action for F002, F003, and F006, with no pipeline step invisible to the viewer.
- **SC-008**: All six features operate correctly on the existing mock dataset of 8+ patients and 3 vets without data conflicts.
