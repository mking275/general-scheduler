# Marketing Brief: The Vera Who Knows Your Family

**Feature**: 011-relationship-memory (Relationship Memory & Consent — VP-4a, cycle 4a)
**Stage**: Stage 2 — Implementation (demo-grade, pilot committed)
**Generated**: 2026-07-11
**Source**: speckit-marketing — compiled from the 011 speckit lifecycle artifacts (discover / spec / plan / tasks `## Marketing Output` sections + marketing-notes.md)
**Audience (priority)**: (1) practice owner / manager (pilot-facing); (2) Goldsmith pilot brief insert — see `goldsmith-pilot-insert.md`

> **Claim discipline**: Every factual claim traces to `../../../marketing/engine-inputs/verified-claims.md` (`[VC-n]`) or the 011 test evidence, cited as such. Scope is the **single voice channel only** (G1) — the after-hours line a caller reaches on the phone today. This is NOT cross-channel memory: Vera does not yet carry the relationship from phone to SMS to portal; that continuity is a later cycle (4b) and is not claimed here. The engineering-harness results below are simulation results ("designed and tested to"); live-clinic numbers are to be measured at the Goldsmith pilot.

---

## Elevator Pitch

**One sentence**: It's the same Vera every time — the after-hours line that remembers your family and knows exactly what she can and can't share with whom.

**Three sentences**: A stateless phone bot starts every call cold — the caller re-explains who they are and which pet they mean, and the practice's memory lives in people's heads and sticky notes. Vera answers the after-hours line already knowing the household: when your number matches one family she greets you by name and knows your pets, and when a number is shared she never guesses — she asks. The recognition that makes her feel like she knows you and the guarantee she'll never tell the wrong person your business are the *same* system — so trust compounds instead of resetting every call.

**Paragraph** (~90 words): The line that used to roll to voicemail now answers already knowing the family. When your number matches one household, Vera opens by name — "Hi Mrs. Alvarez, is this about Rex?" — no re-introducing yourself. When a family shares one phone, she never picks a name; she asks neutrally, and reveals nothing about a household until she's sure who she's talking to. She knows far more than she'll say: every fact is released only to the person entitled to hear it, by policy, default-deny. And a name on caller-ID is never a key — she verifies a real detail before changing anything. Say stop once and she stops reaching out everywhere — yet still helps when you call her.

---

## Why Now

Identity continuity is the one voice differentiator a stateless overlay can't copy without rebuilding its entire memory and operating layer — and the category's framing is being decided right now [discover.md — OST; Why-Now]. The market is in the biggest PIMS displacement wave in decades: no cloud roadmap on the largest legacy system, active sunset on the next, forcing 25,000+ practices to evaluate alternatives over the next few years `[VC-1]`. A practice re-evaluating its stack today is choosing between another record-keeper that answers the phone cold and the first system whose after-hours line actually remembers the family — safely. And the safety is the sell: the same discovery that identity continuity is only a moat if a wrong reveal is impossible is what makes "she knows a lot, but only says what she's allowed to" the headline, not the fine print. The Goldsmith pilot's audited recognition and zero-leak numbers become the category's first published benchmark.

---

## Key Benefits

In the words our customers would use:

1. **Be recognized the moment you call.** No re-explaining who you are or which pet you're calling about — when your number matches your family, the after-hours line greets you by name and already knows your pets. She greets you by name *only when she's sure it's you*; on a shared family phone she asks instead of guessing, so she never speaks the wrong name `[VC-10 — PRODUCT-CLAIM; recognition + soft-confirm built & sim-tested, T013/T028]`. *(Single-channel voice recognition; carrying that memory across SMS/portal is a later 4b announcement, not claimed here.)*
2. **Trust that your information stays yours.** Vera knows a lot about your household, but only ever shares what she's allowed to, with the right person — anything not explicitly permitted for a caller is withheld, and a shared family phone never tricks her into speaking the wrong name. What she *knows* and what she'll *say* are two different things, by design `[011 test evidence: default-deny scoping rail red-teamed to 0 wrong-person reveals on a dirty synthetic corpus, T020/T031]`.
3. **Set your contact preferences once and have them respected.** Say "STOP" a single time and she stops reaching out — every automated message on that channel stops — and she still helps you the moment YOU call HER. Opt-out governs outreach, never service on request `[011 test evidence: 100% outbound suppression on opted-out channels in the harness, T022; SC-002]`.

---

## What Makes This Different

**The privacy story IS the product.** No vet tool treats relationship memory + per-audience consent as a product; today it's a stateless bot plus a compliance opt-out spreadsheet [discover.md — category gap]. Here, recognition and non-leak are one system: Vera can open "Hi Mrs. Alvarez, is this about Rex?" precisely because the same rails that let her know the family also provably stop her from telling the wrong person anything. The recognition is the warmth; the scoping is the safety; they are the same architecture. That is the move — the safety architecture sold as a feature, not buried as a disclaimer.

**KNOW ≠ REVEAL, enforced below the model.** What Vera knows is separated from what she may reveal, per audience, as policy data — not a prompt we hope the model follows. The default is deny: if no rule explicitly permits a fact to this caller, she withholds it, and every share/withhold decision is logged for staff to review [spec.md FR-013/FR-014/FR-016]. This is aligned with the AAVSB administrative-vs-clinical line and TCPA/consent expectations — citable for practice-owner audiences [discover.md — AAVSB whitepaper, §4/§5].

**A name on caller-ID is never a key.** Recognition is identification, not authentication. She'll greet you by name, but she will not change your contact info or take a refill request just because your number showed up — sensitive changes require you to confirm a real detail (your pet's name, your appointment day, checked against the record) or she routes you to a staff callback. A wrong answer is rejected, not waved through [spec.md FR-017/FR-018/FR-019].

**The shared-family-phone fix.** The old behavior silently resolved a shared number to whichever record sorted first — a latent leak exactly where families are messiest. That is gone: a shared number always returns *every* possible person and Vera disambiguates without ever reading the candidate names aloud, revealing nothing household-specific until one caller is confirmed [spec.md FR-010/FR-011; SC-003].

---

## Top 3 Objections + Answers

| Objection | Answer |
|---|---|
| "How do I know it won't blurt out one client's info to another — especially on a phone the whole family shares?" | Because it's built so it can't, not promised so it won't. Reveals are governed by per-audience policy with a default of *deny* — any fact not explicitly permitted for that caller is withheld and logged. On a shared number she never picks a name; she asks, and says nothing household-specific until one caller is confirmed. In the engineering harness, across a deliberately dirty synthetic corpus of shared phones, duplicate owners and ex-spouses, wrong-person reveals were 0 and silent picks on shared lines were 0. The live figure is what we'll measure at your clinic. |
| "So it recognizes my number — can't someone spoof it and change my account?" | No. Recognition is identification, not a password — a name on caller-ID never authorizes a change by itself. Before any change she requires a real detail confirmed against your record (your pet's name, your appointment day), and a high-sensitivity change needs two or a staff callback; a wrong answer is rejected. We ran a 7-attempt spoofed-caller-ID battery — including a wrong pet name and a wrong appointment day — and 0 changes went through. |
| "If a client opts out, does that break the service they actually want?" | No — opt-out governs our *outreach*, not their service. Say STOP once and every Vera-initiated message on that channel stops (100% suppression in the harness), and it's reflected to your staff. But if that same client calls in, Vera still helps them, with disclosure. Stop everywhere; still helped when they come to her. |

---

## Claims Softened or Removed for Discipline (audit trail)

| Original / tempting claim | Why changed | As-published |
|---|---|---|
| Discover seed "the same Vera on any channel" / "remembers you everywhere" | Single-channel voice scope (G1); cross-channel memory (phone↔SMS↔portal) is 4b, not built | Scoped every claim to the voice line; recognition framed as "the after-hours line that remembers your family," no cross-channel "everywhere-she-knows-you" language |
| "0 wrong-person reveals / 0 silent picks / 0 spoofed-ID changes / 100% suppression / 100% migration preservation" as live performance | These are engineering-harness (simulation) results on a synthetic corpus, not live-clinic performance | Framed as "designed and tested to" / "in the engineering harness, across a dirty synthetic corpus"; live numbers "to be measured at the pilot" |
| "≥90% caller auto-ID rate" as a shipped result | That rate is a named Pilot-Activation gate measured on audited real ezyVet data, not the synthetic corpus [spec.md SC-004] | Not claimed as-shipped; recognition described mechanically (greets by name only on an exact single match), the field rate deferred to the pilot |
| Recognition as a general "24/7 / any-time / daytime" capability | 011 lights up the voice line; the consumer surface is the after-hours line (010) | Kept to "the after-hours line that remembers your family" |
| Competitor names (stateless vet voice bots) | Rule 5 — no competitor names in customer-facing copy | Differentiation stated as the category gap + benefits, no names |
| "Vera knows the family" beyond what the policy enforces | discover.md No-Go — marketing bounded by what scoping provably enforces | Every recognition claim paired with its safety boundary; nothing asserted the red-team suite doesn't hold to 0 |

---

## Source Artifacts

| Artifact | Used for |
|---|---|
| discover.md `## Marketing Output` | Positioning seed, why-now, differentiation (category gap) |
| spec.md `## Marketing Output` | Feature name, 3 benefits, one-liner |
| plan.md `## Marketing Output` | Demo flow (see demo-script.md) |
| tasks.md `## Marketing Output` | Demoable milestones, [MARKETING] task flags |
| marketing-notes.md | The 9 built-milestone plain-language claims + copy guardrails (voice-scoped) |
| engine-inputs/verified-claims.md | Claim discipline (`[VC-n]`), VC-11 voice (concrete, numeric, never hype) |

---

*Stage-gated note: at Stage 2, speckit-marketing mandates `brief.md` + `demo-script.md` only. GTM materials (changelog, blog, social — Stage 5; sales one-pager/deck — Stage 6; case study/press — Stage 7) are intentionally NOT generated. The `goldsmith-pilot-insert.md` in this directory is a pilot-facing brief for the already-committed Goldsmith pilot, not a cold-prospect GTM asset.*

**These artifacts are for internal use and the committed pilot only. NEVER publish, post, or distribute without human review and product-truth validation of the PRODUCT-CLAIMs above — and clearance of the two hard gates: the vet-signed memory-scoping policy (VP-9) and the ≥90% recognition rate on audited pilot data (SC-004).**
