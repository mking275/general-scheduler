# Quickstart: Phase 3 Clinical Operations

**Feature**: specs/005-phase3-clinical-ops  
**Date**: 2026-06-19  
**Purpose**: Validation guide — prove each Phase 3 feature works end-to-end

---

## Prerequisites

```bash
# Backend running
cd /home/matt/SMB_Hunt/General_Scheduler
source backend/.venv/bin/activate
uvicorn backend.main:app --host 127.0.0.1 --port 8080 --reload

# Frontend running (separate terminal)
cd /home/matt/SMB_Hunt/General_Scheduler/frontend
npm run dev   # → http://localhost:3000

# Import check (backend must parse cleanly)
python3 -c "from backend.main import app; print('✅ imports OK')"
python3 -c "from backend.repository import db; print('✅ schema OK')"
```

---

## Scenario 1 — F013: Appointment Reminder & Confirmation

**Role**: Front Desk | **SC-P3-001** target: <90 seconds

1. Open http://localhost:3000 → sign in → Front Desk role
2. Find any appointment card — confirm `⏳ Not Sent` badge is visible
3. Check button label: if appointment is >48h away → `Send Reminder (Early — T-48h+)`; if ≤48h → `Send Reminder (Due — T-24h)`
4. Click Send Reminder → ReminderPanel slides in with the composed message bubble
5. Click `[YES]` → badge updates to `📲 Confirmed`; Verbose Log shows 2 REMINDER AGENT steps + 1 RISK AGENT step
6. Verify risk score decreased by ≥10 points

**Action Queue validation**:
7. On a different appointment, click Send Reminder → click `[RESCHEDULE]`
8. Badge updates to `🔄 Reschedule Requested`
9. "Action Queue (1)" panel in Front Desk header shows the appointment

**API smoke test**:
```bash
TB_ID=<any timeblock id from GET /api/timeblocks>
curl -X POST http://127.0.0.1:8080/api/timeblocks/$TB_ID/reminder/send
curl -X POST http://127.0.0.1:8080/api/timeblocks/$TB_ID/reminder/reply \
  -H "Content-Type: application/json" -d '{"reply":"yes"}'
curl http://127.0.0.1:8080/api/timeblocks/action-queue
```

---

## Scenario 2 — F018: Breed-Specific Clinical Intelligence

**Role**: Veterinarian | **SC-P3-002** target: no extra clicks

1. Switch to Vet role
2. Find appointment for a brachycephalic patient (French Bulldog, Pug, Boston Terrier, Shih Tzu)
3. Open the appointment card → amber `🧬 Breed Protocol` banner visible below patient name
4. If procedure is Surgery or Dental: red anaesthesia warning strip visible in header without opening any tab
5. Open History tab → breed flag listed above visit history
6. Open SOAP workspace → "Breed Considerations" section pre-populated with anaesthesia protocol text

**Age-gated flag validation**:
7. Find appointment for Buddy (Golden Retriever, age ≥6) → oncology screening flag should appear
8. Find appointment for a young dog (age <6) with same breed → no oncology flag

**API smoke test**:
```bash
# Get a brachycephalic patient's flags
PID=<patient_id for a bulldog patient>
curl http://127.0.0.1:8080/api/patients/$PID/breed-flags
# Expected: flags array with brachycephalic entry, severity: critical

# Get a mixed-breed patient
curl http://127.0.0.1:8080/api/patients/<mixed-breed-id>/breed-flags
# Expected: flags: []
```

---

## Scenario 3 — F014: Waitlist & Smart Cancellation Backfill

**Role**: Front Desk | **SC-P3-003** target: Verbose Log chain visible <5s

**Add to waitlist first**:
1. On a full appointment slot → "Add to Waitlist" button visible
2. Fill: procedure = Dental Cleaning, urgency = asap → submit
3. Waitlist badge in header increments

**Backfill flow**:
4. Find an existing appointment for Dental Cleaning → click Cancel
5. System asks "Run Backfill Agent?" → confirm
6. Verbose Log streams: scanning → match found → score: 100pts → offer queued
7. WaitlistPanel appears with matched patient details and score
8. Click `[Accept]` → appointment booked, waitlist badge decrements, slot appears on schedule

**API smoke test**:
```bash
curl http://127.0.0.1:8080/api/waitlist
curl -X POST http://127.0.0.1:8080/api/waitlist \
  -H "Content-Type: application/json" \
  -d '{"patient_id":"<id>","clinic_id":"clinic-downtown","procedure_type":"Dental Cleaning","urgency":"asap"}'
TB_ID=<timeblock to cancel>
curl -X POST http://127.0.0.1:8080/api/timeblocks/$TB_ID/cancel
```

---

## Scenario 4 — F015: Preventive Care Tracking

**Role**: Vet (recording) / Front Desk (surfacing) | **SC-P3-004**: ≥2 overdue on fresh seed

**On startup validation**:
1. Open Front Desk view → "📋 Care Due This Month (N)" panel visible in sidebar
2. Confirm N ≥ 2 with at least 2 red `⚠ OVERDUE` rows visible without any user action

**Care recording**:
3. Switch to Vet role → open a Vaccination appointment
4. In the Care Plan tab → select DHPP from dropdown, enter batch number → Save
5. Verbose Log shows: `CARE AGENT: DHPP recorded · Next due: 2027-06-19 · Reminder queued`
6. next_due_date = today + 12 months (verify date arithmetic)

**Standalone historical event**:
7. Click "Log Historical Care Event" in Care Plan tab
8. Select Rabies, enter past date (e.g. 2025-01-15), no appointment linked → Save
9. Event appears in care timeline with `timeblock_id: null`

**Front Desk booking**:
10. In Care Due panel, click "Book" next to an overdue patient
11. Quick-book input pre-populates with patient name + procedure type

**API smoke test**:
```bash
curl http://127.0.0.1:8080/api/care/due-this-month
curl http://127.0.0.1:8080/api/care-protocols
PID=<patient_id>
curl http://127.0.0.1:8080/api/patients/$PID/care-events
curl -X POST http://127.0.0.1:8080/api/patients/$PID/care-events \
  -H "Content-Type: application/json" \
  -d '{"protocol_id":"<dhpp-id>","administered_date":"2026-06-19","batch_number":"LOT-001","administered_by":"Dr. Smith"}'
```

---

## Scenario 5 — F016: Prescription Management

**Role**: Vet (issue/refill) / Front Desk (refill queue) | **SC-P3-005**: conflict fires immediately

**Issue Rx — no conflict**:
1. Vet role → open any appointment → Rx tab
2. Type "Carprof" → typeahead suggests "Carprofen"
3. Fill: dose=25mg, frequency=BID, duration=14, refills=2 → Issue Rx
4. Verbose Log: `PRESCRIPTION AGENT: Carprofen 25mg BID x14d · 2 refills · No allergy conflicts ✓`
5. Prescription appears in patient History tab

**Issue Rx — allergy conflict (Buddy)**:
6. Find Buddy (Golden Retriever — has penicillin allergy flag)
7. In Rx tab, type "Amoxicillin" → Issue Rx
8. Red banner appears: "⚠ Allergy conflict: Amoxicillin (penicillin class)"
9. Rx NOT saved until "Acknowledge & Proceed" clicked

**Refill queue (Front Desk)**:
10. Switch to Front Desk → "💊 Refill Requests (N)" panel
11. Confirm auto-approvable rows show green `✓ Auto-approve`; vet-review rows show amber `⚠ Vet Review`
12. Click Approve on an auto-approvable row → `refills_remaining` decrements, log entry appears

**Vet-initiated refill**:
13. Vet role → Rx tab on a prescription → click "Request Refill"
14. Request appears in Front Desk panel with `initiated_by: vet`

**API smoke test**:
```bash
PID=<buddy-patient-id>
curl http://127.0.0.1:8080/api/patients/$PID/prescriptions
curl -X POST http://127.0.0.1:8080/api/patients/$PID/prescriptions \
  -H "Content-Type: application/json" \
  -d '{"drug_name":"Amoxicillin","dose":"250mg","frequency":"BID","duration_days":10,"refills_remaining":1,"issued_by":"Dr. Smith"}'
# Expected: allergy_conflict object returned, saved: false
curl http://127.0.0.1:8080/api/refill-requests
```

---

## Scenario 6 — F019: Capacity & Revenue Forecasting

**Role**: Regional Manager | **SC-P3-006**: renders <2s

1. Switch to Regional Manager role
2. Scroll below clinic summary cards → "📈 4-Week Forecast" section renders within 2 seconds
3. Each clinic shows 4 bars: solid fill (booked) vs hatched pattern (projected)
4. Red dotted capacity target line visible at 90% height
5. AI Insight card below chart:
   - Green border + "On Track" → clinic trending at/above target
   - Amber border + "Action Suggested" → clinic below target
6. Verbose Log shows FORECAST AGENT computation steps

**API smoke test**:
```bash
curl http://127.0.0.1:8080/api/clinics/clinic-downtown/forecast
curl http://127.0.0.1:8080/api/clinics/clinic-westside/forecast
# Both should return 4 forecast_weeks with booked_slots, projected_slots, utilisation_pct
# verbose_log should contain 4 FORECAST AGENT lines
```

---

## Scenario 7 — Backward Compatibility (SC-P3-007)

Run the full v1.0.0 demo flow:

```bash
# 1. Book a new appointment via natural language
curl -X POST http://127.0.0.1:8080/api/schedule \
  -H "Content-Type: application/json" \
  -d '{"request_text": "Need a wellness exam for a Golden Retriever", "clinic_id": "clinic-downtown"}'

# 2. Send intake questionnaire
TB_ID=<new timeblock id>
curl -X POST http://127.0.0.1:8080/api/intake/send -H "Content-Type: application/json" -d "{\"timeblock_id\":\"$TB_ID\"}"

# 3. Parse owner reply
curl -X POST http://127.0.0.1:8080/api/intake/parse \
  -H "Content-Type: application/json" \
  -d "{\"timeblock_id\":\"$TB_ID\",\"owner_response\":\"She's been scratching a lot and seems tired\"}"

# 4. Generate SOAP draft
curl -X POST http://127.0.0.1:8080/api/soap/draft -H "Content-Type: application/json" -d "{\"timeblock_id\":\"$TB_ID\"}"

# 5. Complete appointment
curl -X POST http://127.0.0.1:8080/api/appointments/$TB_ID/complete

# 6. Approve follow-up
DRAFT_ID=<draft id from complete response>
curl -X POST http://127.0.0.1:8080/api/followup/$DRAFT_ID/approve
```

All steps should return 200 with no errors. No Phase 3 schema additions should break this flow.
