"""[SHIM upgrade] Feature 010 — T008 consent_check shim (contract A2), backed
by the real 011 ``ConsentRegistry`` (T027).

Consent is first-class in L1: ``route_message`` / ``deliver`` MUST consult a
channel-scoped, TCPA-grade opt-out registry before send — not a ``preferences``
dict convention. An opted-out party returns a DENY ``ConsentDecision``; the
default party returns ALLOW.

**T027 upgrade (``ConsentDecision`` shape preserved):** ``bind_registry`` wires
this shim to an 011 ``ConsentRegistry`` so the channel-scoped ``(party, channel)``
set now reads/writes ``contact_consent`` / ``consent_event`` — an opt-out
recorded via the inbound STOP path is immediately visible through the shim. With
no registry bound the in-memory ``_OPT_OUT`` default (010's fixture) runs
unchanged, so the default party still returns ALLOW and the demo opt-out denies.
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

# T027: an optionally-bound real 011 ConsentRegistry (backs the shim in place).
_BOUND: dict[str, object] = {"registry": None}


def bind_registry(registry: Optional[object]) -> None:
    """Back the shim with a real 011 ``ConsentRegistry`` (or ``None`` to restore
    the in-memory fixture). When bound, all three shim ops delegate to the
    registry's ``contact_consent`` / ``consent_event`` tables."""
    _BOUND["registry"] = registry


def opt_out(party_id: str, channel: str) -> None:
    reg = _BOUND["registry"]
    if reg is not None:
        reg.record_opt_out(party_id, channel, source="staff")
        return
    _OPT_OUT.add((party_id, channel))


def opt_in(party_id: str, channel: str) -> None:
    reg = _BOUND["registry"]
    if reg is not None:
        reg.record_opt_in(party_id, channel, source="staff")
        return
    _OPT_OUT.discard((party_id, channel))


async def consent_check(party_id: str, channel: str, purpose: str = "") -> ConsentDecision:
    """Consult the channel-scoped opt-out registry. Deny if opted out. When a
    real registry is bound the decision comes from ``contact_consent``; the
    returned ``ConsentDecision`` shape is identical either way."""
    reg = _BOUND["registry"]
    if reg is not None:
        d = await reg.consent_check(party_id, channel, purpose)
        # Re-wrap into the shim's ConsentDecision (field-identical) so the
        # exact shape 010 asserts is preserved regardless of backing.
        return ConsentDecision(allowed=d.allowed, reason=d.reason,
                               party_id=d.party_id, channel=d.channel, purpose=d.purpose)
    if (party_id, channel) in _OPT_OUT:
        return ConsentDecision(allowed=False, reason="channel_opt_out",
                               party_id=party_id, channel=channel, purpose=purpose)
    return ConsentDecision(allowed=True, reason="no_opt_out_on_record",
                           party_id=party_id, channel=channel, purpose=purpose)
