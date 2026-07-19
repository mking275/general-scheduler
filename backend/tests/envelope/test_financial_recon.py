"""Feature 009 — T039 financial completeness + zero-AR-tolerance harness (SC-004).

Assert coverage of clinical+scheduling+comms+financial/AR/inventory; reconcile
AR/invoice/payment totals to the fixture's synthetic reported figures; assert any
unexplained AR variance **blocks** and every other variance is itemized-or-blocks.
0 silent AR discrepancies.
"""
import uuid

from backend.envelope.reconciliation import Reconciler
from backend.envelope.state_machine import GuardError
from backend.models import PracticeState, VarianceDisposition
from backend.tests.envelope import _pipeline as P

CLINIC = "goldsmith"

_FINANCIAL_CATS = ("patient_client", "scheduling", "communications",
                   "invoicing_billing_payments", "configuration")


def _pid(tag):
    return f"p-fin-{tag}-{uuid.uuid4().hex[:6]}"


def test_financial_completeness_covers_all_categories(repo):
    pid = _pid("cov")
    exp, *_ = P.verify_stage(repo, pid, clinic=CLINIC, seed=61, planted="clean")
    completeness = repo.get_completeness_result(pid)
    coverage = completeness["category_coverage"]

    # 100% category coverage incl. financial/AR/inventory.
    for cat in _FINANCIAL_CATS:
        assert coverage[cat]["present"], f"{cat} not covered"
    # AR/invoice/payment totals computed and matching the answer key.
    ak = exp.answer_key
    assert abs(completeness["ar_balance_total"] - ak.ar_balance_total) < 0.01
    assert completeness["invoice_count"] == ak.invoice_count
    assert abs(completeness["payment_total"] - ak.payment_total) < 0.01


def test_clean_practice_reconciles_no_blocking(repo):
    pid = _pid("clean")
    exp, *_ = P.verify_stage(repo, pid, clinic=CLINIC, seed=62, planted="clean")
    report = Reconciler(repo).reconcile(CLINIC, pid, exp.reported_figures)
    assert report.blocking is False
    assert report.ar_variance.disposition == VarianceDisposition.EXPLAINED


def test_planted_ar_variance_blocks_and_never_silent(repo):
    pid = _pid("arvar")
    exp, _adapter, _profile, sm = P.verify_stage(
        repo, pid, clinic=CLINIC, seed=63, planted="ar_variance")
    assert exp.answer_key.has_planted_ar_variance

    report = Reconciler(repo).reconcile(CLINIC, pid, exp.reported_figures)
    # surfaced red + blocking, never a silent discrepancy (FR-017).
    assert report.blocking is True
    assert report.ar_variance.disposition == VarianceDisposition.BLOCKING
    assert abs(report.ar_variance.amount) > 0.01

    # the state-machine guard holds it out of reconciled / shadow_ready.
    try:
        sm.advance(pid, PracticeState.RECONCILED)
        assert False, "AR variance did not block reconciled"
    except GuardError as e:
        assert e.guard == "ar_variance"
    assert sm.current_state(pid) == "verified"


def test_every_variance_attributed_or_blocks(repo):
    pid = _pid("attr")
    exp, *_ = P.verify_stage(repo, pid, clinic=CLINIC, seed=64, planted="ar_variance")

    # unattributed AR variance blocks; the same variance with a cause is explained.
    blocked = Reconciler(repo).reconcile(CLINIC, pid, exp.reported_figures)
    assert blocked.blocking is True

    explained = Reconciler(repo).reconcile(
        CLINIC, pid, exp.reported_figures,
        attributed_causes={"ar": "owner-approved write-off pre-migration"})
    assert explained.blocking is False
    assert explained.ar_variance.disposition == VarianceDisposition.EXPLAINED
    assert explained.ar_variance.attributed_cause


def test_zero_silent_ar_discrepancies_across_batch(repo):
    """Across a mixed batch, every AR variance is either explained or blocking —
    none passes silently."""
    seeds = {"clean": 65, "ar_variance": 66}
    reports = []
    for planted, seed in seeds.items():
        pid = _pid(planted)
        exp, *_ = P.verify_stage(repo, pid, clinic=CLINIC, seed=seed, planted=planted)
        reports.append(Reconciler(repo).reconcile(CLINIC, pid, exp.reported_figures))
    for r in reports:
        # a nonzero AR variance must never be `explained` without a cause.
        v = r.ar_variance
        if abs(v.amount) > 0.01:
            assert v.disposition == VarianceDisposition.BLOCKING or v.attributed_cause
