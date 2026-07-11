"""Feature 011 — T022 inbound intake seam (contract I1) + T024 STOP→suppression
flow (contract I3).

``sms_gateway.py`` is OUTBOUND-only; this is the **net-new** inbound seam a live
Twilio inbound webhook slots behind (sim/dual-mode over T006). It matches the
config keyword table (``inbound_keywords.<locale>.yaml``, TCPA STOP/START/HELP);
a message that is neither STOP nor a recognized keyword is
``routed_to_staff`` — **never auto-actioned**. Every inbound persists an
append-only ``inbound_message`` (``received_at`` = the SC-006 clock start).

T024 — an inbound **STOP** resolves ``from_identifier`` → party → records the
opt-out (``source="inbound_stop"``) and reflects it in staff consent state
(≤60 s, SC-006). A STOP from an **unresolved multi-match** (shared line) routes
to staff rather than opting out the wrong party (privacy-safe default) — the
resolver's ``is_shared_line`` is the guard.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import yaml

from backend.models import InboundAction, InboundMessage, ResolutionOutcome

# raw config action -> canonical TCPA keyword surfaced on the result
_CANONICAL = {"opt_out": "STOP", "opt_in": "START", "help": "HELP"}


@dataclass
class InboundResult:
    matched_keyword: Optional[str]                 # STOP | START | HELP | None
    action_taken: str                              # I1 action enum
    inbound_message_id: Optional[str] = None
    party_id: Optional[str] = None
    confirmation: str = ""                          # copy sent back to the sender


class InboundGateway:
    def __init__(self, repo, clinic_id: str, resolver=None, consent_registry=None,
                 keyword_path: Optional[str] = None):
        self.repo = repo
        self.clinic_id = clinic_id
        self.resolver = resolver
        self.consent = consent_registry
        cfg = yaml.safe_load(open(keyword_path or _keyword_path())) or {}
        # str(): YAML 1.1 parses bare YES/NO/ON/OFF as booleans — coerce back.
        self.keywords = {str(k).upper(): v for k, v in (cfg.get("keywords") or {}).items()}
        self.responses = cfg.get("responses") or {}

    # ------------------------------------------------------------------ #
    #  I1 — handle_inbound
    # ------------------------------------------------------------------ #
    async def handle_inbound(self, msg: InboundMessage) -> InboundResult:
        action = self.keywords.get((msg.body or "").strip().upper())   # None if no keyword
        canonical = _CANONICAL.get(action) if action else None

        action_taken = InboundAction.NONE
        party_id: Optional[str] = None
        confirmation = ""

        if action in ("opt_out", "opt_in"):
            party_id, resolved = self._resolve_single(msg)
            if resolved and self.consent is not None:
                if action == "opt_out":
                    action_taken = self._do_opt_out(party_id, msg, canonical)
                else:
                    self.consent.record_opt_in(party_id, msg.channel, source="inbound_start")
                    action_taken = InboundAction.OPT_IN_RECORDED
                confirmation = self.responses.get(action, "")
            else:
                # unresolved / shared-line (multi-match): NEVER auto-opt-out the
                # wrong party — hand to staff review.
                action_taken = InboundAction.ROUTED_TO_STAFF
        elif action == "help":
            action_taken = InboundAction.NONE                # informational only
            confirmation = self.responses.get("help", "")
        else:
            # neither STOP nor a recognized keyword -> staff, never auto-actioned
            action_taken = InboundAction.ROUTED_TO_STAFF

        row = self._persist(msg, canonical, action_taken)
        return InboundResult(matched_keyword=canonical, action_taken=action_taken.value,
                             inbound_message_id=row["id"], party_id=party_id,
                             confirmation=confirmation)

    # ------------------------------------------------------------------ #
    #  helpers
    # ------------------------------------------------------------------ #
    def _resolve_single(self, msg: InboundMessage) -> tuple[Optional[str], bool]:
        """Resolve the sender to EXACTLY one party. Returns (party_id, resolved).
        A multi-match (shared line, ``is_shared_line``) or no match -> not
        resolved (caller routes to staff)."""
        if self.resolver is None:
            return None, False
        id_type = "email" if msg.channel in ("email", "portal") else "phone"
        result = self.resolver.resolve(self.clinic_id, msg.from_identifier_normalized,
                                       id_type, channel=msg.channel)
        if result.match_count == 1 and result.outcome == ResolutionOutcome.RESOLVED_SINGLE:
            return result.candidates[0].party_id, True
        return None, False

    def _do_opt_out(self, party_id, msg, canonical) -> InboundAction:
        self.consent.record_opt_out(
            party_id, msg.channel, source="inbound_stop", keyword=canonical or "STOP",
            inbound_message_id=msg.id,
        )
        return InboundAction.OPT_OUT_RECORDED

    def _persist(self, msg: InboundMessage, canonical, action_taken) -> dict:
        row = InboundMessage(
            id=msg.id, clinic_id=msg.clinic_id or self.clinic_id, channel=msg.channel,
            from_identifier_normalized=msg.from_identifier_normalized, body=msg.body,
            matched_keyword=canonical, action_taken=action_taken,
            received_at=msg.received_at,          # SC-006 clock start (arrival time)
        )
        return self.repo.append_inbound_message(row)


def _keyword_path() -> str:
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    return os.path.join(root, "config", "relationship", "inbound_keywords.en.yaml")
