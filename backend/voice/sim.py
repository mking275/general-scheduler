"""Feature 010 — Vera Voice: T005 dual-mode env resolver + scripted call
simulator.

Mirrors ``backend/sms_gateway.py``'s auto-detect: a ``VOICE_LIVE`` force flag
plus credential presence decides ``is_live()``. With no credentials the whole
stack runs in SIMULATION — zero live telephony / LLM-audio calls.

The ``CallSimulator`` replays a scripted call: it feeds caller audio/transcript
and line events (silence, DTMF, hangup) into the bridge and emits ordered turn
events, so every downstream component (bridge, adapters, turn loop, watchdog)
is exercised without Twilio or a realtime LLM.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Iterator, Optional

try:  # load .env like sms_gateway does (no-op if python-dotenv absent)
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))
except ImportError:
    pass

logger = logging.getLogger("vpma.voice.sim")


# --------------------------------------------------------------------------- #
#  Dual-mode resolver (mirrors sms_gateway._resolve_mode)
# --------------------------------------------------------------------------- #
def is_live() -> bool:
    """True only if real telephony + realtime-model credentials are present
    (or ``VOICE_LIVE=true`` forces it). Defaults to False → simulation."""
    force = os.getenv("VOICE_LIVE", "").strip().lower()
    if force == "false":
        return False
    if force == "true":
        return True
    # Auto-detect: need Twilio creds AND at least one realtime-model key.
    twilio_ok = bool(
        os.getenv("TWILIO_ACCOUNT_SID", "").strip()
        and os.getenv("TWILIO_AUTH_TOKEN", "").strip()
        and os.getenv("TWILIO_FROM_NUMBER", "").strip()
    )
    model_ok = bool(
        os.getenv("GEMINI_API_KEY", "").strip()
        or os.getenv("GOOGLE_API_KEY", "").strip()
        or os.getenv("OPENAI_API_KEY", "").strip()
    )
    live = twilio_ok and model_ok
    if not live:
        logger.warning(
            "VOICE: SIMULATION mode — no live telephony/model credentials found. "
            "Set TWILIO_* + GEMINI_API_KEY/OPENAI_API_KEY (or VOICE_LIVE=true) for live."
        )
    return live


# --------------------------------------------------------------------------- #
#  Scripted call events
# --------------------------------------------------------------------------- #
class SimEventType(str, Enum):
    CALLER_UTTERANCE = "caller_utterance"    # caller speaks (text + optional audio)
    SILENCE = "silence"                       # dead air for N ms
    DTMF = "dtmf"                             # keypad digit
    HANGUP = "hangup"                         # caller drops


@dataclass
class SimEvent:
    type: SimEventType
    text: str = ""                            # for CALLER_UTTERANCE
    audio: Optional[bytes] = None             # μ-law 8k payload (optional)
    silence_ms: int = 0                       # for SILENCE
    dtmf: str = ""                            # for DTMF
    at_ms: int = 0                            # relative time offset in the script


@dataclass
class ScriptedCall:
    """A scripted inbound call: caller line + events."""
    inbound_number: str = "+15558675309"
    clinic_id: str = "goldsmith-0001"
    events: list[SimEvent] = field(default_factory=list)

    def utter(self, text: str, at_ms: int = 0, audio: Optional[bytes] = None) -> "ScriptedCall":
        self.events.append(SimEvent(SimEventType.CALLER_UTTERANCE, text=text, audio=audio, at_ms=at_ms))
        return self

    def silence(self, ms: int, at_ms: int = 0) -> "ScriptedCall":
        self.events.append(SimEvent(SimEventType.SILENCE, silence_ms=ms, at_ms=at_ms))
        return self

    def dtmf(self, digit: str, at_ms: int = 0) -> "ScriptedCall":
        self.events.append(SimEvent(SimEventType.DTMF, dtmf=digit, at_ms=at_ms))
        return self

    def hangup(self, at_ms: int = 0) -> "ScriptedCall":
        self.events.append(SimEvent(SimEventType.HANGUP, at_ms=at_ms))
        return self


class CallSimulator:
    """Replays a ScriptedCall, yielding events in order. Consumed by the sim
    Media Streams bridge (T013) and the adapters (T011/T012)."""

    def __init__(self, script: ScriptedCall):
        self.script = script
        self._emitted: list[SimEvent] = []

    def events(self) -> Iterator[SimEvent]:
        for ev in self.script.events:
            self._emitted.append(ev)
            logger.info("SIM emit: %s %r", ev.type.value, ev.text or ev.dtmf or ev.silence_ms)
            yield ev

    @property
    def emitted(self) -> list[SimEvent]:
        return list(self._emitted)


def demo_script() -> ScriptedCall:
    """A representative after-hours booking call used across the sim tests."""
    return (
        ScriptedCall()
        .utter("Hi, this is Jane Alvarez. I'd like to book a follow-up for Rex.", at_ms=1000)
        .utter("Tomorrow afternoon works.", at_ms=5000)
        .silence(400, at_ms=8000)
        .utter("Great, thank you.", at_ms=9000)
        .hangup(at_ms=11000)
    )
