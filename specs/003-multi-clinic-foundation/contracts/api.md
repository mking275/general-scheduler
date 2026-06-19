# API Contracts: Multi-Clinic Foundation — F007

Base URL: `http://localhost:8080`

---

## Clinic Endpoints

### GET /api/clinics
Returns all active clinics sorted by name ascending. First item = default clinic.
```json
[
  {
    "id": "uuid-a",
    "name": "Paws & Claws Downtown",
    "address": "123 Main St, Portland OR 97201",
    "phone": "(503) 555-0100",
    "email": "downtown@pawsandclaws.com",
    "timezone": "America/Los_Angeles",
    "color_hex": "#6C63FF",
    "is_active": true
  },
  {
    "id": "uuid-b",
    "name": "Paws & Claws Westside",
    "address": "456 Oak Ave, Portland OR 97209",
    "phone": "(503) 555-0200",
    "email": "westside@pawsandclaws.com",
    "timezone": "America/Los_Angeles",
    "color_hex": "#00BFA6",
    "is_active": true
  }
]
```

### GET /api/clinics/summary?date=YYYY-MM-DD
Returns aggregate stats for all active clinics for the given date (defaults to today).
Used exclusively by the Regional Manager view.
```json
[
  {
    "clinic_id": "uuid-a",
    "clinic_name": "Paws & Claws Downtown",
    "clinic_color": "#6C63FF",
    "appointment_count": 6,
    "total_slots": 12,
    "utilisation_pct": 50,
    "high_risk_count": 2
  },
  {
    "clinic_id": "uuid-b",
    "clinic_name": "Paws & Claws Westside",
    "clinic_color": "#00BFA6",
    "appointment_count": 0,
    "total_slots": 10,
    "utilisation_pct": 0,
    "high_risk_count": 0
  }
]
```
*Note: A clinic with 0 appointments still appears (FR-017). `utilisation_pct` = `round(appointment_count / total_slots * 100)` where `total_slots` = (available vet hours / average appointment duration of 30 min) for that clinic on that date.*

---

## Extended: Resources (clinic-aware)

### GET /api/resources?clinic_id={id}
Returns only resources (vets + rooms) belonging to the specified clinic.  
When `clinic_id` is omitted, returns all resources (backward-compatible).
```json
// Response shape unchanged from Phase 2 — adds no new fields
```

### GET /api/resources/vets/available?clinic_id={id}&date=YYYY-MM-DD
Returns vets available at the given clinic on the given date (checks VetClinicAssignment day-of-week).
```json
[
  {
    "id": "uuid-vet",
    "name": "Dr. Chen",
    "type": "Vet",
    "is_floating": true,
    "primary_clinic_id": "uuid-a",
    "visiting": true
  }
]
```
*`visiting: true` when the vet's primary clinic differs from the requested `clinic_id`.*

---

## Extended: Schedule Endpoint

### POST /api/schedule  (existing — extended)
Request body gains optional `clinic_id` field. When provided, filters resources to that clinic and runs the floating-vet availability check before solving.
```json
// Request (new field added)
{
  "request_id": "uuid",
  "text": "Book Buddy for a wellness check with Dr. Chen on Tuesday",
  "patient_id": "uuid",
  "clinic_id": "uuid-b"
}
// Response: unchanged shape — conflict message now clinic-specific when vet unavailable
// Conflict response — HTTP 409:
{
  "error": "Dr. Chen is at Paws & Claws Downtown today — next available at Paws & Claws Westside is Tuesday 2026-06-23",
  "logs": ["CLINIC RESOLVER: Dr. Chen assigned to Downtown on Wednesday", "CLINIC RESOLVER: Next available at Westside → Tuesday"]
}
```

---

## Extended: Timeblocks (clinic-aware)

### GET /api/schedule/timeblocks?clinic_id={id}
Returns timeblocks for the given clinic only.  
When `clinic_id` omitted, returns all (backward-compatible).

---

## Extended: Patients (cross-clinic)

### GET /api/patients  (existing — unchanged filter)
No `clinic_id` filter applied. Returns all patients from all clinics (FR-014).  
Response gains `home_clinic_id` and `home_clinic_name` fields:
```json
{
  "id": "uuid",
  "name": "Buddy",
  ...existing fields...,
  "home_clinic_id": "uuid-a",
  "home_clinic_name": "Paws & Claws Downtown"
}
```

---

## Verbose Log Events (F007)

All clinic-resolver agent actions append to the session log:
```json
{ "step": "CLINIC RESOLVER", "message": "Active clinic context: Paws & Claws Westside" }
{ "step": "CLINIC RESOLVER", "message": "Dr. Chen assigned to Downtown on Wednesday — not available at Westside today" }
{ "step": "CLINIC RESOLVER", "message": "Next available at Westside: Tuesday 2026-06-23" }
```
