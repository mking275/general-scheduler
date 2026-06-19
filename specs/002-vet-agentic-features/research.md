# Research: Vet Clinic Agentic Features — Phase 2

## Decisions

### Symptom Extraction (F002)
- **Decision**: Keyword + pattern matching over free text (no LLM call)
- **Rationale**: Demo must work offline, instantly, and deterministically. A curated symptom dictionary (lethargy, vomiting, anorexia, limping, coughing, etc.) with duration pattern regex ("for 3 days", "since yesterday") covers 95% of realistic demo inputs.
- **Alternatives considered**: GPT-4o API call — rejected (latency, cost, network dependency); spaCy NER — rejected (overkill for demo scope, adds dependency).

### Risk Scoring (F004)
- **Decision**: Weighted rule engine (4 signals, additive scoring 0–100)
- **Rationale**: Produces explainable, deterministic scores that demo operators can reason about and predict. Scoring rules: lead time (<24h = +40, <72h = +20), visit type (wellness = +20, emergency = -30), patient history (first visit = +15, >5 visits = -15), procedure urgency (elective = +15, sick = -10).
- **Alternatives considered**: Logistic regression on historical no-show data — rejected (no real historical data exists for demo); random forest — same rejection reason.

### SOAP Note Generation (F006)
- **Decision**: Procedure-type keyed template library (5 templates: Wellness, Vaccination, Surgery, Dental, Grooming) with slot-filling from intake brief
- **Rationale**: Templates produce clinically appropriate, realistic content. Slot-filling from intake data (symptoms → Subjective) makes each note feel personalised without LLM.
- **Alternatives considered**: LLM generation from appointment context — rejected for demo scope (latency, network dependency); single generic template — rejected (not convincing to a real vet).

### Follow-Up Draft Generation (F003)
- **Decision**: Tone-keyed template library (Wellness / Surgery / Emergency) with patient name, vet name, and procedure interpolated
- **Rationale**: Same reasoning as SOAP — fast, deterministic, realistic. Three tones cover all demo appointment types.
- **Alternatives considered**: LLM — rejected; single template — rejected.

### Role State Management (F005)
- **Decision**: React `useState` in `page.tsx`, passed as prop to Dashboard
- **Rationale**: No auth required (demo scope). Session-local state is sufficient — role resets on page reload which is acceptable. Zero backend changes needed for role switching.
- **Alternatives considered**: URL-based routing per role (`/front-desk`, `/vet`) — rejected (adds complexity without demo benefit); localStorage persistence — rejected (unnecessary for demo).

### Room Status State (F005)
- **Decision**: Room status stored in SQLite `rooms` table, updated via `PUT /api/rooms/{id}/status`; frontend polls on role switch
- **Rationale**: Keeps room state server-side so it persists across role switches within the same session. Simple polling on switch is sufficient — no WebSocket needed for demo.
- **Alternatives considered**: Frontend-only state — rejected (would reset on role switch); WebSocket real-time sync — rejected (overkill for demo).

### Patient + Owner Seed Data (F001)
- **Decision**: 10 patients across 4 species (dogs, cats, exotic, bird), 3 flags (alert, chronic, first-visit), seeded at backend startup if table is empty
- **Rationale**: Realistic variety demonstrates the system's handling of different clinical contexts. 10 patients maps naturally to 3 vets × ~3 appointments each.
- **Alternatives considered**: Fewer patients — rejected (not enough variety to be convincing); more patients — unnecessary for demo scope.
