"""Feature 009 — T006 state machine + transition guards acceptance.

The state machine rejects every guarded transition when its precondition is
unmet (counsel-gate, profile-gate, floor, AR); a blocked/held/partial practice
is a valid persisted state that never auto-advances to shadow_ready; each
transition writes one append-only row.
"""
import uuid

import pytest

from backend.envelope.state_machine import GuardError, IllegalTransition, StateMachine
from backend.models import (
    CounselSignoff, FormatProfile, PracticeDatabase, PracticeState,
    QualityAssessment, ReconciliationReport,
)

CLINIC = "goldsmith"


def _new_practice(repo) -> str:
    pid = f"p-{uuid.uuid4().hex[:8]}"
    repo.create_practice_database(PracticeDatabase(
        clinic_id=CLINIC, practice_id=pid, delivery_id="d1"))
    return pid


def _received(repo, sm) -> str:
    pid = _new_practice(repo)
    sm.receive(pid, CLINIC)
    return pid


def test_receive_writes_one_row_and_sets_received(repo):
    sm = StateMachine(repo)
    pid = _received(repo, sm)
    assert sm.current_state(pid) == PracticeState.RECEIVED.value
    rows = repo.get_state_transitions(pid)
    assert len(rows) == 1 and rows[0]["to_state"] == "received" and rows[0]["from_state"] is None


def test_counsel_gate_blocks_profiled_and_normalized(repo):
    sm = StateMachine(repo)
    pid = _received(repo, sm)
    with pytest.raises(GuardError) as e:
        sm.advance(pid, PracticeState.PROFILED)
    assert e.value.guard == "counsel_gate"
    # state unchanged, no extra transition row
    assert sm.current_state(pid) == "received"
    assert len(repo.get_state_transitions(pid)) == 1
    # after the signoff row, profiled is permitted
    repo.append_counsel_signoff(CounselSignoff(clinic_id=CLINIC, practice_id=pid, signed_by="counsel"))
    sm.advance(pid, PracticeState.PROFILED)
    assert sm.current_state(pid) == "profiled"


def test_profile_gate_blocks_normalized(repo):
    sm = StateMachine(repo)
    pid = _received(repo, sm)
    repo.append_counsel_signoff(CounselSignoff(clinic_id=CLINIC, practice_id=pid, signed_by="counsel"))
    sm.advance(pid, PracticeState.PROFILED)
    with pytest.raises(GuardError) as e:
        sm.advance(pid, PracticeState.NORMALIZED)
    assert e.value.guard == "profile_gate"
    assert sm.current_state(pid) == "profiled"
    # once a FormatProfile exists, normalized is reachable
    repo.create_format_profile(FormatProfile(
        clinic_id=CLINIC, practice_id=pid, practice_database_id="x", export_variant="complete_v1"))
    sm.advance(pid, PracticeState.NORMALIZED)
    assert sm.current_state(pid) == "normalized"


def _advance_to_normalized(repo, sm, pid):
    repo.append_counsel_signoff(CounselSignoff(clinic_id=CLINIC, practice_id=pid, signed_by="counsel"))
    repo.create_format_profile(FormatProfile(
        clinic_id=CLINIC, practice_id=pid, practice_database_id="x", export_variant="complete_v1"))
    sm.advance(pid, PracticeState.PROFILED)
    sm.advance(pid, PracticeState.NORMALIZED)


def test_quality_floor_blocks_advance_past_normalized(repo):
    sm = StateMachine(repo)
    pid = _received(repo, sm)
    _advance_to_normalized(repo, sm, pid)
    repo.create_quality_assessment(QualityAssessment(
        clinic_id=CLINIC, practice_id=pid, usable_record_share=0.5, below_floor=True))
    with pytest.raises(GuardError) as e:
        sm.advance(pid, PracticeState.VERIFIED)
    assert e.value.guard == "quality_floor"
    # a below-floor practice can be HELD (first-class off-path) and never reaches shadow_ready
    sm.hold(pid, "quality floor breached")
    assert sm.current_state(pid) == "held"


def test_ar_variance_blocks_reconciled(repo):
    sm = StateMachine(repo)
    pid = _received(repo, sm)
    _advance_to_normalized(repo, sm, pid)
    sm.advance(pid, PracticeState.VERIFIED)
    repo.append_reconciliation_report(ReconciliationReport(
        clinic_id=CLINIC, practice_id=pid, blocking=True))
    with pytest.raises(GuardError) as e:
        sm.advance(pid, PracticeState.RECONCILED)
    assert e.value.guard == "ar_variance"
    assert sm.current_state(pid) == "verified"


def test_offpath_never_auto_advances_to_shadow_ready(repo):
    sm = StateMachine(repo)
    pid = _received(repo, sm)
    sm.hold(pid, "held early")
    with pytest.raises(IllegalTransition):
        sm.advance(pid, PracticeState.SHADOW_READY)
    assert sm.current_state(pid) != "shadow_ready"


def test_full_happy_path_reaches_shadow_ready(repo):
    sm = StateMachine(repo)
    pid = _received(repo, sm)
    _advance_to_normalized(repo, sm, pid)
    sm.advance(pid, PracticeState.VERIFIED)
    sm.advance(pid, PracticeState.RECONCILED)
    sm.advance(pid, PracticeState.IDENTITY_BOOTSTRAPPED)
    sm.advance(pid, PracticeState.SHADOW_READY)
    assert sm.current_state(pid) == "shadow_ready"
    # one append-only row per transition: received..shadow_ready = 7 rows
    assert len(repo.get_state_transitions(pid)) == 7


def test_advance_is_the_only_write_path_and_appends_one_row(repo):
    sm = StateMachine(repo)
    pid = _received(repo, sm)
    repo.append_counsel_signoff(CounselSignoff(clinic_id=CLINIC, practice_id=pid, signed_by="c"))
    before = len(repo.get_state_transitions(pid))
    sm.advance(pid, PracticeState.PROFILED)
    after = len(repo.get_state_transitions(pid))
    assert after - before == 1
