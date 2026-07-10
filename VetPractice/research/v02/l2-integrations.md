# Lane 2 — Functional Integrations Landscape (V0.2)

**Date:** 2026-07-09 · **Author:** Lane 2 analyst · **Supersedes:** the July-7 report's 6-integration list (VetConnect, Stripe, Xero, Trupanion, Vetcove, DICOM)
**Method:** heavy web research (5 parallel research threads), verified against the July-7 envelope-strategy board and the phase-4 Goldsmith design brief. Facts cited with URLs; inference flagged.

**Legend — integration effort class:** Easy = public self-serve API/standard protocol · Medium = gated partner program (OAuth handshake, human approval, weeks–months of BD) · Hard = bespoke per-vendor engineering + negotiation · Human-only = no external surface; guided-operator ("human API") is the path.

---

## 0. Cross-cutting findings (they reframe everything below)

1. **There is no interoperability standard in veterinary medicine.** No FHIR-equivalent; VetXML is a UK insurance/microchip niche. Everything is point-to-point, vendor-specific ([Puppilot interoperability guide](https://www.puppilot.co/blog/veterinary-data-interoperability-the-complete-guide-to-connecting-pims-labs-insurers)). There is no "read the standard feed" shortcut anywhere in this document.
2. **The dominant architecture is hub-and-spoke through the PIMS.** Labs, imaging links, insurance claims, wellness plans all flow *through* the PIMS record. **The single highest-leverage move for Vera: read already-ingested results from the PIMS rather than integrating each vendor directly** — one integration surface instead of 8+ gated partner programs.
3. **The canonical gating pattern is identical across diagnostics vendors:** generate an OAuth client-ID/secret inside the PIMS, email it to the vendor's support desk, a human activates it. No diagnostics/imaging vendor has public self-serve developer signup for production data.
4. **Ownership concentration is the structural risk.** IDEXX owns ezyVet/Neo/Cornerstone *and* the #1 diagnostics rail (VetConnect PLUS, Web PACS). Mars owns Antech + Heska + Sound/AIS + VCA/Banfield *and their proprietary PIMS*. Two conglomerates control most of the diagnostics, imaging, and a large share of the PIMS estate Vera must wrap.
5. **The "human API"/guided-operator fallback is viable in almost every category** because every vendor has a clinician-facing web portal — but it is a *bridge*, and portal ToS/anti-automation terms need per-vendor legal checks before bots run at scale.

---

## (a) Reference labs + in-house analyzers

Market structure: consolidated oligopoly. IDEXX #1 (~45% of overall vet diagnostics per secondary research — see "surprise" note below on the 79% figure); Antech #2 (Mars-owned, 70+ US labs); Zoetis #3 and growing (Vetscan, Virtual Laboratory); Heska acquired by Antech/Mars (closed Apr 2023, $120/share — [Mars press release](https://www.mars.com/news-and-stories/press-releases-statements/mars-completes-acquisition-heska)).

| Vendor | Position / ownership | API reality | Pricing/rev-share | Effort | Human-API fallback |
|---|---|---|---|---|---|
| **IDEXX VetConnect PLUS** | #1 diagnostics; owns ezyVet/Neo/Cornerstone | GATED partner program; developer.vetconnectplus.com exists but is credentialed, not public; access via IDEXX integration-request flow, explicitly gated on fit with "IDEXX's product strategy" ([ezyVet commercial application](https://developers.ezyvet.com/apply/commercial.html)) | Not public | Medium (BD-gated) | Yes — VC+ web portal |
| **Antech** (Mars) | #2; largest NA lab network | GATED; ezyVet flow = generate client ID/secret → email to Antech support ([ezyVet docs](https://docs.ezyvet.com/en/see-all-integrations/diagnostic-tests/antech/antech-integration-configuration/configure-the-api-integration-for-antech)); NectarVet's two-way HealthTracks integration proves third-party access is grantable ([NectarVet](https://www.nectarvet.com/post/integrations-antech-diagnostics)) | Not public | Medium | Yes — HealthTracks |
| **Zoetis Diagnostics / Vetscan** | #3 | GATED via Vetscan Hub / Fuse middleware; named bidirectional PIMS: Covetrus Pulse, AVImark, Impromed; "contact your rep" ([Zoetis connectivity](https://www.zoetisdiagnostics.com/us/virtual-laboratory/connectivity/)) | Not public | Medium via PIMS / Hard direct | Yes — Vetscan Hub |
| **Heska** (now Antech/Mars) | Merged Apr 2023 | No public API; HeskaView/DCU middleware, consolidating into Antech; historically weaker integration breadth ([In Practise](https://inpractise.com/articles/idexx-antech-heska-combination-and-threat-to-idexx)) | Not public | Medium–Hard (in flux) | Yes |

**Bottom line (a):** No public lab API exists anywhere. Every major is a gated partner program with a human-approved OAuth handshake. **Vera should read structured lab results from the PIMS record** (they already land there via the PIMS↔lab integrations) and treat direct lab partnerships as an optimization. NectarVet/Digitail are existence proofs that third parties *can* get direct lab integrations — achievable, but Medium effort each and BD-gated. Never touch the diagnostics *order* path (the July-7 shield holds: route orders through native PIMS→VetConnect untouched and instrument the utilization lift).

**In-house analyzers:** results reach the record via vendor middleware (IDEXX VetLab Station/SmartService, Heska DCU, Zoetis Vetscan Hub) → PIMS. Do not integrate analyzers directly; read the PIMS.

---

## (b) Imaging / PACS

| Vendor | Position / ownership | API reality | Effort | Human-API fallback |
|---|---|---|---|---|
| **IDEXX Web PACS** | IDEXX | GATED "API Partner" config in ezyVet; integration writes a **link to a browser DICOM viewer** into the record, not programmatic pixel access ([ezyVet docs](https://docs.ezyvet.com/en/see-all-integrations/diagnostic-imaging/idexx-web-pacs/about-the-idexx-web-pacs-integration)) | Medium | Yes (browser viewer) |
| **Antech Imaging Services / Sound** (Mars) | Huge cloud PACS — self-reports 920M+ images, ~400k/day, 600k+ consults/yr ([veterinaryteleradiology.com](https://veterinaryteleradiology.com/mars-antech-veterinary-teleradiology/)) | DICOM 3.0 ingest is standard on the modality side; downstream third-party access gated, link-based | Medium | Yes |
| **SignalPET** (AI radiology) | Independent | Has a lightweight **push API** (text+PDF report → PIMS); native integrations with Provet and Vetspire ([SignalPET](https://www.signalpet.com/signalpet-pims-integration/)) | Medium | Yes — report lands in PIMS record |
| **Vetology** (AI + telerad) | Independent | **Bespoke per-PIMS API**, DICOM auto-push, free PACS storage included; published per-scan pricing ([Vetology](https://vetology.net/teleradiology/)) | Hard (per-partner) | Yes |
| **Vetscan Imagyst** (Zoetis AI) | Zoetis | GATED via Fuse/Hub middleware | Medium via PIMS | Yes |
| **DICOMweb** (WADO-RS/QIDO-RS/STOW-RS) | — | **~Zero documented veterinary adoption.** Vet PACS expose proprietary cloud viewers + PIMS "link-to-study," not QIDO/WADO REST. Programmatic pixel pull ⇒ proprietary cloud API or classic DIMSE (C-FIND/C-MOVE) against on-prem PACS; open-source DIMSE→DICOMweb gateways (e.g., [DICOM-RST](https://github.com/UMEssen/DICOM-RST)) could bridge | Hard | n/a |

**Bottom line (b):** The July-7 list's "DICOM" line item was **optimistic shorthand**. DICOM is universal at the modality level, but the clean web path (DICOMweb) is effectively absent in vet. For V0.2, images = study links + AI/telerad report PDFs read from the PIMS record. Raw-pixel access is Hard and should not be on the V0.2 critical path (and Vera's Expert Firewall means she shouldn't be interpreting images anyway — she needs the *report* and the *link*).

---

## (c) Payments + financing

| Vendor | Position / ownership | API reality | Pricing / rev-share | Effort | Human-API fallback |
|---|---|---|---|---|---|
| **Stripe** (Connect + Terminal) | Default rail for modern cloud PIMS (Digitail Secure Payments = Stripe; Sunbit BNPL now GA *through* Stripe — [thepaypers.com](https://thepaypers.com/payments/news/sunbit-launches-on-stripe)) | **PUBLIC self-serve** — the strongest API in this whole report ([docs.stripe.com/connect/saas](https://docs.stripe.com/connect/saas)) | 2.9%+30¢ rack; platforms take app fees / buy-rate markup (~half of vertical SaaS take >90 bps per 2026 Embedded Payments Benchmark); Stripe pays platform rev-share above ~$1M run-rate; Connect ~$2/mo/active acct | Easy (online) – Medium (Terminal/Connect payouts) | Not needed |
| **CareCredit** (Synchrony) | The entrenched vet financing brand | **GATED but REAL API** — Synchrony Developer Portal: QuickScreen / QuickScreen Apply / Consumer Self-Service; sandbox open, production requires Synchrony partnership review ([developer.syf.com](https://developer.syf.com/our-products)). Precedent: **Weave×CareCredit strategic partnership, Feb 2026** ([getweave.com](https://www.getweave.com/press-releases/weave-announces-strategic-carecredit-integration-partnership-with-patient-financing-leader-synchrony/)) | Not disclosed; merchant discount on practice; software rev-share privately negotiated | Hard (BD-gated) | **Yes — staff already drive the Provider Center portal manually**; bridge only (credit flows carry ToS/compliance risk) |
| **Scratchpay** | Vet-native financing (WebBank); enterprise deals (CareVet 200+) | **NONE public.** On ezyVet it runs via an unsupported **Chrome extension** with separate staff login ([support.ezyvet.com](https://support.ezyvet.com/support/solutions/articles/154000227607-how-does-scratchpay-work-with-ezyvet-)) | ~5% flat provider fee, no monthly; consumer $200–$10k, 0–36% APR | Hard / Human-only | **Yes — it is already effectively a human-API product today** |
| **Sunbit** | BNPL expanding into vet; in Shepherd PIMS | **Effectively self-serve on Stripe** — activate via Payment Element/Checkout, vet explicitly targeted | Up to $20k / 72 mo, no hard pull | **Easy** if on Stripe | Not needed |
| **Cherry / Affirm** | Healthcare BNPL / general BNPL | Partner integrations; no vet-relevant self-serve | Cherry up to $50k / 60 mo | Medium | Yes |
| **Terminal ecosystems** | **Clover/Fiserv dominant** — Fiserv now sole integrated processor for Cornerstone + powers IDEXX Payments; Global Payments/OpenEdge **exited** Cornerstone Dec 2024 ([software.idexx.com](https://software.idexx.com/cornerstone-integrated-payments-faqs)); ezyVet's US embedded rail = **PayJunction** ([ezyvet.com/integration/payjunction](https://www.ezyvet.com/integration/payjunction)); Provet=Adyen; Gravity resells Clover; Vetsource runs its own payfac | Clover App Market APIs = Medium; Stripe Terminal = self-serve | — | Medium | — |

**Bottom line (c):** Stripe Connect+Terminal is the rail (only true public API; platform economics; Sunbit toggles on nearly free — the cheapest financing win). CareCredit is the brand clinics demand — real Synchrony APIs exist but production is partnership-gated; the Weave deal (Feb 2026) proves a software layer can land it — start BD now, human-API bridge meanwhile. Watch the pattern: **every modern PIMS is becoming its own payfac** (IDEXX/Fiserv, ezyVet/PayJunction, Provet/Adyen, Digitail/Stripe) — payments is both a Vera revenue line and contested envelope territory. Vet BNPL ≈ $1.24B 2026, ~18% CAGR.

---

## (d) Accounting

**Market share:** QuickBooks ≈ 80% of US SMB accounting (range 62–82% by methodology — [electroiq.com](https://electroiq.com/stats/quickbooks-statistics/)); Xero only ~9% US SMB, and just ~18% of Xero's global base is US. Vet bookkeeping services (VetBooks etc.) standardize on QBO. **The July-7 report's "Xero" pick reflects ezyVet's NZ-origin integration list, not the US market — for US clinics QBO is the build.**

**What big groups actually consolidate on (verified):** Mars Veterinary Health (3,000+ hospitals) = **Oracle Fusion Cloud ERP+HCM** ([oracle.com](https://www.oracle.com/customers/mars-veterinary-health/)); NVA (1,400+) = **Oracle Cloud ERP + Kyriba**; Thrive = **Workday Financials**; growth-stage groups (e.g., Vets Pets) = **Sage Intacct**, migrated off QuickBooks ([sage.com](https://www.sage.com/en-us/success-stories/vets-pets/)). Segmentation: 1–20 clinics → QBO; ~20–150 → Intacct/NetSuite; 150+/PE-platform → Oracle Fusion or Workday (internal IT; won't bolt a wrapper onto the GL).

| Vendor | API reality | Pricing / gating | Effort | Human-API fallback |
|---|---|---|---|---|
| **QuickBooks Online** | GATED public API — REST+OAuth2, free to develop; production requires Intuit App Assessment | 2025 App Partner tiers: Builder $0 → Silver $300/mo → Gold $1,700 → Platinum $4,500; write ("Core") calls unmetered, read/report ("CorePlus") metered ([apideck.com](https://www.apideck.com/blog/quickbooks-api-pricing-and-the-intuit-app-partner-program)) | Easy–Medium | Stopgap only |
| **Xero** | GATED public API, self-serve signup | **Mar 2, 2026 change:** 15% rev-share retired → 5 tiers by connection count + data egress (Starter $0 → Advanced $895/mo; ~AUD$2.40/GB egress) ([accountingtoday.com](https://www.accountingtoday.com/news/xero-shifts-to-tiered-pricing-model-for-developers)) | Easy–Medium | Low priority |
| **Sage Intacct** | GATED **partner-only** (Sage Developer Partner status + Web Services license) | ~$2,500/yr + **$0.015/API call** in production ([marketplace.intacct.com](https://marketplace.intacct.com/becomeapartner)); product $25k–60k/yr | Medium–Hard | **Yes — RPA/browser export around API/report limits is a documented real-world pattern** |
| **NetSuite** | GATED; free dev account; certified "Built for NetSuite" requires SDN application | SDN/BFN fees unpublished; product ~$25k–60k/yr+ | Hard | Rarely worth it (buyers expect certified apps) |

**Bottom line (d):** Build QBO first (covers ~4 of 5 small clinics; the assessment gate is bureaucratic, not technical). Xero only on customer demand — its new connection+egress metering makes it worse economics than July-7 assumed. Intacct is the 20–150-clinic group play (matters for the F6 mid-tier — Goldsmith-scale groups). The mega-groups run tier-1 ERP Vera will never integrate: at that tier Vera *produces clean exports for* their ERP team rather than integrating.

---

## (e) Payroll / HR / shift scheduling

Structural finding: **scheduling and payroll have opposite openness.** SMB shift-scheduling tools are integration-friendly; payroll incumbents are gated B2B partnerships.

| Vendor | API reality | Gating / pricing | Effort | Read/write reality |
|---|---|---|---|---|
| **Deputy** | **PUBLIC self-serve** — "all functionality in UI available via API"; any customer creates an OAuth token ([developer.deputy.com](https://developer.deputy.com/docs/public-api-facts-and-overview)) | Free with subscription | **Easy** | **Read schedules + WRITE/auto-build/auto-fill shifts + read timesheets/labor cost — the only vendor with all three, self-serve** |
| **When I Work** | Public docs, **manual key issuance** by email; markets a veterinary-clinic vertical ([wheniwork.com](https://wheniwork.com/industries/veterinary-clinic-software)) | Administrative gate | Medium | Create/bulk-update/delete shifts verified |
| **Homebase** | API referenced; terms/auth publicly unverifiable | Opaque | Medium–Hard | Defer until confirmed |
| **ADP** | GATED Marketplace partner program ("strategic fit," shared-client counts, mutual SSL certs) | ISV fees undisclosed; referral rev-share tiers to 75% | Hard | TLM APIs read AND write timecards/schedules — richest incumbent surface, but only behind the gate |
| **Paychex** | GATED with public dev portal; endpoints granted à la carte | Undisclosed | Medium–Hard | Time readable; write depth per approved scope |
| **Gusto Embedded** | GATED partner agreement (demo open, production reviewed) | Per-customer + per-employee partner fees | Medium–Hard | Write-heavy (run payroll) — only if Vera wants to BE the payroll surface |
| **Paycom** | **Effectively none public** — customer/partner-only, docs post-access, "thousands of dollars annually" ([getknit.dev](https://www.getknit.dev/blog/paycom-api-integration-guide-in-depth)) | High | Hard / near Human-only | Deprioritize (mid-market skew) |
| **Finch** (unified aggregator) | **PUBLIC unified API → 250+ payroll/HRIS** incl. ADP/Paychex/Gusto/Paycom; automated + assisted credential-based modes, "not screen scraping" ([tryfinch.com](https://www.tryfinch.com/finch-api)) | Usage-priced | **Easy–Medium** | Reads census/pay/labor cost; does NOT run payroll or create shifts |
| Vet-specific | Crocodile HR (UK-only), RosterElf (AU-only) — **no dominant US vet-specific workforce tool with an open API exists** | — | — | Integrate horizontal, not vet-vertical |

**Bottom line (e):** For F3, **Deputy is the priority integration** — the only self-serve API that reads schedules, writes shifts, and reads labor cost; When I Work second. For payroll/labor-cost *reads* feeding F4, **one Finch integration covers ADP/Paychex/Gusto/Paycom** — don't build four direct gated integrations; Finch's "assisted mode" is itself a productized human-API. Strategic note: since Vera's own scheduling engine (Program #1/#2) may *be* the rota brain, Deputy/WIW are actuators Vera writes to — or vendors she displaces at clinics that adopt Vera rostering; the integration is also the migration path.

---

## (l) PIMS surfaces for the envelope at enterprise

*Verification note: the dedicated PIMS research thread failed to return; the highest-stakes rows were re-verified directly this session (marked ✅). Rows marked ◐ are analyst background knowledge at moderate confidence — confirm before any F6 architecture freeze.*

| PIMS | Owner (2026) | Cloud/on-prem | API reality | Export surface | Effort | Human-API-only? |
|---|---|---|---|---|---|---|
| **ezyVet** ✅ | IDEXX | Cloud | Gated REST/OAuth2. **Private track (our D1(b) pilot structure): one-time setup fee; read-only = NO monthly fee, available to all eligible clinics; write-back = per-hospital monthly fee + Partnerships-team approval.** ⚠️ New find: Private API terms **ban incorporating SMS or payment functionality outside ezyVet's framework** ([ezyvet.com/build-a-custom-integration](https://www.ezyvet.com/build-a-custom-integration)) — a direct constraint on wiring F1 SMS / F4 payments through the private integration | Full API read + Automated Reports + §5 bulk request (July-7 ladder holds) | Easy–Medium | No |
| **Cornerstone** ◐ | IDEXX | **On-prem** | No public API. **IDEXX Data Services exists** ✅ ([dataservices-dev.idexx.com/documentation/Cornerstone](https://dataservices-dev.idexx.com/documentation/Cornerstone) — a partner data gateway for Cornerstone; site confirmed live, content credential-gated). Cadence/read-write specifics unverified | Via Data Services if partnered; on-prem report exports | Hard (gated) | No if Data Services granted; else near-yes |
| **Neo** ◐ | IDEXX | Cloud | Data Services family; reported in-product API key + customer-scheduled full data export (unverified this session) | Likely strongest customer export among IDEXX PIMS | Easy–Medium | No |
| **AVImark** ◐ | Covetrus (CD&R/TPG) | On-prem; legacy proprietary file-based store (SQL edition exists) | No public API; only sanctioned channel is Covetrus Connect — **which is PAUSED** ✅ | Backup ZIPs, Excel/CSV reports | **Hard / effectively Human-only for new entrants today** | Near-yes |
| **Impromed** ◐ | Covetrus | On-prem, MS SQL Server | No public API; Connect paused | **On-prem SQL readable in place** (local-agent path) | Medium–Hard | No — SQL agent |
| **Covetrus Pulse** ✅ | Covetrus | Cloud | Gated Connect API — **"New integration requests are paused"** while Covetrus updates "APIs, documentation, and partnership framework"; **no reopen date** ([covetrus.com/about/partner-with-us](https://covetrus.com/about/partner-with-us/)) | Report exports only | Medium if/when reopened / **Human-only now** | Yes, while paused |
| **Shepherd** ◐ | Shepherd (acquired Hippo Manager) | Cloud | Markets an "open API"; no public docs/portal/terms locatable — unproven | Undocumented | Hard until proven | Possibly |
| **Digitail** ✅ | Independent | Cloud | Real public docs, **gated: "all API access is reviewed and approved by the Digitail team"; production requires a DPA; tiered partner levels (0–2); bulk operations explicitly unsupported — real-time only, not for batch export/migration** ([documentation.digitail.io](https://documentation.digitail.io/)) | Real-time API only | Medium | No |
| **Provet Cloud** ✅ | Nordhealth | Cloud | **Most open posture after Vetspire: developer docs freely readable, no login** ([developers.provetcloud.com](https://developers.provetcloud.com/)); OAuth2 REST + subscription/payment endpoints (see §h) | Via REST | Easy–Medium | No |
| **Instinct** ◐ | Instinct Science | Cloud (ER/specialty) | Gated partner API (access via support) | Dashboard exports + API | Medium | No |
| **Vetspire** ✅ | Used by consolidators (Bond Vet et al.); Thrive-affiliated ◐ | Cloud | **Public GraphQL docs; org admins SELF-GENERATE production API keys in the dashboard — no partner gate.** ~24 query + 26 mutation categories: patients, clinical, scheduling, billing/AR, inventory, labs, comms ([developer.vetspire.com](https://developer.vetspire.com/)) | Full GraphQL pull | **Easy–Medium — the most open PIMS surface found** | No |
| **Rhapsody** ◐ | **Chewy** (acquired Petabyte 2022) | Cloud | "Open API"/marketplace marketed; no self-serve portal found — partner-vetted; Chewy is a strategic gatekeeper (and now owns clinics) | Via API if granted | Medium | No |
| **DaySmart Vet** (ex-Vetter) ◐ | DaySmart | Cloud | Gated OAuth2 REST with public docs; discretionary approval | Paginated REST | Easy–Medium | No |
| **IntraVet** ◐ | Patterson | On-prem, MS SQL | No public API | **On-prem SQL read is the practical path** | Medium | No — SQL agent |
| **WOOFware** (VCA) / **PetWare** (Banfield) ◐ | **Mars** proprietary/internal | Internal | **No external API** (high-confidence negative) | None | **Human-only** | **Yes** |

**Standards check ◐:** no vet FHIR exists and no consortium emerged in 2025–26; VetXML remains UK-insurance-scoped. De-facto interchange is commercial middleware — Bitwerx-class payment/appointment middleware and DataHub-Vet-class unified-API/on-clinic-agent vendors for the legacy on-prem tier, plus Vetsource/SyncVet ETL — alongside the two conflicted giants (IDEXX Data Services; Covetrus Connect, paused). A large share of US installs remains on legacy on-prem PIMS (AVImark/Cornerstone/Impromed); exact percentages unverified this session.

**Bottom line (l):** The estate splits into four tiers — (i) genuinely open/near-open: **Vetspire (self-serve GraphQL keys — the most open surface found), Provet Cloud, DaySmart**, ezyVet-with-agreement; (ii) gated-but-real: Digitail, Instinct, IDEXX Data Services, Rhapsody; (iii) on-prem DB/agent territory: Impromed, IntraVet (tractable MS SQL), AVImark (hardest); (iv) human-API-only: Mars internals, Covetrus cloud while Connect is paused, Shepherd until proven. **The two chokepoints for a mixed-PIMS enterprise estate are IDEXX (door open but formal — and it's our competitor-landlord) and Covetrus (door literally closed today: Connect paused, no reopen date).** F6 mixed-estate planning cannot assume a Covetrus API in 2026 — the AVImark/Impromed/Pulse share of any 400-clinic estate is guided-operator + on-prem-agent territory until Connect reopens. Mars-adjacent estates are human-API by construction. The "Redox for vet" the July-7 board asked about exists only in embryonic, service-shaped form (Bitwerx/DataHub-class) — a licensing/acquisition option worth pricing for the legacy tier.

---

## (i) Controlled substances / PDMP

**Which states mandate vet reporting (the key question):** best-verified count is **~18 states requiring dispensing veterinarians to report** (federal PDMP TTAC survey: 49 PDMPs, all require dispensing practitioners, "only 18 required dispensing veterinarians" — [pdmpassist.org TAG](https://www.pdmpassist.org/Content/Documents/pdf/TAG_Veterinary_Best_Practices_20200710.pdf)); corroborated from the other side by "roughly 33 states exempt veterinarians" ([Owner Exchange 2026](https://ownerexchange.com/veterinary-controlled-substance-compliance/)). 2026 estimate: **~15–20 reporting states, trending up** as exemptions get removed. Confidently named reporting states (~12): AR, CT, ME, MA, MI (>48h), NE, NH (>48h), NC, TN, VA, WA, **CA (CURES, 7 days)**. Verified exempt: GA, IL, IA, KS, MD, MN, MS, OH, PA, SD, VT, AZ, DE, NY, MO; KY/LA/NM/WV/WY *repealed* prior vet mandates. Distinguish **reporting** (where Vera's automation attaches) from **querying-before-prescribing** mandates (~6–10 states). Caveat: counts stem from a 2019–21 federal/AVMA baseline refreshed against 2026 secondary sources — re-verify per target state at contract time (AVMA keeps a member-gated live tracker).

**The counterparty is singular: Bamboo Health** (ex-Appriss; Clearlake Capital PE-owned since 2019, no exit found through mid-2026). Common confusion to avoid: **PMP Clearinghouse = submission** (dispenser→state), **PMP Gateway = query/retrieval** into clinical systems (wrong direction for reporting), **AWARxE = the state platform** (44 states).

**Submission mechanics (verified):** ASAP 4.2A files (field PAT20 '02' = veterinary patient) via **SFTP** to `submissions.healthcarecoordination.net` (one account can serve multiple states/facilities), web-portal upload, manual UCF entry, zero-reports, or real-time SOAP/WSDL in select states ([Indiana INSPECT dispenser guide](https://www.in.gov/pla/inspect/files/IN-PMP-Data-Submission-Dispenser-Guide_v-4.0.pdf)). **No public REST API exists.** Per-state version drift is the real complexity (LA = ASAP 4.2B; OH = ASAP 5.0).

**PIMS reality:** the federal TTAC itself documents that most vet PIMS never built ASAP generation. **ezyVet is the standout** with native PMP Clearinghouse auto-upload ([ezyVet docs](https://docs.ezyvet.com/en/browse-documentation/ezyvet/veterinary-care/medications/controlled-drugs/find-and-show-controlled-drug-information/the-controlled-drug-report/pmp-clearinghouse-configuration/configure-the-pmp-clearinghouse-integration)); Cornerstone/AVImark/Vetspire/Shepherd/Provet: none found. Gap-fillers: VetSnap (log + "PMP Assistant," 30+ PIMS), CUBEX (cabinets + 50-state submission), VetScript.

**Bottom line (i):** Narrow but real and growing mandate, **one counterparty, no modern API — ASAP-file-over-SFTP is the integration**, a Medium build whose complexity is per-state ASAP versions + account lifecycle. Guided-operator fallback is fully viable (Vera generates the ASAP file; a human uploads via portal) — an ideal staged launch. Confirmed whitespace: the regulator itself says PIMS vendors never resourced this.

---

## (j) After-hours / teletriage — partner or displaced vendor for F1 voice?

| Vendor | Position (2026) | API | Pricing | **Verdict for F1** |
|---|---|---|---|---|
| **GuardianVets** | **$7M Series A Oct 2025** (Resolute); 2.5M+ after-hours cases; repositioned as "GuardianVets OS": GV Phone System + **AI Voice & Chat** + PIMS integration ([guardianvets.com/ai-voice-and-chat](https://www.guardianvets.com/ai-voice-and-chat)) | None public/gated; no named PIMS, no dev docs | Per-clinic monthly, sliding by vet count; no public rates | **DISPLACE — Vera's most direct competitor.** They already ship F1's exact scope (AI voice + after-hours + urgency routing + PIMS write-back). The July-7 model treated them as a $200–300/mo displaced line item; they are now a freshly funded AI-voice product company |
| **VetTriage** | Founder-owned; in-house licensed DVMs, 24/7 live video, no app | **None (human-only)** — onboarding = co-branded landing page + protocols, live "within hours" | **Free to clinic; owner pays flat $50/session**, no rev-share ([vettriage.com/hospital-partners](https://vettriage.com/hospital-partners/)) | **PARTNER — best warm-transfer target.** Supplies the one thing Vera architecturally cannot (a live DVM); ~80%+ cases resolved without ER |
| **Airvet** | ~$58.8M raised; pivoted to employer benefit (Adobe, PepsiCo); **MWI Animal Health preferred telehealth partner** | Gated partner program, no public API | Employer-funded; clinic terms undisclosed | **PARTNER (second option)** — 24/7 vet queue = natural escalation endpoint; coopetition risk (own instant triage overlaps F1) |
| **Vetster** | $30M Series B Dec 2025 (PetMeds strategic); PetSmart deal Jan 2026 | None — BD deals only | Marketplace per-visit | DISPLACE-adjacent DTC; scheduled consults, not an emergency router |
| **Dutch** | ~$43M; Rx in 34 states; DTC membership ~$15/mo | None | DTC subscription | Lowest F1 relevance |
| **whiskerDocs** | Pivoted to employer/insurer benefits; AI chat | None public | B2B2C | Orthogonal — deprioritize |

**Bottom line (j):** **Nobody in teletriage publishes an API** — escalation is warm phone transfer + co-branded routing, not API handoff (fine: Twilio `<Dial>` does this natively). Strategy: **partner with humans, compete with platforms** — VetTriage as the default medical-escalation partner ($0 clinic cost, hours to launch), Airvet as the channel-savvy alternative, GuardianVets as the competitor whose line item Vera displaces. Vera's wedge is the thing none of them own: *the clinic's own phone number under the clinic's brand.*

---

## (k) Comms rails

**A2P 10DLC 2026 reality (applies on every provider):** brand registration ~$46 Standard (secondary vetting now mandatory) or ~$4 low-volume; campaign vetting $15 one-time; $1.50–$10/mo per campaign; **carrier pass-through per segment post-Jan 19, 2026: AT&T $0.0035, T-Mobile/Verizon $0.0045 out, USCC $0.005** ([Twilio](https://www.twilio.com/en-us/sms/pricing/us), [Telnyx fee schedule](https://support.telnyx.com/en/articles/5634625-10dlc-fees-and-charges)). Throughput is Trust-Score gated. **Implication: register ONE Vera ISV Standard brand with pooled/per-clinic campaigns — never push clinics through their own registration; budget days-to-weeks vetting latency into clinic onboarding (this is an R2 work item).**

**WhatsApp: defer for US clinics.** Per-message template pricing since Jul 1 2025; utility ~$0.004/msg — but **US marketing templates have been PAUSED/blocked since Apr 1, 2025 and remain so**, and only ~32% of US adults use WhatsApp vs ~100% SMS reach ([Meta](https://developers.facebook.com/documentation/business-messaging/whatsapp/pricing), [Manychat](https://help.manychat.com/hc/en-us/articles/19328856186780-Temporary-pause-on-WhatsApp-Marketing-Templates-in-the-US)).

| Provider | API | US pricing highlights | Effort | Note for F1 voice |
|---|---|---|---|---|
| **Twilio** | Public self-serve | Voice $0.0085 in / $0.0140 out per min; SMS $0.0083/seg; number $1.15/mo; **ConversationRelay $0.07/min (GA Jul 2025, BYO-LLM)** → ~$0.0785/min all-in Twilio-side | Medium (10DLC compliance is the overhead) | Pragmatic default; best warm-transfer/TaskRouter patterns; already in our stack (`sms_gateway.py`) |
| **Telnyx** | Public self-serve | **Voice AI $0.05/min incl. STT/TTS**; SMS $0.004/seg (half Twilio); number $1/mo; 10DLC at-cost | Easy–Medium | The cost/latency challenger — owns its network |
| **Plivo** | Public self-serve | Number $0.50/mo; voice $0.0055/$0.0115; HIPAA; BYO-LLM streaming; TwiML-near-clone | Easy | Credible dark horse |
| **Bandwidth** | Hybrid; enterprise contract-gated (12-mo) | Voice $0.0055/$0.0100, 6-sec billing | Medium–Hard | Skip for now (no AI voice layer) |
| **Vonage** (Ericsson) | Public but opaque pricing; proprietary NLU | ~$0.008/min | Medium | Poor BYO-LLM fit |
| **Sinch** | Public, enterprise-flavored | Voice Relay AI launched only Mar 2026 | Medium–Hard | Too new |

**Bottom line (k):** Comms is the one fully-public-API category in this report. Run a **Twilio-default / Telnyx-challenger bake-off** for F1 (feeds R7 voice-cost telemetry: Twilio ~$0.0785/min vs Telnyx ~$0.05/min platform-side, before model costs); Plivo as fallback leverage in negotiation. The only "gate" is 10DLC compliance itself — own it as an ISV.

---

## (f) Procurement / distributors (F2's landscape)

**Structural news that changes the July-7 picture: in Feb 2026, Cencora announced MWI Animal Health will merge with Covetrus (~$3.5B EV for MWI)** ([Cencora investor release](https://investor.amerisourcebergen.com/news/news-details/2026/Covetrus-and-MWI-Animal-Health-to-Merge/default.aspx), [VIN News](https://news.vin.com/default.aspx?pid=210&catId=621&Id=13154850)). Two of the big-three distributors are consolidating — and the merged entity has strong incentive *not* to expose comparative pricing via API.

| Vendor | Position / ownership | API / partner reality | Effort | Human-API viable? |
|---|---|---|---|---|
| **Vetcove** | Largest B2B vet marketplace / comparison layer; ~$153M raised (Thrive, Fuel, Maverick) | **A real REST API exists** — the "Vetcove PIMS Integration API," public ReDoc docs ([integration.vetcove.com/redoc](https://integration.vetcove.com/redoc/)), live with ezyVet/Provet/Vetspire — **but its documented scope is order/inventory sync with a PIMS, NOT an open cross-distributor pricing feed.** Price comparison lives in the web portal only; partner integrations are bespoke, project-managed engagements | Medium–Hard (partner-gated; a pricing endpoint may not exist at all) | **Yes — strongly.** The per-practice qualified price, stock, and rebates are all in the portal; an operator on the clinic's own account compares + checks out today |
| **MWI** (Cencora) | Leading US animal-health distributor; merging with Covetrus | Gated credential-based PIMS connectors (ezyVet live catalog/POs/invoices) + mature **EDI** ecosystem (~$350/mo middleware). "Open API"/Merlin references are **UK-only** — don't assume US | Hard direct; Medium via existing PIMS connector | Yes |
| **Covetrus** | Top-3 distributor + PIMS vendor (Pulse/AVImark/eVetPractice); CD&R+TPG ~$4B, private since 2022 | Gated **Covetrus Connect** — "the only authenticated and supported way to integrate"; application → partnerships team, **~6–8 weeks** ([partner signup](https://software.covetrus.com/apac/veterinary-solutions/covetrus-connect-partner-signup/)) | Hard | Yes |
| **Patterson Veterinary** | Patterson (PDCO); Animal Health net sales $4.1B FY24 | **No public API found**; PIMS supplier connectors + EDI only | Hard / Human-only without a contract | Yes |
| **Midwest Veterinary Supply** | Independent (ex-Victor Medical) | **Lightest-weight distributor API**: practice downloads client ID+secret, coordinated with integrations@midwestvet.net ([ezyVet config](https://docs.ezyvet.com/en/see-all-integrations/product-suppliers/midwest-veterinary-supply/configure-the-api-integration-for-midwest-veterinary-supply)); POs, invoices, automatic price updates | **Medium** | Yes |
| **Chewy Practice Hub** | Chewy (CHWY); vet-only Rx/product marketplace, 1,000+ practices | Gated PIMS partnership; no public API; **rev-share by design** (vets set prices, receive revenue on orders; split undisclosed) | Hard / Human-only | Yes — it's a web portal |
| **Vetsource** (home-delivery Rx) | **Majority-owned by Mars Petcare**; MWI and Patterson also on cap table | API-key exchange brokered by email (practice generates key → datasupport@vetsource.com); scope = home-delivery Rx, not supply comparison | Medium | Yes |

**Bottom line (f) — the F2 verdict:** **Vera cannot do real cross-distributor price comparison via a clean third-party API today. The guided-operator/human-API mode is not the fallback — it is the primary architecture for F2.** The one place true comparison exists (Vetcove) is portal-first, on the clinic's own distributor accounts, with per-practice negotiated pricing — exactly the surface the phase-4 brief's "guided-operator / agentic browsing with the clinic's own account" was designed for. Even a full distributor-API build yields per-clinic credentialed ordering with no normalized comparison feed — you'd be rebuilding Vetcove. Recommended ladder: operator-driven Vetcove (comparison+checkout) → Midwest client-secret + PIMS supplier connectors (ordering/inventory sync) → Covetrus Connect application + Vetcove Partner Integrations as long-lead partnerships (expect order/inventory scope only). The MWI–Covetrus merger makes a Vetcove partnership *more* valuable and *less* likely to be undercut by a distributor-native alternative.

---

## (g) Insurance (point-of-sale claims)

**Headline: Trupanion is the only US pet insurer with true point-of-sale, direct-to-vet-pay claims embedded in practice software** — its own claim, corroborated across all nine carriers researched ([trupanion.com/pet-insurance/veterinarians](https://www.trupanion.com/pet-insurance/veterinarians)). There is **no industry claim rail** — no EDI-837 analog, no clearinghouse; NAPHIA does benchmarking surveys only; VetXML/VetEnvoy has no live US carrier.

| Carrier | Ownership / position | POS / API reality | Effort | Human-API |
|---|---|---|---|---|
| **Trupanion** | TRUP; FY25 rev $1.44B, 1.65M pets, 8,500+ hospitals; ~29–30% brand share | **GATED partner API** (Azure APIM, OAuth client-credentials, provisioned via TruExLaunch@Trupanion.com — not self-serve). True checkout direct pay **fully embedded in ezyVet only**; Cornerstone/Neo get *Exam Day Offer enrollment only*; legacy Express bridges on AVImark/ImproMed/Vetspire/WOOFware etc. (depth unverified) | Medium–Hard (gate is BD, not code) | Yes — free web **Vet Portal** built for manual staff submission (60%+ of direct payments in 60s); third-party-operator ToS unverified |
| **Pumpkin** (Independence Pet Holdings) | Zoetis-launched, sold to JAB/IPH | No API, but a sanctioned vet-facing **PawPortal** for staff-filed claims; **PumpkinNow** (Apr 2025) = ~15-min expedited pay *to the owner*, explicitly not to hospitals | Human-only today | **Most viable non-Trupanion** |
| **Spot** (IPH) | 750k+ pets | None — but the claim form **explicitly authorizes "an authorized representative from your veterinarian's office"** to submit ([claims-form.pdf](https://spotpet.com/claims-form.pdf)) | Human-only | Yes — carrier-sanctioned |
| **Healthy Paws** (Chubb, ~$300M 2024) | 500k+ pets | Direct-to-vet pay **exists but manual + pre-arranged by phone/email** | Human-only | Yes — the only non-Trupanion path to a vet-paid outcome |
| **Nationwide** | #2, ~19–21%; non-renewed ~100k policies 2024 | Quoting API for distribution partners only; **no claims API, no POS**; VitusVet channel dead (ceased ops Feb 2025) | Human-only | Yes (owner reimbursement) |
| **Embrace** (JAB/IPH $1.5B) | — | **None — vet claims by email or fax.** (Trupanion sued Embrace in 2019 over an Express clone) | Human-only | Yes |
| **Fetch** (Warburg) | — | None in US; full vet-facing "FetchPay" direct-pay portal exists **in Australia only** — US port plausible, unevidenced | Human-only (US) | Yes |
| **MetLife Pet** | Employer/group distribution | None; MyPets portal/email/fax | Human-only | Yes |
| **Lemonade Pet** | LMND; pet = largest line, $439M IFP | App-only, AI Jim + owner video statement — **architecturally hostile to intermediation** | Effectively not possible | **Marginal — weakest** |

**Strategic lever:** **Independence Pet Holdings owns Spot, Embrace, Pumpkin, Pets Best, Figo, ASPCA, AKC brands *and* underwriter IAIC (which also underwrites MetLife Pet)** — one BD conversation could cover much of the non-Trupanion market. And since no clearinghouse exists, a multi-carrier "Vera files it from the practice" layer is greenfield — honest framing: Trupanion = clinic paid at checkout; everyone else = filed-for-you owner reimbursement. Vetsource/SyncVet is a records-retrieval pipe carriers already use for SOAP-note pulls — solves Vera's claim-attachment problem.

**Bottom line (g):** the July-7 list was right that Trupanion is the insurance integration — it is literally the *only* one. R9's "insurance operations" should be scoped as: Trupanion partner API (BD now) + guided-operator claim filing across the IPH brands + Healthy Paws pre-arranged direct pay as an operator workflow.

---

## (h) Wellness plans

**Data-quality warning (verified):** a widely-indexed 2026 buyer's guide admitted two vendor names — "Vetsource Premier" and "DVM Subscription Hub" — were **AI-fabricated placeholders** ([vetsoftwarehub correction](https://www.vetsoftwarehub.com/article/veterinary-wellness-plan-software-2026-a-buyers-guide)); search engines still repeat them. **Vetsource does not sell a wellness-plan platform.**

| Option | Reality | Effort | Human-API |
|---|---|---|---|
| **VCP → Covetrus Care Plans** | Category leader (acq. by Covetrus 2021; ~1,000 practices, 350k+ pets); gated behind Covetrus Connect; API keys only via support@careplans.vet | Hard | Yes — enrollment is staff-driven in-PIMS |
| **In-PIMS native modules** | **The dominant pattern**: ezyVet (module free, onboarding fee), Vetspire, Provet Cloud, Shepherd (requires Shepherd Pay), Digitail (self-enrollment + auto-billing), AVImark (+VCP) all ship one | Easy in native UI; Medium via ezyVet/Provet APIs | Yes — universally |
| **Provet Cloud** | **Strongest developer story**: documented REST + a dedicated subscription/wellness Payment API (create/list/renew — .au-hosted docs, US applicability unconfirmed) | Medium | Yes |
| **IDEXX Petly Plans** | Active; no public API found | Medium–Hard | Yes |
| **Standalone (Snout, Nest, baxtr, Premier Pet Care Plan)** | Snout pays clinic at time of service then collects from owner (A/R shift); baxtr is deliberately PIMS-agnostic-no-integration; Premier verified $50 signup + 12-mo auto-renew | Human-only / Medium | Yes (inherently operated layers) |
| **Generic billing (Stripe Billing/Recurly)** | Public self-serve APIs — but all vet logic (benefit accrual, redemption, PIMS sync) is on you | Easy billing; the hard part is write-back | — |

**Bottom line (h):** No wellness vendor has a public third-party API. Lead with **guided-operator over each PIMS's native wellness module** (universal, no vendor blessing needed); add real API integrations only for Provet Cloud and ezyVet; offer Vera-native Stripe billing only where no module exists *and* PIMS write-back is real (billing-without-reconciliation is the standalone-platform failure mode). Pricing norms low-confidence: managed platforms reportedly take 6–15% of collected member fees; only firmly verified numbers are Premier's $50 signup and Scratch's 5% provider fee.

---

## Synthesis — the function × access-model map

| Function | Best access model today | Effort | Human-API viable? | V0.2 verdict |
|---|---|---|---|---|
| (a) Reference labs | Read results **from the PIMS record**; direct = gated partner (IDEXX/Antech/Zoetis) | Medium, BD-gated | Yes (all portals) | PIMS-mediated; never touch order path |
| (b) Imaging/PACS | Study links + report PDFs from PIMS; **DICOMweb ~absent in vet** | Medium; pixels = Hard | Yes (cloud viewers) | Links/reports only; no pixel work |
| (c) Payments | **Stripe Connect+Terminal — public self-serve**; Sunbit BNPL toggles on via Stripe | Easy–Medium | n/a | **Build** |
| (c′) Financing | CareCredit = gated real API (Weave precedent); Scratchpay = none | Hard | Yes (bridge) | BD now + operator bridge |
| (d) Accounting | **QBO** gated-public API (~80% US SMB share); Intacct partner-gated for 20–150-clinic groups | Easy–Medium / Med-Hard | Intacct RPA documented | **Build QBO**; Xero on demand only |
| (e) Scheduling | **Deputy — public self-serve, read+write shifts+labor cost** | Easy | n/a | **Build** |
| (e′) Payroll reads | **Finch unified API** → ADP/Paychex/Gusto/Paycom | Easy–Medium | Finch assisted mode IS a human-API | **Build via Finch** |
| (f) Procurement | **No cross-distributor pricing API exists.** Vetcove API = order/inventory sync only; comparison lives in the portal | Med-Hard (partial) | **Yes — and it's the PRIMARY architecture for F2** | Guided-operator Vetcove + Midwest client-secret ordering |
| (g) Insurance POS | **Trupanion only** (gated OAuth, full POS in ezyVet only); all 8 others human-only | Med-Hard | Yes for 8 of 9 (not Lemonade) | Trupanion BD + operator filing (IPH brands) |
| (h) Wellness plans | No public APIs; in-PIMS native modules dominate | Easy (native UI) | Yes, universally | Operator over PIMS module |
| (i) PDMP | **Bamboo PMP Clearinghouse: ASAP file over SFTP** — no REST API exists; ~18 states mandate vet reporting | Medium | Yes (portal upload) | Build ASAP generator; staged human upload |
| (j) Teletriage | **No APIs anywhere** — warm phone transfer is the integration | Easy (Twilio `<Dial>`) | Inherently human | Partner VetTriage; displace GuardianVets |
| (k) Comms rails | **Fully public APIs** (the only such category) — Twilio default, Telnyx challenger; WhatsApp US = defer | Easy–Medium | n/a | **Build**; own 10DLC as ISV |
| (l) PIMS estate | 4 tiers: open (Vetspire/Provet/DaySmart) → gated (Digitail/Instinct/IDEXX DS) → on-prem agent (Impromed/IntraVet/AVImark) → human-only (Mars internals, Covetrus-while-paused) | Varies | Yes, everywhere | ezyVet private track for pilot; adapter portfolio for F6 |

## The 5 integrations that matter most for V0.2

1. **Twilio (voice + SMS, with Telnyx bake-off)** — F1 is V0.2's headline and comms is the only fully-public-API category; ~$0.0785/min (Twilio ConversationRelay all-in platform-side) vs ~$0.05/min (Telnyx) feeds R7/R8 pricing directly; 10DLC ISV registration is the real work item (R2).
2. **Stripe Connect + Terminal** — the payments rail for F4, the only self-serve API in its category, carries platform economics (app fees + rev-share) and unlocks Sunbit BNPL as a near-free financing toggle; positions Vera before every PIMS finishes becoming its own payfac.
3. **QuickBooks Online (not Xero)** — F4's accounting read at ~80% US SMB share; the July-7 Xero pick was an ezyVet-lineage artifact; Xero's Mar-2026 connection+egress pricing makes it strictly worse for the US.
4. **Trupanion partner API** — the single point-of-sale insurance rail in the market (confirmed: literally no one else has POS claims); direct revenue-visible value at checkout; BD-gated, so start now (R9).
5. **Vetcove via guided-operator (+ Midwest client-secret for ordering)** — F2's price-comparison promise is deliverable *only* through the clinic's own Vetcove portal account; this is the flagship proof of the human-API pattern, and the MWI–Covetrus merger makes distributor-native alternatives less likely, not more.

(Deputy + Finch are #6–7 — cheap, real APIs that make F3/F4 credible fast.)

## Biggest surprise vs July-7 assumptions

**The July-7 board modeled the wrong hostile counterparty for half of V0.2's surface.** It priced IDEXX risk exquisitely — but: (1) **Covetrus Connect is PAUSED to all new integrations with no reopen date** (verified), closing the sanctioned door to AVImark/Impromed/Pulse — a large fraction of any F6 mixed estate — while (2) the **Feb-2026 MWI–Covetrus merger** consolidates two of the big-three distributors under one owner with every incentive to keep pricing opaque, striking directly at F2's premise; and (3) **GuardianVets re-launched as an AI-voice product with a fresh $7M Series A** — the July-7 model booked them as a $200–300/mo displaced line item, not a funded head-on F1 competitor. Secondary surprises: Vetspire's fully self-serve GraphQL keys (the openness outlier nobody flagged); the ezyVet private-API ban on SMS/payment functionality outside ezyVet's framework (new constraint on F1/F4 wiring); and the IDEXX "~79%" figure failing verification (best-sourced ≈45% of overall vet diagnostics — the 79% is *IDEXX's CAG-segment share of IDEXX's own revenue*, a different number that the corpus has been quietly conflating).

## Key Risks

1. **Covetrus dark territory (High × High for F6):** no sanctioned API path to AVImark/Impromed/Pulse today; if Connect reopens with ezyVet-style hostile terms, the on-prem-agent/guided-operator path becomes permanent for ~a third of typical mixed estates.
2. **ezyVet private-API scope trap (Medium × High):** the no-SMS/no-payments-outside-framework clause means F1/F4 must run architecturally *beside* the PIMS integration, not through it — needs counsel review alongside the July-7 §3.2 analysis.
3. **GuardianVets time-to-market (Medium × High for F1):** a funded incumbent already sells "AI voice + after-hours + PIMS write-back" to our exact ICP; after-hours-first is now a race, not open field.
4. **Credit-flow automation liability (Medium × High):** guided-operator over CareCredit/Scratchpay portals touches lending screens — ToS + FCRA/UDAAP exposure; bridge only with counsel sign-off.
5. **BD-gated dependency stack (structural):** the highest-value integrations (Trupanion, CareCredit, Vetcove, IDEXX Data Services) are all human-approved partner programs owned by parties with competing interests; every one needs a human-API fallback in the architecture from day one, or it's a kill switch.
6. **Verification debt:** PIMS rows marked ◐, IDEXX diagnostics share, PDMP state counts (2019–21 baseline), and all rev-share economics need per-deal confirmation.

## Implications for V0.2 (feed the program definitions)

1. **Promote guided-operator from fallback to first-class product capability** (COS-platform pattern, per phase-4 F2 design): it is the *primary* architecture for procurement (F2), insurance filing (8 of 9 carriers), wellness ops, and the Covetrus PIMS tier — budget it as a platform investment with per-vendor ToS review, not per-feature hacks.
2. **Spec 010 (voice):** contract Twilio default + Telnyx challenger; one ISV 10DLC brand with pooled campaigns (R2); VetTriage warm-transfer partnership as the DVM escalation (fills the Expert-Firewall gap); explicitly position against GuardianVets OS in the pilot pitch.
3. **Spec 011 (procurement):** design around the clinic's own Vetcove account (vision-guided compare+checkout) + Midwest client-ID ordering; request Vetcove's OpenAPI spec under NDA to settle whether any pricing endpoint exists; do NOT plan on distributor APIs.
4. **Spec 013 (financial copilot):** QBO replaces Xero as the default connector; Stripe Connect as the rail; Finch for labor-cost reads; Intacct connector deferred to the first 20+ clinic group customer.
5. **Spec 012 (staff scheduling):** Deputy adapter first (read+write, self-serve) — it doubles as the migration path when Vera's own rostering engine displaces it.
6. **Spec 015 (enterprise/F6):** the PIMS-adapter portfolio must include an **on-prem agent tier** (MS-SQL readers for Impromed/IntraVet; file-layer for AVImark) and a **human-API tier** (Covetrus cloud, Mars) — pure-API coverage tops out well short of a 400-clinic mixed estate; price a Bitwerx/DataHub-class license/acquisition as the alternative.
7. **New cheap wedge worth a spec seed: PDMP compliance** — ~18 states, one counterparty, ASAP-file-over-SFTP, federally documented PIMS-vendor neglect; Vera generates the file, staff uploads, automation follows. High compliance-value per engineering dollar, and it deepens the controlled-substance story enterprise buyers ask about.
8. **Start the three long-cycle BD applications now** (they gate later specs, not V0.2 code): Trupanion (TruExLaunch), Synchrony/CareCredit (Weave precedent), Vetcove Partner Integrations; add an Independence Pet Holdings conversation — one deal covers Spot/Embrace/Pumpkin/Pets Best.

## Open Questions

1. Does Vetcove's partner API expose *any* pricing/comparison endpoint, or strictly order/inventory sync? (Request OpenAPI spec under NDA.)
2. What are IDEXX Data Services' actual terms/cadence for Cornerstone — and would IDEXX grant them to us given the ezyVet relationship?
3. When does Covetrus Connect reopen, and on what terms? (Their "updating partnership framework" could land friendlier *or* ezyVet-style.)
4. Do Trupanion's Vet Portal ToS permit a third-party operator/agent acting for the practice?
5. Exact 2026 state-by-state vet PDMP mandate list (AVMA member tracker) — our count is a refreshed 2019–21 baseline.
6. Does the ezyVet private-API SMS/payments ban reach functionality merely *adjacent* to the integration (Vera's own Twilio/Stripe rails), or only functionality delivered through the API? (Counsel.)
7. Unverified ◐ PIMS rows — especially Neo export, AVImark file format, Shepherd/Rhapsody API reality — before F6 adapter costing.

## Where I expect other lanes disagree

- **Strategy/legal lane** will likely read my "guided-operator as primary architecture" as compounding ToS exposure across a dozen vendors, not just IDEXX. My response: the operator acts on the clinic's own credentials on the clinic's own accounts — the July-7 rung-③ logic — but I concede credit/lending portals (CareCredit) are a genuinely different risk class and need counsel.
- **Voice/product lane** may treat GuardianVets as validation ("the category is real"). I score them as the single most dangerous F1 fact: funded, incumbent client base, already integrated. The disagreement is whether after-hours-first is still a wedge or now a contested beach.
- **Architecture lane** will want one clean `PimsAdapter` port; my finding is the enterprise estate forces *three* adapter species (API, on-prem agent, vision/human) with different latency, reliability, and legal envelopes — the port abstraction has to carry that, or F6 estimates will be fiction.
- **Anyone still citing "IDEXX = 79% of diagnostics"** — that's IDEXX's own revenue mix (CAG share of IDEXX revenue), not market share (~45% best-sourced). The strategic conclusion (diagnostics-accretive = shield) survives, but the number should stop appearing in external material.
- **Finance/GTM lane** may prefer Xero continuity (already scoped, 3–5 days). The US market data says QBO — the 3–5-day estimate was never the real cost; the Intuit app assessment is.
