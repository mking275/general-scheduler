"""Feature 010 — Vera Voice: adapter guarantees (contract B2) — NON-NEGOTIABLE,
enforced BELOW the model, not in a prompt.

Three guarantees live here, spanning wave-1 tasks:
  * T016 — disclosure-before-model: first utterance is the disclosure script,
    played before the model engages, on 100% of calls (FR-002/003).
  * T017 — escalation watchdog with INDEPENDENT transfer authority: fires on
    ``protocol_flag`` | literal "emergency" | silence-threshold even if the
    model stalls or misroutes (FR-017), warm-transferring within SLO.
  * T018 — append-only transcript + ``call_turn`` event log on every session
    (FR-021/024); UPDATE/DELETE on a logged turn is rejected at the DB level.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional

from backend.models import (
    CallSession, CallTranscript, CallTurn, EscalationEvent, EscalationTrigger,
    TransferOutcome, TurnRole,
)

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_DISCLOSURE_DIR = os.path.join(_REPO_ROOT, "config", "voice")

# --- literal emergency detection (independent of the model / protocol engine)
_EMERGENCY_LITERALS = ("emergency", "help now", "urgent")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_disclosure(locale: str = "en") -> str:
    path = os.path.join(_DISCLOSURE_DIR, f"disclosure_script.{locale}.txt")
    with open(path) as f:
        return f.read().strip()


# ===========================================================================
# T016 — Disclosure-before-model
# ===========================================================================
class DisclosureNotDeliveredError(RuntimeError):
    """Raised if the model is allowed to engage before disclosure (guard)."""


class DisclosureGuarantee:
    def __init__(self, repo=None, disclosure_text: Optional[str] = None,
                 locale: str = "en"):
        self.repo = repo
        self.disclosure_text = disclosure_text or load_disclosure(locale)
        self._disclosed: set[str] = set()

    def deliver_disclosure(self, session: CallSession) -> CallTurn:
        """Play the disclosure as turn ``seq=1`` and stamp consent = that time.
        Must run before the model engages. Returns the disclosure turn."""
        ts = now_iso()
        turn = CallTurn(call_session_id=session.id, seq=1, role=TurnRole.SYSTEM,
                        text=self.disclosure_text, is_final=True, started_at=ts)
        session.consent_recorded_at = ts          # consent = disclosure time (SC-001)
        self._disclosed.add(session.id)
        if self.repo is not None:
            self.repo.append_call_turn(turn)
            self.repo.update_call_session(session.id, consent_recorded_at=ts)
        return turn

    def is_disclosed(self, session_id: str) -> bool:
        return session_id in self._disclosed

    def guard_model_engage(self, session: CallSession) -> None:
        """The model MUST NOT engage before disclosure. Enforced below the model."""
        if session.id not in self._disclosed:
            raise DisclosureNotDeliveredError(
                f"model engaged before disclosure on call {session.id}")


# ===========================================================================
# T017 — Escalation watchdog with independent transfer authority
# ===========================================================================
# The transfer authority (T029 warm_transfer, stubbed here) — the watchdog
# calls it DIRECTLY, never through the model.
TransferFn = Callable[[CallSession, str], TransferOutcome]


def _sim_transfer(session: CallSession, whisper_summary: str) -> TransferOutcome:
    return TransferOutcome.ANSWERED


@dataclass
class WatchdogResult:
    fired: bool
    trigger: EscalationTrigger
    event: EscalationEvent
    latency_ms: float
    within_slo: bool
    transfer_outcome: TransferOutcome


class EscalationWatchdog:
    """Independent transfer authority. Fires on deterministic signals even if
    the model stalls or misroutes — model compliance is never on the path."""

    def __init__(self, transfer_fn: Optional[TransferFn] = None,
                 slo_ms: int = 3000, silence_threshold_ms: int = 8000, repo=None):
        self.transfer_fn = transfer_fn or _sim_transfer
        self.slo_ms = slo_ms
        self.silence_threshold_ms = silence_threshold_ms
        self.repo = repo

    # --- deterministic detectors ---------------------------------------
    @staticmethod
    def is_emergency_literal(text: str) -> bool:
        t = (text or "").lower()
        return any(lit in t for lit in _EMERGENCY_LITERALS)

    def _fire(self, session: CallSession, trigger: EscalationTrigger,
              protocol_state: Optional[str], summary: str) -> WatchdogResult:
        start = time.monotonic()
        outcome = self.transfer_fn(session, summary)      # independent authority
        latency_ms = (time.monotonic() - start) * 1000.0
        ev = EscalationEvent(
            call_session_id=session.id, trigger=trigger, protocol_state=protocol_state,
            triggered_at=now_iso(), whisper_summary=summary,
            transfer_outcome=outcome, watchdog_fired=True, resolved_at=now_iso(),
            audit_retained_until=(datetime.now(timezone.utc) + timedelta(days=185)).isoformat(),
        )
        if self.repo is not None:
            self.repo.create_escalation_event(ev)
        return WatchdogResult(fired=True, trigger=trigger, event=ev,
                              latency_ms=latency_ms, within_slo=latency_ms <= self.slo_ms,
                              transfer_outcome=outcome)

    def observe_transcript(self, session: CallSession, text: str,
                           protocol_flag: Optional[str] = None) -> Optional[WatchdogResult]:
        if protocol_flag:                                  # protocol_keyword branch (T020 feeds this)
            return self._fire(session, EscalationTrigger.PROTOCOL_KEYWORD, protocol_flag,
                              f"Protocol-flagged ({protocol_flag}) call — connecting a person.")
        if self.is_emergency_literal(text):                # literal "emergency" branch
            return self._fire(session, EscalationTrigger.EXPLICIT_EMERGENCY, None,
                              "Caller stated an emergency — connecting a person now.")
        return None

    def observe_silence(self, session: CallSession, silence_ms: int) -> Optional[WatchdogResult]:
        if silence_ms >= self.silence_threshold_ms:        # silence-threshold branch
            return self._fire(session, EscalationTrigger.SLO_BREACH, None,
                              "Prolonged silence — connecting a person.")
        return None

    def observe_model_stall(self, session: CallSession, waited_ms: int) -> Optional[WatchdogResult]:
        """Model produced no output within SLO — fire regardless of the model."""
        if waited_ms >= self.slo_ms:
            return self._fire(session, EscalationTrigger.SLO_BREACH, None,
                              "Assistant unresponsive — connecting a person.")
        return None


# ===========================================================================
# T018 — Append-only transcript + call_turn event log
# ===========================================================================
class TranscriptLogger:
    """Every turn writes an immutable ``call_turn`` row; the full transcript is
    an append-only ``call_transcript`` record. Immutability is enforced at the
    DB level by the append-only triggers installed in ``VoiceRepository``."""

    def __init__(self, repo):
        self.repo = repo

    def log_turn(self, turn: CallTurn) -> dict:
        return self.repo.append_call_turn(turn)

    def finalize_transcript(self, session: CallSession, full_text: str,
                            vendor_attestation: Optional[str] = None,
                            protocol_flagged: bool = False,
                            audio_ref: Optional[str] = None) -> dict:
        retain_days = 185 if protocol_flagged else 30      # >=6mo for flagged (FR-021)
        transcript = CallTranscript(
            call_session_id=session.id, full_text=full_text, audio_ref=audio_ref,
            consent_record={"disclosure_at": session.consent_recorded_at,
                            "posture": "all_party"},
            vendor_no_training_attestation=vendor_attestation,
            retained_until=(datetime.now(timezone.utc) + timedelta(days=retain_days)).isoformat(),
        )
        return self.repo.append_transcript(transcript)
