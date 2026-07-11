"""T035 [US6] — consent timing + honor harness.

Covers: inbound STOP timing (SC-006), 100% outbound suppression (SC-002),
inbound-still-served WITH a persisted consent_record disclosure via the 010 T033
path (M6/FR-023 — assert the disclosure record exists, not just that service
continued), and opt-back-in audit.
"""
import time

import pytest

from backend.models import CallSession, InboundMessage
from backend.relationship.consent_registry import ConsentRegistry
from backend.relationship.identity_resolver import IdentityResolver
from backend.relationship.inbound_gateway import InboundGateway
from backend.relationship.outbound_consent import (
    OutboundConsentGate, serve_inbound_with_disclosure,
)
from backend.tests.relationship.fixtures.ezyvet_dirty_corpus import build_corpus

CLINIC = "clinic-t035-consent"
TOM = "5551110002"                     # single-match -> party c1002


@pytest.fixture()
def seeded(repo):
    build_corpus(clinic_id=CLINIC).seed_into_repo(repo)
    from sqlalchemy import text
    with repo.engine.begin() as conn:
        conn.execute(text("DELETE FROM contact_consent WHERE clinic_id = :c"),
                     {"c": CLINIC})
    return repo


def _tom(clinic=CLINIC):
    return f"party-{clinic}-c1002"


def _gateway(repo):
    return InboundGateway(repo, CLINIC, resolver=IdentityResolver(repo),
                          consent_registry=ConsentRegistry(repo, CLINIC))


def _msg(body, frm=TOM, channel="sms"):
    return InboundMessage(clinic_id=CLINIC, from_identifier_normalized=frm,
                          body=body, channel=channel)


# --------------------------------------------------------------------------- #
#  SC-006 — STOP recorded + staff-visible <= 60 s (sim clock is instant)
# --------------------------------------------------------------------------- #
async def test_t035_stop_recorded_and_visible_within_60s(seeded):
    gw = _gateway(seeded)
    t0 = time.monotonic()
    res = await gw.handle_inbound(_msg("STOP"))
    elapsed = time.monotonic() - t0
    assert res.action_taken == "opt_out_recorded"
    # staff-visible current state reflects the opt-out
    state = seeded.get_consent(_tom(), "sms")
    assert state and state["ai_contact_allowed"] is False
    assert elapsed <= 60.0                                     # SC-006 (instant in sim)


async def test_t035_opt_back_in_audited(seeded):
    gw = _gateway(seeded)
    await gw.handle_inbound(_msg("STOP"))
    await gw.handle_inbound(_msg("START"))
    assert seeded.get_consent(_tom(), "sms")["ai_contact_allowed"] is True
    # both transitions are in the append-only audit trail
    actions = [e["action"] for e in seeded.get_consent_events(_tom())]
    assert "opt_out" in actions and "opt_in" in actions


# --------------------------------------------------------------------------- #
#  SC-002 — 100% outbound suppression on the covered channel
# --------------------------------------------------------------------------- #
class _SpyGateway:
    def __init__(self):
        self.sends = []

    def send_sms(self, to, body):
        self.sends.append((to, body))
        return {"to": to, "body": body, "status": "sent"}


async def test_t035_outbound_suppression_is_total(seeded):
    reg = ConsentRegistry(seeded, CLINIC)
    reg.record_opt_out(_tom(), "sms", source="inbound_stop", keyword="STOP")
    spy = _SpyGateway()
    gate = OutboundConsentGate(reg, spy)
    suppressed = 0
    for _ in range(20):
        r = await gate.send(_tom(), "+15551110002", "reminder", channel="sms")
        if r.suppressed and not r.sent:
            suppressed += 1
    assert suppressed == 20                                    # 100% (SC-002)
    assert spy.sends == []                                     # send leg never reached


# --------------------------------------------------------------------------- #
#  FR-023 / M6 — opted-out inbound STILL served + consent_record disclosure
# --------------------------------------------------------------------------- #
def test_t035_opted_out_inbound_served_persists_disclosure(seeded, db_url):
    reg = ConsentRegistry(seeded, CLINIC)
    reg.record_opt_out(_tom(), "sms", source="inbound_stop", keyword="STOP")
    # inbound service is NOT gated by the opt-out (consent governs contact only)
    from backend.voice.voice_repository import VoiceRepository
    try:
        vrepo = VoiceRepository(db_url)
        vrepo.init_db()
    except Exception as exc:                                   # pragma: no cover
        pytest.skip(f"voice Postgres unavailable: {exc}")

    session = CallSession(clinic_id=CLINIC, inbound_number="+15551110002",
                          party_id=_tom())
    vrepo.create_call_session(session)
    row = serve_inbound_with_disclosure(
        vrepo, session, full_text="opted-out caller served inbound",
        vendor_attestation="DPA-otter-safe")

    # the disclosure record exists end-to-end (not a bare flag) — M6
    assert row["consent_record"]["disclosure_text"]
    assert row["consent_record"]["disclosure_at"] is not None
    persisted = vrepo.get_transcript(session.id)
    assert persisted["consent_record"]["disclosure_text"]
    assert persisted["vendor_no_training_attestation"] == "DPA-otter-safe"
    # and the outbound opt-out is still in force (inbound service did not clear it)
    assert seeded.get_consent(_tom(), "sms")["ai_contact_allowed"] is False
