"""Feature 010 — Vera Voice: T012 OpenAIRealtimeAdapter (FALLBACK).

Same ``RealtimeModelPort``, live + sim. Selected by a config swap
(``model_provider_pref: openai_realtime``) — no rewrite. Sim drives an
equivalent scripted turn.
"""
from __future__ import annotations

from backend.voice.realtime_model_port import BaseSimAdapter


class OpenAIRealtimeAdapter(BaseSimAdapter):
    provider = "openai_realtime"
    default_voice = "verse"
    out_rate = 24000            # OpenAI Realtime audio-out is 24 kHz PCM
    model_name = "gpt-realtime"

    async def _live_connect(self, system, tools, voice, locale) -> None:  # pragma: no cover
        from openai import AsyncOpenAI  # type: ignore  # noqa: F401
        raise RuntimeError(
            "openai_realtime live connect is a pilot-activation config swap "
            "(OPENAI_API_KEY + VOICE_LIVE=true); not exercised in sim."
        )


# --- provider selection (config swap) --------------------------------------
def select_adapter(model_provider_pref: str = "gemini_live") -> BaseSimAdapter:
    """Return the adapter chosen by ``clinic_voice_config.model_provider_pref``.

    Gemini Live is primary; ``openai_realtime`` is the fallback — a pure config
    swap behind the port.
    """
    from backend.voice.gemini_live_adapter import GeminiLiveAdapter

    pref = (model_provider_pref or "gemini_live").strip()
    if pref == "openai_realtime":
        return OpenAIRealtimeAdapter()
    return GeminiLiveAdapter()
