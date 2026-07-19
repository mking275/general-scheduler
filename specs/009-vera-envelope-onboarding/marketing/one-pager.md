# Vera's First Day — She Arrives Already Knowing Your Practice

**For**: group owner / operations manager · **One page** · reusable across multi-site operators (no client names)

> The move you've done before had a switch-over date, staff retraining, and the quiet risk that some open balances didn't come across. This has none of that. VetAgent reads each practice's own records and Vera arrives already knowing the practice — verified down to the accounts-receivable balance, with nothing for your staff to learn. The figures marked *(build-proven)* are green in our engineering test suite (111 envelope tests inside a 411-test suite); the numbers we'll report to you are measured live on your own records at the pilot.

---

## What "already knows your practice" means

Your group's own complete records arrive. Before Vera says a useful word about any practice, VetAgent has:

- **Received every practice's data under chain of custody** — into a clinic-owned, encrypted vault, each file fingerprinted, timestamped, and checked against exactly what was requested, before anything is interpreted.
- **Profiled each database before mapping a single record** — so the structure is discovered, never guessed. (Guessing the structure is how a data move silently drops financials or scrambles identities.)
- **Loaded it into one canonical practice model with full lineage** — every loaded record traces back to the exact source record it came from, so every fact Vera later states can be traced.
- **Verified it's complete and clean** — every requested category present and counted, including **financials, AR, and inventory**, with dirty-data signals (shared phones, duplicate owners, deceased pets, orphaned records) quantified.
- **Handed the owner a reconciliation report** — requested vs delivered vs loaded, by category, with the financials tied back to your own reported numbers.

Your front desk, meanwhile, does exactly what it did yesterday. There is no switch-over, no new login, nothing to learn.

---

## Why you can trust putting it live

The guarantees are rails below the pipeline, enforced and red-teamed — not promises on a slide:

- **Your accounts receivable reconcile exactly, or the practice doesn't activate.** Zero tolerance on AR: any unexplained accounts-receivable variance is a blocking discrepancy that holds the practice, surfaced in red and itemized. Invoice and payment variances are each itemized and must be attributed to a cause, or they block too *(build-proven: a planted AR variance blocks; 0 silent AR discrepancies pass)*.
- **A legal sign-off gate before we read a record.** Not one record is normalized into the practice model until a counsel sign-off on the clinic-owned-data structure is recorded. Your data stays your data *(build-proven across a full batch: 0 databases advance without a recorded sign-off)*.
- **A quality floor that holds bad data back.** A practice where more than 20% of sampled records are unusable is **held** out of activation with its gap itemized — never quietly shipped on dirty data *(build-proven: the below-floor practice is held and never marked ready)*.
- **A re-run can't corrupt anything.** Loading the same data twice produces a zero-row difference — no duplicates, stable identifiers, 100% of records still resolving to their source. It's a go-live gate *(build-proven: the idempotency re-run-diff proof)*.
- **A partial delivery never passes as complete.** If something requested is missing, VetAgent detects the gap, gives you a paper-trail-ready gap notice, proceeds on what did arrive, and later folds in the remainder with no duplicates — and never marks the practice complete until it is *(build-proven: 100% of partial deliveries detected, 0 silently accepted)*.
- **Nothing your staff will ever see.** A batch-wide red-team scan proves **zero** staff-facing artifacts — no logins, training, dashboards, or notifications — even when a clinician appears in the export *(build-proven: 0 staff-facing artifacts, SC-006)*.

---

## What you'll see (owner and manager only)

Every onboarding surface is yours alone — staff get nothing pushed at them.

| What you get | What it shows |
|---|---|
| **Group rollup** | Every practice's stage and status at a glance, across the whole group |
| **Per-practice drill-down** | From the group view into any single practice's reconciliation |
| **Reconciliation report** | Requested vs delivered vs loaded by category, plus the financial reconciliation (AR / invoices / payments) tied to your own numbers, variances itemized |
| **Gap notices** | Owner-facing, paper-trail-ready record of anything a delivery was missing |
| **One acknowledgment to activate** | A single group-level acknowledgment flips the reconciled practices to ready — with drill-down to each practice's reconciliation before you sign off |

As the batch runs, each new practice reuses what the last one learned, so per-practice effort trends toward a paste — and the same process works across whatever systems your practices run.

---

## The one number that's a target, not a result

We are **designed** to make the **first practice ready within about a week of receiving your data**, with the full group reconciled inside a several-week window — and, unlike every version of this you've done before, **with nothing to switch over at the end**. That one-week figure is a **design target**; it is the number we'll measure on your data at the pilot, not a result we're claiming as achieved.

---

*Everything marked build-proven is green in our engineering test suite (111 envelope tests inside a 411-test suite, all passing at the final checkpoint). Going live on your group is validation on your real, audited records — confirming the reconciliation and the one-week target on your data — not more building. Internal + committed-pilot use only; not for public distribution, and subject to product-truth validation before any external use.*
