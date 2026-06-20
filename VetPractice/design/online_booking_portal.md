# VPMA Online Booking Portal — Production Design Document

**Version:** 1.0  
**Date:** 2026-06-19  
**Status:** Ready for Engineering Review  
**Authors:** Product & Architecture Team  

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [User Personas](#2-user-personas)
3. [Competitive Benchmarking](#3-competitive-benchmarking)
4. [Core User Journey — Step by Step](#4-core-user-journey--step-by-step)
5. [New Client vs. Returning Client Flows](#5-new-client-vs-returning-client-flows)
6. [Agentic Intake Integration](#6-agentic-intake-integration)
7. [Intelligent Slot Suggestion — AI Matching Layer](#7-intelligent-slot-suggestion--ai-matching-layer)
8. [Waitlist UX](#8-waitlist-ux)
9. [Confirmation & Status Tracking Page](#9-confirmation--status-tracking-page)
10. [Public API Design](#10-public-api-design)
11. [Data Model Changes](#11-data-model-changes)
12. [Frontend Architecture](#12-frontend-architecture)
13. [Security & Privacy](#13-security--privacy)
14. [Practice Configuration — Staff-Side Admin](#14-practice-configuration--staff-side-admin)
15. [Integration Points with Existing Systems](#15-integration-points-with-existing-systems)
16. [MOD Upsell Hooks](#16-mod-upsell-hooks)
17. [Phased Build Plan](#17-phased-build-plan)
18. [Success Metrics](#18-success-metrics)

---

## 1. Executive Summary

### What We're Building

VPMA is launching the **first natively agentic, AI-first client-facing online booking portal** for veterinary practices. Unlike every competing product—which treats online booking as a static form with a date picker and a submit button—VPMA's portal is a living, intelligent interface that orchestrates multiple AI agents across the entire pre-visit lifecycle: from first click to doctor-ready patient chart.

The portal is embedded natively in VPMA with zero integration cost, zero third-party dependency, and zero vendor lock-in. It surfaces directly from the same FastAPI backend that powers the staff scheduling board, inheriting all existing schedule, patient, and resource data with no sync friction.

### Elevator Pitch

> "VPMA's Online Booking Portal doesn't just let pet owners pick a time slot—it recommends the right appointment, pre-fills everything we already know about their pet, fires an AI intake form the moment the booking is confirmed, scores the patient's risk profile before the doctor walks in, and tracks the appointment lifecycle in real time from a shareable status URL. Every competitor either bolts on a third-party widget or serves a static date picker. We ship the whole experience, natively, with AI driving every step."

### Key Differentiators vs. All 8 Competitors

| Differentiator | VPMA | All 8 Competitors |
|---|---|---|
| Native implementation (no third-party widget) | ✅ | Shepherd (PetDesk), ezyVet (Vetstoria), Cornerstone/Avimark (PetDesk/Vetsched) all use third parties |
| AI slot recommendation with plain-language explanation | ✅ | ❌ None |
| Agentic pre-visit intake wired to booking confirmation | ✅ | ❌ None |
| Real-time appointment status tracker (shareable URL) | ✅ | ❌ None |
| Native waitlist with AI backfill (not just "no availability") | ✅ | Digitail has basic waitlist; rest have nothing |
| Returning client pre-fill (zero re-entry) | ✅ | ❌ Owners re-enter pet info every booking |
| Risk scoring before the doctor walks in | ✅ | ❌ None |
| No-show risk factored into slot recommendations | ✅ | ❌ None |
| Breed-specific intake flags | ✅ | ❌ None |
| Single unified owner experience (booking + intake + status) | ✅ | ❌ None — Digitail comes closest with their Pet Parent app |

---

## 2. User Personas

### 2.1 New Client — First-Time Booking

**Profile:** Sarah, 31, just adopted a rescue dog. She found the clinic on Google Maps. She doesn't have an account. Her dog has no patient record.

**Goals:**
- Book quickly without being forced to create a password
- Understand what happens next
- Trust that the clinic received her information

**Pain Points with Competitors:**
- Redirected to a Vetstoria or PetDesk branded page — doesn't feel like the clinic
- Asked to fill in full pet medical history before she even has an appointment
- No confirmation she can trust until she gets an email

**What VPMA Does for Her:**
- The clinic's branding, name, and colors appear on the portal — it's clearly *that* clinic
- She only fills in what's strictly necessary for the booking (pet name, species, age, reason for visit)
- Within 2 minutes she has a booking confirmation with a unique status URL she can share with her partner
- The intake form comes after booking, via SMS, when she's not in the middle of the flow

**Key UX Requirements:**
- No mandatory account creation before the first booking
- Progress bar showing "Step 2 of 4" to reduce perceived friction
- Guest token created at booking time; account claimed optionally at end

---

### 2.2 Returning Client — Existing Patient Record

**Profile:** Marcus, 45, has been a client for three years. His cat Mochi has an established record. He wants to book an annual wellness exam.

**Goals:**
- Be recognized immediately
- Not have to re-type everything
- Book in under 60 seconds

**Pain Points with Competitors:**
- Even with an account, he still has to pick the pet, fill in the species, re-enter the reason for visit
- If the PIMS is separate from the booking tool (ezyVet + Vetstoria), his history doesn't pre-fill
- He has to find his confirmation email to know when the appointment is

**What VPMA Does for Him:**
- Phone/email lookup finds Mochi's record instantly
- All patient data is pre-filled: species, breed, DOB, last visit, established vet
- AI recommends "Dr. Chen has seen Mochi before — here's her next available 45-min slot"
- He lands on a live status page he can bookmark

**Key UX Requirements:**
- Phone number as primary lookup key (fastest mobile entry)
- One-click patient selection if multi-pet household
- Pre-filled service type based on last appointment and protocol schedule (e.g., "Mochi is due for her annual wellness")

---

### 2.3 Multi-Pet Household

**Profile:** Jennifer, 38, has three pets: two dogs (Biscuit and Gravy) and a cat (Duchess). She needs to book individual appointments for each pet at the same clinic.

**Goals:**
- Manage all three pets from one account
- Not start from scratch for each pet
- See all her upcoming appointments in one place

**Pain Points with Competitors:**
- Most systems treat each booking as a one-off; there's no household view
- She has to look up herself each time and re-select pets

**What VPMA Does for Her:**
- After phone/email lookup, all three pets appear with a "Select which pet this appointment is for" card interface
- Returning to the portal shows her full household with upcoming appointments per pet
- Separate booking tokens per appointment; one owner session links them all

**Key UX Requirements:**
- Pet selection step is visual: name, photo placeholder (species icon), age, last visit badge
- "Book another appointment for a different pet" link visible on confirmation page
- Owner portal view (lightweight, no account required — just phone + OTP) showing all upcoming and past appointments

---

### 2.4 Emergency / Same-Day Urgency Case

**Profile:** Tom, 52, noticed his dog limping severely at 7am. He wants to know if he can get in today.

**Goals:**
- Signal urgency, not just pick a time
- Get a response quickly — even if it's "join the waitlist for same-day"
- Know someone saw his request

**Pain Points with Competitors:**
- Online booking systems show "no availability" and stop — no next step
- Emergency urgency gets lost in a form that looks the same as a wellness booking
- He ends up calling anyway, defeating the point

**What VPMA Does for Him:**
- Reason for Visit step includes a triage question: "How urgent is this?" → Wellness / Routine / Urgent / Emergency
- If "Urgent" or "Emergency" is selected:
  - Same-day slots are shown first (if configured by practice)
  - A banner appears: "This clinic treats same-day urgencies. Staff will review your request within [X minutes]."
  - If no same-day availability: automatically offered the waitlist, pre-filled as "urgent, flexible today only"
  - Staff receives an alert: "Urgency booking request from Tom — dog limping — review now"
- The risk agent `risk.py` scores the clinical severity based on complaint type and flags for staff

**Key UX Requirements:**
- Urgency selector must be prominent, not a dropdown hidden at the bottom of the form
- Color-coded: Wellness (green), Routine (blue), Urgent (amber), Emergency (red)
- Emergency triage note: display clinic phone number prominently — "For life-threatening emergencies, call us directly at [number] or go to your nearest emergency animal hospital."

---

## 3. Competitive Benchmarking

### 3.1 Competitor Ratings Table

| Competitor | Booking Type | Rating (1–5) | Done Well | Done Poorly |
|---|---|---|---|---|
| **Shepherd** | 3rd party (PetDesk / Chckvet) | ⭐⭐ (2/5) | Good AI-first UI for staff. PetDesk is a recognized brand. | Requires two separate platforms. Double-sync friction. No unified owner experience. Vets complain actively. |
| **ezyVet** | 3rd party (Vetstoria) | ⭐⭐½ (2.5/5) | Vetstoria is purpose-built for vet booking; knows vet workflows. | Owner is redirected to Vetstoria-branded page — brand breaks. ~$100+/mo add-on cost. Configuration is separate. Not native to PIMS. |
| **Provet Cloud** | Native | ⭐⭐⭐½ (3.5/5) | Practice controls which appointment types/slots/doctors are visible. Clean, branded. Best native implementation in market today. | Still a static form. No AI matching. No intake integration. No status tracker. |
| **Covetrus Pulse** | Native | ⭐⭐⭐ (3/5) | Tight ecosystem integration. Works well if you're all-in on Covetrus. | Heavy vendor lock-in. Tightly coupled to Covetrus supply chain. Not portable. |
| **Digitail** | Native + Pet Parent App | ⭐⭐⭐⭐ (4/5) | Pet Parent iOS/Android app. Real-time appointment status. Tails Concierge AI chat booking — the most agentic experience in the market today. | Requires app download (friction for casual users). Chat booking (Tails) is optional add-on. No pre-visit intake wired to booking. |
| **DaySmart Vet** | Native + PetCare App | ⭐⭐⭐ (3/5) | Easiest setup. Best for solo or small practices. PetCare mobile app is solid. | Limited configurability for multi-location. No AI. |
| **Cornerstone (IDEXX)** | 3rd party (PetDesk / Vetsched) | ⭐⭐ (2/5) | Market leader in PIMS data depth. Trusted by large practices. | No native booking story. Legacy architecture. Integration requires separate contract and config. |
| **Avimark (Covetrus)** | 3rd party (PetDesk / Vetsched) | ⭐½ (1.5/5) | Large installed base. | Oldest architecture in the market. Third-party only. Booking experience feels like 2012. No mobile story. |

### 3.2 What "Industry Best" Looks Like

Based on this analysis, the industry-best veterinary booking portal must be:

1. **Native** — zero third-party redirects; same brand, same URL domain feel
2. **Pre-filling** — returning clients see their data instantly, zero re-entry
3. **Agentic post-booking** — intake fires automatically, data surfaces before the visit
4. **AI-matched** — recommends slots, not just lists them
5. **Status-aware** — confirmation is a live page, not a static email
6. **Waitlist-integrated** — "no availability" is never a dead end
7. **Mobile-first** — 60%+ of bookings will come from smartphones
8. **Accessible** — WCAG 2.1 AA, zero exceptions

VPMA's design achieves all 8. No current competitor achieves more than 4.

---

## 4. Core User Journey — Step by Step

### 4.1 Scenario

**Who:** Marcus (returning client) booking an annual wellness exam for his cat Mochi.  
**Device:** iPhone 14 Pro (mobile-first design)  
**Entry Point:** Clinic website → "Book Online" button → portal

### 4.2 URL Structure

```
Standalone hosted:   https://book.vpma.app/{clinic_slug}
Embedded widget:     https://meadowpetclinic.com/book  (iframe or web component pointing to VPMA)
Clinic custom domain: https://book.meadowpetclinic.com (CNAME to VPMA, Phase 3)
```

`clinic_slug` is a URL-safe, human-readable identifier set at clinic creation time (e.g., `meadow-pet-clinic`). It maps directly to `clinics.slug` in the database.

---

### Step 0: Landing — Clinic Portal Home

**URL:** `https://book.vpma.app/meadow-pet-clinic`

**Purpose:** Orient the owner. Display the clinic's branding. Primary CTA.

**Screen Contents:**
- Clinic logo and name (fetched from `GET /public/clinics/{clinic_slug}`)
- Hero: "Book an appointment at Meadow Pet Clinic"
- Clinic address, phone number, hours (from `clinic_booking_config`)
- Primary CTA button: "**Book an Appointment**" [id: `btn-book-start`]
- Secondary link: "Track an existing appointment" [id: `link-track-appointment`]
- Emergency banner (if configured): "For emergencies, call: (555) 123-4567"

**Backend on Load:**
- `GET /public/clinics/meadow-pet-clinic` → returns clinic metadata, branding colors, and booking config (open/closed status, same-day cutoff, advance booking window)
- If clinic is outside business hours, display: "Online booking is open 24/7. Your appointment request will be confirmed next business day."

**Edge Cases:**
- `clinic_slug` not found → 404 page with VPMA brand; "Search for another clinic"
- `clinic_booking_config.online_booking_enabled = false` → "Online booking is currently disabled for this clinic. Please call us at [number]."
- Same-day cutoff passed (e.g., cutoff is 2pm; it's 3pm) → Same-day slots hidden; earliest = tomorrow

---

### Step 1: Owner Identification

**URL:** `https://book.vpma.app/meadow-pet-clinic/identify`

**Purpose:** Determine if this is a new or returning client. Primary identifier: phone number.

**Screen Contents:**
- Header: "Let's find your account"
- Field: Phone number [id: `input-phone`] — formatted as (555) 123-4567 automatically
- Field: Email (optional, shown as helper text: "Or use your email address") [id: `input-email`]
- CTA: "Continue" [id: `btn-identify-continue`]
- Link: "I'm a new client — skip this step" [id: `link-new-client`]
- Progress bar: Step 1 of 4

**Backend on Submit:**
- `POST /public/owners/lookup` with `{phone: "5551234567"}` or `{email: "..."}`
- Returns: `{found: true, owner_id: "uuid", display_name: "Marcus", pets: [{id, name, species, breed, last_visit}]}`
- If `found: false`: transition to new client flow (Step 1B)

**What Backend Does:**
1. Normalize phone (strip formatting, E.164)
2. Query `owners` table: `SELECT id, first_name, pets FROM owners WHERE phone = $1 AND clinic_id = $2 LIMIT 1`
3. Create an `owner_sessions` record (ephemeral, 30-min TTL): returns session token as HttpOnly cookie
4. Return masked display data (never return full DOB, address, or medical records at this step)

**Edge Cases:**
- Phone matches multiple owners (edge case for shared family phone): return all matches; prompt "Is this you?" with first-name and last-initial display, e.g., "Marcus D." / "Jamie D."
- Rate limit: 10 lookup attempts per IP per 5 minutes → 429 error
- Phone not found but email provided: try email lookup; if still not found → new client
- Invalid phone format: inline validation error, no server call

---

### Step 2: Pet Selection

**URL:** `https://book.vpma.app/meadow-pet-clinic/select-pet`

**Purpose:** Choose which pet this appointment is for. (Returning client: select from known pets or add new one.)

**Screen Contents (Returning Client):**
- Header: "Hi Marcus! Which pet is this appointment for?"
- Pet cards [id: `pet-card-{pet_id}`]: Each shows:
  - Species icon (cat 🐱 / dog 🐶 / other)
  - Name (Mochi)
  - Breed + Age (Domestic Shorthair · 4 yrs)
  - Last visit badge ("Last seen: 14 months ago")
  - Due-for-care badge (if `breed_intelligence.py` or protocol data indicates overdue): "Annual wellness overdue ⚠️"
- "Add a different pet" link [id: `link-add-pet`]
- Progress bar: Step 2 of 4

**Backend on Load:**
- `GET /public/owners/{owner_id}/pets` (session-gated via owner_session cookie)
- Calls `GET /api/care/protocols` filtered by species/breed + last visit date → generates "overdue" badges
- Calls `GET /api/breed-protocols` → surfaces breed flags (e.g., "Persian cats need 60-min wellness appointments")

**What Backend Does on Pet Selection:**
- Sets `selected_pet_id` on the owner session
- Fetches appointment history for the selected pet
- Pre-fetches recommended appointment duration from `clinic_booking_config.appointment_durations` by type and breed

**Edge Cases:**
- Pet is deceased (status = 'deceased' in patients table): do not display
- Owner has 0 pets: skip this step; go directly to new patient form
- Owner wants to add a new pet they haven't brought in before: "Add New Pet" → minimal form (name, species, breed, age/DOB) → creates patient record on the backend via `POST /api/patients`; links to owner

---

### Step 3: Appointment Type & Reason

**URL:** `https://book.vpma.app/meadow-pet-clinic/appointment-type`

**Purpose:** Capture what the visit is for. This drives: duration, resource matching, intake question set, triage priority.

**Screen Contents:**
- Header: "What's the reason for Mochi's visit?"
- Appointment type cards (pulled from `clinic_booking_config.bookable_types`):
  - **Annual Wellness Exam** (45 min) — [id: `appt-type-wellness`]
  - **Sick Visit** (30 min)
  - **Vaccines Only** (15 min)
  - **Dental Consultation** (30 min)
  - **Follow-Up** (15 min)
  - **Other** (text entry)
- Urgency selector (below type): "How urgent is this?" — **Wellness** | **Routine** | **Urgent** | **Emergency**
  - Color-coded chips; defaults to "Routine" for wellness types
  - If Emergency selected: modal appears with clinic phone number and nearest emergency hospital info
- Notes field: "Anything specific you'd like us to know?" (optional, 300 char max) [id: `input-visit-notes`]
- Progress bar: Step 3 of 4

**Backend on Load:**
- `GET /public/clinics/{clinic_slug}/appointment-types` → returns only types where `clinic_booking_config.bookable_online = true`
- Duration for each type pulled from config; breed overrides applied (Persian cat → add 15 min to wellness)

**What Backend Does on Selection:**
- Stores `appointment_type_id`, `urgency`, and `notes` on owner session
- Runs preliminary check: does urgency = 'urgent' or 'emergency'? If so, flag for same-day availability check and set `priority = 'urgent'` on future booking record
- Triggers no-show risk pre-score via `risk.py` using appointment type + time of day + owner's historical no-show rate (if returning client) — stored on session for use in slot ranking

**Edge Cases:**
- "Other" selected: free text description; staff manual review before confirmation (set booking to `pending_review` status); owner sees: "We'll confirm your appointment within [X] hours"
- Appointment type requires vet who isn't currently available (e.g., dental consult, only one vet does dentals): show vet's next availability; offer waitlist otherwise
- Emergency selection at after-hours time: display emergency contact immediately; option to still submit a request for first-available next-day slot

---

### Step 4: AI Slot Selection

**URL:** `https://book.vpma.app/meadow-pet-clinic/select-slot`

**Purpose:** Present the best available appointments. Not a raw calendar grid — AI-ranked cards with plain-language explanations.

**Screen Contents:**
- Header: "Here are the best times for Mochi"
- **AI Slot Cards** (top 3 recommendations) — see Section 7 for full detail
  - Each card: Date, time, vet name, duration, explanation blurb, confidence badge
  - Primary CTA on each card: "Book This Slot" [id: `slot-card-{slot_id}-book`]
- "Show more times" expander → falls back to a filtered calendar view (still constrainted to this vet's availability)
- Calendar toggle [id: `toggle-calendar-view`]: "Prefer to browse the calendar?" → full month grid view; slots not passing AI filter shown in grey
- If no slots in next 14 days: "No slots available right now" → Waitlist offer (see Section 8)
- Progress bar: Step 4 of 4

**Backend on Load:**
- `GET /public/clinics/{clinic_slug}/availability?appointment_type={type_id}&patient_id={patient_id}&urgency={urgency}&days=14`
- Returns ranked slots from the AI matching algorithm (see Section 7)
- Each slot includes: `{slot_id, start_datetime, end_datetime, resource_id, vet_name, rank_score, rank_explanation}`

**What Backend Does on Slot Selection:**
- Calls `POST /api/schedule` in "hold" mode — creates a soft-hold on the timeslot (10-minute TTL) to prevent race conditions
- Stores `slot_id`, `resource_id`, `start_datetime` on owner session

**Edge Cases:**
- Two owners click the same slot simultaneously: first POST wins; second gets "This slot was just taken — here's the next best option" with the next-ranked slot highlighted
- Owner takes >10 minutes on this screen: soft-hold expires; re-fetch availability before confirming; notify if slot changed: "Your held slot has expired — we've reserved you an equally good time. Review before confirming."
- Vet requests "request-only" (not visible to clients): those vet's slots excluded from public ranking entirely

---

### Step 5: New Patient Details (if needed) / Review & Confirm

**URL:** `https://book.vpma.app/meadow-pet-clinic/confirm`

**Purpose:** Final data collection, review, and book. For returning clients: mostly a summary with a single confirm tap.

**Screen Contents (Returning Client, Wellness for Mochi):**
- Header: "Review your appointment"
- Summary card:
  - Clinic: Meadow Pet Clinic
  - Pet: Mochi (Domestic Shorthair, 4 yrs)
  - Appointment: Annual Wellness Exam · 45 min
  - Date/Time: Thursday, June 25 · 10:30 AM
  - Vet: Dr. Emily Chen
  - Address: 123 Main St, Suite 200
- Edit links next to each section (returns user to that step)
- Contact details pre-filled from owner record (name, phone, email) — editable inline
- Cancellation policy (from `clinic_booking_config.cancellation_policy`) — displayed inline
- Optional: deposit amount (if `clinic_booking_config.require_deposit = true` and MOD-FIN enabled — greyed out with "Coming soon" in Phase 1)
- Checkboxes:
  - [✓] "I agree to the clinic's cancellation policy" [id: `chk-cancellation-policy`]
  - [✓] "I consent to receive SMS reminders about this appointment" [id: `chk-sms-consent`]
- Primary CTA: "**Confirm Appointment**" [id: `btn-confirm-booking`]

**Backend on Confirm:**
1. `POST /public/bookings` — atomically:
   a. Converts soft-hold to confirmed booking (`timeblocks` record, status = 'booked')
   b. Creates `booking_tokens` record (UUID, 72h initial expiry, linked to timeblock)
   c. Creates `intake_tokens` record (UUID, 7-day expiry, linked to booking_token)
   d. Updates `owner_sessions` with confirmed booking
2. Triggers downstream agents (async, not blocking the response):
   - `intake.py` agent: queued with `intake_token` and appointment type
   - `risk.py` agent: final scoring with confirmed slot + patient history
   - `reminders.py` agent: arms T-48h and T-2h reminder pipeline
3. Calls `POST /api/intake/send` with intake_token (fires SMS with intake form link if MOD-COM enabled; otherwise email)
4. Returns: `{booking_token: "uuid", status_url: "https://book.vpma.app/status/{booking_token}", intake_url: "https://book.vpma.app/intake/{intake_token}"}`

**Edge Cases:**
- Soft-hold expired between Step 4 and Step 5: check on load of confirm page; if expired, redirect back to Step 4 with message
- `POST /public/bookings` fails due to race condition (slot double-booked): return to Step 4, slot marked unavailable
- Owner declines SMS consent: intake form falls back to email link only
- New client (no owner_id yet): `POST /public/owners/register` fires first; creates owner record; then booking proceeds

---

### Step 6: Confirmation & Status Page

**URL:** `https://book.vpma.app/status/{booking_token}`

**Purpose:** Landing page after booking. This replaces the static "you're booked" email with a live status tracker.

See Section 9 for full design.

---

## 5. New Client vs. Returning Client Flows

### 5.1 Returning Client Recognition

**Primary lookup:** Phone number (normalized to E.164)  
**Secondary lookup:** Email address  
**Tertiary:** Both (if phone yields multiple matches, email narrows it)

**Database Query:**
```sql
SELECT 
    o.id, o.first_name, o.last_name, o.phone, o.email,
    array_agg(json_build_object(
        'id', p.id,
        'name', p.name,
        'species', p.species,
        'breed', p.breed,
        'dob', p.dob,
        'last_visit', (
            SELECT MAX(t.start_time) FROM timeblocks t WHERE t.patient_id = p.id AND t.status = 'completed'
        )
    )) as pets
FROM owners o
LEFT JOIN patients p ON p.owner_id = o.id AND p.status != 'deceased'
WHERE (o.phone = $1 OR o.email = $2)
  AND o.clinic_id = $3
GROUP BY o.id
LIMIT 5;
```

**Security:** The public-facing lookup returns ONLY: `{found, display_name, pets: [{name, species}]}`. Full record (address, DOB) is NEVER returned at lookup time. It is fetched only after session token is established.

**Session Token:**
- Created on successful lookup
- Stored as `owner_sessions.token` (UUID v4, 128-bit entropy)
- Returned as HttpOnly, Secure, SameSite=Strict cookie
- TTL: 30 minutes from last activity, extended on each request

---

### 5.2 Pre-Fill for Returning Clients

On successful identification, the following data is pre-populated and read-only unless the owner explicitly clicks "Edit":

| Field | Source | Editable? |
|---|---|---|
| Owner first name / last name | `owners.first_name`, `owners.last_name` | Yes (update propagates to owners table) |
| Phone | `owners.phone` | Yes |
| Email | `owners.email` | Yes |
| Pet name | `patients.name` | No (requires staff correction) |
| Pet species / breed | `patients.species`, `patients.breed` | No |
| Pet age | Calculated from `patients.dob` | No |
| Preferred vet | `owners.preferred_resource_id` | Displayed as preference; can change for this booking |
| Last appointment type | From last `timeblocks` record | Used to set default appointment type selection |
| Care protocol dues | `care/protocols` + last visit | Shown as badge suggesting appointment type |

---

### 5.3 New Client Onboarding

For new clients (no existing owner record), the flow is optimized for minimal friction:

**Minimum Required Fields (Phase 1 MVP):**
- Owner: First name, Last name, Phone, Email
- Pet: Name, Species, Breed (optional in Phase 1 if owner doesn't know), Age/DOB (optional)
- Appointment: Type, Urgency, Notes

**Deliberately Deferred to Intake Form (Post-Booking):**
- Pet's full medical history
- Vaccination records
- Current medications
- Known allergies / prior conditions
- Emergency contact
- Insurance information

**Design Rationale:** Every field before booking is a drop-off risk. Move everything non-essential to the intake form, which fires after a commitment (booking) has been made.

**New Client Registration (Backend):**
```
POST /public/owners/register
Body: {
    first_name, last_name, phone, email,
    clinic_id,
    pet: { name, species, breed, dob_approx }
}
→ Creates owners record
→ Creates patients record (linked to owner + clinic)
→ Returns owner_id, patient_id, session token (cookie)
→ Proceeds identically to returning client from Step 3 onward
```

---

### 5.4 Multi-Pet Household

**Pet Selection UX:**

After owner identification, if `pets.length > 1`, show a card grid:

```
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  🐶 Biscuit     │  │  🐶 Gravy       │  │  🐱 Duchess     │
│  Beagle · 3 yrs │  │  Lab Mix · 6 yrs│  │  Siamese · 2 yrs│
│  Last: 6mo ago  │  │  Last: 2mo ago  │  │  ⚠️ Vaccines due│
└─────────────────┘  └─────────────────┘  └─────────────────┘
                        + Add a new pet
```

**Adding a New Pet Mid-Flow:**
- "Add a new pet" opens a modal (not a new page — preserves flow context)
- Minimal fields: Name, Species, Breed (searchable dropdown), Approximate Age
- Submits `POST /public/patients` (after booking session is established)
- New pet card appears in the grid immediately (optimistic UI update)
- Newly added pet is auto-selected; user can change

**Booking Multiple Pets:**
- Not in one booking flow (complexity, different slots needed)
- After confirmation, "Book another appointment for a different pet" CTA is prominent on the status page
- Returns to Step 2 with owner pre-identified; pet selection shown again

---

## 6. Agentic Intake Integration

This is VPMA's definitive differentiator. No competitor does this.

### 6.1 When Does the Intake Agent Fire?

The `intake.py` agent fires **immediately after `POST /public/bookings` returns a confirmed booking** — asynchronously, non-blocking. It does NOT fire on pending/unconfirmed bookings.

**Timing Logic:**
```python
# After booking confirmation
async def trigger_intake_pipeline(booking_token: str, appointment_type_id: str, 
                                   intake_token: str, appointment_datetime: datetime):
    
    # Calculate when to send:
    # - If appointment is > 48h away: send intake immediately (max collection time)
    # - If appointment is 24-48h away: send within 15 minutes
    # - If appointment is < 24h away (same-day): send within 5 minutes
    
    hours_until_appt = (appointment_datetime - datetime.utcnow()).total_seconds() / 3600
    
    if hours_until_appt > 48:
        delay_minutes = 0  # Send immediately
    elif hours_until_appt > 24:
        delay_minutes = 15
    else:
        delay_minutes = 5  # Urgent; send fast
    
    await queue_task("intake_send", {
        "intake_token": intake_token,
        "appointment_type_id": appointment_type_id,
        "delay_minutes": delay_minutes
    })
```

---

### 6.2 Intake Question Sets by Appointment Type

#### Annual Wellness Exam
1. "How has [PetName]'s appetite been over the past month?" — Scale: Great / Normal / Reduced / Not eating
2. "Any changes in water intake?" — More than usual / Normal / Less than usual
3. "Any changes in weight that you've noticed?" — Seems heavier / Same / Seems lighter
4. "How is [PetName]'s energy and activity level?" — More active / Same / Less active / Lethargic
5. "Any vomiting or diarrhea in the past 2 weeks?" — Yes (how often?) / Occasionally / No
6. "Any lumps, bumps, or skin changes you've noticed?" — Yes (describe) / No
7. "Is [PetName] on any medications or supplements currently?" — Yes (list) / No
8. "Any concerns or questions you'd like Dr. [VetName] to address?" — Free text (500 chars)
9. "Does [PetName] need any vaccine boosters today? (We'll check records, but let us know if you know of any.)" — Not sure / Yes / No
10. "Has [PetName] been to any boarding facilities, dog parks, or other pets in the past 30 days?" — Yes / No (relevant for vaccine/parasite risk)

#### Sick Visit
1. "What symptoms is [PetName] showing?" — Multi-select: Vomiting / Diarrhea / Not eating / Limping / Coughing / Sneezing / Eye/nose discharge / Skin issues / Behavior change / Other (describe)
2. "When did you first notice these symptoms?" — Today / 1-3 days ago / 4-7 days ago / More than a week ago
3. "Have the symptoms gotten better, worse, or stayed the same?" — Better / Same / Worse / Much worse
4. "Has [PetName] eaten or drunk anything in the past 24 hours?" — Yes, normally / Yes, less than usual / No
5. "Any chance [PetName] could have eaten something they shouldn't have?" — Yes (what?) / Not sure / No
6. "Any recent travel or exposure to other animals?" — Yes / No
7. "Current medications or supplements?" — Yes (list) / No
8. "Rate your concern level 1-10" — slider [id: `intake-urgency-slider`]
9. "Any additional info for the vet?" — Free text

#### Vaccines Only
1. "Is [PetName] current on all other vaccines?" — Yes / Not sure / No
2. "Any reactions to vaccines in the past?" — Yes (describe) / No
3. "Any current medications?" — Yes (list) / No
4. "Is [PetName] feeling well today? Any symptoms we should know about?" — Yes (describe) / No, feeling fine
5. "Any questions for the tech today?" — Free text

#### Dental Consultation
1. "What prompted you to request a dental consult?" — Routine / Bad breath / Difficulty eating / Visible tartar / Other (describe)
2. "Is [PetName] eating normally?" — Yes / With some difficulty / No
3. "Any pawing at mouth or face?" — Yes, often / Sometimes / No
4. "When was [PetName]'s last dental cleaning (if ever)?" — Never / <1 year / 1-2 years / 2-5 years / 5+ years
5. "Is [PetName] on any blood thinners or heart medications?" — Yes (important for anesthesia risk) / No
6. "Any anesthesia concerns or history of complications?" — Yes (describe) / No
7. "Questions for the vet?" — Free text

#### Follow-Up
1. "How has [PetName] responded to treatment since your last visit?" — Much better / Somewhat better / No change / Worse
2. "Is [PetName] still on the prescribed medications?" — Yes, as directed / Yes, but missed some doses / No (stopped why?)
3. "Any new symptoms since your last visit?" — Yes (describe) / No
4. "Any remaining questions or concerns?" — Free text

---

### 6.3 How the Owner Responds

**Delivery Method Priority:**

1. **SMS (if MOD-COM/Twilio enabled):** Owner receives: "Hi [Name]! Your appointment for [Pet] at [Clinic] on [Date] is confirmed. Complete [Pet]'s pre-visit health check here (takes ~3 min): https://book.vpma.app/intake/{intake_token}. This link expires in 7 days."
2. **Email (always, as fallback):** Same content, styled HTML email with clinic branding
3. **Portal Banner (on status page):** If owner visits status URL before completing intake: orange banner "📋 Complete Mochi's pre-visit health check — it takes 3 minutes and helps Dr. Chen prepare." → links to intake

**Intake Form UI (at `/intake/{intake_token}`):**
- Mobile-optimized, one-question-per-screen format (reduces cognitive load vs. a long form)
- Progress indicator: "Question 3 of 8"
- Save & continue later: responses saved on each answer; token-based resumption
- Estimated time: "~3 minutes" shown on landing
- "Skip this question" allowed for non-mandatory questions
- Final screen: "All done! Dr. [VetName] will review this before your visit."

**After Submission:**
- `POST /public/intake/{intake_token}/submit` 
- `intake.py` parses responses, extracts structured data, and sets flags
- Flags (examples):
  - `flag_clinical_weight_loss` — if appetite reduced + weight loss noted
  - `flag_anesthesia_risk` — if cardiac meds mentioned + dental consult type
  - `flag_potential_toxin_ingestion` — if "ate something they shouldn't" in sick visit
  - `flag_vaccine_reaction_history` — if past reaction noted
- All flags written to `intake_responses.flags` (JSONB)
- `risk.py` re-scores with intake data incorporated into risk vector

---

### 6.4 How Intake Data Surfaces in the Staff Dashboard

**On the Appointment Card (scheduling board view):**
- Intake status badge: 🟢 Intake Complete / 🟡 Intake Sent / 🔴 Not Started
- If complete: "View intake" link → inline drawer or modal showing all Q&A pairs

**On the Patient Chart (before appointment):**
- "Online Intake" section at top of chart, collapsed by default
- Expands to show all Q&A, timestamps, and auto-generated clinical flags in red/amber/green
- Critical flags shown in a prominent "⚠️ Pre-visit flags" box at top of section:
  ```
  ⚠️ CLINICAL FLAGS (set by intake agent)
  • Reduced appetite + weight loss reported (Owner rated 8/10 concern)
  • No current medications
  • No known allergies
  ```
- All intake text is part of the Verbose Log audit trail

**Staff Alert (if `risk.py` flags urgency):**
- If risk score crosses threshold AND appointment is in next 24h: 
  - Staff dashboard notification: "⚠️ [Pet] (appt tomorrow, [time]) — intake flagged potential [issue]. Review intake."

---

## 7. Intelligent Slot Suggestion — AI Matching Layer

### 7.1 The Problem with Competitor Approaches

Every competitor shows this:

```
[  Mon  ] [  Tue  ] [  Wed  ] [  Thu  ] [  Fri  ]
[ 9:00  ] [       ] [ 10:30 ] [ 9:00  ] [       ]
[ 11:00 ] [ 1:00  ] [       ] [ 11:30 ] [ 2:00  ]
```

This is a scheduling grid. It contains zero intelligence. The owner must:
- Know which vet they want
- Know how long the appointment takes
- Figure out which slot "works"
- Have no idea that Thursday 9am has a 34% no-show rate for this practice

VPMA replaces this with **ranked slot cards** with plain-language explanations.

---

### 7.2 The Slot Ranking Algorithm

**Input Variables:**

| Variable | Source | Weight |
|---|---|---|
| Vet continuity for this patient | `timeblocks` history → `resource_id` of last visit | High (3x) |
| Appointment duration fit | `clinic_booking_config.appointment_durations` + breed overrides | Required (hard constraint) |
| No-show risk by day/time | `risk.py` model: historical slot-level no-show rate | Medium (1.5x) |
| Vet specialization match for complaint | `resources.specializations` vs. `appointment_type + notes` | Medium (2x) |
| Time-to-appointment (urgency) | If urgency=urgent: prefer soonest; else prefer convenient day spread | Conditional |
| Owner-stated time preferences | If provided at prior step (e.g., "mornings preferred"): boost morning slots | Low (1x) |
| Slot buffer adequacy | Ensure prior/next appointment has ≥10min buffer | Required (hard constraint) |
| Vet "hidden" status | `clinic_booking_config.hidden_vets` | Required (exclusion) |

**Scoring Function (simplified):**

```python
def score_slot(slot: Slot, patient: Patient, appointment_type: AppointmentType, 
               urgency: str, owner_prefs: dict) -> float:
    score = 0.0
    
    # Vet continuity (strongest signal)
    if slot.resource_id == patient.preferred_resource_id:
        score += 30.0
    elif slot.resource_id == patient.last_seen_resource_id:
        score += 20.0
    
    # Vet specialization match
    if appointment_type.tags in slot.resource.specializations:
        score += 20.0
    
    # No-show risk (lower historical no-show rate = higher score)
    no_show_rate = get_historical_no_show_rate(slot.start_datetime.weekday(), 
                                                slot.start_datetime.hour,
                                                slot.resource_id)
    score += (1.0 - no_show_rate) * 15.0  # 0-15 points
    
    # Urgency bonus for soonest slot
    if urgency in ('urgent', 'emergency'):
        hours_until = (slot.start_datetime - datetime.utcnow()).total_seconds() / 3600
        score += max(0, 15 - hours_until)  # Decays as appointment gets further away
    
    # Time preference match
    if owner_prefs.get('preferred_time') == 'morning' and slot.start_datetime.hour < 12:
        score += 5.0
    
    return score

def generate_explanation(slot: Slot, patient: Patient, score_factors: dict) -> str:
    parts = []
    if score_factors['vet_continuity']:
        parts.append(f"Dr. {slot.resource.last_name} has seen {patient.name} before")
    if score_factors['duration_fit']:
        parts.append(f"has a {slot.duration_minutes}-min slot that's perfect for {appointment_type.name}")
    if score_factors['low_no_show']:
        parts.append("this time slot historically has the highest attendance rate")
    return " · ".join(parts)
```

**Output:** Top 3 ranked slots returned in the availability response.

---

### 7.3 Slot Card UI

```
┌─────────────────────────────────────────────────────────┐
│  ⭐ Best Match                                           │
│                                                         │
│  Thursday, June 26 · 10:30 AM                          │
│  Dr. Emily Chen  ·  45 min  ·  Annual Wellness         │
│                                                         │
│  "Dr. Chen has seen Mochi before and has a 45-min slot  │
│   that's perfect for an annual wellness exam."          │
│                                                         │
│                    [ Book This Slot ]                   │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  🕐 Also Great                                          │
│                                                         │
│  Friday, June 27 · 9:00 AM                             │
│  Dr. Marcus Webb  ·  45 min  ·  Annual Wellness        │
│                                                         │
│  "Morning slot with low no-show rate — great for        │
│   getting the day started."                             │
│                                                         │
│                    [ Book This Slot ]                   │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  📅 Next Available                                      │
│                                                         │
│  Monday, June 30 · 2:00 PM                             │
│  Dr. Sarah Patel  ·  45 min  ·  Annual Wellness        │
│                                                         │
│  "Soonest available if the earlier times don't work."  │
│                                                         │
│                    [ Book This Slot ]                   │
└─────────────────────────────────────────────────────────┘

                    ↓ Show more times
```

**Slot Card States:**
- `default`: Normal display as above
- `held`: "Someone is holding this slot" — dim card, show "available if they don't confirm"
- `expired_hold`: Back to available — shown with a brief green flash animation
- `selected`: Blue border, "Booked ✓" badge animates in

---

### 7.4 Waitlist Integration (No Availability Path)

If `GET /public/clinics/{clinic_slug}/availability` returns 0 slots within the advance booking window:

```
┌─────────────────────────────────────────────────────────┐
│  😞 No availability in the next 14 days                │
│                                                         │
│  But don't worry — Mochi's on our radar.               │
│  Join the waitlist and we'll text you the moment       │
│  a slot opens up. You'll have 30 minutes to confirm.   │
│                                                         │
│            [ Join Waitlist for Mochi ]                  │
│                                                         │
│  Or call us: (555) 123-4567                            │
└─────────────────────────────────────────────────────────┘
```

---

## 8. Waitlist UX

### 8.1 How Clients Join from the Booking Portal

**Entry Points:**
1. No-availability screen (Step 4 — slot selection)
2. Status page "Join waitlist for an earlier slot" CTA (for owners who booked a far-out slot and want something sooner)
3. Directly: `https://book.vpma.app/meadow-pet-clinic/waitlist`

**Waitlist Join Form (single screen, ~4 fields):**
- "Which pet?" — pre-filled if session active
- "What appointment type?" — pre-filled from prior flow
- Urgency: Wellness / Routine / Urgent (note: "If emergency, please call us now")
- "When can you come in?" — checkboxes:
  - ☑ Weekday mornings (Mon-Fri, 8am-12pm)
  - ☑ Weekday afternoons (Mon-Fri, 12pm-5pm)
  - ☐ Saturday mornings (if clinic open)
  - ☐ Any time (most flexible — recommended)
- "How far in advance do you need notice?" — 
  - At least 1 hour
  - At least 3 hours
  - At least 1 day
- Phone number for SMS notification (pre-filled)

**Backend:**
```
POST /public/waitlist/join
Body: {
    clinic_id, patient_id, owner_id,
    appointment_type_id, urgency,
    time_preferences: ["weekday_morning", "weekday_afternoon"],
    min_notice_hours: 1,
    phone: "5551234567",
    active: true,
    joined_at: timestamp
}
→ Creates waitlist record
→ waitlist.py agent picks this up for AI-backfill matching
```

---

### 8.2 Data Captured at Waitlist Join

| Field | Purpose |
|---|---|
| `urgency` | Priority ranking in waitlist queue |
| `time_preferences` | Filter eligible slots before notifying |
| `min_notice_hours` | Don't notify if slot is < X hours away |
| `phone` | Primary notification channel (SMS) |
| `active` | Set to false on accept or explicit cancellation |
| `joined_at` | For FIFO tie-breaking at equal urgency |
| `appointment_type_id` | Match to correct slot duration |
| `preferred_resource_id` | Optional: "Any vet" vs. specific vet |
| `flexibility_score` | Computed: wider time window = higher score = faster fill |

---

### 8.3 Notification Flow When a Slot Opens

**Trigger:** When a booking is cancelled or a slot is added via staff-side scheduling.

**`waitlist.py` Agent Flow:**
1. Cancellation event fires → `waitlist.py` queries all active waitlist entries for that `clinic_id` + `appointment_type_id`
2. Rank candidates by: urgency DESC, flexibility_score DESC, joined_at ASC
3. For top candidate: check if slot time matches `time_preferences` AND notice window ≥ `min_notice_hours`
4. If match: send SMS notification (MOD-COM) or email fallback

**SMS Notification Text:**
```
Hi [Name]! Great news — a slot just opened at Meadow Pet Clinic 
for [Pet] on [Day, Date] at [Time] with Dr. [Name].

Tap to claim this slot (expires in 30 min):
https://book.vpma.app/waitlist/claim/{waitlist_claim_token}

Reply SKIP to pass and stay on the waitlist.
```

**Claim token:** UUID, 30-minute hard expiry. Created in `waitlist_claim_tokens` table.

---

### 8.4 Accepting From SMS Without Login

**URL:** `https://book.vpma.app/waitlist/claim/{waitlist_claim_token}`

**On Load:**
- Token validated; slot still available: show "Confirm your appointment" screen
- Shows: Pet name, date/time, vet, duration
- Single CTA: "**Confirm — Book This Slot**" [id: `btn-claim-slot`]
- Sub-text: "This offer expires in [XX:XX remaining]" — live countdown timer

**On Confirm:**
1. Slot booked atomically (same flow as standard booking)
2. Owner's `waitlist` record set to `active = false`
3. If slot is already gone (race condition): "Someone else just claimed this slot. We'll notify you when the next one opens."
4. Booking confirmation and status page generated normally

**No-login design:** The `waitlist_claim_token` IS the authentication. It contains the `owner_id` and `patient_id` embedded (encrypted, not as plain URL params). No password required.

---

### 8.5 If Owner Passes (SKIP)

- Reply SKIP → `waitlist.py` marks `waitlist_claim_tokens.status = 'passed'`
- Owner stays at same position in queue (not penalized for one pass)
- After 3 consecutive passes: auto-remove from waitlist with notification: "You've passed on 3 slots — we've removed you from the waitlist. Reply REJOIN to re-add yourself."
- Next candidate in queue is notified within 30 seconds (automated re-trigger)

---

## 9. Confirmation & Status Tracking Page

### 9.1 The Status Page Concept

Every booking generates a unique, shareable URL:  
`https://book.vpma.app/status/{booking_token}`

This is not a static confirmation page. It is a **live lifecycle tracker** that updates as the appointment progresses. Token is valid for 30 days after the appointment date.

---

### 9.2 Appointment Lifecycle States

```
BOOKED → INTAKE_SENT → INTAKE_COMPLETE → CONFIRMED → IN_PROGRESS → COMPLETE → FOLLOW_UP_SENT
```

| State | Trigger | Owner-Visible Message |
|---|---|---|
| `BOOKED` | `POST /public/bookings` succeeds | "Your appointment is confirmed! We'll send you a pre-visit health check shortly." |
| `INTAKE_SENT` | `intake.py` dispatches intake form | "We sent Mochi's pre-visit health check to [phone]. Complete it to help Dr. Chen prepare." |
| `INTAKE_COMPLETE` | `POST /public/intake/{token}/submit` | "Pre-visit health check complete ✓ Dr. Chen will review before your visit." |
| `CONFIRMED` | Staff manually confirms (if manual mode) OR T-48h reminder sent | "Your appointment is confirmed! See you Thursday at 10:30 AM." |
| `IN_PROGRESS` | Staff marks check-in on scheduling board | "Mochi is checked in! The team is with you now." |
| `COMPLETE` | Staff marks appointment complete | "All done! Great visit. We'll send follow-up notes to [email]." |
| `FOLLOW_UP_SENT` | `followup.py` agent dispatches | "Follow-up care instructions sent to [email]. See you next time!" |

---

### 9.3 Status Page UI Design

```
┌──────────────────────────────────────────────────────────┐
│   🐾 Meadow Pet Clinic                                   │
│   ________________________________________________      │
│                                                          │
│   Mochi's Annual Wellness Exam                          │
│   Thursday, June 26 · 10:30 AM · Dr. Emily Chen        │
│   45 Meadow Lane, Suite 200, Springfield                │
│                                                          │
│   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━      │
│                                                          │
│   Appointment Status                                     │
│                                                          │
│   ✅ Booked              Thu Jun 19, 8:23 PM            │
│   ✅ Intake Sent         Thu Jun 19, 8:24 PM            │
│   🟡 Intake Complete     Complete your health check →   │
│   ○  Confirmed                                          │
│   ○  In Progress                                        │
│   ○  Complete                                           │
│   ○  Follow-Up Sent                                     │
│                                                          │
│   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━      │
│                                                          │
│   📋 Pre-Visit Health Check                             │
│   [  Complete Mochi's intake form  ]   (3 min)         │
│                                                          │
│   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━      │
│                                                          │
│   Quick Actions                                         │
│   [ 📅 Add to Calendar ] [ 🔄 Reschedule ] [ ✖ Cancel ]│
│                                                          │
│   📍 Get Directions  ·  📞 Call Clinic                 │
└──────────────────────────────────────────────────────────┘
```

---

### 9.4 Client Actions from Status Page

| Action | Behavior | Backend |
|---|---|---|
| **Add to Calendar** | Generates `.ics` file on-the-fly; also shows "Add to Google Calendar" link with pre-filled params | `GET /public/bookings/{token}/calendar.ics` |
| **Reschedule** | Opens slot selection (Step 4) with current booking pre-cancelled on confirm | `POST /public/bookings/{token}/reschedule` (atomic: cancel + rebook) |
| **Cancel** | Confirmation modal: "Are you sure? Cancellations within 24h may incur a fee." → `POST /public/bookings/{token}/cancel` | Sends cancellation notification to staff; triggers waitlist backfill |
| **View Intake** | If intake complete: collapsible section showing Q&A submitted | Rendered from `intake_responses` (token-gated) |
| **Join Waitlist for earlier** | If appointment >7 days out: CTA to join waitlist for sooner slot | Navigates to waitlist join with pre-filled context |

---

### 9.5 Real-Time Updates

**Mechanism:** Server-Sent Events (SSE) on `GET /public/bookings/{token}/stream`

```javascript
const eventSource = new EventSource(`/public/bookings/${token}/stream`);
eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    updateStatusUI(data.status, data.timestamp);
};
```

- SSE is used instead of WebSockets for simplicity (one-way, server → client)
- If SSE not supported (old browser): falls back to 30-second polling
- Status page is also valid as a static snapshot (no SSE) — the lifecycle progression is readable without real-time updates

---

## 10. Public API Design

All public routes are prefixed with `/public/`. They require **no staff auth tokens**. They are rate-limited, CORS-restricted to allowed origins, and audited via the Verbose Log.

---

### `GET /public/clinics/{clinic_slug}`

**Auth:** None (fully public)  
**Purpose:** Fetch clinic metadata for portal rendering  
**Rate Limit:** 60 req/min per IP

**Response:**
```json
{
  "clinic_id": "uuid",
  "name": "Meadow Pet Clinic",
  "slug": "meadow-pet-clinic",
  "address": "45 Meadow Lane, Suite 200, Springfield, IL 62701",
  "phone": "(555) 123-4567",
  "email": "hello@meadowpetclinic.com",
  "timezone": "America/Chicago",
  "logo_url": "https://cdn.vpma.app/clinics/meadow-pet-clinic/logo.png",
  "brand_color": "#2E7D52",
  "booking_config": {
    "online_booking_enabled": true,
    "advance_booking_days": 30,
    "same_day_cutoff_hour": 14,
    "same_day_enabled": true,
    "emergency_phone": "(555) 911-0000",
    "cancellation_policy": "Cancellations must be made at least 24 hours in advance.",
    "auto_confirm": true,
    "require_deposit": false,
    "bookable_appointment_types": [
      {"id": "wellness", "name": "Annual Wellness Exam", "duration_minutes": 45},
      {"id": "sick", "name": "Sick Visit", "duration_minutes": 30},
      {"id": "vaccines", "name": "Vaccines Only", "duration_minutes": 15},
      {"id": "dental", "name": "Dental Consultation", "duration_minutes": 30},
      {"id": "followup", "name": "Follow-Up", "duration_minutes": 15}
    ]
  }
}
```

---

### `GET /public/clinics/{clinic_slug}/availability`

**Auth:** None  
**Purpose:** Fetch AI-ranked available slots  
**Rate Limit:** 30 req/min per IP  

**Query Params:**
```
appointment_type_id: string (required)
days: integer (default: 14, max: 60)
patient_id: string (optional — enables vet continuity ranking)
urgency: string (optional — "routine" | "urgent")
preferred_time: string (optional — "morning" | "afternoon" | "any")
```

**Response:**
```json
{
  "slots": [
    {
      "slot_id": "uuid",
      "resource_id": "uuid",
      "vet_name": "Dr. Emily Chen",
      "vet_photo_url": "https://cdn.vpma.app/...",
      "start_datetime": "2026-06-26T10:30:00-05:00",
      "end_datetime": "2026-06-26T11:15:00-05:00",
      "duration_minutes": 45,
      "rank": 1,
      "rank_label": "Best Match",
      "rank_explanation": "Dr. Chen has seen Mochi before and has a 45-min slot perfect for an annual wellness exam.",
      "no_show_risk_label": "Low"
    },
    {
      "slot_id": "uuid",
      "resource_id": "uuid",
      "vet_name": "Dr. Marcus Webb",
      "start_datetime": "2026-06-27T09:00:00-05:00",
      "end_datetime": "2026-06-27T09:45:00-05:00",
      "duration_minutes": 45,
      "rank": 2,
      "rank_label": "Also Great",
      "rank_explanation": "Morning slot with historically low no-show rate.",
      "no_show_risk_label": "Low"
    }
  ],
  "total_available": 12,
  "showing_top": 3,
  "has_more": true,
  "waitlist_available": false
}
```

**Backend Functions Called:**
- `GET /api/resources` (internal) → fetch vet list filtered by `hidden = false`
- `GET /api/timeblocks` (internal) → fetch existing appointments for availability gaps
- `risk.py::get_slot_no_show_rates()` → historical no-show rate per slot
- `score_slot()` → rank and annotate slots

---

### `POST /public/owners/lookup`

**Auth:** None  
**Purpose:** Identify returning client  
**Rate Limit:** 10 req/5min per IP  

**Request:**
```json
{
  "clinic_id": "uuid",
  "phone": "5551234567",
  "email": "marcus@example.com"
}
```

**Response (found):**
```json
{
  "found": true,
  "owner_id": "uuid",
  "display_name": "Marcus",
  "pets": [
    {
      "id": "uuid",
      "name": "Mochi",
      "species": "cat",
      "breed": "Domestic Shorthair",
      "age_years": 4,
      "last_visit_label": "14 months ago",
      "care_due": true,
      "care_due_reason": "Annual wellness overdue"
    }
  ]
}
```

**Response (not found):**
```json
{
  "found": false
}
```

**Side Effect:** On `found: true`, creates `owner_sessions` record. Returns session token as `Set-Cookie: vpma_session=<token>; HttpOnly; Secure; SameSite=Strict; Max-Age=1800`

---

### `POST /public/owners/register`

**Auth:** None  
**Purpose:** Create new owner + first patient record  
**Rate Limit:** 5 req/5min per IP  

**Request:**
```json
{
  "clinic_id": "uuid",
  "first_name": "Sarah",
  "last_name": "Johnson",
  "phone": "5559876543",
  "email": "sarah@example.com",
  "sms_consent": true,
  "pet": {
    "name": "Biscuit",
    "species": "dog",
    "breed": "Beagle",
    "dob_approx": "2023-01-01",
    "sex": "male",
    "neutered": true
  }
}
```

**Response:**
```json
{
  "owner_id": "uuid",
  "patient_id": "uuid",
  "session_established": true
}
```

**Backend:**
1. Check for existing owner by phone/email (duplicate prevention)
2. `POST /api/owners` (internal, bypassing staff auth via internal API key)
3. `POST /api/patients` (internal)
4. Creates `owner_sessions` record; returns session cookie

---

### `POST /public/bookings`

**Auth:** `owner_sessions` cookie (required)  
**Purpose:** Confirm a booking  
**Rate Limit:** 5 req/hour per session  

**Request:**
```json
{
  "slot_id": "uuid",
  "patient_id": "uuid",
  "appointment_type_id": "wellness",
  "urgency": "routine",
  "notes": "Mochi has been scratching her ears more than usual",
  "sms_consent": true,
  "cancellation_policy_accepted": true
}
```

**Response:**
```json
{
  "booking_id": "uuid",
  "booking_token": "a1b2c3d4-e5f6-...",
  "status": "booked",
  "status_url": "https://book.vpma.app/status/a1b2c3d4-e5f6-...",
  "intake_url": "https://book.vpma.app/intake/x9y8z7w6-...",
  "appointment": {
    "date": "2026-06-26",
    "time": "10:30",
    "duration_minutes": 45,
    "vet_name": "Dr. Emily Chen",
    "clinic_name": "Meadow Pet Clinic",
    "address": "45 Meadow Lane, Suite 200"
  }
}
```

**Backend (Atomic Transaction):**
```sql
BEGIN;
  -- Convert soft-hold to confirmed booking
  INSERT INTO timeblocks (
    clinic_id, resource_id, patient_id, owner_id, 
    start_time, end_time, appointment_type_id, 
    status, urgency, client_notes, source
  ) VALUES (..., 'booked', 'routine', $notes, 'online_portal');
  
  -- Create booking token
  INSERT INTO booking_tokens (
    id, timeblock_id, owner_id, expires_at, status
  ) VALUES (gen_random_uuid(), $timeblock_id, $owner_id, NOW() + INTERVAL '30 days', 'active');
  
  -- Create intake token  
  INSERT INTO intake_tokens (
    id, booking_token_id, expires_at, status
  ) VALUES (gen_random_uuid(), $booking_token_id, NOW() + INTERVAL '7 days', 'pending');
  
  -- Release soft-hold
  DELETE FROM slot_holds WHERE slot_id = $slot_id AND owner_session_id = $session_id;
COMMIT;
```

---

### `GET /public/bookings/{booking_token}`

**Auth:** None (token IS the auth — must be valid, non-expired, non-revoked)  
**Purpose:** Fetch booking status for status page  

**Response:**
```json
{
  "booking_id": "uuid",
  "status": "intake_sent",
  "clinic_name": "Meadow Pet Clinic",
  "pet_name": "Mochi",
  "appointment_type": "Annual Wellness Exam",
  "vet_name": "Dr. Emily Chen",
  "start_datetime": "2026-06-26T10:30:00-05:00",
  "duration_minutes": 45,
  "address": "45 Meadow Lane, Suite 200, Springfield, IL 62701",
  "lifecycle": [
    {"state": "booked", "completed_at": "2026-06-19T20:23:00Z", "completed": true},
    {"state": "intake_sent", "completed_at": "2026-06-19T20:24:00Z", "completed": true},
    {"state": "intake_complete", "completed_at": null, "completed": false},
    {"state": "confirmed", "completed_at": null, "completed": false},
    {"state": "in_progress", "completed_at": null, "completed": false},
    {"state": "complete", "completed_at": null, "completed": false},
    {"state": "follow_up_sent", "completed_at": null, "completed": false}
  ],
  "intake_token": "x9y8z7w6-...",
  "intake_status": "pending",
  "cancellable": true,
  "reschedulable": true,
  "calendar_url": "https://book.vpma.app/status/{token}/calendar.ics"
}
```

---

### `POST /public/bookings/{booking_token}/cancel`

**Auth:** Token (no additional auth required)  
**Rate Limit:** 3 req/hour per token  

**Request:**
```json
{
  "reason": "schedule_conflict",
  "notes": "Work meeting came up"
}
```

**Response:**
```json
{
  "status": "cancelled",
  "cancelled_at": "2026-06-20T14:00:00Z",
  "fee_applied": false,
  "message": "Your appointment has been cancelled. No fee applies."
}
```

**Backend:**
1. Set `timeblocks.status = 'cancelled'`
2. Set `booking_tokens.status = 'cancelled'`
3. Trigger `waitlist.py` backfill (slot now available)
4. Send staff notification
5. Send owner cancellation confirmation (SMS + email)
6. Check cancellation policy: if within X hours, flag for staff to review fee

---

### `GET /public/intake/{intake_token}`

**Auth:** Token  
**Purpose:** Fetch intake form questions and any saved progress  

**Response:**
```json
{
  "intake_id": "uuid",
  "appointment_type": "wellness",
  "pet_name": "Mochi",
  "vet_name": "Dr. Emily Chen",
  "appointment_date": "2026-06-26",
  "status": "in_progress",
  "questions": [
    {
      "id": "q_appetite",
      "order": 1,
      "text": "How has Mochi's appetite been over the past month?",
      "type": "single_choice",
      "options": ["Great", "Normal", "Reduced", "Not eating"],
      "answer": null,
      "required": true
    },
    {
      "id": "q_water",
      "order": 2,
      "text": "Any changes in water intake?",
      "type": "single_choice",
      "options": ["More than usual", "Normal", "Less than usual"],
      "answer": null,
      "required": false
    }
  ],
  "total_questions": 10,
  "completed_questions": 0,
  "estimated_minutes": 3
}
```

---

### `POST /public/intake/{intake_token}/submit`

**Auth:** Token  
**Purpose:** Submit completed intake form  

**Request:**
```json
{
  "answers": [
    {"question_id": "q_appetite", "answer": "Normal"},
    {"question_id": "q_water", "answer": "Normal"},
    {"question_id": "q_weight", "answer": "Seems lighter"},
    {"question_id": "q_energy", "answer": "Less active"},
    {"question_id": "q_gi", "answer": "No"},
    {"question_id": "q_skin", "answer": "No"},
    {"question_id": "q_meds", "answer": "No"},
    {"question_id": "q_concerns", "answer": "She seems a bit tired lately, and has lost some weight"},
    {"question_id": "q_vaccines", "answer": "Not sure"},
    {"question_id": "q_exposure", "answer": "No"}
  ],
  "submitted_at": "2026-06-20T09:45:00Z"
}
```

**Response:**
```json
{
  "status": "complete",
  "flags_raised": 2,
  "message": "Thank you! Dr. Chen will review this before your visit.",
  "booking_status_url": "https://book.vpma.app/status/a1b2c3d4-..."
}
```

**Backend:**
1. Store all answers in `intake_responses` (JSONB)
2. `intake.py` parses answers, runs flag logic:
   - `weight_loss + low_energy` → set `flag_clinical_weight_loss = true`
3. `risk.py` re-scores with intake answers incorporated
4. Update `booking_tokens.status = 'intake_complete'`
5. Update `intake_tokens.status = 'complete'`
6. If any high-severity flag: push staff alert notification

---

### `GET /public/waitlist/{clinic_slug}/join`

**Auth:** None  
**Purpose:** Render waitlist join form with clinic context  

**Response:** Same as `GET /public/clinics/{clinic_slug}` but filtered to waitlist context (appointment types only, no slot data).

---

### `POST /public/waitlist/join`

**Auth:** `owner_sessions` cookie OR anonymous (creates guest record)  
**Purpose:** Add owner/patient to waitlist  

**Request:**
```json
{
  "clinic_id": "uuid",
  "patient_id": "uuid",
  "owner_id": "uuid",
  "appointment_type_id": "wellness",
  "urgency": "routine",
  "time_preferences": ["weekday_morning", "weekday_afternoon"],
  "min_notice_hours": 3,
  "phone": "5551234567"
}
```

**Response:**
```json
{
  "waitlist_id": "uuid",
  "position": 3,
  "message": "You're #3 on the waitlist. We'll text you at (555) 123-4567 when a slot opens.",
  "manage_url": "https://book.vpma.app/waitlist/{waitlist_token}"
}
```

---

### `GET /public/bookings/{booking_token}/stream` (SSE)

**Auth:** Token  
**Purpose:** Server-Sent Events for real-time status updates  

**Event Format:**
```
data: {"status": "intake_complete", "timestamp": "2026-06-20T09:45:00Z"}

data: {"status": "confirmed", "timestamp": "2026-06-20T10:00:00Z"}
```

**Implementation Notes:**
- FastAPI `StreamingResponse` with `text/event-stream` content type
- Keep-alive ping every 30 seconds: `data: {"type": "ping"}`
- Connection closes automatically when booking reaches terminal state (`complete` or `cancelled`)

---

## 11. Data Model Changes

### 11.1 New Tables

#### `booking_tokens`

```sql
CREATE TABLE booking_tokens (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timeblock_id    UUID NOT NULL REFERENCES timeblocks(id) ON DELETE CASCADE,
    owner_id        UUID NOT NULL REFERENCES owners(id),
    clinic_id       UUID NOT NULL REFERENCES clinics(id),
    
    -- Token lifecycle
    status          TEXT NOT NULL DEFAULT 'active'
                    CHECK (status IN ('active', 'cancelled', 'expired', 'complete')),
    expires_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (NOW() + INTERVAL '30 days'),
    
    -- Booking lifecycle state (mirrors appointment status)
    lifecycle_state TEXT NOT NULL DEFAULT 'booked'
                    CHECK (lifecycle_state IN (
                        'booked', 'intake_sent', 'intake_complete', 
                        'confirmed', 'in_progress', 'complete', 'follow_up_sent'
                    )),
    
    -- Audit
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    cancelled_at    TIMESTAMP WITH TIME ZONE,
    cancel_reason   TEXT,
    cancel_notes    TEXT,
    
    -- Source tracking
    booked_via      TEXT NOT NULL DEFAULT 'online_portal'
                    CHECK (booked_via IN ('online_portal', 'staff_dashboard', 'waitlist_claim', 'phone'))
);

CREATE INDEX idx_booking_tokens_timeblock_id ON booking_tokens(timeblock_id);
CREATE INDEX idx_booking_tokens_owner_id ON booking_tokens(owner_id);
CREATE INDEX idx_booking_tokens_expires_at ON booking_tokens(expires_at) WHERE status = 'active';
```

#### `intake_tokens`

```sql
CREATE TABLE intake_tokens (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    booking_token_id    UUID NOT NULL REFERENCES booking_tokens(id) ON DELETE CASCADE,
    clinic_id           UUID NOT NULL REFERENCES clinics(id),
    patient_id          UUID NOT NULL REFERENCES patients(id),
    appointment_type_id TEXT NOT NULL,
    
    -- Token lifecycle
    status              TEXT NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'sent', 'in_progress', 'complete', 'expired', 'skipped')),
    expires_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (NOW() + INTERVAL '7 days'),
    sent_at             TIMESTAMP WITH TIME ZONE,
    completed_at        TIMESTAMP WITH TIME ZONE,
    
    -- Intake responses (stored as JSONB for schema flexibility)
    responses           JSONB,           -- Array of {question_id, answer, answered_at}
    flags               JSONB,           -- Set by intake.py: {flag_name: bool, ...}
    risk_score_delta    FLOAT,           -- How much intake changed patient risk score
    
    -- Delivery tracking
    delivery_method     TEXT CHECK (delivery_method IN ('sms', 'email', 'both')),
    sms_sent_to         TEXT,
    email_sent_to       TEXT,
    
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_intake_tokens_booking_token_id ON intake_tokens(booking_token_id);
CREATE INDEX idx_intake_tokens_status ON intake_tokens(status) WHERE status IN ('pending', 'sent', 'in_progress');
CREATE INDEX idx_intake_tokens_expires_at ON intake_tokens(expires_at) WHERE status != 'complete';
```

#### `owner_sessions`

```sql
CREATE TABLE owner_sessions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id        UUID REFERENCES owners(id),      -- NULL for anonymous/pre-registration
    clinic_id       UUID NOT NULL REFERENCES clinics(id),
    
    -- Session data (minimal; most data stays in owners/patients tables)
    ip_address      INET,
    user_agent      TEXT,
    
    -- Flow state (ephemeral booking context)
    flow_state      JSONB,   -- {selected_patient_id, selected_slot_id, selected_appt_type, ...}
    
    -- Lifecycle
    expires_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (NOW() + INTERVAL '30 minutes'),
    last_active_at  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Associated bookings (for post-session reference)
    booking_token_id UUID REFERENCES booking_tokens(id)
);

CREATE INDEX idx_owner_sessions_owner_id ON owner_sessions(owner_id);
CREATE INDEX idx_owner_sessions_expires_at ON owner_sessions(expires_at);

-- Cleanup job: DELETE FROM owner_sessions WHERE expires_at < NOW()
-- Run every 15 minutes via pg_cron or a FastAPI background task
```

#### `clinic_booking_config`

```sql
CREATE TABLE clinic_booking_config (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinic_id                   UUID NOT NULL UNIQUE REFERENCES clinics(id) ON DELETE CASCADE,
    
    -- Feature flags
    online_booking_enabled      BOOLEAN NOT NULL DEFAULT FALSE,
    same_day_booking_enabled    BOOLEAN NOT NULL DEFAULT FALSE,
    waitlist_enabled            BOOLEAN NOT NULL DEFAULT TRUE,
    auto_confirm                BOOLEAN NOT NULL DEFAULT TRUE,   -- If false: staff must manually confirm
    require_deposit             BOOLEAN NOT NULL DEFAULT FALSE,  -- MOD-FIN hook
    deposit_amount_cents        INTEGER,
    
    -- Scheduling rules
    advance_booking_days        INTEGER NOT NULL DEFAULT 30,     -- Max days in future for booking
    same_day_cutoff_hour        INTEGER NOT NULL DEFAULT 14,     -- 14 = 2:00 PM local time
    min_booking_notice_hours    INTEGER NOT NULL DEFAULT 1,      -- Can't book < X hours from now
    max_pets_per_booking        INTEGER NOT NULL DEFAULT 1,
    
    -- Display settings
    show_vet_names              BOOLEAN NOT NULL DEFAULT TRUE,
    show_vet_photos             BOOLEAN NOT NULL DEFAULT FALSE,
    show_estimated_wait         BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Appointment types (which are bookable online)
    bookable_appointment_types  JSONB NOT NULL DEFAULT '[]',     -- [{id, name, duration_minutes, enabled}]
    appointment_durations       JSONB NOT NULL DEFAULT '{}',     -- {type_id: minutes, breed_overrides: {}}
    
    -- Messaging customization
    booking_confirmation_msg    TEXT,           -- Custom message shown on confirmation
    intake_sms_template         TEXT,           -- Custom SMS text (uses template vars)
    cancellation_policy         TEXT,
    
    -- Hidden vets (not shown to clients)
    hidden_resource_ids         UUID[] NOT NULL DEFAULT '{}',    -- Array of resource UUIDs
    
    -- Emergency info
    emergency_phone             TEXT,
    emergency_message           TEXT,
    
    -- Branding
    brand_color_primary         TEXT DEFAULT '#2E7D52',
    brand_color_accent          TEXT DEFAULT '#F0A500',
    
    created_at                  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
```

#### `slot_holds` (soft-hold table for race condition prevention)

```sql
CREATE TABLE slot_holds (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinic_id           UUID NOT NULL REFERENCES clinics(id),
    resource_id         UUID NOT NULL REFERENCES resources(id),
    start_datetime      TIMESTAMP WITH TIME ZONE NOT NULL,
    end_datetime        TIMESTAMP WITH TIME ZONE NOT NULL,
    owner_session_id    UUID NOT NULL REFERENCES owner_sessions(id),
    held_at             TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    expires_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (NOW() + INTERVAL '10 minutes'),
    
    CONSTRAINT uq_slot_hold UNIQUE (clinic_id, resource_id, start_datetime)
);

CREATE INDEX idx_slot_holds_expires ON slot_holds(expires_at);
-- Cleanup: DELETE FROM slot_holds WHERE expires_at < NOW()
```

#### `waitlist` (enhanced version of existing waitlist table)

```sql
CREATE TABLE waitlist (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinic_id               UUID NOT NULL REFERENCES clinics(id),
    owner_id                UUID NOT NULL REFERENCES owners(id),
    patient_id              UUID NOT NULL REFERENCES patients(id),
    appointment_type_id     TEXT NOT NULL,
    
    -- Matching criteria
    urgency                 TEXT NOT NULL DEFAULT 'routine'
                            CHECK (urgency IN ('wellness', 'routine', 'urgent')),
    time_preferences        TEXT[] NOT NULL DEFAULT '{}',  -- ['weekday_morning', 'weekday_afternoon', etc.]
    min_notice_hours        INTEGER NOT NULL DEFAULT 3,
    preferred_resource_id   UUID REFERENCES resources(id),  -- NULL = any vet
    
    -- Computed
    flexibility_score       FLOAT NOT NULL DEFAULT 0.5,  -- Higher = easier to fill; re-computed on join
    
    -- Lifecycle
    active                  BOOLEAN NOT NULL DEFAULT TRUE,
    pass_count              INTEGER NOT NULL DEFAULT 0,     -- # of times owner passed on a slot
    notified_count          INTEGER NOT NULL DEFAULT 0,
    joined_at               TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    last_notified_at        TIMESTAMP WITH TIME ZONE,
    removed_at              TIMESTAMP WITH TIME ZONE,
    remove_reason           TEXT CHECK (remove_reason IN ('accepted', 'passed_3x', 'manual', 'expired')),
    
    phone_for_sms           TEXT NOT NULL,
    sms_consent             BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX idx_waitlist_active ON waitlist(clinic_id, appointment_type_id, active) 
    WHERE active = TRUE;
CREATE INDEX idx_waitlist_urgency ON waitlist(urgency, joined_at) WHERE active = TRUE;
```

#### `waitlist_claim_tokens`

```sql
CREATE TABLE waitlist_claim_tokens (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    waitlist_id     UUID NOT NULL REFERENCES waitlist(id),
    slot_id         TEXT NOT NULL,          -- Identifies the offered slot
    start_datetime  TIMESTAMP WITH TIME ZONE NOT NULL,
    resource_id     UUID NOT NULL REFERENCES resources(id),
    
    status          TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending', 'claimed', 'passed', 'expired')),
    expires_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (NOW() + INTERVAL '30 minutes'),
    
    -- Resulting booking (if claimed)
    booking_token_id UUID REFERENCES booking_tokens(id),
    
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    resolved_at     TIMESTAMP WITH TIME ZONE
);
```

---

### 11.2 Additions to Existing Tables

#### `owners` table — add columns

```sql
ALTER TABLE owners ADD COLUMN IF NOT EXISTS preferred_resource_id UUID REFERENCES resources(id);
ALTER TABLE owners ADD COLUMN IF NOT EXISTS sms_consent BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE owners ADD COLUMN IF NOT EXISTS portal_opt_in BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE owners ADD COLUMN IF NOT EXISTS last_portal_login TIMESTAMP WITH TIME ZONE;
ALTER TABLE owners ADD COLUMN IF NOT EXISTS no_show_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE owners ADD COLUMN IF NOT EXISTS booking_count INTEGER NOT NULL DEFAULT 0;
```

#### `timeblocks` table — add columns

```sql
ALTER TABLE timeblocks ADD COLUMN IF NOT EXISTS source TEXT NOT NULL DEFAULT 'staff_dashboard'
    CHECK (source IN ('staff_dashboard', 'online_portal', 'waitlist_claim', 'phone', 'api'));
ALTER TABLE timeblocks ADD COLUMN IF NOT EXISTS urgency TEXT DEFAULT 'routine'
    CHECK (urgency IN ('wellness', 'routine', 'urgent', 'emergency'));
ALTER TABLE timeblocks ADD COLUMN IF NOT EXISTS client_notes TEXT;
ALTER TABLE timeblocks ADD COLUMN IF NOT EXISTS intake_token_id UUID REFERENCES intake_tokens(id);
ALTER TABLE timeblocks ADD COLUMN IF NOT EXISTS risk_score FLOAT;
```

---

### 11.3 Entity Relationship Summary

```
owners
  └─── patients (many-to-one, one owner has many patients)
  └─── owner_sessions (ephemeral)
  └─── waitlist (one owner can be on many waitlists)

clinics
  └─── clinic_booking_config (one-to-one)
  └─── resources (vets, rooms)
  └─── timeblocks (appointments)

timeblocks
  └─── booking_tokens (one-to-one)
       └─── intake_tokens (one-to-one)

waitlist
  └─── waitlist_claim_tokens (one-to-many)
       └─── booking_tokens (one-to-one, if claimed)

slot_holds (ephemeral; links owner_sessions → proposed slot)
```

---

## 12. Frontend Architecture

### 12.1 Technology Recommendation: Embeddable SPA (React + Vite)

**Recommendation:** Build the booking portal as a **React single-page application** compiled with Vite, deployable in two modes:

| Mode | Use Case | How |
|---|---|---|
| **Standalone hosted** | Practice links to a VPMA-hosted URL | `https://book.vpma.app/{clinic_slug}` — full-page experience |
| **Embeddable widget** | Practice embeds in their own website | `<script src="https://cdn.vpma.app/widget.js" data-clinic="meadow-pet-clinic"></script>` — renders into a `<div>` |
| **Custom domain (Phase 3)** | Practice wants full white-label | CNAME `book.meadowpetclinic.com → vpma.app`; TLS via Let's Encrypt |

**Rationale for React over plain HTML/JS:**
- Multi-step wizard flow with complex state (session, slot holds, real-time SSE) is unmanageable in vanilla JS at production quality
- React context manages: owner identity, selected pet, selected slot, booking lifecycle
- Rich animations (slot card selection, progress bar, lifecycle updates) require component lifecycle control
- Widget embedding: the `<script>` tag bundles a shadow-DOM React app — no CSS bleed-through into host site
- Vite bundles into a single optimized JS file: fast initial load
- React without a framework (no Next.js) — no server-side rendering needed; all data is fetched from public APIs

**Bundle Target:**
- Total JS: < 100KB gzipped (achievable with React 18 + limited dependencies)
- No external UI component library — custom components to avoid bloat
- Google Fonts: Inter loaded via `<link rel="preconnect">`

---

### 12.2 URL Structure

```
/                         → Clinic portal home (Step 0)
/identify                 → Owner identification (Step 1)
/select-pet               → Pet selection (Step 2)
/appointment-type         → Appointment type + urgency (Step 3)
/select-slot              → AI slot selection (Step 4)
/confirm                  → Review + confirm (Step 5)
/status/{booking_token}   → Live status tracker
/intake/{intake_token}    → Pre-visit intake form
/waitlist                 → Waitlist join
/waitlist/claim/{token}   → Waitlist claim (SMS link target)
/new-client               → New client onboarding (skips identify step)
```

All routes are rendered client-side (React Router v6). The server serves `index.html` for all paths under the clinic slug.

---

### 12.3 Component Breakdown

#### `<ClinicHeader>`
- **Props:** `clinicName`, `logoUrl`, `brandColor`, `phone`
- **Renders:** Logo, clinic name, phone number (tappable on mobile), emergency banner (if configured)
- **States:** normal, emergency (orange top bar)
- **Accessibility:** `<header role="banner">`, logo has `alt` text, phone has `aria-label="Call clinic"`

#### `<ProgressBar>`
- **Props:** `currentStep: number`, `totalSteps: number`, `stepLabels: string[]`
- **Renders:** Horizontal segmented bar; current step highlighted; past steps filled; future steps empty
- **Behavior:** Animated fill transition on step advance
- **Mobile:** On small screens, shows "Step 2 of 4" text only (bar collapses)

#### `<OwnerIdentifyForm>`
- **Props:** `onFound(owner)`, `onNotFound()`
- **Fields:** Phone (E.164 formatted), Email (optional)
- **States:** idle, loading (POST in flight), found, not-found, error, rate-limited
- **Validation:** Inline, real-time; phone format validated client-side before submission

#### `<PetCard>` / `<PetGrid>`
- **Props:** `pets: Pet[]`, `onSelect(petId)`, `onAddPet()`
- **Renders:** Card grid (2 cols on mobile, 3 on tablet+); each card: species icon, name, breed+age, last visit, care-due badge
- **States:** default, hovered (scale + shadow), selected (border highlight), adding-new (inline form modal)

#### `<AppointmentTypePicker>`
- **Props:** `types: AppointmentType[]`, `onSelect(typeId, urgency, notes)`
- **Renders:** Card buttons for appointment types; urgency chip selector; notes textarea; emergency modal if urgency=emergency
- **Accessibility:** All cards are `<button>` elements; urgency uses `role="radiogroup"`

#### `<SlotCard>`
- **Props:** `slot: Slot`, `rank: number`, `onBook(slotId)`
- **Renders:** Rank badge, date/time, vet name, duration, explanation text, "Book This Slot" CTA
- **States:** default, loading (POST in flight), selected (booked), expired (soft-hold expired), taken (race condition)
- **Animation:** Scale-in on mount; slide-out + next-slot highlight on "taken" edge case

#### `<SlotGrid>` (calendar fallback)
- **Props:** `availability: Record<string, Slot[]>`, `onSelect(slotId)`
- **Renders:** Month calendar; days with slots shown with dot indicators; click day → time list
- **Accessibility:** `<table>` structure with proper `scope`, `aria-label`, keyboard navigation

#### `<ConfirmationSummary>`
- **Props:** `booking: DraftBooking`, `owner: Owner`, `onConfirm()`, `onEditStep(step)`
- **Renders:** Summary card; editable sections; policy checkbox; CTA
- **States:** idle, submitting (spinner on CTA), error (banner)

#### `<StatusTracker>`
- **Props:** `token: string`
- **Behavior:** Fetches `GET /public/bookings/{token}` on mount; subscribes to SSE stream; re-renders on state change
- **Renders:** Clinic header; appointment summary; lifecycle timeline; action buttons; intake CTA if pending
- **SSE Fallback:** Polls every 30 seconds if SSE unavailable

#### `<IntakeForm>`
- **Props:** `token: string`
- **Behavior:** Fetches questions; renders one-per-screen; saves answer on each advance; submits all on final screen
- **States per question:** unanswered, answered, skipped, saving, error
- **Accessibility:** `role="form"`, each question `aria-labelledby` its heading; answer options use `role="radio"` or `role="checkbox"`

#### `<WaitlistForm>`
- **Props:** `clinicId`, `preFilledContext?`
- **Renders:** Pet selector; appointment type; urgency; time preferences (checkboxes); notice preference; phone; submit
- **Confirmation:** Inline after submit; shows queue position

---

### 12.4 Mobile-First Design Requirements

- **Minimum touch target:** 44×44px for all interactive elements (WCAG 2.1 AA)
- **Font sizes:** Minimum 16px body text (prevents iOS auto-zoom on input focus)
- **Viewport meta:** `<meta name="viewport" content="width=device-width, initial-scale=1">`
- **Safe area insets:** `padding-bottom: env(safe-area-inset-bottom)` for iPhone notch/home indicator
- **Sticky CTA:** Primary CTA button is sticky-bottom on mobile for all wizard steps
- **Keyboard avoidance:** Forms scroll above keyboard when focused (handled by OS on native; ensure no fixed elements block view on Android Chrome)
- **Swipe gestures:** Step navigation supports swipe-left (back) on mobile via touch events — optional enhancement, keyboard also works
- **Offline-aware:** If network drops mid-flow, surface a banner: "You're offline — your progress is saved locally. We'll continue when you reconnect." (localStorage draft state)

---

### 12.5 Accessibility Requirements (WCAG 2.1 AA)

| Requirement | Implementation |
|---|---|
| Colour contrast ≥ 4.5:1 (text) | All text/background combos tested with clinic brand colors; fallback to black text if brand color fails contrast |
| Keyboard navigable | All interactions operable with Tab, Enter, Space, Arrow keys; no mouse-only interactions |
| Focus visible | `:focus-visible` outline on all focusable elements; not suppressed |
| Skip navigation | `<a href="#main-content" class="skip-link">Skip to main content</a>` as first focusable element |
| Form labels | All inputs have associated `<label>` elements; no placeholder-as-label |
| Error messages | `aria-describedby` linking inputs to error messages; `aria-invalid="true"` on invalid fields |
| Loading states | `aria-live="polite"` region for status updates; `aria-busy="true"` on loading containers |
| Images | Species icons have `aria-label`; decorative images have `alt=""` |
| Color not sole indicator | Urgency levels distinguished by color AND label text AND icon |
| Language | `lang="en"` on `<html>` |

---

## 13. Security & Privacy

### 13.1 Data Visibility Model

| Data Type | Public (no auth) | Token-Gated (booking token) | Session-Gated (owner session) | Staff Only |
|---|---|---|---|---|
| Clinic name, address, hours | ✅ | ✅ | ✅ | ✅ |
| Available slot times | ✅ (no vet names in free tier — only "Available slot at 10am") | ✅ | ✅ | ✅ |
| Vet names with slots | Config-dependent | ✅ | ✅ | ✅ |
| Owner name (display only) | ❌ | ✅ (own record) | ✅ | ✅ |
| Pet name, species, breed | ❌ | ✅ (own record) | ✅ | ✅ |
| Pet medical history, diagnoses | ❌ | ❌ | ❌ | ✅ |
| Intake form responses | ❌ | ✅ (own record, intake token) | ✅ | ✅ |
| Booking details | ❌ | ✅ (own booking token) | ✅ (own bookings) | ✅ |
| Other patients' records | ❌ | ❌ | ❌ | ✅ |
| Vet schedules (full) | ❌ | ❌ | ❌ | ✅ |
| Risk scores | ❌ | ❌ | ❌ | ✅ |

**Key Principle:** Patient medical records are **never** accessible from the public API — not even via booking token. The booking token confirms/cancels/tracks a specific appointment only.

---

### 13.2 Token Design

#### Booking Token
- **Type:** UUID v4 (128 bits of entropy, cryptographically random via `uuid.uuid4()`)
- **Storage:** `booking_tokens.id` (primary key)
- **Expiry:** 30 days after appointment date
- **Rotation:** No rotation required — token is one-use-readable (no write capability after booking confirmation except cancel/reschedule which require explicit action)
- **Revocation:** `status = 'cancelled'` or `status = 'expired'` disables all token actions

#### Intake Token
- **Type:** UUID v4
- **Expiry:** 7 days from appointment date (hard limit)
- **Rotation:** If owner requests resend (e.g., lost SMS), existing token remains valid; a new delivery is sent (no new token generated, preventing token proliferation)
- **One-time submit:** After `status = 'complete'`, only GET is allowed; POST returns 409 Conflict

#### Waitlist Claim Token
- **Type:** UUID v4
- **Expiry:** 30 minutes (hard TTL — strict for slot integrity)
- **One-time use:** Status flips to `claimed` or `passed` on first action; subsequent requests return 409

#### Owner Session
- **Type:** UUID v4
- **Transmission:** HttpOnly, Secure, SameSite=Strict cookie
- **Expiry:** 30 minutes from last activity (sliding window)
- **Storage server-side:** `owner_sessions` table — session is validated against DB, not self-contained (enables instant server-side revocation)
- **No JWTs for owner sessions:** JWTs are self-verifying and cannot be instantly revoked; DB-backed sessions are required for healthcare data access control

---

### 13.3 Rate Limiting

All rate limits enforced at the FastAPI middleware layer using Redis for distributed counting.

| Endpoint | Limit | Window | Response on Exceed |
|---|---|---|---|
| `POST /public/owners/lookup` | 10 req | 5 min per IP | 429; include `Retry-After` header |
| `POST /public/owners/register` | 5 req | 5 min per IP | 429 |
| `POST /public/bookings` | 5 req | 1 hour per session | 429 |
| `GET /public/clinics/{slug}/availability` | 30 req | 1 min per IP | 429 |
| `POST /public/intake/{token}/submit` | 3 req | 1 hour per token | 409 |
| `POST /public/waitlist/join` | 3 req | 10 min per IP | 429 |
| `POST /public/bookings/{token}/cancel` | 3 req | 1 hour per token | 429 |

**Bot Detection:**
- All public API responses include `X-Request-ID` header (correlatable via Verbose Log)
- Honey-pot field in booking form (`<input name="hp_company" style="display:none">` — bots fill it; humans don't; if filled, reject silently with 200 but log the attempt)
- Availability endpoint: slot times are returned in ±5 minute fuzzy format to discourage scraping for schedule inference (`"10:30"` shown as `"10:30"` but if requested 50+ times in a minute, times drift by ±5 min randomly)

---

### 13.4 HIPAA Considerations

VPMA is a Business Associate (BA) under HIPAA for any vet practice that qualifies as a Covered Entity. Key technical safeguards for the booking portal:

| Safeguard | Implementation |
|---|---|
| Encryption in transit | TLS 1.3 on all endpoints; HSTS enforced with 1-year max-age |
| Encryption at rest | Postgres column-level encryption (pgcrypto) for `intake_tokens.responses` and any field containing symptoms/medications |
| Minimum Necessary | Public API returns only the data needed for the specific step; no bulk patient exports |
| Audit Controls | Every public API request is logged to the Verbose Log: IP, user agent, endpoint, timestamp, session ID, result |
| Integrity Controls | Booking tokens are validated against DB on every request — no token forgery possible |
| PHI in SMS | SMS messages contain NO PHI — only the owner's first name + pet's name + a link. The link (HTTPS) is where PHI is served. SMS content itself is not PHI-bearing. |
| PHI in Email | Email confirmation bodies are PHI-light (appointment date, vet name only). Full intake data is served only via the authenticated portal link. |
| Right of Access | Owner can view their own intake responses via booking token — this supports HIPAA access rights for patients |
| Breach Notification | Verbose Log + alerting pipeline triggers on anomalous access patterns (>100 failed token lookups in 1 hour from one IP) |

---

### 13.5 Schedule Scraper Prevention

Competitors scraping VPMA vet schedules is a real concern (especially for Provet or ezyVet competitive intel gathering).

Defenses:
1. **Authentication for vet names:** If `clinic_booking_config.show_vet_names = false`, availability endpoint returns `"Dr. [Last Initial]."` only, preventing direct vet identification
2. **Slot obfuscation:** Availability API does not return ALL slots — returns only the top-ranked 3 (publicly) + 9 more "show more" (session-gated). Full slot grid requires session.
3. **Rate limiting** as above — 30 req/min makes automated scraping slow and detectable
4. **No predictable patterns:** `slot_id` is UUID v4; slot times are not monotonically sequential in the API response
5. **Honeypot analytics:** If same IP requests availability for 5+ different appointment types in <10 minutes, flag and throttle

---

## 14. Practice Configuration — Staff-Side Admin

This section describes additions to the existing VPMA staff dashboard for controlling the booking portal.

### 14.1 Booking Portal Settings Page

**Navigation:** Dashboard → Settings → Online Booking Portal

**URL:** `/dashboard/{clinic_id}/settings/booking-portal`

**Sections:**

#### General Settings
- **Enable Online Booking** — Toggle [id: `toggle-online-booking`]
  - When disabled: portal shows "Online booking is currently disabled" message
- **Auto-Confirm Bookings** — Toggle [id: `toggle-auto-confirm`]
  - Off: every booking goes to `pending` status; staff sees queue; owner sees "We'll confirm your appointment within X hours"; X is configurable
  - On: bookings are instantly confirmed (recommended for most practices)
- **Booking Confirmation Message** — Textarea (shown on confirmation page and in email)

#### Scheduling Rules
- **Advance Booking Window** — Slider/number: 7 to 90 days [id: `input-advance-days`]
- **Same-Day Booking** — Toggle + cutoff time picker [id: `toggle-same-day`, `input-same-day-cutoff`]
  - Cutoff time: "Clients can book same-day until [HH:MM]"
- **Minimum Notice** — "Clients can't book less than [X] hours/minutes from now" — dropdown [id: `select-min-notice`]
- **Buffer Time Between Appointments** — Number input (minutes) [id: `input-buffer-time`]

#### Appointment Types
- Table of all appointment types in the system
- Per type: Name | Duration (editable) | Bookable Online (toggle) | Intake Question Set (select)
- "Edit duration by breed" expander: e.g., "Persian cats get +15 min for wellness"
- "Custom message for this appointment type" — textarea shown to client when they select it

#### Vets & Staff Visibility
- Table: Vet name | Shown to Clients | Order (drag-to-reorder)
- For each vet: "Visible" / "Hidden" / "Request Only" (shown to clients but booked as "preference, subject to availability" — useful for new vet building clientele)
- Note: Hidden vets' slots are still used for availability calculation but attributed as "Dr. [Staff]" or removed from ranking

#### Waitlist
- **Enable Waitlist** — Toggle [id: `toggle-waitlist`]
- **Max Waitlist Days** — How long a waitlist entry stays active (default: 30 days)
- **Claim Window Duration** — How long clients have to claim a notified slot (default: 30 min)
- **Max Consecutive Passes** — Before auto-removing from waitlist (default: 3)

#### Communication (MOD-COM upsell hook)
- **SMS for Booking Confirmations** — Toggle (disabled if MOD-COM not active; shows "Upgrade to enable SMS" with upgrade link)
- **Custom SMS Templates** — Text area with variable hints: `{pet_name}`, `{vet_name}`, `{date}`, `{time}`, `{intake_link}`
- **Intake Form Reminder** — Toggle: "Send a reminder if intake isn't complete 24h before appointment"

#### Deposits (MOD-FIN upsell hook)
- **Require Deposit** — Toggle (disabled if MOD-FIN not active; shows "Upgrade to collect deposits")
- **Deposit Amount** — Dollar amount field (shown only if MOD-FIN active)
- **Deposit Policy** — Textarea: what happens if client cancels

#### Danger Zone
- **Reset Booking Config to Defaults** — Button with confirmation modal
- **Disable Online Booking** — Duplicated from top for discoverability

---

## 15. Integration Points with Existing Systems

### 15.1 Verbose Log (Agent Audit)

Every action in the online booking portal creates a Verbose Log entry. Log format is consistent with existing agent logs:

```python
verbose_log.append({
    "timestamp": datetime.utcnow().isoformat(),
    "source": "online_booking_portal",
    "clinic_id": clinic_id,
    "owner_id": owner_id,           # May be null for anonymous
    "patient_id": patient_id,       # May be null before patient selected
    "booking_token_id": token_id,   # May be null before booking confirmed
    "action": "booking_confirmed",  # or: "lookup_attempted", "slot_held", "intake_submitted", etc.
    "metadata": {
        "appointment_type": "wellness",
        "vet_id": resource_id,
        "slot_datetime": start_datetime,
        "ip_address": request.client.host,  # For audit; not shown in UI
        "user_agent": request.headers.get("user-agent"),
    },
    "result": "success"             # or: "not_found", "rate_limited", "slot_taken", etc.
})
```

This means every booking, cancellation, intake submission, and waitlist join is fully auditable in the existing agent dashboard.

---

### 15.2 Risk Agent Integration

`risk.py` is called at two points in the online booking flow:

**Point 1: Slot Selection (pre-booking)**
- Called with: `owner_id`, `patient_id`, `appointment_type_id`, `urgency`, `slot_datetime`
- Returns: `{no_show_probability: float, clinical_risk: str, flags: []}`
- Used to: rank slots (penalize high no-show-risk slots in AI ranking)
- Does NOT block the booking

**Point 2: Intake Submission (post-intake)**
- Called with: full intake Q&A + existing patient record
- Returns: updated `{clinical_risk: str, flags: [], suggested_actions: []}`
- Used to: surface pre-visit flags on staff dashboard; potentially escalate urgency
- Result stored in `timeblocks.risk_score` and `intake_tokens.flags`

**New no-show risk model input (for online bookings):**
Add `source = 'online_portal'` as a feature. Historical analysis should determine if online-booked appointments have different no-show characteristics than phone-booked (hypothesis: lower no-show due to self-motivated booking, but validate with data).

---

### 15.3 Reminder Pipeline Auto-Arm

When `POST /public/bookings` succeeds, the reminder pipeline is armed automatically:

```python
# In booking confirmation handler (async)
await reminders_service.arm_appointment(
    clinic_id=clinic_id,
    timeblock_id=timeblock_id,
    booking_token=booking_token,
    owner_phone=owner.phone,
    owner_email=owner.email,
    sms_consent=booking.sms_consent,
    appointment_datetime=slot.start_datetime
)
```

This triggers `POST /api/reminders/sweep` to register:
- **T-48h reminder:** "Your appointment for [Pet] at [Clinic] is in 2 days. Confirm or reschedule: [status_url]"
- **T-2h reminder:** "Your appointment is today at [time]. Tap to add to maps: [directions_url]"

The T-48h reminder for online bookings includes an intake nudge if `intake_token.status != 'complete'`:
> "Complete [Pet]'s pre-visit health check to help Dr. [Name] prepare: [intake_url]"

---

### 15.4 Staff Scheduling Board

Online-booked appointments appear on the staff scheduling board identically to phone-booked appointments, with the following additions:

**Visual indicators on appointment block:**
- 🌐 Globe icon: "Booked online" (from `timeblocks.source = 'online_portal'`)
- 📋 Clipboard icon: Intake status badge (green/amber/red) — links to intake drawer
- ⚠️ Flag icon: If any `intake_tokens.flags` are set

**Appointment detail drawer (right panel):**
- "Booking Source: Online Portal" label
- "Client Notes (from booking):" — shows `timeblocks.client_notes`
- "Pre-Visit Intake:" section (as described in Section 6.4)
- "Risk Score:" field (from `timeblocks.risk_score`)

**No other changes needed** — the scheduling board already renders from `timeblocks`; online bookings populate the same table.

---

### 15.5 Migration: Importing Existing Client Data for Returning Client Lookup

For existing clinics migrating to VPMA with an existing client database:

**Step 1: Phone number normalization**
```sql
-- Normalize existing phone numbers to E.164 format
UPDATE owners SET phone = regexp_replace(phone, '[^0-9]', '', 'g');
-- Then prefix with country code where missing (assume US)
UPDATE owners SET phone = '1' || phone WHERE length(phone) = 10;
```

**Step 2: Email deduplication**
```sql
-- Flag duplicate emails (same email linked to multiple owner records — merge candidates)
SELECT email, count(*) as dupe_count
FROM owners
WHERE email IS NOT NULL
GROUP BY email
HAVING count(*) > 1;
```

**Step 3: Phone + email validation**
- Run a validation pass; mark invalid/missing contacts with `portal_opt_in = false` (they won't appear as "found" in lookup until fixed)
- Provide staff a dashboard report: "X clients have invalid contact info — update to enable online booking lookup"

**Step 4: Portal opt-in toggle**
- Initially set `portal_opt_in = false` for all existing clients (conservative)
- Staff can bulk-enable via "Enable Online Portal for all clients" in settings
- Or opt-in is set to `true` automatically on first online booking or manual staff edit

---

## 16. MOD Upsell Hooks

The booking portal is designed to naturally surface the value of additional VPMA modules without being pushy. Each upsell hook appears at a moment of genuine user need.

### 16.1 MOD-COM — SMS Gateway (Twilio)

**Where it surfaces:**
- **Booking Confirmation:** If MOD-COM is not active, confirmation shows "Email confirmation sent" and a dim "📱 Enable SMS confirmations" banner with a single upgrade link — not a modal, not blocking
- **Staff Settings → Communication:** SMS template fields are visible but locked with "Upgrade to enable" button
- **Intake form delivery:** If no MOD-COM, intake is email-only. Owner sees on status page: "Intake form sent to [email]. Enable SMS for faster response rates." — [Learn more] link
- **T-48h / T-2h reminders:** Work via email without MOD-COM; SMS upgrade unlocks higher engagement rates

**Activation:** When clinic enables MOD-COM, Twilio credentials are configured in the staff dashboard. The `reminders.py`, `intake.py`, and `waitlist.py` agents automatically detect MOD-COM status via `require_module('MOD-COM')` gate and switch delivery channels.

---

### 16.2 MOD-FIN — Deposits & Prepayment

**Where it surfaces:**
- **Booking Confirmation Step (Step 5):** If MOD-FIN not active AND `clinic_booking_config.require_deposit` is configured, a gray "💳 Add deposit at booking" card appears with "Available with Payments module — [Learn more]"
- **Staff Settings → Deposits:** Deposit fields visible but locked
- **Cancellation scenario:** If a client cancels within the no-fee window, a banner appears to staff: "Enable deposits to protect against last-minute cancellations → [Enable MOD-FIN]"

**When active:** A Stripe payment step is inserted between Step 4 (slot selection) and Step 5 (confirm). The deposit amount is captured and held; released or charged based on cancellation policy.

---

### 16.3 MOD-TEL — Telemedicine Video Consult

**Where it surfaces:**
- **Step 3 (Appointment Type):** If MOD-TEL is active, a "📹 Video Consult" appointment type appears in the list. If not active, it appears grayed out: "Video Consults coming soon — [Learn more]"
- **Step 4 (Slot Selection):** Video consult slots show a 📹 icon; no room/resource required (vet's video availability only)
- **Confirmation:** Video bookings show a "Join Video Call" button on the status page (disabled until T-5min before appointment time)

**Design:** Video consult booking is identical to in-person in terms of flow. The difference: slot availability comes from `resources` where `resource_type = 'vet'` and `supports_telemedicine = true`; confirmation generates a video call link via MOD-TEL provider.

---

### 16.4 Non-Intrusiveness Principle

All upsell hooks follow these rules:
1. **Never block the booking flow** — a missing module is gracefully degraded, not a wall
2. **One surface per module per session** — if the owner already saw the MOD-COM upsell on confirmation, don't show it again on the status page
3. **Staff-side framing, not client-side** — clients never see "upgrade" messages; only staff do
4. **Value-first messaging** — "Enable SMS to reach clients in <2 min (vs. 24h email open rates)" not "Buy SMS now"

---

## 17. Phased Build Plan

### Phase 1 — MVP: Core Booking Loop

**Goal:** First online booking goes live. Returning and new clients can book. Intake fires. No AI features yet.

**What's Built:**
- ✅ All new database tables (Section 11)
- ✅ All public API routes (Section 10), except `/availability` AI ranking (returns flat chronological list)
- ✅ React SPA — all wizard steps (Steps 0-5) + confirmation page
- ✅ Status tracker page (static — SSE not yet implemented; page polls every 60 seconds)
- ✅ Intake form delivery (email only; SMS blocked pending MOD-COM)
- ✅ Intake form UI at `/intake/{token}`
- ✅ `clinic_booking_config` admin settings page (staff dashboard)
- ✅ Returning client lookup + session management
- ✅ New client registration
- ✅ Soft-hold (slot reservation) mechanism
- ✅ Reminder pipeline auto-arm on booking
- ✅ Online bookings appear on staff scheduling board with 🌐 badge
- ✅ Verbose Log entries for all portal actions
- ✅ Rate limiting middleware

**APIs Needed (new):**
- All `POST/GET /public/*` routes listed in Section 10
- Internal: `POST /internal/bookings` (for the public API layer to call the existing schedule system with an internal API key)
- Internal: `POST /internal/owners` (same pattern)

**Effort:** **XL** (full-stack; frontend SPA + 12 new API routes + DB migrations + admin UI)  
**Estimate:** 6–8 weeks (2 backend engineers + 1 frontend engineer)

---

### Phase 2 — AI Slot Suggestions + Waitlist + Real-Time Status

**Goal:** VPMA's portal is now demonstrably smarter than any competitor.

**What's Built:**
- ✅ AI slot ranking algorithm (`score_slot` function, `rank_explanation` generation)
- ✅ `SlotCard` component with rank badges and plain-language explanations
- ✅ Waitlist join flow (portal + SMS confirmation)
- ✅ `waitlist.py` backfill trigger on cancellation
- ✅ Waitlist claim token + SMS claim flow
- ✅ SSE real-time status updates on status tracker page
- ✅ Risk agent integration at slot selection + intake submission
- ✅ Intake flags surfaced in staff dashboard (pre-visit flags UI)
- ✅ Staff alert on high-risk intake submission
- ✅ Emergency urgency flow (triage modal, same-day slot priority)
- ✅ Calendar fallback view (SlotGrid component)
- ✅ "Care overdue" badges using `care/protocols` + `breed_intelligence.py`

**APIs Needed:**
- `GET /public/bookings/{token}/stream` (SSE)
- `POST /public/waitlist/join`
- `GET /public/waitlist/{token}/claim`
- Enhancement to `/availability` endpoint: add `rank_score`, `rank_explanation`, `no_show_risk_label`

**Effort:** **L** (backend: AI ranking + waitlist backfill logic; frontend: SlotCard + SSE + waitlist flow)  
**Estimate:** 3–4 weeks (1 backend + 1 frontend)

---

### Phase 3 — Embeddable Widget + Custom Branding + Mobile PWA

**Goal:** Practice can embed the booking portal directly on their own website. Enterprise-grade white-labeling.

**What's Built:**
- ✅ Embeddable widget script (`widget.js`) — bundles React app into shadow DOM; accepts `data-clinic` attribute
- ✅ Widget configurability: `data-appointment-type="wellness"` (pre-selects type), `data-embed-mode="inline|modal"` (modal = "Book Now" button opens overlay)
- ✅ Custom domain support: CNAME configuration in staff settings; Let's Encrypt TLS provisioning via ACME
- ✅ Branded CSS variables from `clinic_booking_config.brand_color_*` applied to all components
- ✅ Custom clinic logo on portal (currently uses VPMA placeholder)
- ✅ Progressive Web App manifest: `manifest.json` + service worker for offline status tracking
- ✅ "Add to Home Screen" prompt on iOS/Android (owner bookmarks their clinic's portal)
- ✅ Appointment history page (lightweight owner portal: phone OTP → see all past + upcoming bookings)
- ✅ MOD-COM: SMS fully integrated (confirmations, reminders, waitlist, intake)
- ✅ MOD-FIN: Deposit collection at booking (Stripe payment step)
- ✅ MOD-TEL: Video consult appointment type

**APIs Needed:**
- `GET /public/owners/{owner_id}/appointments` (session-gated — owner history view)
- `POST /public/owners/verify-otp` (for appointment history login)
- `POST /public/owners/send-otp`

**Effort:** **M** (widget bundling: M; custom domain: M; PWA: S; owner history portal: M)  
**Estimate:** 3–4 weeks (1 frontend + devops for custom domain ACME)

---

### Phase Summary Table

| Phase | What | Effort | Weeks | Key Deliverable |
|---|---|---|---|---|
| 1 — MVP | Core booking loop, intake, config | XL | 6-8 | Online bookings work end-to-end |
| 2 — AI | Slot ranking, waitlist, real-time | L | 3-4 | Industry's smartest booking UI |
| 3 — Scale | Widget, branding, PWA | L | 3-4 | Embeddable anywhere; mobile app feel |

---

## 18. Success Metrics

### 18.1 Primary KPIs

| Metric | Definition | Target (3 months post-launch) | How to Measure |
|---|---|---|---|
| **Online Booking Adoption Rate** | % of all appointments booked via online portal vs. phone/walk-in | 25% of all bookings online | `timeblocks.source = 'online_portal'` count / total |
| **Booking Completion Rate** | % of sessions that reach Step 0 and complete a booking | > 60% completion | Funnel: `owner_sessions` created → `booking_tokens` created |
| **Intake Completion Rate** | % of online bookings where intake form is fully submitted | > 70% within 48h | `intake_tokens.status = 'complete'` / `booking_tokens.status != 'cancelled'` |
| **No-Show Rate Delta** | No-show rate for online-booked vs. phone-booked | Online no-show ≤ phone no-show | `timeblocks.status = 'no_show'` segmented by source |
| **Waitlist Conversion Rate** | % of waitlist joins that result in a booked appointment | > 50% | `waitlist_claim_tokens.status = 'claimed'` / `waitlist.id` count |
| **Time-to-Fill Cancelled Slots** | Avg minutes from cancellation to a replacement booking via waitlist | < 45 minutes | `waitlist_claim_tokens.resolved_at - booking_tokens.cancelled_at` |

---

### 18.2 Secondary KPIs

| Metric | Target | Notes |
|---|---|---|
| Booking funnel drop-off by step | < 20% per step | Step-level analytics in Verbose Log |
| Avg booking completion time (click to confirm) | < 4 minutes | Session timestamps |
| Intake form avg completion time | < 3 minutes | `intake_tokens.completed_at - intake_tokens.sent_at` |
| Phone call volume reduction | −20% after 3 months | Anecdotal (staff-reported) + booking source shift |
| Slot suggestion acceptance rate | > 50% take the #1 ranked slot | `slot_cards_rank_1_booked / total_bookings` |
| Waitlist opt-in rate (when no slots) | > 75% | `waitlist.id` created / `availability = 0` sessions |
| Returning client pre-fill usage | > 80% of known clients identified | `owner_sessions.owner_id != null` / total sessions |

---

### 18.3 Operational Health Metrics

| Metric | Alert Threshold | Action |
|---|---|---|
| `POST /public/bookings` error rate | > 1% in 5 min | PagerDuty alert |
| Soft-hold expiry rate (slot race conditions) | > 5% of holds | Investigate slot contention; may need shorter hold TTL |
| Intake delivery failure rate (email bounce) | > 10% | Alert ops; update email validation |
| Slot ranking p95 latency | > 500ms | Profile `score_slot` and DB query; add caching |
| SSE connection success rate | > 95% | Fall back to polling if < 90% |
| Waitlist claim expiry rate (nobody claims) | > 40% | Review notify timing; adjust urgency matching |

---

### 18.4 Measurement Infrastructure

All metrics above are computable from existing tables — no separate analytics database needed in Phase 1. A simple SQL query layer (or SQLite → Postgres VIEW) can power a metrics dashboard in the staff admin area.

In Phase 2, add a lightweight `portal_events` table for funnel analysis:

```sql
CREATE TABLE portal_events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id      UUID REFERENCES owner_sessions(id),
    clinic_id       UUID NOT NULL REFERENCES clinics(id),
    event_type      TEXT NOT NULL,          -- 'step_viewed', 'step_completed', 'step_abandoned', etc.
    step            TEXT,                   -- 'identify', 'select_pet', 'appointment_type', etc.
    metadata        JSONB,
    occurred_at     TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_portal_events_clinic ON portal_events(clinic_id, occurred_at);
```

This enables: step-by-step funnel analysis, A/B testing future UI variations, and per-clinic conversion benchmarking.

---

*Document End — v1.0*

*Next revision triggers: Phase 1 engineering kickoff review, MOD-COM integration design, MOD-FIN Stripe integration spec.*
