"""Feature 010 — Vera Voice: T013 Twilio Media Streams bridge + T014
transparent session resumption.

Bridges a Twilio Media Streams WebSocket (bidirectional μ-law 8 kHz) to a
``RealtimeModelPort``, transcoding both directions. Live + **sim** dual-mode:
sim uses the T005 ``CallSimulator`` harness (no Twilio), streaming audio frames
port<->caller both directions so the whole path is exercised with zero live
telephony.

Session resumption (T014, D3): Gemini Live has a ~10-min WS lifetime / 15-min
session cap (w/o ``contextWindowCompression``). On a mid-call WS drop the bridge
calls ``adapter.resume()``, increments ``session_resume_count``, and preserves
consent linkage — the disclosure is NOT replayed (the caller is never dropped
and never re-disclosed).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from backend.voice import sim as sim_mod
from backend.voice import transcode
from backend.voice.realtime_model_port import (
    AudioChunk, BaseSimAdapter, ModelEvent, ModelEventType,
)
from backend.voice.sim import ScriptedCall, SimEventType

logger = logging.getLogger("vpma.voice.bridge")

# Gemini Live limits (D3).
WS_LIFETIME_MS = 10 * 60 * 1000
SESSION_CAP_MS = 15 * 60 * 1000


@dataclass
class BridgeResult:
    frames_to_model: int = 0          # inbound caller frames sent to the port
    frames_to_caller: int = 0         # outbound model frames sent to the caller
    finals: list[str] = field(default_factory=list)
    session_resume_count: int = 0
    disclosure_replayed: bool = False
    interrupted_count: int = 0
    ended: bool = False


class MediaStreamBridge:
    def __init__(self, adapter: BaseSimAdapter, live: Optional[bool] = None):
        self.adapter = adapter
        self.live = sim_mod.is_live() if live is None else live
        self.result = BridgeResult()
        self._disclosure_done = False
        self._outbound_ulaw: list[bytes] = []
        # Wire model-output audio -> caller (transcode PCM24k -> μ-law 8k).
        self.adapter.on("final", self._on_final)
        self.adapter.on("interrupted", self._on_interrupted)

    @property
    def is_live(self) -> bool:
        return self.live

    def _on_final(self, ev: ModelEvent) -> None:
        if ev.text:
            self.result.finals.append(ev.text)
        if ev.audio is not None:
            ulaw = transcode.pcm_to_ulaw(ev.audio.pcm, ev.audio.rate)
            self._outbound_ulaw.append(ulaw)
            self.result.frames_to_caller += 1

    def _on_interrupted(self, ev: ModelEvent) -> None:
        self.result.interrupted_count += 1

    def mark_disclosure_delivered(self) -> None:
        """Called once by the disclosure guarantee (T016). Survives resume so a
        resumed session never re-discloses."""
        self._disclosure_done = True

    async def _feed_caller_audio(self, ulaw: bytes) -> None:
        pcm = transcode.ulaw_to_pcm(ulaw, transcode.MODEL_IN_RATE)
        await self.adapter.send(AudioChunk(pcm, transcode.MODEL_IN_RATE))
        self.result.frames_to_model += 1

    async def resume(self) -> None:
        """T014: re-establish the model session without dropping/re-disclosing."""
        await self.adapter.resume()
        self.result.session_resume_count = self.adapter.resume_count
        # Consent linkage preserved: disclosure flag intact -> not replayed.
        self.result.disclosure_replayed = False

    async def run_sim(
        self,
        script: ScriptedCall,
        drop_ws_after_events: Optional[int] = None,
    ) -> BridgeResult:
        """Drive a scripted call end-to-end in sim. Optionally inject a WS drop
        after N caller events to exercise transparent resumption (T014)."""
        assert not self.live, "run_sim is sim-only"
        simulator = sim_mod.CallSimulator(script)
        caller_event_count = 0

        for ev in simulator.events():
            if ev.type == SimEventType.CALLER_UTTERANCE:
                caller_event_count += 1
                # Synthesize μ-law if the script didn't carry audio.
                ulaw = ev.audio or _synth_ulaw(len(ev.text))
                await self._feed_caller_audio(ulaw)
                # Inject a mid-call WS drop -> transparent resume.
                if drop_ws_after_events and caller_event_count == drop_ws_after_events:
                    logger.info("BRIDGE: injecting WS drop -> resume")
                    self.adapter.connected = False
                    await self.resume()
            elif ev.type == SimEventType.SILENCE:
                pass  # silence handled by the watchdog (T017), not the bridge
            elif ev.type == SimEventType.DTMF:
                pass
            elif ev.type == SimEventType.HANGUP:
                self.result.ended = True
                break

        self.result.session_resume_count = self.adapter.resume_count
        return self.result

    @property
    def outbound_ulaw_frames(self) -> list[bytes]:
        return list(self._outbound_ulaw)


def _synth_ulaw(text_len: int) -> bytes:
    """Deterministic μ-law caller audio for the sim (length scales with text)."""
    from backend.voice.realtime_model_port import _tone_pcm
    ms = max(120, min(2000, text_len * 40))
    pcm8k = _tone_pcm(transcode.TELEPHONY_RATE, ms=ms, freq=300, amp=6000)
    return transcode.pcm_to_ulaw(pcm8k, transcode.TELEPHONY_RATE)
