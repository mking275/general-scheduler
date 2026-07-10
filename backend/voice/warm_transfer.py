"""Feature 010 — Vera Voice: T029 warm transfer + T030 overflow fallback (Phase E).

The escalation endpoint with **independent transfer authority** (plugs into the
T017 ``EscalationWatchdog`` via ``as_transfer_fn``). In live mode this is a
Twilio **Conference + Dial** with a **whisper summary** delivered to the human
*before* the caller is bridged; in sim the whole chain runs with no telephony.

Fallback chain (T030, FR-020) — **never dead air, never a silent drop**:
  1. Dial ``on_call_target``s in ``priority`` order; the first to answer gets the
     whisper summary, then the caller is connected.
  2. If none answer -> read out the ER directory + make a callback promise (the
     callback reuses the ``sms_gateway`` outbound leg).
  3. Last resort -> voicemail with a callback promise.

Escalation-event persistence (T031): ``escalate_and_persist`` writes a complete
``escalation_event`` (target, whisper, outcome, fallback path) — the auditable
record of every escalation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional

from backend.models import (
    CallSession, EscalationEvent, EscalationTrigger, TransferOutcome,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class TransferResult:
    outcome: TransferOutcome
    whisper_summary: str
    target: Optional[dict] = None            # the on_call_target that answered
    whisper_before_connect: bool = False     # whisper delivered BEFORE caller bridged
    attempts: list = field(default_factory=list)   # targets tried, in priority order
    fallback_path: Optional[str] = None      # set when no human answered
    er_directory_read: bool = False
    callback_promised: bool = False
    dead_air: bool = False                   # INVARIANT: always False


# An "answer policy" decides, in sim, whether a given target picks up. Default:
# the first (highest-priority) target answers. Tests inject no-answer policies.
AnswerPolicy = Callable[[dict], bool]


class WarmTransfer:
    def __init__(
        self,
        targets: list[dict],
        sms_gateway=None,
        er_directory: Optional[list[dict]] = None,
        repo=None,
        answer_policy: Optional[AnswerPolicy] = None,
        live: Optional[bool] = None,
    ):
        # Ordered by transfer-attempt priority.
        self.targets = sorted(targets or [], key=lambda t: t.get("priority", 999))
        self.sms_gateway = sms_gateway
        self.er_directory = er_directory or []
        self.repo = repo
        self.answer_policy = answer_policy or (lambda t: t == self.targets[0] if self.targets else False)
        if live is None:
            from backend.voice import sim as sim_mod
            live = sim_mod.is_live()
        self.live = live

    # ------------------------------------------------------------------ #
    #  The transfer + fallback chain
    # ------------------------------------------------------------------ #
    def transfer(self, session: CallSession, whisper_summary: str) -> TransferResult:
        assert not self.live, "live warm transfer is a pilot-activation config swap"
        res = TransferResult(outcome=TransferOutcome.NO_ANSWER,
                             whisper_summary=whisper_summary)

        # 1. Dial targets in priority order; whisper BEFORE connecting the caller.
        for target in self.targets:
            res.attempts.append(target.get("label", target.get("phone", "?")))
            if self.answer_policy(target):
                # Whisper the summary to the human first, THEN bridge the caller.
                res.whisper_before_connect = True
                res.target = target
                res.outcome = TransferOutcome.ANSWERED
                return res

        # 2. No human answered -> ER directory readout + callback promise.
        if self.er_directory:
            res.er_directory_read = True
            res.outcome = TransferOutcome.FALLBACK_ER_DIRECTORY
            res.fallback_path = "er_directory_readout+callback"
            self._promise_callback(session)
            res.callback_promised = True
            return res

        # 3. Last resort -> voicemail with callback promise.
        res.outcome = TransferOutcome.VOICEMAIL_CALLBACK
        res.fallback_path = "voicemail+callback"
        self._promise_callback(session)
        res.callback_promised = True
        return res

    def _promise_callback(self, session: CallSession) -> None:
        """Reuse the sms_gateway outbound leg for the callback guarantee."""
        if self.sms_gateway is not None and session.inbound_number:
            self.sms_gateway.send_sms(
                session.inbound_number,
                "This is Goldsmith Veterinary Clinic's after-hours line. We could not "
                "reach the on-call team by phone; a member of staff will call you back. "
                "If this is a life-threatening emergency, please contact the ER listed.",
            )

    # ------------------------------------------------------------------ #
    #  Watchdog adapter (independent transfer authority)
    # ------------------------------------------------------------------ #
    def as_transfer_fn(self) -> Callable[[CallSession, str], TransferOutcome]:
        """The callable the T017 ``EscalationWatchdog`` invokes directly."""
        def _fn(session: CallSession, whisper_summary: str) -> TransferOutcome:
            return self.transfer(session, whisper_summary).outcome
        return _fn

    # ------------------------------------------------------------------ #
    #  Escalation-event persistence (T031)
    # ------------------------------------------------------------------ #
    def escalate_and_persist(
        self,
        session: CallSession,
        whisper_summary: str,
        trigger: EscalationTrigger,
        protocol_state: Optional[str] = None,
        watchdog_fired: bool = False,
    ) -> tuple[TransferResult, EscalationEvent]:
        result = self.transfer(session, whisper_summary)
        ev = EscalationEvent(
            call_session_id=session.id,
            trigger=trigger,
            protocol_state=protocol_state,
            triggered_at=_now_iso(),
            transfer_target_id=(result.target or {}).get("id") if result.target else None,
            whisper_summary=whisper_summary,
            transfer_outcome=result.outcome,
            fallback_path=result.fallback_path,
            watchdog_fired=watchdog_fired,
            resolved_at=_now_iso(),
            audit_retained_until=(datetime.now(timezone.utc) + timedelta(days=185)).isoformat(),
        )
        if self.repo is not None:
            self.repo.create_escalation_event(ev)
        return result, ev


# --------------------------------------------------------------------------- #
#  Config loader — build targets/er_directory from clinic_voice_config yaml
# --------------------------------------------------------------------------- #
def targets_from_config(cfg: dict) -> list[dict]:
    return list(cfg.get("on_call_targets") or [])


def er_directory_from_config(cfg: dict) -> list[dict]:
    return list(cfg.get("er_directory") or [])
