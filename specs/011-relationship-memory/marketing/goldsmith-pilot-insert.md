# Goldsmith Pilot — Insert: The Vera Who Knows Your Family

**For**: Goldsmith clinic owner / operations manager (committed pilot)
**One page** · **2026-07-11** · Companion to the Goldsmith pilot package (and to the after-hours-line insert)

> Scope: this is the **voice line** — the after-hours phone your clients already reach. Vera remembers the family *on the call*. Carrying that memory across SMS and the portal is a later cycle and is not part of this pilot. The numbers below marked *(harness)* are results from our simulation test suite on a deliberately dirty synthetic corpus; the numbers we'll report to you are **measured live on your audited ezyVet records**.

---

## What "knows the family" does on the line

When a client calls, Vera resolves the household *before* her first substantive word, and then:

- **Greets a recognized caller by name** — but only when the number matches exactly one contact in one family: "Hi Mrs. Alvarez — is this about Rex?" No re-introducing themselves, no re-explaining which pet. Recognition is identification, not a password.
- **Never guesses on a shared phone.** When a number maps to more than one household, she asks neutrally for the name on the account, **never reads the candidate names aloud**, and reveals nothing household-specific until exactly one caller is confirmed. The old silent single-pick behavior is gone.
- **Says only what a given caller is entitled to hear.** What she knows and what she'll say are two different things: reveals are governed per audience with a default of *deny*, and every share/withhold decision is logged for your staff.
- **Requires a real detail before any change.** A name on caller-ID never authorizes a change. Low-sensitivity changes ask one detail checked against your record; contact-info edits and refill requests need two or a staff callback. A wrong answer is rejected.
- **Honors opt-out once, everywhere on that channel.** A client texts STOP once; every Vera-initiated outbound on that channel stops and it's reflected to staff — yet an opted-out client who calls in is still served, with disclosure.

---

## Why this is safe to put on your line

Recognition and non-leak are the **same** system — the warmth and the safety are one architecture, enforced **below the language model**, not in a prompt:

- **Default-deny reveal rail** — any fact not explicitly permitted for a caller's audience is withheld, and every reveal decision is recorded *(harness: 0 wrong-person reveals across a deliberately dirty synthetic corpus of shared phones, duplicate owners, and ex-spouses)*.
- **Shared-phone leak eliminated** — a multi-match returns the full candidate set, never a silently-chosen record *(harness: 0 silent picks on shared lines)*.
- **Caller-ID is not a key** — sensitive changes require a knowledge factor validated against your records *(harness: a 7-attempt spoofed-caller-ID battery — including a wrong pet name and a wrong appointment day — yielded 0 unauthorized changes)*.
- **Opt-out is a first-class trust surface** — recorded, revocable, audited, honored *(harness: 100% suppression of Vera-initiated outbound on opted-out channels)*, and aligned with the AAVSB opt-out expectation and TCPA/consent state.
- **Nothing was lost migrating your data into households** *(harness: 100% owner→patient link preservation; the migration refuses to run rather than silently drop a link)*.
- **Red-team gate stays green** — before any client-facing reveal is enabled, the passing bar is **zero** wrong-person reveals, not "few."

---

## What we'll measure at the pilot

No competitor publishes these numbers. Yours will be the first measured in the category — on your real, audited records.

| What we measure | Target | Status |
|---|---|---|
| Wrong-person reveals (scoping violations) | 0 | Firm SLO — harness-proven, to be re-verified live |
| Multi-match lookups resolving to a silent single pick | 0 | Firm SLO — the shared-phone leak is eliminated |
| Voice-initiated changes executed without clearing the verification bar | 0 | Firm SLO — to be measured live |
| Recorded opt-outs honored on Vera-initiated outbound | 100% | Firm SLO — to be measured live |
| Owner→patient links preserved through migration | 100% | Firm SLO — re-verified against your export |
| Callers auto-identified + soft-confirmed on an exact single match | ≥90% | **Pilot-Activation gate** — measured on your audited ezyVet data, not the synthetic corpus |

**Week-1 ground truth we need from you**: a real ezyVet export for the identity/dedup audit (shared phones, duplicate owners, ex-spouses, deceased pets — so we tune the resolver on *your* data before it auto-identifies anyone), a veterinarian-signed memory-scoping policy (VP-9), and your staff-role list so audience is derived from role, not a shared login.

---

*Everything above is built and tested in simulation. Going live is gated on two things — the vet-signed memory-scoping policy (VP-9) and the ≥90% recognition rate on your audited pilot data (SC-004) — plus counsel sign-off on the consent/no-training terms. That is validation, not more building. Internal + committed-pilot use only; not for public distribution.*
