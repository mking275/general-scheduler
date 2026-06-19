# API Contracts: Phase 3 Clinical Operations

**Feature**: specs/005-phase3-clinical-ops  
**Date**: 2026-06-19  
**Base URL**: `http://127.0.0.1:8080`  
**Auth**: None (demo mode)  
**Format**: JSON request/response bodies

---

## F013 — Appointment Reminders

### `POST /api/timeblocks/{timeblock_id}/reminder/send`

Triggers the Reminder Agent to compose the confirmation message and records that it was sent.

**Response** `200`:
```json
{
  "timeblock_id": "uuid",
  "confirmation_status": "sent",
  "reminder_sent_at": "2026-06-19T21:00:00",
  "composed_message": "Hi Sarah! Buddy has an appointment tomorrow at 10:00 AM with Dr. Smith...",
  "verbose_log": [
    "REMINDER AGENT: Composing confirmation message for Buddy (Sarah Mitchell)",
    "REMINDER AGENT: Message sent → status: sent"
  ]
}
```

---

### `POST /api/timeblocks/{timeblock_id}/reminder/reply`

Processes simulated owner reply; updates confirmation status and recalculates risk score.

**Request**:
```json
{ "reply": "yes" }
```
`reply` values: `"yes"` | `"confirm"` | `"ok"` → `confirmed`; `"reschedule"` | `"cancel"` | `"no"` → `reschedule_requested`

**Response** `200`:
```json
{
  "timeblock_id": "uuid",
  "confirmation_status": "confirmed",
  "confirmed_at": "2026-06-19T21:01:00",
  "risk_delta": -12,
  "new_risk_score": 28,
  "verbose_log": [
    "REMINDER AGENT: Owner reply received → 'yes' → status: confirmed",
    "RISK AGENT: Confirmation received → score adjusted −12 → new score: 28"
  ]
}
```

**Error** `404`: timeblock not found

---

### `GET /api/timeblocks/action-queue`

Returns all timeblocks with `confirmation_status` in `[unconfirmed, reschedule_requested]`.

**Response** `200`:
```json
{
  "count": 2,
  "items": [
    {
      "timeblock_id": "uuid",
      "patient_name": "Rex",
      "owner_name": "Carlos Rivera",
      "confirmation_status": "unconfirmed",
      "appointment_date": "2026-06-20T09:00:00",
      "vet_name": "Dr. Smith",
      "clinic_id": "clinic-downtown"
    }
  ]
}
```

---

## F014 — Waitlist & Backfill

### `POST /api/timeblocks/{timeblock_id}/cancel`

Cancels a booked slot and runs the BackfillAgent.

**Response** `200`:
```json
{
  "timeblock_id": "uuid",
  "cancelled": true,
  "backfill_matches": [
    {
      "waitlist_id": "uuid",
      "patient_name": "Daisy",
      "procedure": "Dental Cleaning",
      "score": 100,
      "urgency": "asap",
      "owner_name": "Lucia Gomez"
    }
  ],
  "verbose_log": [
    "BACKFILL AGENT: Slot freed — Dental Cleaning · Dr. Smith · 10:00 AM",
    "BACKFILL AGENT: Scanning waitlist — 3 entries evaluated",
    "BACKFILL AGENT: Match found — Daisy (Dental Cleaning) · Score: 100pts",
    "BACKFILL AGENT: Offer queued for Daisy (owner: Lucia Gomez)"
  ]
}
```

---

### `GET /api/waitlist`

Returns all active waitlist entries (offer_status ≠ accepted).

**Query params**: `clinic_id` (optional)

**Response** `200`:
```json
{
  "count": 3,
  "items": [
    {
      "id": "uuid",
      "patient_name": "Daisy",
      "procedure_type": "Dental Cleaning",
      "urgency": "asap",
      "preferred_vet": "Dr. Smith",
      "join_date": "2026-06-18T14:00:00",
      "offer_status": "waiting"
    }
  ]
}
```

---

### `POST /api/waitlist`

Adds a patient to the waitlist.

**Request**:
```json
{
  "patient_id": "uuid",
  "clinic_id": "clinic-downtown",
  "procedure_type": "Dental Cleaning",
  "preferred_vet_id": "uuid-or-null",
  "urgency": "asap"
}
```

**Response** `201`:
```json
{ "id": "uuid", "offer_status": "waiting", "join_date": "2026-06-19T21:05:00" }
```

---

### `POST /api/waitlist/{waitlist_id}/accept`

Owner accepts the backfill offer — books the slot, removes from waitlist.

**Response** `200`:
```json
{
  "timeblock_id": "uuid",
  "patient_name": "Daisy",
  "booked": true,
  "verbose_log": ["BACKFILL AGENT: Daisy accepted offer → slot booked · waitlist entry removed"]
}
```

---

### `POST /api/waitlist/{waitlist_id}/decline`

Owner declines — marks `offer_status: expired`, tries next match.

**Response** `200`:
```json
{
  "waitlist_id": "uuid",
  "offer_status": "expired",
  "next_match": { "patient_name": "Rex", "score": 80 }
}
```

---

## F018 — Breed Intelligence

### `GET /api/patients/{patient_id}/breed-flags`

Returns active breed protocol flags for a patient.

**Response** `200`:
```json
{
  "patient_id": "uuid",
  "breed": "French Bulldog",
  "flags": [
    {
      "flag_type": "brachycephalic",
      "title": "Anaesthesia Risk",
      "detail": "Brachycephalic breeds have narrow airways and are at elevated risk during general anaesthesia. Ensure pre-oxygenation, use short-acting agents, and have reversal agents ready. Monitor SpO2 closely post-procedure.",
      "severity": "critical",
      "age_threshold_years": 0
    }
  ]
}
```

**Response** `200` (no flags): `{ "patient_id": "uuid", "breed": "Mixed", "flags": [] }`

---

## F015 — Care Tracking

### `GET /api/patients/{patient_id}/care-events`

Returns care history for a patient with overdue/upcoming status.

**Response** `200`:
```json
{
  "patient_id": "uuid",
  "care_events": [
    {
      "id": "uuid",
      "protocol_name": "DHPP",
      "administered_date": "2025-06-01",
      "next_due_date": "2026-06-01",
      "status": "overdue",
      "days_overdue": 18,
      "batch_number": "LOT-4421",
      "administered_by": "Dr. Smith"
    }
  ]
}
```

---

### `POST /api/patients/{patient_id}/care-events`

Logs a care event. `timeblock_id` is optional (null for historical/standalone).

**Request**:
```json
{
  "protocol_id": "uuid",
  "administered_date": "2026-06-19",
  "timeblock_id": "uuid-or-null",
  "batch_number": "LOT-7812",
  "administered_by": "Dr. Smith"
}
```

**Response** `201`:
```json
{
  "id": "uuid",
  "next_due_date": "2027-06-19",
  "verbose_log": [
    "CARE AGENT: DHPP recorded for Buddy · Administered: 2026-06-19",
    "CARE AGENT: Next due date computed → 2027-06-19 (12-month interval)",
    "CARE AGENT: Reminder queued at T-30d (2027-05-20)"
  ]
}
```

---

### `GET /api/care/due-this-month`

Returns patients with any care item due within the next 30 days.

**Response** `200`:
```json
{
  "count": 7,
  "items": [
    {
      "patient_id": "uuid",
      "patient_name": "Buddy",
      "owner_name": "Sarah Mitchell",
      "protocol_name": "DHPP",
      "next_due_date": "2026-06-25",
      "days_until_due": 6,
      "status": "upcoming",
      "procedure_type": "Vaccination"
    }
  ]
}
```

---

### `GET /api/care-protocols`

Returns all care protocols.

**Response** `200`: `{ "protocols": [{ "id": "uuid", "species": "dog", "protocol_name": "DHPP", "interval_months": 12 }] }`

---

## F016 — Prescription Management

### `GET /api/patients/{patient_id}/prescriptions`

Returns all active prescriptions for a patient.

**Response** `200`:
```json
{
  "prescriptions": [
    {
      "id": "uuid",
      "drug_name": "Carprofen",
      "dose": "25mg",
      "frequency": "BID",
      "duration_days": 14,
      "refills_remaining": 2,
      "supply_ends_at": "2026-07-03",
      "issued_by": "Dr. Smith",
      "issued_date": "2026-06-19"
    }
  ]
}
```

---

### `POST /api/patients/{patient_id}/prescriptions`

Issues a new prescription. Runs allergy conflict check before saving.

**Request**:
```json
{
  "drug_name": "Amoxicillin",
  "dose": "250mg",
  "frequency": "BID",
  "duration_days": 10,
  "refills_remaining": 1,
  "issued_by": "Dr. Smith",
  "timeblock_id": "uuid-or-null"
}
```

**Response** `201` (no conflict):
```json
{
  "id": "uuid",
  "supply_ends_at": "2026-06-29",
  "allergy_conflict": null,
  "verbose_log": ["PRESCRIPTION AGENT: Amoxicillin 250mg BID x10d · 1 refill · No allergy conflicts ✓"]
}
```

**Response** `200` (conflict detected — not blocked, requires client acknowledgement):
```json
{
  "allergy_conflict": {
    "drug_class": "penicillin",
    "patient_flag": "penicillin allergy",
    "message": "⚠ Allergy conflict: Amoxicillin (penicillin class) — patient has a documented penicillin allergy. Acknowledge to proceed."
  },
  "saved": false
}
```

**Re-submit with acknowledgement** — add `"acknowledged": true` to request body → saves with conflict noted.

---

### `POST /api/prescriptions/{prescription_id}/refill-request`

Creates a refill request from either role.

**Request**:
```json
{ "initiated_by": "front_desk" }
```
or `"initiated_by": "vet"`

**Response** `201`:
```json
{
  "id": "uuid",
  "status": "auto_approved",
  "eligibility_reason": "2 refills remaining · Last exam 3 months ago",
  "verbose_log": ["PRESCRIPTION AGENT: Refill request created · auto-approval eligible · refills_remaining: 2 → 1"]
}
```

---

### `GET /api/refill-requests`

Returns all pending refill requests.

**Response** `200`:
```json
{
  "count": 2,
  "items": [
    {
      "id": "uuid",
      "patient_name": "Buddy",
      "drug_name": "Carprofen",
      "status": "auto_approved",
      "eligibility": "auto_approve",
      "refills_remaining": 2,
      "initiated_by": "front_desk"
    }
  ]
}
```

---

### `POST /api/refill-requests/{id}/approve`

One-click approve — decrements `refills_remaining`.

**Response** `200`:
```json
{
  "prescription_id": "uuid",
  "refills_remaining": 1,
  "verbose_log": ["PRESCRIPTION AGENT: Refill approved by front desk · refills_remaining: 2 → 1"]
}
```

---

## F019 — Capacity Forecasting

### `GET /api/clinics/{clinic_id}/forecast`

Returns 4-week capacity and revenue forecast.

**Response** `200`:
```json
{
  "clinic_id": "clinic-downtown",
  "clinic_name": "Paws & Claws Downtown",
  "trend": "on_track",
  "forecast_weeks": [
    {
      "week_label": "Jun 23",
      "booked_slots": 14,
      "projected_slots": 16,
      "capacity_slots": 18,
      "utilisation_pct": 89,
      "projected_revenue": 1840
    },
    { "week_label": "Jun 30", "booked_slots": 11, "projected_slots": 15, "capacity_slots": 18, "utilisation_pct": 83, "projected_revenue": 1620 },
    { "week_label": "Jul 7",  "booked_slots": 0,  "projected_slots": 16, "capacity_slots": 18, "utilisation_pct": 89, "projected_revenue": 1760 },
    { "week_label": "Jul 14", "booked_slots": 0,  "projected_slots": 17, "capacity_slots": 18, "utilisation_pct": 94, "projected_revenue": 1900 }
  ],
  "insight": "Downtown is tracking ahead of last month's pace. Utilisation is projected to reach 94% in week 4 — consider opening an additional afternoon slot.",
  "verbose_log": [
    "FORECAST AGENT: Loading 8 weeks of historical data for Paws & Claws Downtown",
    "FORECAST AGENT: Linear regression → slope: +0.42 slots/week · R²: 0.87",
    "FORECAST AGENT: Trend classified: on_track (pace 89% of capacity)",
    "FORECAST AGENT: 4-week projection computed · Revenue estimate: $7,120 total"
  ]
}
```
