"""Phase E — T022 inbound seam, T023 registry, T024 STOP flow, T025 suppression
+ inbound-served disclosure."""
import pytest

from backend.models import CallSession, InboundMessage
from backend.relationship.consent_registry import ConsentDecision, ConsentRegistry
from backend.relationship.identity_resolver import IdentityResolver
from backend.relationship.inbound_gateway import InboundGateway
from backend.relationship.inbound_sim import InboundSimulator
from backend.relationship.outbound_consent import (
    OutboundConsentGate, serve_inbound_with_disclosure,
)
from backend.tests.relationship.fixtures.ezyvet_dirty_corpus import build_corpus

CLINIC = "clinic-consent"
TOM_PHONE = "5551110002"          # single-match -> party c1002
SHARED = "5551110001"             # multi-match (Alvarez + Nguyen) shared line


@pytest.fixture()
def seeded(repo):
    build_corpus(clinic_id=CLINIC).seed_into_repo(repo)
    # contact_consent is an upsert (current-state) table, NOT append-only — reset
    # it per test so persistent-Postgres state does not leak across runs.
    from sqlalchemy import text
    with repo.engine.begin() as conn:
        conn.execute(text("DELETE FROM contact_consent WHERE clinic_id = :c"),
                     {"c": CLINIC})
    return repo


@pytest.fixture()
def gateway(seeded):
    resolver = IdentityResolver(seeded)
    registry = ConsentRegistry(seeded, CLINIC)
    return InboundGateway(seeded, CLINIC, resolver=resolver, consent_registry=registry)


def _tom():
    return f"party-{CLINIC}-c1002"


def _msg(body, frm=TOM_PHONE, channel="sms"):
    return InboundMessage(clinic_id=CLINIC, from_identifier_normalized=frm,
                          body=body, channel=channel)


# --------------------------------------------------------------------------- #
#  T022 — inbound seam: keyword match, staff routing, persistence, sim-only
# --------------------------------------------------------------------------- #
async def test_t022_stop_matches_keyword(gateway):
    res = await gateway.handle_inbound(_msg("STOP"))
    assert res.matched_keyword == "STOP"


async def test_t022_free_text_routes_to_staff_never_auto_actioned(gateway, seeded):
    res = await gateway.handle_inbound(_msg("what are your hours?"))
    assert res.matched_keyword is None
    assert res.action_taken == "routed_to_staff"


async def test_t022_every_inbound_writes_one_row(gateway, seeded):
    before = len(seeded.get_inbound_messages(CLINIC))
    await gateway.handle_inbound(_msg("STOP"))
    await gateway.handle_inbound(_msg("hello"))
    assert len(seeded.get_inbound_messages(CLINIC)) == before + 2


async def test_t022_sim_seam_no_network(gateway):
    sim = InboundSimulator()
    sim.register_handler(gateway.handle_inbound)
    assert sim.is_live() is False              # sim only — no live webhook
    res = await sim.post(_msg("STOP"))         # flows through the same seam
    assert res.matched_keyword == "STOP"


# --------------------------------------------------------------------------- #
#  T023 — consent registry: opt-out/opt-in + append-only events + staff state
# --------------------------------------------------------------------------- #
async def test_t023_opt_out_then_check_denies(seeded):
    reg = ConsentRegistry(seeded, CLINIC)
    reg.record_opt_out(_tom(), "sms", source="staff")
    dec = await reg.consent_check(_tom(), "sms")
    assert isinstance(dec, ConsentDecision)
    assert dec.allowed is False


async def test_t023_opt_in_restores_and_events_are_appended(seeded):
    reg = ConsentRegistry(seeded, CLINIC)
    before = len(seeded.get_consent_events(_tom()))
    reg.record_opt_out(_tom(), "sms", source="staff")
    reg.record_opt_in(_tom(), "sms", source="staff")
    assert (await reg.consent_check(_tom(), "sms")).allowed is True
    assert len(seeded.get_consent_events(_tom())) == before + 2   # both audited
    # current state row reflects the latest (staff-visible, FR-024)
    state = reg.current_state(_tom(), "sms")
    assert state["ai_contact_allowed"] is True


# --------------------------------------------------------------------------- #
#  T024 — STOP -> suppression flow + shared-line safety
# --------------------------------------------------------------------------- #
async def test_t024_inbound_stop_records_opt_out_staff_visible(gateway, seeded):
    res = await gateway.handle_inbound(_msg("STOP"))
    assert res.action_taken == "opt_out_recorded"
    assert res.party_id == _tom()
    # staff-visible immediately (SC-006 ≤60s — sim is synchronous/instant)
    state = seeded.get_consent(_tom(), "sms")
    assert state and state["ai_contact_allowed"] is False
    # the opt-out event links the inbound message id
    ev = seeded.get_consent_events(_tom())[-1]
    assert ev["keyword"] == "STOP" and ev["inbound_message_id"] == res.inbound_message_id


async def test_t024_opt_back_in_later_audited(gateway, seeded):
    await gateway.handle_inbound(_msg("STOP"))
    res_in = await gateway.handle_inbound(_msg("START"))
    assert res_in.action_taken == "opt_in_recorded"
    assert seeded.get_consent(_tom(), "sms")["ai_contact_allowed"] is True


async def test_t024_shared_line_stop_routes_to_staff_opts_out_nobody(gateway, seeded):
    res = await gateway.handle_inbound(_msg("STOP", frm=SHARED))
    assert res.action_taken == "routed_to_staff"
    assert res.party_id is None
    # neither shared-line party was opted out
    for pid in (f"party-{CLINIC}-c1001", f"party-{CLINIC}-c2001"):
        assert seeded.get_consent(pid, "sms") is None


# --------------------------------------------------------------------------- #
#  T025 — outbound suppression (100%) + inbound-served disclosure
# --------------------------------------------------------------------------- #
class _SpyGateway:
    def __init__(self):
        self.sends = []

    def send_sms(self, to, body):
        self.sends.append((to, body))
        return {"to": to, "body": body, "status": "sent"}


async def test_t025_opt_out_suppresses_all_outbound(seeded):
    reg = ConsentRegistry(seeded, CLINIC)
    reg.record_opt_out(_tom(), "sms", source="inbound_stop", keyword="STOP")
    spy = _SpyGateway()
    gate = OutboundConsentGate(reg, spy)
    # 100% of outbound attempts on the covered channel are suppressed (SC-002)
    for _ in range(5):
        r = await gate.send(_tom(), "+15551110002", "Reminder: appt tomorrow", channel="sms")
        assert r.suppressed is True and r.sent is False
    assert spy.sends == []                       # gateway send leg NEVER reached


async def test_t025_allowed_party_outbound_sends(seeded):
    reg = ConsentRegistry(seeded, CLINIC)
    spy = _SpyGateway()
    gate = OutboundConsentGate(reg, spy)
    r = await gate.send(_tom(), "+15551110002", "hi", channel="sms")
    assert r.sent is True and len(spy.sends) == 1


def test_t025_inbound_served_persists_consent_record_disclosure(db_url):
    # the opted-out client calling IN is still served AND a consent_record
    # disclosure row is written via the 010 T033 path (FR-023, M6).
    from backend.voice.voice_repository import VoiceRepository
    try:
        vrepo = VoiceRepository(db_url)
        vrepo.init_db()
    except Exception as exc:                     # pragma: no cover
        pytest.skip(f"voice Postgres unavailable: {exc}")

    session = CallSession(clinic_id=CLINIC, inbound_number="+15551110002",
                          party_id=_tom())
    vrepo.create_call_session(session)
    row = serve_inbound_with_disclosure(vrepo, session,
                                        full_text="opted-out caller served inbound")
    assert row["consent_record"]["disclosure_text"]          # text present, not a bare flag
    assert row["consent_record"]["disclosure_at"] is not None
    persisted = vrepo.get_transcript(session.id)
    assert persisted["consent_record"]["disclosure_text"]
