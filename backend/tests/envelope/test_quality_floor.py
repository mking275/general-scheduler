"""Feature 009 — T040 quality-floor + category-aware-hold harness (FR-015).

A fixture practice seeded >20% unusable is **held** with the gap itemized and
never reaches ``shadow_ready``; a category-lopsided practice (financials
reconcile, clinical thin) is held category-aware — the hold is driven by the
clinical-side dirtiness even though the financial category is complete.
"""
import uuid

from backend.envelope.quality import QualityAssessor, enforce_floor
from backend.envelope.reconciliation import Reconciler
from backend.envelope.state_machine import GuardError
from backend.models import PracticeState
from backend.tests.envelope import _pipeline as P

CLINIC = "goldsmith"


def _pid(tag):
    return f"p-qf-{tag}-{uuid.uuid4().hex[:6]}"


def test_over_floor_practice_held_and_never_shadow_ready(repo):
    pid = _pid("dirty")
    # verify_stage runs completeness+quality but advances to VERIFIED; a dirty
    # practice's quality guard blocks that advance, so re-run without the advance.
    exp, adapter, profile, sm = P.normalize_once(
        repo, pid, clinic=CLINIC, seed=71, planted="dirty")
    from backend.models import CounselSignoff
    repo.append_counsel_signoff(CounselSignoff(
        clinic_id=CLINIC, practice_id=pid, signed_by="counsel"))
    sm.advance(pid, PracticeState.PROFILED)
    sm.advance(pid, PracticeState.NORMALIZED)
    from backend.envelope.completeness import CompletenessChecker
    CompletenessChecker(repo).check(CLINIC, pid)
    qa = QualityAssessor(repo).assess(CLINIC, pid)

    assert exp.answer_key.below_floor
    assert qa.below_floor is True

    # the >20%-unusable practice is HELD with the gap itemized.
    held = enforce_floor(sm, pid, qa, CLINIC)
    assert held is True
    assert sm.current_state(pid) == "held"
    assert qa.itemized_gap                          # the gap is itemized

    # it can NEVER reach verified/shadow_ready — the quality_floor guard blocks.
    try:
        sm.advance(pid, PracticeState.VERIFIED)
        assert False, "held practice advanced past the quality floor"
    except GuardError as e:
        assert e.guard == "quality_floor"
    assert sm.current_state(pid) == "held"


def test_below_floor_practice_not_blocked_on_this_criterion(repo):
    pid = _pid("clean")
    exp, *_rest = P.verify_stage(repo, pid, clinic=CLINIC, seed=72, planted="clean")
    qa = repo.get_quality_assessment(pid)
    assert qa["below_floor"] is False
    # a clean practice is not held on the floor (it reached `verified`).
    sm = _rest[-1]
    assert sm.current_state(pid) == "verified"


def test_category_lopsided_held_category_aware(repo):
    """A dirty practice whose FINANCIALS still reconcile is held on the clinical
    dirtiness — the hold is category-aware, not a financial gap."""
    pid = _pid("lopsided")
    exp, adapter, profile, sm = P.normalize_once(
        repo, pid, clinic=CLINIC, seed=73, planted="dirty")
    from backend.models import CounselSignoff
    from backend.envelope.completeness import CompletenessChecker
    repo.append_counsel_signoff(CounselSignoff(
        clinic_id=CLINIC, practice_id=pid, signed_by="counsel"))
    sm.advance(pid, PracticeState.PROFILED)
    sm.advance(pid, PracticeState.NORMALIZED)
    completeness = CompletenessChecker(repo).check(CLINIC, pid)
    qa = QualityAssessor(repo).assess(CLINIC, pid)

    # financials reconcile: the financial category is present + AR reconciles.
    report = Reconciler(repo).reconcile(CLINIC, pid, exp.reported_figures)
    assert completeness.category_coverage["invoicing_billing_payments"]["present"]
    assert report.ar_variance.disposition.value == "explained"   # financials fine

    # yet the practice is held — driven by clinical-side unusable records.
    assert qa.below_floor is True
    assert enforce_floor(sm, pid, qa, CLINIC) is True
    assert sm.current_state(pid) == "held"
