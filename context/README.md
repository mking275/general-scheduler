# VetAgent — Context

**Orientation for any agent working in this workspace. Read this first, then
`/home/matt/COS-platform/context/habits.md` (W1–W10), then any interface board naming this stream.**

**Workspace owner**: the **VetAgent agent** stream (see COS-platform `context/team.md`).
Other streams: read anything, write nothing — asks go through the interface board.

---

## What VetAgent Is

AI-native veterinary practice operations, built on COS-platform. The persona is **Vera — the
practice's AI Chief of Staff**: she KNOWs the practice, ADVISEs with cited evidence, and the
veterinarian always DECIDEs. She is not a vet and not a lawyer — architecturally (the Expert
Firewall), not just in copy.

This repo: FastAPI backend + Next.js frontend (demo-stage product), `specs/` 001–009,
`marketing/` (engine assets + Goldsmith package), `VetPractice/` (research + design),
`StrategicStudy/` (strategy boards).

## Current State (2026-07-09)

- **Goldsmith pilot**: proposal + data-request letter delivered (`marketing/proposals/`).
  23-clinic group on ezyVet; kickoff targeted first week of August. Phases: data & ingestion →
  design loops on real data → side-by-side at up to 3 clinics.
- **Strategy**: the Envelope — *internal framing:* anesthetized replacement; *public framing:*
  orchestrate the stack, ezyVet is one actuator. Full board:
  `StrategicStudy/envelope-strategy-board-2026-07-07.md`. The data-access ladder (§5 customer
  data request → ezyVet Automated Reports → guided-operator "human API" → partner API last)
  keeps IDEXX's kill switch away from everything that matters.
- **Phase 4 design** (Goldsmith feedback): `VetPractice/design/phase4-goldsmith-feedback-design.md`
  — voice (F1, after-hours first), procurement (F2), staff scheduling (F3), financial (F4),
  ops advice (F5), enterprise hierarchy (F6) + additions R1–R9. Spec seeds 010–015.
- **Spec 009** (`specs/009-vera-envelope-onboarding/`): Vera's First Day — connect, Unveiling,
  shadow receipts, verb promotion, Phase D cutover.

## Key Docs Map

| Need | Read |
|---|---|
| Strategy + risks + decisions | `StrategicStudy/envelope-strategy-board-2026-07-07.md` |
| What we're building next | `VetPractice/design/phase4-goldsmith-feedback-design.md` |
| Onboarding/migration design | `specs/009-vera-envelope-onboarding/discover.md` |
| Client-facing package | `marketing/proposals/goldsmith-package-2026-07/` |
| Claim discipline | `marketing/engine-inputs/verified-claims.md` |
| Vet market research | `VetPractice/research_report.md`, `vpma_*` docs |
| Core architecture (not ours — Vera agent's) | `~/ModelGarden/research/vera-architecture/` |
| **Speckit lifecycle + program roadmap** | **[uber-speckit.md](file:///home/matt/FarmAgent2-Workspace/context/uber-speckit.md)** — canonical. VetAgent = Program #2 |

## The Split (habits W4/W10)

Copy-across-verticals → **Vera-core** (Vera agent, ModelGarden). Rewrite-per-vertical →
**here** (domain packs, ezyVet/PIMS adapters, pilot ops, GTM). **W10**: this stream authors
the vet domain pack — including clinical-adjacent content (triage protocols) — but packs ship
only through the C1 schema with core-enforced Expert Firewall rails. Current asks on the
core: see `COS-platform/context/vera-vetagent-interface-board-2026-07-09.md`.

## Working Rules (deltas from COS-platform habits)

1. **Claim discipline extends to runtime**: any factual claim in marketing OR in Vera's output
   traces to `verified-claims.md` or the practice record. VC-3 (the $16,860 replacement math)
   does **not** apply to envelope clinics — their budget line is the companion-tool stack.
2. **Never market the ezyVet integration publicly** (ToS §4.1 posture); the replacement endgame
   is never written into client-facing material.
3. **No diagnostics-order-path code, ever**, without Matt's explicit direction — routing labs
   through native VetConnect untouched is both strategy and shield.
4. **Production is cloud**; ModelGarden's DGX hardware is a development/evaluation resource.
5. **Matt's checkout may hold demo WIP** — follow `patterns/agent-coordination/` R1–R8;
   background agents work in worktrees only.

## Sensitivities

- **Dr. Goldsmith is a close personal contact of Matt's.** Client-facing materials stay
  arm's-length professional; partnership/equity conversations are Matt-only. He is also a
  strategic partner (prior multi-hundred-clinic exit; ambitions toward large operators and an
  eventual IDEXX transaction) — treat pilot metrics as evidence for that thesis.
- The adversarial analyses (envelope board appendices D/E) are internal-only.

## Stage

See `context/stage.md`.
