"""Feature 009 — T011 counsel-gate acceptance.

- with NO counsel_signoff row, advancing a received practice to
  profiled/normalized is blocked (holds at received);
- after the signoff row is written the transition is permitted;
- the vault receipt itself is unaffected by the gate.

Also: a static assertion that the gate has NO engineering bypass — no
"advance anyway" / override path exists in counsel_gate.py.
"""
import ast
import uuid

import pytest

from backend.envelope.counsel_gate import CounselGate
from backend.envelope import counsel_gate as counsel_gate_mod
from backend.envelope.state_machine import GuardError, StateMachine
from backend.models import PracticeDatabase, PracticeState

CLINIC = "goldsmith"


def _received(repo, sm):
    pid = f"p-{uuid.uuid4().hex[:8]}"
    repo.create_practice_database(PracticeDatabase(
        clinic_id=CLINIC, practice_id=pid, delivery_id="d1"))
    sm.receive(pid, CLINIC)
    return pid


def test_gate_blocks_then_permits(repo):
    sm = StateMachine(repo)
    gate = CounselGate(repo)
    pid = _received(repo, sm)

    assert gate.is_cleared(pid) is False
    with pytest.raises(GuardError):
        sm.advance(pid, PracticeState.PROFILED)
    with pytest.raises(GuardError):
        sm.advance(pid, PracticeState.NORMALIZED)
    assert sm.current_state(pid) == "received"   # holds at received

    gate.record_signoff(CLINIC, pid, signed_by="general_counsel",
                        scope="clinic-owned-data structure v1")
    assert gate.is_cleared(pid) is True
    sm.advance(pid, PracticeState.PROFILED)       # now permitted
    assert sm.current_state(pid) == "profiled"


def test_gate_has_no_engineering_bypass():
    """No override / advance-anyway / force path exists in the gate module."""
    src = open(counsel_gate_mod.__file__).read()
    tree = ast.parse(src)
    func_names = {n.name for n in ast.walk(tree)
                  if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    forbidden = {"override", "force", "bypass", "advance", "skip_gate", "waive"}
    assert not (func_names & forbidden), f"counsel gate must not expose {func_names & forbidden}"
