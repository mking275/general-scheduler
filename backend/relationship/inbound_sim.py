"""Feature 011 — T006 inbound dual-mode resolver + simulator.

``sms_gateway.py`` is OUTBOUND-only. This is the greenfield INBOUND seam a live
Twilio inbound webhook will slot behind (Pilot-Activation, config swap — no code
change). It mirrors ``SMSGateway``'s auto-detect exactly: an ``INBOUND_LIVE``
force flag, else credential presence decides live vs. sim. In sim-mode a test
harness posts scripted ``InboundMessage``s through the same seam with **zero
network / telephony**.

Env:
  INBOUND_LIVE          "true" to force live, "false" to force sim
                        (default: auto-detect on Twilio credential presence)
  TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN / TWILIO_FROM_NUMBER
"""
from __future__ import annotations

import logging
import os
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

Handler = Callable[[Any], Any]


class InboundSimulator:
    def __init__(self, handler: Optional[Handler] = None):
        self._account_sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
        self._auth_token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
        self._from_number = os.getenv("TWILIO_FROM_NUMBER", "").strip()
        self._force = os.getenv("INBOUND_LIVE", "").strip().lower()
        self._live = self._resolve_mode()
        self._handler: Optional[Handler] = handler
        self.received: list[Any] = []   # sim capture — every posted message

        if self._live:
            logger.info("InboundSimulator: LIVE mode — real webhook expected.")
        else:
            logger.warning(
                "InboundSimulator: SIMULATION mode active — no live webhook is "
                "registered; scripted InboundMessages post through the seam with "
                "no network call. Set INBOUND_LIVE=true + Twilio creds to go live."
            )

    # ------------------------------------------------------------------ #
    #  Mode resolution (mirrors SMSGateway._resolve_mode)
    # ------------------------------------------------------------------ #
    def _resolve_mode(self) -> bool:
        if self._force == "false":
            return False
        if self._force == "true":
            return True
        return bool(self._account_sid and self._auth_token and self._from_number)

    def is_live(self) -> bool:
        """True iff a real inbound webhook path is active. False = sim."""
        return self._live

    # ------------------------------------------------------------------ #
    #  The seam
    # ------------------------------------------------------------------ #
    def register_handler(self, handler: Handler) -> None:
        """Register the intake handler (T022 ``inbound_gateway.handle_inbound``)
        the live webhook will also call."""
        self._handler = handler

    def post(self, message: Any) -> Any:
        """Post an inbound message through the intake seam.

        In sim-mode this is a pure in-process call — the identical seam a live
        Twilio inbound webhook hits, with no network. Returns whatever the
        registered handler returns (or the message itself if none)."""
        self.received.append(message)
        if self._handler is not None:
            return self._handler(message)
        return message
