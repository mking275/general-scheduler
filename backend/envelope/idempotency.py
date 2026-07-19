"""Feature 009 — re-run-diff idempotency + lineage helper (T019/T031/T038/T045).

The formal proof behind SC-003 and one of the six readiness criteria: normalizing
the **same** source a second time must produce a **0-row diff** against the first
load — no duplicate records, stable identifiers — and **100%** of canonical
records must resolve back to a source record via ``entity_ref``/``source_id``.

The diff target is the generic ``canonical_record`` lineage spine (keyed by
``entity_ref``) **plus** the typed financial/inventory read-models (keyed by
``source_id``) — the tables a bad, non-deterministic ingest would corrupt. The
surrogate ``id``/``created_at`` columns are deliberately excluded from the
signature: idempotency is about the **deterministic lineage keys + payloads**
being stable, not the row's opaque uuid (the upsert is delete-then-insert, so the
surrogate id legitimately rotates while the lineage key stays put).

This module is imported by the T038 gate test, the T031 readiness evaluator, and
the T045 go-live checkpoint — one authoritative proof, three consumers.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# The lineage spine + the typed financial/inventory read-models the re-run-diff
# gate covers (the binding: "diff canonical_record plus the typed read-models").
CANONICAL_SPINE = "canonical_record"
TYPED_READ_MODELS = (
    "ledger_entry", "invoice_record", "payment_record", "ar_balance",
    "inventory_item",
)
DIFF_TABLES = (CANONICAL_SPINE,) + TYPED_READ_MODELS

# Columns excluded from a row signature (opaque / non-deterministic).
_OPAQUE = {"id", "created_at", "clinic_id", "practice_id"}


@dataclass
class IdempotencyReport:
    practice_id: str
    duplicate_count: int              # net row growth across DIFF_TABLES (0 = clean)
    stable_identifiers: bool          # every lineage key + payload identical re-run
    lineage_coverage: float           # fraction of canonical records w/ resolvable lineage
    diff: list[str] = field(default_factory=list)   # human-readable diffs (empty = 0-row)

    @property
    def is_idempotent(self) -> bool:
        return (self.duplicate_count == 0
                and self.stable_identifiers
                and not self.diff
                and self.lineage_coverage >= 1.0)


def _sig(row: dict) -> tuple:
    """A deterministic signature of a row, excluding opaque/scoping columns."""
    return tuple(sorted((k, _stable(v)) for k, v in row.items() if k not in _OPAQUE))


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return tuple(sorted((k, _stable(v)) for k, v in value.items()))
    if isinstance(value, list):
        return tuple(_stable(v) for v in value)
    return value


def _snapshot(repo, practice_id: str) -> dict[str, dict]:
    """table -> {lineage_key: row_signature}. canonical_record keys on
    ``entity_ref`` (its unique lineage key); typed tables key on ``source_id``."""
    snap: dict[str, dict] = {}
    cr: dict[str, tuple] = {}
    for r in repo.list_canonical_records(practice_id):
        cr[r["entity_ref"]] = _sig(r)
    snap[CANONICAL_SPINE] = cr
    for t in TYPED_READ_MODELS:
        d: dict[str, tuple] = {}
        for r in repo.list_canonical(t, practice_id):
            d[r["source_id"]] = _sig(r)
        snap[t] = d
    return snap


def _counts(repo, practice_id: str) -> dict[str, int]:
    return {t: repo.count_canonical(t, practice_id) for t in DIFF_TABLES}


def lineage_coverage(repo, practice_id: str) -> float:
    """Fraction of canonical records that resolve to a source record via a
    non-empty ``entity_ref`` **and** ``source_id`` (100% is the SC-003 bar)."""
    recs = repo.list_canonical_records(practice_id)
    if not recs:
        return 0.0
    covered = sum(1 for r in recs if r.get("entity_ref") and r.get("source_id"))
    return round(covered / len(recs), 4)


def has_full_lineage(repo, practice_id: str) -> bool:
    recs = repo.list_canonical_records(practice_id)
    return bool(recs) and lineage_coverage(repo, practice_id) >= 1.0


def rerun_diff(repo, clinic_id: str, practice_id: str, adapter, profile,
               raw_export: Any) -> IdempotencyReport:
    """Normalize ``raw_export`` a **second** time and diff the canonical store
    against the pre-re-run snapshot. Returns the idempotency proof (0 duplicates,
    stable identifiers, 100% lineage → ``is_idempotent``)."""
    from backend.envelope.normalizer import Normalizer

    before = _snapshot(repo, practice_id)
    before_counts = _counts(repo, practice_id)

    # THE RE-RUN — the same source, the same deterministic keys.
    Normalizer(repo).normalize(clinic_id, practice_id, adapter, profile, raw_export)

    after = _snapshot(repo, practice_id)
    after_counts = _counts(repo, practice_id)

    diffs: list[str] = []
    duplicate_count = 0
    for t in DIFF_TABLES:
        grew = after_counts[t] - before_counts[t]
        if grew != 0:
            duplicate_count += max(grew, 0)
            diffs.append(f"{t}: row count {before_counts[t]} -> {after_counts[t]}")
        b, a = before[t], after[t]
        for key in sorted(set(a) - set(b)):
            diffs.append(f"{t}: new lineage key {key!r} after re-run")
        for key in sorted(set(b) - set(a)):
            diffs.append(f"{t}: lineage key {key!r} vanished after re-run")
        for key in sorted(set(a) & set(b)):
            if a[key] != b[key]:
                diffs.append(f"{t}: unstable payload at {key!r}")

    stable = (before == after)
    coverage = lineage_coverage(repo, practice_id)
    return IdempotencyReport(
        practice_id=practice_id, duplicate_count=duplicate_count,
        stable_identifiers=stable, lineage_coverage=coverage, diff=diffs,
    )
