"""Feature 009 — T021 per-practice completeness verification.

Category coverage + record counts vs the ``FormatProfile`` + referential-integrity
checks; flags any missing or short category. Explicitly covers **financial/AR/
inventory**, computing AR-balance totals, invoice counts, and payment totals for
the downstream reconciliation (FR-012/013).

Coverage per §5 ``scope_category``:
  * ``present`` — at least one of the category's canonical categories has ingested
    records;
  * ``short``   — present, but fewer records ingested than the profile declared for
    the category's source entities (records were dropped / failed to map);
  * absent      — no ingested records (surfaced in ``missing_or_short``).

A category-lopsided practice (financials reconcile, clinical thin) is surfaced
category-aware — each category carries its own coverage line.
"""
from __future__ import annotations

import os
from typing import Any, Optional

import yaml

from backend.models import CompletenessResult

_CONFIG = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "config", "envelope", "section5_scope.yaml",
)

# §5 scope_category -> the canonical CanonicalRecord.category values that satisfy it.
SCOPE_CANONICAL: dict[str, list[str]] = {
    "patient_client": ["client", "patient"],
    "scheduling": ["appointment", "provider"],
    "invoicing_billing_payments": ["invoice", "ledger", "payment", "ar_balance"],
    "communications": ["communication"],
    "attachments_imaging": ["attachment"],
    "configuration": ["product_service", "inventory"],
}


class CompletenessChecker:
    def __init__(self, repo, config_path: Optional[str] = None):
        self.repo = repo
        with open(config_path or _CONFIG) as f:
            cfg = yaml.safe_load(f)
        # scope_category -> the ezyVet source entities the §5 letter requested
        self.scope_source: dict[str, list[str]] = {
            c["key"]: c["source_entities"] for c in cfg["categories"]
        }

    # ------------------------------------------------------------------ #
    def check(self, clinic_id: str, practice_id: str) -> CompletenessResult:
        profile = self.repo.get_format_profile(practice_id)
        profiled_entities: dict[str, int] = (profile or {}).get("entities") or {}
        records = self.repo.list_canonical_records(practice_id)

        by_cat: dict[str, list[dict]] = {}
        for r in records:
            by_cat.setdefault(r["category"], []).append(r)

        category_coverage: dict[str, dict[str, Any]] = {}
        missing_or_short: list[str] = []
        for scope_cat, canon_cats in SCOPE_CANONICAL.items():
            source_entities = self.scope_source.get(scope_cat, [])
            profiled = sum(int(profiled_entities.get(e, 0)) for e in source_entities)
            ingested = sum(len(by_cat.get(c, [])) for c in canon_cats)
            present = ingested > 0
            short = present and profiled > ingested
            category_coverage[scope_cat] = {
                "present": present, "ingested": ingested,
                "profiled": profiled, "short": short,
            }
            if not present or short:
                missing_or_short.append(scope_cat)

        findings = self._referential_integrity(by_cat)

        # financial block — the reconciliation source figures (from typed tables).
        ars = self.repo.list_canonical("ar_balance", practice_id)
        payments = self.repo.list_canonical("payment_record", practice_id)
        ar_total = round(sum(_f(a["balance"]) for a in ars), 2)
        invoice_count = self.repo.count_canonical("invoice_record", practice_id)
        payment_total = round(sum(_f(p["amount"]) for p in payments), 2)

        result = CompletenessResult(
            clinic_id=clinic_id, practice_id=practice_id,
            category_coverage=category_coverage,
            referential_integrity_findings=findings,
            ar_balance_total=ar_total, invoice_count=invoice_count,
            payment_total=payment_total,
            missing_or_short=sorted(set(missing_or_short)),
        )
        self.repo.create_completeness_result(result)
        return result

    # ------------------------------------------------------------------ #
    #  Referential integrity — orphaned patient -> client edges.
    # ------------------------------------------------------------------ #
    @staticmethod
    def _referential_integrity(by_cat: dict[str, list[dict]]) -> list[dict]:
        client_ids = {str(c["payload"].get("source_id", c["source_id"]))
                      for c in by_cat.get("client", [])}
        findings: list[dict] = []
        for p in by_cat.get("patient", []):
            owner = p["payload"].get("client_source_id")
            if owner is not None and str(owner) not in client_ids:
                findings.append({
                    "kind": "orphaned_ref", "category": "patient",
                    "entity_ref": p["entity_ref"], "missing_client": str(owner),
                })
        return findings


def _f(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
