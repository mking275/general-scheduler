# Discovery: Relationship Memory & Consent — "Vera knows the family"

**Feature type**: new-product-surface (client-facing identity + memory-scoping capability **and** the C1 memory-scoping *policy shape* — not the memory engine, which is core-owned per the W4 split)
**Appetite**: Medium (4a now — pilot-critical for VP-3 Voice; 4b/4c post-pilot)
**Passes run**: 0, 1, 2, 3, 4, 5, 6
**Artifact confidence**: MEDIUM (regulatory grounding HIGH/first-hand AAVSB; identity-continuity thesis is Matt's + competitively reasoned, not yet validated on a real client cohort; no ezyVet client data audited yet)
**Date**: 2026-07-09

---

## Customer Artifacts
**Human-provided:**
- Matt's identity-continuity thesis (L0 §4; synthesis thesis #1): *"the receptionists answer calls; Vera knows the family."* Same Vera across phone/SMS/portal/kiosk/visit is the voice moat a stateless overlay cannot copy without rebuilding the whole operating layer.
- Goldsmith pilot (23-clinic ezyVet group) is the field test; VP-3 after-hours line (~Oct) is the first consumer of 4a.

**Agent-sourced (persisted):**
- AAVSB whitepaper (first-hand, Mar 2025): record-review-for-reminders → "Client should be informed and allowed to opt out" (§5); decision-involvement → written consent each use (§4). Administrative lane = minimal consent, but opt-out is expected.
- L5 voice/legal: Utah AI Policy Act floor (affirmative disclosure at call start); all-party recording states (CA/FL/IL/PA/WA/…); *In re Otter.AI* — no-training clauses with voice/STT vendors are live CIPA exposure ($5k/violation). TCPA consent state per channel.
- Competitive (L3/L5): Dodo (sanctioned ezyVet partner), Otto (5k clinics), Weave, Scritch — all **stateless per-call**; none holds cross-channel relationship memory or per-audience scoping.

Overall confidence: **MEDIUM** — regulation and competitive gap are HIGH; desirability on a real client cohort and dirty-PIMS resolution reality are unvalidated.

## System Reality
### Files Touched
- `backend/models.py` — `Owner(id, name, phone, email, patient_ids[])` → `Patient(owner_id, …)`. **Flat owner→patient; one phone + one email per owner; no household, no multi-contact.** Multi-pet exists via `patient_ids[]`.
- `backend/repository.py::lookup_owner_by_phone_or_email` — exact-match `WHERE phone=? LIMIT 1`; `_normalize_phone` strips to 10-digit. This **is** the caller-identity primitive today — but naive: no fuzzy match, `LIMIT 1` silently drops collisions, no verification step.
- `backend/main.py::/public/owners/lookup` — already privacy-aware: returns **first name only, no medical history at lookup**. The sole extant "scoping" behavior — hand-coded in one endpoint, not a policy.
- Consent today = overwritable booleans: `owners.sms_consent`, `owners.portal_opt_in`, `waitlist_entries.sms_consent`. **No** channel-scoped AI-contact registry, no revocation/audit, no per-channel (voice/email) preference.
- `sms_gateway.py` is **outbound-only** — no inbound webhook, no `STOP`/keyword handling. Opt-outs **cannot even be received** today.
- `owner_sessions` — short-lived booking token, not a Thoth relationship thread.
- `patterns/chief-of-staff/person-like-memory.md` (Thoth) — thread/conversation/identity substrate; the engine, core-owned.

### DB Tables
| Table | Exists? | Schema matches? | Surprise? |
|---|---|---|---|
| owners | yes | partial | no household / multi-contact / opt-out fields |
| patients | yes | yes | multi-pet via owner_id (ok) |
| households / family | **no** | — | "the family" is unrepresentable today |
| contact_consent / opt_out_registry | **no** | — | only per-txn `sms_consent` exists |
| relationship threads / conversations | **no** | — | Thoth-owned; not in vertical DB |

### External Dependencies
| Dependency | Built? | Deployed? | Notes |
|---|---|---|---|
| Core Thoth (client-facing memory) | pattern only | no | board ask #4; W4 split — consume, don't fork |
| C1 domain-pack schema (scoping policy) | no | no | must carry per-audience scoping (board ask #3; core ETA ~post-Wk8) |
| VP-1 Postgres+RLS data plane | in progress | no | memory/scoping cannot live in demo SQLite |
| Twilio TCPA + voice-vendor DPA | partial | no | no-training clauses (In re Otter.AI) — counsel |

### Data Volumes
Proxy: demo SQLite seed (~8 patients). Real scale = ezyVet exports, **not yet audited** — the P5 dirty-data risk is unmeasured.

### Surprises
1. The caller-identity primitive **already exists and already leaks a scoping instinct** (first-name-only, no-history-at-lookup). This spec formalizes ad-hoc code into a policy — not greenfield.
2. `LIMIT 1` on phone match: a shared household phone silently resolves to whichever owner row sorts first — a **latent privacy incident precisely where households are messiest**. The dirty-data risk is already in the code, not hypothetical.
3. **No household / multi-contact model exists.** Owner = single contact. "Vera knows the family" is literally not representable — building the household/contact model is the core of 4a.
4. The opt-out registry has **no intake path**: SMS is outbound-only — a consent/opt-out feature must first build inbound message handling (`STOP`) before it can honor a single revocation. Consent is greenfield end-to-end.
5. Constitution v1.0.0 (SQLite / no-ORM / no-LLM / demo scope) is superseded by pilot architecture (VP-1 PG+RLS + core Thoth). Memory-scoping and cross-channel threads ride that plane; this is a sanctioned supersession, not a violation.

## JTBD
**Job statement**: *"When anyone interacts with Vera — owner, staff, or client, on any channel — I want it to be the same Vera, who remembers the relationship and knows exactly what she may say to whom — so trust compounds instead of resetting every call."*
**Push**: stateless overlays (Dodo/Otto) make every call start cold; clients re-explain; staff re-key; the practice's memory lives in people's heads and sticky notes.
**Pull**: "Hi Mrs. Alvarez — is this about Rex's follow-up?" on the first ring, and an AI that provably won't tell an unverified caller what it knows.
**Anxiety**: an AI revealing PII to the wrong person; being contacted after opting out; "who can Vera tell what?"
**Habit**: receptionists remember regulars; shared logins; per-channel silos (phone system ≠ SMS ≠ portal).
**Non-consumption alternative**: stateless per-call voice bots + human memory + a compliance opt-out spreadsheet.
**Confidence**: MEDIUM — thesis is Matt's and regulator-grounded on consent, but not validated against a client cohort.

## Opportunity
**Product outcome**: identity continuity as the voice differentiator (enables VP-3); opt-out-as-trust-feature. Measurable: % of calls where caller auto-identified + soft-confirmed; **scoping-violation rate (target 0)**; opt-out honored across every channel (100%); demoable "she remembered me" recognition.
**Opportunity**: no vet tool treats relationship memory + per-audience consent as a product; today it's stateless bots + a compliance chore. The moat starts the moment memory + correction signals accrue.
**Top 3 assumptions**:
1. **Desirability** — clients want to be remembered across channels (thesis; unvalidated on cohort). *Medium risk.*
2. **Usability** — phone-match + soft-confirm identifies enough callers to feel continuous **without** false-positive PII leaks on dirty PIMS data. *High risk (surprise #2).*
3. **Feasibility** — per-audience scoping expressible as a C1 policy over core Thoth without forking the engine (W4 split holds). *Medium risk — depends on core ask #4.*

## Shaping
### Solution Sketch (4a, Medium — pilot-critical for VP-3)
- **Household & identity resolution**: elevate flat owner→patient into a household/contact model; resolve/dedup against messy PIMS data (normalized phone+email+name); **kill `LIMIT 1`** — return a candidate set and disambiguate by soft-confirm, never silent pick.
- **Caller identity + verification bar**: phone-number match → **soft confirmation** ("Is this Maria, about Rex?"). Soft-confirm is *identification, not authentication*; a **defined verification bar** (a knowledge factor beyond caller-ID) is required before any voice-initiated **change** (reschedule/cancel/refill-request/contact-info edit).
- **Per-audience memory-scoping policy (the C1 shape)**: audience classes — **owner / practice manager / staff / verified client / unverified caller**. Encode that *what Vera KNOWS ≠ what she may REVEAL*; **default-deny**, verified-reveal. Formalize today's first-name-only lookup as the unverified default.
- **Client AI-contact opt-out registry**: first-class, **channel-aware** (voice/SMS/email/portal), honored everywhere, visible to staff; aligns TCPA + the AAVSB opt-out expectation. **Requires building the inbound-SMS `STOP` path first** (surprise #4). Turns a compliance burden into a trust surface Vera manages.
- **4b (post-pilot)**: cross-channel threads (phone↔SMS↔portal↔kiosk) on Thoth + consent audit surface. **4c (S)**: relationship signals into briefings ("the Alvarezes called twice about billing — churn flag").

### Rabbit Holes
1. **Identity resolution against dirty ezyVet data** — shared phones, duplicate owners, ex-spouses, deceased pets, multi-pet households. The named hard problem (P5); **audit a real export before trusting auto-ID**.
2. Scoping is a **security boundary, not a UX nicety** — a wrong REVEAL is a privacy incident; must be red-teamed, not spec-reviewed.
3. Verification-bar friction vs security — a real bar without turning every call into an interrogation.
4. **W4 split** — do not build the memory engine here; consume Thoth. Requires core ask #4 to land; coordinate, don't fork.
5. No-training vendor clauses + consent-state matrix (In re Otter.AI, TCPA) — counsel + DPA, not code.

### No-Gos (this cycle)
- Building the memory engine (Thoth is core); cross-channel threads (4b); hard 2FA / biometric voiceprint auth; acting on any **unverified**-caller change request; marketing "knows the family" beyond what the scoping policy provably enforces.

### Appetite Assessment
Medium confirmed for 4a; **gate the resolver on a real-data identity audit** before committing to it. 4b/4c queue post-pilot behind Thoth core.

## Registry + Constitution
### COS-Platform Registry
- **Consumes**: chief-of-staff `person-like-memory` (Thoth substrate — engine core-owned, consume via interface); C1 domain-pack schema (scoping-policy layer); VP-2/009 owner-lookup + session primitives (extend, don't fork).
- **Registers back**: **memory-scoping-policy** (per-audience KNOW≠REVEAL) and **contact-consent / opt-out registry** as pattern candidates — any vertical with client-facing memory *copies* these → Vera-core per the split rule.

### Constitution Check
| Principle | Applies? | Status |
|---|---|---|
| I Demo-First, Value-Visible | yes | compliant — scoping decisions + opt-out state visible in Verbose Log |
| II Agentic Pipeline Integrity | yes | compliant — reveals gate through policy; no bypass path |
| III Data Simplicity (SQLite/no-ORM) | yes | **tension** — scoping + threads need VP-1 PG plane + Thoth; demo SQLite superseded (sanctioned by VP-1) |
| IV Role-Aware UI | yes | compliant — per-audience scoping *is* role-awareness generalized to clients |
| V Incremental Buildability | yes | compliant — 4a ships independently; 4b/4c layer on |

**Violations**: none hard. One architecture-supersession flag (III), already sanctioned by VP-1.

## Competitive Context
### Best-in-Class Patterns
- **Dodo / Otto / Weave / Scritch** — stateless per-call; structurally cannot say "about Rex's follow-up?" — this is the wedge.
- **Assort / Hyro** (human-health) — deep-integrate for continuity but expose no per-audience scoping or opt-out registry.
- **Banking phone-verification** — the reference for a knowledge-based soft-confirm + step-up bar for changes.
### Category Gap
No vet (or vet-adjacent) tool treats relationship memory + per-audience consent scoping as a product. Opt-out-as-trust-feature and KNOW≠REVEAL are unserved. *"The receptionists answer calls; Vera knows the family."*

## ICE Score
| Factor | Score | Assumption |
|---|---|---|
| Impact | 8/10 | The voice moat; enables VP-3 differentiation — but 4a is an enabler whose felt value lands through Voice, not standalone |
| Confidence | 6/10 | Substrate/pattern + a working caller-identity primitive exist; dirty-PIMS resolution and scoping-as-C1-policy are unvalidated; regulatory footing is strong |
| Ease | 5/10 | Dirty-data identity resolution + security-grade scoping + core-Thoth dependency are hard; only the opt-out registry is straightforward |
| **ICE Score** | **240** | |

**Low-confidence flags**: Confidence (6) and Ease (5). Validation: (a) audit a real ezyVet export for household/dedup reality *before* building the resolver; (b) confirm with core that C1 can carry the memory-scoping policy (board asks #3/#4) before treating the split as settled.

## Proceed Signal
- [x] Ready to proceed to speckit-specify — **4a scope only**
- [ ] Needs more discovery: real-data identity audit + C1/Thoth confirmation are gates, not blockers

**Recommendation**: **Proceed with caveats** — (1) 4a only; 4b cross-channel threads wait on core Thoth (ask #4) landing; (2) gate the resolver on a real ezyVet-export identity audit (dirty-data P5); (3) treat scoping as a security boundary — default-deny, verified-reveal, red-team before any client-facing reveal; (4) coordinate the C1 memory-scoping policy shape with core — consume Thoth, don't fork; (5) counsel: TCPA consent-state matrix + no-training voice-vendor clauses (In re Otter.AI) before VP-3 go-live.

## Marketing Output
**Produced by**: speckit-discover — 2026-07-09

### Positioning Message Seed
*"When anyone interacts with Vera — owner, staff, or client, on any channel — it's the same Vera, who remembers the relationship and knows exactly what she may say to whom, so trust compounds instead of resetting every call."* — **"The receptionists answer calls; Vera knows the family."**
**Source**: JTBD statement. Use in: speckit-marketing brief.md (elevator pitch anchor).

### Why-Now Angle
Identity continuity is the one voice differentiator a stateless overlay (Dodo/Otto/Weave) can't copy without rebuilding the entire memory + operating layer — and the displacement wave is deciding the category's framing now.
**Source**: OST product outcome. Use in: brief.md (Why Now).

### Differentiation Source
Per-audience KNOW≠REVEAL scoping + a channel-aware AI-contact opt-out registry as a *trust feature*, not a compliance chore — a job no vet tool does. Keep public claims bounded by what the scoping policy provably enforces.
**Source**: Competitive category gap. Use in: brief.md (What Makes This Different).
