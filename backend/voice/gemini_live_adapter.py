"""Feature 010 — Vera Voice: T011 GeminiLiveAdapter (PRIMARY).

Gemini 3.1 Flash Live (native speech-to-speech). Live + sim dual-mode behind
the ``RealtimeModelPort``. Sim mode emits scripted partial/final/tool_call/
interrupted events with zero live API calls; ``is_live()`` gates the real
connect. Selected by default (``model_provider_pref: gemini_live``).
"""
from __future__ import annotations

from backend.voice.realtime_model_port import BaseSimAdapter

from backend.model_config import GEMINI_LIVE


class GeminiLiveAdapter(BaseSimAdapter):
    provider = "gemini_live"
    default_voice = "vera-en-us"
    out_rate = 24000            # Gemini Live audio-out is 24 kHz PCM
    model_name = GEMINI_LIVE

    async def _live_connect(self, system, tools, voice, locale) -> None:  # pragma: no cover
        # Pilot-activation only: real google-genai Live session. Import is
        # deferred so sim runs without the SDK / any network.
        from google import genai  # type: ignore  # noqa: F401
        raise RuntimeError(
            "gemini_live live connect is a pilot-activation config swap "
            "(GEMINI_API_KEY + VOICE_LIVE=true); not exercised in sim."
        )
