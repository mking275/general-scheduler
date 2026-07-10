"""Feature 010 — Vera Voice: T010 RealtimeModelPort (contract B1).

Provider-agnostic port so the Gemini Live primary and the OpenAI Realtime
fallback are a **config swap, not a rewrite**. Both adapters (T011/T012)
satisfy this Protocol.

``BaseSimAdapter`` implements the port entirely in SIMULATION — it emits
scripted ``partial``/``final``/``tool_call``/``interrupted`` events with zero
live API calls. The concrete adapters subclass it and gate real ``connect`` on
``sim.is_live()``.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Literal, Optional, Protocol, runtime_checkable

logger = logging.getLogger("vpma.voice.port")

ModelEventName = Literal["partial", "final", "tool_call", "error", "interrupted"]


@dataclass
class AudioChunk:
    pcm: bytes
    rate: int


@dataclass
class Tool:
    name: str
    description: str = ""
    parameters: dict = field(default_factory=dict)


class ModelEventType(str, Enum):
    PARTIAL = "partial"
    FINAL = "final"
    TOOL_CALL = "tool_call"
    ERROR = "error"
    INTERRUPTED = "interrupted"


@dataclass
class ModelEvent:
    type: ModelEventType
    text: str = ""
    tool: Optional[dict] = None
    audio: Optional[AudioChunk] = None
    meta: dict = field(default_factory=dict)


@runtime_checkable
class RealtimeModelPort(Protocol):
    async def connect(self, system: str, tools: list[Tool], voice: str, locale: str) -> None: ...
    async def send(self, chunk: "AudioChunk | str") -> None: ...
    def on(self, event: ModelEventName, cb: Callable[[ModelEvent], Any]) -> None: ...
    async def interrupt(self) -> None: ...
    async def resume(self) -> None: ...


def _tone_pcm(rate: int, ms: int = 200, freq: int = 440, amp: int = 8000) -> bytes:
    """Deterministic PCM16 tone standing in for synthesized speech audio."""
    import math
    import struct
    n = int(rate * ms / 1000)
    return b"".join(struct.pack("<h", int(amp * math.sin(2 * math.pi * freq * i / rate)))
                    for i in range(n))


class BaseSimAdapter:
    """Sim-mode implementation of RealtimeModelPort shared by both providers."""

    provider: str = "sim"
    default_voice: str = "vera-en-us"
    out_rate: int = 24000

    def __init__(self) -> None:
        self._cbs: dict[str, list[Callable[[ModelEvent], Any]]] = {}
        self._sim_queue: list[ModelEvent] = []
        self.connected = False
        self.connect_attempts = 0
        self.live_connect_called = False
        self.resume_count = 0
        self._system = ""
        self._tools: list[Tool] = []

    # --- port surface ----------------------------------------------------
    def on(self, event: ModelEventName, cb: Callable[[ModelEvent], Any]) -> None:
        self._cbs.setdefault(event, []).append(cb)

    async def _emit(self, ev: ModelEvent) -> None:
        for cb in self._cbs.get(ev.type.value, []):
            res = cb(ev)
            if hasattr(res, "__await__"):
                await res

    async def connect(self, system: str, tools: list[Tool], voice: str = "",
                       locale: str = "en-US") -> None:
        self.connect_attempts += 1
        self._system = system
        self._tools = tools or []
        from backend.voice import sim as _sim
        if _sim.is_live():
            # Live path — real provider connect. Not exercised by tests.
            self.live_connect_called = True
            await self._live_connect(system, tools, voice or self.default_voice, locale)
        self.connected = True

    async def _live_connect(self, system, tools, voice, locale) -> None:  # pragma: no cover
        raise RuntimeError(
            f"{self.provider}: live connect requires credentials + VOICE_LIVE=true "
            "(pilot-activation config swap; not exercised in sim)."
        )

    async def send(self, chunk: "AudioChunk | str") -> None:
        if not self.connected:
            raise RuntimeError("send() before connect()")
        # In sim, a caller input drives the queued scripted model response.
        await self._drive_scripted_response(chunk)

    async def interrupt(self) -> None:
        await self._emit(ModelEvent(ModelEventType.INTERRUPTED))

    async def resume(self) -> None:
        """Transparent session resumption — re-establish without re-disclosing."""
        self.resume_count += 1
        self.connected = True
        logger.info("%s: session resumed (count=%d)", self.provider, self.resume_count)

    # --- sim scripting ---------------------------------------------------
    def queue_sim_events(self, events: list[ModelEvent]) -> None:
        self._sim_queue.extend(events)

    def queue_reply(self, text: str, with_tool: Optional[dict] = None) -> None:
        """Convenience: script a partial->final reply (+ optional tool_call)."""
        self._sim_queue.append(ModelEvent(ModelEventType.PARTIAL, text=text[: max(1, len(text) // 2)]))
        if with_tool:
            self._sim_queue.append(ModelEvent(ModelEventType.TOOL_CALL, tool=with_tool))
        self._sim_queue.append(ModelEvent(
            ModelEventType.FINAL, text=text,
            audio=AudioChunk(_tone_pcm(self.out_rate), self.out_rate),
        ))

    async def _drive_scripted_response(self, chunk) -> None:
        if not self._sim_queue:
            # Default: echo a short final so the bridge always has audio-out.
            self._sim_queue.append(ModelEvent(
                ModelEventType.FINAL, text="",
                audio=AudioChunk(_tone_pcm(self.out_rate, ms=120), self.out_rate),
            ))
        # Emit exactly one scripted turn (up to and including the next FINAL).
        while self._sim_queue:
            ev = self._sim_queue.pop(0)
            await self._emit(ev)
            if ev.type == ModelEventType.FINAL:
                break
