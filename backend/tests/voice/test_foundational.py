"""Phase 2 (Foundational) verification — T004..T008."""
import os
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import insert, text
from sqlalchemy.exc import IntegrityError, DBAPIError

from backend.models import (
    CallSession, CallTurn, RefillRequestDraft, VerificationState,
)


# --- T004: VoiceRepository on docker-compose Postgres ----------------------
def test_t004_init_db_creates_8_tables(repo):
    assert repo.engine.dialect.name == "postgresql", "must target Postgres, not SQLite"
    with repo.engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema='public'"
        )).scalars().all()
    for t in ("call_session", "call_turn", "call_transcript", "escalation_event",
              "refill_request_draft", "clinic_voice_config", "on_call_target",
              "triage_protocol"):
        assert t in rows, f"table {t} missing"


def test_t004_refill_check_constraint(repo):
    tbl = repo.tables["refill_request_draft"]
    # A valid draft inserts fine.
    ok = RefillRequestDraft(call_session_id="sess-1", party_id="p1",
                            patient_ref="Rex", drug_name_asserted="apoquel")
    repo.create_refill_draft(ok)
    # A non-draft status is rejected by the CHECK constraint at the DB level.
    with pytest.raises((IntegrityError, DBAPIError)):
        with repo.engine.begin() as conn:
            conn.execute(insert(tbl).values(
                id="bad-1", call_session_id="sess-1", party_id="p1",
                patient_ref="Rex", drug_name_asserted="apoquel",
                status="auto_approved",
            ))


def test_t004_scoping_and_roundtrip(repo):
    sess = CallSession(clinic_id="goldsmith-0001", inbound_number="+15558675309",
                       verification_state=VerificationState.UNVERIFIED)
    repo.create_call_session(sess)
    got = repo.get_call_session(sess.id, clinic_id="goldsmith-0001")
    assert got and got["inbound_number"] == "+15558675309"
    # app-level clinic scoping stand-in for RLS: wrong clinic -> no row
    assert repo.get_call_session(sess.id, clinic_id="other-clinic") is None


# --- T005: dual-mode resolver + call simulator -----------------------------
def test_t005_is_live_false_without_creds(monkeypatch):
    from backend.voice import sim
    for var in ("VOICE_LIVE", "TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN",
                "TWILIO_FROM_NUMBER", "GEMINI_API_KEY", "GOOGLE_API_KEY",
                "OPENAI_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    assert sim.is_live() is False


def test_t005_force_flag(monkeypatch):
    from backend.voice import sim
    monkeypatch.setenv("VOICE_LIVE", "true")
    assert sim.is_live() is True
    monkeypatch.setenv("VOICE_LIVE", "false")
    assert sim.is_live() is False


def test_t005_simulator_emits_ordered_events():
    from backend.voice import sim
    simulator = sim.CallSimulator(sim.demo_script())
    types = [ev.type.value for ev in simulator.events()]
    assert types[0] == "caller_utterance"
    assert types[-1] == "hangup"
    assert "silence" in types


# --- T006: ChannelBinding shim ---------------------------------------------
def test_t006_shared_line_multiple_candidates():
    from backend.voice.shims import channel_binding_shim as cb
    b = cb.resolve_binding("+15551110001")
    assert len(b.candidate_parties) > 1
    assert b.is_shared_line


def test_t006_unknown_number_ephemeral_unverified():
    from backend.voice.shims import channel_binding_shim as cb
    b = cb.resolve_binding("+19998887777")
    assert len(b.candidate_parties) == 1
    assert b.candidate_parties[0].ephemeral
    assert b.audience_scope == "caller_unverified"
    assert b.verification_level == "none"


def test_t006_disambiguation_soft_confirms_one_without_enumerating():
    from backend.voice.shims import channel_binding_shim as cb
    b = cb.resolve_binding("+15551110001")
    b2 = cb.disambiguate(b, "Jane")
    assert b2.verification_level == "soft_confirmed"
    assert b2.confirmed_party.party_id == "party-alvarez-jane"
    assert b2.audience_scope == "client_verified"


def test_t006_unmatched_answer_stays_unverified():
    from backend.voice.shims import channel_binding_shim as cb
    b = cb.resolve_binding("+15551110001")
    b2 = cb.disambiguate(b, "Napoleon Bonaparte")
    assert b2.verification_level == "none"
    assert b2.confirmed_party is None


# --- T007: L2 bridge + pre-speak interposition -----------------------------
async def test_t007_pre_speak_replace_overrides_draft():
    from backend.voice.shims import l2_bridge_shim as l2

    class ReplacingHooks(l2.TurnHooks):
        async def pre_speak(self, draft, ctx):
            return l2.TurnDecision(action="replace",
                                   text="Let me connect you to a person.",
                                   override_reason="protocol_flag")

    draft = l2.ModelOutput(text="Sure, I can book that for you.")
    ctx = l2.TurnContext(session_id="s", seq=2)
    result = await l2.converse_turn({}, draft, ctx, hooks=ReplacingHooks())
    assert result.action == "replace"
    assert result.spoken_text == "Let me connect you to a person."
    assert result.model_draft == "Sure, I can book that for you."
    assert result.spoken_text != result.model_draft


async def test_t007_registry_marked_prototype():
    from backend.voice.shims import l2_bridge_shim as l2
    sess = await l2.bridge_inbound("voice", {"from": "+15551110002"})
    assert sess["registry_mark"] == "prototype"


# --- T008: consent shim ----------------------------------------------------
async def test_t008_optout_denies_default_allows():
    from backend.voice.shims import consent_shim as cs
    denied = await cs.consent_check("party-optout-demo", "voice", "callback")
    assert denied.allowed is False
    allowed = await cs.consent_check("party-regular", "voice", "callback")
    assert allowed.allowed is True
