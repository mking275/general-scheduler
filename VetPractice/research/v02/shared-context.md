# Shared Context — VetAgent V0.2 Research (read first)

You are one of five analysts researching inputs for **VetAgent V0.2** — the next product version, defined via a product-level "UberSpeckit" run. Date: 2026-07-09. Reach your own conclusions; cite sources with URLs; distinguish verified fact from inference.

## What VetAgent is (current state)
AI-native veterinary practice operations built on the COS-platform pattern: **Vera, the practice's AI Chief of Staff** (KNOW/ADVISE — the vet DECIDES; architecturally cannot prescribe/diagnose — "Expert Firewall"). Demo-grade product (FastAPI+Next.js): scheduling, intake/SOAP/follow-up agents, no-show risk, waitlist fill, conversational onboarding. Strategy: **the envelope** — Vera wraps the incumbent PIMS (ezyVet first) rather than replacing it day-1; data via customer-rights exports + vendor automated reports + vision-guided "human API" + partner API last. Pilot: Dr. Goldsmith's 23-clinic group (ezyVet), kickoff ~Aug 2026. Goldsmith is also a strategic partner: prior multi-hundred-clinic exit, ambition to take VetAgent to the biggest operators, eventual IDEXX transaction.

## V0.2 feature inputs (from Goldsmith feedback + phase-4 design)
F1 customer-facing **voice** (phone→Vera: scheduling + emergency routing; after-hours first) · F2 **procurement** with real price-comparison shopping · F3 **worker/shift scheduling** · F4 **financial integrations + business advice** · F5 **operational efficiency advice** · F6 **enterprise hierarchy for 400-clinic and 11,000-clinic operators** (org-tree tenancy, hierarchical Vera, mixed-PIMS estates). Core/vertical split: reusable engine = Vera-core (separate stream); vet domain packs/adapters = VetAgent.

## Key local files (read as needed; modify nothing)
- `~/SMB_Hunt/General_Scheduler/VetPractice/design/phase4-goldsmith-feedback-design.md` — F1–F6 + R1–R9 design brief
- `~/SMB_Hunt/General_Scheduler/StrategicStudy/envelope-strategy-board-2026-07-07.md` — strategy + 6 research appendices (competitive facts as of Jul 7: ezyVet ToS verified, IDEXX 79% diagnostics, Vello, AI-Assisted Notes beta, VC-9 "agentic layer ❌ on 7 of 8 PIMS")
- `~/SMB_Hunt/General_Scheduler/marketing/engine-inputs/verified-claims.md` — the claim corpus (VC-1 displacement wave, VC-2 stack costs…)
- `~/SMB_Hunt/General_Scheduler/marketing/VetAgent_vs_ezyVet_Report_DrGoldsmith.pdf` context: 74 ezyVet integrations; 6 that matter (VetConnect, Stripe, Xero, Trupanion, Vetcove, DICOM)
- `~/ModelGarden/research/vera-architecture/` — the Vera Program (core architecture; esp. 08-uber-speckit-jobs.md for the UberSpeckit form)

## Rules
- Web research expected — load WebSearch/WebFetch via ToolSearch. It is mid-2026: search for CURRENT facts; our competitive corpus is from June–July 7, 2026 — find what's changed.
- Voice: concrete, numeric, never hype.
- Write your COMPLETE analysis to the output file named in your task prompt. End with: **Key Risks**, **Implications for V0.2** (specific, actionable — these feed program definitions), **Open Questions**, and **Where I expect other lanes disagree**.
- Return ONLY a tight summary per your task prompt.
