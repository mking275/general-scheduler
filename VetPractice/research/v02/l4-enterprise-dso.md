# Lane 4 — Enterprise Requirements at 400 / 11,000-Clinic Scale + the Dental DSO Analog

Research date: 2026-07-09. Author: Lane 4. All figures dated; verified fact vs. inference marked. Currency: mid-2026.

---

## Executive Summary (≤5 sentences)

A 400-clinic buyer with a hot product in hand will accept a *credible-in-progress* enterprise package — SOC 2 Type II in observation (or Type I + roadmap), SSO/SAML + basic RBAC + audit logs, a completed CAIQ/SIG-Lite, $5M cyber/E&O, and a signable MSA with a fees-based liability cap — because the champion (here, Goldsmith) absorbs risk the procurement function normally guards against; the 11,000-clinic org demands the *completed* checklist plus SCIM auto-provisioning, 7-level org-hierarchy RBAC, contractual uptime SLA with escalating service credits, pen-test attestation, Okta/Entra + ITSM integration, and $10M+ coverage, with security review itself becoming the gating path (78% of enterprise deals slip on it). The dental DSO market is vet's future rendered ~10 years early: three national platforms (Heartland ~1,900–2,500 offices, Aspen ~1,100, PDS ~1,000+) run on purpose-built multi-site cloud PMS, and **Denticon/Planet DDS is the definitive case study** — it won by being architected for org-tree tenancy, template/fee-schedule inheritance, and 60–90-day post-acquisition onboarding from day one, not bolted on. The AI overlays that scaled in dental (Overjet, Pearl) sold *top-down corporate deals off a 3–5 site / 90-day measurable pilot* and won because they proved production/ROI in comparable data; the ones that stalled died in "pilot purgatory" and the "AI graveyard" — clunky integration, no adoption plan, per-seat pricing mismatch, and pilots that produced no decision-grade data. The three transferable lessons for VetAgent F6: (1) build org-tree tenancy + policy inheritance as core architecture, not a later feature; (2) win the enterprise via a measurable multi-site pilot that produces a defensible go/no-go number, then land-and-expand top-down; (3) change-management/adoption engineering is the real product — the tool that staff won't use delivers zero value regardless of integration quality.

---

## HALF A — Enterprise Readiness for Health-Services Buyers

### A1. SOC 2 Type II — realistic timeline & cost from zero (startup, 2026)

**Verified (multiple 2026 sources):**
- **Timeline from zero: ~9 months typical**; full range 6–20 months, driven by the mandatory **observation window (6–12 months)** before an auditor can test controls over time. You cannot compress the observation period — it is calendar time, not effort.
- **First-year all-in cost: $25k–$80k** for a 10–50-person startup. Component breakdown (with a compliance-automation platform, which is now standard):
  - Compliance automation platform (Vanta/Drata/Sprinto-class): $8k–$15k
  - Auditor (Type II): $15k–$35k (specialist range $15k–$75k)
  - Penetration test: $5k–$15k
  - Security tooling: $3k–$10k
  - Plus internal staff time (the real hidden cost)
- **Ongoing maintenance: ~40% of initial** = $10k–$40k/yr.
- **Go straight to Type II, skip Type I.** ~85% of mid-market and ~98% of Fortune-500 buyers require Type II; doing Type I first usually means paying twice. (Caveat: Type I can be a useful *interim artifact* to unblock a champion-led deal while the Type II window runs — see minimum-viable package below.)

**Implication:** Because of the immovable observation window, VetAgent must **start the SOC 2 clock now** if it wants Type II available for the 11k-tier conversations that follow the 400-clinic pilot. A Goldsmith pilot (Aug 2026) can proceed on Type I + "in observation," but the 11k org will want the completed Type II report in hand.

### A2. Vendor security questionnaires (CAIQ / SIG)

- **CAIQ v4** (Cloud Security Alliance): ~260 questions, 17 control domains, aligned to the CSA Cloud Controls Matrix.
- **SIG** (Shared Assessments): the other dominant standard; comes in SIG-Lite (screening) and SIG-Core (full).
- **VSA / custom internal questionnaires** also common at large orgs.
- **Hard blockers that stall deals (2026):** SOC 2 Type II and SSO are the two most consistent "deal-doesn't-move-without-it" items; SCIM and audit-log retention close behind.
- **78% of companies report security reviews caused deal delays in the past year.** The questionnaire *is* the sales cycle at enterprise scale.

**Implication:** Maintain a **Trust Center** (pre-answered CAIQ + SIG-Lite, SOC 2 report under NDA, pen-test summary, subprocessor list, BAA-equivalent DPA). This converts a 6-week questionnaire drag into a link.

### A3. SSO / SCIM / RBAC / audit logging

- **Correct build order (enterprise identity stack): RBAC → audit logs → organizations → SCIM.** RBAC first because everything depends on roles; audit logs second because every enterprise customer asks. This is the recognized "enterprise tier" baseline.
- **SSO: SAML 2.0 + OIDC.** Model each tenant as a per-organization SSO connection; customer IdP admin uploads metadata. Managed auth (WorkOS/Clerk/Auth0-class) exposes SAML as a first-class primitive — fastest production path.
- **SCIM (Directory Sync):** automated provisioning + **deprovisioning that propagates immediately** (not at next login). Should work on both SAML and OIDC configs.
- **RBAC at enterprise scale = multi-level** (one source cites "7-level RBAC"); IdP group memberships map to internal teams/roles. **This is the direct technical analog to F6's org-tree tenancy.**
- **Audit logs: retain ≥12 months** (longer for regulated); log every create/update/deactivate. Enterprise buyers ask for retention terms explicitly.
- **IdP support:** Okta + Microsoft Entra ID are the must-haves.

### A4. Uptime SLA & penalties

- **Typical commitment: 99.5%–99.9%.** 99.9% = ~43m 49s downtime/month, ~8h 45m/year.
- **Escalating service credits (standard):** ~10% of monthly fees for 99.0–99.9%; ~25% for 95.0–99.0%; 50–100% below 95%.
- Service credits are framed as **fee adjustments** (low legal risk) — the vendor's preferred remedy vs. hard penalties/termination rights.

### A5. Contract / MSA realities

- **Liability cap:** industry standard = **fees paid in the preceding 12 months.** This is the anchor; enterprises push for multiples (2–3x) or super-caps for data-breach.
- **Non-negotiable carve-outs from the cap:** confidentiality breach, indemnification (IP infringement + data breach from vendor security failure), gross negligence / willful misconduct.
- **Indemnification:** vendor indemnifies for IP infringement, data breaches caused by vendor security failures, and legal violations.
- **First-draft numbers are not final:** documented Fortune-500 deals opened at $20M/$20M insurance and $20M liability and settled at $5M/$5M. Everything is negotiable; the opening ask is theater.

### A6. Insurance requirements

- **Enterprise baseline: $5M per claim / $5M aggregate** for both **Tech E&O and Cyber Liability**; large enterprises mandate **$5M–$10M**.
- Also commonly required: General Liability and Hired & Non-Owned Auto at $1M–$5M, with **customer named as Additional Insured.**
- Underwriters weight the **customer contract's indemnification language** as the single biggest factor — i.e., a punishing MSA raises your premium.

### A7. Data residency / privacy for vet (no HIPAA, but real obligations)

- **HIPAA does not apply** — animals are not "persons," pet records aren't PHI. This is a genuine relief vs. human-health SaaS.
- **BUT:** **35 states have veterinary confidentiality statutes** (CA, FL, GA, KY, …) restricting disclosure without client consent + governing retention/release.
- **Client PII triggers CCPA/CPRA** (CA) and equivalent state privacy laws; **all 50 states have breach-notification laws** (name + license/financial data).
- Enterprise vet buyers will still demand a **DPA (data-processing agreement)** — the BAA-equivalent — covering data location, subprocessors, breach duties.

**Implication:** VetAgent gets to skip HIPAA/BAA machinery (a real cost/speed advantage over human-health analogs) but must still ship a **DPA + state-privacy posture + breach-notification readiness.** Position "no-HIPAA" as a speed advantage, not an absence of obligation.

### A8. Enterprise rollout playbook (multi-hundred-site)

- **Deployment models:** big-bang / phased-by-region / pilot-first. Enterprise health-services = pilot-first then wave.
- **Pilot design: pick 3 sites — one easy, one hard, one median.** Don't scale until 3 are live and *measured*.
- **Waves: cohorts of 10–20 sites, 6–8 weeks apart** (some say 10–15/wave with overlap). Fixed cadence matters more than wave size; success stories compound.
- **Governance:** central PMO + site-level leads who localize while preserving consistency.
- **Go-live is the midpoint, not the finish** — sustained value depends on post-live refinement.

### A9. Minimum-Viable Enterprise Readiness — 400-clinic tier vs. 11,000-tier delta

**400-CLINIC TIER (champion-led / "hot product" minimum viable):**
A 400-clinic buyer with an internal champion (Goldsmith archetype) accepts a *credible-in-progress* posture:
1. **SOC 2 Type II in observation** (Type I report already issued) + written roadmap to Type II report date.
2. **SSO (SAML 2.0)** + basic **RBAC** (org/location/role) + **audit logs (12-mo retention).**
3. **Completed CAIQ or SIG-Lite** + a Trust Center / security one-pager.
4. **Pen test done once** (summary letter available).
5. **Cyber + Tech E&O at $5M/$5M.**
6. **Signable MSA** with fees-based (12-mo) liability cap + standard carve-outs; **DPA** covering data location + breach duties.
7. **Uptime target stated** (99.5–99.9%) even if not yet contractually credited.
8. **Pilot-first rollout** (3 sites: easy/hard/median) with a measurable success metric.
9. Okta/Entra SSO connection working; SCIM "on roadmap" tolerated.

**11,000-CLINIC TIER — the DELTA (what the mega-org additionally demands):**
- **Completed SOC 2 Type II report** (not "in observation") — and often **HITRUST or ISO 27001** on top (Overjet markets HITRUST as a DSO differentiator; the vet analog will follow).
- **SCIM auto-provisioning/deprovisioning** — not optional; lifecycle automation is mandatory at this headcount.
- **Multi-level (org-tree / "7-level") RBAC + policy inheritance** matching their corporate hierarchy — this is F6.
- **Contractual uptime SLA with escalating service credits** (not just a target) + published status page + incident-response SLAs.
- **Annual pen test** (recurring, with remediation attestation) + continuous vulnerability scanning evidence.
- **Full SIG-Core** (not Lite) + custom questionnaire + possible on-site/vendor-risk audit.
- **Insurance $10M+**, customer as Additional Insured.
- **MSA negotiation with legal on both sides:** liability multiples/super-caps for data breach, source-code escrow possibly, business-continuity/DR plan, right-to-audit clause.
- **Enterprise identity + ITSM integration:** Okta/Entra provisioning at scale, plus **ServiceNow/ITSM** integration for ticketing/incident handoff.
- **Wave rollout program:** central PMO, per-site go-live model, train-the-trainer at scale, cohort cadence (10–20 sites/6–8 wks), documented change-management framework, per-site onboarding budget line.
- **Dedicated named CSM / TAM + executive sponsor cadence + quarterly business reviews.**

**One-line framing:** *400-clinic = "credible and in-progress, backed by a champion who absorbs risk." 11,000-clinic = "completed, contractual, and audited — the procurement/security function is the buyer, and it gates the deal."*

---

## HALF B — The Dental Service Organization (DSO) Analog

Dental consolidated earlier and harder than vet; it is a live preview of vet's org-tree future.

### B1. DSO landscape 2026 (verified figures, ranges where sources differ)

- **Heartland Dental** (KKR + Ontario Teachers') — largest platform, **~1,900–2,500 supported offices** (sources vary; ~2,500 "supported," ~1,900 recent count).
- **Aspen Dental / The Aspen Group** (Leonard Green + Ares) — **~1,000–1,100 offices.**
- **Pacific Dental Services (PDS)** — **1,000+ offices.**
- Three national platforms together support **~15% of US dentists.**
- **Deep mid-market:** MB2 Dental (Charlesbank + Warburg Pincus, ~600 partnerships), Smile Brands (New Mountain, ~700 practices/75 brands), Mortenson (Audax + Genstar), Dental Care Alliance (Quad-C), Sage Dental (Carousel), + 15 more PE-backed regional/specialty platforms.
- **Pattern to note:** heavy PE ownership → relentless roll-up → mixed software estates from acquisition → strong demand for standardization tooling. This is exactly the vet trajectory (IDEXX/consolidators).

### B2. PMS software serving DSOs at scale

- **Denticon (Planet DDS)** — THE multi-site cloud case study. Launched **2003** (a decade ahead of cloud competitors), **purpose-built for DSOs**, ~13,000 practices, clients incl. Park Dental, Smile Brands, D4C, Dental Care Alliance. Best fit 5–200+ locations.
- **Dentrix Ascend (Henry Schein One)** — cloud, best 2–20 locations; **Dentrix Enterprise** (on-prem) for 20+ with complex insurance hierarchies, consolidated cross-entity P&L, legacy HL7/lab integrations.
- **CareStack** — enterprise DSO cloud, $400–600/mo/location, 6–12 wk implementation.
- **Curve Dental** — cloud, commonly evaluated for DSO migration.
- **tab32** — cloud-native, smaller groups; **Oryx** — emerging DSOs, FDA-certified built-in imaging; **Archy** — newer cloud-native challenger.

### B3. How DSO-grade software handles hierarchy / inheritance / mixed estates / migration waves

**Org hierarchy + policy inheritance (Denticon is the reference model):**
- Fee schedules assignable at **four levels**: every provider/every location (org-wide) → every provider/specific office → specific provider/every location → specific provider/specific office. **This is central-policy/local-execution in production.**
- Define appointment types, fee schedules, scheduling rules, provider templates **once, apply across every location; new clinics inherit the playbook automatically.** (Literal template inheritance down the org tree.)
- Centralized real-time reporting drills across locations (production, new patients, aging AR, collections).

**Mixed estates + migration waves:**
- A DSO migration = **N simultaneous migrations** with shared infra + cross-location patient records + zero-disruption expectation — fundamentally different from single-practice.
- Goal of migration is to **reduce variance between locations** so training/reporting/patient-experience don't depend on local workarounds.
- **Decoupling insight (key for F6):** acquired practices can join the *centralized scheduling/ops layer within 60–90 days* even when the *PMS migration is a year+ away.* → **The ops/AI layer onboards faster than the system-of-record swap.** This is exactly VetAgent's "envelope" thesis — wrap first, migrate later.
- DSOs should carry a **per-location onboarding budget line** (assessment/remediation/standardization/go-live) as a cost of acquisition.

### B4. AI overlays in dental — winners, how they sold, what killed the losers

**Winners (imaging/clinical AI):**
- **Overjet** — 10 FDA-cleared modules, dual provider+payer platform, **HITRUST-certified**, strongest DSO fit. Sold **top-down corporate deals** off pilots: Dental Care Alliance (pilot → **370–400+ practices, 21 states**); **North American Dental Group — Overjet Voice across all 216 locations** (first enterprise DSO full-scale clinical Voice AI rollout, Jan 2026); Great Lakes Dental Partners; Mortenson IRIS across **147 locations / 9 states**. **Acquired DentalBee** (voice clinical documentation) to add the voice/scribe layer — consolidation, not a failure.
- **Pearl** — 7 FDA-cleared modules; Second Opinion ~$349/mo (third-party listing), volume pricing for larger orgs; DSO deals with **Sage Dental** and **Risas Dental (all 27 locations).**
- **VideaHealth (now "Videa")** — 90,000+ clinicians; rebranded and expanded to private practice. Thriving.
- **Arini** — YC-backed dental voice AI receptionist; "hundreds of DSOs/groups"; 300ms answer, books into Open Dental/Eaglesoft/Denticon/Dentrix, 24/7, HIPAA-compliant; case-study ROI claims 25x–72x first-year. Directly analogous to VetAgent F1 (customer-facing voice).

**Go-to-market mechanics (verified):**
- Enterprise DSO sales = **field execs + C-suite calls + corporate-IT pilots running 12–24 months.**
- **Pilots = 3–5 locations, 90-day measurement window**, then corporate rollout.
- **Pricing:** per-office / per-location or volume-based corporate deals (not pure per-seat at scale). Custom-quoted by size/location count/modules.

**What killed / stalled the losers (the "AI graveyard"):**
- **"Pilot purgatory":** most DSO tech pilots fail because **nobody designed them to produce comparable data** → no defensible go/no-go → CFO kills the spend.
- **"AI graveyard":** software bought on enthusiasm, abandoned via poor implementation, failed training, low adoption, clunky integration — *while the subscription keeps billing.* "Charismatic salespeople win the room; the product never fits the problem."
- **Change management, not tech, is the failure mode.** Providers who don't see immediate workflow benefit opt out quietly, location by location, until utilization hits ~40% unreported. Six months post-acquisition the same software runs 3 different ways across locations.
- **Integration/data-security barriers** hinder ~32% of PMS-market adoption.
- Note on consolidation: dental AI is mostly consolidating via **acquisition** (DentalBee→Overjet) rather than dramatic public shutdowns — the "failure" mode is quiet abandonment inside accounts, not company death.

### B5. Best DSO-software case study (one paragraph)

**Denticon / Planet DDS** is the single most instructive precedent for VetAgent F6. Launched in 2003 as the first cloud-enabled dental PMS — a full decade before cloud competitors — it made an architectural bet that the buyer of the future was the *multi-location organization*, not the solo practice, and built org-tree tenancy, hierarchical policy/fee-schedule inheritance (assignable at four levels from org-wide down to a single provider in a single office), define-once-apply-everywhere templates that new clinics inherit automatically, and consolidated cross-location real-time reporting as *core primitives* rather than later bolt-ons. That head start compounded into ~13,000 practices and marquee DSO logos (Smile Brands, Park Dental, D4C, Dental Care Alliance). The transferable lesson is not a feature list but a sequencing decision: because central-policy/local-execution was in the data model from day one, Denticon could absorb acquired mixed estates and stand up standardized workflows quickly — even decoupling the centralized ops layer (live in 60–90 days) from the slower system-of-record migration. VetAgent's "envelope" strategy is the same move one layer up: win the org-tree and the standardization layer first, let the PIMS swap come later.

### B6. The 3 strongest DSO lessons for V0.2

1. **Org-tree tenancy + policy inheritance must be core architecture, not a bolt-on (F6).** Denticon's durable moat is that hierarchy and 4-level inheritance were in the data model from 2003. VetAgent should model tenancy as a tree (org → region → clinic → provider) with policy/briefing/config inheritance and local override *now*, before scale forces a rewrite. This is also the exact technical shape of enterprise RBAC ("7-level") that the 11k-tier procurement will demand — one architecture serves both product and security requirements.

2. **Win the enterprise via a measurable multi-site pilot that produces a defensible number, then land-and-expand top-down.** Every dental AI winner ran the same play: 3–5 site / 90-day pilot instrumented to produce comparable cross-site data → corporate C-suite decision → full rollout in waves (Overjet: pilot → 216/370/147-site rollouts). Every loser died in "pilot purgatory" because the pilot produced no decision-grade metric. VetAgent's Goldsmith 23-clinic pilot must be designed *from the start* to output a go/no-go number (no-show reduction, waitlist-fill revenue, hours saved) that a CFO can act on — and the ops/AI layer can go live in 60–90 days ahead of any PIMS migration (the envelope thesis, confirmed by DSO practice).

3. **Change-management/adoption engineering is the real product; the tool staff won't use is worth zero.** The "AI graveyard" is full of well-integrated software that failed on adoption — quiet opt-out to ~40% utilization, 3 different workflows per location. VetAgent must ship an adoption program (train-the-trainer, per-site go-live model, utilization telemetry surfaced to corporate, central PMO cadence) as a first-class deliverable, and price/rollout per-location (not per-seat) to match how DSOs buy. Vera's KNOW/ADVISE framing helps here — an advisory COS that reduces clinician clicks is more adoptable than one that adds workflow burden.

---

## Key Risks

- **SOC 2 observation window is calendar-time and cannot be compressed** — if the clock isn't started well before the 11k-tier conversations, it becomes a hard deal-blocker. Start now.
- **Mixed-PIMS estates at 400/11k scale** mean F6 must handle heterogeneous systems-of-record (ezyVet + others) simultaneously — far harder than Denticon's single-PMS world. VetAgent's envelope/adapter layer is doing something Denticon never had to.
- **"AI graveyard" risk is existential for an advisory product** — Vera is closer to an overlay than a system-of-record, so it is *more* abandonable than a PMS. Adoption telemetry + demonstrated ROI are survival, not nice-to-have.
- **Champion dependency:** the 400-clinic deal rides on Goldsmith; the 11k deal will not have a champion who waives procurement. The readiness gap between the two tiers is where deals die.
- **Insurance + liability exposure of an AI that advises on operations/finance** (F4/F5) — even with the Expert Firewall, an AI giving business/financial advice raises E&O underwriting scrutiny and MSA indemnification pressure.

## Implications for V0.2 (actionable, feeds program definitions)

- **F6 tenancy = tree with inheritance + override, modeled now.** Org → region → clinic → provider; policies, briefings, config, and RBAC roles inherit down with local override. Deliberately mirror Denticon's 4-level fee-schedule model and enterprise "7-level RBAC" so one architecture satisfies both product hierarchy and enterprise-identity procurement.
- **Enterprise-identity stack in build order RBAC → audit logs → orgs → SCIM.** SAML+OIDC SSO with Okta/Entra; 12-month audit-log retention; SCIM for the 11k tier. Consider a managed-auth provider (WorkOS-class) to ship SAML fast.
- **Start SOC 2 Type II clock immediately**; issue Type I as the interim artifact for the Goldsmith-tier deal; stand up a Trust Center with pre-answered CAIQ + SIG-Lite. Plan HITRUST/ISO 27001 as the 11k-tier upgrade (Overjet precedent).
- **Instrument the Goldsmith pilot to emit a CFO-grade go/no-go metric** across the 23 clinics from day one; treat the ops/AI layer as go-live in 60–90 days decoupled from PIMS migration.
- **Ship an adoption/change-management program as a product deliverable** (train-the-trainer, per-site go-live playbook, utilization telemetry to corporate, central PMO cadence) and **price per-location, not per-seat.**
- **Legal/insurance readiness package:** signable MSA (12-mo fees liability cap + standard carve-outs), DPA for state-vet-privacy + CCPA + breach notification, $5M cyber/E&O for the 400 tier scaling to $10M+ for 11k.
- **Rollout model:** pilot 3 sites (easy/hard/median) → waves of 10–20 sites at 6–8 wk cadence, central PMO + site leads.

## Open Questions

- Does Goldsmith's 23-clinic group have an existing IdP (Okta/Entra), or will VetAgent need to support the messy no-SSO reality of smaller vet groups until the 11k tier?
- At the 11k tier, will VetAgent need **ServiceNow/ITSM integration** for incident/ticket handoff, and is that in F6 scope or a separate enterprise program?
- What is the vet-market equivalent of HITRUST — does any vet-specific certification carry procurement weight, or is generic SOC 2 + ISO the ceiling?
- How does the mixed-PIMS estate reality change the pilot metric? (Denticon standardized on one PMS; VetAgent must show cross-PIMS value.)
- Per-location pricing at 11,000 clinics: what corporate/volume discount curve is realistic, and does the advisory-COS value justify per-location vs. usage-based?

## Where I expect other lanes disagree

- **vs. a competitive/PIMS lane:** I treat the "envelope / wrap-first, migrate-later" thesis as *validated by DSO practice* (Denticon's 60–90-day ops layer vs. year+ PMS migration). A PIMS-focused lane may argue the system-of-record is the only durable moat and an overlay is structurally abandonable ("AI graveyard") — that tension is real and I flag adoption telemetry as the mitigation, not a resolution.
- **vs. a go-to-market/pricing lane:** I argue per-location corporate pricing (dental precedent). A GTM lane focused on land-and-expand SMB motion may favor per-seat/usage pricing that scales bottoms-up — these collide at the 400→11k transition.
- **vs. a product-scope lane:** I push SOC 2 / SCIM / MSA / insurance as *near-term* investments driven by the 11k ambition. A lane optimizing for the Aug-2026 Goldsmith pilot may argue this is premature over-building — the champion-led 400-tier accepts a lighter package, and burning runway on 11k-grade compliance before product-market fit is a real risk. My position: start only the *calendar-bound* item (SOC 2 clock) early; defer the rest to just-in-time.
- **vs. an AI-capability lane:** I emphasize change-management/adoption as the decisive factor over raw model capability. A lane bullish on agentic/voice capability may argue superior AI drives adoption on its own — dental evidence says otherwise (great tools died on adoption).

---

## Sources

SOC 2 / compliance: sprinto.com/blog/soc-2-compliance-cost; humanr.ai/intelligence/soc-2-type-2-cost-benchmarks-timeline-120k; complyjet.com/blog/soc-2-for-startups; soc2auditors.org/soc-2-audit-cost
Security questionnaires / identity: securityboulevard.com/2026/04/9-critical-security-questionnaire-items-that-stall-enterprise-saas-deals; blog.getagency.com/articles/security-questionnaires-caiq-sig-vsa; hashorn.com/blog/enterprise-ready-saas-sso-scim-audit-logs; revian.ai/blog/enterprise-crm-sso-scim-rbac; ssojet.com/blog/critical-audit-log-events-b2b-saas-enterprise; workos.com/blog/best-scim-providers-for-automated-user-provisioning-in-2026
SLA / MSA / insurance: finbergfirm.com/2026/04/01/key-clauses-in-tech-service-level-agreements-sla-for-2026; toslawyer.com/saas-sla-agreement-uptime-penalty-clauses; promise.legal/startup-legal-guide/contracts/saas-agreements; altonrisk.io/blog/enterprise-contract-insurance-requirements; joinalliancerisk.com/startup-insurance-enterprise-contracts
Vet privacy: accountablehq.com/post/hipaa-compliance-for-veterinary-practices; co.vet/post/veterinary-medical-records-laws; mahanlaw.com/practice-areas/veterinary-practice-consulting/data-privacy-and-security-in-veterinary-practices
Rollout: jdhc.us/blog/managing-multi-site-healthcare-system-implementations; tec-tel.com/use-cases/multi-site-rollout-playbook
DSO landscape: ctacquisitions.com/dental-dso-pe-rollup-tracker-2026; medixdental.com/largest-dsos-in-the-us; beckersdental.com/dso-dpms/the-largest-dsos-headed-into-2026
DSO PMS: planetdds.com; themolarreport.com/reviews/denticon; support.planetdds.com/hc/en-us/articles/115002085472; planetdds.com/blog/most-powerful-denticon-features-for-dsos; ustechautomations.com/resources/blog/dental-medspa-dentrix-ascend-vs-enterprise-for-multi-location-2026; ekimit.com/cloud-migration-dso-dental-software; carestack.com; oryxdental.com
Dental AI: overjet.com/blog/overjet-vs-pearl-dental-ai-software; overjet.com/blog/north-american-dental-group-to-implement-overjet-voice-across-216-locations; drbicuspid.com (Dental Care Alliance, Great Lakes deals); hellopearl.com; arini.ai; videa.ai; ohiotechnews.com/dentalbee-acquired-overjet
Failure modes: groupdentistrynow.com/dso-group-blog/dental-cyber-watch-live-2 (AI graveyard); overjet.com/blog/how-to-run-a-dental-ai-pilot; mybcat.com/blog/dso-change-management-centralize-patient-access; medixdental.com/top-3-reasons-emerging-dsos-are-failing-with-their-technology-strategy
