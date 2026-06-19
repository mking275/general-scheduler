# Implementation Plan: Vet Clinic Agentic Features — Phase 2

**Branch**: `002-vet-agentic-features` | **Date**: 2026-06-19 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `specs/002-vet-agentic-features/spec.md`

## Summary

Six agentic features that transform the existing appointment scheduler into a full clinic operations platform. The core pattern is consistent: enrich every TimeBlock with patient context (F001), add risk intelligence at booking time (F004), wrap the visit with an agentic intake→SOAP→follow-up loop (F002, F006, F003), and surface the right information to the right role (F005). All agent actions are template/rule-driven in demo scope — no external LLM calls required.

## Technical Context

**Language/Version**: Python 3.11 (backend), TypeScript / Next.js 16 (frontend)  
**Primary Dependencies**: FastAPI, sqlite3, Lucide React, Vanilla CSS  
**Storage**: SQLite — single `scheduler.db` file, existing schema extended with new tables  
**Testing**: Manual demo verification against seeded mock dataset; success criteria from spec SC-001 through SC-008  
**Target Platform**: Local dev + Cloudflare quick tunnel for sharing  
**Project Type**: Web application (FastAPI backend + Next.js frontend)  
**Performance Goals**: <2s for all agent-generated content; <500ms role view switch; 60fps animations  
**Constraints**: No external API calls in demo scope; all data seeded locally; no real SMS/email  
**Scale/Scope**: 8–10 mock patients, 3 vets, 5+ rooms, ~20 demo appointments

## Constitution Check

| Principle | Status | Notes |
|---|---|---|
| I. Demo-First | ✅ PASS | All 6 features produce visible Verbose Log output |
| II. Agentic Pipeline | ✅ PASS | Intake, Risk, SOAP, Follow-Up all route through agent layer |
| III. Data Simplicity | ✅ PASS | SQLite extension only; no new external services |
| IV. Role-Aware UI | ✅ PASS | F005 defines explicit role ownership for every feature |
| V. Incremental Build | ✅ PASS | Build order F001→F005→F004→F002→F003→F006 maintained |
| Stack compliance | ✅ PASS | Python + FastAPI + Next.js + Vanilla CSS throughout |
| No double-booking | ✅ PASS | No changes to constraint solver |
| 60fps animations | ✅ PASS | Role switch uses CSS transitions, no repaints |

**Gate result: PASS — proceed to design phases.**

## Project Structure

### Documentation (this feature)

```text
specs/002-vet-agentic-features/
├── plan.md              ← this file
├── research.md          ← Phase 0 output
├── data-model.md        ← Phase 1 output
├── contracts/
│   └── api.md           ← Phase 1 output
└── tasks.md             ← Phase 2 output (/speckit-tasks)
```

### Source Code Layout

```text
backend/
├── main.py              ← add 12 new endpoints
├── models.py            ← extend with Patient, Owner, PreExamBrief,
│                           RiskScore, SoapNote, FollowUpDraft, RoomStatus
├── repository.py        ← add CRUD for all new models
├── agents/
│   ├── intake.py        ← extend with symptom extraction
│   ├── risk.py          ← NEW: RiskScoringAgent
│   ├── soap.py          ← NEW: SoapDraftAgent
│   ├── followup.py      ← NEW: FollowUpDraftAgent
│   └── dispatch.py      ← extend to attach patient + risk at dispatch
└── seed_data.py         ← NEW: mock patients, owners, histories

frontend/src/
├── app/
│   └── page.tsx         ← add role state, wire new components
├── components/
│   ├── Dashboard.tsx    ← extend with role-switched views
│   ├── AppointmentCard.tsx  ← NEW: replaces inline card rendering
│   ├── PatientPanel.tsx     ← NEW: F001 expanded patient view
│   ├── IntakePanel.tsx      ← NEW: F002 mock intake flow
│   ├── RiskBadge.tsx        ← NEW: F004 indicator + tooltip
│   ├── RoleSelector.tsx     ← NEW: F005 header toggle
│   ├── RoomBoard.tsx        ← NEW: F005 vet tech view
│   ├── VetView.tsx          ← NEW: F005 vet appointment list
│   ├── SoapWorkspace.tsx    ← NEW: F006 SOAP note editor
│   └── FollowUpPanel.tsx    ← NEW: F003 draft + approve
```

## Complexity Tracking

No constitution violations. All complexity is justified by feature requirements.

---

*Next step: `/speckit-tasks` to generate the actionable task list.*
