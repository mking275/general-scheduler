# API Contracts: Vet Clinic Agentic Features — Phase 2

Base URL: `http://localhost:8080` (dev) / tunnel URL (demo)

---

## F001 — Patient & Owner Endpoints

### GET /api/patients
Returns all patients with owner summary.
```json
[{
  "id": "uuid",
  "name": "Buddy",
  "species": "dog",
  "breed": "Golden Retriever",
  "dob": "2019-03-14",
  "weight_kg": 28.5,
  "flags": ["alert"],
  "flag_notes": "Allergic to penicillin",
  "owner": { "id": "uuid", "name": "Sarah M.", "phone": "(503) 555-0142" },
  "visit_count": 7,
  "last_visit_date": "2026-04-10",
  "last_visit_procedure": "Annual Wellness"
}]
```

### GET /api/patients/{id}
Returns single patient with full owner detail.

### POST /api/patients
Create a new patient record.
```json
// Request
{ "name": "Whiskers", "species": "cat", "breed": "Siamese",
  "dob": "2021-06-01", "weight_kg": 4.2, "flags": ["first_visit"],
  "owner_id": "uuid" }
// Response: 201 Created — full patient object
```

### GET /api/owners
Returns all owners with linked patient IDs.

---

## F002 — Pre-Visit Intake Endpoints

### POST /api/intake/send
Trigger the pre-visit questionnaire for an appointment (mocked — instantly logs action).
```json
// Request
{ "timeblock_id": "uuid" }
// Response: 200
{ "status": "pending", "message": "Questionnaire sent to owner (simulated)" }
```

### POST /api/intake/parse
Submit a mock owner response and get a structured Pre-Exam Brief back.
```json
// Request
{ "timeblock_id": "uuid", "owner_response": "He's been lethargic for 3 days and not eating" }
// Response: 200
{
  "timeblock_id": "uuid",
  "chief_complaint": "Lethargy and reduced appetite",
  "symptoms": [
    { "name": "lethargy", "duration_days": 3, "severity": "mild" },
    { "name": "anorexia", "duration_days": 2, "severity": "mild" }
  ],
  "owner_verbatim": "He's been lethargic for 3 days and not eating",
  "suggested_focus": ["GI", "metabolic panel"],
  "status": "received"
}
```

### GET /api/intake/{timeblock_id}
Returns the PreExamBrief for a timeblock, or `{ "status": "not_started" }`.

---

## F003 — Follow-Up Draft Endpoints

### POST /api/followup/draft
Auto-generate a follow-up message draft (triggered by appointment completion).
```json
// Request
{ "timeblock_id": "uuid" }
// Response: 200
{
  "id": "uuid",
  "subject": "Buddy's Visit Summary — Dr. Smith",
  "body": "Hi Sarah, great to see Buddy today!...",
  "tone": "wellness",
  "status": "draft"
}
```

### PUT /api/followup/{id}
Update draft body/tone before approval.
```json
// Request: { "body": "edited text", "tone": "wellness" }
// Response: 200 — updated draft object
```

### POST /api/followup/{id}/approve
Mark draft as approved and sent (mocked send).
```json
// Response: 200
{ "status": "sent", "approved_at": "2026-06-19T14:23:00Z" }
```

---

## F004 — Risk Score Endpoints

### GET /api/risk/{timeblock_id}
Returns the risk score for an appointment.
```json
{
  "timeblock_id": "uuid",
  "risk_level": "high",
  "score": 75,
  "factors": [
    "Same-day booking (+40)",
    "First visit (+15)",
    "Elective wellness procedure (+20)"
  ]
}
```
*Risk is calculated at booking time and stored. This endpoint retrieves the stored score.*

---

## F005 — Room Status Endpoints

### GET /api/rooms
Returns all rooms with current status.
```json
[{
  "id": "uuid",
  "name": "Exam Room 1",
  "type": "Room",
  "status": "available",
  "current_timeblock_id": null
}]
```

### PUT /api/rooms/{id}/status
Update a room's status.
```json
// Request
{ "status": "prep", "timeblock_id": "uuid" }
// Response: 200 — updated room object
```

---

## F006 — SOAP Note Endpoints

### POST /api/soap/draft
Generate a SOAP note draft for an appointment.
```json
// Request
{ "timeblock_id": "uuid" }
// Response: 200
{
  "id": "uuid",
  "timeblock_id": "uuid",
  "subjective": "Owner reports lethargy x3 days and reduced appetite...",
  "objective": {
    "vitals": { "temperature_c": null, "heart_rate": null, "resp_rate": null, "weight_kg": 28.5 },
    "exam_findings": { "general": null, "cardiovascular": null, "gastrointestinal": null }
  },
  "assessment": "",
  "plan": "Recommend complete blood panel and urinalysis. Recheck in 7 days if no improvement.",
  "signed": false
}
```

### PUT /api/soap/{id}
Save edits to an unsigned SOAP note.
```json
// Request: partial object with updated fields
// Response: 200 — updated note, or 409 if already signed
```

### POST /api/soap/{id}/sign
Sign and finalise the SOAP note. Triggers follow-up draft generation.
```json
// Request: { "signed_by": "vet_resource_id" }
// Response: 200
{ "signed": true, "signed_at": "2026-06-19T15:44:00Z", "followup_draft_id": "uuid" }
```

---

## Extended: Appointment Completion

### POST /api/appointments/{timeblock_id}/complete
Mark an appointment as complete. Triggers SOAP signing check and follow-up draft.
```json
// Request: { "force": false }  — if force=false and SOAP unsigned, returns warning
// Response 200 (complete):
{ "status": "complete", "followup_draft_id": "uuid" }
// Response 409 (SOAP unsigned, force=false):
{ "warning": "SOAP note is unsigned", "action_required": "sign_soap_or_force_complete" }
```

---

## Verbose Log Events (F002, F003, F006)

All agent actions append to the existing `/api/session` log stream with this shape:
```json
{ "step": "INTAKE AGENT", "message": "Sent pre-visit questionnaire to owner (Sarah M.)" }
{ "step": "INTAKE AGENT", "message": "Owner response received — extracting symptoms..." }
{ "step": "INTAKE AGENT", "message": "Parsed → Lethargy (3d, mild), Anorexia (2d, mild)" }
{ "step": "SOAP AGENT",   "message": "Draft generated from Wellness template + intake brief" }
{ "step": "FOLLOWUP AGENT","message": "Wellness follow-up draft generated for Buddy (Sarah M.)" }
```
