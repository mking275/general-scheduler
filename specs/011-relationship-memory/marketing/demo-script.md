# Demo Script: The Vera Who Knows Your Family

**Stage**: Stage 2 — Implementation (demo-grade, pilot committed)
**Generated**: 2026-07-11
**Runtime**: Estimated ~5 minutes
**Audience**: Goldsmith clinic owner + operations manager (also usable for privacy-conscious prospective clinics / investors)

> **Discipline for the presenter**: This is a **simulation** demo of recognition and scoping on the **voice line** — say so once, plainly. Describe the tested guarantees as "designed and tested to"; the live numbers are what the pilot measures. Keep the scope to the phone: this is single-channel recognition, NOT "Vera knows you across SMS and the portal" (that's 4b). The whole demo makes one point — recognition and non-leak are the *same* system: she greets you by name only when she's sure it's you.

---

## Pre-Demo Setup

**What to have ready**:
- [ ] One clinic migrated from flat owners into households (show the migration preserved every link)
- [ ] The Alvarez household seeded with two co-owners on **one shared phone**, plus a second household sharing that same number
- [ ] `memory_scoping` policy + `verification_policy` loaded; the ScopedRecall reveal rail on
- [ ] The staff reveal log + consent/review-queue views open in a second window
- [ ] A known single-match number (Jane Alvarez) ready to call from

**Opening line**: "Your after-hours line used to answer every caller as a stranger. Watch it answer already knowing the family — and watch what it refuses to do the instant it *isn't* sure who's calling."

---

## Demo Flow

### Step 1: The Problem
*"Here's what a stateless phone bot does — and the leak hiding inside it."*

Every call starts cold: the caller re-explains who they are and which pet they mean, and the practice's memory lives in people's heads. Worse, on the old lookup a shared family phone silently resolved to whichever record sorted first — a latent privacy incident sitting exactly where families are messiest. That's the "before."

### Step 2: The Recognition
*"Now Jane Alvarez calls — her number matches exactly one family."*

Vera opens "Hi Mrs. Alvarez — is this about Rex?" She greets by name and already knows the pets, and books the follow-up. On screen, the reveal log shows every fact she chose to share and why.

**What to highlight**: She greets by name *only* on an exact single-contact match — identification, not a password. This is the warmth. Note what's about to make it safe: the same rail that let her recognize Jane is the one that stops her leaking to anyone else.

### Step 3: The Non-Leak (the proof)
*"Now a call from the phone the whole family shares."*

Vera does **not** guess a name. She asks neutrally, "May I get the name on the account?", disambiguates over the candidate set **without ever reading the names aloud**, and reveals nothing household-specific until one caller is confirmed. On screen: the old silent single-pick is gone — a probable-duplicate lands in the staff review queue, never auto-merged.

**What to highlight**: A shared family phone never tricks her into speaking the wrong name. In the engineering harness, across a deliberately dirty synthetic corpus — shared phones, duplicate owners, ex-spouses — wrong-person reveals were **0** and silent picks on shared lines were **0**. Recognition and non-leak are the same system.

### Step 4: The Bar & the Wrong Person (the security proof)
*"A recognized caller now tries to change something — and a red-teamer tries to trick her."*

A soft-confirmed caller asks to change the contact email: Vera requires the higher bar — two real details or a staff callback — and blocks the change when it isn't cleared. Then run the spoofed-caller-ID battery: a caller whose number matches but who answers with the *wrong* pet name and the *wrong* appointment day. Every attempt is rejected.

**What to highlight**: A name on caller-ID is not a key. In the harness we ran a **7-attempt spoofed-caller-ID battery** — including a wrong pet name and a wrong appointment day — and **0** changes went through. A default-deny reveal request for another household's balance is refused and logged. The passing bar is zero, not "few."

### Step 5 (Final): The Payoff
*"And here's the trust surface your clients feel."*

A client texts "STOP." It's recorded, confirmed, and visible to staff in seconds; every Vera-initiated outbound to that channel stops. Then that same client calls in — and Vera still serves them, with disclosure. Tie back to the opening line: the after-hours line now remembers the family, provably knows what it may say to whom, and stops reaching out the moment a client asks — while still helping the moment they reach out.

**What to highlight**: Say stop once, she stops everywhere on that channel — 100% outbound suppression in the harness — and still helps when the client calls her. Opt-out governs outreach, not service.

---

## Key Talking Points

1. The recognition that makes Vera feel like she knows you and the guarantee she won't leak are the **same** system — identity, scoping, and consent are policy and rails below the model, red-teamed to zero, not a prompt we hope it follows.
2. She greets you by name only when she's sure it's you — a shared family phone never tricks her into speaking the wrong name, and a name on caller-ID never authorizes a change.
3. Say stop once and she stops everywhere on that channel — and still helps when you call her.

---

## Common Questions During Demo

| Question | Answer |
|---|---|
| "Are these real numbers?" | These are simulation results on a deliberately dirty synthetic corpus — recognition and scoping have been designed and tested to these guarantees in an engineering harness: 0 wrong-person reveals, 0 silent picks on shared lines, 0 changes on a 7-attempt spoofed-caller-ID battery, 100% outbound suppression. The Goldsmith pilot is where we measure the live-clinic numbers on your audited records — and no competitor publishes them. |
| "Does she recognize me everywhere — texts, portal, next visit?" | Today this is the **voice line** only — she remembers your family when you call. Carrying that same memory across SMS and the portal is the next cycle (4b); we're not claiming it yet. |
| "What stops her greeting the wrong person on a shared phone?" | She greets by name only on an exact match to a single family. The instant a number maps to more than one household she stops guessing, asks neutrally, and never reads the candidate names aloud — nothing household-specific comes out until exactly one caller is confirmed. |
| "Is this a compliance checkbox or a real safeguard?" | A real safeguard, and citable: reveals are default-deny per audience with every decision logged, and it aligns with the AAVSB administrative/clinical line and TCPA/consent expectations. The privacy architecture is the feature, not the fine print. |

---

## Source Artifacts

Built from the demo flow in: plan.md `## Marketing Output` (Primary), spec.md User Scenarios (US1–US6), tasks.md Demoable Milestones. Guardrails from marketing-notes.md; claim discipline from engine-inputs/verified-claims.md.
