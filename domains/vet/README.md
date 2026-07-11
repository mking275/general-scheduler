# VetAgent Domain Pack — `domains/vet/`  (v0.1.0, DRAFT)

> **Program #6 Cycle 6c.** The vet vertical's L3 domain pack: everything Vera
> knows that is specifically veterinary — roles, staffing/licensure constraints,
> appointment types, species handling, compliance tracking, practice KPIs,
> terminology. Ships through the **C1 Domain Pack schema** with the safety rails
> **core enforces** (W10: content ours, rails theirs — neither weakens the other's half).

## Status: DRAFT, Tier-1 only

- **Version** `0.1.0` · **locale** `en-US` · **currency** `USD`.
- **Not signed.** Every file carries `signed_by: null`. Nothing here is activated
  for live client-facing or clinical use.
- **Tier-1 (administrative) content only.** Tier-2 (clinical) is declared, gated,
  and empty — see `clinical/README.md`.

## Tier policy (absolute)

| Tier | What | Where | Gate |
|---|---|---|---|
| **Tier-1 administrative** | who / how-many / which-room / when-due. No medical judgment. | every file in this pack | provenance + DRAFT; signs at Pilot-Activation |
| **Tier-2 clinical** | dosing, drug interactions, contraindications, triage/breed protocol content | `clinical/` (empty in v0.1.0) | **licensed-vet review + `signed_by`**; 010 engine refuses unsigned protocols live |

**If a fact smells clinical, it does not go in a Tier-1 file** — it is noted as
future gated content in `clinical/README.md`. The validation test enforces this
with a denylist grep (dosing / drug-interaction / contraindication keys).

## File tree

```
domains/vet/
  pack.yaml                     manifest: id/version, locale/currency, modules, provenance+signed_by
  README.md                     this file
  kpis.yaml                     revenue/DVM, ARPP, no-show, slot-recovery, containment, staff-hours, staff-pull
  workforce/
    roles.yaml                  dvm, licensed_vet_tech, vet_assistant, csr_front_desk, practice_manager, kennel_attendant
    constraints.yaml            INSTANCES of the 4 generic constraint types (no new types, no Python)
  scheduling/
    appointment_types.yaml      wellness/sick/surgery/dental/euthanasia/... durations+buffers+rooms+sensitivity
    species_handling.yaml       canine/feline/exotic/avian ADMIN handling flags (no medicine)
  compliance/
    regulations.yaml            license/DEA renewal shapes, records-retention, OSHA basics, PDMP duty pointer
  comms/
    references.yaml             INCLUDE-BY-REFERENCE to live 010/011 configs (path + checksum)
  clinical/
    README.md                   Tier-2 STUB: what lands here + the signature gate (NO clinical content)
  knowledge/
    glossary.yaml               admin/operational vet terminology
```

## How the pack maps to capability-module hooks

Per the board's three-layer architecture (Vera Core L1 · Capability Modules L2 ·
Domain Packs L3) the pack **configures** shared L2 modules via hook interfaces.
The module executes generic logic; the pack supplies YAML instances/config.

| Pack file | Capability module (L2) | Hook it configures |
|---|---|---|
| `workforce/roles.yaml` | `capabilities/workforce/` | role registry + permitted-action lookup |
| `workforce/constraints.yaml` | `capabilities/workforce/` + `capabilities/scheduling/` | `validate(subject, action, ctx, *, batch) -> ConstraintCheck[]` |
| `scheduling/appointment_types.yaml` | `capabilities/scheduling/` | appointment-type durations/buffers/room-requirements |
| `scheduling/species_handling.yaml` | `capabilities/scheduling/` | room-assignment + handling flags |
| `compliance/regulations.yaml` | `capabilities/compliance/` | credential-expiry + duty-existence tracking |
| `comms/references.yaml` | `capabilities/comms/` | memory_scoping policy data + verification + disclosure (by reference) |

### The constraint-validation hook (the load-bearing one)

Per the board's agreed hook shape:

```
validate(subject: PartyRef, action: ActionRef, ctx: ScheduleContext,
         *, batch: list | None = None) -> ConstraintCheck | list[ConstraintCheck]

ConstraintCheck: { allowed, constraint_id, constraint_type, severity, reason, evidence[] }
```

The pack ships **YAML instances of four GENERIC engine types only** — never
Python, never a new type:

| Generic type | Vet instances (in `constraints.yaml`) |
|---|---|
| `role_requirement` | `dvm_required_for_surgery`, `dvm_required_for_euthanasia`, `controlled_substance_dispense_requires_dea_dvm`, `exotic_requires_qualified_dvm` |
| `procedure_gate` | `anesthesia_limit` (max_concurrent + recovery_buffer + requires_role), `dental_under_anesthesia_gate` |
| `resource_capacity` | `exam_room_availability`, `surgery_suite_availability`, `isolation_room_availability`, `boarding_kennel_capacity` |
| `licensure_ratio` | `tech_supervision_ratio`, `assistant_supervision_ratio` |

Contract requirements honored: **batch-first** (a rota validates as one call),
**deterministic hard path** (`hard` constraints never route through an LLM),
**`constraint_id` + `evidence` non-optional** (every denial is briefing-explainable).

### Memory scoping (the privacy rail)

`comms/references.yaml` points at the **three-field** `memory_scoping` policy
(`allow_classes` / `scope_predicates` / `kind_to_class`, the H1 revision). The
**enforcement point is core** (`scoped_recall`, default-deny, audience mandatory);
the **policy data is vertical**. The pack extends `_KIND_TO_CLASS` / `_ALLOW_CLASSES`
by config, never by weakening the rail.

## Provenance discipline (non-negotiable)

Every file carries a `provenance:` block (source paths/citations, confidence,
review_status), a `signed_by: null`, and a DRAFT marker. This is the pack's
day-one requirement, confirmed by core on the interface board.

## Data maturity

Durations, ratios, retention periods, and no-show baselines are **industry-default
placeholders** (or state-variable), marked in each file's provenance. Real
distributions arrive with **Goldsmith data ingestion (~Aug)** and replace the
fixtures at pilot activation.

## Validation

`backend/tests/pack/test_vet_pack.py`: all YAML parses · pack.yaml self-consistent
(referenced files exist) · every `constraints.yaml` instance uses only the 4
generic types · every file has a provenance block + `signed_by` · **zero
clinical-tier keys** present in Tier-1 files (denylist grep).
