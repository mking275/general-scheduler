# Phase 3 Design Document — Clinical Operations
**Feature Branch**: `004-phase3-clinical-operations`  
**Created**: 2026-06-19  
**Status**: Pre-Spec (feeds into speckit specify)  
**Depends on**: Phase 1 (scheduler), Phase 2 (F001–F006 agentic pipeline), Phase 3 (F007 multi-clinic)  
**Excludes**: F017 Invoice Drafts → deferred to Financial Module

## Overview

Phase 3 closes the operational gaps that prevent the system from being a credible full Practice Management platform. Phase 2 established the agentic pipeline (intake → SOAP → follow-up). Phase 3 extends it to cover the full patient lifecycle: reminders, refills, preventive care, and clinical intelligence — the things that make owners stay with a clinic long-term.

### Build Order

Per gap analysis prioritisation:

| # | Feature | Priority | Rationale |
|---|---|---|---|
| F013 | Appointment Reminder & Confirmation Agent | P1 | Most visible gap — we book and tell no one |
| F018 | Breed-Specific Clinical Intelligence | P1 (quick win) | Low effort, high clinical credibility |
| F014 | Waitlist & Smart Cancellation Backfill | P2 | Revenue recovery, best demo moment |
| F015 | Preventive Care & Wellness Plan Tracking | P2 | Recurring revenue engine, retention driver |
| F016 | Prescription Management | P2 | Safety + legal requirement |
| F019 | Capacity & Revenue Forecasting | P3 | Executive/growth story for Regional Manager |

---

## F013 — Appointment Reminder & Confirmation Agent

### Problem Statement

Appointments are booked but owners receive zero outbound communication. F004 (No-Show Risk) flags which appointments are at risk but provides no mechanism to prevent them. The most-cited deficiency in SMB veterinary software is "reminders that don't actually work" — specifically one-way blast SMS with no confirmation loop.

### User Story

> As a front desk worker, I want the system to automatically send a confirmation request to owners 48 hours before their appointment and track whether they've confirmed — so I know exactly which appointments are at risk without making any calls myself.

### Agentic Pipeline Design

```
T-48h trigger on all upcoming appointments:
  REMINDER AGENT:
    → Compose confirmation message:
        "Hi [Owner]! Reminder: [Pet] has an appointment [Day] at [Time] 
         with [Vet]. Please reply YES to confirm or RESCHEDULE to find 
         a new time."
    → Set confirmation_status = 'sent'
    → Log: "REMINDER AGENT: Confirmation sent to [Owner]"

Owner replies YES:
    → confirmation_status = 'confirmed'
    → Risk score updated: -20 points (owner engaged)
    → Log: "REMINDER AGENT: Confirmed by owner ([X]min after send)"

Owner replies RESCHEDULE:
    → confirmation_status = 'reschedule_requested'
    → Slot freed, waitlist checked (triggers F014 if built)
    → Log: "REMINDER AGENT: Reschedule requested — slot released"

No reply by T-24h:
    → confirmation_status = 'unconfirmed'
    → Flag surfaced in Front Desk "Action Queue"
    → Log: "REMINDER AGENT: No response — flagged for follow-up call"

T-2h reminder (all confirmed appointments):
    → Short reminder: "See you today at [Time]! [Clinic address]"
```

**Demo mode**: No real SMS. Owner "replies" via a mock response panel in the UI — same pattern as the intake agent (F002). The demo operator types a response to simulate the owner, showing the agent processing it in real time.

### UI / UX Spec

**On every appointment card (Front Desk + Vet views):**
- Confirmation status badge alongside the existing intake/risk badges:
  - `📲 Confirmed` — green
  - `⏳ Pending` — grey (reminder sent, no reply yet)
  - `⚠ Unconfirmed` — amber (T-24h passed, no reply)
  - `📞 Call Needed` — red (T-4h, still unconfirmed)
  - `🔄 Reschedule` — purple (owner requested new time)

**New "Action Queue" panel in Front Desk view:**
- Header: `⚡ Needs Attention (3)` — count of unconfirmed appointments
- Each row: patient name, appointment time, status badge, "Send Reminder" button, "Mark Confirmed" (manual override for phone calls)
- Collapsed by default, expands on click

**Mock owner response panel:**
- Appears below the appointment card when status is 'sent'
- Text area: "Simulate owner reply…" with preset buttons: [YES] [RESCHEDULE] [Type custom reply]
- Verbose Log shows full agent processing chain on submit

**Verbose Log entries:**
```
REMINDER AGENT: Scheduled confirmation for [Owner] (appt: [Date Time])
REMINDER AGENT: Confirmation sent to [Owner]
REMINDER AGENT: Owner reply received — "YES"
REMINDER AGENT: Appointment [ID] confirmed ✓ · Risk score updated
```

### Backend Requirements

**Schema additions:**
- `confirmation_status` TEXT on `timeblocks` table: `not_sent | sent | confirmed | unconfirmed | reschedule_requested`
- `confirmed_at` TEXT (ISO datetime, nullable)
- `reminder_sent_at` TEXT (ISO datetime, nullable)

**New endpoints:**
- `POST /api/appointments/{id}/send-reminder` — set status to 'sent', log agent step
- `POST /api/appointments/{id}/confirm` — body: `{ reply: "YES" | "RESCHEDULE" | str }` — processes reply, updates status, adjusts risk score
- `GET /api/appointments/action-queue` — returns all appointments with status: unconfirmed or reschedule_requested, sorted by appointment time

**Agent file:** `backend/agents/reminder.py`
- `ReminderAgent.compose_message(timeblock, patient, owner)` → str
- `ReminderAgent.process_reply(reply_text)` → `{ intent: confirmed | reschedule | unclear, confidence: float }`
- `ReminderAgent.update_risk_on_confirm(timeblock_id)` → calls RiskScorer to recalculate

### Acceptance Criteria

1. Every appointment card shows a confirmation status badge reflecting the current state
2. Submitting "YES" via the mock panel changes the badge to Confirmed and logs the agent action
3. Submitting "RESCHEDULE" changes the badge to 🔄 Reschedule and releases the slot in the solver
4. The Action Queue shows all unconfirmed appointments with a manual override option
5. Verbose Log shows every step of the reminder agent pipeline
6. Risk score is recalculated when an appointment is confirmed (score decreases)

### Demo Talking Points

> *"The system doesn't just show you a calendar — it actively works to protect every slot. 48 hours before the appointment, it reaches out. The owner replies. The agent reads it, updates the risk score, and tells front desk exactly which two appointments still need a call. That's three hours of phone tag eliminated, every morning."*

---

## F018 — Breed-Specific Clinical Intelligence

### Problem Statement

The current system records breed as demographic data but does nothing with it clinically. Veterinary medicine is deeply breed-aware: brachycephalic dogs require modified anaesthesia protocols, Cavalier King Charles Spaniels have high rates of mitral valve disease, Maine Coon cats are prone to HCM. This knowledge exists in every vet's head — but not in any scheduling system.

### User Story

> As a veterinarian, when I open a patient record for a breed with known health predispositions, I want the system to surface relevant breed-specific protocols and age-appropriate screening suggestions — so I never miss a proactive recommendation.

### Agentic Pipeline Design

```
Patient record loaded → Breed Intelligence Agent:
  → Look up breed in protocol table (30+ breeds for demo)
  → If breed has flags:
      → Attach breed_flags[] to patient record in response
      → For each flag: { type, title, detail, age_threshold_years }
      → Filter by patient age: only surface age-appropriate flags

  → Screening suggestions (age + breed gated):
      → "Golden Retriever, 7y: Annual oncology screening recommended"
      → "German Shepherd, 5y: Hip dysplasia radiograph suggested"
      → "Persian, 4y: Renal function panel recommended annually"

  → Anaesthesia alerts (surfaced before any surgical procedure):
      → "Brachycephalic — intubate with smaller tube, extended recovery monitoring"
      → Surface as blocker-level warning on Surgery/Dental appointments
```

**Demo breed protocol table (minimum coverage):**

| Breed | Flags | Age Threshold |
|---|---|---|
| Bulldog / Pug / Shih Tzu / Boxer | Brachycephalic — anaesthesia risk | Any |
| Golden Retriever | Cancer predisposition — annual oncology screen | 6y+ |
| German Shepherd | Hip/elbow dysplasia — radiograph | 4y+ |
| Cavalier King Charles Spaniel | Mitral valve disease — cardiac auscultation | 5y+ |
| Maine Coon / Ragdoll | HCM — cardiac echo | 5y+ |
| Persian | PKD / chronic renal — renal panel | 4y+ |
| Labrador Retriever | Obesity risk / joint disease | 5y+ |
| Dobermann | DCM — cardiac screening | 4y+ |
| Dachshund | IVDD — neurological watch | Any |
| Siamese | Dental disease / respiratory — dental cleaning | 3y+ |
| Greyhound | Anaesthetic sensitivity — barbiturate caution | Any |

### UI / UX Spec

**On patient cards (all roles):**
- `🧬 Breed Protocol` banner below the patient name when breed has active flags
- Banner colour: amber for informational, red for safety-critical (anaesthesia alerts)
- Clicking opens a breed protocol popover with each flag's title and detail text

**In VetAppointmentCard expanded view:**
- Breed flags surface in the **History tab** header, before the visit list
- For surgical/dental procedures: anaesthesia flags appear as a persistent amber strip in the card header (not just in History tab — always visible when card is open)

**In SOAP Note workspace:**
- New "Breed Considerations" section appears between Subjective and Objective
- Pre-populated with age-appropriate breed flags
- Vet can acknowledge each one (checkbox) — acknowledged flags are logged in the SOAP record

**Verbose Log entries:**
```
BREED AGENT: Rex (German Shepherd, 6y) — 2 active breed protocols loaded
BREED AGENT: Hip dysplasia screening recommended (age threshold: 4y) ✓
BREED AGENT: No anaesthesia flags for this breed
```

### Backend Requirements

**Schema additions:**
- New `breed_protocols` table: `breed_pattern TEXT, flag_type TEXT, title TEXT, detail TEXT, age_threshold_years INTEGER, severity TEXT` (info | warning | critical)
- Seeded at startup from a breed protocol JSON in `backend/seed_data.py`
- `GET /api/patients/{id}/breed-flags` — returns active flags for patient's breed and current age

**Agent file:** `backend/agents/breed_intelligence.py`
- `BreedIntelligenceAgent.get_flags(breed, age_years)` → `list[BreedFlag]`
- `BreedIntelligenceAgent.get_anesthesia_warnings(breed)` → `list[BreedFlag]` (severity=critical only)
- Pattern matching on breed name (case-insensitive, partial match — "Bulldog" matches "English Bulldog", "French Bulldog")

**Extend existing endpoints:**
- `GET /api/patients/{id}` response gains `breed_flags: list[BreedFlag]`
- `POST /api/soap/draft` gains `breed_considerations: list[str]` section in output

### Acceptance Criteria

1. A French Bulldog patient shows a `🧬 Breed Protocol` banner with anaesthesia warning
2. The anaesthesia warning appears as a persistent strip on any Surgery or Dental appointment card
3. A Golden Retriever aged 7+ shows an oncology screening suggestion in the History tab
4. Breed flags appear in the "Breed Considerations" section of the SOAP draft
5. A mixed-breed or unknown breed shows no breed banner (graceful fallback)
6. Verbose Log shows breed agent loading protocols on patient record access

### Demo Talking Points

> *"The system already knows that Max is a French Bulldog. Before the vet walks in, it's flagged brachycephalic airway risk and modified the SOAP note to include the anaesthesia protocol. That's not a feature — that's institutional knowledge encoded into the workflow."*

---

## F014 — Waitlist & Smart Cancellation Backfill

### Problem Statement

Cancelled appointments leave revenue gaps with no automated recovery mechanism. A manual waitlist (if maintained at all) requires staff to phone each person in order and hope someone answers. The slot often goes unfilled.

### User Story

> As a front desk worker, when an appointment is cancelled, I want the system to automatically find the best-matched patient on the waitlist, offer them the slot, and fill it — without me making a single phone call.

### Agentic Pipeline Design

```
Appointment cancelled → Cancellation Backfill Agent:
  STEP 1 — Match:
    → Query waitlist WHERE procedure_type MATCHES cancelled.procedure
                      AND preferred_vet IN (cancelled.vet, ANY)
                      AND clinic_id = cancelled.clinic_id
    → Score matches: exact procedure + vet = 100pts, 
                     same procedure any vet = 80pts,
                     same category different procedure = 40pts
    → Select top match

  STEP 2 — Offer:
    → Compose offer: "A slot just opened up for [procedure] on 
       [Day] at [Time] with [Vet]. Want it? Reply YES within 30min."
    → Set waitlist_entry.offer_status = 'offered', offer_expires_at = now+30min
    → Log: "BACKFILL AGENT: Offer sent to [Owner] for [procedure] slot"

  STEP 3 — Resolution:
    → Owner replies YES within 30min:
        → Book appointment, remove from waitlist
        → Log: "BACKFILL AGENT: Slot filled — [Pet] booked"
    → No reply / NO:
        → Offer next match (up to 3 attempts)
        → If no takers: slot marked Available, front desk notified
        → Log: "BACKFILL AGENT: No takers after 3 attempts — slot open"
```

**Demo mode**: Offers/replies simulated via mock panel — same pattern as Intake (F002) and Reminder (F013).

### UI / UX Spec

**"Add to Waitlist" button:**
- Appears on appointment cards when the preferred slot is full
- Also available as a standalone "Join Waitlist" action in the quick-book input
- Captures: preferred procedure, preferred vet (optional), any clinic / specific clinic, urgency (flexible / within 1 week / ASAP)

**Waitlist indicator in Front Desk header:**
- `📋 Waitlist (4)` badge next to the clinic name
- Click opens the Waitlist panel: list of all waitlisted patients, sorted by urgency + join date
- Each row: patient name, procedure, preferred vet, wait duration, status (waiting / offer sent / expired)

**Cancellation flow:**
- When staff marks an appointment cancelled, a "Run Backfill Agent?" prompt appears
- If confirmed: Verbose Log fills with the backfill agent chain in real time
- This is the primary demo moment for this feature — the full agent chain visible step by step

**Verbose Log entries:**
```
BACKFILL AGENT: Cancellation detected — [Procedure] slot freed at [Time]
BACKFILL AGENT: Searching waitlist for procedure match...
BACKFILL AGENT: Match found — Daisy (Dental Cleaning) · Score: 100pts
BACKFILL AGENT: Offer sent to owner (Sarah M.) · Expires in 30min
BACKFILL AGENT: Owner accepted! Daisy booked for [Date Time] ✓
```

### Backend Requirements

**New table: `waitlist`**
```sql
CREATE TABLE IF NOT EXISTS waitlist (
    id TEXT PRIMARY KEY,
    patient_id TEXT NOT NULL,
    clinic_id TEXT,
    procedure_type TEXT NOT NULL,
    preferred_vet_id TEXT,
    urgency TEXT DEFAULT 'flexible',  -- flexible | within_week | asap
    joined_at TEXT NOT NULL,
    offer_status TEXT DEFAULT 'waiting',  -- waiting | offered | accepted | expired
    offer_sent_at TEXT,
    offer_expires_at TEXT,
    filled_timeblock_id TEXT
);
```

**New endpoints:**
- `POST /api/waitlist` — add patient to waitlist
- `GET /api/waitlist` — list all active waitlist entries (clinic-filtered)
- `DELETE /api/waitlist/{id}` — remove entry
- `POST /api/appointments/{id}/cancel` — cancel appointment, optionally trigger backfill
- `POST /api/waitlist/backfill/{cancelled_timeblock_id}` — run backfill agent against a specific freed slot
- `POST /api/waitlist/{id}/respond` — simulate owner response: `{ accept: bool }`

**Agent file:** `backend/agents/backfill.py`
- `BackfillAgent.find_matches(timeblock)` → `list[WaitlistMatch]` scored
- `BackfillAgent.run_backfill(timeblock_id)` → logs full chain, returns result

### Acceptance Criteria

1. Patient can be added to waitlist with procedure, preferred vet, urgency
2. Cancelling an appointment triggers the backfill agent flow (with confirmation prompt)
3. Verbose Log shows the full match-score-offer-accept chain
4. Accepting fills the slot — appointment appears on the schedule board
5. After 3 failed offers, the slot is marked open and front desk is notified
6. Waitlist count badge in header reflects current active entries

### Demo Talking Points

> *"A patient just cancelled. Watch — the agent checks the waitlist, finds Daisy who's been waiting 3 days for a dental slot, sends her an offer, and 30 seconds later her appointment is on the board. No phone calls. No hold music. Just a slot that was going to be empty, filled by an agent."*

---

## F015 — Preventive Care & Wellness Plan Tracking

### Problem Statement

Vaccination schedules, annual wellness reminders, and parasite prevention protocols are the financial backbone of a veterinary practice — but they're almost universally managed in paper card files or separate spreadsheets entirely disconnected from the scheduling system. Clinics lose recurring appointments because reminders never get sent.

### User Story

> As a veterinarian, after completing a vaccination appointment, I want the system to automatically record what was administered and compute the next-due date — and as a front desk worker, I want a daily list of which patients have upcoming or overdue preventive care so I can proactively reach out.

### Agentic Pipeline Design

```
Appointment completed (procedure = Vaccination / Wellness):
  CARE TRACKER AGENT:
    → Record care event:
        { patient_id, event_type, administered_date, 
          batch_number, next_due_date, protocol_id }
    → Compute next_due_date from protocol:
        Rabies: annually (or 3-yearly based on product)
        DHPP: annually after puppy series
        Bordetella: 6 months
        Heartworm: annually (test + prevention)
        Wellness exam: annually
    → Queue reminder: T-30d before next_due_date
    → Log: "CARE AGENT: [Vaccine] recorded · Next due [Date]"

Daily (front desk load):
  → Surface all patients with next_due_date within 30 days
  → Surface all patients with overdue care (next_due_date < today)
  → Outreach queue: patient name, care type, due date, days overdue

Proactive outreach trigger (T-30d):
  → "Hi [Owner]! [Pet]'s [care_type] is due in ~30 days. 
     Would you like to book? Reply BOOK or LATER."
  → Demo: mock reply panel, same as F013 pattern
```

**Care protocols seeded for demo:**

| Protocol ID | Species | Description | Interval |
|---|---|---|---|
| RABIES_ANNUAL | Dog/Cat | Rabies vaccine | 12 months |
| DHPP | Dog | Core dog vaccine | 12 months |
| FVRCP | Cat | Core cat vaccine | 12 months |
| BORDETELLA | Dog | Kennel cough | 6 months |
| HEARTWORM_TEST | Dog | Annual HW test | 12 months |
| WELLNESS_EXAM | All | Annual wellness | 12 months |
| DENTAL_CLEANING | All | Dental hygiene | 12 months |
| FeLV | Cat | Feline leukemia | 12 months |

### UI / UX Spec

**New "Care Plan" tab in VetAppointmentCard:**
- Vaccination timeline (visual, chronological): past events as solid dots, future dues as outlined dots
- Each event: date, care type, vet who administered, batch number (if vaccine)
- Overdue items: red badge `⚠ OVERDUE — 32 days`
- Upcoming items: amber badge `📅 Due in 18 days`
- "Record Care Event" button for logging manually or from current appointment

**Patient card flag additions:**
- `🔴 OVERDUE` flag badge when any care item is past due
- `📅 DUE SOON` flag badge when any care item is within 30 days

**Front Desk "Preventive Care" panel (alongside Action Queue from F013):**
- "📋 Care Due This Month (7)" collapsible panel
- Table: Patient | Care Type | Due Date | Days Until/Overdue | "Book" button
- Sorted: overdue first (red), then upcoming (amber)
- "Book" button opens the quick-book input pre-populated with patient + procedure

**Verbose Log entries:**
```
CARE AGENT: Appointment complete — recording vaccination events
CARE AGENT: DHPP administered to Buddy · Batch: VX-2026-441
CARE AGENT: Next due: 2027-06-18 · Reminder queued T-30d
CARE AGENT: Bordetella due in 28 days for Rex · Added to outreach queue
```

### Backend Requirements

**New tables:**
```sql
CREATE TABLE IF NOT EXISTS care_protocols (
    id TEXT PRIMARY KEY,
    species TEXT NOT NULL,          -- dog | cat | all
    protocol_name TEXT NOT NULL,
    interval_months INTEGER NOT NULL,
    description TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS care_events (
    id TEXT PRIMARY KEY,
    patient_id TEXT NOT NULL,
    protocol_id TEXT NOT NULL,
    administered_date TEXT NOT NULL,
    administered_by TEXT DEFAULT '',
    batch_number TEXT DEFAULT '',
    next_due_date TEXT NOT NULL,
    reminder_sent INTEGER DEFAULT 0,
    timeblock_id TEXT               -- linked appointment if applicable
);
```

**New endpoints:**
- `GET /api/patients/{id}/care-plan` — full care event history + upcoming dues
- `POST /api/patients/{id}/care-events` — log a new care event (auto-computes next_due_date from protocol)
- `GET /api/care/due-this-month` — all patients with due/overdue care (clinic-filtered)
- `POST /api/care/{event_id}/remind` — trigger proactive outreach (mock)

**Agent file:** `backend/agents/care_tracker.py`
- `CareTrackerAgent.record_event(timeblock_id)` → extracts procedure, logs care events
- `CareTrackerAgent.compute_next_due(protocol_id, administered_date)` → date
- `CareTrackerAgent.get_overdue(clinic_id)` → list of overdue patient/protocol pairs

**Seed data:** Populate 1–3 historical care events per demo patient with realistic dates, plus 2–3 upcoming/overdue items for demo visibility.

### Acceptance Criteria

1. Completing a vaccination appointment auto-triggers care event recording
2. Care Plan tab shows timeline with past events and next-due dates
3. Overdue patients show `🔴 OVERDUE` badge on their appointment card
4. Front Desk Care panel shows all due-this-month patients with Book button
5. Book button pre-populates the quick-book with the correct patient and procedure
6. Verbose Log shows care tracker agent steps on appointment completion

### Demo Talking Points

> *"Buddy got his DHPP today. The agent recorded the batch number, computed next June as the due date, and queued a reminder for May. In 11 months, this clinic will get a fresh appointment without making a single phone call. That's recurring revenue on autopilot."*

---

## F016 — Prescription Management

### Problem Statement

After every visit where medication is prescribed, nothing in the current system records what was given, at what dose, for how long, or how many refills remain. Refill requests arrive by phone. Staff manually pull the paper record. The vet manually verifies. This happens dozens of times per week.

### User Story

> As a veterinarian, I want to issue a prescription from within the SOAP note, and as a front desk worker, I want a refill request queue where I can approve routine refills with one click — with the system flagging anything that requires vet review.

### Agentic Pipeline Design

```
Vet creates Rx in SOAP Plan section:
  PRESCRIPTION AGENT:
    → Validate: check drug name against patient allergy list
    → If ALERT flag + penicillin-class drug:
        → Hard warning: "⚠ ALLERGY CONFLICT — patient has penicillin allergy"
        → Require vet to acknowledge before saving
    → Create prescription record: drug / dose / frequency / duration / refills_remaining
    → Compute supply_ends_at: today + (duration_days)
    → Schedule refill reminder: supply_ends_at - (duration_days * 0.2)
        e.g. 30-day supply → reminder at day 24
    → Log: "PRESCRIPTION AGENT: Rx issued — [Drug] [dose] x [duration]d · [N] refills"

Refill request arrives (owner calls or requests via portal):
  REFILL AGENT:
    → Check: is prescription on record? → yes
    → Check: refills_remaining > 0? → yes
    → Check: last exam within 12 months? → yes (safe to auto-approve)
    → Auto-approve: decrement refills_remaining, set refill_date
    → Notify: "Refill approved. Ready for pickup."
    → Log: "REFILL AGENT: Auto-approved — [Drug] refill #[N] for [Patient]"

    → If any check fails:
    → Status: 'needs_vet_review'
    → Add to vet review queue
    → Log: "REFILL AGENT: Refill flagged for review — [reason]"
```

### UI / UX Spec

**New "Rx" tab in VetAppointmentCard (next to Labs):**
- Active prescriptions list: drug name, dose, frequency, start date, supply end date, refills remaining
- "Issue Prescription" form:
  - Drug name (free text + typeahead from common vet drug list)
  - Dose + unit selector (mg, mg/kg, mL)
  - Frequency (SID / BID / TID / QID / PRN)
  - Duration (days) or "Ongoing"
  - Refills (0–5)
  - Notes field
- Allergy conflict warning: red banner if drug class matches patient allergy flag
- "Issue Rx" button → saves and triggers prescription agent

**Patient record prescription history:**
- Past prescriptions listed in History tab with date, drug, vet, status (active / completed / cancelled)

**Front Desk "Refill Queue" panel:**
- `💊 Refill Requests (2)` collapsible panel
- Each row: patient name, drug, refills remaining, last exam date, auto-approve status
  - Green `✓ Auto-approve` if all checks pass — one-click confirm
  - Amber `⚠ Vet Review` if exam expired or refills exhausted
- Approving logs the action and updates the prescription record

**Common vet drug typeahead list (demo seed):**
Amoxicillin, Carprofen, Metronidazole, Prednisone, Enalapril, Furosemide, Phenobarbital, Gabapentin, Apoquel, Cytopoint, Thyroid (Methimazole), Famotidine, Omeprazole, Tramadol, Doxycycline

**Verbose Log entries:**
```
PRESCRIPTION AGENT: Rx issued — Carprofen 25mg BID x 14d · 2 refills
PRESCRIPTION AGENT: No allergy conflicts detected ✓
REFILL AGENT: Refill request received — Buddy / Carprofen
REFILL AGENT: All checks passed (exam: 3 months ago · refills: 2 remaining)
REFILL AGENT: Auto-approved ✓ · Refills remaining: 1
```

### Backend Requirements

**New tables:**
```sql
CREATE TABLE IF NOT EXISTS prescriptions (
    id TEXT PRIMARY KEY,
    patient_id TEXT NOT NULL,
    timeblock_id TEXT,
    drug_name TEXT NOT NULL,
    dose TEXT NOT NULL,
    frequency TEXT NOT NULL,
    duration_days INTEGER,
    is_ongoing INTEGER DEFAULT 0,
    refills_total INTEGER DEFAULT 0,
    refills_remaining INTEGER DEFAULT 0,
    issued_by TEXT NOT NULL,
    issued_at TEXT NOT NULL,
    supply_ends_at TEXT,
    status TEXT DEFAULT 'active'    -- active | completed | cancelled
);

CREATE TABLE IF NOT EXISTS refill_requests (
    id TEXT PRIMARY KEY,
    prescription_id TEXT NOT NULL,
    requested_at TEXT NOT NULL,
    status TEXT DEFAULT 'pending',  -- pending | approved | needs_review | denied
    reviewed_by TEXT,
    reviewed_at TEXT,
    notes TEXT DEFAULT ''
);
```

**New endpoints:**
- `POST /api/prescriptions` — issue Rx (includes allergy check logic)
- `GET /api/prescriptions/patient/{patient_id}` — full Rx history
- `POST /api/prescriptions/{id}/refill-request` — log incoming refill request
- `GET /api/prescriptions/refill-queue` — all pending refill requests (clinic-filtered)
- `POST /api/prescriptions/refill-requests/{id}/approve` — approve refill
- `POST /api/prescriptions/refill-requests/{id}/flag` — send to vet review

**Agent file:** `backend/agents/prescription.py`
- `PrescriptionAgent.issue(rx_data, patient)` → allergy check + save
- `PrescriptionAgent.check_allergy_conflict(drug_name, patient_flags)` → bool + detail
- `RefillAgent.evaluate(refill_request)` → `{ auto_approve: bool, reason: str }`

**Seed data:** 1–2 active prescriptions per demo patient with varied refill states.

### Acceptance Criteria

1. Vet can issue a prescription from the Rx tab in VetAppointmentCard
2. Allergy conflict shows a red warning when drug class matches patient flag
3. Prescription appears in patient History tab with full details
4. Refill Queue in Front Desk view shows pending requests with auto-approve status
5. One-click approve updates refills_remaining and logs agent action
6. Requests flagged for vet review remain in queue with amber status
7. Verbose Log shows full prescription and refill agent chains

### Demo Talking Points

> *"The vet prescribes Carprofen right from the SOAP note. The agent checks for allergies — clear. Two weeks later the owner calls for a refill. The system checks: exam was 3 months ago, one refill remaining — auto-approved. The front desk clicked one button. The vet wasn't involved. That's a workflow that runs itself."*

---

## F019 — Capacity & Revenue Forecasting

### Problem Statement

The Regional Manager view shows what happened (historical heat map) and what's booked (forward calendar). It tells the manager nothing about whether they're on track for a good month — or which location is trending toward a revenue shortfall.

### User Story

> As a regional manager, I want to see a 4-week revenue and capacity forecast alongside the historical actuals — with a plain-English insight card telling me what I should do about it.

### Agentic Pipeline Design

```
On Regional Manager view load → Forecast Agent:
  INPUT: Last 8 weeks of actuals per clinic
         (appointment count, procedure mix, day-of-week patterns)

  STEP 1 — Trend analysis:
    → Compute weekly totals for past 8 weeks
    → Fit linear trend: is volume growing, flat, or declining?
    → Compute avg appointments / week, avg revenue / week
      (revenue = appointments × avg_procedure_value from fee schedule)

  STEP 2 — Forward projection (4 weeks):
    → Apply trend to next 4 weeks
    → Layer in existing bookings (actual booked appointments already in DB)
    → Compute: projected_total = existing_booked + trend_projected_unbooked
    → Compute: booking_gap = projected_total - target_capacity (e.g. 90% utilisation)

  STEP 3 — Insight generation (template-based):
    → If declining trend + booking gap > 15%:
        "Downtown is tracking 18% below last month's pace.
         At current booking rate, [N] slots will go unfilled this week.
         Consider a targeted wellness promotion."
    → If strong growth:
        "Westside is up 22% month-over-month. Consider adding 
         a vet day or extending hours to meet demand."
    → If on-target:
        "Both clinics are tracking to plan. Downtown: 87% utilisation 
         forecast. Westside: 91%."
```

### UI / UX Spec

**New "Forecast" section in Regional Manager view (below the clinic cards):**
- Header: `📈 4-Week Forecast`
- Side-by-side bars: one bar group per clinic
  - 4 forward bars (weeks 1–4): projected total appointments
  - Existing booked shown as solid fill, projected unbooked as hatched/lighter fill
  - Red dotted line = target capacity
- Below bars: AI Insight card
  - Icon: 💡
  - Plain English 2–3 sentence insight
  - If action recommended: orange border, "Action Suggested" badge
  - If on-track: green border, "On Track" badge

**Revenue projection (optional display toggle):**
- Toggle "Show Revenue Estimate" → bars relabel as revenue ($) using avg procedure value
- Revenue estimated from procedure mix × seeded fee schedule values

**Verbose Log entries:**
```
FORECAST AGENT: Analysing 8-week trend for Downtown Clinic...
FORECAST AGENT: Trend: -4.2 appts/week · Current pace: 19 appts/week
FORECAST AGENT: Projected week 1: 22 appts (18 booked + 4 projected)
FORECAST AGENT: Insight generated — below-target trajectory detected
```

### Backend Requirements

**New endpoint:**
- `GET /api/clinics/forecast?weeks_back=8&weeks_forward=4` — returns per-clinic:
  - `actuals: [{ week_start, appointment_count, revenue_estimate }]` (8 weeks)
  - `forecast: [{ week_start, booked_count, projected_count, capacity_target }]` (4 weeks)
  - `insight: { summary: str, status: on_track | action_needed | strong_growth }`

**Agent file:** `backend/agents/forecast.py`
- `ForecastAgent.compute_trend(clinic_id, weeks_back)` → slope, intercept, r²
- `ForecastAgent.project_forward(clinic_id, weeks_forward, trend)` → list of weekly projections
- `ForecastAgent.generate_insight(clinic_id, projections)` → insight dict (template-based)

**Fee schedule** (seed in `backend/seed_data.py`):
| Procedure | Avg Value |
|---|---|
| Wellness Exam | $85 |
| Vaccination (per shot) | $35 |
| Surgery | $650 |
| Dental Cleaning | $320 |
| General Practice | $120 |
| X-Ray | $175 |
| Ultrasound | $220 |

### Acceptance Criteria

1. Regional Manager view shows a 4-week forecast section below clinic cards
2. Each clinic has 4 projected bars with booked vs. projected fill distinction
3. A target capacity line is visible on the chart
4. AI Insight card shows a plain-English 2–3 sentence summary per clinic
5. Declining trend clinics show "Action Suggested" badge with an amber border
6. On-track clinics show "On Track" badge with a green border
7. Verbose Log shows forecast agent computation steps

### Demo Talking Points

> *"The heat map tells you what happened. The forecast tells you what's coming. Downtown is trending 18% below last month — the agent already knows, and it's suggesting a wellness promotion. This is the difference between a reporting tool and a management tool."*

---

## Shared Design Constraints (All F013–F019)

These apply to every feature in this phase, per the project constitution:

| Constraint | Detail |
|---|---|
| **Demo-first** | Every agent action must appear in the Verbose Log. If it's not visible, it doesn't count. |
| **No external services** | All outbound communication (SMS, email) is mocked. Owner replies simulated via in-UI panel. |
| **No new dependencies** | Python stdlib + existing pip packages only. No new npm packages on frontend. |
| **Role-aware** | Every feature must declare its primary role owner. Features that span roles must work in both. |
| **Seed data required** | Each feature must ship with realistic demo data seeded at startup. |
| **Backward compatible** | No feature may break the existing v1.0.0 demo. Schema changes via `ALTER TABLE` with try/except. |
| **SQLite only** | No external databases, no Redis, no message queues for demo scope. |

## Role Ownership Summary

| Feature | Primary Role | Also Visible In |
|---|---|---|
| F013 Reminders | Front Desk (Action Queue) | All roles (status badge on cards) |
| F018 Breed Intel | Veterinarian (SOAP, card) | All roles (patient card banner) |
| F014 Waitlist | Front Desk (Waitlist panel) | — |
| F015 Wellness Plans | Front Desk (Care panel) | Vet (Care Plan tab) |
| F016 Prescriptions | Veterinarian (Rx tab) | Front Desk (Refill Queue) |
| F019 Forecasting | Regional Manager | — |

## Success Criteria (Phase 3)

- **SC-P3-001**: A demo operator can demonstrate F013 (full reminder → confirm cycle) in under 90 seconds
- **SC-P3-002**: F018 breed warning appears on a brachycephalic patient's surgical appointment without any extra clicks
- **SC-P3-003**: F014 backfill agent chain is fully visible in Verbose Log within 5 seconds of cancellation
- **SC-P3-004**: F015 Care Plan tab shows at least 2 overdue items for demo patients on fresh startup
- **SC-P3-005**: F016 allergy conflict warning fires on Rx issuance for any ALERT-flagged patient
- **SC-P3-006**: F019 Forecast section loads within 2 seconds of Regional Manager view activation
- **SC-P3-007**: All Phase 3 features operate on top of v1.0.0 data without a database wipe
