"""Feature 009 — T043 partial→delta reconciliation harness (SC-009).

The partial fixture (attachments omitted) is detected against §5 scope, produces
an owner-facing gap notice, proceeds on delivered data **without** being marked
complete (``partial`` state); the delta fixture re-ingests idempotently (0
duplicates) and updates the reconciliation report (gap closed). A corrupt export
is rejected at discovery and leaves the canonical store untouched.
"""
import uuid

import pytest

from backend.envelope.completeness import CompletenessChecker
from backend.envelope.delta import reingest_delta
from backend.envelope.format_discovery import DiscoveryError
from backend.envelope.gap_notice import GapNoticeService
from backend.envelope.quality import QualityAssessor
from backend.envelope.reconciliation import Reconciler
from backend.envelope.scope_check import ScopeChecker, manifest_from_export
from backend.envelope.state_machine import StateMachine
from backend.models import CounselSignoff, FormatProfile, PracticeDatabase, PracticeState
from backend.tests.envelope import _pipeline as P
from backend.tests.envelope.fixtures.ezyvet_synthetic_export import (
    generate_delta_export, generate_practice_export,
)

CLINIC = "goldsmith"
SEED = 4242


def _ingest_partial(repo, pid):
    """Ingest the partial fixture (attachments omitted) to `verified`, with the
    scope-vs-request record + reconciliation report. Returns the partial export."""
    exp = generate_practice_export(pid, seed=SEED, variant="partial")
    repo.create_practice_database(PracticeDatabase(
        clinic_id=CLINIC, practice_id=pid, delivery_id="d1"))
    sm = StateMachine(repo)
    sm.receive(pid, CLINIC)
    # scope-vs-request: attachments_imaging is absent in the partial manifest.
    ScopeChecker(repo).check(CLINIC, pid, "pdb1", manifest_from_export(exp))
    adapter = P.adapter_for(pid, CLINIC)
    profile = adapter.profile(exp)
    repo.create_format_profile(FormatProfile(
        clinic_id=CLINIC, practice_id=pid, practice_database_id="pdb1",
        entities=profile.entities, encodings=profile.encodings,
        export_variant=profile.export_variant))
    from backend.envelope.normalizer import Normalizer
    Normalizer(repo).normalize(CLINIC, pid, adapter, profile, exp)
    repo.append_counsel_signoff(CounselSignoff(
        clinic_id=CLINIC, practice_id=pid, signed_by="counsel"))
    sm.advance(pid, PracticeState.PROFILED)
    sm.advance(pid, PracticeState.NORMALIZED)
    CompletenessChecker(repo).check(CLINIC, pid)
    QualityAssessor(repo).assess(CLINIC, pid)
    sm.advance(pid, PracticeState.VERIFIED)
    Reconciler(repo).reconcile(CLINIC, pid, exp.reported_figures)
    return exp, sm


def test_partial_detected_gap_notice_not_complete(repo):
    pid = f"p-partial-{uuid.uuid4().hex[:6]}"
    exp, sm = _ingest_partial(repo, pid)

    # detected against §5 scope -> owner-facing gap notice + PARTIAL hold.
    notice = GapNoticeService(repo).detect_and_notice(CLINIC, pid, state_machine=sm)
    assert notice is not None
    assert "attachments_imaging" in notice.missing_categories
    assert notice.text and "PARTIAL" in notice.text            # paper-trail-ready

    # proceeds on delivered data but is NOT marked complete (partial state).
    assert sm.current_state(pid) == "partial"
    # the reconciliation report shows the outstanding gap.
    report = repo.get_reconciliation_reports(pid)[-1]
    assert "attachments_imaging" in report["outstanding_gap"]
    # 0 partial deliveries pass as complete.
    assert sm.current_state(pid) != "shadow_ready"


def test_delta_reingest_idempotent_closes_gap_updates_report(repo):
    pid = f"p-delta-{uuid.uuid4().hex[:6]}"
    exp, sm = _ingest_partial(repo, pid)
    GapNoticeService(repo).detect_and_notice(CLINIC, pid, state_machine=sm)
    assert sm.current_state(pid) == "partial"
    before = repo.count_canonical("canonical_record", pid)

    # the delta (attachments arriving later) merges idempotently.
    delta = generate_delta_export(pid, seed=SEED)
    adapter = P.adapter_for(pid, CLINIC)
    res = reingest_delta(repo, CLINIC, pid, adapter, delta, exp.reported_figures)

    # advanced past partial; gap closed; report updated.
    assert res.state != "partial"
    assert res.gap_closed is True
    assert "attachments_imaging" not in res.report.outstanding_gap
    assert res.records_added > 0                    # the attachments were added

    # re-running the SAME delta adds 0 records (0 duplicates — idempotent merge).
    again = reingest_delta(repo, CLINIC, pid, adapter, delta, exp.reported_figures)
    assert again.records_added == 0
    assert repo.count_canonical("canonical_record", pid) == before + res.records_added


def test_corrupt_delta_rejected_at_discovery_store_untouched(repo):
    pid = f"p-corrupt-{uuid.uuid4().hex[:6]}"
    exp, sm = _ingest_partial(repo, pid)
    GapNoticeService(repo).detect_and_notice(CLINIC, pid, state_machine=sm)
    before = repo.count_canonical("canonical_record", pid)

    adapter = P.adapter_for(pid, CLINIC)
    corrupt = b"not a zip file at all -- truncated/garbage bytes"
    with pytest.raises(DiscoveryError):
        reingest_delta(repo, CLINIC, pid, adapter, corrupt, exp.reported_figures)

    # never partially normalized — the canonical store is untouched (FR-033).
    assert repo.count_canonical("canonical_record", pid) == before
    assert sm.current_state(pid) == "partial"


def test_hundred_percent_partial_detected_zero_silent(repo):
    """Across several partial practices, 100% detected, 0 silently complete."""
    detected = 0
    pids = []
    for i in range(3):
        pid = f"p-pd-{uuid.uuid4().hex[:6]}"
        _ingest_partial(repo, pid)
        sm = StateMachine(repo)
        notice = GapNoticeService(repo).detect_and_notice(CLINIC, pid, state_machine=sm)
        if notice is not None:
            detected += 1
        pids.append(pid)
    assert detected == len(pids)                    # 100% detected (SC-009)
    for pid in pids:
        assert StateMachine(repo).current_state(pid) == "partial"   # 0 silent complete
