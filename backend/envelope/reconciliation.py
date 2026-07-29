"""Feature 009 — T024 reconciliation report + T025 zero-AR-tolerance guard.

The per-practice **ReconciliationReport**: requested-vs-delivered-vs-ingested
counts by §5 category + **financial reconciliation** (AR balances, invoice totals,
payment totals) tied back to the source's own reported figures (the fixture's
synthetic reported figures in this build), with every variance itemized (FR-016).

**Zero-AR-tolerance (T025, FR-017)** — any *unexplained* AR-balance variance is a
**blocking** discrepancy (surfaced red, not buried): an AR variance with no
attributed cause makes the report ``blocking``, which the state-machine
``ar_variance`` guard reads to hold the practice out of ``reconciled``/
``shadow_ready``. Invoice/payment-total variances are itemized with an attributed
cause **or they block**.

The report is **append-only** (a new version is appended, never updated in place);
the owner-acknowledgment (T026) is likewise a fresh appended version.
"""
from __future__ import annotations

from typing import Any, Optional

from backend.envelope.completeness import SCOPE_CANONICAL
from backend.models import (
    FinancialVariance, ReconciliationReport, VarianceDisposition,
)

_EPS = 0.01


def _variance(ingested: float, reported: float,
              cause: Optional[str]) -> FinancialVariance:
    """Itemize one financial variance. Nonzero + no attributed cause -> blocking;
    zero or attributed -> explained."""
    amount = round(ingested - reported, 2)
    if abs(amount) > _EPS and not cause:
        return FinancialVariance(amount=amount,
                                 disposition=VarianceDisposition.BLOCKING)
    return FinancialVariance(amount=amount,
                             disposition=VarianceDisposition.EXPLAINED,
                             attributed_cause=cause)


class Reconciler:
    def __init__(self, repo):
        self.repo = repo

    def reconcile(self, clinic_id: str, practice_id: str,
                  reported_figures: dict[str, Any],
                  attributed_causes: Optional[dict[str, str]] = None,
                  derived_figures: Optional[dict[str, str]] = None,
                  ) -> ReconciliationReport:
        """Build + append the reconciliation report. ``reported_figures`` are the
        source system's own numbers (``ar_balance_total`` / ``invoice_count`` /
        ``payment_total``); ``attributed_causes`` optionally explains an
        ``invoice``/``payment``/``ar`` variance (an unexplained AR variance always
        blocks).

        ``derived_figures`` names any figure this report COMPUTED rather than read
        from the source, mapped to the reason the source could not supply it. Every
        such figure carries its reason into the owner-facing report — a derived
        number presented as though it were the source's own is the dishonest version
        of this report, and is exactly the failure a competitor's customers
        discovered only after their open balances went missing.

        Real case (2026-07-29): ezyVet's complete export ships no accounts-receivable
        aging file and no per-client balance, so ``ar_balance_total`` is derived from
        invoice line items less payments and MUST be disclosed as such."""
        causes = attributed_causes or {}
        derived = derived_figures or {}
        completeness = self.repo.get_completeness_result(practice_id)
        profile = self.repo.get_format_profile(practice_id)
        profiled_entities: dict[str, int] = (profile or {}).get("entities") or {}

        coverage: dict[str, dict] = (completeness or {}).get("category_coverage") or {}

        # per-category requested / delivered / ingested counts.
        category_counts: dict[str, dict[str, int]] = {}
        outstanding_gap: list[str] = []
        for scope_cat in SCOPE_CANONICAL:
            cov = coverage.get(scope_cat, {})
            delivered = int(cov.get("profiled", 0))
            ingested = int(cov.get("ingested", 0))
            present = bool(cov.get("present", delivered > 0 or ingested > 0))
            # we requested every §5 category; when absent, requested is unknown-
            # but-nonzero and the category is an outstanding gap.
            requested = delivered if present else 0
            category_counts[scope_cat] = {
                "requested": requested, "delivered": delivered, "ingested": ingested,
            }
            if not present or cov.get("short"):
                outstanding_gap.append(scope_cat)

        # financial reconciliation vs the source's reported figures.
        ing_ar = float((completeness or {}).get("ar_balance_total", 0.0))
        ing_inv = float((completeness or {}).get("invoice_count", 0.0))
        ing_pay = float((completeness or {}).get("payment_total", 0.0))
        ar_var = _variance(ing_ar, float(reported_figures.get("ar_balance_total", ing_ar)),
                           causes.get("ar"))
        inv_var = _variance(ing_inv, float(reported_figures.get("invoice_count", ing_inv)),
                            causes.get("invoice"))
        pay_var = _variance(ing_pay, float(reported_figures.get("payment_total", ing_pay)),
                            causes.get("payment"))

        blocking = any(v.disposition == VarianceDisposition.BLOCKING
                       for v in (ar_var, inv_var, pay_var))

        # A DERIVED figure has no independent source number to tie to, so its
        # variance is arithmetic identity, not evidence. Recording the reason keeps
        # the report honest: "this reconciles" and "we computed both sides" are
        # different claims and the owner is entitled to know which one they have.
        disclosures = [
            f"{figure}: {reason}" for figure, reason in sorted(derived.items())
        ]

        report = ReconciliationReport(
            clinic_id=clinic_id, practice_id=practice_id,
            category_counts=category_counts,
            ar_variance=ar_var, invoice_variance=inv_var, payment_variance=pay_var,
            outstanding_gap=sorted(set(outstanding_gap) | set(disclosures)),
            blocking=blocking, owner_acknowledged=False, audience="owner",
        )
        self.repo.append_reconciliation_report(report)
        return report
