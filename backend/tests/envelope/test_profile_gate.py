"""Feature 009 — T014 profile-before-normalize guard acceptance.

- attempting normalization on a database with no FormatProfile is rejected;
- once discovery writes the profile the practice may advance to profiled then
  normalized;
- 0 databases are reachable at `normalized` without a profile.
"""
import uuid

import pytest

from backend.envelope.extraction_port import SimExtractionPort
from backend.envelope.format_discovery import FormatDiscovery
from backend.envelope.state_machine import GuardError, StateMachine
from backend.models import CounselSignoff, PracticeDatabase, PracticeState
from backend.tests.envelope.fixtures.ezyvet_synthetic_export import generate_practice_export

CLINIC = "goldsmith"


def _prep(repo, sm):
    pid = f"p-{uuid.uuid4().hex[:8]}"
    repo.create_practice_database(PracticeDatabase(
        clinic_id=CLINIC, practice_id=pid, delivery_id="d1"))
    sm.receive(pid, CLINIC)
    repo.append_counsel_signoff(CounselSignoff(clinic_id=CLINIC, practice_id=pid, signed_by="c"))
    return pid


def test_normalize_blocked_without_profile_then_permitted(repo):
    sm = StateMachine(repo)
    pid = _prep(repo, sm)
    sm.advance(pid, PracticeState.PROFILED)
    # no FormatProfile -> normalized rejected
    with pytest.raises(GuardError) as e:
        sm.advance(pid, PracticeState.NORMALIZED)
    assert e.value.guard == "profile_gate"
    assert sm.current_state(pid) == "profiled"

    # discovery writes the profile -> normalized reachable
    fd = FormatDiscovery(repo, extraction_port=SimExtractionPort())
    fd.discover(CLINIC, pid, "pdb1", generate_practice_export(pid, seed=7))
    sm.advance(pid, PracticeState.NORMALIZED)
    assert sm.current_state(pid) == "normalized"


def test_zero_databases_normalized_without_a_profile(repo):
    """Across a small batch, no practice is at `normalized` without a profile."""
    sm = StateMachine(repo)
    fd = FormatDiscovery(repo, extraction_port=SimExtractionPort())
    pids = []
    for i in range(4):
        pid = _prep(repo, sm)
        sm.advance(pid, PracticeState.PROFILED)
        pids.append(pid)
        if i % 2 == 0:  # only half get a profile + normalize
            fd.discover(CLINIC, pid, "pdb", generate_practice_export(pid, seed=i))
            sm.advance(pid, PracticeState.NORMALIZED)
    for pid in pids:
        if sm.current_state(pid) == "normalized":
            assert repo.has_format_profile(pid), f"{pid} normalized without a profile"
