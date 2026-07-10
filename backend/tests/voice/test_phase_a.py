"""Phase A (Bridge + Model Port) verification — T009..T014."""
import pytest

from backend.voice import transcode
from backend.voice.realtime_model_port import (
    AudioChunk, ModelEvent, ModelEventType, RealtimeModelPort, Tool, _tone_pcm,
)


# --- T009: transcode round-trip --------------------------------------------
def test_t009_ulaw_pcm_roundtrip_amplitude():
    # 8 kHz μ-law source tone.
    pcm8k = _tone_pcm(transcode.TELEPHONY_RATE, ms=500, freq=440, amp=8000)
    ulaw_in = transcode.pcm_to_ulaw(pcm8k, transcode.TELEPHONY_RATE)
    # Round trip: μ-law 8k -> PCM 16k -> μ-law 8k
    pcm16k = transcode.ulaw_to_pcm(ulaw_in, transcode.MODEL_IN_RATE)
    assert transcode.rms(pcm16k) > 0
    ulaw_out = transcode.pcm_to_ulaw(pcm16k, transcode.MODEL_IN_RATE)
    # Compare amplitude of the decoded input vs decoded output (both at 8k).
    r_in = transcode.rms(transcode.ulaw_to_pcm(ulaw_in, transcode.TELEPHONY_RATE))
    r_out = transcode.rms(transcode.ulaw_to_pcm(ulaw_out, transcode.TELEPHONY_RATE))
    # Within amplitude tolerance (μ-law + resample is lossy but bounded).
    assert abs(r_in - r_out) / max(1, r_in) < 0.15


# --- T010: port protocol ---------------------------------------------------
def test_t010_adapters_satisfy_port():
    from backend.voice.gemini_live_adapter import GeminiLiveAdapter
    from backend.voice.openai_realtime_adapter import OpenAIRealtimeAdapter
    assert isinstance(GeminiLiveAdapter(), RealtimeModelPort)
    assert isinstance(OpenAIRealtimeAdapter(), RealtimeModelPort)


# --- T011: Gemini sim turn --------------------------------------------------
async def test_t011_gemini_sim_full_turn_no_live_call():
    from backend.voice.gemini_live_adapter import GeminiLiveAdapter
    a = GeminiLiveAdapter()
    finals, tools, interrupts = [], [], []
    a.on("final", lambda ev: finals.append(ev.text))
    a.on("tool_call", lambda ev: tools.append(ev.tool))
    a.on("interrupted", lambda ev: interrupts.append(ev))
    a.queue_reply("You're booked for tomorrow at 2pm.",
                  with_tool={"name": "book", "args": {"slot": "t2"}})
    await a.connect(system="disclosure+persona", tools=[Tool("book")])
    await a.send(AudioChunk(_tone_pcm(16000, 100), 16000))
    assert finals == ["You're booked for tomorrow at 2pm."]
    assert tools and tools[0]["name"] == "book"
    assert a.live_connect_called is False
    await a.interrupt()
    assert len(interrupts) == 1


# --- T012: OpenAI selected by config swap ----------------------------------
async def test_t012_openai_selected_by_pref():
    from backend.voice.openai_realtime_adapter import OpenAIRealtimeAdapter, select_adapter
    a = select_adapter("openai_realtime")
    assert isinstance(a, OpenAIRealtimeAdapter)
    assert a.provider == "openai_realtime"
    finals = []
    a.on("final", lambda ev: finals.append(ev.text))
    a.queue_reply("Equivalent turn on the fallback.")
    await a.connect(system="s", tools=[])
    await a.send("caller audio")
    assert finals == ["Equivalent turn on the fallback."]
    # default remains gemini
    from backend.voice.gemini_live_adapter import GeminiLiveAdapter
    assert isinstance(select_adapter("gemini_live"), GeminiLiveAdapter)


# --- T013: sim bridge streams both directions ------------------------------
async def test_t013_sim_bridge_bidirectional(monkeypatch):
    monkeypatch.setenv("VOICE_LIVE", "false")
    from backend.voice.gemini_live_adapter import GeminiLiveAdapter
    from backend.voice.media_stream_bridge import MediaStreamBridge
    from backend.voice.sim import demo_script

    adapter = GeminiLiveAdapter()
    await adapter.connect(system="s", tools=[])
    bridge = MediaStreamBridge(adapter)
    assert bridge.is_live is False           # dual-mode flag honored
    res = await bridge.run_sim(demo_script())
    assert res.frames_to_model > 0           # caller -> port
    assert res.frames_to_caller > 0          # port -> caller
    assert res.ended is True
    assert bridge.outbound_ulaw_frames        # real μ-law bytes produced


# --- T014: transparent session resumption ----------------------------------
async def test_t014_ws_drop_resumes_without_redisclose(monkeypatch):
    monkeypatch.setenv("VOICE_LIVE", "false")
    from backend.voice.gemini_live_adapter import GeminiLiveAdapter
    from backend.voice.media_stream_bridge import MediaStreamBridge
    from backend.voice.sim import demo_script

    adapter = GeminiLiveAdapter()
    await adapter.connect(system="s", tools=[])
    bridge = MediaStreamBridge(adapter)
    bridge.mark_disclosure_delivered()       # disclosure already played (turn 1)
    res = await bridge.run_sim(demo_script(), drop_ws_after_events=1)
    assert res.session_resume_count >= 1     # resume happened
    assert bridge._disclosure_done is True    # consent linkage preserved
    assert res.disclosure_replayed is False   # NOT re-disclosed
    assert res.ended is True                  # caller never dropped
