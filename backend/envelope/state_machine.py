"""Feature 009 — T006 per-practice staged state machine + transition guards.

One append-only ``state_transition`` row per practice advances the linear happy
path ``received -> profiled -> normalized -> verified -> reconciled ->
identity_bootstrapped -> shadow_ready``; ``blocked`` / ``partial`` / ``held`` /
``delta`` are **first-class** off-path states (a practice may sit at any of them
without stalling the batch and never auto-advances to ``shadow_ready``).

**This is the single write path** — every state change goes through ``advance()``
(or ``receive()`` for the initial row); there is no bypass that mutates
``practice_database.state`` without also appending the audit row.

Four hard transition guards, keyed to the target state:

  * **counsel gate** (T011)  — ``profiled`` / ``normalized`` unreachable until a
    ``counsel_signoff`` row exists (FR-004). No engineering bypass by design.
  * **profile-before-normalize** (T014) — ``normalized`` unreachable without a
    completed ``FormatProfile`` (FR-006).
  * **quality-floor block** (T023) — if a ``QualityAssessment`` marks the
    practice ``below_floor`` (>20% unusable), it cannot advance past
    ``normalized``; the caller holds it at ``held`` (FR-015).
  * **AR-variance block** (T026) — if the latest ``ReconciliationReport`` is
    ``blocking`` (unexplained AR variance), it cannot reach ``reconciled`` or
    beyond (FR-017).

The floor/AR guards read the assessment/report rows the downstream tiers write
(T022/T023 quality, T024/T025 reconciliation); wiring them here keeps the state
machine the sole arbiter of advancement.
"""
from __future__ import annotations

from typing import Callable, Optional

from backend.models import PracticeState, StateTransition

# The linear happy path.
LINEAR: tuple[str, ...] = (
    PracticeState.RECEIVED.value,
    PracticeState.PROFILED.value,
    PracticeState.NORMALIZED.value,
    PracticeState.VERIFIED.value,
    PracticeState.RECONCILED.value,
    PracticeState.IDENTITY_BOOTSTRAPPED.value,
    PracticeState.SHADOW_READY.value,
)

OFF_PATH: frozenset[str] = frozenset({
    PracticeState.BLOCKED.value, PracticeState.PARTIAL.value,
    PracticeState.HELD.value, PracticeState.DELTA.value,
})

VALID_STATES: frozenset[str] = frozenset(s.value for s in PracticeState)


class GuardError(Exception):
    """A hard transition guard blocked the advance. The practice's state is
    unchanged and no ``state_transition`` row is written."""

    def __init__(self, practice_id: str, to_state: str, guard: str, detail: str = ""):
        self.practice_id = practice_id
        self.to_state = to_state
        self.guard = guard
        super().__init__(
            f"[{guard}] transition of {practice_id} -> {to_state} blocked: {detail}"
        )


class IllegalTransition(Exception):
    """The requested edge is not a legal transition (structural, not a guard)."""


def _as_value(state) -> str:
    return state.value if isinstance(state, PracticeState) else str(state)


class StateMachine:
    def __init__(self, repo):
        self.repo = repo
        # target_state -> ordered guards that must all pass
        self._guards: dict[str, list[Callable[[str], None]]] = {
            PracticeState.PROFILED.value: [self._counsel_gate],
            PracticeState.NORMALIZED.value: [self._counsel_gate, self._profile_gate],
            PracticeState.VERIFIED.value: [self._quality_floor],
            PracticeState.RECONCILED.value: [self._quality_floor, self._ar_variance],
            PracticeState.IDENTITY_BOOTSTRAPPED.value: [self._quality_floor, self._ar_variance],
            PracticeState.SHADOW_READY.value: [self._quality_floor, self._ar_variance],
        }

    # ------------------------------------------------------------------ #
    #  Read the current state (last transition wins)
    # ------------------------------------------------------------------ #
    def current_state(self, practice_id: str) -> Optional[str]:
        pd = self.repo.get_practice_database_by_practice(practice_id)
        return pd["state"] if pd else None

    # ------------------------------------------------------------------ #
    #  Initial receipt row — the ONLY entry into the machine
    # ------------------------------------------------------------------ #
    def receive(self, practice_id: str, clinic_id: str, reason: str = "vault receipt") -> None:
        """Write the initial ``-> received`` transition (from_state=None)."""
        self.repo.append_state_transition(StateTransition(
            clinic_id=clinic_id, practice_id=practice_id,
            from_state=None, to_state=PracticeState.RECEIVED, reason=reason,
        ))
        self.repo.set_practice_state(practice_id, PracticeState.RECEIVED.value)

    # ------------------------------------------------------------------ #
    #  advance — the single guarded write path
    # ------------------------------------------------------------------ #
    def advance(self, practice_id: str, to_state, reason: str = "",
                clinic_id: Optional[str] = None) -> str:
        target = _as_value(to_state)
        if target not in VALID_STATES:
            raise IllegalTransition(f"{target!r} is not a valid practice_state")

        pd = self.repo.get_practice_database_by_practice(practice_id)
        if pd is None:
            raise IllegalTransition(f"{practice_id} has no practice_database (receive() first)")
        current = pd["state"]
        clinic_id = clinic_id or pd["clinic_id"]

        self._check_legal(practice_id, current, target)

        # run every guard for the target; the first failure blocks (raises)
        for guard in self._guards.get(target, []):
            guard(practice_id)

        self.repo.append_state_transition(StateTransition(
            clinic_id=clinic_id, practice_id=practice_id,
            from_state=current, to_state=target, reason=reason,
        ))
        self.repo.set_practice_state(practice_id, target)
        return target

    # ------------------------------------------------------------------ #
    #  Structural legality (not a guard)
    # ------------------------------------------------------------------ #
    def _check_legal(self, practice_id: str, current: str, target: str) -> None:
        # shadow_ready is reachable ONLY from identity_bootstrapped — an
        # off-path (held/blocked/partial/delta) practice never auto-advances.
        if target == PracticeState.SHADOW_READY.value \
                and current != PracticeState.IDENTITY_BOOTSTRAPPED.value:
            raise IllegalTransition(
                f"{practice_id}: shadow_ready only from identity_bootstrapped "
                f"(current={current}); off-path states never auto-advance"
            )

    # ------------------------------------------------------------------ #
    #  Guards
    # ------------------------------------------------------------------ #
    def _counsel_gate(self, practice_id: str) -> None:
        """No profiled/normalized without a recorded counsel_signoff (FR-004)."""
        if not self.repo.has_counsel_signoff(practice_id):
            raise GuardError(practice_id, "profiled/normalized", "counsel_gate",
                             "no counsel_signoff row on the clinic-owned-data structure")

    def _profile_gate(self, practice_id: str) -> None:
        """No normalized without a completed FormatProfile (FR-006)."""
        if not self.repo.has_format_profile(practice_id):
            raise GuardError(practice_id, "normalized", "profile_gate",
                             "no FormatProfile row for the database")

    def _quality_floor(self, practice_id: str) -> None:
        """>20% unusable -> cannot advance past normalized; hold it (FR-015)."""
        qa = self.repo.get_quality_assessment(practice_id)
        if qa is not None and qa.get("below_floor"):
            raise GuardError(practice_id, "verified+", "quality_floor",
                             f"usable_record_share={qa.get('usable_record_share')} below floor")

    def _ar_variance(self, practice_id: str) -> None:
        """Unexplained AR variance -> cannot reach reconciled/beyond (FR-017)."""
        reports = self.repo.get_reconciliation_reports(practice_id)
        if reports and reports[-1].get("blocking"):
            raise GuardError(practice_id, "reconciled+", "ar_variance",
                             "reconciliation report is blocking (unexplained AR variance)")

    # ------------------------------------------------------------------ #
    #  Convenience: hold / block / mark-partial (off-path, always legal)
    # ------------------------------------------------------------------ #
    def hold(self, practice_id: str, reason: str, clinic_id: Optional[str] = None) -> str:
        return self.advance(practice_id, PracticeState.HELD, reason, clinic_id)

    def block(self, practice_id: str, reason: str, clinic_id: Optional[str] = None) -> str:
        return self.advance(practice_id, PracticeState.BLOCKED, reason, clinic_id)

    def mark_partial(self, practice_id: str, reason: str, clinic_id: Optional[str] = None) -> str:
        return self.advance(practice_id, PracticeState.PARTIAL, reason, clinic_id)
