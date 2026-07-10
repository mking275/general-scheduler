# General Scheduler Constitution

## Core Principles

### I. Demo-First, Value-Visible
Every feature must be demonstrable in under 60 seconds. If an agent action is not visible in the Verbose Log, it doesn't count. The system's intelligence must be auditable, not a black box.

### II. Agentic Pipeline Integrity
All scheduling decisions flow through the agent pipeline: Intake → Semantic Match → Constraint Solve → Dispatch. No direct database writes that bypass the pipeline. Every booking is the output of an agent decision, not a form submission.

### III. Data Simplicity
SQLite for persistence. No ORMs. No external services in demo scope. All data must seed cleanly on fresh start. Mock data must be realistic enough to be convincing to a veterinary professional.

**Platform-track exception (added v1.1.0):** Platform-track features — the VP-1 convergence platform and its dependents (including feature 010 and later platform-track specs) — target the pilot platform rather than the demo scaffold. For these specs only, **PostgreSQL + Row-Level Security (RLS)** persistence and **external LLM / realtime services** are permitted, provided the spec's plan **declares the departure explicitly** (target platform, which principle clauses are departed from, and why). The **demo track retains Principle III as written** — SQLite, no ORMs, no external services. This exception scopes the departure to platform-track work and does not relax the demo constitution for demo-track features.

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

### Amendment History
- **v1.1.0 (2026-07-09)** — Added the **Platform-track exception** to Principle III: platform-track features (VP-1 convergence and its dependents, including 010+) may use PostgreSQL+RLS and external LLM/realtime services when their plan declares the departure. The demo track retains Principle III unchanged. Rationale: the pilot/convergence platform (external realtime LLM + Postgres/RLS envelope plane) is architecturally required for platform-track work and cannot be served by the demo's SQLite/no-external-service constraint; scoping the exception keeps the demo constitution intact for demo-track features. (MINOR: additive, backward-compatible — new permission, no existing rule removed.)
- **v1.0.0 (2026-06-19)** — Initial ratification.

**Version**: 1.1.0 | **Ratified**: 2026-06-19 | **Last Amended**: 2026-07-09
