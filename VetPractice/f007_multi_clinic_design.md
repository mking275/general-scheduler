# F007 — Multi-Clinic Foundation

**Status**: Design  
**Depends on**: F001–F006 (Phase 2)  
**Priority**: P1 for commercial viability; Low effort relative to impact

---

## Problem Statement

The current scheduler assumes a single clinic. Every resource, patient, appointment, and room
lives in one flat namespace. Corporate vet groups — the fastest-growing buyer segment — operate
2–50 locations. An independent clinic that evaluates this software will ask within 60 seconds:
*"What happens when we open a second location?"*

Without multi-clinic support the answer is "start over." That's a deal-killer.

---

## What Multi-Clinic Actually Means

### Three buyer archetypes

| Buyer | Situation | What they need |
|---|---|---|
| **Solo clinic owner** | 1 location, growing | Future-proof; don't want to migrate data when they expand |
| **Small group** | 2–5 locations, same owner | Shared patient records, floating vets, per-location schedules |
| **Corporate group** | 6–50 locations, regional managers | Central ops dashboard, cross-location reporting, role hierarchy |

Our demo targets the **small group** archetype — most relatable, most common acquisition target.

---

## Core Concepts

### Clinic
A physical location. Has its own name, address, phone, branding, and timezone. All resources
(vets, rooms) belong to a clinic. Patients have a "home clinic" but are portable.

### Floating Vet
A veterinarian credentialed to work at more than one clinic. Common in small group practices
where a specialist covers multiple sites on different days. The scheduler must know *which*
clinic a vet is at on any given day, not just that they exist.

### Patient Portability
A patient's medical records (SOAP notes, intake briefs, history) follow them across locations.
If Buddy was seen at the Downtown clinic last week and comes into the Westside clinic today,
the vet should see the full history — not a blank record.

### Location Context
Every UI session operates within a "selected clinic" context. The header shows which clinic
you're viewing. Switching clinics re-filters the entire schedule board. A Regional Manager
role can see an aggregate view across all clinics.

---

## Data Model Changes

### New Entity: Clinic

| Field | Type | Notes |
|---|---|---|
| id | string (UUID) | Primary key |
| name | string | e.g. "Paws & Claws — Downtown" |
| address | string | Street address |
| phone | string | Main clinic phone |
| email | string | Clinic contact email |
| timezone | string | e.g. "America/Los_Angeles" |
| color_hex | string | Brand colour for UI differentiation (e.g. "#6C63FF") |
| is_active | boolean | Soft delete / deactivation |

### Modified Entities

**Resource** — gains `clinic_id` (primary location) and `float_clinic_ids[]` (additional locations
where a vet is credentialed). Rooms always belong to exactly one clinic.

**TimeBlock** — gains `clinic_id` (the location where the appointment takes place).

**Patient** — gains `home_clinic_id` (where they're registered) but records are readable
from any clinic.

**Owner** — no change; owners are shared across clinics naturally.

### Relationship Map

```
Clinic ──< Resource (Vet)     [many vets per clinic; vets can float]
Clinic ──< Resource (Room)    [many rooms per clinic; rooms don't float]
Clinic ──< TimeBlock          [appointments happen at a specific clinic]
Patient >── Clinic            [home_clinic_id; records portable elsewhere]
```

### New Join: vet_clinic_assignments
For floating vets — tracks which clinics a vet works at and on which days.

| Field | Type | Notes |
|---|---|---|
| vet_id | string (FK) | → Resource (Vet) |
| clinic_id | string (FK) | → Clinic |
| schedule_days | string[] | e.g. ["Monday", "Wednesday"] |
| is_primary | boolean | Primary vs secondary location |

---

## Agent Pipeline Changes

### Scheduling — Clinic-Aware Dispatch
When the Intake Agent parses a scheduling request, it must now resolve:
1. **Which clinic?** — extracted from request ("at the downtown office") or defaults to
   the user's selected clinic context.
2. **Is the requested vet available at that clinic on that day?** — checked against
   `vet_clinic_assignments`, not just `availability_windows`.
3. **Are there rooms at that clinic?** — constraint solver filters to `clinic_id`-matched rooms.

### Risk Scoring — Location-Aware Factors
No-show patterns differ by location. Future: add `clinic_id` as a factor input so the risk
model can learn location-specific patterns. For demo: neutral (no location factor in scoring yet).

### Patient Lookup — Cross-Clinic
When the intake agent looks up a patient at Clinic B, it searches the global patients table
(no clinic filter). The brief is generated from the patient's full history, regardless of
where prior visits occurred. A "Last seen at: Downtown" label is shown.

---

## UI / UX Design

### Location Switcher (Header)
Sits in the top-left of the header, left of the role selector.
- Dropdown showing all active clinics with their colour dot
- Currently selected clinic name displayed
- Selecting a new clinic re-fetches the schedule board filtered to that clinic
- Regional Manager role shows an "All Locations" option that renders an aggregate view

```
[🟣 Downtown ▼]  [Front Desk | Vet Tech | Vet]
```

### Clinic Colour Coding
Each clinic gets a distinct brand colour (set at creation, with defaults). That colour appears:
- As a dot in the location switcher
- As a left-border accent on appointment cards
- In the page header background (subtle tint)

This makes it visually impossible to mistake which clinic you're looking at.

### Floating Vet Indicator
On appointment cards, if the assigned vet's primary clinic is different from the current clinic:
- Small 📍 pin icon next to vet name
- Tooltip: "Dr. Chen — visiting from Westside"

### Regional Manager View ("All Locations")
A new dashboard layout (only visible in Regional Manager role):
- Side-by-side columns, one per clinic
- Each column shows today's appointment count, utilization %, and risk summary
- Click a clinic column to drill into that location's full schedule
- No booking from this view — read-only aggregate

### Patient History Cross-Clinic Banner
When a patient is being seen at a clinic other than their home clinic, their appointment card
shows a subtle banner:
> 🏥 *Patient's home clinic: Downtown. Viewing full cross-location history.*

---

## New Role: Regional Manager

| Role | Scope | Actions |
|---|---|---|
| Front Desk | Single clinic | Book, intake, follow-up |
| Vet Tech | Single clinic | Room board, prep |
| Veterinarian | Single clinic | SOAP, sign, view patients |
| **Clinic Manager** *(new)* | Single clinic | All of above + clinic settings, staff assignment |
| **Regional Manager** *(new)* | All clinics | Aggregate view, cross-location reports, no booking |

For demo scope: add Regional Manager to the role selector. It renders the aggregate view.
Clinic Manager is a future phase (too much settings UI for demo).

---

## Demo Scenario

**Setup**: 2 mock clinics — "Paws & Claws Downtown" (purple) and "Paws & Claws Westside" (teal).

**Floating vet**: Dr. Chen is credentialed at both. On Monday/Wednesday she's Downtown;
Tuesday/Thursday she's Westside.

**Demo flow**:
1. Open app — see Downtown schedule (default)
2. Switch to Westside in the location dropdown — schedule board re-renders with Westside's rooms
   and appointments; header tints teal
3. Book an appointment at Westside — Dr. Chen appears as available (it's her Westside day)
4. Switch to Regional Manager role — see side-by-side clinic columns with today's stats
5. Click on a patient seen at Westside who originally registered at Downtown —
   "Home clinic: Downtown" banner appears; full SOAP history from both locations is visible

**Talking points**:
> *"Most vet software forces you to choose: one database per location, or one giant shared
>  database with no separation. We built it the right way — each clinic has its own operational
>  context, but patient records and floating staff are shared automatically. This is how a
>  corporate group manages 10 locations without chaos."*

---

## Build Effort Estimate

| Component | Effort | Notes |
|---|---|---|
| `clinics` table + migration | XS | New table + `clinic_id` column on 3 existing tables |
| Seed data (2 clinics, assignments) | XS | Extend `seed_data.py` |
| Location switcher component | S | Dropdown + context propagation |
| Schedule board filtering | S | Add `?clinic_id=` param to `/api/schedule` |
| Regional Manager view | M | New dashboard layout, aggregate API endpoint |
| Floating vet availability check | M | Extend constraint solver + `vet_clinic_assignments` table |
| Patient cross-clinic banner | XS | Conditional UI element on PatientPanel |
| Cross-clinic patient history API | S | Remove clinic filter from patient queries |

**Total: ~3–4 days of focused build time after Phase 2 is complete.**

---

## What We Do NOT Build (Demo Scope)

- Per-clinic billing / invoicing separation
- Staff scheduling by location (which days each vet works where) UI
- Clinic-specific branding (logos, custom colours beyond the default palette)
- Data isolation / access control enforcement (demo uses honour-system role toggle)
- Cross-clinic inventory management
- Multi-timezone appointment display (all times shown in local browser time)

---

## Dependency on Phase 2

F007 must be built **after** Phase 2 is complete because:
- `TimeBlock` already has `patient_id`, `intake_status`, etc. — adding `clinic_id` is one more column
- `seed_data.py` is already being written — extending it for 2 clinics is trivial
- The role selector (F005 T013) is already built — adding Regional Manager is a new case

The schema `clinic_id` columns should be added as a **migration on top of Phase 2**,
not merged into it. This keeps Phase 2 clean and independently shippable.

---

## Next Steps

1. Run `speckit-specify` on this feature to produce `specs/003-multi-clinic/spec.md`
2. Run `speckit-plan` to extend data model and API contracts
3. Run `speckit-tasks` — estimated 15–20 tasks
4. Implement after Phase 2 smoke test passes (T036)
