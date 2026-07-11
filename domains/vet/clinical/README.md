# VetAgent Domain Pack — `clinical/` (Tier-2, GATED — NO CONTENT IN v0.1.0)

> **STATUS: STUB. This directory is intentionally empty of content.** No clinical
> knowledge is authored here in pack v0.1.0. This README declares what *will* live
> here and the gate that content must pass first. Authoring clinical content
> without passing the gate is a hard violation of the Tier-1/Tier-2 discipline.

## The Tier-1 / Tier-2 line (absolute)

The vet domain pack is authored in two tiers:

- **Tier-1 — administrative** (shipped in v0.1.0): roles, staffing/licensure
  constraints, appointment types + durations, species *handling* flags, practice
  KPIs, compliance *tracking shapes*, comms references. Governs *who / how many /
  which room / when-is-it-due*. Carries **no medical judgment**.
- **Tier-2 — clinical-adjacent** (this directory; gated): anything that smells
  clinical — **dosing, drug interactions, contraindications, triage protocol
  content, breed care protocols, medical restraint technique, treatment plans.**

**Rule:** if a fact is clinical, it does **not** enter a Tier-1 file. It is noted
as future gated content here. The Tier-1 validation test (`backend/tests/pack/
test_vet_pack.py`) enforces this with a denylist grep — clinical keys in Tier-1
files fail the build.

## What will live here (future, gated)

- **Triage protocols** — the vet-signed escalation state machines the voice line
  runs (keyword-first, deterministic). Content is AVMA-teletriage-anchored, per
  VP-9. The *engine* already exists (feature 010); it is the *signed content*
  that is gated.
- **Breed / species care protocols** — species- and breed-specific care guidance.
- **Drug-interaction knowledge** — KNOW-layer only, citation-carrying, **never
  verb-enabling**. Vera may surface cited drug-interaction knowledge to a
  veterinarian; she never orders, doses, or prescribes.

## The gate (why nothing is here yet)

Tier-2 content enters a pack **only** with:

1. **Licensed-vet-reviewed provenance** — a named, credentialed DVM reviewer of
   record, not just an author.
2. **`signed_by` populated** — the signature workflow. Every Tier-2 file carries
   `signed_by` + `signed_at`; `null` means unsigned means **cannot run live**.

This gate is **already enforced in code, live**: feature 010's triage engine
**refuses to run an unsigned protocol** (the T022 signature gate). An unsigned
protocol is usable in **sim mode only**.

### The pending-signature fixture

There is already an **UNSIGNED** sample triage protocol in the repo:

- `config/voice/triage_protocol.goldsmith.sample.yaml`
  (sha256/16 = `456981fc4280599c`, 2026-07-11)
  - `version: 0.0.0-sample`, `signed_by: null`, `signed_at: null`
  - Exercises the engine + format; blocks live emergency handling until signed.

This fixture is the concrete example of a Tier-2 artifact **pending signature**.
When VP-9 authors the real protocol and a DVM signs it, `signed_by`/`signed_at`
populate and the 010 engine will accept it live. Until then it is sim-only, and
it is **not** promoted into this `clinical/` directory.

## Signature workflow (open decisions, per VP-9)

- **Which DVM signs?** Per-clinic vs. per-group signing authority — open.
- **Versioning + clinic-override bounds** for signed protocols — open.
- **Regression-suite ownership split with core** (50+ scenario suite) — open.

These are tracked as VP-9 `Decisions` in
`VetPractice/design/v02-uberspeckit-programs.md`.

---

**Provenance for this stub**

- Sources:
  - `COS-platform/context/vera-vetagent-interface-board-2026-07-09.md` — two-tier
    readiness; `signed_by` non-negotiable; clinical gated on signature.
  - `VetPractice/design/v02-uberspeckit-programs.md` §VP-9 — seed + open decisions.
  - `config/voice/triage_protocol.goldsmith.sample.yaml` — the pending-signature fixture.
  - `context/README.md` Working Rule (W10) — content ours, rails core; Expert Firewall.
- Confidence: high (this is a policy/gate statement, not sourced facts).
- Review status: **DRAFT**.
- Tier: **Tier-2 gate declaration** (no Tier-2 content present).
- `signed_by: null`
