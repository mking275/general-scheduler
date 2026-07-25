# Abridge → VetAgent: Design Transfer

**Date:** 2026-07-24 · **Trigger:** Jay's email (his physician brother, large Greenville hospital system, "changed his life")
**Corpus:** `VetPractice/research/abridge/report.md` ([V]/[U]-tagged, cited). This board is the judgment layer: what we adopt, what we adapt, what we decline.

---

## I. What Abridge actually proves

Abridge is the existence proof for our pilot's literal success condition — **clinicians begging for the software** (Kaiser: 24,600 physicians; #1 KLAS two years running at 95.1; NEJM-AI RCT burnout reduction). Mechanically, the love comes from five design decisions, none of which is "the AI is smart":

1. **Zero behavior change during work.** No wake words, no hardware, no scripts; specialty/language/speakers auto-detected. The clinician does nothing new — the product happens *to* them.
2. **Magic in under 60 seconds.** Draft note lands 38–76s after the visit [V, peer-reviewed]. Sub-minute latency is itself a trust signal — it feels like the system was listening, not batch-processing.
3. **Output lands inside the tool they already live in** (Epic; "never need to leave"). Not an app they must visit.
4. **Trust by construction, not assertion — "Linked Evidence."** Every generated phrase is one click from its source transcript passage with audio replay. Plus an ironclad contract: the clinician who had the encounter always reviews and signs; and a published won't-do list. **Trust comes from making the AI catchable.**
5. **They sell identity restoration, not efficiency.** "Arrive prepared. Stay present. Leave finished." The counter-finding matters equally [V]: total after-hours EHR time often *doesn't* shrink — the work *feels* different. Hours-saved is the least reliable claim in the category.

Validation of our existing shape: Abridge is **enterprise-only via the Epic partnership** — independents literally cannot buy it. That's the same side of the market our ICP decision picked (large groups via deep ezyVet envelope), while Digitail fights for the independents Abridge ignores.

## II. What VetAgent adopts (decisions)

**D1 — Linked Evidence becomes product surface, not audit plumbing.** We already built the substrate: `entity_ref`/`source_id` lineage on 100% of envelope records (009), append-only logs, claim-discipline receipts. Doctrine from today: **every Vera output — SOAP draft sentence, booking confirmation, reconciliation line, briefing claim — is one click from its source** (call-audio timestamp, PIMS record, §5 export lineage). This is culturally impossible to retrofit; we're early enough to make it constitutional. Applies to VP-3 briefings, 010 voice actions, 009 reconciliation reports (already compliant), and everything after.

**D2 — The published won't-do list.** Abridge earns trust partly by loudly not doing things (no auto-sign; scope limits). We have the pieces (Expert Firewall, adapter guarantees, disclosure-first, DVM-signs-clinical, routing-not-diagnosis) — assemble them into a **customer-facing one-page "What Vera will never do"** and treat it as a marketing asset, not a compliance appendix. (Marketing engine input; Raskin narrative stage will like it.)

**D3 — Engineering budgets from the magic-moment math** (targets for the voice/scribe stack): draft artifact < 60s after interaction end; zero new hardware; zero wake words; opt-in from the professional's own phone. These become NFRs on any scribe-shaped work.

**D4 — Pilot metrics: instrument feelings, not just minutes.** Translate Abridge's flywheel to vet and add to the Synergy Vet pilot plan alongside containment/booking metrics:
- after-hours record-completion time per DVM ("pajama time")
- same-day callback completion rate
- **staff opt-in rate week-over-week — the "beg for it" metric, formalized** (Working Rule 0's success condition becomes a number)
- a short fulfillment pulse (MGB-style burnout/presence questions, per-clinic)
And marketing discipline per the counter-finding: **lead with "leave finished," never with hours-saved.**

**D5 — The scribe wedge, resequenced but envelope-safe.** Jay's nudge + Digitail field intel (the scribe is the #1 *loved* feature in vet software) + Abridge's proof → ambient SOAP documentation is the strongest staff-pull wedge we have. Proposal: **spec candidate 012 "Vera Notes"** — opt-in ambient SOAP scribing from the DVM's own phone, Abridge-grade UX targets (D3), Linked-Evidence-native (D1). Two envelope-honest phases:
- **Pilot phase:** draft delivered to the vet through existing channels (their phone, email-to-self, clipboard) — no PIMS write verbs (009's non-goal stands), no forced adoption, no logins for anyone who didn't opt in. Invisible-adoption compliant *because opt-in pull is the doctrine's success path, not a violation of it*.
- **Post-activation phase:** write-back into ezyVet when write verbs promote at pilot-activation gates.
Status: **discovery-ready, awaiting Matt's go.** Note for core/Steward: scribing generalizes across verticals (MedWatchers pharmacists do CMR documentation; FarmAgent field notes) — candidate platform-common capability per the C8-scheduling precedent, with the vet vertical proving it first.

## III. What we decline

- **Room hardware / always-on ambient in clinics** — Abridge proves software-only wins; also our privacy posture is cleaner opt-in per-encounter.
- **Hours-saved headlines** — per the counter-evidence; feelings metrics carry the story.
- **A separate destination app for staff** — everything lands where people already are (phone, existing channels, the PIMS at write-back).

## IV. The Greenville caveat (handle with grace)

No evidence Prisma Health runs Abridge; the one trace found lists Prisma as a **DeepScribe** customer [U, single source]. Jay's brother may be describing a competitor — which strengthens, not weakens, the thesis (the *category* reverses burnout when the five design decisions hold). Suggested move: Matt asks Jay, naturally: "which system does your brother's hospital actually use? We tore down Abridge and the whole ambient-documentation category — the lessons hold either way." Never correct Jay in writing.

## V. For the Jay conversation (one paragraph)

"Your brother's experience is exactly the adoption dynamic we're engineering for: nothing new to learn, the hated work disappears, every AI sentence traceable to its source, and the professional signs everything. We tore Abridge down to the studs — the five design decisions that make physicians love it are all transferable, three were already in our architecture (source-traceability, professional-signs, zero-behavior-change), and the other two just became engineering targets (sub-60-second drafts, opt-in from the vet's own phone). The plan: your DVMs get an opt-in note-taking experience of that grade during the pilot, and we measure what your brother described — not hours saved, but whether people leave finished."

---
*Related: `VetPractice/research/abridge/report.md` (full corpus) · Digitail deep-dive §VI (scribe = most-loved vet feature) · spec 010 (voice stack the scribe rides on) · 009 lineage substrate (Linked Evidence foundation).*
