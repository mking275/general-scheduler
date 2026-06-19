# Feature Specification: Multi-Clinic Foundation

**Feature Branch**: `003-multi-clinic-foundation`  
**Created**: 2026-06-19  
**Status**: Draft  
**Input**: User description: "Multi-clinic operations support — allow the scheduler to manage multiple physical clinic locations with shared patient records, floating vets, per-location schedule boards, and a Regional Manager aggregate view. Schema must be clinic-aware before further features are built."

## Assumptions

- Phase 2 (F001–F006) is complete. All existing tables (`resources`, `timeblocks`, `patients`) exist and are populated with seed data.
- F007 is a schema-first feature — clinic context is added as a migration layer, not a rewrite.
- Demo scope: exactly 2 mock clinics. No limit is implied for production.
- No real access control or data isolation enforcement — role switching remains a UI-level toggle.
- All appointment times are displayed in local browser timezone; no multi-timezone conversion logic is required.
- "Floating vet" availability is declared by day-of-week, not by individual date, for demo simplicity.
- Patient records are globally readable across all clinics; there is no per-clinic data silo.

---

## Clarifications

### Session 2026-06-19

- Q: Which clinic is shown by default on first load when multiple clinics exist? → A: The alphabetically first clinic by name (deterministic, zero-config). Users switch immediately via the location switcher.
- Q: What is the single canonical term for a physical practice location? → A: "clinic" — used consistently across spec, code, UI, and API. Terms "location" and "site" are retired.
- Q: When a vet's clinic assignment is removed, what happens to their existing booked appointments there? → A: Existing appointments are preserved and honoured; only new bookings at that clinic are blocked.
- Q: What does the Regional Manager view show for a clinic column with zero appointments today? → A: Column remains visible showing clinic name, 0% utilisation, and a "No appointments today" placeholder message.
- Q: How specific should the conflict message be when a floating vet is double-booked across clinics? → A: Specific — name the blocking clinic and suggest the next available date at the requested clinic (e.g. "Dr. Chen is at Downtown today — next available at Westside is Tuesday").

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Clinic-Aware Schedule Board (Priority: P1)

A front desk worker at a multi-location practice opens the app and immediately knows which clinic's schedule they are viewing. They can switch to another location and see that clinic's rooms, vets, and appointments without reloading the page.

**Why this priority**: Every other multi-clinic feature depends on the location context being established first. Without a working location switcher and clinic-filtered data, no other multi-clinic story can be tested independently.

**Independent Test**: With 2 seeded clinics and appointments at each, open the app. Verify the header shows the default clinic name. Switch location. Verify the schedule board shows only that clinic's rooms and appointments. Switch back. Verify the original clinic's data re-appears.

**Acceptance Scenarios**:

1. **Given** 2 clinics exist, **When** the app loads, **Then** the header displays the default clinic name and a location switcher dropdown is visible.
2. **Given** the user selects a different clinic from the switcher, **When** the selection is confirmed, **Then** the schedule board re-renders showing only that clinic's vets, rooms, and appointments within 1 second.
3. **Given** the user is viewing Clinic B, **When** they book a new appointment, **Then** the appointment is saved with Clinic B's `clinic_id` and does not appear in Clinic A's schedule board.
4. **Given** the user switches clinics, **When** the schedule board updates, **Then** the header colour accent changes to reflect the newly selected clinic's brand colour.

---

### User Story 2 — Floating Vet Scheduling (Priority: P1)

A front desk worker booking an appointment at a clinic can only see and book vets who are assigned to work at that clinic. A floating vet appears as available at whichever clinic is assigned to them for that day.

**Why this priority**: Without this, multi-clinic scheduling produces nonsensical results — a vet booked at two places at once, or a vet not appearing at the clinic where they're actually working that day.

**Independent Test**: Seed one floating vet assigned to Clinic A on Mondays and Clinic B on Tuesdays. On a Monday, switch to Clinic A — verify the floating vet appears as bookable. Switch to Clinic B — verify the floating vet does not appear as bookable on Monday. On a Tuesday, reverse should be true.

**Acceptance Scenarios**:

1. **Given** a vet is assigned to Clinic A on Monday and Clinic B on Tuesday, **When** a user books on a Monday at Clinic A, **Then** the vet appears in the list of available resources.
2. **Given** the same vet above, **When** a user books on a Monday at Clinic B, **Then** the vet does not appear as available (they are at Clinic A today).
3. **Given** a floating vet is assigned to the currently viewed clinic, **When** their appointment card is displayed, **Then** a "visiting" indicator is shown if the clinic is not their primary location.
4. **Given** a booking request specifies a floating vet by name at the wrong clinic for that day, **When** the constraint solver evaluates it, **Then** the system rejects the booking and suggests the correct clinic or next available date.

---

### User Story 3 — Cross-Clinic Patient Records (Priority: P1)

When a patient is seen at any clinic, their full medical history — SOAP notes, intake briefs, visit count — is visible to the attending vet regardless of which clinic originally created those records.

**Why this priority**: Patient safety. A vet walking into an exam at Clinic B must know the patient has an allergy documented at Clinic A. Siloed records are a clinical risk and a major pain point in current multi-location practices.

**Independent Test**: Create a patient with a SOAP note at Clinic A. Switch to Clinic B and book the same patient. Open the appointment card at Clinic B. Verify the full patient history including the Clinic A SOAP note is visible, with a "home clinic" indicator shown.

**Acceptance Scenarios**:

1. **Given** a patient's home clinic is Clinic A, **When** they are booked at Clinic B, **Then** their appointment card at Clinic B shows their complete history including records from Clinic A.
2. **Given** a patient has records from multiple clinics, **When** the vet opens the SOAP workspace, **Then** the Subjective section pre-fill uses the most recent intake brief regardless of which clinic it came from.
3. **Given** a patient's home clinic differs from the current clinic, **When** their appointment card is displayed, **Then** a banner shows: "Home clinic: [Clinic A name]. Viewing full cross-location history."
4. **Given** a search for patients at Clinic B, **When** the patient list is retrieved, **Then** patients from all clinics are returned (no clinic filter on the patient search endpoint).

---

### User Story 4 — Regional Manager Aggregate View (Priority: P2)

A regional manager can switch to a special view that shows all clinic locations side by side — their appointment counts, utilisation rates, and high-risk appointment flags — so they can identify which location needs attention today without drilling into each one individually.

**Why this priority**: This is the primary demo differentiator for the corporate buyer segment. No existing SMB vet software offers a real-time multi-location ops view. It turns a feature into a strategic selling point.

**Independent Test**: Switch to Regional Manager role. Verify a side-by-side column layout appears, one column per clinic, each showing today's appointment count, a utilisation percentage, and a count of high-risk appointments. Verify clicking a column navigates into that clinic's full schedule.

**Acceptance Scenarios**:

1. **Given** the user selects Regional Manager role, **When** the view renders, **Then** one column per clinic is displayed side by side, each labelled with the clinic name and colour accent.
2. **Given** each clinic column is rendered, **When** the data loads, **Then** each column shows: today's total appointments, utilisation % (booked slots / total available slots), and count of high-risk appointments.
3. **Given** the Regional Manager view is active, **When** the user clicks on a clinic column, **Then** the view drills into that clinic's full schedule board (equivalent to selecting that clinic in the location switcher).
4. **Given** the Regional Manager view is active, **When** a high-risk appointment count is greater than zero, **Then** the count is displayed in red to signal attention needed.
5. **Given** a clinic has zero appointments today, **When** the Regional Manager view renders, **Then** that clinic's column remains visible and shows "No appointments today" as a placeholder alongside a 0% utilisation figure.

---

### Edge Cases

- What if a floating vet has no clinic assignment for today's day-of-week? → They do not appear as available at any clinic for booking today. Their existing appointments remain visible.
- What if a floating vet's clinic assignment is removed? → All existing appointments at that clinic are preserved and honoured. The vet no longer appears as bookable at that clinic for new appointments.
- What if a patient has no home clinic set (legacy record)? → Treat as belonging to the default (alphabetically first) clinic. No banner is shown.
- What if only one clinic exists in the system? → The location switcher is hidden. All behaviour reverts to single-clinic mode.
- What if a booking request does not specify a clinic? → Default to the user's currently selected clinic context.
- What if the Regional Manager view is accessed when only one clinic exists? → Show the single clinic column with a note: "Add a second location to unlock multi-clinic reporting."
- What if a floating vet is double-booked at two clinics on the same day (data integrity error)? → The constraint solver rejects the second booking with a specific message naming the blocking clinic and suggesting the next available date at the requested clinic.

---

## Requirements *(mandatory)*

### Functional Requirements

**F007a — Clinic Entity & Schema**
- **FR-001**: The system MUST store clinic records with: name, address, phone, email, timezone, and brand colour.
- **FR-002**: The system MUST associate every Resource (Vet and Room) with a primary clinic.
- **FR-003**: The system MUST associate every TimeBlock with the clinic where it takes place.
- **FR-004**: The system MUST store a `home_clinic_id` on every Patient record.
- **FR-005**: The system MUST seed exactly 2 mock clinics with at least 2 vets and 2 rooms each.

**F007b — Location Switcher**
- **FR-006**: The system MUST display a location switcher in the dashboard header showing the currently selected clinic. On first load, the default selected clinic MUST be the clinic whose name is first alphabetically.
- **FR-007**: Switching clinic context MUST filter the schedule board, room board, and vet list to the selected clinic within 1 second.
- **FR-008**: The header MUST apply the selected clinic's brand colour as a visual accent.
- **FR-009**: When only one clinic exists, the location switcher MUST be hidden.

**F007c — Floating Vets**
- **FR-010**: The system MUST support assigning a vet to one or more clinics with associated days-of-week per clinic. When an assignment is removed, all previously booked appointments at that clinic MUST be preserved; only new booking attempts for that vet at that clinic MUST be blocked.
- **FR-011**: The scheduling constraint solver MUST only offer vets who are assigned to the currently selected clinic on the day of the requested appointment.
- **FR-012**: A floating vet's appointment card MUST display a "visiting" indicator when viewed at a non-primary clinic.
- **FR-013**: Attempting to book a floating vet at a clinic they are not assigned to on that day MUST return a specific conflict message that names the clinic they are assigned to that day AND states the next available date at the requested clinic (e.g. "Dr. Chen is at [Clinic A] today — next available at [Clinic B] is [date]").

**F007d — Cross-Clinic Patient Records**
- **FR-014**: Patient lookup MUST search across all clinics, not filtered by selected clinic context.
- **FR-015**: A patient appointment card viewed at a non-home clinic MUST display a "Home clinic: [name]" banner.
- **FR-016**: The SOAP workspace Subjective pre-fill MUST use the most recent intake brief from any clinic.

**F007e — Regional Manager View**
- **FR-017**: The Regional Manager role MUST render a side-by-side aggregate dashboard, one column per clinic. Clinic columns MUST always be shown, even if a clinic has zero appointments; those columns display a "No appointments today" placeholder and 0% utilisation.
- **FR-018**: Each clinic column MUST display: clinic name, today's appointment count, utilisation percentage, and high-risk appointment count.
- **FR-019**: Clicking a clinic column MUST navigate into that clinic's full schedule in Front Desk view.
- **FR-020**: High-risk appointment counts greater than zero MUST be visually highlighted in red.

### Key Entities

- **Clinic**: Name, address, phone, email, timezone, brand colour hex, active status.
- **VetClinicAssignment**: Junction between a Vet (Resource) and a Clinic. Carries `schedule_days[]` (days of week) and `is_primary` flag.
- **Resource** (extended): gains `clinic_id` (primary clinic) and `float_clinic_ids[]` (derived from VetClinicAssignment).
- **TimeBlock** (extended): gains `clinic_id`.
- **Patient** (extended): gains `home_clinic_id`.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A demo operator can switch between 2 clinic locations and have the schedule board fully re-render with correct data in under 1 second.
- **SC-002**: Booking an appointment at Clinic B with a floating vet who is only assigned to Clinic A on that day is rejected by the system with a clear alternative suggestion, not silently accepted.
- **SC-003**: A patient's full history from Clinic A is visible when their appointment is opened at Clinic B, with the home clinic banner displayed.
- **SC-004**: The Regional Manager view renders a side-by-side dashboard for all clinics within 2 seconds of role selection.
- **SC-005**: When only one clinic is seeded, zero multi-clinic UI elements appear — the app behaves identically to the Phase 2 single-clinic demo.
- **SC-006**: The entire F007 feature operates correctly on top of the Phase 2 seeded dataset without requiring a database wipe or manual migration step.
