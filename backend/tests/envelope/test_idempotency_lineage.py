"""Feature 009 — T038 idempotency + lineage re-run-diff gate (SC-003).

Normalize the fixture twice and diff the canonical store: assert **0** duplicate
records, stable identifiers, and **100%** of records resolve to a source record
via ``entity_ref``/``source_id``. The first-class SC-003 gate — the re-run-diff
idempotency proof, reused at the T045 go-live checkpoint.
"""
import uuid

from backend.envelope.idempotency import (
    DIFF_TABLES, lineage_coverage, rerun_diff,
)
from backend.tests.envelope import _pipeline as P

CLINIC = "goldsmith"


def _pid():
    return f"p-idem-{uuid.uuid4().hex[:8]}"


def test_rerun_diff_is_zero_row_and_stable(repo):
    pid = _pid()
    exp, adapter, profile, _sm = P.normalize_once(repo, pid, clinic=CLINIC, seed=51)

    before_counts = {t: repo.count_canonical(t, pid) for t in DIFF_TABLES}
    report = rerun_diff(repo, CLINIC, pid, adapter, profile, exp)
    after_counts = {t: repo.count_canonical(t, pid) for t in DIFF_TABLES}

    # a 0-row diff: no duplicates anywhere, stable identifiers, empty diff.
    assert report.duplicate_count == 0, report.diff
    assert report.diff == []
    assert report.stable_identifiers is True
    assert report.is_idempotent is True
    # row counts unchanged across the re-run (delete-then-insert on stable keys).
    assert after_counts == before_counts


def test_hundred_percent_lineage_coverage(repo):
    pid = _pid()
    P.normalize_once(repo, pid, clinic=CLINIC, seed=52)
    # 100% of canonical records resolve to a source record via entity_ref/source_id.
    assert lineage_coverage(repo, pid) == 1.0
    recs = repo.list_canonical_records(pid)
    assert recs
    assert all(r["entity_ref"] and r["source_id"] for r in recs)


def test_three_reruns_never_duplicate(repo):
    """Idempotency holds across repeated re-runs (not just the second)."""
    pid = _pid()
    exp, adapter, profile, _sm = P.normalize_once(repo, pid, clinic=CLINIC, seed=53)
    baseline = repo.count_canonical("canonical_record", pid)
    for _ in range(3):
        report = rerun_diff(repo, CLINIC, pid, adapter, profile, exp)
        assert report.is_idempotent
        assert repo.count_canonical("canonical_record", pid) == baseline
