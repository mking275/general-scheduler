# General Scheduler Constitution

## Core Principles

### I. Demo-First, Value-Visible
Every feature must be demonstrable in under 60 seconds. If an agent action is not visible in the Verbose Log, it doesn't count. The system's intelligence must be auditable, not a black box.

### II. Agentic Pipeline Integrity
All scheduling decisions flow through the agent pipeline: Intake → Semantic Match → Constraint Solve → Dispatch. No direct database writes that bypass the pipeline. Every booking is the output of an agent decision, not a form submission.

### III. Data Simplicity
SQLite for persistence. No ORMs. No external services in demo scope. All data must seed cleanly on fresh start. Mock data must be realistic enough to be convincing to a veterinary professional.

### IV. Role-Aware UI
Every UI element must have a clear role owner (Front Desk / Vet Tech / Vet). No feature ships without a defined role context. The interface adapts to the user's job, not the other way around.

### V. Incremental Buildability
Each feature (F001–F006) must be independently deployable and testable. No feature may break the existing working demo. Build order: F001 → F005 → F004 → F002 → F003 → F006.

## Technology Stack

- **Backend**: Python 3.11+, FastAPI, SQLite (via sqlite3 stdlib)
- **Frontend**: Next.js 16, TypeScript, Vanilla CSS (no Tailwind), Lucide icons
- **Agent Pipeline**: Pure Python heuristics + template engine (no external LLM calls in demo)
- **Deployment**: Cloudflare tunnel for demo sharing; GitHub repo at mking275/general-scheduler

## Quality Gates

- No double-bookings permitted under any input (constraint solver is the guard)
- All new API endpoints must appear in the Verbose Log during operation
- Frontend must maintain 60fps during animations
- Each feature must work with the seeded mock dataset of 8+ patients and 3 vets

## Governance

Constitution supersedes all other practices. Deviations require explicit justification in the plan's Complexity Tracking section.

**Version**: 1.0.0 | **Ratified**: 2026-06-19 | **Last Amended**: 2026-06-19
