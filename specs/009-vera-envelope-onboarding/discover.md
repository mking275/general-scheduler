# Discovery: Vera Envelope Onboarding — "Vera's First Day"

**Feature type**: new-surface (the adoption path for envelope clinics — **and the migration itself**: the envelope period continuously populates the native VetAgent practice model, so cutover is a formality, not an event; customer-facing, revenue-critical)
**Appetite**: medium (~6w to Goldsmith-pilot-ready; the read-only half of the envelope MVP)
**Passes run**: 0, 1, 2, 3, 4, 5, 6 (via the 2026-07-07 Envelope Strategy research board + FarmAgent onboarding-WIP survey)
**Artifact confidence**: HIGH on mechanism reuse (FarmAgent 044 shipped analogs), MEDIUM on ezyVet-specific unknowns (data quality, shared logins)
**Date**: 2026-07-07

---

## Customer Artifacts

**Human-provided:**
- Dr. Goldsmith (23-clinic group, ezyVet): green-light for user testing; explicit strategy input — *he does not want to change software.* ezyVet is annoying but works; migrations are expensive disruption; what he lacks is a Chief of Staff. Vera must be additive, not a replacement.
- Envelope Strategy decision board (`StrategicStudy/envelope-strategy-board-2026-07-07.md`): five-lane analysis + synthesis; D1 (clinic as API contracting party), D2(c) (orchestrate the stack, PIMS as one actuator), D4 (derived memory ≠ cached User Data).

**Agent-sourced (persisted):**
- ezyVet Private Integration ToS verified first-hand (§3.2(e)/(f)/(h), §4.1, §7.4(a)); API surface: 216 endpoints, OAuth2, 60/min/endpoint + 180/min/database; all six Vera verbs readable via API.
- FarmAgent onboarding survey: specs 032 (onboarding agent), 044 (as-built, shipped), 048 (Vera Program steel thread), onboarding-corpus (source ladder, Unveiling arc, activation bridge).

## System Reality

### Files / components read
- `specs/008-vera-onboarding/` — six-phase conversational onboarding (native track): document magic w/ streaming narration + ✅/⚠️/❓ confirm, magic-link deferred signup, Replace event, role-based first actions, session persisted per phase. **Built (36/36 tasks).**
- FarmAgent 044 as-built: guest-start temp tenant → claim-account with stable tenant ID; onboarding as a job inside the agent surface; canvas computed from session state (cannot drift). **Shipped, live-verified.**
- FarmAgent 048 steel thread: job router → tool contracts → **autonomy gate (do/propose/advise)** → session log → memory substrate; 5-act Unveiling arc. Explicitly designed to generalize to a second vertical. **In progress.**
- `sms_gateway.py`: real dual-mode Twilio wrapper (not simulated) — briefing/comms delivery channel exists.
- Envelope board Appendix C: read verbs are the clean mode; write verbs are the gated/risky mode.

### External Dependencies
- **The data-access ladder (2026-07-09 revision — API no longer on the critical path):** ① bulk corpus via the clinic's **§5 written request** (One IDEXX Master Terms, ezyVet Offering Terms: copies of Customer Data on 10 business days' notice, drive or file transfer, no fee stated); ② deltas via ezyVet's own **Automated Reports** (scheduled email/Dropbox, self-serve); ③ the **human API** — Vera vision-guides staff through the vendor's own export/UI flows (screen share + agentic vision; no API, no bot, no ToS attachment; also covers PetDesk/QuickBooks/PMP portals — one capability for the whole long tail); ④ partner API as optional accelerator for real-time verbs only. Customer terms §6.3 (customer solely responsible for backups) makes the continuous clinic-owned vault contract-compliance; §5.2 expressly contemplates customer-authorized third-party access/write-back ("Unsanctioned Services" = unsupported, not prohibited).
- Gemini (extraction/insight/vision) — live PII subprocessor obligation (DPA needed); no retention of raw screen frames (client PII); Twilio (TCPA consent flows).

### Surprises
1. The envelope makes onboarding *easier* than native onboarding: **there is no data migration** — ezyVet already holds the practice. The source ladder inverts the work: inherit from ezyVet → documents for what it lacks → ask minimally → refine via usage.
2. FarmAgent has already paid the tuition: provision-rollback orphan-account bug (wrap the full transaction), FORCE-RLS-on-onboarding-tables (SEC-20), and a confirmation pathway that passed spec review while silently broken (mandate human click-through + e2e gate before pilot).
3. 048's steel thread *wants* this feature — VetAgent envelope onboarding is the second-vertical proof the Vera Program architecture was built for.

## JTBD
**Job statement**: *"When my practice group adopts Vera alongside ezyVet, I want her connected, knowledgeable, and visibly useful within one day — without moving data, retraining staff, or scheduling a cutover — so that by the time we decide to leave ezyVet, the migration has already happened: the data is in place, the staff already work with Vera, and switching is the day we stop paying for the old system."*
**Push**: every PIMS change he's seen cost months and morale; staff are at click-fatigue capacity; no bandwidth for training.
**Pull**: a Chief of Staff who arrives already knowing the practice (from its own ezyVet records) and earns each responsibility with visible receipts.
**Anxiety**: an AI acting on medical records; another tool to babysit; "what does my staff have to learn?"
**Habit**: ezyVet + 5–8 companion tools + human workarounds (shared logins, sticky notes, after-hours charting).
**Non-consumption alternative**: status quo; or wait for ezyVet's native AI (Vello, AI-Assisted Notes beta) — which will be scribe/engagement features, not an operating layer.
**Confidence**: MEDIUM-HIGH — grounded in Goldsmith's own words + the P5 caution that his sophistication may not represent the broader ICP (WTP test runs in parallel, per the board).

## Opportunity
**Product outcome**: time-to-first-value < 1 day (connect → first briefing); zero staff training hours; verb activation driven by clinic pull (shadow receipts → promote), not vendor push; **cutover-readiness always visible and always ≤ days away** — the migration is amortized invisibly across the envelope period. Measurable: minutes from credential to first briefing; % of insights confirmed accurate; days to first verb promotion; cutover-readiness score per clinic; per-clinic marginal onboarding cost (target: ≈ credential paste + 1 Unveiling session).
**Opportunity**: onboarding is the demo, the conversion moment, and the moat-start (derived memory + correction signals begin day 1). Across 23 clinics, marginal cost → 0; clinic N inherits group priors.
**Top 3 assumptions**:
1. ezyVet data quality is good enough for verified insights (P5's #1 risk — the §5 bulk export doubles as the audit corpus).
2. The §5 "provide copies of your data" request works mid-subscription and returns a usable format (validated by *sending it* — cheapest possible test; counsel blesses the reading in parallel).
3. Staff will engage with a message-first agent without UI training, and will accept vision-guided sessions (shared-login + consent reality check in staff discovery).

## Shaping
### Solution Sketch (phased)
- **Phase A — Connect + Unveil (read-only):** ezyVet read adapter + sync-narration job reusing 008's document-magic UX (streaming "Found 4 providers… 3,214 patients…" + ✅/⚠️/❓ confirms); guest-start/claim-account (044 pattern, fixed transaction semantics); Act-3 insight engine ("I noticed…"), honesty-gated to record-verifiable insights only; first briefing delivered via existing Twilio/email path same day.
- **Phase B — Shadow week:** counterfactual receipts ("2 cancellations went unfilled; I'd have filled both — here's who I'd have texted") from the autonomy gate running everything at `advise`.
- **Phase C — Verb promotion:** per-verb advise→propose→do promotion UI + audit log; first write verb = waitlist/slot recovery (per board D3). Writes are **dual-path**: ezyVet remains system of record; the native practice model mirrors continuously. Write verbs themselves are the envelope-MVP spec, not this one.
- **Phase D — Cutover (the Replace event, for real):** a **cutover-readiness meter** (data completeness, verbs at `do`, staff engagement, days-of-parallel-run) computed continuously; when the practice chooses, the system of record swaps to native VetAgent, ezyVet becomes a read-only archive, and the subscription ends. Spec 008's Replace animation is the product moment. The dead-man's switch (board risk #1) and the migration are the same machinery — the practice is always days, not months, from cutover.
### Rabbit Holes
- **Pretending the native twin isn't a §3.2(h) question.** The continuously-populated native practice model is the point — and it is exactly what the ToS bans the *partner* from building. The entire structure rides on the clinic-owns-its-records posture: the clinic contracts the API, the clinic populates its own next system, VetAgent develops for that clinic. **Counsel sign-off on this structure is the gate for the whole spec, not a checkbox.** Public posture stays "orchestrate the stack"; the painless replacement is the private endgame, never the marketing.
- Insight cleverness before insight *verification* — one wrong "I noticed" burns the clinic (P5).
- Custom chat UI for staff — message-first; the owner surface is the existing web app.
### No-Gos (this cycle)
- Any write verb; anything touching diagnostics ordering or controlled substances; browser automation; marketing the integration publicly (ToS §4.1 / D1 posture); multi-PIMS adapters (design the port, build one adapter).

### Appetite Assessment
Medium. Phase A is ~2–3 eng-months (the read-only half of the envelope MVP's 6–7); Phases B–C ride the 90-day pilot plan. Small enough to gate on week-1 ground truth (data quality, shared logins, MSA check) before committing.

### COS-Platform Registry
- Consumes: chief-of-staff pattern (interaction loop, autonomy ladder), briefing-artifact pattern, FarmAgent 048 Vera-Program seams (job router/tool contracts/autonomy gate — coordinate extraction rather than fork), onboarding session/extraction-log schema (032/044 convention incl. `source_id` seeding).
- Registers back: **agentic-envelope-onboarding** as a pattern candidate (source ladder over an incumbent system + Unveiling + shadow receipts + verb promotion) — the generalizable "adopt-alongside" motion for any vertical with an incumbent system of record.

### Constitution Check
- KNOW/ADVISE/DECIDE preserved: onboarding runs entirely in KNOW/ADVISE; every promotion to `do` is an explicit human decision with audit trail.
- Licensed-act firewall: no clinical verbs exist in the catalog at any autonomy level.
- Claim discipline: "I noticed" insights must trace to records (the claim-check ethos applied to runtime output, not just marketing).

## Competitive Context
### Best-in-Class Patterns
Plaid Link (credential → instant account visibility), Superhuman onboarding (white-glove unveiling), FarmAgent 044 (guest-start, live canvas), spec 008 (document magic).
### Category Gap
No PIMS or PIMS-adjacent tool onboards by *reading the incumbent and earning verbs*. Vello syncs; it does not introduce itself, notice things, or ask for trust incrementally. The Unveiling-over-ezyVet is a demo no competitor can copy without becoming an orchestration layer themselves.

## ICE Score
| Dimension | Score | Rationale |
|---|---|---|
| Impact | 9/10 | Converts the envelope from strategy slide to felt product; unblocks the Goldsmith pilot; the adoption motion for every future envelope clinic |
| Confidence | 7/10 | Mechanisms shipped in FarmAgent/008; unknowns are ezyVet-specific (data quality, shared logins, MSA) and front-loaded to week 1 |
| Ease | 6/10 | Read-only scope, ~2–3 eng-months; risk concentrated in the insight engine's honesty gate and sync narration quality |

**Low-confidence flags**: Ease (6) — the Act-3 insight engine is new ground; validation = data-quality audit on 2–3 real clinic exports before building it.

## Proceed Signal
**Proceed with caveats**: (1) week-1 ground truth (MSA check, staff discovery incl. shared logins, data-quality audit, **2 weeks of after-hours call logs from 2–3 clinics** — feeds spec 010's containment ceiling) gates the build; (2) coordinate with FarmAgent 048 on the autonomy-gate/job-router seams — extract, don't fork; (3) read-only until shadow receipts have run ≥2 weeks at pilot clinics; (4) copy FarmAgent's *fixed* provisioning/RLS patterns and mandate the e2e + human click-through gate before anything is shown to Goldsmith.

## Marketing Output
### Positioning Message Seed
"You never do a migration. Vera shows up on day one already knowing your practice, earns every responsibility you give her — and if you ever decide to switch, the switch is already done." (Keep ezyVet unnamed in public copy — ToS §4.1 posture; the replacement endgame is never the marketing.)
### Why-Now Angle
The displacement wave forces everyone else to sell migrations; Vera is the only Chief of Staff you can hire without changing anything. [VC-1 adjacent; needs an envelope-variant entry in verified-claims.md — VC-3's replacement math does not apply to envelope clinics.]
### Differentiation Source
The Unveiling on the clinic's own live data — a demo that is also the install, impossible for a PIMS-bound AI to replicate.
