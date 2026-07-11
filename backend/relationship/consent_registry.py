"""Feature 011 — T023 consent/opt-out registry (contract I2). Upgrades the 010
``shims/consent_shim.py`` (T008) into a real, revocable, audited registry.

Writes the current ``contact_consent`` state (one row per ``(party_id, channel)``,
via the repo's UNIQUE upsert) **and** an append-only ``consent_event``
(revocable + reversible audit trail, FR-021). Opt-out suppresses Vera-initiated
**outbound only** on the covered channel — it never gates inbound service.
Current state is staff-visible (FR-024).

The ``ConsentDecision`` shape is preserved EXACTLY from ``consent_shim.py`` so
T027 can back the 010 shim with this registry without changing 010's API.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from backend.models import ConsentAction, ConsentEvent, ContactConsent


@dataclass
class ConsentDecision:                       # shape preserved from consent_shim.py (T008)
    allowed: bool
    reason: str = ""
    party_id: Optional[str] = None
    channel: str = "voice"
    purpose: str = ""


class ConsentRegistry:
    def __init__(self, repo, clinic_id: str):
        self.repo = repo
        self.clinic_id = clinic_id

    # ------------------------------------------------------------------ #
    #  consent_check — consulted BEFORE any Vera-initiated outbound (C3)
    # ------------------------------------------------------------------ #
    async def consent_check(self, party_id: str, channel: str,
                            purpose: str = "") -> ConsentDecision:
        row = self.repo.get_consent(party_id, channel)
        if row is not None and not row.get("ai_contact_allowed", True):
            return ConsentDecision(allowed=False, reason="channel_opt_out",
                                   party_id=party_id, channel=channel, purpose=purpose)
        return ConsentDecision(allowed=True, reason="no_opt_out_on_record",
                               party_id=party_id, channel=channel, purpose=purpose)

    # ------------------------------------------------------------------ #
    #  record_opt_out / record_opt_in — current state + append-only event
    # ------------------------------------------------------------------ #
    def record_opt_out(self, party_id: str, channel: str, *, source: str,
                       keyword: Optional[str] = None,
                       inbound_message_id: Optional[str] = None) -> None:
        self._apply(party_id, channel, allowed=False, action=ConsentAction.OPT_OUT,
                    source=source, keyword=keyword, inbound_message_id=inbound_message_id)

    def record_opt_in(self, party_id: str, channel: str, *, source: str) -> None:
        self._apply(party_id, channel, allowed=True, action=ConsentAction.OPT_IN,
                    source=source)

    def _apply(self, party_id, channel, *, allowed, action, source,
               keyword=None, inbound_message_id=None) -> None:
        # (1) current state — one row per (party_id, channel) via UNIQUE upsert
        self.repo.upsert_consent(ContactConsent(
            clinic_id=self.clinic_id, party_id=party_id, channel=channel,
            ai_contact_allowed=allowed,
            source=(source if source in ("inbound_stop", "staff", "portal") else "staff"),
            changed_by=source,
        ))
        # (2) append-only audit event (revocable + reversible trail)
        self.repo.append_consent_event(ConsentEvent(
            clinic_id=self.clinic_id, party_id=party_id, channel=channel,
            action=action, keyword=keyword, inbound_message_id=inbound_message_id,
        ))

    # ------------------------------------------------------------------ #
    #  Staff surface helper (FR-024)
    # ------------------------------------------------------------------ #
    def current_state(self, party_id: str, channel: str) -> Optional[dict]:
        return self.repo.get_consent(party_id, channel)
