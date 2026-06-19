# Implementation Plan: Multi-Clinic Foundation — F007

**Branch**: `003-multi-clinic-foundation` | **Date**: 2026-06-19 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `specs/003-multi-clinic-foundation/spec.md`  
**Depends on**: Phase 2 (F001–F006) complete and smoke-tested

## Summary

F007 adds clinic-awareness to the existing scheduler as a thin migration layer — no rewrites, no table drops. Four user stories: clinic-aware schedule board (US1), floating vet scheduling (US2), cross-clinic patient records (US3), and a Regional Manager aggregate view (US4). All existing Phase 2 functionality must continue to work unchanged when only one clinic exists (SC-005).

## Technical Context

**Language/Version**: Python 3.11 (backend), TypeScript / Next.js (frontend)  
**Primary Dependencies**: FastAPI, sqlite3 stdlib, Vanilla CSS — no new packages  
**Storage**: SQLite — `scheduler.db` extended with 2 new tables; 3 existing tables gain `clinic_id` column via `ALTER TABLE`  
**Migration strategy**: Additive-only. All `ALTER TABLE` calls are wrapped in try/except (already established pattern in `repository.py`). Existing rows get `clinic_id = NULL`, mapped to the default (alphabetically first) clinic at query time.  
**Testing**: Manual demo verification; SC-001 through SC-006 are the acceptance gates  
**Target Platform**: Local dev + Cloudflare tunnel  
**Performance Goals**: Clinic switch <1s (SC-001); Regional Manager view <2s (SC-004)  
**Constraints**: No real RBAC; no multi-timezone; 2 mock clinics in seed data  
**Scale/Scope**: 2 clinics, 1 floating vet, 4 rooms (2 per clinic), ~20 appointments split across clinics

## Constitution Check

| Principle | Status | Notes |
|---|---|---|
| I. Demo-First | ✅ PASS | Location switcher + Regional Manager are high-visibility |
| II. Agentic Pipeline | ✅ PASS | Constraint solver extended; conflict messages are agent output |
| III. Data Simplicity | ✅ PASS | SQLite migration only; 2 new tables |
| IV. Role-Aware UI | ✅ PASS | Regional Manager is a new role slot in existing RoleSelector |
| V. Incremental Build | ✅ PASS | Build order: schema → seed → API → switcher → floating vet → cross-clinic → regional view |
| Stack compliance | ✅ PASS | Python + FastAPI + Next.js + Vanilla CSS |
| No double-booking | ✅ PASS | Constraint solver extended with clinic-day check, not bypassed |
| 60fps animations | ✅ PASS | Clinic switch uses same CSS transition pattern as role switch |

**Gate result: PASS — proceed to design phases.**

## Project Structure

### New Source Files

```text
backend/
├── agents/
│   └── clinic_resolver.py     ← NEW: resolves default clinic, validates vet-clinic-day availability
└── seed_data.py               ← EXTEND: add 2 clinics, 1 floating vet, vet_clinic_assignments

frontend/src/components/
├── ClinicSwitcher.tsx          ← NEW: clinic context dropdown (header)
└── RegionalManagerView.tsx     ← NEW: aggregate side-by-side column dashboard
```

### Modified Source Files

```text
backend/
├── models.py          ← add Clinic, VetClinicAssignment models
├── repository.py      ← add clinic CRUD, vet_clinic_assignments CRUD,
│                         alter timeblocks/resources/patients for clinic_id,
│                         get_clinics_summary() for Regional Manager API
└── main.py            ← add /api/clinics endpoints, /api/clinics/summary,
│                         extend schedule endpoint with clinic_id context
frontend/src/
├── app/page.tsx                ← add clinicId state, pass to Dashboard
├── components/Dashboard.tsx   ← pass clinicId prop to all child components
├── components/RoleSelector.tsx ← add Regional Manager role option
└── components/VetView.tsx     ← pass clinicId filter to appointment list
```

## Build Order

```
T001 (schema migration)
  ↓
T002 (models)
  ↓
T003 (seed 2 clinics + assignments)
  ↓
T004 (clinic CRUD repo) ──────────────────────────────────────┐
T005 (vet_clinic_assignments repo)                            │
  ↓                                                           │
T006 (clinic endpoints) ──── T007 (clinic_resolver agent)    │
  ↓                                                           │
T008 (extend constraint solver) ─────────────────────────────┘
  ↓
T009 (ClinicSwitcher component) → T010 (wire into page.tsx)
  ↓
T011 (filter schedule board by clinic_id)
  ↓
T012 (filter room board by clinic_id) ──── T013 (cross-clinic patient banner)
  ↓
T014 (Regional Manager API endpoint)
  ↓
T015 (RegionalManagerView component) → T016 (wire into RoleSelector + Dashboard)
  ↓
T017 (extend seed data for demo scenario) → T018 (smoke test)
```

## Complexity Tracking

No constitution violations. The constraint solver extension (T008) is the highest-risk task — it touches existing booking logic. Mitigated by: keeping the clinic-filter as a pre-pass before the existing solver, not replacing it.

---

*Next step: `/speckit-tasks`*
