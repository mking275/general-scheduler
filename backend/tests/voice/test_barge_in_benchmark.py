"""T038 — barge-in benchmark on 8 kHz call audio (SC-007).

Builds a representative 8 kHz μ-law call-audio set (the wave-1 T019 seam): a
large body of NON-interrupts (backchannels spoken over Vera + true silence) plus
a set of real interruptions. Asserts the false-barge-in rate stays **< 2%** and
detect p95 **< 400 ms** across the set. Sim only — synthesized 8 kHz audio, no
telephony.
"""
import audioop
import math

from backend.voice import transcode
from backend.voice.barge_in import DETECT_BUDGET_MS, BargeInDetector
from backend.voice.realtime_model_port import _tone_pcm


def _p95(vals: list[int]) -> int:
    if not vals:
        return 0
    s = sorted(vals)
    k = (len(s) - 1) * 0.95
    lo, hi = math.floor(k), math.ceil(k)
    if lo == hi:
        return s[int(k)]
    return int(round(s[lo] + (s[hi] - s[lo]) * (k - lo)))


def _ulaw(amp: int, ms: int = 200, freq: int = 300) -> bytes:
    """Synthesize an 8 kHz μ-law frame at a given amplitude (0 ≈ silence)."""
    pcm = _tone_pcm(transcode.TELEPHONY_RATE, ms=ms, freq=freq, amp=amp)
    return transcode.pcm_to_ulaw(pcm, transcode.TELEPHONY_RATE)


def _energy(ulaw: bytes) -> int:
    pcm = transcode.ulaw_to_pcm(ulaw, transcode.TELEPHONY_RATE)
    return audioop.rms(pcm, 2)


# Backchannels that WILL be spoken over Vera (at real speech energy) — these are
# the #1 false-barge risk and must be filtered.
_BACKCHANNELS = ["uh-huh", "mm-hmm", "yeah", "okay", "right", "sure", "got it",
                 "i see", "hmm", "aha", "uh huh", "mhm", "ok", "yep"]

# Real interruptions that SHOULD cut through.
_INTERRUPTS = ["wait, stop", "no that's wrong", "actually hold on",
               "that's not the right day", "emergency my dog collapsed",
               "can you repeat that", "let me stop you there"]


def _build_negative_set(n: int) -> list[dict]:
    """NON-interrupt audio events: backchannels over Vera + silence frames."""
    events = []
    for i in range(n):
        if i % 4 == 3:
            # true silence frame
            ulaw = _ulaw(amp=20, ms=200)
            events.append({"text": "", "energy": _energy(ulaw), "kind": "silence"})
        else:
            bc = _BACKCHANNELS[i % len(_BACKCHANNELS)]
            ulaw = _ulaw(amp=6000, ms=200)               # spoken at real energy
            events.append({"text": bc, "energy": _energy(ulaw), "kind": "backchannel"})
    return events


def test_t038_false_barge_rate_under_2pct_and_p95_under_400ms():
    det = BargeInDetector()
    negatives = _build_negative_set(250)                 # 250 non-interrupts
    positives = [{"text": t, "energy": _energy(_ulaw(8000)), "kind": "interrupt"}
                 for t in _INTERRUPTS * 8]               # 56 real interrupts

    latencies: list[int] = []
    false_bargeins = 0
    for ev in negatives:
        r = det.detect(caller_text=ev["text"], energy=ev["energy"])
        latencies.append(r.detect_latency_ms)
        if r.barge_in:
            false_bargeins += 1                          # a non-interrupt that fired

    true_positive = 0
    for ev in positives:
        r = det.detect(caller_text=ev["text"], energy=ev["energy"])
        latencies.append(r.detect_latency_ms)
        if r.barge_in:
            true_positive += 1

    false_rate = false_bargeins / len(negatives)
    assert false_rate < 0.02, f"false-barge rate {false_rate:.3%} >= 2%"
    assert true_positive == len(positives)               # every real interrupt caught
    assert _p95(latencies) < 400
    assert _p95(latencies) < DETECT_BUDGET_MS


def test_t038_emergency_always_cuts_through_at_any_energy():
    det = BargeInDetector()
    for amp in (20, 2000, 8000):                         # even whispered
        ulaw = _ulaw(amp=amp)
        r = det.detect(caller_text="emergency", energy=_energy(ulaw))
        assert r.barge_in is True and r.cut_through is True
        assert r.detect_latency_ms < 400
