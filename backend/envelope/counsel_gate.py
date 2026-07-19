"""Feature 009 — T011 counsel sign-off gate.

Records/enforces **counsel sign-off on the clinic-owned-data structure** as a
hard state-machine guard: ``received -> profiled/normalized`` is **unreachable**
until a ``counsel_signoff`` row is recorded (FR-004, §3.2(h) posture). This is
the one gate with **no engineering bypass by design** — the enforcement lives in
``state_machine.StateMachine._counsel_gate`` (the single write path), which
consults ``repo.has_counsel_signoff`` on every advance to ``profiled`` /
``normalized``. This module owns the *recording* side of that gate; there is
deliberately no "advance anyway" / override function here.

Vault receipt (T009, a §6.3 backup) proceeds **before** the gate and is
unaffected by it.
"""
from __future__ import annotations

from typing import Optional

from backend.models import CounselSignoff


class CounselGate:
    def __init__(self, repo):
        self.repo = repo

    def record_signoff(self, clinic_id: str, practice_id: str, signed_by: str,
                       structure_version: str = "v1", scope: str = "",
                       signed_at: Optional[str] = None) -> CounselSignoff:
        """Record counsel sign-off on the clinic-owned-data structure — the
        append-only row whose PRESENCE the state machine's counsel gate checks.
        After this row exists, the practice may advance to profiled/normalized."""
        kwargs = dict(clinic_id=clinic_id, practice_id=practice_id,
                      signed_by=signed_by, structure_version=structure_version,
                      scope=scope)
        if signed_at is not None:
            kwargs["signed_at"] = signed_at
        signoff = CounselSignoff(**kwargs)
        self.repo.append_counsel_signoff(signoff)
        return signoff

    def is_cleared(self, practice_id: str) -> bool:
        """True iff a counsel_signoff row exists for the practice (the gate
        condition the state machine enforces)."""
        return self.repo.has_counsel_signoff(practice_id)
