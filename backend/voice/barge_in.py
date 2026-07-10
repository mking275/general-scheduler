"""Feature 010 — Vera Voice: T019 barge-in detection + backchannel filter.

Server VAD with a <400 ms detect budget. "emergency" ALWAYS cuts through
(barge-in -> escalation). Backchannels ("uh-huh", "mm-hmm") are the #1
turn-taking failure and must NOT misfire as an interrupt (D4).
"""
from __future__ import annotations

from dataclasses import dataclass

from backend.voice.adapter_guarantees import _EMERGENCY_LITERALS

DETECT_BUDGET_MS = 400
VAD_FRAME_MS = 20                     # server VAD frame size
_ENERGY_THRESHOLD = 500               # RMS above this = speech onset

# Backchannels that must be filtered out (never trigger barge-in).
BACKCHANNELS = {
    "uh-huh", "uh huh", "uhhuh", "mm-hmm", "mmhmm", "mhm", "mm", "yeah", "yep",
    "ok", "okay", "right", "sure", "got it", "i see", "hmm", "aha",
}


@dataclass
class BargeInResult:
    barge_in: bool
    cut_through: bool                 # emergency always cuts through
    reason: str
    detect_latency_ms: int


def _normalize(text: str) -> str:
    return "".join(ch for ch in (text or "").lower() if ch.isalnum() or ch.isspace()).strip()


class BargeInDetector:
    def __init__(self, detect_budget_ms: int = DETECT_BUDGET_MS,
                 backchannel_filter: bool = True):
        self.detect_budget_ms = detect_budget_ms
        self.backchannel_filter = backchannel_filter

    def detect(self, caller_text: str = "", energy: int = 0,
               frames_observed: int = 3) -> BargeInResult:
        """Decide whether caller speech during Vera's utterance is a real
        interrupt. Detect latency is ``frames_observed`` VAD frames + a small
        classification cost, kept inside the <400 ms budget."""
        latency = min(self.detect_budget_ms - 1, frames_observed * VAD_FRAME_MS + 60)
        text = _normalize(caller_text)

        # 1. Emergency ALWAYS cuts through, regardless of energy/backchannel.
        if any(lit in (caller_text or "").lower() for lit in _EMERGENCY_LITERALS):
            return BargeInResult(True, cut_through=True, reason="emergency",
                                 detect_latency_ms=latency)

        # 2. Backchannel filter — acknowledgements are not interrupts.
        if self.backchannel_filter and text in BACKCHANNELS:
            return BargeInResult(False, cut_through=False, reason="backchannel_filtered",
                                 detect_latency_ms=latency)

        # 3. Real speech onset (meaningful content or sustained energy).
        meaningful = bool(text) and text not in BACKCHANNELS
        if meaningful or energy >= _ENERGY_THRESHOLD:
            return BargeInResult(True, cut_through=False, reason="speech_onset",
                                 detect_latency_ms=latency)

        return BargeInResult(False, cut_through=False, reason="no_speech",
                             detect_latency_ms=latency)
