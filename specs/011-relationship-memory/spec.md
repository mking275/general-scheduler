# Feature Specification: Relationship Memory & Consent — "Vera Knows the Family"

**Feature Branch**: `011-relationship-memory`

**Created**: 2026-07-09

**Status**: Draft

**Input**: Cycle 4a of VP-4. "When anyone interacts with Vera — owner, staff, or client, on any channel — I want it to be the same Vera, who remembers the relationship and knows exactly what she may say to whom — so trust compounds instead of resetting every call." Scope: household/party identity model, caller identification + verification, per-audience KNOW≠REVEAL scoping, client AI-contact opt-out registry (and its inbound-message prerequisite), and the shared-phone collision fix.

---

## Problem Statement

Today Vera's data model is flat: one owner, one phone, one email, one owner→patient link. "The family" is unrepresentable; callers are matched by an exact-phone lookup that silently returns whichever record sorts first (a latent leak on shared household phones); the only scoping behavior is a single hand-coded first-name-only endpoint; and consent exists as overwritable per-transaction booleans with no way to even *receive* an opt-out (the gateway is outbound-only). Stateless competitors start every call cold; identity continuity — done safely — is the voice moat, but a wrong reveal is a privacy incident, not a bug. Cycle 4a builds the household identity substrate, formalizes scoping as policy, and turns consent into a first-class, honored-everywhere registry.

## Clarifications

### Session 2026-07-09

- Q: How strong must a phone/name match be before Vera greets a caller by name (soft-confirm), given dirty PIMS data? → A: Name-greeting only on an exact normalized-phone match to a single household contact; any ambiguity or no-match drops to a neutral "May I get the name on the account?" — a guessed name is never spoken.
- Q: What knowledge factor constitutes the verification bar for a voice-initiated change, and how does it tier by sensitivity? → A: Tiered. Low-sensitivity changes (reschedule/cancel) require one knowledge factor beyond caller-ID (e.g., pet's name + appointment day); high-sensitivity actions (contact-info edit, refill request) require two factors or defer to a staff callback. Caller-ID alone never authorizes any change. (Matt, 2026-07-09)
- Q: Does an AI-contact opt-out suppress only Vera-initiated outreach, or also Vera serving an inbound contact the client initiates? → A: Opt-out suppresses Vera-initiated outbound on the opted-out channel(s) only. Inbound clients are always served, with disclosure — consent governs contact, not service on request.
- Q: When the resolver finds probable-duplicate or colliding PIMS records, does it auto-merge or group-with-review? → A: Never silently merge. The resolver proposes household groupings; collisions and probable duplicates go to a staff review queue; automatic identification proceeds only on unambiguous single matches.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Vera Recognizes the Family (Priority: P1)

The flat owner→patient model is elevated to a household that holds multiple contacts (co-owners, authorized callers) and multiple pets, resolved and de-duplicated against messy PIMS data by normalized phone + email + name. Any contact in the household resolves to the same shared relationship.

**Why this priority**: This is the net-new substrate every other 4a story stands on — "Vera knows the family" is literally not representable without it.

**Independent Test**: Seed a household with two co-owners (different phones) and three pets; verify a lookup by either contact resolves to the same household with all three pets, and that no medical detail is exposed at the resolution step.

**Acceptance Scenarios**:
1. **Given** a household with two co-owners and three pets, **When** either contact's phone or email is used, **Then** the same household and full pet roster resolve, with no duplicate created for an added authorized contact.
2. **Given** two records that appear to be the same person, **When** the resolver runs, **Then** it proposes a grouping for staff review and does **not** silently merge them.

### User Story 2 — Same Vera on the First Ring (Priority: P1)

An inbound caller whose number matches a single household contact is auto-identified, and Vera opens with a soft confirmation ("Hi Mrs. Alvarez — is this about Rex's follow-up?"). Soft-confirm is **identification, not authentication**.

**Why this priority**: This recognition moment is the felt value of the program and the differentiator VP-3 Voice ships on; a stateless overlay structurally cannot do it.

**Independent Test**: Place an inbound contact from a number matching exactly one household contact; verify Vera greets by name with a soft-confirm question, and that a "no" cleanly re-opens without asserting identity.

**Acceptance Scenarios**:
1. **Given** an inbound number matching exactly one contact, **When** the interaction opens, **Then** Vera soft-confirms by name and offers the most likely reason (recent/upcoming pet activity).
2. **Given** the caller answers "no, this is someone else," **When** Vera responds, **Then** she drops the assumed identity and asks for the name on the account, revealing nothing; a no-match caller is treated as unverified from the first turn.

### User Story 3 — Vera Never Reveals to the Wrong Person (Priority: P1)

What Vera **KNOWS** is separated from what she may **REVEAL**, per audience, as policy data. Audiences: owner, manager, staff, verified client, unverified caller. Reveal is **default-deny** — anything not explicitly permitted for an audience is withheld.

**Why this priority**: Scoping is a security boundary, not a UX nicety; a wrong reveal is a privacy incident. Without it, identity continuity is a liability rather than a moat.

**Independent Test**: For each audience, request the same facts (schedule availability, own-household pet detail, another household's detail, financial detail) and verify each is revealed or refused strictly per policy, with the default being refusal.

**Acceptance Scenarios**:
1. **Given** an unverified caller, **When** they ask beyond general schedule availability, **Then** Vera declines and offers to verify or take a message — revealing no household, pet, or financial detail.
2. **Given** a verified client asking about their own household, **When** Vera responds, **Then** she reveals own-household detail but withholds financial detail and any other household's information; any request with no explicit reveal rule is refused by default, and every reveal decision is visible in the staff verbose log.

### User Story 4 — Shared Household Phone Never Leaks (Priority: P1)

When an inbound identifier matches **more than one** contact or household, Vera returns and disambiguates over a candidate set — she never silently picks one record.

**Why this priority**: This is a live privacy bug (`LIMIT 1` on the current phone lookup) sitting exactly where households are messiest — the difference between a demoable feature and a shipped leak.

**Independent Test**: Seed two households sharing one phone number; place an inbound contact from it and verify Vera disambiguates and reveals nothing household-specific until the caller resolves it.

**Acceptance Scenarios**:
1. **Given** a number matching contacts in two households, **When** a lookup runs, **Then** the system returns **all** candidates — never a single silently-chosen record.
2. **Given** multiple candidates, **When** Vera responds, **Then** she disambiguates with a neutral question and withholds all household-specific detail until exactly one candidate is confirmed, then proceeds against that household only.

### User Story 5 — Verified Before Any Change (Priority: P2)

Before Vera acts on a voice-initiated change (reschedule, cancel, refill request, contact-info edit), the caller must clear a verification bar — a knowledge factor beyond caller-ID — tiered by the action's sensitivity.

**Why this priority**: VP-3 lets callers change things; soft-confirm alone must never authorize a change. Needed before Voice can act, but the read-only recognition path (US1–US4) delivers value first.

**Independent Test**: As a soft-confirmed-only caller, request a reschedule and a contact-info edit; verify the reschedule prompts the lower-tier factor and the contact-info edit prompts the higher bar (or defers to staff), and a failed challenge blocks the change.

**Acceptance Scenarios**:
1. **Given** a soft-confirmed caller requesting a low-sensitivity change, **When** Vera proceeds, **Then** she first requires one knowledge factor and blocks the change until it passes; a high-sensitivity change requires the higher bar (or a staff callback).
2. **Given** a verification failure, **When** the caller cannot clear the bar, **Then** Vera declines, leaves state unchanged, offers a staff callback, and logs the attempt.

### User Story 6 — Opt Out Once, Honored Everywhere (Priority: P2)

A client can opt out of AI contact per channel (voice / SMS / email / portal); the preference is first-class, revocable, honored on every channel, and visible to staff. Because the gateway is outbound-only today, this story includes building **inbound message handling and STOP-keyword processing** so a revocation can even be received.

**Why this priority**: Aligns TCPA and the AAVSB opt-out expectation and turns a compliance chore into a trust surface — but its felt value trails the identity moat and it depends on new inbound plumbing.

**Independent Test**: Send an inbound "STOP" from a client number; verify the opt-out is recorded, reflected to staff, and no Vera-initiated outbound goes to that channel thereafter, while an inbound contact the client initiates is still served.

**Acceptance Scenarios**:
1. **Given** an inbound "STOP" (or equivalent keyword), **When** received, **Then** the opt-out is recorded, confirmed to the sender, reflected in staff-visible consent state, and all Vera-initiated outbound on that channel is thereafter suppressed; a later opt-back-in is recorded with the same audit trail.
2. **Given** an opted-out client who calls or messages in, **When** they initiate, **Then** Vera still serves them (with disclosure) — opt-out governs outreach, not inbound service.

### Edge Cases

- Deceased pet / former co-owner on a household → excluded from soft-confirm reason guesses; flagged for staff, never volunteered.
- Ex-spouses sharing history but not authorization → separate contacts; reveal scope is own-household-as-authorized, not "everyone ever linked."
- Shared staff login → audience inferred from role, not login identity (best-effort in 4a).
- Inbound message that is neither STOP nor a recognized keyword → routed to staff/normal handling, not auto-actioned.
- Caller clears verification for a low-sensitivity change then escalates mid-call → the higher bar is re-applied before the sensitive action.

## Requirements *(mandatory)*

### Household & Identity Model
- **FR-001**: The system MUST represent a household holding multiple contacts and multiple patients, replacing the flat single-owner→patient model.
- **FR-002**: Each contact MUST support multiple phone numbers and emails and MUST carry a household role (e.g., co-owner, authorized caller).
- **FR-003**: Identity resolution MUST match inbound identifiers (normalized phone, email, name) to a household and de-duplicate against existing records.
- **FR-004**: The resolver MUST NOT silently merge distinct records; probable duplicates and collisions MUST be surfaced to a staff review queue.
- **FR-005**: Migration of existing flat owner→patient data into households MUST preserve every current owner–patient link with no loss.

### Caller Identification
- **FR-006**: On an inbound contact, the system MUST attempt identity resolution before Vera's first substantive turn.
- **FR-007**: Vera MUST auto-identify and soft-confirm by name **only** on an exact normalized-phone match to a single household contact; on any ambiguity (multiple candidates, partial/fuzzy match) or no match she MUST NOT speak a guessed name and MUST fall back to a neutral "May I get the name on the account?".
- **FR-008**: Soft-confirmation MUST be treated as identification only, never authentication, and MUST NOT by itself authorize any reveal beyond the unverified-caller scope. (The change-authorization gate is FR-017.)
- **FR-009**: A rejected soft-confirm MUST cause Vera to drop the assumed identity and reveal nothing tied to it.

### Shared-Phone Disambiguation
- **FR-010**: Identifier lookup MUST return the **full candidate set** and MUST NOT reduce a multi-match to a single silently-chosen record.
- **FR-011**: When more than one candidate exists, Vera MUST disambiguate via a neutral question and withhold all household-specific detail until exactly one candidate is confirmed.

### Per-Audience Scoping (KNOW ≠ REVEAL)
- **FR-012**: The system MUST classify every interaction into one audience of: owner, manager, staff, verified client, unverified caller. The staff-side audiences (owner/manager/staff) MUST be derived from a per-user staff role held in `clinic_staff_role` (role → audience 1:1), not from a shared login identity; **voice callers are always classified into the client tier (verified client / unverified caller) in 4a**.
- **FR-013**: Reveal decisions MUST be governed by explicit per-audience policy data (the C1 `memory_scoping` shape), separating what Vera knows from what she may reveal.
- **FR-014**: Scoping MUST be **default-deny**: any fact not explicitly permitted for the current audience MUST be withheld.
- **FR-015**: The unverified-caller audience MUST be limited to general schedule availability; verified clients MUST be limited to their own household and MUST NOT receive financial detail.
- **FR-016**: Every reveal decision MUST be recorded and surfaced in the staff-facing verbose log.

### Verification Bar for Changes
- **FR-017**: No voice-initiated change (reschedule, cancel, refill request, contact-info edit) MUST proceed on caller-ID or soft-confirm alone.
- **FR-018**: The verification bar MUST be tiered by action sensitivity: low-sensitivity changes (reschedule/cancel) require **one** knowledge factor beyond caller-ID (e.g., pet's name + appointment day); high-sensitivity actions (contact-info edit, refill request) require **two** factors or deferral to a staff callback. Each knowledge factor MUST be validated against an authoritative source, and a factor passes **only** on a match: the **pet's name** validates against the caller's household roster (`patient_household_link`) using a normalized **exact-or-first-token** match; the **appointment day** validates against the 010 booking/schedule store. An answer that does not match the source MUST fail the factor (an unvalidated or always-passing bar does not satisfy this requirement).
- **FR-019**: A failed verification MUST block the change, leave state unchanged, offer a staff callback, and log the attempt.

### Consent / Opt-Out Registry
- **FR-020**: The system MUST provide inbound message handling, including recognition and processing of STOP (and equivalent opt-out keywords), as the prerequisite intake path.
- **FR-021**: An AI-contact consent record MUST be channel-aware (voice, SMS, email, portal), per contact, revocable, and reversible, with an audit trail of every change.
- **FR-022**: A recorded opt-out MUST suppress all Vera-initiated outbound on the opted-out channel(s) and MUST be honored across every channel it covers.
- **FR-023**: An opted-out client who initiates contact MUST still be served, subject to the standard AI + recording disclosure.
- **FR-024**: Current consent state MUST be visible to staff.

## Key Entities

- **Household**: The family unit; groups contacts and patients; anchor of shared relationship memory.
- **Contact (Party)**: A person in a household; multiple phones/emails, a household role, and consent state. Replaces the flat single-owner record.
- **Patient**: A pet linked to its household; multi-pet-per-household is native.
- **Identity Resolution**: A match event from an inbound identifier to a candidate set → resolved / soft-confirmed / ambiguous / unmatched.
- **Verification Challenge**: A knowledge-factor challenge for a voice-initiated change; sensitivity tier, factors required, outcome.
- **Memory-Scoping Policy**: Per-audience reveal rules (default-deny) expressed as C1 policy data — the vertical half of relationship memory.
- *Audience prose↔enum correspondence (used throughout data-model/contracts/tasks)*: the prose audiences "verified client" and "unverified caller" are the enum values `client_verified` and `caller_unverified`; "owner"/"manager"/"staff" map to the enum `owner`/`manager`/`staff`. Same five audiences, two surface forms.
- **Consent Record**: Per-contact, channel-aware AI-contact preference with revocation/reversal audit trail.
- **Inbound Message / Opt-Out Event**: A received inbound message and the STOP/keyword handling that records a consent change.

## Success Criteria *(mandatory)*

- **SC-001**: Scoping-violation rate (a reveal outside the audience's policy) is **0** across a red-team test suite.
- **SC-002**: Recorded opt-outs are honored on **100%** of Vera-initiated outbound attempts across every covered channel.
- **SC-003**: **0** instances of a multi-match lookup resolving to a single silently-chosen record (the `LIMIT 1` leak is eliminated).
- **SC-004**: *Build-time proxy* — across the synthetic fixture corpus, **every** inbound contact from an exact single-contact-match number auto-identifies and soft-confirms, and every non-single-match falls back to neutral with no name spoken (the mechanism is proven at build time; the corpus's single-match numbers ID by construction, so this is a correctness proxy, not the field rate). The **≥90% auto-ID + soft-confirm rate on audited real pilot data** is a named **Pilot-Activation gate** (measured against real ezyVet-export/pilot data, alongside the ezyVet identity audit — not the synthetic corpus).
- **SC-005**: **0** voice-initiated changes execute without clearing the applicable verification bar.
- **SC-006**: A STOP received on any inbound-enabled channel is recorded and reflected to staff within **60 seconds** in **≥99%** of cases.
- **SC-007**: Existing owner→patient links migrate into households with **100%** preservation (no orphaned pets, no lost contacts).

## Assumptions & Risks

- Household, scoping, and consent ride the VP-1 Postgres + RLS data plane and **consume** the core Thoth memory substrate — the demo SQLite/no-ORM constitution is superseded here (sanctioned by VP-1); this cycle does not fork the engine.
- Per-audience scoping is expressed as the C1 `memory_scoping` policy data, assuming core confirms C1 can carry it (board ask #4). If it slips, the policy ships as a vertical shim marked `prototype` per the split rule.
- **Dirty-data risk (highest)**: identity resolution against real ezyVet exports (shared phones, duplicate owners, ex-spouses, deceased pets) is unmeasured. The resolver build is **gated on a real-export identity audit** before it is trusted for auto-ID.
- Scoping is a security boundary — red-teamed, not spec-reviewed, before any client-facing reveal. No-training voice/STT vendor clauses and the TCPA consent-state matrix require counsel + DPA (In re Otter.AI) before VP-3 go-live.

---

## Non-Goals (Future Scope)

- **Building the memory engine** — Thoth is core-owned; 4a consumes it.
- **Cross-channel thread continuity** (phone↔SMS↔portal↔kiosk) — **4b, post-pilot**, behind core Thoth landing.
- **Relationship signals into briefings** ("the Alvarezes called twice about billing — churn flag") — **4c**.
- **Hard 2FA / biometric voiceprint authentication** — the verification bar is knowledge-factor only.
- Acting on any **unverified**-caller change request.
- Marketing "knows the family" beyond what the scoping policy provably enforces.

---

## Marketing Output
**Produced by**: speckit-specify — 2026-07-09

### Feature Brief

**Consumer-Friendly Feature Name**: The Vera Who Knows Your Family

**Key Benefits** (in customer language):
1. Be recognized the moment you call — no re-explaining who you are or which pet you're calling about. It's the after-hours line that remembers your family. *(4a is single-channel voice recognition; cross-channel continuity is a 4b announcement.)*
2. Trust that your information stays yours — Vera knows a lot, but only ever shares what she's allowed to, with the right person.
3. Set your contact preferences once and have them respected everywhere — opt out on any channel and it just works.

**One-Line Description** (≤25 words): It's the same Vera every time — the voice line that remembers your family and knows exactly what she can and can't share with whom.
