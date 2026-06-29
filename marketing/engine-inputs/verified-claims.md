# Verified-Claims Corpus — VetAgent (VPMA)

> The claim-check "type system" source for VetAgent assets (FR-3). Every checkable claim in an asset must trace here. **Status:** VERIFIED (sourced fact) · PENDING (proposed/not-yet-true) · PRODUCT-CLAIM (a promise about VetAgent — true only if the product delivers; must be product-truth-validated before publish). Sources: `../vpma_marketing_strategy.md` (cites the **VPMA Stack Cost Model, June 2026** and **CI reports across 8 PIMS platforms**), `../vpma_communication_guide.md`. Locale: en.

| ID | Claim | Status | Source |
|---|---|---|---|
| **VC-1** | The biggest PIMS displacement wave in decades: **Cornerstone (~14,000 installs) has no cloud roadmap; Avimark (~11,000) is in active sunset** (Covetrus migrating users to Pulse); **25,000+ practices** will be forced to evaluate cloud alternatives over 36–60 months. | **VERIFIED** | strategy §1 / CI reports |
| **VC-2** | The average independent 3-vet practice subscribes to **5–8 separate tools** and spends **~$2,100/month (range $1,548–$2,748)** across them — tools that don't reliably sync. | **VERIFIED** | VPMA Stack Cost Model |
| **VC-3** | VetAgent Professional + key modules replaces that stack for **~$695/month** → **~$1,405/month ($16,860/year) savings** for a typical 3-vet practice. | **PRODUCT-CLAIM** ⚠️ | Stack Cost Model — *VetAgent's own pricing; validate pricing/modules are live before claiming* |
| **VC-4** | A human Practice Administrator / Chief of Staff at Vera's scope costs **$100,000–$200,000/year all-in**; Vera is **~$695/month (~$8,340/year)** — a 12–24× difference. | **VERIFIED** (salary) / **PRODUCT-CLAIM** (Vera price) | strategy §4 Layer-1b |
| **VC-5** | Owner-vets routinely **chart after hours / until midnight** and run the business they were never trained for (50–60 hr weeks). | **VERIFIED** (ICP research) | strategy §2 psychographic |
| **VC-6** | Staff spend **6+ hours/week manually bridging systems** ("copying data between systems"). | **VERIFIED** | Reddit r/VetTech quote, cited in strategy §1 |
| **VC-7** | Purchase triggers: **Avimark sunset notice, PetDesk/VitusVet renewal, server crash, new-practice opening, staff burnout, conference evaluation.** | **VERIFIED** | strategy §2 trigger table |
| **VC-8** | Vera **acts, not just records**: messages owners pre-visit + briefs the vet; **fills a cancelled slot from the waitlist (typically <4 min)**; drafts the discharge from the signed SOAP for one-click approval; flags at-risk/overdue patients. | **PRODUCT-CLAIM** ⚠️ | strategy §4 Layer-2 — *must be product-truth-validated; the vet approves all clinical/financial actions* |
| **VC-9** | The **agentic operating layer scores ❌ across 7 of 8** major PIMS platforms (Digitail's Tails Concierge the only entrant, still maturing); Cornerstone scores ❌ on all agentic features. | **VERIFIED** | CI reports across 8 PIMS |
| **VC-10** | VetAgent **gets smarter as you use it** — Vera learns the practice's patients/vets/patterns and that institutional knowledge compounds (a switching moat). | **PRODUCT-CLAIM** | strategy §4 Layer-3 — product promise |
| **VC-11** | Brand-voice rule: **concrete + numeric, never hype** (e.g., "fills your waitlist in under 4 minutes," not "leverages advanced ML"). | **VERIFIED** (guidance) | comms guide §1 |
| **VC-12** | ezyVet per-user pricing (~$260–$300/user/mo) gets expensive for a 3-vet/10-staff practice ($1,500–$2,500/mo PIMS-only); Shepherd's AI is explicitly **"doctor-controlled"** (no autonomous follow-up/waitlist/risk). | **VERIFIED** | CI / Shepherd stated philosophy |

## Usage notes for the claim-check
- **PRODUCT-CLAIMs (VC-3, VC-4 price, VC-8, VC-10)** → flag for **product-truth validation**: VetAgent's pricing must be live and Vera's agentic behaviors must actually work before any asset asserts them. VC-8 is the riskiest (the agentic behaviors are the core promise).
- Brand/voice copy and the persona ("Vera," "Chief of Staff") are exempt from claim-check.
- No PENDING items currently (no pending-law claims in the VetAgent narrative).
