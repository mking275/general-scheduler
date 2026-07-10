"""Feature 010 — Vera Voice: T009 audio transcode.

Twilio Media Streams carry **μ-law 8 kHz** (G.711u); the realtime models want
linear **PCM 16 kHz** (Gemini Live in) / **24 kHz** (audio out). This bridges
both directions, day-1.

Uses the stdlib ``audioop`` (Python <=3.12); on 3.13+ the ``audioop-lts``
backport provides the same API (see requirements.txt).
"""
from __future__ import annotations

try:
    import audioop  # stdlib through 3.12
except ImportError:  # pragma: no cover - 3.13+ backport
    import audioop_lts as audioop  # type: ignore

TELEPHONY_RATE = 8000       # μ-law 8 kHz on the wire
MODEL_IN_RATE = 16000       # PCM 16 kHz into the model
MODEL_OUT_RATE = 24000      # PCM 24 kHz out of the model
WIDTH = 2                   # 16-bit linear samples
CHANNELS = 1


def ulaw_to_pcm(ulaw: bytes, target_rate: int = MODEL_IN_RATE) -> bytes:
    """μ-law 8 kHz -> linear PCM16 at ``target_rate``."""
    lin8k = audioop.ulaw2lin(ulaw, WIDTH)
    if target_rate == TELEPHONY_RATE:
        return lin8k
    converted, _ = audioop.ratecv(lin8k, WIDTH, CHANNELS, TELEPHONY_RATE, target_rate, None)
    return converted


def pcm_to_ulaw(pcm: bytes, src_rate: int = MODEL_OUT_RATE) -> bytes:
    """Linear PCM16 at ``src_rate`` -> μ-law 8 kHz for the telephony leg."""
    if src_rate != TELEPHONY_RATE:
        down, _ = audioop.ratecv(pcm, WIDTH, CHANNELS, src_rate, TELEPHONY_RATE, None)
    else:
        down = pcm
    return audioop.lin2ulaw(down, WIDTH)


def rms(pcm: bytes) -> int:
    """RMS amplitude of a PCM16 buffer (for round-trip / VAD checks)."""
    if not pcm:
        return 0
    return audioop.rms(pcm, WIDTH)
