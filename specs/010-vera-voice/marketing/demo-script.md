# Demo Script: Vera After-Hours — Your Phone, Always Answered

**Stage**: Stage 2 — Implementation (demo-grade, pilot committed)
**Generated**: 2026-07-10
**Runtime**: Estimated ~5 minutes
**Audience**: Goldsmith clinic owner + operations manager (also usable for prospective clinics / investors)

> **Discipline for the presenter**: This is a **simulation** demo of the after-hours line. Say so once, plainly. Describe the tested guarantees as "designed and tested to" — the live numbers are what the pilot measures. Never say "24/7", "around the clock", or "day or night": this is the **after-hours** line. Do not imply Vera already recognizes the caller as a shipped capability — caller identity (VP-4a) ships in parallel; the soft-confirm shown here is a check, not memory.

---

## Pre-Demo Setup

**What to have ready**:
- [ ] One clinic loaded with `clinic_voice_config` + a manual `on_call_target`
- [ ] A signed (VP-9) triage protocol active
- [ ] A known client (`Mrs. Alvarez` + pet `Rex`) present
- [ ] The morning-briefing view open in a second window
- [ ] The vet's review queue visible (to show the refill draft landing)

**Opening line**: "It's 9pm. Right now, this call rolls to voicemail — and that voicemail is a booking you lost. Watch what happens instead."

---

## Demo Flow

### Step 1: The Problem
*"Here's what tonight looks like on your current setup."*

It's after hours. The clinic line normally goes to voicemail, and by morning that's a callback to chase — if the client hasn't already booked somewhere else. Three after-hours calls tonight would be three voicemails and, likely, at least one lost client.

### Step 2: The Answer + Disclosure
*"Now watch what happens when Mrs. Alvarez calls the after-hours line."*

Vera answers on the first ring. Before anything else, her first sentence discloses she is an AI assistant — not a nurse or veterinarian — that the call is recorded and transcribed, and that the caller can say "emergency" at any time. She soft-confirms "Is this Mrs. Alvarez?", then books a follow-up for Rex against the live schedule, reading the day, time, provider, and reason back before writing anything.

**What to highlight**: The disclosure plays *before the model engages* — it's enforced in the adapter, below the AI, so it can't be skipped. In the engineering harness this fired on 100% of calls; that's the guarantee we bring into the pilot to measure live.

### Step 3: The Refill (the trust proof)
*"She asks for a refill — watch where it goes."*

Mrs. Alvarez asks to refill Rex's medication. Vera captures it, tells her a veterinarian will review it, and logs it as a **draft** — never "approved." On screen it lands in the vet's review queue, not any auto-approve path.

**What to highlight**: There is deliberately no code path for Vera to approve a refill. "Logged for your veterinarian's approval — never automatic." That's the Expert Firewall: Vera routes, the vet decides.

### Step 4: The Emergency (the safety proof)
*"Now the call that matters most."*

A second call: "My dog just collapsed." Vera interrupts mid-flow, uses zero clinical language, and warm-transfers to the on-call vet — whispering a spoken summary to the human *before* the caller is connected. Then kill the on-call line to show the fallback: Vera reads out the emergency-care directory and guarantees a call-back. Never dead air, never a silent drop.

**What to highlight**: Escalation has *independent authority* — it fires even if the AI stalls or disconnects. In the harness, 100% of flagged calls reached a human with zero silent drops. The live figure is exactly what the pilot exists to measure.

### Step 5 (Final): The Payoff
*"And here's what you walk into tomorrow morning."*

The next-morning briefing shows every overnight call — booked, drafted, escalated, deflected — each with its outcome, a cost-per-call figure, and the follow-ups that need a person. Three calls that would have been three voicemails are now one booking on your calendar, one refill draft in your vet's queue, and one safely-handled emergency. Tie back to the opening line: the voicemail you would have cleared at 8am is already handled.

---

## Key Talking Points

1. Every after-hours call is answered on the first ring instead of going to voicemail — a lost booking becomes a booking on your calendar.
2. Genuine emergencies always reach a person, briefed before they pick up — and the guarantee lives below the model, not in a prompt.
3. Refills are logged for the vet's approval, never automatic — Vera schedules and routes; your veterinarian decides.

---

## Common Questions During Demo

| Question | Answer |
|---|---|
| "Are these real numbers?" | These are simulation results — the after-hours line has been designed and tested to these guarantees in an engineering harness. The Goldsmith pilot is where we measure the live-clinic numbers, and no competitor publishes them, so yours would be the category's first. |
| "Does it recognize the caller already?" | The soft-confirm you saw is an identity check. Caller recognition — Vera knowing it's about Rex's follow-up — ships in parallel (VP-4a); it's the platform direction, not something this after-hours line does on its own today. |
| "Can it make a medical decision or approve a drug?" | No, architecturally. Triage is pure routing with zero assessment language; refills are drafts for your vet. That's the Expert Firewall and it aligns with the AAVSB administrative/clinical line. |

---

## Source Artifacts

Built from the demo flow in: plan.md `## Marketing Output` (Primary), spec.md User Scenarios, tasks.md Demoable Milestones. Guardrails from marketing-notes.md.
