# Lane 3 — Market Competitors (mid-2026 refresh)

**Analyst:** Lane 3 · **Date:** 2026-07-09 · **Corpus baseline refreshed against:** June–July 7, 2026 competitive facts
**Scope of "agentic" for scoring:** does the product take real operational actions on the clinic's behalf (book/reschedule, fill waitlists, run follow-up sequences, place orders, refill Rx) *with limited or no per-action human approval* — NOT scribing, summaries, or "suggestions a human must action."

---

## Executive summary

The core of VC-9 holds: as of July 2026 no major PIMS has shipped an autonomous **agentic operating layer** — Shepherd's own 2026 AI feature comparison lists "autonomous actions: none identified" across every PIMS, and the incumbents' AI is still scribe/summary/suggestion (ezyVet AI-Assisted Notes, Covetrus ambient notes + treatment suggestions, Provet summaries, Instinct→ScribbleVet decision support). Two things have changed since the corpus, and both matter: (1) **Digitail broadened** from the single "Tails Concierge" to a **three-agent GA suite** (Concierge / Medical / Practice Manager, 20+ workflows) — still human-in-the-loop, but no longer "one immature entrant"; (2) more importantly, the agentic layer is now being colonized **from the overlay/front-desk direction** — Otto (ex-TeleVet, ~5,000 clinics) is shipping "agentic appointment confirmations," Weave (public, multi-vertical) has an AI Receptionist that books/confirms/backfills by voice+text in early access, and YC-backed **Dodo** runs an autonomous 24/7 voice receptionist that already integrates every major PIMS. That overlay-on-incumbent-PIMS position is *exactly* VetAgent's envelope slot, and it is filling fast. The whitespace for V0.2's full four-way combination (envelope + agentic ops + voice + enterprise hierarchy) is still open, but the near-term competitive squeeze comes from voice/comms overlays broadening into ops, not from the PIMS.

---

## 1. PIMS incumbents — agentic-layer state (July 2026)

Verified vendor-by-vendor. All remain documentation/suggestion tools unless noted.

- **ezyVet (IDEXX).** AI-Assisted Notes (voice→SOAP) rolling from pilot to **GA for US customers now** (still labeled pilot/beta in docs; PM Duncan Crawford). Vello client-engagement layer embedded, "double-digit growth." No autonomous ops. IDEXX is moving up-stack at the *engagement/scribe* layer, not the agentic layer — consistent with the corpus.
- **IDEXX Neo.** Positioned as "simple/easy" cloud PIMS; minimal AI. No agentic features.
- **Covetrus Pulse.** The most orchestration-ambitious incumbent: ambient SOAP, AI pre-visit + visit summaries, **AI treatment suggestions**, **AI Treatment Board updates for team coordination**, markets "end-to-end workflow automation," claims ~6 hrs/week/DVM saved. Still suggestions + updates, not autonomous action. 250+ integrations, built-in pharmacy (vRxPro).
- **Provet Cloud.** AI clinical summaries, auto discharge instructions, SOAP. Notable for **open architecture, scalable API, HL7/FHIR** and multi-site orientation — relevant as an envelope target, but no agentic ops.
- **Shepherd.** Explicitly and deliberately **"doctor-controlled"**: TranscribeAI, SummarizeAI, DiagnoseAI. Philosophy piece "Why Doctor-Controlled AI Matters." Still non-agentic *by design* — unchanged from corpus.
- **Digitail.** **CHANGED.** Now a **three-agent GA suite** — Tails **Concierge** (intake, booking, triage, follow-ups, Rx refills, discharge, proactive check-ins), Tails **Medical** (scribe, charge capture/voice-to-invoice, risk flagging, treatment-plan recs), Tails **Practice Manager** (account setup, analytics, commissions, inventory, coaching) — "20+ AI workflows," "NEW." Serves 10,000+ vets (doubled in a year). $23M Series B (Five Elms, **Nov 10 2025**), ~$37M total. Crucially still human-in-loop: outputs "reviewed, edited, or rejected by your team," "critical decisions always remain with licensed professionals"; **no autonomy rate disclosed.** This is the only PIMS with a real agentic *product*, but it's rip-and-replace (its own PIMS), not an overlay, and it can't serve mixed-PIMS estates.
- **Instinct.** **CHANGED.** Acquired **ScribbleVet on Jan 16, 2026**; building "the industry's first clinical intelligence platform" with Plumb's decision support embedded. 360k+ vet professionals. This is **decision support + scribe**, not agentic ops — but it is the clearest "intelligence-native PIMS" repositioning of 2026.
- **Rhapsody (Petabyte).** Enterprise PIMS + Petabyte Analytics; NVA partner (1,200 hospitals; NVA holds a minority stake) and the "Petabyte Consortium." Enterprise-grade but no agentic AI evident.
- **NaVetor (Patterson).** "AI-powered workflows coming in 2026" — **voice commands** to access data/streamline tasks. Not yet shipped; not agentic.
- **Hippo Manager.** Affordability/simplicity core PIMS; minimal AI.
- **DaySmart Vet.** **Daisy Voice** AI-dictation scribe (pilot). Marketing/engagement focus. No agentic ops.
- **Vetspire.** AI scribe + patient summaries. Documentation-only.

**Read:** Across the 8 "major" PIMS in the corpus, the autonomous agentic operating layer is still **❌ on 7 of 8**, with **Digitail the single partial (🟡) entrant** — now materially more mature (3 agents vs 1). Cornerstone (legacy IDEXX) remains ❌ on all agentic features.

---

## 2. AI-native newcomers & adjacents since the corpus

- **Lupa Pets** — **NEW / notable.** AI-native operating system (PIMS + client app + inpatient tool + note transcription in one). **US$20M Series A (total ~$25M)**, launching a "Veterinary AI Lab" to build practice-wide AI agents. **200+ independent clinics.** European-founded; an AI-native full-stack analog to Digitail, earlier stage.
- **Otto (formerly TeleVet)** — **CHANGED / sharp.** ~5,000 clinics. Free AI Suite (Recap scribe, Memo call transcription, Suggest client-comms drafts) **plus now "releasing AI agentic appointment confirmations built for veterinary clinic workflows."** Deep PIMS integrations (ezyVet, Cornerstone, AVImark, Neo, Impromed). Overlay client-comms platform moving into agentic. ~$43M raised historically.
- **VetRec** — Scribe rolled out to **70% of the VEG emergency network**; also runs a veterinary answering service. Documentation-only.
- **Scribe field** (ScribbleVet [→Instinct], HappyDoc, CoVet, Talkatoo, PawfectNotes, ScribeNote, Vetspire) — pricing ~$40–$450/mo. All documentation-only. **CoVet** won a 2026 Purina Pet Care Innovation Prize. **Talkatoo** is dictation-only (not true ambient/SOAP). Consolidation signal: ScribbleVet absorbed by a PIMS.
- **Vetsource / VetSuccess** — Enterprise data & insights (VetSuccess became Vetsource Data & Insights in 2022); connects Cornerstone, Neo, AVImark, ezyVet; retention/compliance/revenue dashboards + home-delivery. **Analytics, no action.**
- **iVET360** — Analytics/benchmarking + managed services (2026 Benchmark Report: industry +2.6% revenue but declining visit volume; iVET360 clients +6.7%). Analytics/services, no agentic product.
- **PetDesk** — Phones fully merged into Communications (all clinics by end-June 2026); AI call summaries write back to **all major PIMS**, ~85% calls handled real-time. Summaries/unified inbox — not yet autonomous booking.
- **MoeGo** — Grooming/boarding/daycare OS; 36% of reviewers are in veterinary, pushing "next-gen operating system for pet care," multi-location tiers. Adjacent, not a vet-PIMS competitor yet, but an expansion watch-item.

---

## 3. Voice AI marketed to vet clinics *today* (competitor angle only)

(Voice tech/vendor deep-dive is a separate lane — this is the competitor-positioning read.)

- **Dodo (vetdodo, YC-backed, Stanford founders)** — Purpose-built **autonomous voice AI receptionist** for vet + dental; 24/7 calls/texts/emails, FAQs→emergencies, **deep real-time PIMS integration** (records, history, schedule), HIPAA/GDPR/E2E/audit. Claims $60k+/yr/clinic revenue lift, "hundreds of clinics." The most direct competitor to VetAgent F1 (customer-facing voice).
- **Weave AI Receptionist** — Public, multi-vertical (dental/optometry origin). Answers day/night in human-like voice, **completes scheduling, confirmations, and cancellation backfill via voice or text.** Waitlist / early-access (25% off through 2026). From ~$399/mo suite. Distribution + PIMS-agnostic overlay = credible fast-follower.
- **PetDesk Phones** — PIMS-integrated caller context + AI summaries; not (yet) an autonomous booking voice agent.
- **AVA by VetPawer** — AI receptionist for vet (ezyVet-integrated).
- **Horizontal voice-AI with vet verticals** — Famulor (40+ languages, 300+ PMS integrations), plus a long tail (agentzap, kordless, voicefleet, welco, davoice, myaifrontdesk). Slang.ai / Loman.ai did **not** surface as having live vet-specific verticals as of this search — treat as not-yet-in-vet.

**Read:** Front-desk voice is the **most contested and fastest-moving agentic beachhead** in vet right now. Multiple players already do PIMS-agnostic, action-taking voice booking. This is precisely VetAgent's F1 territory and its envelope architecture.

---

## 4. Enterprise / consolidator-serving vendors

- **Petabyte / Rhapsody** — The incumbent enterprise stack for a large consolidator: **NVA (1,200 hospitals)** partner + minority investor; "Petabyte Consortium" for cross-industry build. PIMS + enterprise analytics. **Displace-or-partner target #1** at F6 scale.
- **Vetsource Data & Insights (incl. VetSuccess)** — De-facto enterprise analytics/home-delivery layer across multi-PIMS estates. Partner (data) or displace (action layer).
- **iVET360** — Enterprise benchmarking + managed marketing/ops services. Partner/complement.
- **In-house / proprietary** — Mars (Banfield/BluePearl/VCA) runs proprietary systems; Thrive/others mix. These are build-vs-buy incumbents VetAgent must out-execute or slot beneath.
- **IDEXX (ezyVet + Vello + Neo + Cornerstone)** — The gorilla; owns both the PIMS and the up-stack engagement layer at enterprise scale.

**Whom VetAgent displaces/partners at F6:** *Partner* with the analytics layer (Vetsource/VetSuccess, iVET360 — they see data, don't act); *displace or sit above* the enterprise PIMS-analytics stacks (Petabyte/Rhapsody) by being the cross-PIMS **action** layer over mixed estates — the one thing none of them do.

---

## 5. Positioning read — whitespace, sharpest threat, fast-follower timeline

**Whitespace for V0.2's four-way combination (envelope + agentic ops + voice + enterprise hierarchy):** still genuinely open. Nobody has all four:
- Digitail/Lupa have agentic ops + voice, but **only inside their own PIMS** (rip-and-replace) → can't serve a mixed-PIMS 400/11,000-clinic estate.
- Dodo/Weave/Otto have voice + narrow (front-desk) agentic + PIMS-agnostic overlay, but **no full ops breadth** (no procurement/shift/finance agents) and **no enterprise org-tree hierarchy**.
- Petabyte/Vetsource/iVET360 have **enterprise scale + analytics but no action layer.**

The uncontested slot: a **PIMS-agnostic agentic operating layer that spans the whole ops surface (voice front desk → scheduling → procurement → shift → financial advice), works over mixed-PIMS enterprise estates, with hierarchical tenancy.** That exact stack has no occupant. VetAgent's defensible edge vs the overlay voice players is **ops breadth + F6 enterprise hierarchy + the "Chief of Staff / Expert Firewall" advisory framing**; vs the PIMS players it is **the envelope (no rip-and-replace) + cross-PIMS reach.**

**Sharpest threat to the V0.2 thesis:** the **overlay voice/comms players broadening from front-desk into full ops** (Otto agentic confirmations + Weave AI Receptionist + Dodo). They already occupy VetAgent's identical architectural position (overlay on incumbent PIMS), already ship action-taking voice, already integrate every major PIMS, and already have thousands of clinics of distribution. They need only widen scope — not re-architect. This is sharper *near-term* than the IDEXX bundle because it is happening now and contests the same slot.

**Fast-follower timeline:**
- **Overlay voice→ops broadening: 6–12 months.** Otto is already shipping agentic confirmations; Weave is in early access. Expect scheduling+waitlist+recall automation to generalize across these players within a year.
- **Digitail/Lupa suite deepening + possible down-market/enterprise push: 12–18 months.** Well-funded, iterating fast, but rip-and-replace limits envelope overlap.
- **IDEXX native agentic bundle into ezyVet/Vello (the "Teams move"): 12–24 months, no announcement yet.** Highest severity (fatal per strategy board II.a), lower near-term probability; the shot clock is running via AI-Assisted Notes GA but no agent announced.

---

## Key Risks
- **The envelope slot is being taken from the front desk inward.** VetAgent's differentiation collapses toward "ops breadth + enterprise hierarchy" if Otto/Weave/Dodo add scheduling/procurement/recall autonomy before VetAgent ships F1–F6.
- **Everyone is human-in-the-loop, including Digitail.** If VetAgent is *also* human-in-loop (and the Expert Firewall guarantees it will be for clinical), the agentic differentiation vs Digitail/Otto narrows to breadth and enterprise, not "autonomy." Marketing "agentic" as the wedge is risky when no one autonomously acts and the honest scoreboard is "❌ everywhere."
- **Consolidation is accelerating** (Instinct⊃ScribbleVet; Vetsource⊃VetSuccess): point tools get absorbed into PIMS, shrinking the neutral-overlay runway.
- **Distribution asymmetry:** Otto ~5,000, Digitail 10k+ vets, Instinct 360k professionals, Weave installed base across verticals. VetAgent starts at 23 clinics.

## Implications for V0.2 (actionable — feed to program definitions)
- **F1 (voice) is a red-ocean beachhead, not blue.** Compete on *ops integration depth + enterprise hierarchy + Chief-of-Staff framing*, not "we answer the phone." Consider build-vs-partner on the voice telephony layer (Dodo/Famulor-class as infrastructure) so eng focuses on the ops brain. (Coordinate with the voice lane.)
- **Lead V0.2 positioning with F6 (enterprise hierarchy over mixed-PIMS estates) + ops breadth (F2 procurement, F3 shift, F4 finance).** That is the whitespace no competitor holds; front-desk voice alone is already contested.
- **Reframe the agentic claim honestly:** "the only *cross-PIMS, whole-clinic, enterprise-hierarchy* operating layer," not "the only agentic AI." The scoreboard truth is that everyone is advisory/human-in-loop — align with the Expert Firewall rather than fighting it.
- **Treat Petabyte/Rhapsody and Vetsource/VetSuccess as partner-or-displace targets** in the F6 GTM: partner for data, displace for action.
- **Watch Otto and Weave as the true fast-followers**; watch Instinct's "clinical intelligence platform" as the PIMS most likely to add decision-support-driven actions next.

## Open Questions
- Does Digitail (or Otto) disclose any **true autonomy rate** (% actions taken without approval)? None found — all assert human oversight. Needs primary confirmation.
- Are Weave AI Receptionist / Otto agentic confirmations **actually shipped GA** or waitlist/beta? (Weave = early access; Otto = "releasing.") Materially affects the 6–12 month timeline.
- What are the **enterprise contract lock-ins** at NVA (Petabyte), Mars (proprietary), Thrive? Displacement feasibility at F6 hinges on this.
- Slang.ai / Loman.ai in vet: confirmed absent in search — worth a targeted re-check before ruling out.

## Where I expect other lanes disagree
- **Voice lane:** likely frames Dodo/Weave/Famulor as *vendors/infrastructure* (build-vs-buy for F1); I frame them as *competitors* occupying the envelope slot. Both can be true — the disagreement is whether they're a partner or a threat.
- **Strategy/envelope lane:** their board ranks the **IDEXX native-bundle (II.a) as THE fatal threat**; I downgrade it to #3 by *near-term probability* and elevate the overlay-voice players to the sharpest *near-term* threat. Expect pushback on threat ranking (severity vs immediacy).
- **Pricing/product-truth owner:** my "whitespace is open" rests on VetAgent actually shipping working agentic ops (VC-8, flagged riskiest). If V0.2 ships human-in-loop like everyone else, the differentiation is breadth+enterprise, not autonomy — a lane focused on the product promise may read the moat as thinner.
- **Market-sizing lane:** may treat enterprise/consolidator as greenfield; I argue it's already served by proprietary/consortium software (Petabyte-NVA), so F6 is a displacement fight, not a land grab.

---
### Sources
- ezyVet AI-Assisted Notes / Vello: docs.ezyvet.com; ezyvet.com/ai-assisted-notes; software.idexx.com/vello-ezyvet
- Digitail Tails suite + funding: digitail.com/tails-ai; prnewswire "Digitail Raises $23M USD Series B" (Nov 10 2025); fiveelms.com
- Covetrus Pulse / IDEXX Neo: vetclinictech.com; puppilot.co; capterra.com
- Shepherd AI comparison (agentic = none): shepherd.vet/blog/ai-in-veterinary-software-feature-comparison-for-2026; shepherd.vet/blog/why-doctor-controlled-ai-matters
- Provet Cloud / NaVetor / DaySmart / Hippo: puppilot.co; vetsoftwarehub.com; shepherd.vet 8-best
- Instinct⊃ScribbleVet: prnewswire / instinct.vet/news (Jan 16 2026)
- Rhapsody/Petabyte/NVA: rhapsody.vet; businesswire (Petabyte–NVA); rhapsody.pet consortium
- Vetsource/VetSuccess/iVET360: vetsource.com; veterinaryanalytics.com; ivet360.com/2026-benchmark
- Otto (TeleVet): otto.vet; otto.vet/otto-ai; businesswire (AI Suite); techcrunch (rebrand/$43M)
- Lupa Pets: vettimes.com (US$20M round + Veterinary AI Lab)
- VetRec: techedgeai.com (VEG rollout)
- PetDesk: petdesk.com/blog/one-place-for-all-veterinary-communication
- Voice: vetdodo.com; getweave.com/ai-receptionist; famulor.io; vetpawer.com
- Scribe pricing/CoVet: pawfectnotes.com; happydoc.ai; prnewswire (CoVet Purina prize)
- Agentic-orchestration framing + 83% adoption stat: appstekcorp.com; co.vet; helpsquad.com
