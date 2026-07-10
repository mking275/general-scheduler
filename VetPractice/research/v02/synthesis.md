# VetAgent V0.2 — Research Synthesis

**Date**: 2026-07-09 · **Method**: six lanes (L0 first-hand regulatory/verification + L1 consolidators, L2 integrations, L3 competitors, L4 enterprise/DSO, L5 voice — parallel agents, adversarially briefed), load-bearing claims verified first-hand by the lead. Corpus: this directory. **Feeds**: `VetPractice/design/v02-uberspeckit-programs.md`.

---

## Verdicts on the three research questions

### 1. The 400- and 11,000-clinic use cases
- **"400" = the second-tier PE roll-up** (PetVet ~450, Thrive ~400–500, Alliance ~300, AmeriVet ~230): corporate ops/IT, sponsor margin pressure, **irreducibly mixed PIMS estates** — F6's lead persona, and Goldsmith's prior-exit scale/warm network.
- **"11,000" = the entire US corporate-owned clinic universe** (~30% of ~30k general practices + ~75% of specialty/ER ≈ 9–12k), i.e., the TAM ceiling the architecture must not preclude — not one operator (Mars ≈ 2,100 US, on closed proprietary PetWare/WOOFware).
- **The envelope is mandatory at this tier, from two independent directions**: L1 (no single-PIMS vendor can serve a mixed estate; the vision/"human API" path must be *permanent and first-class* for closed/legacy systems) and L4 (dental's winning play — Denticon — decoupled the ops layer, live in 60–90 days, from year+ system-of-record migrations).
- **Enterprise readiness splits cleanly**: 400-tier accepts credible-in-progress (SOC 2 Type II *in observation*, SIG-Lite, $5M cyber, 3-site pilot); 11k-tier demands the completed audited checklist (Type II done, SCIM, contractual SLAs+credits, PMO wave rollouts). Start only the calendar-bound item now: **the SOC 2 clock**.
- **Dental's deepest lesson**: org-tree tenancy + policy inheritance as *core architecture* (Denticon, from 2003) is simultaneously the product moat and the security-checklist answer; and the "AI graveyard" is quiet in-account abandonment (~40% utilization) — **adoption engineering is the real product**, and pilots must emit a CFO-grade go/no-go number.

### 2. Functional integrations
- **No open rails exist in vet.** Only three categories have public self-serve APIs — comms (Twilio/Telnyx), payments (Stripe), SMB shift-scheduling (Deputy) — and they map exactly onto F1, F4, F3. Everything else is relationship-gated and per-clinic-credentialed.
- **The PIMS record is the hub**: reading already-ingested labs/imaging/claims from the PIMS collapses 8+ gated partner programs into one surface — the envelope pays for itself again.
- **Guided-operator ("human API") is the PRIMARY architecture** — not fallback — for procurement (Vetcove price comparison is portal-only), insurance filing (8 of 9 carriers; Trupanion is the only POS rail), wellness plans, and the Covetrus PIMS tier.
- **Corrections to the July-7 six-integration list**: Stripe ✅, Trupanion ✅ (start the BD clock now), **Xero → QBO** (~80% US share; Xero's Mar-2026 repricing makes it strictly worse), "DICOM" was optimistic (DICOMweb ≈ zero vet adoption; use study links/PDFs via PIMS), Vetcove = human-API-first.
- **The estate forces three adapter species**, not one port: API adapters / on-prem agents (AVImark, Impromed tier) / human-API — different legal + latency envelopes each.

### 3. Competitors
- **VC-9 holds but must be reworded** (action item: update `verified-claims.md`): the autonomous agentic layer is still ❌ across major PIMS (all scribe/summary/suggestion); Digitail is the sole PIMS with a shipping agentic product (now a 3-agent GA suite, human-in-loop, rip-and-replace only). **The real contest is the overlay layer — our slot**: Otto (~5,000 clinics, agentic confirmations), Weave AI Receptionist (dental today, vet-adjacent installed base), **Dodo** (vet-native autonomous voice: hundreds of clinics, writes to 5 PIMS, *sanctioned ezyVet integration partner*, emergency routing shipping today, expanding vet→dental→PT), Scritch, Lupa.
- **Threat ranking**: ① overlay voice/comms broadening front-desk→ops (6–12 mo) — including **GuardianVets' AI relaunch** ($7M Series A Oct-2025; after-hours is a contested beach, and our stack-cost model must stop booking them as merely a displaced line item); ② IDEXX bundling a native agentic layer (12–24 mo; AI-Assisted Notes GA is the shot clock); ③ Digitail/Lupa suites (12–18 mo, rip-and-replace-limited).
- **Chewy acquired Modern Animal** (Apr 8 2026, ~$500M, 18→47 locations): tech-forward operators build, don't buy → target traditional roll-ups (Alliance, AmeriVet, Rarebreed, Mission).
- **Nobody publishes containment or pricing** — the Goldsmith pilot's measured numbers become a marketing asset unique in the category.

## The two theses that survived everything (Matt-confirmed)

1. **Identity continuity is the voice moat**: the same Vera on every call, at the kiosk, behind the briefing — "the receptionists answer calls; **Vera knows the family**." A stateless overlay can only match this by building the whole memory + operating layer. Generates: caller ID+verification, per-audience memory scoping, cross-channel threads, relationship memory as first-class Thoth workload.
2. **Benefits, not feature-parity**: maintain a quarterly table-stakes floor (answer / book / refill-request / route-emergency — all in F1's design); spend every other dollar on the benefit ladder (slots filled, staff-hours returned, missed-call revenue, one bill) and the moats (memory, cross-stack orchestration, hierarchy). Deliberate non-matches are strategy: refills stay draft-for-approval (AAVSB), no per-call gimmicks.

## Regulatory scaffolding (L0, first-hand)

AAVSB whitepaper (Mar 2025) draws our architecture: administrative AI = blessed lane (minimal consent); diagnosis/treatment = the hard line (with unlicensed-practice exposure for tools that *replace* rather than augment); draft-for-approval endorsed verbatim; decision-involvement triggers written-consent → keep triage pure routing, zero assessment language. Voice: first-utterance AI+recording disclosure (Utah floor + all-party states); *PA v. Character Technologies* (May 2026): behavior over disclaimers. Liability lands on the facility → our audit trail is the clinic's defensibility, and enterprise will ask for exactly that.

## Corrections to our own prior documents (action items)

| Doc | Correction |
|---|---|
| Envelope board ("Done/verified" + Appendix D) | "IDEXX ~79% diagnostics revenue" → CAG ≈ **92% of IDEXX's own revenue** (FY25/26 filings); *market* share of vet diagnostics is a different, smaller figure (~45%, imperfectly sourced). Strategic conclusion unchanged — strengthened. |
| `verified-claims.md` VC-9 | Reword per L3 (Digitail 3-agent suite; overlay-layer contest; "no player combines cross-PIMS agentic ops with enterprise hierarchy"). |
| Stack-cost model / VC-2 adjacents | GuardianVets is a **competitor**, not only a displaced line item. |
| Phase-4 brief F2 | MWI–Covetrus merger (Feb 2026) + Covetrus Connect pause → price-comparison premise needs re-shaping; watch item. |
| Integration report (Goldsmith package) | Xero → QBO; DICOM framing; Vetcove access model. Revise before any V0.2-era reuse. |
| L5 note | RECOVER is CPR, not phone triage — protocols anchor on AVMA teletriage + tech-triage CE. |
| ezyVet private-API terms (new find) | Terms reportedly restrict SMS/payment functionality "outside ezyVet's framework" for API partners — **counsel question** for how envelope clinics wire F1/F4 (likely fine via non-API rungs; verify). |

## Top risks for V0.2 (synthesis-level)

1. **Speed in the overlay slot** — Dodo/Otto/GuardianVets are shipping now; our voice differentiation (continuity + operating layer) must demo by pilot Phase 3 or the category narrative sets without us.
2. **VC-8 product truth** — the whitespace argument assumes working agentic ops; if V0.2 ships human-in-loop-only like everyone else, the moat is breadth+enterprise, not autonomy. Be honest in claims.
3. **Adoption abandonment** (dental's graveyard) — telemetry + train-the-trainer + utilization SLOs are product features, not services.
4. **Counterparty drift** — we priced IDEXX risk exquisitely and missed Covetrus consolidating (MWI merger, Connect pause). Watch Mars (Antech + proprietary PIMS) the same way.
5. **Pilot dependency** — nearly every program's evidence chain routes through Goldsmith Phase 2–3 instrumentation; slippage there ripples everywhere.
