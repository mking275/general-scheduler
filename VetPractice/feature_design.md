# Feature Design Document — Paws & Claws Agentic Scheduler
**Based on:** VetPractice research report + current demo architecture  
**Status:** Design / Pre-Build  

---

## F001 — Patient Record Card on Appointments

### Problem it solves
Scheduled appointment cards currently show procedure, vet, room, and date — but nothing about the *patient*. In a real clinic, front desk staff need to instantly see who's coming in and why.

### User Story
> As a front desk worker, when I look at the schedule board, I want to see the patient's name, species, breed, and any flagged history (allergies, aggression, chronic conditions) so I can prepare the room and brief the vet *before* they walk in.

### Agentic Pipeline Design
This is a **data enrichment** step that runs at dispatch time:
```
DISPATCH → Patient Lookup Agent
  → if patient exists in DB: attach record to TimeBlock
  → if new patient: create stub record, flag as "First Visit"
  → TimeBlock now carries: { patient, flags, visit_count, last_visit_date }
```

### UI / UX Spec
**Appointment card expands to show:**
- Pet avatar icon (species-based: dog 🐕 cat 🐈 bird 🦜 exotic 🦎)
- Patient name + breed in bold
- Age + weight (last recorded)
- Colour-coded flag badges:
  - 🔴 **ALERT** — known aggression, allergy, or anesthesia risk
  - 🟡 **CHRONIC** — ongoing condition (diabetes, heart disease)
  - 🟢 **FIRST VISIT** — no prior history on file
- Last visit date + what it was for
- Owner name + phone number (tap-to-call on mobile)

**Interaction:** Cards are collapsed by default (current view). Clicking expands to show the patient panel. A "patient detail" modal opens on double-click with full history.

### Backend Requirements
- New `Patient` model: `{ id, name, species, breed, dob, weight_kg, flags[], owner_id, visit_history[] }`
- New `Owner` model: `{ id, name, phone, email, pets[] }`
- `TimeBlock` gains `patient_id` foreign key
- `GET /api/patients` — list all patients
- `POST /api/patients` — create patient
- `GET /api/patients/{id}` — patient detail
- Seed mock data: 8-10 patients with varied histories, flags, breeds

### Demo Talking Points
> *"The moment an appointment is booked, the agent enriches it with the patient's full context — the vet walks in already knowing this dog has an anesthesia allergy. That's a safety feature, not just a UX improvement."*

---

## F002 — Pre-Visit Intake Agent *(upgraded v1.1)*

### Problem it solves
Front desk spends significant time on the phone collecting symptoms before appointments. Vets walk into exams cold — no context, no visual history. The intake agent flips both of these by reaching out to the owner automatically and collecting both symptom text **and photos** before the visit.

### User Story
> As a clinic owner, I want the system to automatically message pet owners before their appointment to collect symptoms and photos of any concerns — so my vet can read a pre-exam brief *and* see what the owner saw at home before walking into the room, with zero front desk involvement.

### Agentic Pipeline Design
```
TimeBlock created (T-24h trigger)
  → Intake Agent composes message to owner:
      "Hi Sarah! Buddy has an appointment coming up with us.
       Can you tell us what's been going on? Any symptoms, changes
       in behaviour, or concerns?
       📸 Feel free to include photos too — images of anything unusual
       you've noticed (skin conditions, swelling, discharge, changes in
       posture or gait) are really helpful for us to prepare before
       your visit."

  → Owner replies with text + optional photos
  → Symptom Extraction Agent parses text reply:
      { symptoms: ["lethargy", "not eating"], duration: "3 days",
        severity: "mild", owner_concern: "possible stomach issue" }
  → Photos stored as owner_images linked to the appointment
  → Pre-Exam Brief generated and attached to appointment:
      CHIEF COMPLAINT: Lethargy and reduced appetite x3 days
      OWNER NOTES: "He just seems off, not his usual self"
      SUGGESTED FOCUS AREAS: GI, metabolic panel
  → Vet sees brief AND owner photos before entering room
```

**In demo mode (no real SMS):** The mock owner reply panel displays the exact message that would be sent (including the photo prompt). The demo operator types a symptom response and can attach real image files to simulate what the owner sends. The full agent processing chain plays out in the Verbose Log in real time.

### UI / UX Spec
**On the appointment card:**
- `📲 Intake: ✅ Received` or `⏳ Pending` badge
- Clicking opens the **Pre-Exam Brief panel**:
  - Chief complaint (auto-extracted, formatted)
  - Symptom tags: `lethargy · 3d · mild`
  - Owner's exact words (quoted, in italics)
  - Suggested focus areas (agent-generated green tags)

**Mock owner reply panel (demo mode):**
- Displays the full message sent to the owner in a styled bubble
- Text area for symptom description
- **Photo attachment section**: file picker (accepts image/*, up to 5 files)
- Live thumbnail preview grid with per-photo remove button
- Submit button shows `Submit Response + 2 photo(s) →` when files are attached

**In the Vet's Imaging tab** (new in v1.1):
- `OWNER` badge section: **"Owner-Submitted Photos (N)"**
- Auto-fill thumbnail grid — all photos submitted during intake
- Click any thumbnail → full-screen lightbox with dark overlay and × close
- Clinical imaging studies (X-Ray, Ultrasound) render below in **"Clinical studies"** section

**In the VerboseLog:**
```
INTAKE AGENT: Sent pre-visit questionnaire to owner (Sarah M.)
INTAKE AGENT: Photo attachment option included in owner message
INTAKE AGENT: Owner response received — extracting symptoms...
INTAKE AGENT: Parsed → Lethargy (3d), Anorexia (2d), severity: mild
INTAKE AGENT: Suggested focus: GI, metabolic panel
INTAKE AGENT: 2 owner photo(s) uploaded — visible in Imaging tab
INTAKE AGENT: Pre-Exam Brief saved ✓
```

### Backend Requirements
- `POST /api/intake/send` — trigger questionnaire; returns the formatted message text for display in mock panel
- `POST /api/intake/parse` — run symptom extraction NLP on owner reply text
- `POST /api/intake/{timeblock_id}/images` — accept base64-encoded photo array; stores in `owner_images` table
- `GET /api/timeblocks/{timeblock_id}/images` — returns all images for an appointment (owner photos + future clinical)
- `owner_images` table: `{ id, timeblock_id, patient_id, filename, content_type, data (base64), caption, submitted_at, source }`
- `PreExamBrief` model attached to `TimeBlock`
- Symptom keyword dictionary (expandable to LLM call in production)

### Demo Talking Points
> *"The agent reaches out, listens, understands, and briefs the vet — with zero front desk involvement. And now the vet doesn't just get the symptoms in text. They open the Imaging tab and see exactly what the owner saw at home. That's a vet walking into an exam room more informed than they've ever been."*

---

## F003 — Post-Appointment Follow-Up Agent

### Problem it solves
After an appointment, clinics need to send discharge instructions, follow-up reminders, and results. Currently done manually by vets or staff — often skipped. Client communication quality is inconsistent.

### User Story
> As a vet, after I mark an appointment as complete, I want the system to automatically draft a plain-English follow-up message for the owner — covering what we found, what to watch for, and when to come back — so I don't have to write it myself.

### Agentic Pipeline Design
```
Appointment marked COMPLETE
  → Follow-Up Agent receives: { procedure, findings_notes, vet_name, patient }
  → Agent generates draft message:
      Subject: "Buddy's Visit Summary — Dr. Smith"
      Body: "Hi Sarah, great to see Buddy today! Here's a quick 
             summary of his visit..."
             [Findings in plain English]
             [Care instructions]
             [Follow-up: "Book a recheck in 2 weeks if..."]
  → Draft shown to vet/front desk for 1-click approve + send
  → Sent via email/SMS (mocked in demo)
```

**Tone adaptation:** Agent adjusts tone based on visit type:
- Wellness visit → warm and celebratory ("Buddy is doing great!")
- Surgery → reassuring and detailed ("Here's what to watch for tonight...")
- Emergency → urgent and clear ("Please call us immediately if...")

### UI / UX Spec
**Appointment card gets a "Mark Complete" button.**  
On click → a **Follow-Up Draft panel** slides in:
- Editable text area with the generated message
- Tone selector: Warm / Clinical / Urgent
- Regenerate button
- "Approve & Send" button (mocked — shows success toast)
- VerboseLog shows the generation steps in real time

### Backend Requirements
- `POST /api/appointments/{id}/complete` — marks TimeBlock as done
- `POST /api/followup/draft` — takes appointment context, returns generated text
- Template-based generation for demo (procedure → template lookup → fill-in)
- `followup_status: draft | approved | sent` on TimeBlock

### Demo Talking Points
> *"The vet clicks one button. The agent writes the discharge email. The vet reads it, tweaks one sentence, clicks send. That's 10 minutes of documentation reduced to 30 seconds — every single appointment, every day."*

---

## F004 — No-Show Risk Indicator

### Problem it solves
Research identifies no-shows as a top financial pain point. Clinics have no way to predict which appointments are likely to be missed, so they treat every slot the same.

### User Story
> As a clinic manager, I want to see a risk score on each appointment so I can proactively call high-risk patients or double-book low-risk slots.

### Agentic Pipeline Design
```
At booking → Risk Scoring Agent evaluates:
  Signals:
    + Last-minute booking (< 24h notice) → +risk
    + Patient has prior no-shows → +risk  
    + Long distance from clinic (if known) → +risk
    + Monday morning or Friday afternoon → +risk
    + Wellness/elective (not urgent) → +risk
    - Emergency or sick visit → -risk (owner motivated)
    - Established patient (5+ visits) → -risk
    - Appointment > 3 days out + reminder confirmed → neutral

  Output: { risk_level: "low|medium|high", risk_score: 0-100, factors: [] }
```

**In demo:** Since we have no historical data, risk is rule-based on:
- Booking recency (same-day = high, 1 week out = medium)
- Procedure type (wellness = medium, emergency = low)
- First visit vs returning (first visit = slightly higher)

### UI / UX Spec
**On each appointment card:**
- Small coloured dot in the top-right corner:
  - 🟢 Low risk
  - 🟡 Medium risk  
  - 🔴 High risk
- Hovering the dot shows a tooltip: *"High risk — same-day booking, first visit, elective procedure"*
- Clicking opens a **Risk Detail panel** listing contributing factors
- **Manager view** (future): sorted schedule with highest-risk slots flagged for proactive outreach

### Backend Requirements
- `RiskScorer` class in the agent pipeline
- Rules engine (expandable to ML model later)
- `risk_score` and `risk_factors[]` stored on `TimeBlock`
- `GET /api/schedule/risk-summary` — aggregate risk for the day

### Demo Talking Points
> *"Most software just shows you the calendar. This tells you which appointments are likely to vanish. A clinic running 30 appointments a day with a 15% no-show rate is losing 4-5 slots daily. If you can predict 3 of those, you've paid for the software."*

---

## F005 — Role-Split UI (Vet Tech / Front Desk Views)

### Problem it solves
Research finding: *"Workflows are designed for the business owner or vet, creating huge bottlenecks for Vet Techs and front desk staff who do most of the data entry."* One view for everyone means nobody's view is optimised.

### User Story
> As a front desk worker, I want a view focused on booking, client communication, and the daily flow — not SOAP notes. As a vet tech, I want a view focused on what's in each room, what prep is needed, and patient vitals.

### Role Definitions (Demo Scope)

| Role | Primary View | Key Actions |
|---|---|---|
| **Front Desk** | Daily schedule grid, incoming requests, client comms | Book appointments, send intake forms, approve follow-ups |
| **Vet Tech** | Room-by-room status board, prep checklist, vitals entry | Mark rooms ready, log pre-exam vitals, flag concerns |
| **Veterinarian** | Patient-centric view, SOAP note workspace | Review brief, complete exam, mark done, approve follow-up |

### UI / UX Spec
**Role selector on the dashboard header** — three tabs: Front Desk | Vet Tech | Veterinarian

**Front Desk view (current dashboard, refined):**
- Appointment cards with booking + communication focus
- Quick-book input prominent
- Client comms queue (intake pending, follow-ups to approve)

**Vet Tech view:**
- **Room status board** — grid of rooms with current status:
  - 🔵 Available | 🟡 Prep Needed | 🟠 Patient In | ✅ Done
- Each room card shows: who's next, procedure, special prep notes, estimated duration
- "Mark Ready" button per room

**Vet view:**
- Appointment list sorted by their schedule
- Pre-exam brief front-and-center
- SOAP note workspace (F006)
- "Mark Complete" → triggers follow-up draft (F003)

### Backend Requirements
- `role` state in frontend (no auth changes — demo uses local state toggle)
- Role-filtered views of the same underlying data
- Room status field: `available | prep | occupied | cleaning`
- `PUT /api/rooms/{id}/status`

### Demo Talking Points
> *"We showed one view earlier. But the research is clear — front desk, techs, and vets have completely different jobs. The agent serves each role exactly what they need, nothing more. This is what 'role-aware AI' looks like in practice."*

---

## F006 — SOAP Note Draft Agent

### Problem it solves
The #1 burnout driver in veterinary medicine: vets typing SOAP notes after hours. The research cites "Ambient Clinical Scribing" as the highest-value agentic feature in the entire space.

### User Story
> As a veterinarian, after I complete an exam, I want the system to have already drafted a structured SOAP note based on the pre-visit intake, the procedure performed, and standard findings for that visit type — so I just review, edit, and sign rather than type from scratch.

### Agentic Pipeline Design
```
Appointment type + Pre-Exam Brief + Procedure
  → SOAP Draft Agent:

  SUBJECTIVE (from intake brief):
    "Owner reports lethargy x3 days and reduced appetite. 
     No vomiting or diarrhea noted."

  OBJECTIVE (template + procedure-specific blanks):
    Vitals: T: ___ HR: ___ RR: ___ Weight: ___
    Physical exam: [procedure-specific checklist pre-filled where possible]

  ASSESSMENT (procedure-based template):
    "Presentation consistent with [possible differentials based on symptoms]"
    [Vet fills in final diagnosis]

  PLAN (standard for procedure type):
    Recommendations: [auto-suggested based on assessment]
    Follow-up: [auto-suggested interval]
    Prescriptions: ___
    Client instructions: [links to F003 follow-up]
```

**In demo:** Full SOAP template pre-filled from procedure + intake data. Vet only needs to fill in vitals and confirm/edit the assessment.

### UI / UX Spec
**In the Vet role view**, each appointment card has a "Open SOAP Note" button.  
Opens a **SOAP Note workspace panel** (slides in from right, full height):

- Four clearly delineated sections: S / O / A / P
- Subjective: pre-filled from intake brief, editable
- Objective: vitals entry form + physical exam checklist (procedure-specific)
- Assessment: editable free text with AI-suggested differentials shown as ghost text
- Plan: auto-populated with standard recommendations, editable
- **"Sign & Complete"** button → marks appointment done, triggers F003 follow-up draft
- VerboseLog shows: `SOAP AGENT: Draft generated from intake + procedure template`

### Backend Requirements
- `POST /api/soap/draft` — takes `{ appointment_id }`, returns structured SOAP draft
- SOAP template library keyed by procedure type (Surgery, Dental, Wellness, Vaccination, Grooming)
- `SoapNote` model: `{ id, appointment_id, subjective, objective, assessment, plan, signed_by, signed_at }`
- `PUT /api/soap/{id}` — save edits
- `POST /api/soap/{id}/sign` — finalize and trigger follow-up

### Demo Talking Points
> *"The number one reason vets leave the profession is administrative burnout — not the medicine. This agent turns a 20-minute charting session into a 3-minute review. Multiply that by 15 appointments a day. That's two hours of a vet's life returned to them, every day."*

---

## Build Priority & Dependencies

```
F001 (Patient Cards)  ← foundational, enables F002/F004/F006
  └── F004 (No-Show Risk)  ← low effort, high demo impact
  └── F002 (Pre-Visit Intake)  ← medium effort, highest "wow" factor
        └── F006 (SOAP Note)  ← depends on intake data
              └── F003 (Follow-Up)  ← depends on SOAP completion
F005 (Role Split)  ← independent, can be built in parallel
```

**Recommended build order:** F001 → F005 → F004 → F002 → F003 → F006
