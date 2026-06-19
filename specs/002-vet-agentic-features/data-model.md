# Data Model: Vet Clinic Agentic Features — Phase 2

## New Entities

### Patient
Represents an animal patient registered at the clinic.

| Field | Type | Notes |
|---|---|---|
| id | string (UUID) | Primary key |
| name | string | Pet's name |
| species | enum | dog / cat / bird / exotic |
| breed | string | e.g. "Golden Retriever" |
| dob | date | Date of birth |
| weight_kg | float | Most recently recorded |
| flags | string[] | Values: "alert" / "chronic" / "first_visit" |
| flag_notes | string | Free text e.g. "Allergic to penicillin" |
| owner_id | string (FK) | → Owner |
| visit_count | int | Auto-incremented on each completed appointment |
| last_visit_date | date \| null | Updated on appointment completion |
| last_visit_procedure | string \| null | Last procedure type |

**State transitions**: Patients are created at booking (first visit) or pre-seeded. `visit_count` and `last_visit_*` update when a TimeBlock is marked complete.

---

### Owner
Represents the pet's human owner / contact.

| Field | Type | Notes |
|---|---|---|
| id | string (UUID) | Primary key |
| name | string | Full name |
| phone | string | E.g. "(503) 555-0142" |
| email | string | For follow-up messages |
| patient_ids | string[] | All linked pets |

---

### PreExamBrief
Structured output of the intake agent. One per TimeBlock.

| Field | Type | Notes |
|---|---|---|
| id | string (UUID) | Primary key |
| timeblock_id | string (FK) | → TimeBlock (1:1) |
| chief_complaint | string | Agent-generated summary |
| symptoms | JSON | Array of `{name, duration_days, severity}` |
| owner_verbatim | string | Exact owner quote |
| suggested_focus | string[] | e.g. ["GI", "metabolic panel"] |
| status | enum | not_started / pending / received |
| created_at | datetime | |

**State transitions**: `not_started` → `pending` (questionnaire triggered) → `received` (owner response parsed).

---

### RiskScore
Risk assessment attached to a TimeBlock at booking time.

| Field | Type | Notes |
|---|---|---|
| id | string (UUID) | Primary key |
| timeblock_id | string (FK) | → TimeBlock (1:1) |
| risk_level | enum | low / medium / high |
| score | int | 0–100 |
| factors | string[] | Human-readable contributing factors |
| calculated_at | datetime | |

---

### SoapNote
Structured SOAP note for an appointment. One per TimeBlock.

| Field | Type | Notes |
|---|---|---|
| id | string (UUID) | Primary key |
| timeblock_id | string (FK) | → TimeBlock (1:1) |
| subjective | string | Pre-filled from PreExamBrief |
| objective | JSON | `{vitals: {}, exam_findings: {}}` — procedure-specific schema |
| assessment | string | Vet-filled diagnosis |
| plan | string | Auto-suggested + vet-edited |
| signed | boolean | False until vet signs |
| signed_at | datetime \| null | |
| signed_by | string \| null | Vet resource ID |

**State transitions**: `signed=false` → `signed=true` (irreversible). Signing triggers FollowUpDraft creation.

---

### FollowUpDraft
Agent-generated client communication draft. One per TimeBlock.

| Field | Type | Notes |
|---|---|---|
| id | string (UUID) | Primary key |
| timeblock_id | string (FK) | → TimeBlock (1:1) |
| subject | string | Email subject line |
| body | string | Full message body |
| tone | enum | wellness / surgery / emergency |
| status | enum | not_started / draft / approved / sent |
| generated_at | datetime \| null | |
| approved_at | datetime \| null | |

**State transitions**: `not_started` → `draft` (auto-generated on appointment complete) → `approved` (staff clicks approve) → `sent` (mocked).

---

### RoomStatus (extension of existing Room)
The existing `rooms` table gains a `status` column.

| Field | Type | Notes |
|---|---|---|
| status | enum | available / prep / occupied / cleaning |
| current_timeblock_id | string \| null | FK → TimeBlock if occupied |

---

## Extended Entities

### TimeBlock (existing — extended)
The following fields are added to the existing `timeblocks` table:

| New Field | Type | Notes |
|---|---|---|
| patient_id | string \| null (FK) | → Patient |
| intake_status | enum | not_started / pending / received |
| followup_status | enum | not_started / draft / sent |
| risk_level | enum \| null | low / medium / high (denormalised for query speed) |

---

## Entity Relationships

```
Owner ──< Patient >── TimeBlock ──1 PreExamBrief
                          │
                          ├──1 RiskScore
                          ├──1 SoapNote
                          └──1 FollowUpDraft

TimeBlock >── Room (existing, extended with status)
TimeBlock >── Resource/Vet (existing)
```

---

## Validation Rules

- A `Patient` must have a valid `owner_id` before being saved.
- A `PreExamBrief` can only exist for a TimeBlock with `status = scheduled`.
- A `SoapNote` cannot be signed if `objective.vitals` is entirely empty (vet must enter at least one vital).
- A `FollowUpDraft` status can only advance forward (not_started → draft → approved → sent); no rollback.
- A `RoomStatus` of `occupied` requires a non-null `current_timeblock_id`.
