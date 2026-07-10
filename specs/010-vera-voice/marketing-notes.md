# Marketing Notes: Vera Voice (after-hours) — [MARKETING] milestones as built

**Produced by**: speckit-implement — 2026-07-10 (wave 3, feature close)
**Source**: spec.md `## Marketing Output` + tasks.md `[MARKETING]` tasks (T016, T017, T023, T028, T029, T034)
**Scope note (per G1/G2)**: In cycles 3a/3b Vera answers the **after-hours line only** — evenings, overnight, weekends, and holidays outside the clinic's regular hours. Every claim below is scoped to after-hours calls. Daytime calls are never routed to Vera (enforced by the T042 after-hours gate, read from each clinic's configured hours). All six milestones are **built and tested in simulation**; going live is a configuration switch (credentials + a vet-signed triage protocol), not more building.

---

## The six customer-visible / announcement-blocking milestones

### 1. Every after-hours call is answered — and the caller always knows it's an AI (T016)
**What it does now:** The moment someone calls after hours, Vera picks up on the first ring and — before anything else happens — says who she is: an AI assistant, not a nurse or veterinarian; that the call is recorded and transcribed so the team can follow up; and that the caller can say "emergency" at any time to reach a person. This greeting plays on **100% of calls**, and consent is timestamped to that moment.
**Plain-language claim:** "Your after-hours calls never go to voicemail again — and every caller is told, up front, that they're talking to an AI and how to reach a real person."
**Guardrail for copy:** Say "AI assistant," never imply a human or a clinician. This is announcement-blocking — do not launch messaging that hides the AI disclosure.

### 2. A real emergency always reaches a person — every time (T017 + T029)
**What it does now:** If a caller says "emergency," or describes something the clinic's triage protocol flags as urgent (e.g. collapse, not breathing, poisoning), Vera hands off to a human. The hand-off has **independent authority**: it fires even if the AI stalls, disconnects, or gets it wrong. A warm transfer dials the on-call team in priority order and **whispers a summary to the person before** the caller is connected — the human is briefed first. Tested across every protocol keyword, at every point in a call, with the model deliberately stalled: **100% reached a human, zero silent drops.**
**Plain-language claim:** "When it's a real emergency, Vera gets a person on the line — every single time — and briefs them before they pick up."
**Guardrail for copy:** This is the existential safety promise. "Every time / 100%" is backed by the test suite; keep the claim exactly that strong and no stronger (it's the after-hours line reaching your on-call team, not an ER).

### 3. Callers book and reschedule against your real schedule (T023)
**What it does now:** A confirmed caller can book or reschedule an appointment. Vera **reads the appointment back** (day, time, provider, reason) before writing anything, then books it straight through the clinic's existing scheduling pipeline. Bookings are idempotent — a dropped connection or a call-back can't create a double-booking of the same slot for the same pet.
**Plain-language claim:** "Vera turns after-hours calls into booked appointments on your actual calendar — no double-bookings, no morning cleanup."
**Guardrail for copy:** "Books against your live schedule." Don't imply Vera diagnoses or decides care — she schedules.

### 4. Refill requests become vet-review drafts — never auto-approved (T028)
**What it does now:** When a caller asks for a medication refill, Vera captures it as a **draft for the vet to review** — even when refills remain on file. There is deliberately **no path** for Vera to approve a refill herself; the auto-approve route is unreachable from the voice channel, enforced below the model and at the database.
**Plain-language claim:** "Refill requests land in your vet's review queue as drafts — Vera never approves medication on her own."
**Guardrail for copy:** Announcement-blocking legal/clinical promise. Never suggest Vera "handles refills" in a way that implies approval; she *captures* them for review.

### 5. No dead air — ER directory and a call-back guarantee when no one picks up (T029 + T030)
**What it does now:** If the on-call team doesn't answer, Vera doesn't drop the caller. She reads out the emergency (ER) directory and promises a call-back, and as a last resort takes a voicemail with a call-back promise. The caller is **never left in silence**.
**Plain-language claim:** "Even when your on-call team can't pick up, no caller is ever left hanging — Vera points them to emergency care and guarantees a call-back."

### 6. A morning briefing of every overnight call (T034)
**What it does now:** Each morning the clinic gets a rollup of the night's calls: what happened on each (contained, booked, escalated, deflected), the cost of each call, and the follow-ups that need a human — call-backs owed, refill drafts awaiting the vet, and escalations. It's delivered over the clinic's existing messaging channel.
**Plain-language claim:** "Start each day with a clear picture of every after-hours call — what Vera handled, what it cost, and the short list that needs you."
**Guardrail for copy:** This is the owner-facing "recovered revenue / peace of mind" surface. Frame it around the benefit (nothing slips overnight), not the mechanics.

---

## Copy-alignment status
✅ **Aligned.** The one caller-facing script — the disclosure (T016) — matches the AI-first, "not a nurse or veterinarian," say-"emergency" promise in the Feature Brief. The staff-facing morning briefing uses plain outcome language ("contained without a person," "call-backs owed," "refill drafts awaiting your review"), not error-speak. No UI labels drifted from the spec's consumer-friendly framing.

⚠️ **Reviewer note for launch messaging:** All milestones are validated in **simulation** only. Before any public claim, they must pass `speckit-user-review`, and live operation additionally requires the deferred Pilot-Activation gates (live Twilio/model credentials, a **vet-signed** triage protocol, and counsel sign-off on the consent/no-training DPA clauses). Keep "100% / every time" claims scoped to the after-hours line reaching the clinic's on-call team.
