# Data Model: Multi-Clinic Foundation — F007

## New Entities

### Clinic

| Field | Type | Notes |
|---|---|---|
| id | string (UUID) | Primary key |
| name | string | e.g. "Paws & Claws Downtown" — used for alphabetical sort |
| address | string | Street address |
| phone | string | Main clinic phone |
| email | string | Clinic contact email |
| timezone | string | e.g. "America/Los_Angeles" (stored, not yet used in display) |
| color_hex | string | Brand colour, e.g. "#6C63FF" — applied as CSS custom property |
| is_active | boolean | Default true; soft-delete for decommissioned clinics |

**Default selection rule**: On app load, the clinic with the alphabetically lowest `name` is selected as the active context. This is enforced in the frontend — no `is_default` column needed.

---

### VetClinicAssignment

Junction table linking a Vet resource to one or more Clinics with day-of-week availability.

| Field | Type | Notes |
|---|---|---|
| id | string (UUID) | Primary key |
| vet_id | string (FK) | → Resource (type=Vet) |
| clinic_id | string (FK) | → Clinic |
| schedule_days | string (JSON array) | e.g. `["Monday","Wednesday","Friday"]` |
| is_primary | boolean | True = this is the vet's home clinic |

**Constraints**:
- A vet may have at most one `is_primary = true` assignment across all clinics.
- `schedule_days` values are English day names (Monday–Sunday). No date ranges — day-of-week recurrence only.
- A vet with no `VetClinicAssignment` for a given clinic is never bookable there.

**Assignment removal behaviour** (clarification Q3): Removing a `VetClinicAssignment` record blocks new bookings at that clinic. Existing `TimeBlock` records referencing that vet at that clinic are **not** deleted or modified.

---

## Extended Entities

### Resource (existing — extended)

| New Field | Type | Notes |
|---|---|---|
| clinic_id | string \| null (FK) | Primary clinic; null = pre-migration row, treated as default clinic |

**Note**: Rooms always have exactly one `clinic_id`. Vets have a primary `clinic_id` (their home clinic) and may appear at additional clinics via `VetClinicAssignment`.

---

### TimeBlock (existing — extended)

| New Field | Type | Notes |
|---|---|---|
| clinic_id | string \| null (FK) | Clinic where the appointment takes place; null = default clinic |

---

### Patient (existing — extended)

| New Field | Type | Notes |
|---|---|---|
| home_clinic_id | string \| null (FK) | Patient's registered clinic; null = default clinic |

**Cross-clinic access**: Patient records are globally readable regardless of `home_clinic_id`. The field is used only for the "Home clinic" banner in the UI.

---

## Relationships

```
Clinic ──< Resource (Room)              [1 clinic per room; rooms don't float]
Clinic ──< Resource (Vet, primary)      [1 primary clinic per vet]
Clinic ──< VetClinicAssignment ──> Vet  [many-to-many via junction table]
Clinic ──< TimeBlock                    [appointments happen at a specific clinic]
Patient >── Clinic (home_clinic_id)     [home registration; not a filter boundary]
```

---

## Query Patterns

### Clinic-filtered schedule board
```sql
SELECT * FROM timeblocks
WHERE (clinic_id = ? OR clinic_id IS NULL)
AND date(start_time) = date('now')
```

### Vets available at a clinic today
```sql
SELECT r.* FROM resources r
JOIN vet_clinic_assignments a ON a.vet_id = r.id
WHERE a.clinic_id = ?
AND r.type = 'Vet'
AND instr(a.schedule_days, :today_day_name) > 0
```

### Regional Manager summary
```sql
SELECT
  c.id, c.name, c.color_hex,
  COUNT(tb.id) AS appointment_count,
  SUM(CASE WHEN rs.risk_level = 'high' THEN 1 ELSE 0 END) AS high_risk_count
FROM clinics c
LEFT JOIN timeblocks tb ON tb.clinic_id = c.id AND date(tb.start_time) = ?
LEFT JOIN risk_scores rs ON rs.timeblock_id = tb.id
WHERE c.is_active = 1
GROUP BY c.id
```

---

## Validation Rules

- `Clinic.name` must be unique across all active clinics.
- `VetClinicAssignment.vet_id` must reference a Resource with `type = 'Vet'`.
- Each clinic in seed data must have at least 2 rooms and 2 vets assigned.
- `TimeBlock.clinic_id` is set at booking time from the user's active clinic context and is immutable after creation.
- A `VetClinicAssignment` with `is_primary = true` must have the same `clinic_id` as the vet's `Resource.clinic_id`.
