"""Feature 009 — T024 reconciliation + T025 zero-AR-tolerance + T026 owner surface.

T024 — the report presents per-category requested/delivered/ingested counts and a
financial reconciliation against the answer key's reported figures; a partial
practice's report shows the outstanding gap; the planted-AR-variance practice
surfaces the variance.
T025 — the planted AR variance is blocking and held out of reconciled/shadow_ready;
an invoice/payment variance with an attributed cause is itemized-and-allowed while
an unattributed one blocks; 0 silent AR discrepancies pass.
T026 — the report is owner/manager-audience-only; a practice is not activatable
until a group-level acknowledgment is recorded; the group report drills down; the
ack is an append (append-only preserved).
"""
import uuid

import pytest

from backend.envelope.completeness import CompletenessChecker
from backend.envelope.extraction_port import SimExtractionPort
from backend.envelope.normalizer import Normalizer
from backend.envelope.owner_surface import OwnerSurface
from backend.envelope.pims import load_adapters
from backend.envelope.pims.port import resolve_adapter
from backend.envelope.reconciliation import Reconciler
from backend.envelope.state_machine import GuardError, IllegalTransition, StateMachine
from backend.models import (
    CounselSignoff, FormatProfile, PracticeDatabase, PracticeState,
    VarianceDisposition,
)
from backend.tests.envelope.fixtures.ezyvet_synthetic_export import generate_practice_export

CLINIC = "goldsmith"


def _adapter(pid):
    load_adapters()
    return resolve_adapter("ezyvet", "complete_v1", clinic_id=CLINIC, practice_id=pid,
                           practice_database_id="pdb1", extraction_port=SimExtractionPort())


def _ingest_and_verify(repo, pid, seed=21, variant="complete", planted="clean"):
    """Receive -> normalize -> completeness; leaves the practice at `normalized`
    with a completeness result. Returns the fixture export."""
    repo.create_practice_database(PracticeDatabase(
        clinic_id=CLINIC, practice_id=pid, delivery_id="d1"))
    sm = StateMachine(repo)
    sm.receive(pid, CLINIC)
    exp = generate_practice_export(pid, seed=seed, variant=variant, planted=planted)
    a = _adapter(pid)
    profile = a.profile(exp)
    repo.create_format_profile(FormatProfile(
        clinic_id=CLINIC, practice_id=pid, practice_database_id="pdb1",
        entities=profile.entities, encodings=profile.encodings,
        export_variant=profile.export_variant))
    Normalizer(repo).normalize(CLINIC, pid, a, profile, exp)
    repo.append_counsel_signoff(CounselSignoff(clinic_id=CLINIC, practice_id=pid, signed_by="c"))
    sm.advance(pid, PracticeState.PROFILED)
    sm.advance(pid, PracticeState.NORMALIZED)
    sm.advance(pid, PracticeState.VERIFIED)
    CompletenessChecker(repo).check(CLINIC, pid)
    return exp, sm


# --------------------------------------------------------------------------- #
#  T024 — the report
# --------------------------------------------------------------------------- #
def test_report_counts_and_financial_reconciliation(repo):
    pid = f"p-recon-{uuid.uuid4().hex[:6]}"
    exp, _ = _ingest_and_verify(repo, pid, planted="clean")
    report = Reconciler(repo).reconcile(CLINIC, pid, exp.reported_figures)

    # per-category requested/delivered/ingested
    for cat in ("patient_client", "invoicing_billing_payments", "attachments_imaging"):
        counts = report.category_counts[cat]
        assert set(counts) == {"requested", "delivered", "ingested"}
    # a clean practice reconciles financially (no blocking)
    assert report.blocking is False
    assert report.ar_variance.disposition == VarianceDisposition.EXPLAINED


def test_partial_report_shows_outstanding_gap(repo):
    pid = f"p-recon-partial-{uuid.uuid4().hex[:6]}"
    exp, _ = _ingest_and_verify(repo, pid, variant="partial", planted="clean")
    report = Reconciler(repo).reconcile(CLINIC, pid, exp.reported_figures)
    assert "attachments_imaging" in report.outstanding_gap


# --------------------------------------------------------------------------- #
#  T025 — zero-AR-tolerance
# --------------------------------------------------------------------------- #
def test_planted_ar_variance_blocks_reconciled(repo):
    pid = f"p-arvar-{uuid.uuid4().hex[:6]}"
    exp, sm = _ingest_and_verify(repo, pid, planted="ar_variance")
    assert exp.answer_key.has_planted_ar_variance
    report = Reconciler(repo).reconcile(CLINIC, pid, exp.reported_figures)

    # surfaced red + blocking, never silent
    assert report.blocking is True
    assert report.ar_variance.disposition == VarianceDisposition.BLOCKING
    assert abs(report.ar_variance.amount) > 0.01

    # the state-machine guard holds it out of reconciled / shadow_ready
    with pytest.raises(GuardError) as e:
        sm.advance(pid, PracticeState.RECONCILED)
    assert e.value.guard == "ar_variance"
    assert sm.current_state(pid) == "verified"


def test_ar_variance_with_attributed_cause_is_allowed(repo):
    pid = f"p-arvar-ok-{uuid.uuid4().hex[:6]}"
    exp, sm = _ingest_and_verify(repo, pid, planted="ar_variance")
    # an attributed cause explains the AR variance -> itemized, not blocking
    report = Reconciler(repo).reconcile(
        CLINIC, pid, exp.reported_figures,
        attributed_causes={"ar": "write-off approved by owner pre-migration"})
    assert report.blocking is False
    assert report.ar_variance.disposition == VarianceDisposition.EXPLAINED
    assert report.ar_variance.attributed_cause
    sm.advance(pid, PracticeState.RECONCILED)     # not blocked
    assert sm.current_state(pid) == "reconciled"


def test_invoice_variance_unattributed_blocks_attributed_allows(repo):
    pid = f"p-invvar-{uuid.uuid4().hex[:6]}"
    exp, _ = _ingest_and_verify(repo, pid, planted="clean")
    reported = dict(exp.reported_figures)
    reported["invoice_count"] = exp.answer_key.invoice_count + 5   # a variance

    blocked = Reconciler(repo).reconcile(CLINIC, pid, reported)
    assert blocked.invoice_variance.disposition == VarianceDisposition.BLOCKING
    assert blocked.blocking is True

    allowed = Reconciler(repo).reconcile(
        CLINIC, pid, reported, attributed_causes={"invoice": "voided drafts excluded"})
    assert allowed.invoice_variance.disposition == VarianceDisposition.EXPLAINED
    assert allowed.blocking is False


# --------------------------------------------------------------------------- #
#  T026 — owner surface + group ack
# --------------------------------------------------------------------------- #
def test_owner_only_audience_and_group_ack_activation(repo):
    pids = [f"p-owner-{uuid.uuid4().hex[:6]}" for _ in range(2)]
    for pid in pids:
        exp, _ = _ingest_and_verify(repo, pid, planted="clean")
        Reconciler(repo).reconcile(CLINIC, pid, exp.reported_figures)

    surface = OwnerSurface(repo)
    # staff audience is not a reachable surface
    with pytest.raises(PermissionError):
        surface.latest_report(pids[0], audience="staff")

    # not activatable before the group ack
    assert all(not surface.is_activatable(pid) for pid in pids)

    # the group rollup drills down to each practice's reconciliation
    rollup = surface.group_report(CLINIC, pids)
    assert set(rollup["drill_down"]) == set(pids)

    before = sum(len(repo.get_reconciliation_reports(pid)) for pid in pids)
    result = surface.acknowledge_group(CLINIC, pids, acknowledged_by="dr_goldsmith")
    after = sum(len(repo.get_reconciliation_reports(pid)) for pid in pids)

    assert set(result["acknowledged"]) == set(pids)
    # the ack is an APPEND (one new report version per practice), not an update
    assert after == before + len(pids)
    assert all(surface.is_activatable(pid) for pid in pids)


def test_group_ack_skips_blocking_practice(repo):
    clean = f"p-mix-clean-{uuid.uuid4().hex[:6]}"
    blocking = f"p-mix-block-{uuid.uuid4().hex[:6]}"
    exp_c, _ = _ingest_and_verify(repo, clean, planted="clean")
    Reconciler(repo).reconcile(CLINIC, clean, exp_c.reported_figures)
    exp_b, _ = _ingest_and_verify(repo, blocking, planted="ar_variance")
    Reconciler(repo).reconcile(CLINIC, blocking, exp_b.reported_figures)

    surface = OwnerSurface(repo)
    result = surface.acknowledge_group(CLINIC, [clean, blocking], acknowledged_by="owner")
    assert result["acknowledged"] == [clean]
    assert result["held"] == [blocking]
    assert surface.is_activatable(clean)
    assert not surface.is_activatable(blocking)
