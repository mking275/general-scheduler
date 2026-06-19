# Research: Phase 3 Clinical Operations

**Feature**: specs/005-phase3-clinical-ops  
**Date**: 2026-06-19  
**Purpose**: Resolve all technical decisions before plan.md is written

---

## Decision Log

### D001 — Schema migration strategy
- **Decision**: ALTER TABLE with `try/except` around each column addition, consistent with F007 pattern
- **Rationale**: SQLite has no `IF NOT EXISTS` for columns; try/except is the established project pattern from `repository.py`
- **Alternatives considered**: DROP + recreate (destructive, unacceptable); migration versioning table (overkill for demo)

### D002 — Reminder status storage
- **Decision**: Add `confirmation_status`, `confirmed_at`, `reminder_sent_at` columns to `timeblocks` table via ALTER TABLE
- **Rationale**: Confirmation is 1:1 with a TimeBlock; no separate table needed; consistent with how `followup_status` is already stored on timeblocks
- **Alternatives considered**: Separate `confirmations` table (unnecessary join complexity for demo)

### D003 — Breed protocol data
- **Decision**: Seed `breed_protocols` table in `seed_data.py` with 12 entries covering: French Bulldog, English Bulldog, Pug, Boston Terrier (brachycephalic), Golden Retriever, Labrador (oncology screening), German Shepherd (hip dysplasia), Cavalier King Charles Spaniel (cardiac), Doberman (DCM), Dachshund (IVDD), Maine Coon (HCM), Persian (PKD)
- **Rationale**: Covers 3 major clinical concern clusters; enough variety for credible demo; partial-match pattern handles breed name variants
- **Alternatives considered**: Hard-coding in agent logic (not extensible); external CSV (unnecessary complexity)

### D004 — Waitlist backfill agent architecture
- **Decision**: New `backend/agents/backfill.py` with `BackfillAgent` class; synchronous scoring loop returning ordered match list; called from cancellation endpoint
- **Rationale**: Consistent with existing agent pattern (intake.py, risk.py, etc.); scoring is pure Python, no external calls; Verbose Log via existing `log_agent_step()`
- **Alternatives considered**: Background task (unnecessary for demo; breaks Verbose Log real-time feel)

### D005 — Care protocol intervals
- **Decision**: `care_protocols` table seeded with 8+ entries: DHPP (12mo dogs), Rabies (12mo all), Bordetella (6mo dogs), FVRCP (12mo cats), FeLV (12mo cats <2y), Leptospirosis (12mo dogs), Heartworm test (12mo dogs), Dental (12mo all)
- **Rationale**: Covers the most common preventive care types a vet professional would expect; 8+ satisfies FR-P3-007
- **Alternatives considered**: Species-agnostic protocols (less clinically accurate)

### D006 — Prescription drug list
- **Decision**: Seeded in-memory list of 20 common vet drugs in `backend/agents/prescription.py`: Carprofen, Meloxicam, Amoxicillin, Cephalexin, Metronidazole, Prednisone, Enalapril, Furosemide, Phenobarbital, Tramadol, Gabapentin, Apoquel, Cytopoint, Doxycycline, Clindamycin, Trazodone, Acepromazine, Maropitant (Cerenia), Omeprazole, Onsior
- **Rationale**: 20 drugs > 15 minimum (FR-P3-010); covers NSAIDs, antibiotics, cardiac, neuro, dermatology — credible to a vet
- **Alternatives considered**: Static JSON file (unnecessary for demo); database table (over-engineered)

### D007 — Drug-class allergy map
- **Decision**: Hardcoded dict in `prescription.py`: `{"penicillin": ["amoxicillin", "ampicillin"], "nsaid": ["carprofen", "meloxicam", "onsior"], "sulfa": ["sulfamethoxazole"], "cephalosporin": ["cephalexin", "cefpodoxime"]}`. Patient ALERT flags checked against drug class keywords.
- **Rationale**: Sufficient for demo; no external drug DB needed; constitution bars new dependencies
- **Alternatives considered**: OpenFDA drug interaction API (external service, out of scope)

### D008 — Forecast calculation
- **Decision**: Linear regression (slope = Σ(xi-x̄)(yi-ȳ)/Σ(xi-x̄)²) over 8 weeks of seeded historical data in `backend/agents/forecast.py`; no scipy/numpy — pure Python stdlib math
- **Rationale**: Constitution bars new pip packages; stdlib `statistics` module sufficient; slope → status classification is the key demo output
- **Alternatives considered**: Moving average (simpler but less impressive); numpy linear_model (requires new dependency)

### D009 — Frontend chart rendering (Forecast bars)
- **Decision**: CSS bar chart with `div` elements and percentage-height; no charting library
- **Rationale**: No new npm packages (constitution); pure CSS achieves the booked/projected visual distinction via solid vs. hatched background patterns; capacity line as absolute-positioned hr
- **Alternatives considered**: Chart.js (new npm dependency, banned); Recharts (banned); SVG path (complex, no library)

### D010 — Care event timeblock linkage (Q3 answer: B)
- **Decision**: `timeblock_id` nullable FK in `care_events`; demo primary path auto-populates it from appointment completion; "Log Historical" form leaves it null
- **Rationale**: Per clarification Q3: standalone care events must be supported

### D011 — Refill request dual entry points (Q1 answer: C)
- **Decision**: Both entry points write to same `refill_requests` table; Vet path: `POST /api/prescriptions/{id}/refill-request`; Front Desk path: same endpoint called from panel; `initiated_by` field records role
- **Rationale**: Per clarification Q1: either role can initiate

### D012 — Reminder button label logic (Q4 answer: C)
- **Decision**: Client-side computation in `AppointmentCard.tsx`: `const daysOut = Math.ceil((apptDate - today) / 86400000); label = daysOut > 2 ? 'Send Reminder (Early — T-48h+)' : 'Send Reminder (Due — T-24h)'`
- **Rationale**: Per clarification Q4: no server cron; label reflects timing

---

## Existing Codebase Integration Points

### Backend files to extend
| File | Extension needed |
|---|---|
| `backend/repository.py` | Add 7 new tables + ALTER TABLE migrations; new CRUD methods for each entity |
| `backend/main.py` | New endpoints for reminders, breed flags, waitlist, care, prescriptions, forecasting |
| `backend/seed_data.py` | Seed breed_protocols, care_protocols, drug list, waitlist entries, historical appointments |
| `backend/models.py` | New Pydantic models: WaitlistEntry, CareProtocol, CareEvent, Prescription, RefillRequest, BreedProtocol, ForecastResult |

### New backend agent files
| File | Purpose |
|---|---|
| `backend/agents/reminder.py` | ReminderAgent — compose message, update confirmation_status |
| `backend/agents/breed.py` | BreedIntelligenceAgent — match patient breed against breed_protocols |
| `backend/agents/backfill.py` | BackfillAgent — score waitlist entries against cancelled slot |
| `backend/agents/care.py` | CareTrackerAgent — compute next_due_date, identify overdue patients |
| `backend/agents/prescription.py` | PrescriptionAgent — drug list, allergy conflict check, refill eligibility |
| `backend/agents/forecast.py` | ForecastAgent — linear regression, status classification, insight text |

### Frontend components to extend
| File | Extension needed |
|---|---|
| `AppointmentCard.tsx` | Confirmation status badge, Send Reminder button + mock reply panel |
| `VetAppointmentCard.tsx` | Breed banner, Care Plan tab, Rx tab |
| `Dashboard.tsx` | Action Queue panel, Care Due panel, Refill Requests panel (Front Desk); Forecast section (Regional Manager) |

### New frontend components
| File | Purpose |
|---|---|
| `ReminderPanel.tsx` | Mock owner reply panel with YES/RESCHEDULE/text input |
| `WaitlistPanel.tsx` | Waitlist management: add entry, backfill offer UI |
| `ForecastChart.tsx` | CSS bar chart with booked/projected fill + capacity line |
