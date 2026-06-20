# Veterinary PIMS Market — Opportunity Analysis

**Research Date:** June 2026 | **Methodology:** Competitive intelligence synthesis across 8 PIMS platforms (Cornerstone, Avimark, ezyVet, Shepherd, Provet Cloud, Covetrus Pulse, Digitail, Vetspire, DaySmart Vet) plus companion stack cost modeling. All claims grounded in sourced review data, pricing documents, and feature matrices. No specific product in development was assumed or evaluated.

---

## 1. Market Context

The veterinary practice management software market serves an estimated 30,000–35,000 companion animal practices in North America, with the independent SMB segment (1–4 DVMs, single location) comprising the majority by count — roughly 60–70% of all practices. The market is undergoing a structural transition: the two dominant platforms (Cornerstone and Avimark) are on-premise Windows applications with a combined installed base exceeding 25,000 practices, and both are architecturally dated. Avimark is in active sunset by Covetrus, and Cornerstone has no cloud roadmap. This creates a massive displacement window — tens of thousands of practices will need to migrate to cloud-native software within the next 3–5 years by force (sunset risk) or by competitive pressure (staff expectations, mobile access, remote capability).

The pricing landscape is fragmented and opaque. Legacy platforms are quote-based with no public pricing. Cloud-native challengers range from DaySmart Vet at ~$116/month (no AI) to ezyVet at ~$260–300/user/month (enterprise-grade). Between them sits a sparse middle: Shepherd at ~$299/month per DVM (unlimited users) and Provet Cloud at $99–$129/vet plus a $249–$299 platform fee. This middle tier is where independent SMB practices shop, and the value proposition gap is real.

Beyond the PIMS subscription itself, a typical independent practice running 2–3 vets pays $1,200–$2,800/month on companion tools: client communications ($300–$500/mo via PetDesk or VitusVet), reputation management ($300–$500/mo via Podium or Birdeye), analytics ($249–$500/mo via Vetsource or iVET360), and after-hours triage ($200–$500/mo via GuardianVets). These tools are universally siloed, poorly integrated with the PIMS, and arrive with annual contracts and price opacity. Total software spend for a mid-size practice frequently exceeds $2,000/month before counting the PIMS itself.

AI is entering the market in a narrow, first-generation form. As of mid-2026, seven of eight platforms have launched or announced AI SOAP note drafting. But the AI story ends there for most. No platform offers autonomous agentic pipelines — the ability to detect patient need, draft outreach, execute follow-up, and optimize schedules without staff intervention. Digitail's "Tails Concierge" is the most agentic product in the market and it is still maturing. The AI ceiling across the entire market is low: ambient transcription is becoming table stakes, but the layer above it — AI that acts on behalf of the practice — is completely unoccupied.

---

## 2. Lens 1 — Pain Frequency Map

### Aggregated Pain Theme Table

| Pain Theme | Vendor Sources | Cross-Vendor? | Severity | Key Evidence |
|---|---|---|---|---|
| **UX complexity / too many clicks** | Cornerstone, ezyVet, Shepherd, Provet Cloud, Covetrus Pulse | ✅ 5+ platforms | 🔴 Workflow Blocker | *"It feels like I'm navigating 5 different tabs just to complete one appointment."* — Reddit r/veterinary (Shepherd); *"Without extensive individual customization it is very clunky and inefficient."* — Capterra (ezyVet); *"The UI is horrible to navigate. Lots of confusing keystrokes."* — Capterra (Cornerstone) |
| **Legacy/no-cloud architecture** | Cornerstone, Avimark | ✅ 2 dominant platforms, ~25K installs | 🔴 Business Risk | *"Cornerstone freezes during busy times. Our server goes down and the whole clinic stops."* — Software Advice; *"It works, but it feels like it was designed in 2005. No mobile, no cloud, no AI."* — Reddit (Avimark) |
| **Zero native AI / automation gap** | Cornerstone (10/10 ❌), Avimark (10/10 ❌), Shepherd (8/10 ❌), Provet Core (4 ❌ + 3 roadmap), DaySmart (least agentic) | ✅ Majority of market | 🟠 Growing blocker | *"We've been told to migrate to Pulse. Avimark is clearly winding down."* — Capterra; All platforms: 0 agentic features except Digitail (partial) |
| **PIMS sync failures with companion tools** | PetDesk/Petvisor, VitusVet, GuardianVets (ALL external comms tools) | ✅ Universal across stack | 🔴 Workflow Blocker | *"PMS sync failures — text logs don't reliably import to patient records."* — Capterra (PetDesk); *"Staff spends 6 hours a week copying data between systems."* — Reddit r/VetTech |
| **Opaque pricing / hidden fees** | PetDesk ($480/mo sticker shock), Podium (auto-renewal), Birdeye, Cornerstone, ezyVet, Avimark | ✅ Market-wide | 🟠 Churn driver | *"We were paying $480/month and didn't realize half the features needed another add-on."* — Capterra (PetDesk); Cornerstone, ezyVet, Avimark, Covetrus Pulse, Vetspire all quote-only |
| **Annual contract lock-in (companion tools)** | Podium, PetDesk, Birdeye, VitusVet | ✅ 4+ companion tools | 🟠 Friction / churn | *"Podium's contract is brutal. We wanted to leave at month 10 and they held us to the full 12 months."* — Gartner |
| **Steep learning curve / new staff onboarding** | Cornerstone, ezyVet, Provet Cloud, Avimark | ✅ 4 platforms | 🟠 Operational cost | *"Switching from Cornerstone to ezyVet was painful but our new grads are so much happier."* — Reddit r/VetTech; *"Moving from Impromed to Provet Cloud was a rough transition."* — Reddit |
| **No native waitlist / AI backfill** | Cornerstone (⚠️ manual), ezyVet (⚠️ no auto-backfill), Shepherd (🔌 Oliver only), Provet (⚠️ basic, roadmap), All Tier 2 (❌) | ✅ 7/8 platforms | 🟠 Revenue leak | All platforms: no AI-powered waitlist backfill as of mid-2026 |
| **No native telemedicine** | Cornerstone (🔌), Avimark (🔌), Shepherd (❌), Provet (🔌), DaySmart (❌), Vetspire (🔌) | ✅ 6/8 platforms | 🟡 Emerging need | Digitail is the only platform with true native telemedicine; all others third-party or absent |
| **No agentic follow-up / autonomous outreach** | Cornerstone (❌), Avimark (❌), ezyVet (❌), Shepherd (❌), Provet (❌), all Tier 2 | ✅ 7/8 platforms | 🔴 Revenue leak | Every platform: follow-up is either manual or rule-triggered; no AI detects need and acts autonomously |
| **Weak/fragmented reporting** | Cornerstone (⚠️ no real-time web dash), Avimark (⚠️ no advanced), Shepherd (⚠️ limited custom), Provet Core (single-site only), Covetrus Pulse (⚠️ poor UX), all Tier 2 custom report = ⚠️ | ✅ 7/8 platforms | 🟠 Decision-making gap | Custom report builder = ⚠️ for ALL four Tier 2 competitors; Cornerstone has no real-time dashboard |
| **Tool sprawl / 5-8 system logins** | Stack costs doc: average mid-size practice uses 7+ tools | ✅ Market-wide structural | 🔴 Staff burnout | *"The true cost of software isn't the subscription. It's the 6 hours a week my staff spends copying data between systems."* — Reddit r/VetTech |
| **No AI patient risk scoring** | Cornerstone (❌), Avimark (❌), Shepherd (❌ — DiagnoseAI advisory only), Provet (❌ manual triage), all Tier 2 | ✅ 7/8 platforms | 🟡 Clinical risk | No platform has automated patient risk scoring |
| **Pet insurance claim friction** | Cornerstone (⚠️ still portal-based), Avimark (🔌), Shepherd (🔌), Provet (✅ best), DaySmart (🔌) | ✅ 5/8 platforms | 🟡 Revenue drag | Only ezyVet and Provet have full direct-pay insurance; majority of market relies on third-party or manual |
| **Payment processing fees above market** | Shepherd Pay (user complaint), Provet Pay (revenue share model) | ✅ 2+ platforms, growing | 🟡 Cost concern | *"Shepherd Pay fees are noticeably higher than what we were paying."* — Reddit |

### Pain Map Analysis

The single most cross-cutting pain in this market is **operational fragmentation**: practices are running 5–8 separate tools with broken sync between them, paying $1,200–$2,800/month in total, and spending 6+ hours/week manually bridging them. This is not a specific product's failure — it is a structural market failure that every platform contributes to by tolerating the external tool ecosystem rather than absorbing it.

The second major pattern is the **UX complexity tax**: every platform above DaySmart Vet generates complaints about multi-tab workflows, excessive clicks, and steep learning curves. This is especially damaging in a market where staff turnover is high (veterinary technician shortage is a documented industry problem) and every new hire must re-learn complex software. The problem is architectural — these platforms were built for power users and never redesigned for modern expectations.

The third pattern is the **AI readiness gap**: legacy platforms have zero AI, and cloud-native challengers have first-generation reactive AI (SOAP transcription) that stops short of autonomous action. The "agentic layer" — AI that monitors practice state, detects opportunities, and takes action — does not exist in any shipping product as of mid-2026.

---

## 3. Lens 2 — Feature Desert Map

### 60-Feature Taxonomy: ❌ and ⚠️ Counts Across All 8 Platforms

For this analysis: ❌ = not available; ⚠️ = partial/weak; 🔌 = requires paid third-party. Both ❌ and 🔌 are counted as market failures (practices must spend separately or go without).

| Feature | ❌ Count | ⚠️ Count | 🔌 Count | Best Market Score | Opportunity Type |
|---|---|---|---|---|---|
| **A01 — AI SOAP drafting** | 2 | 0 | 1 | ✅ Shepherd, Covetrus, Digitail, Vetspire | Becoming table stakes — 5 platforms now have it |
| **A02 — Agentic pre-visit intake** | 7 | 0 | 1 | ❌ (none agentic) | **DESERT** — nobody has it |
| **A03 — Patient risk scoring (automated)** | 7 | 1 | 0 | ⚠️ Provet (triage board, manual) | **DESERT** — ceiling is ⚠️ |
| **A04 — Agentic follow-up** | 7 | 0 | 0 | ❌ | **DESERT** — nobody has it |
| **A05 — AI waitlist backfill** | 7 | 0 | 0 | ❌ (Provet: roadmap) | **DESERT** — nobody has it |
| **A06 — Agentic reminder pipeline** | 2 | 4 | 0 | ⚠️ ezyVet rule-based | Everyone tried, nobody nailed it |
| **A07 — Predictive forecasting** | 7 | 0 | 1 | ❌ | **DESERT** — nobody has it |
| **A08 — Agentic billing from SOAP** | 2 | 4 | 0 | ⚠️ Shepherd, Provet (rule-based) | Everyone tried (rule-based), no AI-agentic |
| **A09 — Agent audit log** | 7 | 0 | 0 | ❌ | **DESERT** — nobody has it |
| **A10 — Modular AI architecture** | 6 | 0 | 0 | 🆕 Provet (3 features) | Early movers only; no composable framework |
| **S04 — Waitlist management** | 0 | 5 | 2 | ⚠️ | Everyone tried, ceiling = ⚠️ |
| **S07 — Online self-scheduling** | 0 | 0 | 3 | ✅ ezyVet, Provet, DaySmart | Strong for cloud-native; legacy lacks native |
| **C02 — AI-assisted SOAP drafting** | 2 | 0 | 1 | ✅ (5 platforms) | Becoming table stakes |
| **C07 — Breed-specific alerts** | 0 | 6 | 0 | ⚠️ | **Ceiling is low** — 6 platforms = ⚠️ |
| **C08 — Patient risk scoring** | 4 | 3 | 0 | ⚠️ | **Ceiling is low** — best score = ⚠️ |
| **C10 — Telemedicine** | 2 | 0 | 5 | ✅ Digitail only | Near-universal dependency on third-party |
| **F05 — Payment plans/financing** | 0 | 2 | 5 | ✅ Shepherd (Sunbit), ezyVet (CC) | 5 platforms third-party; not native for most |
| **F08 — QuickBooks/Xero integration** | 0 | 3 | 2 | ⚠️ Avimark (QB only), Shepherd (QB) | ezyVet has NO native QB; Provet API-only |
| **F09 — Pet insurance claims** | 0 | 2 | 3 | ✅ ezyVet, Provet | Most platforms partial or third-party |
| **L07 — Critical value flags** | 0 | 5 | 0 | ⚠️ | **Ceiling is low** — 5 platforms = ⚠️ |
| **P02 — Payroll integration** | 3 | 3 | 0 | ⚠️ | No vet-specific payroll; SMB uses Gusto/ADP |
| **P06 — Mobile app** | 2 | 3 | 0 | ✅ Provet, DaySmart, Tier 2 | Legacy platforms have none; cloud varies |
| **R03 — Patient retention analytics** | 0 | 4 | 2 | ✅ ezyVet | Most practices rely on third-party tools |
| **R04 — Custom report builder** | 0 | 4 | 0 | ✅ ezyVet, Avimark | All Tier 2 platforms = ⚠️; widespread gap |
| **R06 — AI-driven insights** | 2 | 4 | 0 | ⚠️ | **Ceiling is low** — best = ⚠️ across all |

### Feature Desert Priority (Ranked by Impact)

**Tier 1 Deserts (nobody has it, ❌ across 7+ platforms):**
1. Agentic follow-up (A04) — 7/8 ❌
2. AI waitlist backfill (A05) — 7/8 ❌
3. Agentic pre-visit intake (A02) — 7/8 ❌
4. Predictive forecasting (A07) — 7/8 ❌
5. Agent audit log (A09) — 7/8 ❌

**Tier 2 Deserts (everyone tried, ceiling is ⚠️):**
1. Patient risk scoring (C08/A03) — best score = ⚠️ manual
2. Breed-specific alerts (C07) — 6/8 = ⚠️ workarounds
3. Critical value flags (L07) — 5/8 = ⚠️
4. Custom report builder (R04) — all Tier 2 = ⚠️; AI-driven insights = ⚠️ best
5. Waitlist management (S04) — 5/8 = ⚠️; no automation anywhere

### Adjacent Feature Deserts (Outside 60-Feature Taxonomy)

The stack costs document reveals significant spending on capabilities that exist entirely outside current PIMS — areas where integration quality is universally poor:

| Adjacent Category | Monthly Spend | # Platforms Integrating Natively | Integration Quality | Market Gap |
|---|---|---|---|---|
| **Client communications / texting** | $300–$500/mo | 0 native (all 🔌) | Poor — universal sync failures | Full absorption into PIMS |
| **Reputation / review management** | $300–$500/mo | 0 native | None | High spend, zero native coverage |
| **Business analytics / BI** | $249–$500/mo | 0 native (iVET360 = 🔌) | API-only | Mid-size practices pay separately |
| **After-hours triage / overflow** | $200–$500/mo | 0 native | None (email-only logs) | No PIMS has this natively |
| **Native telemedicine** | Low (~$0 direct) | 1 (Digitail only) | Mostly third-party | Digitail is alone here |
| **Pet financing (BNPL)** | $0 (client-pays) | 2 (Shepherd: Sunbit; ezyVet: CC) | Partial | Underserved outside top 2 |
| **Payroll / HR** | $79–$200/mo | 0 native | None — all third-party | No vet-specific offering exists |

---

## 4. Lens 3 — Segment & Pricing Whitespace

### Segment Coverage Table

| Segment | Platforms Serving Them | Price Range (PIMS only) | Fit Score | Whitespace Assessment |
|---|---|---|---|---|
| **Solo (1 DVM, 1 location)** | DaySmart Vet, Shepherd (pricing fits), Provet Core | $116–$299/mo | 🟡 Medium | DaySmart is budget but lacks AI; Shepherd is strong but click-heavy; solo practices underserved by design |
| **Independent SMB (2–4 DVMs, 1 location)** — largest segment | Shepherd, Provet Core/Pro, DaySmart Vet, Digitail | $300–$700/mo | 🟡 Medium | Most served, but none excellent; all lack autonomous AI; companion tool costs add $600–$1,000 on top |
| **Multi-location independent (3–8 DVMs, 2–4 locations)** | ezyVet, Shepherd (multi-loc portal), Provet Pro, Covetrus Pulse, Vetspire | $500–$1,500/mo | 🟡 Medium | Price cliff exists here: practices outgrow SMB tools but can't justify enterprise pricing |
| **Specialty/emergency hospitals** | ezyVet (dominant), Vetspire, Cornerstone | $800–$2,000+/mo | ✅ Well-served | ezyVet purpose-built; Vetspire strong; this segment is crowded |
| **Corporate/DSO groups (10+ locations)** | ezyVet, Cornerstone, Covetrus Pulse, Vetspire | Custom enterprise | ✅ Well-served | Enterprise segment crowded; IDEXX ecosystem dominates |

### Price Ladder Map

```
$0 ────────────────────────────────────────────────────── $2,000+/mo

$116     $299     $350-500   $600-900   $1,500+
DaySmart  Shepherd  Provet      ????      ezyVet/Cornerstone
                               GAP
```

**The critical price cliff:** Between Provet Pro (~$500–700/mo for a 3-vet practice) and ezyVet/Cornerstone (~$1,200–$2,000+/mo), there is a significant gap. Multi-location independent practices with 3–8 DVMs and 2–4 locations find that they've outgrown SMB tools but enterprise pricing is unjustifiable. This segment is forced to either overpay for enterprise or stitch together SMB tools with growing pain.

### Segment-Specific Whitespace

**Solo Practices (1 DVM):**
- DaySmart Vet at $116/mo is the only true entry point
- No AI at that price; Daisy Voice is a $99 add-on
- Solo vets have no option with native AI + comms + scheduling in one tool under $250/mo
- Companion tool costs bring total spend to ~$550/mo — nearly 5x the PIMS cost

**Independent SMB (2–4 DVMs) — THE HIGH-VALUE TARGET:**
- Shepherd at $299/DVM-mo is the closest to purpose-built for this segment
- Shepherd explicitly targets this segment: "companion animal practices 1–4 DVMs"
- BUT: no native online scheduling, no native telemedicine, click-heavy UX, no agentic capabilities
- Provet Core is viable but multi-location and Pro features gated; UK/European flavor
- This segment pays $600–$1,500/mo total for all software; clear consolidation opportunity

**Multi-Location Independent (3–8 DVMs, 2–4 locations):**
- Forced into Pro/Enterprise tiers of ezyVet or Provet
- ezyVet per-user pricing at $260–$300/user/month becomes $1,500–$2,500+/mo for 6–8 users
- No dedicated platform built for this bracket; they're underserved by SMB tools and overpaying for enterprise

### Adjacent Spend — Total Cost of Practice Software

| Category | Monthly Cost (2–3 vet, 1 location) | Integration Quality | Displacement Feasibility |
|---|---|---|---|
| PIMS core | $300–$500 | — | Core product |
| Client comms (PetDesk/VitusVet) | $300–$500 | ❌ Sync failures universal | High — practices hate these tools |
| Reputation/marketing (Podium/Birdeye) | $300–$500 | ❌ No PIMS integration | Medium — contract lock-in |
| Analytics/BI (Vetsource/iVET360) | $249–$400 | 🔌 API-only | Medium — high perceived value |
| After-hours triage (GuardianVets) | $200–$300 | ❌ Email-only logs | High — no good option exists |
| Payroll (Gusto) | $79–$200 | ❌ No vet-specific | Low — Gusto is beloved |
| **TOTAL** | **$1,428–$2,400/mo** | | |

The total cost model reveals that practices paying $400/month for their PIMS are actually paying $1,400–$2,400/month for their full software stack. The PIMS is frequently the cheapest line item. A product that consolidates client comms, reputation management, analytics, and after-hours triage into the PIMS subscription — at a combined price less than the individual tools — has enormous economic leverage.

---

## 5. Lens 4 — Loyalty Driver Analysis

### Positive Review Theme Table

| Feature/Capability | Frequency in Positive Reviews | Platforms That Have It | Quote Evidence |
|---|---|---|---|
| **Auto charge capture from SOAP** | Very High — top-praised feature across Shepherd, ezyVet, Provet | Shepherd, ezyVet, Provet, Covetrus Pulse, Digitail | *"The automatic charge capture has been a game-changer — we've seen a significant reduction in missed charges since switching."* — Capterra (Shepherd) |
| **IDEXX/Antech lab integration depth** | Very High — top-praised for legacy and cloud platforms | Cornerstone (best), Avimark, ezyVet, Shepherd, Provet, all Tier 2 | *"The integration with IDEXX lab equipment is the best in the industry. Results come right into the patient record."* — G2 (Cornerstone) |
| **Ambient AI SOAP drafting** | High — new but generating strong word-of-mouth | Shepherd (TranscribeAI), Covetrus Pulse, Digitail, Vetspire, ezyVet (beta) | *"TranscribeAI is genuinely impressive — it listens and fills in the SOAP while I talk to the client. I don't change how I speak at all."* — Shepherd.vet source |
| **Responsive customer support** | High — cited as key retention driver | Provet Cloud (sub-2-min chat), ezyVet, DaySmart | *"Customer support is exceptional — they get back to you in under 2 minutes via live chat."* — Capterra (Provet) |
| **Financial/reporting accuracy** | High — top reason legacy users stay | Avimark (top-praised), Cornerstone | *"The reporting is incredibly robust — I can pull any data I need. That's what keeps me on Avimark."* — G2 |
| **Inventory accuracy (controlled substance)** | Medium — praised by compliance-focused practices | Cornerstone, ezyVet, Covetrus Pulse | Cornerstone: Full ASAP 4.2 export, DEA tracking; praised for compliance |
| **Native unlimited texting included in price** | Medium-High — cited as competitive differentiator | Shepherd (unlimited SMS no extra cost) | Shepherd positioning: unlimited texts/emails; no extra cost |
| **Open API / vendor independence** | Medium — resonates with tech-forward practices | Provet (explicitly cited), Vetspire (GraphQL), ezyVet (partner-only) | *"We chose Provet because it isn't owned by IDEXX or another diagnostic company. The open API means we're not locked into anyone's ecosystem."* — Capterra (Provet) |
| **Multi-location centralized admin** | Medium — key for growing practices | ezyVet, Shepherd (multi-loc portal), Provet Pro, all enterprise platforms | Key enterprise differentiator; cited by practices managing 2+ locations |
| **DaySmart pricing transparency** | Medium — cited as unique differentiator at budget tier | DaySmart Vet only | Best pricing transparency in the market; publicly listed; no demo required |

### Table Stakes vs. Genuine Differentiators

**Table Stakes (must have — failure here = elimination from consideration):**
- SOAP note creation with template customization
- IDEXX and Antech two-way lab integration
- Auto-charge capture from SOAP (increasingly expected)
- Automated reminders via SMS/email
- Cloud-based access (increasingly required by new practices)
- QuickBooks integration (US practices)
- Basic financial reporting

**Genuine Differentiators (what creates delight and drives word-of-mouth):**
1. **Ambient AI SOAP that requires zero behavior change** — TranscribeAI is specifically praised for this; voice AI that needs commands (Daisy) is less loved
2. **Transparent pricing with no hidden fees** — DaySmart cited explicitly; practices are trained to expect opacity and reward transparency
3. **Responsive sub-2-minute support** — Provet's <2-min live chat is a genuine retention driver
4. **Vendor independence** — Practices feel trapped by IDEXX ecosystem; independence is emotionally resonant (especially for Provet)
5. **Auto charge capture that "never misses a charge"** — Direct revenue impact; practices calculate this in dollars, not features

---

## 6. Lens 5 — Trend Signal Analysis

### Trend Signal Table

| Signal | Platforms Showing It | Maturity | Projected Timeline |
|---|---|---|---|
| **AI SOAP transcription (ambient)** | Shepherd, Covetrus Pulse, Digitail, Vetspire, ezyVet (beta), Provet (add-on), DaySmart Daisy | 🟢 Live, 5+ platforms | TABLE STAKES in 12 months |
| **AI patient summary / history synthesis** | Provet (free), Vetspire, ezyVet | 🟡 Live, 3 platforms | Standard feature in 18 months |
| **AI discharge instructions** | Provet (free, 2025 launch) | 🟢 Live, 1 platform | Adoption wave begins |
| **Agentic front-desk AI** | Digitail (Tails Concierge only) | 🔴 Early/maturing | 18–24 months to widespread |
| **AI waitlist backfill** | Provet (roadmap only) | 🔴 Not live anywhere | 18+ months |
| **AI billing from SOAP (true agentic)** | None (rule-based only) | 🔴 Not live | 24+ months |
| **On-premise → cloud migration** | Avimark (being forced by Covetrus), Cornerstone (no cloud roadmap) | 🟢 Happening now — 25K+ practices in motion | 3–5 year displacement window |
| **AI pricing shift (add-on vs. included)** | Shepherd (included), Provet ($40 add-on), DaySmart ($99 add-on) | 🟡 No consensus | Platforms converging toward inclusion |
| **Per-DVM pricing model** | Shepherd, Provet, ezyVet | 🟢 Dominant for cloud-native | Standard model for new entrants |
| **Open API / ecosystem openness** | Provet (all tiers), Vetspire (GraphQL — best-in-class), Shepherd, Digitail | 🟡 Growing | Developer ecosystem becomes a moat |
| **Native mobile app** | DaySmart, Provet, Digitail, Vetspire, Covetrus Pulse; ezyVet (iOS limited) | 🟡 Mixed maturity | Required feature in 18 months |
| **Pet parent mobile app** | Digitail, DaySmart (PetCare app), Shepherd (none native) | 🟡 Early | Growing client expectation |
| **PIMS consolidation of companion tools** | None doing it fully yet | 🔴 Greenfield | First mover opportunity — 2–3 years |
| **Direct-pay pet insurance integration** | ezyVet (Trupanion, PetSure), Provet, Covetrus Pulse | 🟡 Growing | Standard in 24 months |
| **Controlled substance digital logging native** | Covetrus Pulse (native), Cornerstone, ezyVet; others via VetSnap 🔌 | 🟡 Fragmented | DEA regulatory pressure will accelerate |

### 18-Month Market Trajectory Narrative

The veterinary PIMS market in mid-2026 is at an inflection point driven by three convergent forces.

**Force 1: The Legacy Displacement Wave.** Avimark's active sunset by Covetrus is pushing ~11,000+ practices into the migration market. Cornerstone's lack of a cloud roadmap creates comparable pressure. Over the next 18–36 months, a meaningful fraction of these practices will be actively evaluating cloud alternatives. This is the largest demand event in the history of the PIMS market — and it coincides with the most fragmented competitive landscape in years. The winners in this window will define the market for the next decade.

**Force 2: AI Becomes Table Stakes, Then Differentiates.** AI SOAP transcription is becoming table stakes — five platforms have it live and two more are in beta. Any new entrant launching without ambient SOAP AI will be dismissed in 2026. But transcription is the floor. The ceiling — AI that acts autonomously on behalf of the practice, manages follow-up, fills schedules, and surfaces risk — is entirely unoccupied. Provet has three roadmap items here but none live. Digitail's Tails Concierge is the closest and still maturing. The "agentic" layer of the PIMS stack will be the defining battleground in 18–36 months.

**Force 3: Total Cost Compression.** Practices paying $1,400–$2,400/month for fragmented tool stacks are increasingly aware of the consolidation opportunity. The client communications slot ($300–$500/mo for PetDesk/VitusVet) is the most obvious and hated line item — expensive, poorly integrated, locked by annual contracts. As PIMS platforms add native comms capabilities and market this displacement, practices will respond. The platform that positions itself as the "all-in-one" alternative to the fragmented stack — at a price that's visibly lower — has a structural advantage in sales conversations.

---

## 7. Full Opportunity Priority Matrix

All opportunities scored on: Pain Intensity (30%) | Market Size (30%) | Competitive Whitespace (30%) | Build Feasibility (10%)

| # | Opportunity | Pain (×0.3) | Size (×0.3) | Whitespace (×0.3) | Feasibility (×0.1) | **Weighted Score** |
|---|---|---|---|---|---|---|
| 1 | **Agentic Practice Operating Layer** — autonomous AI that manages follow-up, waitlist backfill, pre-visit intake, and risk scoring without staff action | 5 | 5 | 5 | 3 | **4.80** |
| 2 | **Full-Stack Consolidation for Independent SMB** — PIMS + native comms + reputation + analytics in one platform at a price below the current fragmented stack | 5 | 5 | 4 | 3 | **4.50** |
| 3 | **AI Waitlist Backfill Engine** — detects cancellations, matches against waitlist, sends confirmations, fills slots automatically | 4 | 4 | 5 | 4 | **4.30** |
| 4 | **Native Client Communications (Texting/Comms) Inside PIMS** — displacing PetDesk/VitusVet by including two-way SMS, reminders, and review solicitation natively | 5 | 5 | 3 | 4 | **4.30** |
| 5 | **Agentic Follow-Up Pipeline** — AI detects post-visit need (recheck, vaccine due, chronic condition) and autonomously drafts/sends outreach without staff trigger | 5 | 4 | 5 | 3 | **4.30** |
| 6 | **Independent SMB Cloud Migration Target** — cloud-native PIMS specifically designed for 2–4 DVM practices migrating from Cornerstone/Avimark with white-glove migration | 4 | 5 | 3 | 3 | **3.90** |
| 7 | **Automated Patient Risk Scoring** — AI analyzes visit history, lab trends, vaccine gaps to surface at-risk patients proactively | 4 | 4 | 5 | 3 | **3.90** |
| 8 | **Native Reputation Management (Reviews)** — displacing Podium/Birdeye; $300–$500/mo displacement opportunity with zero native competition | 4 | 4 | 5 | 4 | **3.90** |
| 9 | **Vendor-Independent Open Platform** — positioned as not owned by IDEXX/Covetrus/Zoetis; open API all tiers; no ecosystem lock-in | 3 | 4 | 3 | 4 | **3.40** |
| 10 | **Transparent Pricing Model** — public, tiered pricing with no demo-required, no hidden fees; alone differentiates in a quote-only market | 2 | 5 | 4 | 5 | **3.50** |
| 11 | **Native Telemedicine Integration** — built-in video consult; only Digitail has it; eliminates GuardianVets spend for after-hours | 3 | 3 | 4 | 3 | **3.30** |
| 12 | **AI-Driven Business Intelligence / Predictive Analytics** — revenue forecasting, patient retention risk, utilization predictions | 3 | 3 | 5 | 3 | **3.30** |
| 13 | **Pet Insurance Direct-Pay for All Segments** — one-click claim submission + direct payment; currently only ezyVet and Provet do this well | 3 | 4 | 3 | 3 | **3.30** |
| 14 | **Agentic Pre-Visit Intake** — AI collects patient history, chief complaint, and updated info from pet owner before appointment; syncs to SOAP | 4 | 3 | 5 | 3 | **3.30** |
| 15 | **Modern UX / Low-Click Workflow Design** — deliberate UX investment to reduce the "5 tabs for one appointment" problem universally cited across platforms | 4 | 5 | 2 | 4 | **3.40** |

---

## 8. Top 5 Deep-Dives

### Opportunity #1: Agentic Practice Operating Layer
**Weighted Score: 4.80**

**Market Evidence**
The entire agentic AI capability layer (A02 through A10 in the taxonomy) scores ❌ across 7 of 8 platforms. Digitail's Tails Concierge is the only product approaching "agentic" in the market, and even it is described as still maturing. Every other platform's AI is reactive and advisory: it responds to a vet's action but never initiates one on its own. The contrast is stark — AI SOAP transcription is table stakes in 12 months, but autonomous pipelines don't exist. The agentic layer is completely unoccupied market territory.

The features in the agentic layer represent real, quantified revenue impact:
- **Agentic follow-up:** Every unreached lapsed patient is direct revenue loss. Practices currently use rule-based reminders (automated by date), but no system detects a patient who had abnormal labs and hasn't returned in 90 days and acts on that signal.
- **AI waitlist backfill:** Last-minute cancellations represent direct lost revenue. No platform fills them automatically.
- **Agentic billing from SOAP:** Rule-based auto-charge exists in Shepherd and Provet, but true AI-driven billing — detecting undocumented procedures from transcription and prompting billing — does not.
- **Agent audit log:** When AI takes action on behalf of a practice, practices will need accountability. Nobody has built this yet.

**Who Is Suffering**
Every segment suffers from the absence of agentic AI, but independent SMB practices (2–4 DVMs) feel it most acutely. They have the smallest staff-to-patient ratios, the least administrative bandwidth, and the fewest resources to hire coordinators or analysts to manually perform the tasks an agentic system would automate. Their staff is already logging into 5–8 systems, spending 6+ hours/week on data bridging. Adding an autonomous layer to practice operations directly attacks their #1 operational problem.

**What Solving It Looks Like**
A practice operating layer that:
- Detects post-visit follow-up needs from clinical data (labs, diagnoses, protocols) and autonomously drafts outreach
- Monitors the schedule in real-time, detects cancellations, matches against the waitlist, and sends booking confirmations without staff action
- Analyzes incoming pre-visit intake forms and routes flags to the appropriate clinician before the appointment
- Surfaces patients at clinical or revenue risk on a dashboard and suggests (or executes) action
- Maintains an audit trail of every AI-initiated action for compliance and quality review

**What Existing Players Have Tried (And Why It's Not Enough)**
Shepherd has rule-based reminders and auto-charge from SOAP — but these fire on schedules, not on detected need. Provet has roadmap items for AI scheduling optimization and stock management, but nothing live in the agentic space as of mid-2026. ezyVet's "Communication Tasks" engine is rule-triggered, not adaptive. The gap is architectural: platforms built rule engines when what practices need is an inference engine that reads context and acts.

**Why This Is a Real Opportunity and Not a Trap**
The trap in AI is building features that are impressive in demos but don't survive real workflows. The agentic layer avoids this by targeting workflows that are *already happening manually* in every practice — follow-up calls are already being made, waitlists are already being managed, reminder campaigns are already running. The question is who does them: a staff member spending 2 hours or a system running overnight. The economic case is immediate and calculable.

**Adjacent Opportunity It Unlocks**
An agentic layer that works well becomes the retention moat. Once a practice's follow-up pipeline and waitlist management are automated and tuned to their patient base, switching costs become enormous — the AI "knows" the practice's patterns. This is the same dynamic that makes CRM churn low once workflows are embedded.

---

### Opportunity #2: Full-Stack Consolidation for Independent SMB
**Weighted Score: 4.50**

**Market Evidence**
The stack costs document quantifies the problem precisely: a typical 2–3 vet practice pays $1,428–$2,400/month across 5–8 separate tools. The PIMS is frequently the cheapest line item. PetDesk/VitusVet alone costs $300–$500/month and generates the most complaints: sync failures, annual contracts, opaque pricing, and feature-gating. The document states explicitly: *"The largest single spend category is client communications/texting ($200–$500/mo) followed by reputation/marketing ($300–$500/mo)."*

Not one of the 8 PIMS platforms natively covers: (1) client communications/texting, (2) reputation/review management, and (3) business analytics — the three most expensive companion tool categories. Shepherd comes closest with native unlimited SMS/texting, but has no reputation management and limited analytics. Provet has the open API to connect these but doesn't absorb them natively.

**Who Is Suffering**
Independent SMB practices (2–4 DVMs, 1 location). This is the largest segment by count (~60–70% of all practices). They are price-sensitive, staff-constrained, and deeply frustrated by tool sprawl. The *"6 hours a week copying data between systems"* quote comes from this segment. They can't afford enterprise solutions and they've outgrown basic tools.

**What Solving It Looks Like**
A PIMS that includes — at no additional per-tool cost, no sync failures — native two-way texting, automated reminders, online booking, review solicitation/response, and basic retention analytics. Priced at a total cost visibly below the combined fragmented stack. The value proposition writes itself: *"Replace 5 tools. Pay less than you're paying for just your comms tool."*

**What Existing Players Have Tried (And Why It's Not Enough)**
Shepherd includes unlimited SMS natively — the right instinct, but it stops there. No review management, no analytics. PetDesk positions as a companion tool, not a PIMS — it bridges the comms gap but requires a PIMS underneath. Provet's open API enables connections but not native absorption. The fragmented stack persists because no single vendor has fully committed to the "all-in-one for SMB vet" thesis.

**Why This Is a Real Opportunity and Not a Trap**
The displacement trigger is economic and immediately calculable. When a practice can see that their current stack costs $1,800/month and the consolidated alternative costs $700/month, the conversation starts. Annual savings of $13,200 for a typical SMB practice is a compelling anchor. The trap to avoid: building shallow integrations that create a new version of the sync failures they're escaping. Native must mean native.

**Adjacent Opportunity It Unlocks**
Each companion tool displacement is a step function in retention and ARPU. Once communications, analytics, and reputation are native, the practice's data is fully inside the platform — enabling the agentic layer described in Opportunity #1.

---

### Opportunity #3: AI Waitlist Backfill Engine
**Weighted Score: 4.30**

**Market Evidence**
Waitlist management scores ⚠️ across 5 of 8 platforms and ❌ or 🔌 in the remaining 3. Not a single platform has AI-powered waitlist backfill as of mid-2026. Provet has it on their roadmap but not live. The feature is documented as a gap everywhere, and it represents direct, immediately quantifiable lost revenue: a cancelled appointment slot that goes unfilled is money that cannot be recovered. In a market where veterinary appointment availability is a known consumer pain point (high demand, constrained capacity), this is particularly acute.

**Who Is Suffering**
All practice sizes, but most impactful for practices with long appointment backlogs (multi-location and specialty practices where wait times run 2–4 weeks). A 2-vet practice running 6-week waits for new patient appointments and losing 3–5 slots per week to cancellations is leaving significant annual revenue on the table.

**What Solving It Looks Like**
Real-time detection of cancellation → automated match against waitlist by species, appointment type, doctor preference, and availability → two-way SMS confirmation sent to waitlist patient → slot filled within minutes without staff action. The key differentiator vs. rule-based systems: matching on multiple criteria simultaneously and prioritizing by urgency, not just queue position.

**What Existing Players Have Tried (And Why It's Not Enough)**
Shepherd uses Oliver for waitlist — a third-party integration (🔌) that is passive queue management, not active backfill. ezyVet has "Planning Guides" and dashboard tracking — manual. Provet has basic native waitlist "to fill gaps" — not smart. No platform has the real-time match-and-confirm loop.

**Why This Is a Real Opportunity and Not a Trap**
Unlike some AI features, this one has a direct, measurable revenue number attached to it. A practice can calculate: "I have 10 cancellations per week, average visit revenue $250, fill rate before = 20%, fill rate after AI backfill = 80%. That's $1,500/week in recovered revenue." The ROI case is the sales pitch.

**Adjacent Opportunity It Unlocks**
Waitlist data reveals the practice's true demand curve — the gap between appointment availability and patient need. This feeds directly into predictive scheduling optimization and staffing recommendations (the AI forecasting opportunity).

---

### Opportunity #4: Native Client Communications Inside PIMS
**Weighted Score: 4.30**

**Market Evidence**
Every PIMS platform in the research relies on third-party tools for client communications: Cornerstone → Vello or PetDesk; Avimark → VitusVet, PetDesk, Rapport; Shepherd → PetDesk Direct Booking for scheduling; Provet → 150+ integration partners. The result is universal: sync failures (*"text logs don't reliably import to patient records"* — Capterra, PetDesk), expensive contracts ($300–$500/month for a single tool), and staff spending hours on manual data entry.

PetDesk/Petvisor is the market leader in this companion category and generates intense complaint volume despite high ratings (4.6–4.7/5) — suggesting switching intent is high but alternatives are limited. VitusVet at $319–$399/month is the runner-up with similar complaints.

The displacement opportunity: a PIMS that natively handles two-way texting, automated appointment reminders, online booking confirmations, and review solicitation — baking these into the subscription at no additional per-tool cost — eliminates the most hated line item in the practice stack.

**Who Is Suffering**
Every independent SMB practice. This is the most universal pain point in the companion tool stack. The annual contract on PetDesk ($300–$500/mo × 12 months = $3,600–$6,000/year) is a clear and painful cost.

**What Solving It Looks Like**
Native two-way SMS/MMS from within the PIMS patient record, automated reminders (appointment, vaccine, recheck), online booking integration, and post-visit review solicitation — all natively integrated so there are no sync failures. Included in the base subscription or at a marginal add-on price (<$50/month).

**What Existing Players Have Tried (And Why It's Not Enough)**
Shepherd comes closest with native unlimited SMS included in the subscription — a clear competitive advantage. But Shepherd doesn't have native online booking (🔌 via PetDesk or Chckvet) and has no review management. Provet and ezyVet both offer native texting but not the full communications stack. None have review solicitation natively.

**Why This Is a Real Opportunity and Not a Trap**
The risk here is execution, not market need. Texting and review management are solved technical problems — the challenge is integrating them seamlessly enough that sync failures never happen. The PIMS already owns the patient record and appointment data — native comms have an inherent integration advantage over external tools.

**Adjacent Opportunity It Unlocks**
Native comms data feeds the agentic follow-up pipeline (Opportunity #5) — if the comms layer is inside the PIMS, AI can see message history and response patterns, enabling true adaptive outreach.

---

### Opportunity #5: Agentic Follow-Up Pipeline
**Weighted Score: 4.30**

**Market Evidence**
Post-visit follow-up automation scores ❌ across 7 of 8 platforms in the agentic sense — all existing implementations are either manual or rule-triggered. ezyVet's "Communication Tasks engine" fires by appointment type, not by clinical signal. Shepherd's messaging templates require manual trigger. Provet's reminder automation fires on calendar-based rules. No platform detects: *"This patient had a blood panel with borderline kidney values 90 days ago and hasn't returned — the doctor should reach out"* and then acts on that signal.

The clinical and revenue impact is large. A patient who should have had a 30-day recheck after a diabetes diagnosis but never returned represents both a clinical risk (worsening health, potential emergency) and a revenue loss. Practices report that these patients "fall through the cracks" constantly — not from neglect, but from bandwidth constraints.

**Who Is Suffering**
All companion animal practices, but most acutely solo and 2–3 DVM practices where one receptionist is managing a full schedule and follow-up calls compete with incoming call volume. The practices that most need proactive outreach have the least capacity to generate it.

**What Solving It Looks Like**
An AI system that reads the clinical record — diagnosis codes, lab results, treatment plans, vaccination status — and detects unresolved follow-up needs. It then drafts a personalized outreach message (or call script), routes it for doctor approval (configurable), and sends via the patient's preferred contact channel. The doctor's review step is critical: this must be "agentic with a human in the loop," not fully autonomous, to maintain clinical safety standards and practice trust.

**What Existing Players Have Tried (And Why It's Not Enough)**
The rule-based reminder systems that exist (ezyVet, Provet, Shepherd) are date-triggered: "30 days after appointment, send reminder." This is useful but deaf to clinical context. A patient with a normal recheck and a patient with abnormal lab values get the same reminder. The agentic version reads clinical context.

**Why This Is a Real Opportunity and Not a Trap**
The concern with clinical AI is liability. The mitigation: build this as a "surface and suggest" system that requires doctor approval before any message is sent. This keeps the vet in control, reduces liability, and aligns with the "doctor-controlled" philosophy that Shepherd explicitly markets as a feature. The agentic pipeline becomes the vet's administrative assistant, not a replacement for clinical judgment.

**Adjacent Opportunity It Unlocks**
A follow-up pipeline that works at scale is the foundation of a loyalty/retention analytics product. Once you know which patients responded to outreach and which churned regardless, you have the data to build predictive patient retention models — which is a separately monetizable analytics capability.

---

*End of Veterinary PIMS Market — Opportunity Analysis*
*Research compiled June 2026. All claims grounded in competitive intelligence reports covering Cornerstone, Avimark, ezyVet, Shepherd, Provet Cloud, Covetrus Pulse, Digitail, Vetspire, and DaySmart Vet, plus companion stack cost modeling.*
