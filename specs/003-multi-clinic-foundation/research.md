# Research: Multi-Clinic Foundation — F007

## Decisions

### Default Clinic Resolution (US1)
- **Decision**: `GET /api/clinics` returns clinics sorted by name ascending. Frontend picks `clinics[0]` as default. No backend "default" flag needed.
- **Rationale**: Clarification Q1 answer. Deterministic, zero-config. Avoids a `is_default` column that would need maintenance when clinics are renamed.
- **Alternatives considered**: `localStorage` persistence — rejected (demo resets expected; not worth the state complexity); user prompt on load — rejected (adds friction to demo startup).

### clinic_id on NULL rows (Migration Safety) (US1)
- **Decision**: Existing rows with `clinic_id = NULL` are treated as belonging to the alphabetically first clinic at query time. No backfill migration needed.
- **Rationale**: Keeps Phase 2 demo data working without a database wipe (SC-005, SC-006). The `OR clinic_id IS NULL` clause is added to all clinic-filtered queries during the transition.
- **Alternatives considered**: Backfill migration script — rejected (risk of breaking existing demo data); hard foreign key constraint — rejected (SQLite FK enforcement is opt-in anyway).

### Floating Vet Availability Check (US2)
- **Decision**: Two-step check in `clinic_resolver.py`: (1) is the vet assigned to the requested clinic at all? (2) is today in their `schedule_days` for that clinic? If either fails, compute next available date by scanning forward up to 14 days.
- **Rationale**: Simple loop over `VetClinicAssignment` records. Deterministic and testable. The "next available" suggestion (FR-013, clarification Q5) requires the 14-day lookahead.
- **Alternatives considered**: Calendar-based availability engine — rejected (overkill for demo; day-of-week is sufficient).

### Constraint Solver Extension (US2)
- **Decision**: Add a pre-filter step before the existing `HeuristicSolver` that removes vets not available at the selected clinic on the appointment day. The solver itself is unchanged.
- **Rationale**: Zero risk of breaking existing single-clinic flow. When `clinic_id` is not provided, the pre-filter is skipped entirely — backward compatible.
- **Alternatives considered**: Modify solver internals — rejected (high regression risk); separate multi-clinic solver — rejected (DRY violation).

### Cross-Clinic Patient Lookup (US3)
- **Decision**: `GET /api/patients` and `GET /api/patients/{id}` have no `clinic_id` filter. `home_clinic_id` is stored but used only to generate the "Home clinic" banner in the frontend.
- **Rationale**: Patient safety — a vet at Clinic B must see records from Clinic A (FR-014). Siloing by clinic is explicitly out of scope.
- **Alternatives considered**: Clinic-filtered patient list with opt-in "show all" — rejected (adds UI complexity, confusing in demo).

### Regional Manager Aggregate API (US4)
- **Decision**: Single endpoint `GET /api/clinics/summary?date=YYYY-MM-DD` returns an array of per-clinic stats: `{clinic_id, clinic_name, clinic_color, appointment_count, total_slots, utilisation_pct, high_risk_count}`.
- **Rationale**: One round-trip for the entire dashboard. Computed server-side from existing `timeblocks` and `risk_scores` tables — no new data needed.
- **Alternatives considered**: Separate endpoints per clinic — rejected (N+1 problem even at 2 clinics); WebSocket streaming — rejected (overkill for demo).

### Brand Colour Strategy (US1)
- **Decision**: Two default colours: Clinic A = `#6C63FF` (purple), Clinic B = `#00BFA6` (teal). Stored in `clinics.color_hex`. Applied as CSS custom property `--clinic-color` on the root `<body>` on clinic switch.
- **Rationale**: One CSS variable controls header accent, card border, and switcher dot — no per-component colour prop needed.
- **Alternatives considered**: Per-component colour prop — rejected (prop drilling complexity); Tailwind classes — rejected (not in stack).
