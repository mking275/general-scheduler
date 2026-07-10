"""Feature 010 — Vera Voice: L3 realtime streaming tier (VetAgent-owned).

Everything external (Twilio Media Streams, Gemini Live / OpenAI Realtime) runs
in sim/dual-mode mirroring ``backend/sms_gateway.py``'s auto-detect pattern, so
the whole package is testable with zero live telephony / LLM-audio calls.
Live-mode is a config swap (``VOICE_LIVE=true`` + credentials).
"""
