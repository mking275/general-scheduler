# Feature Specification: General Scheduler Prototype

**Feature Branch**: `[001-general-scheduler]`  
**Created**: 2026-06-18  
**Status**: Draft  
**Input**: User description: "Neuro-Symbolic Agentic Scheduler Prototype for the Veterinary Industry with Next.js frontend"

## Clarifications

### Session 2026-06-18
- Q: Should the mock login flow differentiate between user roles, or just provide a single generic entry point? → A: Single generic user role (keep it simple).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Natural Language Scheduling (Priority: P1)

A veterinary clinic owner or front-desk worker wants to schedule an emergency surgery by simply typing a natural language request (e.g., "Need an emergency surgery for a Golden Retriever") into the system, so they don't have to navigate complex calendars manually.

**Why this priority**: Core value proposition of the agentic AI workflow. Eliminates the "calendar Tetris" problem for end users.

**Independent Test**: Can be fully tested by submitting a text string to the Intake Agent and verifying it parses intent and outputs a valid TimeBlock.

**Acceptance Scenarios**:

1. **Given** a mocked schedule with available Vets and Rooms, **When** the user inputs "Book Dr. Smith for surgery at 2pm", **Then** the system parses the request and successfully schedules the TimeBlock.
2. **Given** an invalid or conflicting request, **When** the user inputs "Book Dr. Smith" but Dr. Smith is busy, **Then** the system detects the conflict via the Constraints Solver and suggests the next available slot or another qualified Vet.

---

### User Story 2 - Verbose Demonstration Mode (Priority: P2)

A potential buyer wants to see *how* the AI makes its decisions (Intake -> Vector Match -> Constraint Solve -> Dispatch) in a dedicated UI panel, so they can trust the Neuro-Symbolic engine rather than treating it as a black box.

**Why this priority**: Crucial for demonstrating the product to stakeholders and building trust in the AI's reliability.

**Independent Test**: Can be fully tested by submitting any request and verifying that the real-time log panel populates with the 4 distinct thought process steps.

**Acceptance Scenarios**:

1. **Given** a natural language request, **When** the scheduling pipeline processes it, **Then** the Verbose Mode panel displays the exact output of the Intake Agent, the ranked Semantic Matcher results, and the Solver's validation steps.

---

### Edge Cases

- What happens when a user requests an emergency appointment but no qualified Vet is available? (System must gracefully propose alternative times or refer to an emergency hospital).
- How does the system handle ambiguous language? (e.g., "Book the dog in" without specifying which dog or what procedure). The Intake Agent should formulate a response asking for clarification.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST parse unstructured natural language requests into a structured `Job` entity.
- **FR-002**: System MUST rank candidate Vets using a Semantic Matcher to satisfy soft constraints (e.g., Vet preferences).
- **FR-003**: System MUST validate hard constraints (Skills, Availability, Rooms) using a rules-based Heuristic Engine.
- **FR-004**: System MUST persist and retrieve schedule data from memory.
- **FR-005**: System MUST provide a publicly accessible, interactive frontend with premium micro-animations (maintaining 60fps).
- **FR-006**: System MUST simulate a mock login flow for demonstration purposes, providing a single generic user role without complex permission states.

### Key Entities

- **Request**: The raw unstructured string from the user and tracking ID.
- **Job**: The parsed intent containing `required_skills`, `estimated_duration`, and `soft_requirements`.
- **Resource**: The actors (Vets) and assets (Exam Rooms) that fulfill Jobs. Contains `availability_windows` and `hard_skills`.
- **TimeBlock**: The final binding of a Job to Resources over a specific start and end time.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Intake Agent parses complex requests into valid attributes with >95% accuracy.
- **SC-002**: System resolves a standard schedule (e.g., 5 Vets, 3 Rooms, 20 Appointments) in under 1 second without double-booking.
- **SC-003**: Frontend Verbose Demonstration Mode updates within 2 seconds of the user submitting a request, clearly visualizing all pipeline stages.
- **SC-004**: System can be deployed and accessed publicly via URL (e.g., Vercel) for client demos.
