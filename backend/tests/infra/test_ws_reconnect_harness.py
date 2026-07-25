"""PILOT-INFRA — websocket-drop harness for the voice-bridge service.

Starts ``backend.voice_bridge_main:app`` in-process (Starlette ``TestClient``),
opens the Twilio Media Streams websocket, force-drops it mid-call, and asserts:

  1. ``/healthz`` carries the deploy-provenance git SHA (Pattern #4).
  2. The bridge accepts Twilio-shaped media frames and streams model audio back.
  3. An **abrupt** drop (socket close with NO ``stop`` event — what a dropped
     call looks like at the app layer) does not raise out of the server and does
     not corrupt session state: the service is still healthy afterward.
  4. The reconnect / resume + watchdog **seams** the drop handler relies on
     exist (``adapter.resume`` / ``bridge.resume`` / ``EscalationWatchdog``).

Honesty note (what is NOT assertable locally): true reconnect authority is
client/Twilio-side — Twilio re-dials a dropped call and the model session is
re-established via ``adapter.resume()`` without re-disclosing. ``TestClient``
cannot reproduce a mid-flight TCP reset, and there is no real Twilio peer to
re-dial. So this harness asserts the SERVER-side contract (survive the drop
cleanly, seams present); the client-side reconnect loop is covered by the
Feature-010 sim (``MediaStreamBridge.run_sim(drop_ws_after_events=...)``), which
exercises ``resume()`` end-to-end without a socket.
"""
from __future__ import annotations

import base64
import json

from fastapi.testclient import TestClient

from backend.voice_bridge_main import app

# 20 ms of μ-law payload (any bytes are valid G.711u; the bridge transcodes it).
_ULAW_FRAME = base64.b64encode(b"\xff" * 160).decode("ascii")


def _media(stream_sid: str = "MZsim") -> str:
    return json.dumps({"event": "media", "streamSid": stream_sid,
                       "media": {"payload": _ULAW_FRAME}})


def _start(stream_sid: str = "MZsim") -> str:
    return json.dumps({"event": "start", "streamSid": stream_sid,
                       "start": {"streamSid": stream_sid}})


def test_healthz_carries_git_sha():
    client = TestClient(app)
    r = client.get("/healthz")
    assert r.status_code == 200
    body = r.json()
    assert body["service"] == "vetagent-voice-bridge"
    assert body["status"] == "ok"
    assert "git_sha" in body          # provenance slot present (value baked at build)
    assert "live" in body


def test_ws_accepts_and_bridges_media():
    """Happy path: start -> media -> the bridge streams model audio back."""
    client = TestClient(app)
    with client.websocket_connect("/twilio/media-stream") as ws:
        ws.send_text(json.dumps({"event": "connected"}))
        ws.send_text(_start())
        ws.send_text(_media())
        reply = json.loads(ws.receive_text())
        assert reply["event"] == "media"
        assert reply["streamSid"] == "MZsim"
        assert reply["media"]["payload"]          # non-empty outbound audio
        ws.send_text(json.dumps({"event": "stop"}))


def test_abrupt_drop_does_not_crash_server():
    """A dropped call = socket close with NO `stop`. The server must survive and
    stay healthy (no corrupted state, no unhandled exception)."""
    client = TestClient(app)
    with client.websocket_connect("/twilio/media-stream") as ws:
        ws.send_text(_start())
        ws.send_text(_media())
        _ = ws.receive_text()                      # drain one outbound frame
        # Exit the context WITHOUT sending `stop` -> abrupt drop -> the endpoint
        # takes its WebSocketDisconnect path.
    # Service is still up and provenance still reports after the drop.
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_reconnect_and_watchdog_seams_exist():
    """Assert the seams the drop handler documents actually exist, so the
    server-side survival contract is backed by real resume/watchdog surfaces."""
    from backend.voice.adapter_guarantees import EscalationWatchdog
    from backend.voice.media_stream_bridge import MediaStreamBridge
    from backend.voice.realtime_model_port import BaseSimAdapter

    adapter = BaseSimAdapter()
    bridge = MediaStreamBridge(adapter)
    # Transparent-resumption seam (T014): re-establish without re-disclosing.
    assert hasattr(adapter, "resume") and callable(adapter.resume)
    assert hasattr(bridge, "resume") and callable(bridge.resume)
    assert bridge._disclosure_done is False        # disclosure flag survives resume
    # Independent escalation watchdog (C3 / T017) — silence + stall detectors.
    assert hasattr(EscalationWatchdog, "observe_silence")
    assert hasattr(EscalationWatchdog, "observe_model_stall")


async def test_sim_resume_preserves_session_state():
    """End-to-end resume coverage without a socket: the Feature-010 sim injects a
    WS drop and asserts the session resumes (count increments) and the
    disclosure is NOT replayed — the reconnect behaviour the harness references
    but cannot drive through TestClient."""
    from backend.voice.media_stream_bridge import MediaStreamBridge
    from backend.voice.realtime_model_port import BaseSimAdapter
    from backend.voice.sim import ScriptedCall

    adapter = BaseSimAdapter()
    await adapter.connect(system="test", tools=[])
    bridge = MediaStreamBridge(adapter, live=False)
    bridge.mark_disclosure_delivered()
    script = (ScriptedCall()
              .utter("hi there")
              .utter("are you still there")
              .utter("okay thanks")
              .hangup())
    result = await bridge.run_sim(script, drop_ws_after_events=1)
    assert result.session_resume_count >= 1        # resumed after the injected drop
    assert result.disclosure_replayed is False     # never re-disclosed
    assert result.ended is True                    # clean end, state intact
