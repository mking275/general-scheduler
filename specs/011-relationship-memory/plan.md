# Feature 011 — Relationship Memory & Consent ("Vera Knows the Family"): Implementation Plan

**Branch**: `011-relationship-memory` · **Scope**: VP-4a cycle 4a only (household/identity substrate, caller ID + tiered verification, per-audience KNOW≠REVEAL scoping, consent/opt-out registry + inbound seam, shared-phone fix). 4b cross-channel threads / 4c relationship signals are out of scope. · **Target**: VP-1 convergence platform (Postgres + RLS) consuming the **shipped** core Thoth substrate — **NOT** the demo SQLite scaffold. · **Pilot**: parallel with VP-3 Voice (010), live demo Phase 3 (~Oct 2026).

---

## Technical Context

### Runtime stack (platform, not demo repo)
- **Python 3.11 + FastAPI** on VP-1; **Postgres + RLS** (`clinic_id` tenant scope; party-scoped tables also filter `party_id`). Local `docker-compose` Postgres with app-level scoping for the single-clinic build (VP-1-slip degradation, per 010).
- **Consumes shipped core Thoth** (migrations 054–056 in production): `ThreadManager` (`thread_id` binding), `recall()` / `recall_by_kind()` with temporal filtering + access tracking, `entity_ref` `{type}:{stable_id}` namespace, sleep-agent consolidation (core, no vertical config). 011 **consumes**, never forks the engine (W4 split).
- **entity_ref taxonomy (VetAgent-owned mapping, stable-ID keys — board-confirmed)**: `household:vah_*` (synthesized), `client:ezyvet_c*`, `patient:ezyvet_p*`, `staff:*`, `clinic:*`. Display names live in the fact payload, **never in the key** (surname collisions, PIMS name edits, PII-in-log). VetAgent supplies the PIMS→`entity_ref` mapping at the ChannelBinding layer; does **not** rely on Thoth's conversation-derived name-keys.
- **Inbound intake is greenfield**: `sms_gateway.py` is outbound-only. This cycle builds the inbound webhook seam + STOP/keyword processing (sim-mode, like 010) as the prerequisite for a consent revocation to even be *received*.

### 010 reuse surfaces — 011 FORMALIZES and extends these shims (no duplication)
| 010 artifact (shim) | 011 upgrade |
|---|---|
| `shims/channel_binding_shim.py` (T006) — in-memory registry, candidate-party set + open-name disambiguation, never enumerates names aloud | Backed by the real resolver over `contact_identifier` candidate sets; keeps the identity-safe disambiguation contract; `is_shared_line` becomes the `LIMIT 1`-kill primitive |
| `shims/consent_shim.py` (T008) — channel-scoped `(party,channel)` opt-out set | Backed by `contact_consent` + `consent_event` audit registry; fed by the new inbound STOP path |
| `HouseholdSummary` stub (contract A4, prefetch.py) — returns `None` when VP-4a absent | Real audience-scoped projection; removes the stub, lights the continuity moat |
| `VoiceRepository` patterns (`voice_repository.py`) — CRUD + append-only + `CHECK` guards on Postgres | Reused as the persistence pattern for the 13 new 011 tables (append-only audit spine) |

### C3 ChannelBinding alignment (core committed L1/L2)
Core committed `verification_level` (4-tier) + `party_candidates`→Thoth party IDs, and `consent_registry` checked in `ChannelRouter.route_message()`. **Seam reconcile is a non-mutating boundary adapter (R5, H2)**: 010 has **two** vocabularies — the shim's 3-value `VerificationLevel` (`none|soft_confirmed|strong`) and `VerificationState` (`unverified|soft_confirmed`) — and both keep their exact strings everywhere in 010 (the 116-green suite hard-asserts them). 011 translates **only at the core-binding edge**, mapping every value of both enums onto core's tiers (`none|unverified→unverified`, `soft_confirmed→phone_match`, `strong→identity_confirmed`; `code_verified` is reached only via 011's own factor progression, `otp_verified` unused). 011's own tiered bar produces `code_verified` (1 factor) / `identity_confirmed` (2 factors) directly. Audience scope derives from tier + role, never from caller-ID alone.

### The KNOW≠REVEAL enforcement split (board ask #2 — core ASKED to hold the rail)
VetAgent's binding position: the **enforcement point must be core** — a scoped recall API whose `audience` parameter is *mandatory* so an unscoped client-facing recall is *unrepresentable* (default-deny). The **policy data** (C1 `memory_scoping policy`) stays vertical. Core's Thoth delivery leans toward a domain-pack query-time filter and has **not yet confirmed** the mandatory-audience rail. **Until core confirms**, 011 ships a VetAgent-side `ScopedRecall` wrapper (contract C) that makes unscoped client-facing recall unrepresentable, registry-marked `prototype`, with an extraction note — same pattern as 010's L3 shims.

### Performance / correctness goals
| Metric | Target | Method |
|---|---|---|
| Scoping-violation rate (SC-001) | **0** | default-deny ScopedRecall + red-team suite gates go-live |
| `LIMIT 1` silent-pick (SC-003) | **0** | resolver returns full candidate set; single-silent-pick is unrepresentable |
| Auto-ID + soft-confirm on single-match (SC-004) | build-time proxy = 100% on synthetic corpus; **≥90% real-data = Pilot-Activation gate** (M2) | exact normalized-phone single-contact match only |
| Voice change without cleared bar (SC-005) | **0** | tiered `verification_challenge` gate before any change verb |
| STOP recorded + staff-visible (SC-006) | ≤60 s in ≥99% | inbound webhook → synchronous consent write + staff surface |
| Flat owner→household migration (SC-007) | **100%** link preservation | migration with pre/post link-count assertion, zero orphaned pets |

---

## Constitution Check

> **Complexity Tracking** — this Constitution Check *is* the plan's Complexity Tracking section (aliased per the speckit template). One tracked departure (Principle III), justified in place under the v1.1.0 Platform-track exception.

GS constitution **v1.1.0**: Principle III carries a Platform-track exception permitting PostgreSQL+RLS and external services for platform-track specs (VP-1 and dependents) whose plan declares the departure. 011 is platform-track (Postgres+RLS + core Thoth) and **declares that departure here**.

| Principle | Status | Notes |
|---|---|---|
| I Demo-First / Verbose Log | ✅ (exceeds) | every reveal decision, resolution event, verification attempt, consent change is an append-only, staff-visible record |
| II Agentic Pipeline Integrity | ✅ | reveals gate through the scoping policy; no bypass reveal path; changes gate through the verification bar |
| III Data Simplicity (SQLite, no external services) | ✅ **departure permitted under v1.1.0 Platform-track exception** | scoping + consent ride VP-1 PG/RLS; memory consumes core Thoth. Not an unresolved violation. |
| IV Role-Aware UI | ✅ | per-audience scoping *is* role-awareness generalized to clients; staff consent + review-queue surfaces |
| V Incremental Buildability | ✅ | 4a ships independently; US1–US4 (read-only recognition) deliver value before US5/US6 |

**Security-boundary discipline preserved**: scoping is red-teamed, not spec-reviewed, before any client-facing reveal; soft-confirm is identification only (never authorization); the resolver never auto-merges; opt-out suppresses outbound only (inbound always served, with disclosure).

---

## Project Structure — New Files (on VP-1 platform)

```
backend/relationship/                        # VetAgent-owned 4a tier
├── household_repository.py                  # Postgres/RLS ops for the 13 new tables (VoiceRepository pattern)
├── identity_resolver.py                     # normalized phone+email+name → candidate set; NEVER LIMIT 1
├── review_queue.py                          # probable-duplicate / collision → staff queue; NEVER auto-merge
├── verification.py                          # tiered knowledge-factor bar (config-driven policy)
├── scoped_recall.py                         # [SHIM — extract to core rail] mandatory-audience wrapper over Thoth recall
├── scoping_policy.py                         # loads C1 memory_scoping policy; default-deny evaluator
├── reveal_log.py                            # append-only reveal-decision audit (FR-016)
├── consent_registry.py                      # channel-aware opt-out registry + audit (upgrades T008 shim)
├── inbound_gateway.py                       # NEW inbound webhook seam + STOP/keyword processing (sim-mode)
└── entity_ref.py                            # PIMS stable-id → {type}:{stable_id} mapping (household:vah_* synth)

config/relationship/
├── memory_scoping.<clinic>.yaml             # C1 memory_scoping policy (default-deny) — VP-9-signed policy content
├── verification_policy.<clinic>.yaml        # sensitivity tiers → factors required; staff-callback deferral
└── inbound_keywords.<locale>.yaml           # STOP / START / HELP keyword table (TCPA)

specs/011-relationship-memory/
├── plan.md                                  # this file
├── research.md                              # Phase 0 — decisions + rationale
├── data-model.md                            # 13 tables + migration
└── contracts/
    ├── identity-resolution.md               # resolver API (candidate sets) + review queue + verification bar
    ├── scoped-recall.md                     # ScopedRecall rail (ask to core) + memory_scoping policy shape
    └── inbound-consent.md                   # inbound webhook seam + consent registry + STOP
```
*(The skill's AGENTS.md pointer update is deferred — this task is scoped to the spec directory only.)*

---

## Implementation Phases & Effort (engineer-weeks; ew)

Total **~12.5–15.5 ew**. Calendar shorter with parallelism (A‖E setup; F after A–D).

| Phase | Scope | Effort | Notes / risk |
|---|---|---|---|
| **A — Household & identity data model + migration** | 13 net-new tables; flat `owners→household/contact/identifier` migration w/ 100% link preservation (SC-007); `entity_ref` stable-id mapping. **Gated on a real ezyVet-export identity audit** before the resolver is trusted for auto-ID. | **2.5–3 ew** | Migration correctness is load-bearing; dirty-data audit is a hard input gate. |
| **B — Identity resolver + candidate sets + review queue** | Normalized phone+email+name matching → **full candidate set** (kills `LIMIT 1`); probable-duplicate / collision → staff review queue; **never auto-merge**. Exact-single-match → auto-ID only. | **2–2.5 ew** | Highest dirty-data risk (R1). |
| **C — Caller ID + tiered verification bar (config policy)** | Soft-confirm = identification only; `verification_challenge` gate: 1 factor (low-sensitivity reschedule/cancel) / 2 factors or staff callback (high-sensitivity contact-edit/refill); failed → block + unchanged state + callback + log. | **1.5–2 ew** | Policy-as-config; audit every attempt. |
| **D — Per-audience scoping: policy data + ScopedRecall + reveal log** | `memory_scoping policy` loader (default-deny); **ScopedRecall** mandatory-audience wrapper over Thoth recall (unscoped client-facing recall unrepresentable); append-only reveal-decision log. | **2–2.5 ew** | Security-critical (SC-001=0); enforcement-location risk (R2). |
| **E — Consent/opt-out registry + inbound webhook seam** | Channel-aware registry + audit (upgrades T008); **new inbound webhook + STOP/keyword processing** (sim-mode); ≤60 s staff-visible; opt-out suppresses outbound only, inbound always served. | **1.5–2 ew** | Greenfield inbound = new intake surface. |
| **F — 010 shim upgrade + Thoth binding** | Replace `channel_binding_shim`(T006) w/ resolver, `consent_shim`(T008) w/ registry, `HouseholdSummary` stub (A4) w/ audience-scoped projection; bind `thread_id` (single-channel voice continuity; 4b cross-channel is out of scope). | **1–1.5 ew** | Coordinate C3 4-tier reconcile with core. |
| **G — Test + red-team + migration verification** | Red-team: wrong-person reveal attempts, shared-line collisions, spoofed caller-ID, soft-confirm-as-auth, STOP timing; SC-001/003/005 = 0 harness; SC-007 migration assertion. | **2 ew** | Gates go-live (security boundary). |

**Hard gates before any client-facing reveal**: real ezyVet-export identity audit complete (dirty-data); C1 `memory_scoping` shape confirmed with core (or ScopedRecall shim path); counsel sign-off on TCPA consent-state matrix + no-training vendor DPA; red-team suite green (SC-001=0).

---

## Dependencies & Fallbacks

- **Core Thoth substrate — SHIPPED (migrations 054–056 in prod).** `thread_id`, `entity_ref`, `recall_by_kind` are the stable integration points. Consume, don't fork.
- **KNOW≠REVEAL rail (core scoped-recall API, mandatory audience) — pending core confirmation.** Fallback: VetAgent `ScopedRecall` wrapper (contract C), registry-marked `prototype`, extracted when core lands the rail.
- **C1 `memory_scoping policy` schema freeze — pending (core ~post-Wk8).** Fallback: ship the policy as a vertical shim marked `prototype` per the split rule; FR set (default-deny, deny-on-missing-rule, audit-on-reveal) is the C1 rail spec.
- **Real ezyVet-export identity audit — HARD input gate on the resolver.** Without it, auto-ID stays disabled and Vera falls back to neutral "name on the account" for all callers (US2 degrades, not breaks).
- **010 Voice (parallel) — consumer of 4a.** The shim-upgrade path (Phase F) is the join; 010 already runs against the shims with a `None`-returning stub, so 011 lighting them up is additive.
- **VP-1 Postgres+RLS** — same posture as 010: single-clinic app-level scoping if RLS slips (pilot-only degradation); do **not** regress to SQLite (consent + reveal audit need the envelope plane).

---

## Test Strategy (summary; detail in Phase G)

1. **Scoping red-team (SC-001=0)** — for each audience (owner/manager/staff/verified-client/unverified-caller) request schedule availability, own-household pet detail, **another household's detail**, financial detail; assert reveal/refuse strictly per policy with default = refuse; assert every decision is in the reveal log. Wrong-person reveal attempts included.
2. **Shared-line collision (SC-003=0)** — two households sharing one number: assert full candidate set returned, neutral disambiguation, zero household detail until exactly one candidate confirmed, no name ever spoken aloud.
3. **Spoofed caller-ID / soft-confirm-as-auth** — a matched number requesting a change with no knowledge factor: assert block; assert soft-confirm alone never authorizes; high-sensitivity requires 2 factors or staff callback; every attempt logged.
4. **Migration (SC-007=100%)** — pre/post link-count assertion; zero orphaned pets, zero lost contacts.
5. **Consent (SC-002/006)** — inbound STOP recorded + staff-visible ≤60 s; outbound suppressed on covered channels; opted-out inbound still served with disclosure; opt-back-in audited.

---

## Top 3 Technical Risks

1. **Identity resolution against dirty ezyVet exports** (feasibility/privacy, HIGH). Shared phones, duplicate owners, ex-spouses, deceased pets — a false-positive auto-ID is a PII leak, not a bug. *Mitigation*: gate auto-ID on a real-export identity audit; auto-greet **only** on exact normalized-phone single-contact match (clarification); everything else → candidate set + neutral disambiguation + staff review queue; **never auto-merge**; resolver disabled-safe (falls back to neutral name prompt).
2. **KNOW≠REVEAL enforcement location unresolved** (security, existential to SC-001=0). If scoping ships as a domain-pack query-time filter, the privacy boundary is a per-vertical opt-in in the least-audited layer — the one most likely to leak. *Mitigation*: build the `ScopedRecall` rail **now** so unscoped client-facing recall is unrepresentable (mandatory audience, default-deny), marked `prototype`/extract; red-team suite gates go-live; push core to adopt the mandatory-audience API as the C1 rail (board ask #2).
3. **Spoofed caller-ID + soft-confirm-as-authorization confusion** (security). Caller-ID is trivially spoofable; treating recognition as authorization = a wrong-person change. *Mitigation*: soft-confirm is identification-only by construction (FR-008 — never authorizes a reveal beyond unverified scope or any change); tiered knowledge-factor bar before **any** change (never caller-ID alone); high-sensitivity → 2 factors or staff callback; `verification_challenge` audit + spoofed-caller-ID red-team set.

---

## Conflicts: spec vs. shipped Thoth seams

1. **Reveal enforcement point (the live tension).** Spec FR-013/014 frame scoping as *default-deny policy data* and the board records VetAgent's binding position that **enforcement must be core** (mandatory-audience recall API). Core's Thoth delivery instead provides an **unscoped** `recall()` and *leans toward domain-pack query-time filtering*. This is unresolved. Resolution in this plan: build the `ScopedRecall` shim that imposes the mandatory-audience rail vertically now, marked for extraction, and hold the ask open with core. No functional blocker — only *where* the rail lives.
2. **entity_ref keying convention.** Thoth auto-assigns `entity_ref` from conversation context using **name-keys** (`worker:juan_garcia`); VetAgent requires **stable-id keys** (`client:ezyvet_c12345`) — names-as-keys break on surname collisions, PIMS name edits, and put PII in every log/index. Core has not confirmed migrating its convention. Resolution: 011 supplies the PIMS→`{type}:{stable_id}` mapping at the ChannelBinding layer and does not consume Thoth's name-derived keys for party identity; flagged to core to settle before the namespace fossilizes.
3. **Cross-channel continuity scope.** Thoth's `ThreadManager` *offers* cross-channel thread continuity, but the spec lists it as a **4b non-goal**. Resolution: 011 binds `thread_id` for single-channel (voice) continuity only and does not build the cross-channel switching surface — using the seam without over-reaching scope. Not a conflict, a scope guard.

---

## Marketing Output
**Produced by**: speckit-plan — 2026-07-10

### Demo Flow Sketch

**Audience**: Goldsmith clinic owner + operations manager (and, as an asset, prospective clinics / privacy-conscious investors).
**Estimated runtime**: ~5 minutes.
**Pre-demo setup**: One clinic migrated from flat owners into households; the Alvarez household seeded with two co-owners on **one shared phone** + a second household sharing that number; `memory_scoping` policy + `verification_policy` loaded; the ScopedRecall rail on; staff consent + review-queue views open.

**Step 1 — The Setup**: Vera already runs the schedule and (010) answers the after-hours line. Today we show *who she knows and what she'll say* — starting from the exact shared-phone number that silently leaked a record last quarter.

**Step 2 — The Recognition**: We call from Jane Alvarez's number, which matches exactly one contact. Vera opens "Hi Mrs. Alvarez — is this about Rex's follow-up?" — soft-confirm, identification only. She books the follow-up. The reveal log shows every fact she chose to share, and why.

**Step 3 — The Non-Leak (the proof)**: We call from the *shared* household number. Vera does **not** guess a name — she asks neutrally "May I get the name on the account?", disambiguates over the candidate set without ever reading the names aloud, and reveals nothing household-specific until one caller resolves. On screen: the old `LIMIT 1` silent-pick is gone; a probable-duplicate lands in the staff review queue, **never auto-merged**.

**Step 4 — The Bar & the Wrong Person**: A soft-confirmed caller asks to change the contact email — Vera requires the higher bar (two factors) or offers a staff callback, and blocks the change when it isn't cleared. A red-team caller asks what another household's balance is — default-deny, refused, logged.

**Step 5 — The Payoff**: A client texts "STOP." It's recorded, confirmed, and visible to staff in seconds; every Vera-initiated outbound to that channel stops — yet when that same client calls in, Vera still serves them, with disclosure. Same Vera, everywhere — who remembers the family and provably knows what she may say to whom.

**Key talking point**: The recognition that makes Vera feel continuous and the guarantee she won't leak are the *same* system — identity, scoping, and consent are policy and rails below the model, red-teamed to zero, not a prompt we hope it follows.
