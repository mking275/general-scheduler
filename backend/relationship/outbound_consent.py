"""Feature 011 — T025 outbound suppression enforcement + inbound-served
disclosure wiring.

Two halves of FR-022/023 / SC-002:

* **Outbound suppression** — ``OutboundConsentGate.send`` consults
  ``consent_check`` BEFORE any Vera-initiated outbound (reusing the
  ``sms_gateway`` outbound leg). A recorded opt-out suppresses 100% of outbound
  on the covered channel; the gateway send leg is never reached for a suppressed
  message.

* **Inbound-served disclosure** — an opted-out client who INITIATES inbound is
  still served (consent governs contact, not service on request, FR-023). The
  served interaction MUST **emit/persist a ``consent_record`` disclosure via
  010's existing T033 path** (``TranscriptLogger.finalize_transcript`` →
  ``call_transcript.consent_record`` = disclosure text + timestamp), not merely
  assert it (M6).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from backend.voice.adapter_guarantees import TranscriptLogger, now_iso


@dataclass
class OutboundResult:
    sent: bool
    suppressed: bool
    reason: str = ""
    receipt: Any = None


class OutboundConsentGate:
    """Guards the Vera-initiated outbound leg with a consent pre-check."""

    def __init__(self, consent_registry, gateway):
        self.consent = consent_registry
        self.gateway = gateway          # e.g. backend.sms_gateway.SMSGateway

    async def send(self, party_id: str, to: str, body: str, *,
                   channel: str = "sms", purpose: str = "") -> OutboundResult:
        decision = await self.consent.consent_check(party_id, channel, purpose)
        if not decision.allowed:
            # Suppressed — the gateway send leg is NEVER reached (SC-002 = 100%).
            return OutboundResult(sent=False, suppressed=True, reason=decision.reason)
        receipt = self.gateway.send_sms(to=to, body=body)
        return OutboundResult(sent=True, suppressed=False, receipt=receipt)


def serve_inbound_with_disclosure(voice_repo, call_session, *, full_text: str = "",
                                  disclosure_text: Optional[str] = None,
                                  vendor_attestation: Optional[str] = None) -> dict:
    """An opted-out inbound caller is still served — persist the AI + recording
    disclosure via 010's T033 ``consent_record`` path (disclosure text + ts).
    Returns the persisted ``call_transcript`` row."""
    if getattr(call_session, "consent_recorded_at", None) is None:
        call_session.consent_recorded_at = now_iso()
        # reflect the disclosure time on the session row if it is persisted
        try:
            voice_repo.update_call_session(call_session.id,
                                           consent_recorded_at=call_session.consent_recorded_at)
        except Exception:
            pass
    logger = TranscriptLogger(voice_repo)
    return logger.finalize_transcript(
        call_session, full_text=full_text, disclosure_text=disclosure_text,
        vendor_attestation=vendor_attestation,
    )
