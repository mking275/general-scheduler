"""VetAgent voice-bridge service entrypoint (PILOT-INFRA, W7).

A standalone FastAPI/ASGI app that hosts ONLY the realtime voice surface, so it
can run as its own Cloud Run service (min-instances 1, long-lived websockets)
separate from the stateless api. This is **wiring only** — it mounts the
existing Feature-010 voice bridge (``MediaStreamBridge`` + ``BaseSimAdapter``)
onto a Twilio Media Streams websocket and exposes a health endpoint carrying the
build's git SHA (deploy provenance, Pattern #4). No new product logic lives here:
triage/autonomy/watchdog behaviour stays in ``backend/voice/*``; this module only
terminates the socket, frames Twilio's JSON envelope, and drives the bridge.

Run:  uvicorn backend.voice_bridge_main:app --host 0.0.0.0 --port 8080
"""
from __future__ import annotations

import base64
import json
import logging
import os

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from backend.voice import sim as _sim
from backend.voice.media_stream_bridge import MediaStreamBridge
from backend.voice.realtime_model_port import BaseSimAdapter

logger = logging.getLogger("vpma.voice.bridge_service")

# Deploy provenance (Pattern #4): baked at build (GIT_SHA build arg -> env).
GIT_SHA = os.environ.get("GIT_SHA", "unknown")

app = FastAPI(title="VetAgent — Voice Bridge")


# Cloud Run reserves /healthz at the edge (see backend/main.py) — production
# probes the /api/healthz alias.
@app.get("/api/healthz")
@app.get("/healthz")
def healthz():
    """Liveness + deploy-provenance probe. Must return 200 with no external
    dependency (no model connect, no DB) — the socket surface is exercised
    separately by Twilio. ``live`` reports whether the bridge would use real
    telephony/model credentials (``VOICE_LIVE`` / TWILIO_* / model keys) or the
    sim path."""
    return {
        "status": "ok",
        "service": "vetagent-voice-bridge",
        "git_sha": GIT_SHA,
        "live": _sim.is_live(),
    }


def _new_bridge() -> tuple[BaseSimAdapter, MediaStreamBridge]:
    """Construct a per-connection adapter + bridge. The concrete provider
    (Gemini Live primary / OpenAI Realtime fallback) is a config swap at
    pilot-activation; in sim this is the shared ``BaseSimAdapter``."""
    adapter = BaseSimAdapter()
    bridge = MediaStreamBridge(adapter, live=_sim.is_live())
    return adapter, bridge


@app.websocket("/twilio/media-stream")
async def media_stream(ws: WebSocket) -> None:
    """Terminate a Twilio Media Streams websocket and bridge it to the realtime
    model port.

    Twilio's envelope is newline-free JSON text frames with an ``event`` field:
    ``connected`` -> ``start`` -> many ``media`` -> ``stop``. A **graceful**
    hangup delivers ``stop``; a **dropped** call delivers no ``stop`` — the TCP
    socket simply closes and the server sees ``WebSocketDisconnect``. This
    handler treats that abrupt close as the honest failure case and guarantees
    the server unwinds without corrupting bridge/session state.

    Reconnect / resume authority (C3 watchdog, T014 transparent resumption) is
    client/Twilio-side: Twilio re-dials on a dropped call and the model session
    is re-established via ``adapter.resume()`` **without** replaying the
    disclosure. This handler exposes those seams (``bridge.resume``) but does not
    own the reconnect decision — it owns only surviving the drop cleanly.
    """
    await ws.accept()
    adapter, bridge = _new_bridge()
    await adapter.connect(system="Vera voice pilot (bridge service)", tools=[])
    session = {"stream_sid": None, "frames_in": 0, "clean_close": False}
    try:
        while True:
            msg = json.loads(await ws.receive_text())
            event = msg.get("event")
            if event == "connected":
                continue
            if event == "start":
                start = msg.get("start") or {}
                session["stream_sid"] = msg.get("streamSid") or start.get("streamSid")
            elif event == "media":
                ulaw = base64.b64decode(msg["media"]["payload"])
                await bridge._feed_caller_audio(ulaw)  # transcode + drive model
                session["frames_in"] += 1
                # Drain any model-produced audio back to the caller.
                out_frames = bridge.outbound_ulaw_frames
                if out_frames:
                    for out in out_frames:
                        await ws.send_text(json.dumps({
                            "event": "media",
                            "streamSid": session["stream_sid"],
                            "media": {"payload": base64.b64encode(out).decode("ascii")},
                        }))
                    bridge._outbound_ulaw.clear()
            elif event == "stop":
                bridge.result.ended = True
                session["clean_close"] = True
                break
    except WebSocketDisconnect:
        # Abrupt drop (no `stop`). Bridge state (resume_count, disclosure flag,
        # frame counters) stays intact and consistent for the audit spine; on a
        # Twilio reconnect the resume seam continues the same session.
        logger.warning(
            "voice-bridge: websocket dropped abruptly (stream_sid=%s frames_in=%d) "
            "-> server survives; resume authority is client-side",
            session["stream_sid"], session["frames_in"],
        )
    finally:
        # Honest cleanup: no partial writes, no state mutation beyond the result
        # already recorded. Session facts remain queryable for the escalation /
        # reveal audit even on an abrupt drop.
        logger.info(
            "voice-bridge: connection closed (stream_sid=%s frames_in=%d clean=%s ended=%s)",
            session["stream_sid"], session["frames_in"], session["clean_close"], bridge.result.ended,
        )
