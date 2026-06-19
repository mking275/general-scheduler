# Feature Gap Analysis — What Comes After v1.0.0

**Date:** June 2026  
**Input:** Project research docs (F001–F012), external VPMS market research, v1.0.0 feature inventory  
**Purpose:** Decide what belongs in the base module before going wider (add-on modules, integrations)

---

## What v1.0.0 Covers Well

| Category | Coverage |
|---|---|
| Staff-side scheduling | ✅ Strong — booking, roles, filters, 12-week view |
| Agentic pipeline (intake → SOAP → follow-up) | ✅ Strong — full pipeline visible in Verbose Log |
| Clinical depth (vet workspace) | ✅ Good — labs, history tabs, SOAP, AI follow-up suggestions |
| Multi-location | ✅ Good — clinic switcher, floating vet, regional manager view |
| Risk awareness | ✅ Good — no-show risk scoring, high-risk watch, patient flags |

**What's thin or absent:** anything on the *client (pet owner) side*, revenue/billing, preventive care cadence, prescriptions, and operational forecasting.

---

## Candidate Features — Tier 1: High Impact, Core to Base Module

These directly extend the scheduling/clinical loop and have a natural, demo-visible agentic story.

---

### F013 — Appointment Reminder & Confirmation Agent

**The gap**  
We book appointments but send nothing to the owner. F004 (No-Show Risk) flags the problem but doesn't solve it. Market research consistently identifies *"two-way reminders"* as the most requested missing feature in SMB VPMS tools.

**The agentic angle**
```
T-48h: Agent sends "Confirm Buddy's appt Thursday 9am — reply YES to confirm"
Owner YES → appointment marked confirmed, no-show risk score drops automatically
Owner "Need to reschedule" → agent opens rebooking flow, slot freed
T-2h:  Final reminder sent
No reply by T-24h → flags "Unconfirmed — consider calling" in front desk queue
```

**What it looks like in the UI**
- Confirmation status badge on each card: `📲 Confirmed` / `⚠ Unconfirmed` / `📞 Call Needed`
- "Confirmation Queue" panel in Front Desk view — one click to resend
- Verbose Log: `REMINDER AGENT: Confirmation sent to Sarah M. · Confirmed 14min later`

**Complexity:** Medium  
**Why base module:** No-show prevention is table-stakes. Without this, F004 is a warning light with no steering wheel.

---

### F014 — Waitlist & Smart Cancellation Backfill

**The gap**  
When an appointment is cancelled, the slot goes empty. There's no mechanism to fill it. High-demand clinics leave revenue on the table every single day.

**The agentic angle**
```
Cancellation received → Cancellation Backfill Agent:
  1. Checks waitlist for procedure type + vet preference match
  2. Identifies: "Daisy's dental cleaning was waitlisted — fits this slot perfectly"
  3. Sends owner: "A slot opened Thursday 10am — want it? Reply YES within 30min"
  4. Accepted → books automatically, updates schedule board
  5. No reply in 30min → offers to next waitlisted patient
```

**What it looks like in the UI**
- "Add to Waitlist" button on appointment cards when preferred slot is full
- `Waitlist (3)` count badge in the header
- Verbose Log shows the full backfill chain as it happens — **excellent demo moment**

**Complexity:** Medium  
**Why base module:** Pure revenue recovery. A single filled cancellation per day pays for the software.

---

### F015 — Preventive Care & Wellness Plan Tracking

**The gap**  
Vaccination due dates, annual wellness reminders, heartworm schedules — the *recurring revenue engine* of every vet practice — are almost universally managed in spreadsheets or paper cards, completely disconnected from the scheduling system.

**The agentic angle**
```
Post-appointment → Care Tracker Agent:
  - Records vaccination lot number + next-due date per protocol (species/weight)
  - Queues proactive outreach at T-30d: "Buddy's rabies booster is due in 3 weeks. Book now?"
  - Overdue patients surfaced daily in front desk view
```

**What it looks like in the UI**
- **Care Plan tab** on the patient record (next to History, Labs, SOAP)
- Vaccination timeline: past shots with dates, upcoming due dates highlighted in amber/red
- "Overdue" badge on patient cards for anything past due
- Daily "Preventive Care Due This Month" list for front desk

**Complexity:** Medium-High  
**Why base module:** This is the #1 reason owners stay with a clinic — proactive reminders. Every competitor has it. Without it the system looks like a scheduling tool, not practice management.

---

### F016 — Prescription Management

**The gap**  
Prescriptions are completely absent. After any visit, medications prescribed have no record in the system — no dose, no duration, no refill tracking. Refill requests arrive by phone and require manual record lookup every time.

**The agentic angle**
```
Vet issues Rx in SOAP Plan → Prescription Agent:
  - Creates: drug / dose / frequency / duration / refills_remaining
  - Checks against patient allergy flags — warns on penicillin-class for flagged patients
  - Schedules refill reminder at 80% of supply duration
  
Refill request arrives → Agent evaluates:
  → In-protocol + exam within 12 months: auto-approves, notifies owner
  → Out-of-protocol or expired: flags for vet review
```

**What it looks like in the UI**
- **Rx tab** in VetAppointmentCard
- Prescription list on patient record: drug, dose, dates, refills remaining
- "Refill Requests" queue for front desk — approve/deny in one click
- Drug-allergy interaction warning inline with existing allergy banner

**Complexity:** Medium  
**Why base module:** Prescription tracking is a safety and legal requirement. Any vet evaluating the system will notice its absence immediately.

---

## Candidate Features — Tier 2: High Value, Second Milestone

Compelling features but either require more infrastructure or work better as a focused follow-up sprint.

---

### F017 — Invoice Draft Generation (Not Full Billing)

**The gap**  
Appointments are marked complete but generate no financial record.

**The agentic angle (scoped)**  
Not a full billing system — payment processing and insurance are integration-layer problems. The agentic win here is **automatic line-item invoice drafting at appointment completion**:
```
Appointment COMPLETE → Billing Agent:
  - Reads: procedure, labs ordered, Rx issued, duration
  - Generates: consultation fee + procedure fee + lab fees + Rx cost
  - Front desk reviews, adjusts if needed, marks as sent
```

**Scope boundary:** We generate the draft. Stripe/QuickBooks sync = add-on module.

**What it looks like:** Invoice button on completed cards. Regional Manager view gains a revenue summary bar.

**Complexity:** Medium. Needs a fee schedule table seeded with realistic vet pricing.

---

### F018 — Breed-Specific Clinical Intelligence

**The gap**  
The risk scorer and SOAP templates treat every dog identically. Breed-specific conditions are core to veterinary medicine — brachycephalic airway, GDV risk in deep-chested breeds, breed-predisposed cancers.

**The agentic angle**
```
Patient record loaded → Breed Intelligence Agent:
  - Looks up breed in protocol table
  - Attaches flags: "Brachycephalic — extended anesthesia monitoring required"
  - Suggests: "Golden Retrievers over 6y: consider annual cancer screening"
  - Surfaces in SOAP as "Breed Considerations" section
```

**What it looks like:** `🧬 Breed Protocol` banner on patient cards for flagged breeds. Subtle but powerful in a live demo.

**Complexity:** Low-Medium. A breed protocol JSON table of ~30 breeds. Logic is pure lookups. High demo impact for low build cost.

---

### F019 — Capacity & Revenue Forecasting

**The gap**  
The Regional Manager view shows actuals and forward bookings. It doesn't tell you whether you're trending toward a good month or a bad one.

**The agentic angle**
```
Weekly → Forecast Agent:
  - Analyses last 8 weeks of actuals
  - Projects 4 weeks forward: appointment volume, revenue estimate, no-show probability
  - Narrative insight: "Downtown trending 12% below last month. Westside has 3 open vet slots."
  - Suggests: "Wellness promotion for Downtown in week 3 could close the gap."
```

**What it looks like:** "Forecast" section in Regional Manager — 4-week projection bars with a narrative card. High executive-audience demo value.

**Complexity:** Medium. Linear trend on existing timeblock data + template-based narrative (same pattern as SOAP/follow-up agents).

---

## What to Deliberately Exclude from Base Module

| Feature | Why Not |
|---|---|
| **Payment processing** | Stripe/Square = add-on integration module |
| **Client online booking portal** | Requires auth, client accounts, public URL — separate product surface |
| **Telemedicine / video consults** | WebRTC or third-party — out of scope for base |
| **Inventory management** | Deep supply chain logic — dedicated module |
| **DICOM / radiology viewer** | Enterprise scope, separate viewer integration |
| **Insurance claims** | Carrier-specific regulatory formats — integration layer only |

---

## Recommended Build Order for v1.1

```
Priority 1 — Close the obvious gaps:
  F013  Appointment Reminder & Confirmation Agent
  F016  Prescription Management
  F015  Preventive Care / Wellness Plan Tracking

Priority 2 — Add the revenue story:
  F014  Waitlist & Smart Cancellation Backfill
  F018  Breed-Specific Clinical Intelligence   ← low effort, high demo impact
  F017  Invoice Draft Generation

Priority 3 — Executive / growth story:
  F019  Capacity & Revenue Forecasting
```

**F013 first** — we book appointments and tell no one. That's the most glaring gap.  
**F016 second** — prescriptions are a safety issue, not a feature request.  
**F015 third** — wellness tracking is why owners stay with a clinic long-term.  
**F018 is a quick win** — low code cost, very high clinical credibility in demos.

---

## How Each Feature Differentiates from Legacy VPMS

| Feature | What legacy VPMS does | What our agents do |
|---|---|---|
| F013 Reminders | Blast SMS, no two-way | Confirmation dialog → auto-rebooking if declined |
| F014 Waitlist | Maintain a list | Match, offer, and book in real time |
| F015 Wellness | Show due dates | Proactive outreach, protocol by species/weight |
| F016 Prescriptions | Record what was prescribed | Interaction check, auto-approve safe refills |
| F017 Invoicing | Manual line entry | Draft from appointment context automatically |
| F018 Breed Intel | Breed in demographics | Protocol flags surfaced in clinical workflow |
| F019 Forecasting | Show a calendar | Project trends, generate narrative action suggestions |

**The pattern:** every legacy system records. Every agent *acts*.
