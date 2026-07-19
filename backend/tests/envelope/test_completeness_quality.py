"""Feature 009 — T021 completeness + T022 quality + T023 quality-floor block.

T021 — completeness reports coverage + counts for every requested category
including financial/AR/inventory, flags a short category, computes AR/invoice/
payment totals, and is category-aware (a lopsided practice surfaces the thin
category).
T022 — quality quantifies each planted dirty-data pattern and computes a
usable-record share matching the answer key within tolerance.
T023 — the >20%-unusable practice is held and never shadow_ready; a below-floor
practice is blocked past normalized; a practice under the floor is not blocked.
"""
import uuid

import pytest

from backend.envelope.completeness import CompletenessChecker
from backend.envelope.extraction_port import SimExtractionPort
from backend.envelope.normalizer import Normalizer
from backend.envelope.pims import load_adapters
from backend.envelope.pims.port import resolve_adapter
from backend.envelope.quality import QualityAssessor, enforce_floor
from backend.envelope.state_machine import GuardError, StateMachine
from backend.models import (
    CounselSignoff, FormatProfile, PracticeDatabase, PracticeState,
)
from backend.tests.envelope.fixtures.ezyvet_synthetic_export import generate_practice_export

CLINIC = "goldsmith"


def _adapter(pid):
    load_adapters()
    return resolve_adapter("ezyvet", "complete_v1", clinic_id=CLINIC, practice_id=pid,
                           practice_database_id="pdb1", extraction_port=SimExtractionPort())


def _ingest(repo, pid, seed=11, variant="complete", planted="clean", mutate=None):
    exp = generate_practice_export(pid, seed=seed, variant=variant, planted=planted)
    if mutate:
        mutate(exp)
    a = _adapter(pid)
    profile = a.profile(exp)
    repo.create_format_profile(FormatProfile(
        clinic_id=CLINIC, practice_id=pid, practice_database_id="pdb1",
        entities=profile.entities, encodings=profile.encodings,
        export_variant=profile.export_variant))
    Normalizer(repo).normalize(CLINIC, pid, a, profile, exp)
    return exp


# --------------------------------------------------------------------------- #
#  T021 — completeness
# --------------------------------------------------------------------------- #
def test_completeness_covers_all_categories_and_financials(repo):
    pid = "p-comp"
    exp = _ingest(repo, pid)
    result = CompletenessChecker(repo).check(CLINIC, pid)

    # every §5 category has a coverage line
    for cat in ("patient_client", "scheduling", "invoicing_billing_payments",
                "communications", "attachments_imaging", "configuration"):
        assert cat in result.category_coverage
        assert result.category_coverage[cat]["present"]

    # financial totals match the answer key
    ak = exp.answer_key
    assert result.ar_balance_total == pytest.approx(ak.ar_balance_total, abs=0.01)
    assert result.invoice_count == ak.invoice_count
    assert result.payment_total == pytest.approx(ak.payment_total, abs=0.01)
    # the planted orphaned refs surface in referential integrity
    assert any(f["kind"] == "orphaned_ref" for f in result.referential_integrity_findings)


def test_completeness_flags_a_short_category(repo):
    pid = "p-comp-short"

    def _drop_ids(exp):
        # add client rows with no stable id -> profiled counts them, normalize
        # skips them -> ingested < profiled -> patient_client is SHORT.
        for k in range(3):
            exp.entities["clients"].append(
                {"client_id": "", "first_name": "Ghost", "last_name": str(k),
                 "phone": "", "email": "", "address": ""})

    _ingest(repo, pid, mutate=_drop_ids)
    result = CompletenessChecker(repo).check(CLINIC, pid)
    assert result.category_coverage["patient_client"]["short"] is True
    assert "patient_client" in result.missing_or_short


def test_completeness_is_category_aware_lopsided(repo):
    pid = "p-comp-lopsided"

    def _thin_clinical(exp):
        # financials intact; clinical thin (attachments removed entirely)
        exp.entities["attachments"] = []

    _ingest(repo, pid, mutate=_thin_clinical)
    result = CompletenessChecker(repo).check(CLINIC, pid)
    # financials reconcile (present), attachments surfaced as absent
    assert result.category_coverage["invoicing_billing_payments"]["present"]
    assert result.category_coverage["attachments_imaging"]["present"] is False
    assert "attachments_imaging" in result.missing_or_short


# --------------------------------------------------------------------------- #
#  T022 — quality
# --------------------------------------------------------------------------- #
def test_quality_quantifies_dirty_patterns_and_usable_share(repo):
    pid = "p-qual"
    exp = _ingest(repo, pid, planted="clean")
    qa = QualityAssessor(repo).assess(CLINIC, pid)
    ak = exp.answer_key

    assert qa.duplicate_owners >= 1
    assert qa.orphaned_refs >= 1
    assert qa.deceased_pets == len(ak.deceased_patient_ids)
    # usable-record share matches the answer key within tolerance
    assert qa.usable_record_share == pytest.approx(ak.usable_record_share, abs=0.05)
    assert qa.below_floor is False


# --------------------------------------------------------------------------- #
#  T023 — quality-floor block
# --------------------------------------------------------------------------- #
def _to_normalized(repo, sm, pid):
    repo.append_counsel_signoff(CounselSignoff(clinic_id=CLINIC, practice_id=pid, signed_by="c"))
    sm.advance(pid, PracticeState.PROFILED)
    sm.advance(pid, PracticeState.NORMALIZED)


def test_dirty_practice_is_held_and_never_shadow_ready(repo):
    pid = f"p-floor-{uuid.uuid4().hex[:6]}"
    repo.create_practice_database(PracticeDatabase(
        clinic_id=CLINIC, practice_id=pid, delivery_id="d1"))
    sm = StateMachine(repo)
    sm.receive(pid, CLINIC)
    _ingest(repo, pid, planted="dirty")   # writes the FormatProfile too
    _to_normalized(repo, sm, pid)

    qa = QualityAssessor(repo).assess(CLINIC, pid)
    assert qa.below_floor is True, qa.usable_record_share

    held = enforce_floor(sm, pid, qa)
    assert held is True
    assert sm.current_state(pid) == "held"
    # the guard independently blocks any advance past normalized
    with pytest.raises(GuardError) as e:
        sm.advance(pid, PracticeState.VERIFIED)
    assert e.value.guard == "quality_floor"
    # a held practice never auto-advances to shadow_ready
    from backend.envelope.state_machine import IllegalTransition
    with pytest.raises(IllegalTransition):
        sm.advance(pid, PracticeState.SHADOW_READY)


def test_clean_practice_below_floor_is_not_blocked(repo):
    pid = f"p-clean-{uuid.uuid4().hex[:6]}"
    repo.create_practice_database(PracticeDatabase(
        clinic_id=CLINIC, practice_id=pid, delivery_id="d1"))
    sm = StateMachine(repo)
    sm.receive(pid, CLINIC)
    _ingest(repo, pid, planted="clean")
    _to_normalized(repo, sm, pid)

    qa = QualityAssessor(repo).assess(CLINIC, pid)
    assert qa.below_floor is False
    assert enforce_floor(sm, pid, qa) is False
    sm.advance(pid, PracticeState.VERIFIED)     # not blocked on quality
    assert sm.current_state(pid) == "verified"
