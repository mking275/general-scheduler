# Marketing Brief: Vera's First Day — She Arrives Already Knowing Your Practice

**Feature**: 009-vera-envelope-onboarding (Vera Envelope Onboarding — "Vera's First Day": data receipt → verified, reconciled, shadow-ready)
**Stage**: Stage 2 — Implementation (demo-grade, pilot committed)
**Generated**: 2026-07-19
**Source**: speckit-marketing — compiled from the 009 speckit lifecycle artifacts (spec / plan / tasks `## Marketing Output` sections) + the T045 final-checkpoint SC coverage
**Audience (priority)**: (1) group owner / operations manager (pilot-facing and reusable for PE-owned multi-site operators); (2) proof-points companion — see `proof-points.md`; owner one-pager copy — see `one-pager.md`

> **Claim discipline**: Every factual claim traces to `../../../marketing/engine-inputs/verified-claims.md` (`[VC-n]`) or the 009 build evidence (the 111-test envelope suite inside the 411-test project suite, all green at the T045 checkpoint), cited as such. Scope is the **on-ramp only** — from the moment your group's own data copies arrive to the moment each practice is verified, reconciled, and marked *ready* (what the build calls shadow-ready). Ongoing operation of the assistant is a separate feature and is not claimed here. **The word we never use is "ready" as an achieved clock result**: "the first practice ready within about a week of receiving your data" is a **design target the pilot will confirm (SC-007)**, not a measured outcome — it is marked as such everywhere below. The forbidden framing — a data "migration", a "cutover", a "conversion" — is intentionally absent: Vera reads the practice's own records and arrives already knowing it; staff experience nothing new.

---

## Elevator Pitch

**One sentence**: VetAgent reads your group's own records and Vera arrives already knowing each practice — verified down to the last accounts-receivable balance, with nothing for your staff to learn.

**Three sentences**: Adopting a new system usually means a data move you have to survive — a switch-over date, staff retraining, and the quiet dread that some open client balances didn't come across. Here there is no such day: VetAgent turns each practice's own delivered records into a working assistant that already knows that practice, and hands the owner a reconciliation report — clinical, scheduling, and the financials — that ties back to the practice's own numbers before anything goes live. Your accounts receivable reconcile exactly, or the practice doesn't activate; meanwhile your front desk keeps working exactly as it does today, because there is nothing to switch over and nothing new to log into.

**Paragraph** (~95 words): You've done a data move before and you remember the parts that hurt: the switch-over weekend, the training, and finding out weeks later that thousands in open client balances never transferred. VetAgent does the opposite. Your group's own records arrive, and Vera reads them into a working assistant that already knows each practice — every record traceable back to where it came from. Before a single practice activates, the owner gets a reconciliation report proving what was received, what was loaded, and that the financials — AR, invoices, payments — tie back to your own reported figures. Any unexplained AR variance blocks activation. Your staff experience nothing new.

---

## Why Now

Your group is likely re-evaluating its systems anyway: the market is in the biggest practice-management displacement wave in decades — the largest legacy system has no cloud roadmap and the next is being sunset, forcing 25,000+ practices to evaluate alternatives over the next few years `[VC-1]`. When a large operator re-evaluates, the deciding fear isn't features — it's the move itself, and the single worst story on record in this category is a data move that "didn't promise financial history": open client balances that silently didn't transfer, thousands in revenue lost, discovered too late [spec.md — competitive bar]. That fear is exactly what this on-ramp is built to retire. The category markets a roughly one-week sandbox and weeks of hand-holding but does **not** promise your financials reconcile; VetAgent meets that time bar as a design target **and** closes the financial gap with a reconciliation the owner can trust — with nothing to switch over at the end [spec.md — Problem Statement; SC-007].

---

## Key Benefits

In the words our customers would use:

1. **No move to survive — she just already knows the practice.** VetAgent reads each practice's own delivered records into a working assistant; there is no switch-over date, no retraining, and nothing new for your staff to log into. The invisible-adoption guarantee is enforced, not promised: a batch-wide red-team scan proves **zero** staff-facing artifacts — no logins, no training, no dashboards, no notifications — even when a clinician appears in the export `[009 build evidence: invisible-adoption red-team scan, SC-006 / test_invisible_adoption.py]`.
2. **Proof nothing was lost — down to the AR balance.** Before any practice goes live, the owner gets a reconciliation report: what was requested, what was delivered, what was loaded, by category — and the financials (AR, invoices, payments) tied back to the practice's own reported numbers, every variance itemized. **Your accounts receivable reconcile exactly, or the practice doesn't activate** `[009 build evidence: zero-AR-tolerance reconciliation gate, FR-017 / test_financial_recon.py]`.
3. **It scales the way your group does.** Every practice onboards as its own independent unit with a group-level rollup and drill-down into each practice's reconciliation; one blocked practice never stalls the rest; and the next practice reuses what the last one learned, so marginal effort trends toward a paste. The same core generalizes across whatever systems your practices run — new system, new adapter, no forked pipeline `[009 build evidence: batch orchestration + group rollup + prior inheritance, FR-024/025/026 / test_batch.py]`.

---

## What Makes This Different

**The reconciliation is the product, not the fine print.** Reviewability is what a large operator actually buys — and the trust centerpiece here is a financial reconciliation tied to the practice's *own* reported figures, with a **zero-tolerance rule on AR**: any unexplained accounts-receivable variance is a blocking discrepancy that holds the practice out of activation, surfaced red, never buried [spec.md FR-016/FR-017]. This is the precise failure that cost a competitor its customers — open balances that quietly didn't come across — and here it *cannot* pass silently. Invoice and payment variances are each itemized and must be attributed to an identified cause, or they block too.

**Four hard gates below the pipeline, not four promises on a slide.** The guarantees are structural rails the build enforces, red-teamed at the final checkpoint:
- **A legal sign-off gate before normalize** — not one record is read into the canonical practice model until a counsel sign-off on the clinic-owned-data structure is recorded. Your data stays your data, and the gate is provable across the whole batch [spec.md FR-004; T045 — 0 databases reach profiled/normalized without a recorded sign-off].
- **Zero-AR-tolerance reconciliation** — the benefit above, enforced as a blocking transition, not a report footnote [spec.md FR-017].
- **A quality floor** — a practice where more than 20% of sampled records are unusable is **held** out of activation with the gap itemized, never quietly shipped on dirty data [spec.md FR-015].
- **Profile-before-normalize** — the pipeline profiles each delivered database (entities, counts, encodings, relationships) *before* it maps anything; normalization is blocked until a profile exists, so the schema is never guessed. Guessing the schema is how a data move silently drops financials or mangles identities [spec.md FR-005/FR-006].

**Every fact is traceable, and a re-run can't corrupt the store.** Every loaded record carries lineage back to the exact source record it came from — so every fact Vera later states can be traced. And ingest is idempotent: re-run it and you get a zero-row diff — no duplicates, stable identifiers, 100% of records still resolving to their source. That re-run-diff proof is a go-live gate, not a nice-to-have [spec.md FR-009/FR-010; SC-003].

**Honesty about partial deliveries is a feature.** If a delivery arrives missing something that was requested (attachments and imaging are a known risk), the pipeline detects the gap against what was requested, produces an owner-facing, paper-trail-ready gap notice, proceeds on what *did* arrive, and later folds in the remainder with no duplicates — and never marks an incomplete practice as complete [spec.md FR-030/FR-031/FR-032; SC-009].

---

## Top 3 Objections + Answers

| Objection | Answer |
|---|---|
| "Every data move I've done lost something — how do I know my open balances came across?" | Because the practice can't activate until they reconcile. Before anything goes live you get a reconciliation report tying AR balances, invoice totals, and payment totals back to your own reported figures. The rule is zero tolerance on AR: any unexplained accounts-receivable variance is blocking — it holds the practice, surfaced in red, itemized, not buried. In the build this is a hard gate proven by a dedicated financial-reconciliation test; a planted AR variance blocks and zero silent AR discrepancies get through. The live figures are what we measure on your data at the pilot. |
| "What does my staff have to do, and when's the switch-over?" | Nothing, and there isn't one. There's no switch-over date, no training, no new login — VetAgent reads your practices' own records and Vera arrives already knowing each one. This isn't a promise; it's enforced. A batch-wide red-team scan checks the entire run for any staff-facing artifact — logins, training, dashboards, notifications — and the activation gate rejects any run that produced one. Even a clinician who shows up in the export gets a schedule entry, never an account. |
| "We're 100+ practices on more than one system — does this actually scale, or does it fork?" | It scales without forking. Each practice is its own independent unit — its own receipt, verification, reconciliation, and activation — rolled up into one group view you can drill into per practice. A blocked or held practice never stalls the others, and the next practice inherits what the last one learned, so per-practice effort trends down across the batch. The pipeline reads different systems through pluggable adapters behind one stable port — a new system is a new adapter, not a rebuilt core. |

---

## Claims Softened or Removed for Discipline (audit trail)

| Original / tempting claim | Why changed | As-published |
|---|---|---|
| "Practice ready within a week of receiving your data" as an achieved result | SC-007 is a **design target**; the build has no wall-clock proxy — only its enablers are proven. The calendar figure is measured at the pilot | Framed everywhere as "designed to" / "a design target the pilot will confirm (SC-007)", never as a measured outcome |
| "Migration" / "cutover" / "conversion" | Binding rule: customer-facing copy never uses these; the frame is that Vera reads the practice's own records and arrives already knowing it | Reframed as "no move to survive", "nothing to switch over", "she already knows the practice"; the three words appear nowhere in customer copy |
| "Zero staff-facing artifacts / zero duplicates / zero silent AR discrepancies" as live-clinic performance | These are build-suite results at the T045 checkpoint (111 envelope tests green), not live-clinic measurements | Cited as build evidence / red-team gates ("proven in the build"); live figures deferred to "what we measure on your data at the pilot" |
| Competitor named as the cautionary tale (the open-balance failure) | Rule: no competitor named in customer-facing copy | Told as "the single worst story on record in this category" / "a competitor's customers", no name |
| Legal mechanics of how the data is obtained (request clause, ToS sections) | Rule: no ToS/§5/legal-strategy mechanics in customer copy | Reduced to a product-safety framing: "a legal sign-off gate before we read a single record; your data stays your data" |
| Naming Vera as the thing being bought | Naming rule: VetAgent is the product (bought); Vera is the differentiator (experienced) | "VetAgent reads your records; Vera arrives already knowing the practice" |

---

## Source Artifacts

| Artifact | Used for |
|---|---|
| spec.md `## Marketing Output` | Feature name, 3 benefits, one-liner, guidance note |
| spec.md User Scenarios / FR-001–FR-033 / SC-001–SC-010 | The four hard gates, reconciliation, invisible adoption, batching, partial-delivery |
| plan.md `## Marketing Output` (Demo Flow Sketch) | The five-beat owner story (arrival → gate → reconciliation → held practice → invisible payoff) |
| tasks.md (T045 checkpoint; Demoable-milestone table) | Announcement-blocking gates; the 111-test envelope suite; build-proven vs pilot-deferred split |
| engine-inputs/verified-claims.md | Claim discipline (`[VC-n]`); VC-9 overlay-layer framing; VC-11 (concrete, numeric, never hype) |

---

*Stage-gated note: at Stage 2, speckit-marketing mandates the brief + demo/enablement copy for the committed pilot only. GTM materials (changelog, blog, social — Stage 5; sales deck — Stage 6; case study/press — Stage 7) are intentionally NOT generated. `one-pager.md` and `proof-points.md` in this directory are owner-facing and reusable across the multi-site ICP (no client names), not cold-prospect GTM assets.*

**These artifacts are for internal use and the committed pilot only. NEVER publish, post, or distribute without human review and product-truth validation — including confirmation of the SC-007 timing target on live pilot data, which is a design target until measured.**
