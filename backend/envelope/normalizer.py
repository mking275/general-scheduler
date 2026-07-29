"""Feature 009 — T018/T019/T020 canonical normalizer.

Canonical load into the platform practice model (+ the net-new financial/AR/
ledger/payment + inventory tables), driven through the adapter's ``normalize()``.
The core stays PIMS-agnostic: it calls the adapter **only** through the port
(``resolve_adapter``), never a concrete adapter module.

Three guarantees this module owns:

  * **Lineage (T018)** — every canonical record is persisted with its
    ``source_id`` / ``entity_ref`` lineage (seeded via
    ``backend/relationship/entity_ref.py`` inside the adapter). 100% of records
    resolve back to a specific source row via their ``entity_ref``; the
    ``entity_ref`` keys are byte-identical to what 011's resolver consumes.
  * **Idempotency (T019)** — deterministic ``source_id`` keys + a delete-then-
    insert upsert on the lineage key: re-running ingest against the same source
    yields **no duplicate records and stable identifiers** (FR-010; the
    re-run-diff gate T038 proves it formally).
  * **Unmapped preservation (T020)** — a source field with no canonical target
    is preserved in the ``unmapped_field_sidecar`` (tied to the owning record's
    lineage), never silently discarded (FR-008 US3-scenario-3).

Every record lands in the generic ``canonical_record`` spine (all categories —
the idempotency/lineage diff target and the clinical/scheduling hydration store);
financial/inventory categories ALSO land in their typed net-new tables (the
reconciliation/completeness read models).
"""
from __future__ import annotations

from typing import Any
from uuid import uuid4

from backend.envelope.pims.port import NormalizeResult
from backend.models import (
    ARBalance, InventoryItem, InvoiceRecord, LedgerEntry, PaymentRecord,
)

# canonical category -> (typed table name, model, numeric fields to coerce)
_TYPED: dict[str, tuple[str, Any, tuple[str, ...]]] = {
    "ledger": ("ledger_entry", LedgerEntry, ("amount",)),
    "invoice": ("invoice_record", InvoiceRecord, ("total",)),
    "payment": ("payment_record", PaymentRecord, ("amount",)),
    "ar_balance": ("ar_balance", ARBalance, ("balance",)),
    "inventory": ("inventory_item", InventoryItem, ("qty_on_hand",)),
}


def _as_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


class NormalizationYieldError(RuntimeError):
    """Raised when a non-empty profile normalizes to zero records — a mapping
    failure that would otherwise pass silently through every later stage."""


class Normalizer:
    def __init__(self, repo):
        self.repo = repo

    # ------------------------------------------------------------------ #
    #  normalize — the single canonical-load path
    # ------------------------------------------------------------------ #
    def normalize(self, clinic_id: str, practice_id: str, adapter,
                  profile, raw_export: Any) -> NormalizeResult:
        """Load one profiled database into the canonical store via the adapter.
        Idempotent: safe to re-run against the same source (0 duplicates)."""
        result: NormalizeResult = adapter.normalize(profile, raw_export)

        # EMPTY-YIELD GUARD. A profile that found rows but a normalize that
        # produced none is a MAPPING failure, not an empty practice — and it is
        # the most dangerous shape this pipeline can take, because every
        # downstream stage happily reports success on zero records: completeness
        # computes, quality assesses, the state machine advances to `verified`,
        # and an operator reads a green run over an empty database.
        #
        # This is not hypothetical. On the first real delivery (Coastal Creek,
        # 2026-07-29) the adapter keyed rows by nested path while the entity map
        # keyed by basename; 618,109 profiled rows normalized to ZERO and the
        # pipeline reported verified. Fail loudly instead.
        profiled_rows = sum((profile.entities or {}).values())
        if profiled_rows > 0 and not result.records:
            raise NormalizationYieldError(
                f"normalize produced 0 records from {profiled_rows:,} profiled rows "
                f"for practice={practice_id!r} — the adapter mapped nothing. This is a "
                f"mapping/keying failure, not an empty practice; refusing to advance."
            )

        # 1) generic canonical spine — every category, lineage on 100% of rows.
        generic_rows: list[dict] = []
        for rec in result.records:
            generic_rows.append({
                "id": str(uuid4()),
                "clinic_id": clinic_id,
                "practice_id": practice_id,
                "category": rec.category,
                "entity_ref": rec.entity_ref,
                "source_id": rec.source_id,
                "payload": rec.payload,
                "unmapped_fields": rec.unmapped_fields,
            })
        if generic_rows:
            self.repo.upsert_canonical(
                "canonical_record", generic_rows,
                key_cols=("practice_id", "entity_ref"))

        # 2) typed financial / inventory read models.
        for category, (table_name, model, numeric) in _TYPED.items():
            typed_rows = [
                self._typed_row(model, numeric, clinic_id, practice_id, rec)
                for rec in result.records if rec.category == category
            ]
            if typed_rows:
                self.repo.upsert_canonical(
                    table_name, typed_rows,
                    key_cols=("practice_id", "source_id"))

        # 3) unmapped-field sidecar (T020) — never silently dropped. Keyed on the
        #    owning record's lineage + the source field so a re-run is idempotent.
        sidecar_rows: list[dict] = []
        for uf in result.unmapped_fields:
            if "source_field" not in uf:
                continue                      # a row-level flag (e.g. missing id)
            sidecar_rows.append({
                "id": str(uuid4()),
                "clinic_id": clinic_id,
                "practice_id": practice_id,
                "entity_ref": uf.get("entity_ref", ""),
                "source_field": uf["source_field"],
                "raw_value": _stringify(uf.get("raw_value")),
            })
        if sidecar_rows:
            self.repo.upsert_canonical(
                "unmapped_field_sidecar", sidecar_rows,
                key_cols=("practice_id", "entity_ref", "source_field"))

        return result

    # ------------------------------------------------------------------ #
    #  payload (canonical field names) -> typed model row
    # ------------------------------------------------------------------ #
    @staticmethod
    def _typed_row(model, numeric: tuple[str, ...], clinic_id: str,
                   practice_id: str, rec) -> Any:
        fields = {name for name in model.model_fields}
        kwargs: dict[str, Any] = {
            "clinic_id": clinic_id,
            "practice_id": practice_id,
            "entity_ref": rec.entity_ref,
            "source_id": rec.source_id,
        }
        for key, val in rec.payload.items():
            if key in ("source_id",) or key not in fields:
                continue
            kwargs[key] = _as_float(val) if key in numeric else val
        return model(**kwargs)


def _stringify(value: Any) -> str:
    return "" if value is None else str(value)
