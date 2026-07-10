"""[SHIM — extract post-pilot] Feature 010 — T008 consent_check shim
(contract A2).

Consent is first-class in L1: ``route_message`` / ``deliver`` MUST consult a
channel-scoped, TCPA-grade opt-out registry before send — not a ``preferences``
dict convention. An opted-out party returns a DENY ``ConsentDecision``; the
default party returns ALLOW. Extracted to core L1 post-pilot.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class ConsentDecision:
    allowed: bool
    reason: str = ""
    party_id: Optional[str] = None
    channel: str = "voice"
    purpose: str = ""


# Channel-scoped opt-out registry: (party_id, channel) -> opted out.
_OPT_OUT: set[tuple[str, str]] = {
    ("party-optout-demo", "voice"),
    ("party-optout-demo", "sms"),
}


def opt_out(party_id: str, channel: str) -> None:
    _OPT_OUT.add((party_id, channel))


def opt_in(party_id: str, channel: str) -> None:
    _OPT_OUT.discard((party_id, channel))


async def consent_check(party_id: str, channel: str, purpose: str = "") -> ConsentDecision:
    """Consult the channel-scoped opt-out registry. Deny if opted out."""
    if (party_id, channel) in _OPT_OUT:
        return ConsentDecision(allowed=False, reason="channel_opt_out",
                               party_id=party_id, channel=channel, purpose=purpose)
    return ConsentDecision(allowed=True, reason="no_opt_out_on_record",
                           party_id=party_id, channel=channel, purpose=purpose)
