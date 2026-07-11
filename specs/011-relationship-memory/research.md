# Feature 011 — Relationship Memory & Consent: Phase 0 Research

Decisions resolve the Technical Context unknowns. Grounded in the clarified spec (all decisions final), the 010 implementation surfaces, and the shipped Thoth substrate (board section "THOTH MEMORY SUBSTRATE — Vera-core status (2026-07-10)").

---

## D1 — Household / party model shape
- **Decision**: Elevate the flat `Owner(one phone, one email)→Patient` model into `household ← household_contact ← contact_identifier` + `patient_household_link`. A household holds many contacts (co-owners, authorized callers) and many patients; a contact holds many phones/emails and a household role.
- **Rationale**: "The family" is literally unrepresentable today (discover surprise #3). Multi-identifier-per-contact is what lets *either* co-owner's number resolve to the same shared relationship (US1).
- **Alternatives**: extend `owners` with array columns (rejected — cannot express co-owners with distinct verification/consent state, or authorized non-owner callers); model households only in Thoth (rejected — PIMS anchoring + RLS + staff review queue need relational structure).

## D2 — entity_ref keying (stable IDs, not names)
- **Decision**: `{type}:{stable_id}` — `household:vah_*` (synthesized), `client:ezyvet_c*`, `patient:ezyvet_p*`, `staff:*`, `clinic:*`. Display names live in the fact payload, never the key.
- **Rationale**: Names-as-keys (Thoth's `worker:juan_garcia` convention) break on our data — surname collisions across households, PIMS name edits, and PII-in-identifier landing in every log line and index. VetAgent supplies the PIMS→entity_ref mapping at the ChannelBinding layer rather than consuming Thoth's conversation-derived name-keys for party identity.
- **Alternatives**: consume Thoth auto-extracted name-keys (rejected — see above; flagged to core to migrate the convention).

## D3 — Identity resolution against dirty data (kill `LIMIT 1`)
- **Decision**: Resolver returns the **full candidate set** for a normalized identifier; auto-ID + soft-confirm **only** on an exact normalized-phone match to a single household contact; any ambiguity/no-match → neutral "name on the account", no guessed name spoken. Probable duplicates and collisions → **staff review queue; never auto-merge**.
- **Rationale**: `WHERE phone=? LIMIT 1` silently returns whichever row sorts first — a live privacy incident exactly where households are messiest (surprise #2, SC-003). A guessed name on ambiguous/dirty data is a false-positive PII leak. Auto-ID is gated on a real ezyVet-export identity audit before it is trusted.
- **Alternatives**: fuzzy auto-match with a confidence threshold (rejected for auto-greet — the clarification is exact-single-match only; fuzzy candidates still surface, but only for staff-reviewed disambiguation, never a spoken guess).

## D4 — Soft-confirm vs. authentication; tiered verification bar
- **Decision**: Soft-confirm is **identification only** — never authorizes a change or a reveal beyond unverified scope. Any voice-initiated change clears a tiered knowledge-factor bar: **low-sensitivity** (reschedule/cancel) = 1 factor beyond caller-ID (e.g. pet name + appointment day); **high-sensitivity** (contact-info edit, refill request) = 2 factors **or** defer to staff callback. Caller-ID alone never authorizes. Failed challenge → block, state unchanged, offer callback, log.
- **Rationale**: Caller-ID is spoofable; VP-3 lets callers change things, so recognition must not be authorization (FR-008/017/018, SC-005). Knowledge-factor only — hard 2FA/voiceprint is an explicit non-goal.
- **Alternatives**: single fixed bar for all changes (rejected — over-interrogates low-risk reschedules while under-protecting contact edits); biometric voiceprint (out of scope).

## D5 — KNOW≠REVEAL enforcement location (the rail)
- **Decision**: Enforce with a mandatory-`audience` scoped recall API so an unscoped client-facing recall is **unrepresentable** (default-deny). Policy data (`memory_scoping policy`) is vertical; the rail is core-owned. **Until core confirms the rail**, ship a VetAgent `ScopedRecall` wrapper over Thoth `recall()`/`recall_by_kind()`, registry-marked `prototype` with an extraction note.
- **Rationale**: A query-time filter in the domain pack makes the privacy boundary a per-vertical opt-in in the layer least likely to be audited and most likely to have a bug (SC-001 target = 0). FarmAgent needs the identical rail (crew must not recall owner financials). Board ask #2 — core asked to hold the rail.
- **Alternatives**: domain-pack query-time filter as the primary enforcement (rejected as the *boundary*; acceptable only as defense-in-depth behind the rail); post-hoc reveal audit without a pre-reveal gate (rejected — audits a leak after it happened).

## D6 — Consent registry + greenfield inbound intake
- **Decision**: Channel-aware (`voice|sms|email|portal`), per-contact, revocable/reversible opt-out registry with an append-only audit trail; opt-out suppresses **Vera-initiated outbound only** (inbound clients always served, with disclosure). Because `sms_gateway.py` is outbound-only, build the **inbound webhook seam + STOP/keyword processing** as the prerequisite intake path (sim-mode, like 010).
- **Rationale**: A revocation cannot be *received* today (surprise #4). TCPA + AAVSB opt-out expectation; consent governs contact, not service on request (clarification). SC-006: STOP recorded + staff-visible ≤60 s.
- **Alternatives**: keep per-transaction `sms_consent` booleans (rejected — overwritable, no audit, no per-channel/voice/email preference, no revocation path).

## D7 — Consume shipped Thoth; scope discipline
- **Decision**: Bind `thread_id` for single-channel voice continuity; consume `recall_by_kind("identity")` + `recall()` (temporal-filtered, access-tracked) behind ScopedRecall; rely on the sleep agent for consolidation (no vertical config). Do **not** build cross-channel thread switching (4b non-goal) or the memory engine (core-owned).
- **Rationale**: Thoth shipped (migrations 054–056). W4 split holds — consume, don't fork. Using the thread seam without over-reaching into 4b keeps 4a independently shippable.
- **Alternatives**: build a vertical thread store (rejected — forks the engine).

## D8 — Migration of flat owners → households (SC-007)
- **Decision**: One-time migration: each `owner` → a household + one contact + its identifiers (phone, email) + `patient_household_link` for every current owner→patient link; synthesize `household:vah_*` ids. Pre/post link-count assertion; zero orphaned pets, zero lost contacts is a test gate.
- **Source of truth (M1)**: the **production** migration reads the **platform Postgres `owners` table**, which VP-1/009 envelope ingestion hydrates from PIMS (ezyVet) — *not* the demo SQLite `owners`, which is **demo-track only**. The **dev/test** path reads a synthetic flat-owner fixture (derived from the T007 corpus) via a small **SQLite→PG hydration helper** so the same migration code runs against a Postgres source in both paths (no divergent SQLite read path in the real run).
- **Rationale**: 100% link preservation is SC-007 and a hard correctness bar; the migration is where silent data loss would hide.
- **Alternatives**: lazy per-call migration (rejected — leaves the resolver operating over a mixed model; correctness unverifiable in one pass).
