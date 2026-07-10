# Goldsmith Pilot — Insert: Vera's After-Hours Line

**For**: Goldsmith clinic owner / operations manager (committed pilot)
**One page** · **2026-07-10** · Companion to the Goldsmith pilot package

> Scope: the **after-hours line only** — evenings, overnight, weekends, and holidays outside your configured hours. Daytime calls are never routed to Vera during the pilot. The numbers below marked *(harness)* are results from our simulation test suite; the numbers we'll report to you are **measured live at your clinics**.

---

## What the after-hours line does

When your line would otherwise roll to voicemail, Vera answers on the first ring and:

- **Discloses she's an AI**, up front, every call — not a nurse or veterinarian — that the call is recorded and transcribed, and that the caller can say "emergency" at any time to reach a person.
- **Books and reschedules** against your live schedule, reading the day, time, provider, and reason back before writing anything — straight through your existing scheduling pipeline, with no double-bookings to clean up in the morning.
- **Captures refill requests as drafts for your veterinarian's approval — never automatic.** There is no path for Vera to approve a refill.
- **Escalates a genuine emergency to a person, every time** — warm-transferring to your on-call team with a spoken summary before they pick up; and if no one answers, reading out emergency-care directions and guaranteeing a call-back. No caller is left in silence.
- **Delivers a morning briefing** of every overnight call — booked, drafted, escalated, deflected — with its outcome, a cost-per-call figure, and the short list of follow-ups that need a person.

---

## The safety architecture (why this is safe to put on your line)

The guarantees do not depend on the AI "getting it right" — they are enforced **below the language model**, in the adapter:

- **Disclosure before the model engages** — the AI disclosure is the first utterance, played before the model does anything, so it cannot be skipped *(harness: 100% of calls)*.
- **Independent escalation authority** — a stated "emergency" or a protocol-flagged call triggers escalation even if the model stalls or disconnects *(harness: 100% of flagged calls reached a human, zero silent drops)*.
- **No autonomous clinical or financial action** — refills are drafts for your vet; triage is pure routing with zero assessment language. This is the **Expert Firewall**, aligned with the AAVSB administrative/clinical line: administrative AI, the veterinarian decides, routing not diagnosis.
- **Signed triage protocol required** — the emergency protocol must be signed by your veterinarian before the line handles a live emergency.

---

## What we'll measure at the pilot

No competitor publishes these numbers. Yours will be the first measured in the category.

| What we measure | Target | Status |
|---|---|---|
| Emergencies escalated to a person (zero silent drops) | 100% | Firm SLO — to be measured live |
| Booking accuracy (post-call audit) | ≥99% | Firm SLO — to be measured live |
| Callers told it's an AI, before anything else | 100% | Firm SLO — to be measured live |
| Refills auto-approved by the AI | 0 | Firm SLO — to be measured live |
| After-hours calls resolved without a person (containment) | 50–60% (provisional) | Ceiling set by your real after-hours call mix — finalized after the 2-week call-log pull |
| Cost per call | Reported from call #1 | To be measured live |

**Week-1 ground truth we need from you**: a 2-week pull of your after-hours call logs (to set the achievable containment ceiling and the emergency fraction), a veterinarian-signed triage protocol, and your on-call contact/schedule.

---

*Everything above is built and tested in simulation. Going live is a configuration switch — live telephony/model credentials, your signed triage protocol, and counsel sign-off on the consent/no-training terms — not more building. Internal + committed-pilot use only; not for public distribution.*
