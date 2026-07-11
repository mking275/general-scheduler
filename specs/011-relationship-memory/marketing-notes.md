# Marketing Notes — "Vera Knows the Family" (Feature 011, VP-4a cycle 4a)

**Produced by**: speckit-implement — 2026-07-11
**Source**: spec.md / tasks.md `## Marketing Output`
**Scope guard (G1)**: This build lights up the **voice channel only** (inbound
phone calls, plus SMS STOP/START for consent). Every customer-facing claim below
is scoped to what a caller experiences on the phone today. Cross-channel memory
(SMS ↔ portal ↔ voice) is a later cycle — do not imply it.

> **Caveat for reviewers**: this is engineering-side copy input for
> speckit-marketing, NOT approved marketing. Two hard gates stand before any of
> these can be *said publicly*: (1) the vet-signed memory-scoping policy (VP-9)
> and (2) the real-data ≥90% recognition rate on audited pilot data (SC-004).
> Both are Pilot-Activation items, not shipped in this build.

---

## The 9 [MARKETING] milestones, in plain customer language

Each entry: what a customer/clinic would actually be told, then the honest
boundary so nobody oversells it.

### 1. T008 — "Your whole family, under one roof" (the migration)
**Say**: "When Vera turns on, every pet and every owner you already have comes
across intact — nothing gets lost or orphaned. Families with two owners and
three pets stay one family."
**Boundary**: Announcement-blocking. Proven at 100% link preservation on the
test corpus; the migration *refuses to run* rather than silently drop a link.
Real preservation is re-verified against your actual records at activation.

### 2. T010 — "She never guesses who you are" (the shared-line fix)
**Say**: "If two households share a phone number, Vera will never assume she's
talking to the wrong one. She asks — she doesn't guess."
**Boundary**: Announcement-blocking (this closes a real privacy bug). The old
"pick the first match" behavior is gone: a shared number always returns *every*
possible person, never a silent single pick.

### 3. T013 — "Hi Mrs. Alvarez — is this about Rex?" (recognition)
**Say**: "When your number matches exactly one client, Vera greets you by name
and already knows your pets — no re-introducing yourself every call."
**Boundary**: Customer-visible headline feature. Greeting-by-name happens only
on an exact single-contact phone match; it's identification, not a password —
it never by itself authorizes a change. Runs in a safe "audit-only" mode until
your records pass the identity audit.

### 4. T015 — "A name on caller-ID is not a key" (the verification bar)
**Say**: "Vera won't change your contact info or request a refill just because
your number showed up. Sensitive changes require you to confirm real details —
or she routes you to a staff callback."
**Boundary**: Announcement-blocking security gate. Low-risk actions (reschedule,
cancel) ask one detail; high-risk actions (contact edits, refills) require two
real, checked details or a staff callback. A *wrong* answer is rejected — she
verifies, she doesn't just ask.

### 5. T020 — "She knows more than she'll say" (the privacy rail)
**Say**: "Vera only shares what a given caller is entitled to hear. What she
knows and what she'll say are two different things — by design."
**Boundary**: Announcement-blocking. The default is *deny*: if there's no
explicit rule allowing a piece of information to a caller, she withholds it.
Every share/withhold decision is logged for staff to review.

### 6. T022 — "Text STOP and it just works" (the opt-out doorway)
**Say**: "Clients can text STOP to opt out of automated messages, any time —
Vera receives it and acts on it. Anything that isn't a clear command goes to a
human, never auto-handled."
**Boundary**: Customer-visible / TCPA trust surface. In this build the inbound
line runs in simulation behind the same seam a live carrier webhook will use;
going live is a config flip plus counsel sign-off.

### 7. T028 — "She greets you from what she remembers" (the recognition summary)
**Say**: "A recognized caller hears a warm, personal opening — their name, their
pets — because Vera pulls a short household summary scoped to *their* family."
**Boundary**: Customer-visible. The summary is strictly own-household: it can
never surface another family's details, and an unverified caller gets no name in
the greeting at all.

### 8. T030 — "The pilot didn't break" (no regression)
**Say (internal / clinic-facing reassurance)**: "Turning on family-recognition
did not change or degrade anything about the voice assistant clinics are already
using."
**Boundary**: Announcement-blocking. All 116 existing voice tests still pass
after the upgrade; the existing behavior and its guarantees are byte-for-byte
preserved.

### 9. T031 — "Red-teamed to zero" (the security proof)
**Say**: "Before this ships, we actively try to trick Vera into revealing the
wrong person's information — and the passing bar is zero leaks, not 'few'."
**Boundary**: Announcement-blocking. Across the full collision test set,
wrong-person reveals = 0 and every no-rule request is refused. This is the gate
that must stay green for any client-facing reveal to be enabled.

---

## In-app copy touched (voice-scoped)

| Surface | Copy today | Customer-language? | Note |
|---|---|---|---|
| Recognized-caller greeting | "Hi {name} — is this about {pet}?" | ✅ | Name only on exact single match; identification, not auth. |
| Shared-line prompt | "May I get the name on the account?" | ✅ | Neutral — never reads candidate names aloud. |
| Verification challenge | asks for a real detail (pet name / appointment day) | ✅ | Wrong answer → blocked + staff-callback offer. |
| STOP confirmation | "You have been unsubscribed… Reply START to resubscribe." | ✅ | Sim copy; live copy is counsel-reviewed at activation. |
| Opted-out inbound service | served + AI/recording disclosure persisted | ✅ | Disclosure text + timestamp recorded, not a bare flag. |

**Overall copy status**: ✅ Aligned with the Feature Brief, voice-channel-scoped.
No cross-channel or "always knows you everywhere" language — that would overstate
cycle 4a.
