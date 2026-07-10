# VetAgent V0.2 — UberSpeckit Program List

**Date**: 2026-07-09 · **Stream**: VetAgent agent (W1) · **Form**: canonical `FarmAgent2-Workspace/context/uber-speckit.md` (12-step lifecycle mandatory per program; dual-deliverable rule applies to every artifact)
**Inputs**: Goldsmith feedback (phase-4 brief F1–F6 + R1–R9) · Vera Program #2 (VetAgent Convergence) · V0.2 research corpus (`VetPractice/research/v02/` — synthesis + lanes L0–L5)
**Supersedes**: the canonical list's Program #2 as written (its JTBD — "replace Cornerstone" — predates the envelope strategy; revision proposed below, adoption via the interface board since the canonical file is FarmAgent-workspace-owned).

---

## The V0.2 Thesis (three sentences)

**One Vera, everywhere, remembering.** The same "person" who answers the phone at 2am runs the waitlist at 9, drafts the discharge at 3, and briefs the owner at 7 — across every channel, with the family's history in mind, over the incumbent PIMS the clinic never has to leave. We sell measured benefits (slots filled, staff-hours returned, missed-call revenue, one bill), never feature-grids; and everything client- or patient-adjacent lives inside the AAVSB's own administrative/clinical line, enforced architecturally.

## Program Registry & Dependency Graph

```
                     ┌─ VP-1 Convergence v2 (envelope data plane + Vera loop) ─┐
   [core C1–C5] ──►  │                                                          ├─► VP-8 Enterprise (400→11k)
                     ├─ VP-2 First Day onboarding (spec 009) ◄─ pilot Phase 1–2 │
                     ├─ VP-3 Voice (after-hours → full front door)              │
                     ├─ VP-4 Relationship Memory & Consent  ◄─ (enables VP-3    │
                     │        differentiation: "same person")                   │
                     ├─ VP-5 Staff & Shift Scheduling ─ (on-call rota → VP-3)   │
                     ├─ VP-6 Financial Copilot                                  │
                     ├─ VP-7 Procurement ─ (watch: MWI–Covetrus)                │
                     └─ VP-9 Vet Domain Pack (W10 content; ships via C1) ───────┘
   VP-10 Ops Advisor rides pilot shadow-receipt evidence; graduates post-pilot.
```

**Sequencing**: *Now (pilot, Aug–Oct)*: VP-1, VP-2, VP-3(a), VP-4(a), VP-9(a) + SOC 2 clock (VP-8a paperwork). *Post-pilot (Q4)*: VP-5, VP-6, VP-3(b–c), VP-4(b). *2027*: VP-7, VP-8 (b–d), VP-10 — timed to Goldsmith's operator introductions.

---

## VP-1 — VetAgent Platform Convergence v2 *(revision of canonical Program #2)*

> **Phase**: now · **Appetite**: Large (8–10 wks) · **Spec seeds**: existing 2a/2b cycles + envelope data plane

### JTBD
*"When I bring Vera into my clinics, I want her running on real infrastructure over the PIMS I already have — reading everything, remembering everything, acting only where I've said yes — so my group gets a Chief of Staff without a migration project."* (Rewrites the stale "replace Cornerstone" JTBD — Goldsmith runs ezyVet; the strategy is the envelope.)

### Discovery Seed
- Canonical Program #2 cycles 2a (PostgreSQL+RLS+COS wiring) and 2b (Vera loop port; 20 agents → tool catalog; `VERA_PROFESSIONAL_BOUNDARIES` at catalog level) — unchanged.
- Envelope board (data ladder ①–④) + L2: PIMS record as hub; three adapter species (API / on-prem agent / human-API) with distinct legal+latency envelopes — **not** one clean port.
- L2 correction set: Covetrus Connect paused; Vetspire self-serve GraphQL; Provet open — adapter priority order.

### Delivery Cycles
| Cycle | Appetite | Stories |
|---|---|---|
| 1a Foundation | M | 2a as written (PG, RLS `clinic_id`, COS wiring) |
| 1b Vera loop + catalog | L | 2b as written; boundaries enforced at tool-catalog level |
| 1c **Envelope data plane** | L | §5-request bulk ingestion → extraction pipeline; ezyVet Automated Reports intake; read-through cache + append-only action log (no shadow DB); `PimsAdapter` port with the three adapter species |
| 1d Pilot deploy | M | GCP deploy; Goldsmith clinics 1–3; weekly scorecard plumbing (CFO go/no-go metric from day 1 — L4) |

### Key Decisions for Discovery
Adapter-species interface (one port, three drivers vs three ports)? · Cache freshness SLAs per verb? · Fork GS repo vs new repo (inherited from #2)?

### Dependencies
Core C1/C2 (board asks) · feeds everything.

### Marketing Output seed
Positioning: "No migration. Vera works with what you have." Why-now: displacement wave + AAVSB-blessed administrative lane. Differentiation: only cross-PIMS agentic layer.

---

## VP-2 — Vera's First Day *(spec 009, discovery complete)*

> **Phase**: now (pilot Phases 1–2 ARE this program's field test) · **Appetite**: Medium (Phase A ≈ 2–3 eng-months)

JTBD, cycles (Connect+Unveil → shadow receipts → verb promotion → Phase D cutover-readiness), decisions, and gates: as in `specs/009-vera-envelope-onboarding/discover.md`. Next lifecycle step: **specify**. Pilot week-1 ground truth (counsel structure, staff discovery incl. shared logins, data-quality audit) gates the build.

---

## VP-3 — Vera Voice: the Front Door *(spec seed 010; F1)*

> **Phase**: now (after-hours demo targeted for pilot Phase 3, ~Oct) · **Appetite**: Large across cycles; A1 Medium

### JTBD
*"When a client calls my clinic — 2pm or 2am — I want them answered immediately by the same Vera who knows their family and my schedule, who books them, handles the routine, and gets true emergencies to a vet fast — so we never lose a client to a missed call and my staff never drown in the phones."*

### Discovery Seed
- L5: build direct on **Twilio Media Streams + Gemini Live** (~$0.03–0.04/min all-in ≈ $36–50/clinic/mo COGS after-hours; supports a $149–249/mo flat voice tier vs the $200–300 GuardianVets line). Gemini Live is Preview → C3 port keeps an OpenAI Realtime fallback. Telnyx bake-off (~35% cheaper minutes).
- L5 legal bar: AVMA-teletriage-anchored protocol (routing + generic first aid only; zero assessment language); first-utterance AI+recording disclosure (Utah floor + all-party states); deterministic escalation keywords, **100%-escalation SLO on flagged calls**; human overflow behind everything; *PA v. Character Technologies* — behavior over disclaimers.
- L3/L0 competitive: **Dodo** (vet-native, sanctioned ezyVet partner, ER routing shipping), Otto, Weave, **GuardianVets AI** ($7M) — the category exists; our wedge is VP-4's continuity + the operating layer. Healthcare containment benchmark 44–60%; nobody publishes numbers → our pilot metrics are marketing assets.
- Benefits doctrine: quarterly table-stakes floor = answer / book / refill-*request* (draft-for-approval only) / route-emergency.

### Delivery Cycles
| Cycle | Appetite | Stories |
|---|---|---|
| 3a After-hours line (1 clinic) | M | Answer+disclose → identify caller (VP-4a) → book/reschedule → voicemail deflection → morning report of every call |
| 3b Emergency routing | M | Vet-signed protocol state machine; hard keywords; warm transfer to on-call (VP-5 rota) / ER partner directory (VP-9); 100% escalation SLO; full transcripts |
| 3c Daytime overflow + continuity | M | Overflow rings Vera before voicemail; cross-channel thread pickup ("about Rex's follow-up?"); ES bilingual |
| 3d Scale + telemetry | M | Containment/booking/escalation dashboards; cost-per-call telemetry (R7); number porting; overflow-to-human contract |

### Key Decisions for Discovery
Overflow partner (VetTriage?) vs staff rota only? · GuardianVets: displace, or partner where they hold the human layer? · Voice tier pricing final (flat $149–249 in platform fee vs add-on)? · New line vs port the clinic's number (trust + 10DLC implications)?

### Dependencies
Core C3 (realtime channel tier — **the pacing ask on the board**) · VP-4a caller identity · VP-5 rota · VP-9 protocols/directory.

### Marketing Output seed
One-liner: "Your phone, answered by someone who already knows the family — every hour of every day." Demo: call twice; she remembers. Then watch the same Vera fill tomorrow's gap.

---

## VP-4 — Relationship Memory & Consent *(vertical half only — the substrate is CORE)*

> **Phase**: 4a now (pilot-critical for VP-3), 4b post-pilot · **Appetite**: Medium (thinner than first drafted)
> **Scope correction (Matt, 2026-07-09)**: relationship memory is a *common Vera function* per W4 — every vertical copies it. The **substrate** (identity-resolution framework, per-audience scoped memory views, cross-channel thread continuity, consent/opt-out registry machinery) is a **proposed core program** (Thoth #5 extension — board ask upgraded). VetAgent's VP-4 = the vertical half: household/multi-pet identity resolution against messy PIMS data, the vet audience taxonomy + reveal rules (shipped as the C1 `memory_scoping` block), TCPA/vet-board consent specifics, and the verification bar for voice-initiated changes.

### JTBD
*"When anyone interacts with Vera — owner, staff, or client, on any channel — I want it to be the same Vera, who remembers the relationship and knows exactly what she may say to whom — so trust compounds instead of resetting every call."*

### Discovery Seed
- Matt's thesis (L0 §4): identity continuity IS the voice moat — "the receptionists answer calls; Vera knows the family."
- COS `person-like-memory.md` + Thoth (core #5): threads, identity continuity, topic drift — now with its most demanding consumer.
- L0 regulatory: **per-audience memory scoping** (client-facing persona reveals only client-appropriate memory); AAVSB opt-out expectations → **client AI-contact opt-out registry** as a first-class trust feature; TCPA consent state; no-training clauses with voice vendors (*In re Otter.AI* wiretap exposure).

### Delivery Cycles
4a Caller identity + verification (number match → soft confirm) + client-scoped memory view + opt-out registry (M) · 4b Cross-channel threads (phone↔SMS↔portal↔kiosk) + consent audit surface (M) · 4c Relationship signals into briefings ("the Alvarezes called twice about billing — flagging churn risk") (S)

### Key Decisions
Client-identity resolution across PIMS records (households, multi-pet)? · Memory-scoping policy representation in C1 vs core? · Verification bar for voice-initiated changes?

### Dependencies
Core Thoth (#5) + C1 scoping schema — board ask. Feeds VP-3 differentiation directly.

---

## VP-5 — Staff & Shift Scheduling *(spec seed 012; F3)*

> **Phase**: post-pilot Q4 · **Appetite**: Medium (thin: domain pack + config over the core engine)

**JTBD**: *"Vera drafts next month's rota — DVM/tech coverage ratios, licensure, PTO, on-call, float across sister clinics — and my staff swap shifts by texting her."*
**Seed**: core scheduling engine (#1, "schedule is the spine") + staffing domain pack (VP-9); **L2 find: Deputy has a true public read+write API** → build-vs-integrate is now a real discovery question; on-call rota feeds VP-3b; float pools = first cross-clinic verb (VP-8 preview); labor-rule constraints.
**Cycles**: 5a rota drafting + constraints (M) · 5b conversational swaps/absences w/ approval ladder (S) · 5c float pools + demand-forecast staffing from appointment load (M).
**Decisions**: Deputy integrate vs native? · Rota constraint rep in C1? · Demand forecast source (native schedule vs envelope-read)?

---

## VP-6 — Financial Copilot *(spec seed 013; F4)*

> **Phase**: post-pilot Q4 · **Appetite**: Medium

**JTBD**: *"Overnight, Vera reconciles yesterday to the penny; Monday's briefing shows revenue per DVM, no-show cost, and one specific recommendation — with the evidence linked."*
**Seed**: **Stripe Connect + Terminal** (public, platform economics; Sunbit BNPL free toggle; beat the PIMS-payfac land-grab) · **QBO not Xero** (L2 correction, ~80% share; Intacct partner-gated at 20–150-clinic groups — VP-8 tier) · advisory firewall ("not a CPA") with Abridge-style linked evidence · **counsel item**: ezyVet API terms' SMS/payment-outside-framework clause vs our non-API wiring (likely fine — verify).
**Cycles**: 6a payments rail + reconciliation (M) · 6b QBO sync + KPI layer (S) · 6c advisory briefings w/ evidence links (M).
**Decisions**: payfac posture (Stripe Connect platform vs referral)? · CareCredit (gated-real, Weave precedent) timing? · Group-tier consolidation (Intacct) now or VP-8?

---

## VP-7 — Procurement *(spec seed 011; F2)*

> **Phase**: 2027 (needs partnership lead time; premise re-shaped) · **Appetite**: Medium

**JTBD**: *"Vera notices stock running low, compares real prices across my suppliers, and hands me a one-tap cart at the best total cost."*
**Seed**: **no cross-distributor pricing API exists** (L2) → guided-operator is the PRIMARY architecture (Vetcove portal via vision-guided sessions; Midwest client-secret ordering; Vetcove API = order/inventory sync only) · **MWI–Covetrus merger (Feb 2026) strikes at the comparison premise** — fewer independent price points; re-shape as "best available total cost + delivery time," not pure price war · predictive reorder from usage trends.
**Decisions**: Vetcove partnership pursuit vs pure guided-operator? · Scope: top-N SKUs vs full catalog? · Kill criterion if consolidation leaves <2 comparable sources?

---

## VP-8 — Enterprise: 400 → 11,000 *(spec seed 015; F6 + R1–R4)*

> **Phase**: 8a now (clock items), 8b–d 2027 · **Appetite**: Large

### JTBD
*"As a regional director of a 400-clinic group, my Vera briefs me on my 32 clinics — exceptions, policy compliance, staffing gaps — while corporate sets the autonomy policy once and every clinic inherits it; and the platform doesn't blink whether we run 1 PIMS or 9."*

### Discovery Seed
- L1: lead persona = second-tier PE roll-up (Alliance, AmeriVet, Rarebreed, Mission — mixed legacy estates, no internal AI team); Mars/Chewy-tier build their own — deprioritize; 11k = multi-tenant/multi-operator ceiling, not one logo.
- L4 (Denticon blueprint): **org-tree tenancy + policy inheritance as core architecture** — the same structure answers the 11k security checklist ("7-level RBAC"); wave-rollout PMO + train-the-trainer + **utilization telemetry as product** (the AI-graveyard defense); pilots must emit the CFO number.
- Enterprise-readiness split (L4): 400-tier = Type II *in observation* + SIG-Lite + $5M cyber + 3-site pilot; 11k delta = completed Type II, SCIM, SLA credits, ITSM, $10M+, named CSM.
- Hierarchical Vera (Veras briefing Veras) → **COS-platform pattern ask** (FarmAgent multi-ranch wants it too).

### Delivery Cycles
8a Clock items now: SOC 2 program start, security-questionnaire pack, insurance (S, mostly non-eng) · 8b Org-tree tenancy + policy inheritance + delegated admin (L) · 8c Hierarchical briefings (clinic→region→exec rollups, exception-based) (M) · 8d SSO/SCIM + audit + wave-rollout tooling + adoption telemetry (L).

### Key Decisions
Tenancy tree in core vs VetAgent (split rule says core — board ask)? · Utilization SLO defaults? · First enterprise design partner (via Goldsmith network) and when to engage relative to pilot go/no-go?

---

## VP-9 — Vet Domain Pack *(W10 content program; ships via C1)*

> **Phase**: content authoring starts at C1 schema freeze (board ask #3) · **Appetite**: Medium, ongoing

**JTBD**: *"Everything Vera knows that is specifically veterinary — triage protocols, staffing ratios, practice KPIs, the AAVSB line, the ER directory — versioned, testable, and shipped through the schema with the safety rails core enforces."*
**Seed**: AVMA-teletriage-anchored phone protocols (vet-signed, per-clinic ER directory + poison control) · AAVSB administrative/clinical taxonomy encoded per verb (L0) · staffing/licensure constraint sets (VP-5) · practice-KPI definitions (VP-6) · 50+ scenario regression suite per the core evaluation pattern · content mine, rails theirs (W10) — neither may weaken the other's half.
**Decisions**: protocol sign-off workflow (which DVM signs; per-clinic vs per-group)? · Pack versioning + clinic-override bounds? · Regression-suite ownership split with core?

---

## VP-10 — Ops Advisor *(spec seed 014; F5)*

> **Phase**: 2027, gated on pilot insight-accuracy track record · **Appetite**: Medium

As phase-4 brief: shadow receipts matured into observe→hypothesize→propose-experiment→measure loops; Confidence-to-Urgency matrix keeps advice in briefings, not interruptions. Rides VP-1 telemetry + VP-9 heuristics. **Gate**: ≥ agreed insight-accuracy threshold across pilot Phase 3 before any efficiency recommendation ships.

---

## Cross-Program Actions (not programs)

1. **Corrections sweep** (synthesis table): envelope board IDEXX figure; VC-9 rewording + GuardianVets reclassification in `verified-claims.md`; integration-report revisions before reuse.
2. **Board asks to core** (update interface board): C3 realtime tier is pacing VP-3; C1 freeze date paces VP-9; Thoth client-relationship workload + memory-scoping (VP-4); org-tree tenancy + hierarchical-Vera pattern (VP-8). Plus: canonical `uber-speckit.md` Program #2 revision per VP-1 (FarmAgent-workspace owner applies).
3. **Counsel queue**: D1 contracting structure (existing) + derived-memory/caching (existing) + ezyVet SMS/payment-clause read (new, VP-6) + voice consent/no-training vendor clauses (VP-3/VP-4).
4. **Pilot instrumentation** is the evidence spine: containment, booking, escalation, slot-recovery, staff-hours, diagnostics-utilization (the IDEXX shield number), utilization telemetry — wired from VP-1 day 1.

## Next Lifecycle Steps

Per the mandatory sequence: **VP-3 and VP-4 → `speckit-discover` now** (VP-2 is already at specify). VP-1 inherits Program #2's existing artifacts + a delta-discovery for cycle 1c. Everything else queues per sequencing. No step skipping without Matt's explicit instruction.
