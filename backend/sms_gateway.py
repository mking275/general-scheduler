"""
SMS / Email gateway for VPMA.
Wraps Twilio (SMS) and can be extended to SendGrid (email).

Behaviour:
  - If TWILIO_ACCOUNT_SID + TWILIO_AUTH_TOKEN + TWILIO_FROM_NUMBER are set
    (via env vars or .env file) → real messages are sent via Twilio.
  - Otherwise → falls back to simulation mode with a WARNING log.
    This keeps dev/demo working with zero credentials.

Environment variables (set in .env or system env):
  TWILIO_ACCOUNT_SID   e.g. ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  TWILIO_AUTH_TOKEN    your auth token
  TWILIO_FROM_NUMBER   E.164 format  e.g. +15551234567
  SMS_ENABLED          "true" to force live mode, "false" to force simulation
                       (defaults to auto-detect based on credential presence)

Usage:
  from sms_gateway import SMSGateway
  gw = SMSGateway()
  receipt = gw.send_sms(to="+15559876543", body="Hi, confirm your appt? Reply YES")
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

# Load .env if present (no-op if python-dotenv not installed)
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))
except ImportError:
    pass

logger = logging.getLogger("vpma.sms")


@dataclass
class SMSReceipt:
    dispatch_id: str
    to: str
    body: str
    channel: str = "sms"
    status: str = "delivered"          # delivered | failed | simulated
    provider_sid: str = ""             # Twilio MessageSid if live
    sent_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    error: str = ""
    simulated: bool = False

    def to_dict(self) -> dict:
        return {
            "dispatch_id": self.dispatch_id,
            "to": self.to,
            "channel": self.channel,
            "status": self.status,
            "provider_sid": self.provider_sid,
            "sent_at": self.sent_at,
            "simulated": self.simulated,
            "error": self.error or None,
            # body omitted from dict for privacy — stored in DB separately
        }


class SMSGateway:
    """
    Unified SMS dispatch layer.  Instantiate once at app startup.
    Thread-safe — Twilio client is stateless.
    """

    def __init__(self):
        self._account_sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
        self._auth_token  = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
        self._from_number = os.getenv("TWILIO_FROM_NUMBER", "").strip()
        self._force       = os.getenv("SMS_ENABLED", "").strip().lower()

        self._live = self._resolve_mode()
        self._client = None

        if self._live:
            try:
                from twilio.rest import Client  # type: ignore
                self._client = Client(self._account_sid, self._auth_token)
                logger.info(
                    "SMSGateway: Live Twilio mode — from=%s", self._from_number
                )
            except ImportError:
                logger.error(
                    "SMSGateway: twilio package not installed — falling back to simulation. "
                    "Run: pip install twilio"
                )
                self._live = False
        else:
            logger.warning(
                "SMSGateway: SIMULATION mode active — no SMS credentials found. "
                "Set TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN / TWILIO_FROM_NUMBER in .env to enable live SMS."
            )

    # ------------------------------------------------------------------ #
    #  Public API
    # ------------------------------------------------------------------ #

    @property
    def is_live(self) -> bool:
        """True if real SMS will be sent, False if simulating."""
        return self._live

    def send_sms(self, to: str, body: str) -> SMSReceipt:
        """
        Send an SMS to `to` (E.164 format preferred, e.g. +15551234567).
        Returns an SMSReceipt regardless of mode.
        """
        dispatch_id = str(uuid4())
        to_clean = self._normalise_phone(to)

        if not to_clean:
            return SMSReceipt(
                dispatch_id=dispatch_id,
                to=to or "",
                body=body,
                status="failed",
                error="invalid_phone_number",
                simulated=not self._live,
            )

        if self._live and self._client:
            return self._send_twilio(dispatch_id, to_clean, body)
        else:
            return self._simulate(dispatch_id, to_clean, body)

    def send_reminder(
        self,
        to: str,
        owner_name: str,
        patient_name: str,
        procedure: str,
        appt_date: str,
        appt_time: str,
        clinic_name: str = "your vet",
    ) -> SMSReceipt:
        """
        Convenience method: sends the standard appointment reminder template.
        Reply YES = confirm, NO = reschedule.
        """
        body = (
            f"Hi {owner_name or 'there'} 👋 Reminder from {clinic_name}: "
            f"{patient_name} has a {procedure} appointment on {appt_date} at {appt_time}. "
            f"Reply YES to confirm or NO to reschedule."
        )
        return self.send_sms(to=to, body=body)

    def send_confirmation_ack(self, to: str, patient_name: str, appt_date: str, appt_time: str) -> SMSReceipt:
        """Sends a 'confirmed' acknowledgement back to the owner."""
        body = (
            f"✅ Confirmed! {patient_name}'s appointment on {appt_date} at {appt_time} is all set. "
            f"We'll see you then!"
        )
        return self.send_sms(to=to, body=body)

    def send_intake_link(self, to: str, owner_name: str, patient_name: str, intake_url: str) -> SMSReceipt:
        """Sends the pre-visit intake form link."""
        body = (
            f"Hi {owner_name or 'there'}, please complete {patient_name}'s pre-visit health form "
            f"before your appointment: {intake_url}"
        )
        return self.send_sms(to=to, body=body)

    def send_waitlist_offer(
        self,
        to: str,
        owner_name: str,
        patient_name: str,
        slot_date: str,
        slot_time: str,
        accept_url: str,
        window_minutes: int = 30,
    ) -> SMSReceipt:
        """Sends a waitlist slot-offer notification."""
        body = (
            f"Hi {owner_name or 'there'} — a slot opened up for {patient_name}: "
            f"{slot_date} at {slot_time}. "
            f"Reply YES or visit {accept_url} to claim it (offer expires in {window_minutes} min)."
        )
        return self.send_sms(to=to, body=body)

    # ------------------------------------------------------------------ #
    #  Private helpers
    # ------------------------------------------------------------------ #

    def _resolve_mode(self) -> bool:
        """Determine live vs. simulation mode."""
        if self._force == "false":
            return False
        if self._force == "true":
            return True
        # Auto-detect: all three credentials must be present
        return bool(self._account_sid and self._auth_token and self._from_number)

    def _send_twilio(self, dispatch_id: str, to: str, body: str) -> SMSReceipt:
        """Dispatch via Twilio REST API."""
        try:
            msg = self._client.messages.create(
                body=body,
                from_=self._from_number,
                to=to,
            )
            logger.info("SMSGateway: Sent SMS sid=%s to=%s", msg.sid, to)
            return SMSReceipt(
                dispatch_id=dispatch_id,
                to=to,
                body=body,
                status="delivered",
                provider_sid=msg.sid,
                simulated=False,
            )
        except Exception as exc:
            logger.error("SMSGateway: Twilio send failed: %s", exc)
            return SMSReceipt(
                dispatch_id=dispatch_id,
                to=to,
                body=body,
                status="failed",
                error=str(exc),
                simulated=False,
            )

    def _simulate(self, dispatch_id: str, to: str, body: str) -> SMSReceipt:
        """Log the message content without sending, return simulated receipt."""
        logger.info(
            "SMSGateway [SIMULATED] → %s | %s",
            to,
            body[:80] + ("…" if len(body) > 80 else ""),
        )
        return SMSReceipt(
            dispatch_id=dispatch_id,
            to=to,
            body=body,
            status="delivered",
            simulated=True,
        )

    @staticmethod
    def _normalise_phone(phone: str) -> str:
        """
        Best-effort normalisation to E.164.
        Strips spaces, dashes, parens.  Prepends +1 for 10-digit US numbers.
        Returns empty string if unrecognisable.
        """
        if not phone:
            return ""
        digits = "".join(c for c in phone if c.isdigit())
        if len(digits) == 10:
            return f"+1{digits}"
        if len(digits) == 11 and digits.startswith("1"):
            return f"+{digits}"
        if phone.startswith("+"):
            return phone  # assume already E.164
        return ""  # unrecognisable — caller will get failed receipt


# ── Module-level singleton (created at import time) ───────────────────────
# Import this directly:  from sms_gateway import sms
sms = SMSGateway()
