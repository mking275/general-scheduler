"""Phase B (Turn loop + adapter guarantees — the safety spine) — T015..T019."""
from datetime import datetime, timezone

import pytest
from sqlalchemy import delete, text, update

from backend.models import (
    CallSession, CallTurn, EscalationTrigger, GateDecision, TransferOutcome,
    TurnRole, VerificationState,
)


# --- T015: every turn passes through pre_speak -----------------------------
async def test_t015_every_turn_through_pre_speak():
    from backend.voice.turn_loop import ProtocolAwareHooks, TurnLoopStats, run_turn
    from backend.voice.shims.l2_bridge_shim import ModelOutput, TurnContext

    stats = TurnLoopStats()
    hooks = ProtocolAwareHooks(stats=stats)
    drafts = ["Hi there.", "Tomorrow at 2pm works.", "You're all set."]
    for i, d in enumerate(drafts, start=2):
        res = await run_turn({}, ModelOutput(text=d),
                             TurnContext(session_id="s", seq=i), hooks)
        assert res.spoken_text == d          # model narrates when unflagged
    assert stats.turns == 3
    assert stats.pre_speak_invocations == 3   # 100%: one per turn


async def test_t015_protocol_and_gate_override_model():
    from backend.voice.turn_loop import ProtocolAwareHooks, run_turn
    from backend.voice.shims.l2_bridge_shim import ModelOutput, TurnContext

    # Protocol flags emergency -> model output overridden to escalate.
    hooks = ProtocolAwareHooks(
        protocol_step=lambda delta: {"urgency": "emergency"} if "collapsed" in delta else None,
    )
    res = await run_turn({}, ModelOutput(text="Sure, I can book that."),
                         TurnContext(session_id="s", seq=2, transcript_delta="my dog collapsed"),
                         hooks)
    assert res.action == "escalate"
    assert res.spoken_text != "Sure, I can book that."

    # Gate rejects a write -> model output replaced.
    hooks2 = ProtocolAwareHooks(gate_classify=lambda tools: GateDecision.REJECT)
    res2 = await run_turn({}, ModelOutput(text="Approved.", tool_calls=[{"name": "x"}]),
                          TurnContext(session_id="s", seq=3), hooks2)
    assert res2.action == "replace"


# --- T016: disclosure-before-model, 100% ------------------------------------
def test_t016_disclosure_seq1_on_100_calls():
    from backend.voice.adapter_guarantees import DisclosureGuarantee
    g = DisclosureGuarantee()
    for _ in range(100):
        sess = CallSession(clinic_id="goldsmith-0001", inbound_number="+15550000000")
        turn = g.deliver_disclosure(sess)
        assert turn.seq == 1
        assert turn.role == TurnRole.SYSTEM
        assert "emergency" in turn.text.lower()
        # consent recorded == disclosure time (SC-001)
        assert sess.consent_recorded_at == turn.started_at


def test_t016_model_may_not_engage_before_disclosure():
    from backend.voice.adapter_guarantees import (
        DisclosureGuarantee, DisclosureNotDeliveredError,
    )
    g = DisclosureGuarantee()
    sess = CallSession(clinic_id="c", inbound_number="+1")
    with pytest.raises(DisclosureNotDeliveredError):
        g.guard_model_engage(sess)
    g.deliver_disclosure(sess)
    g.guard_model_engage(sess)               # now allowed


def test_t016_disclosure_persists(repo):
    from backend.voice.adapter_guarantees import DisclosureGuarantee
    sess = CallSession(clinic_id="goldsmith-0001", inbound_number="+15551112222")
    repo.create_call_session(sess)
    g = DisclosureGuarantee(repo=repo)
    g.deliver_disclosure(sess)
    turns = repo.get_turns(sess.id)
    assert turns and turns[0]["seq"] == 1 and turns[0]["role"] == "system"
    got = repo.get_call_session(sess.id)
    assert got["consent_recorded_at"] is not None


# --- T017: escalation watchdog with independent transfer authority ----------
async def test_t017_watchdog_fires_on_model_stall_within_slo():
    from backend.voice.adapter_guarantees import EscalationWatchdog

    transfers = []

    def transfer(session, summary):
        transfers.append((session.id, summary))
        return TransferOutcome.ANSWERED

    wd = EscalationWatchdog(transfer_fn=transfer, slo_ms=3000)
    sess = CallSession(clinic_id="c", inbound_number="+1")
    # Model stalled well past SLO — watchdog fires independently.
    res = wd.observe_model_stall(sess, waited_ms=5000)
    assert res is not None and res.fired
    assert res.event.watchdog_fired is True
    assert res.within_slo                    # transfer completed within SLO
    assert len(transfers) == 1               # 0 silent drops — a human was reached


def test_t017_literal_emergency_and_silence_and_protocol_branches():
    from backend.voice.adapter_guarantees import EscalationWatchdog
    wd = EscalationWatchdog(slo_ms=3000, silence_threshold_ms=8000)
    sess = CallSession(clinic_id="c", inbound_number="+1")

    r1 = wd.observe_transcript(sess, "this is an emergency my dog collapsed")
    assert r1 and r1.trigger == EscalationTrigger.EXPLICIT_EMERGENCY

    r2 = wd.observe_silence(sess, silence_ms=9000)
    assert r2 and r2.trigger == EscalationTrigger.SLO_BREACH

    # protocol_flag branch (T020 engine feeds the flag) — testable now.
    r3 = wd.observe_transcript(sess, "hello", protocol_flag="emergency")
    assert r3 and r3.trigger == EscalationTrigger.PROTOCOL_KEYWORD

    # a benign turn does not fire
    assert wd.observe_transcript(sess, "I'd like to book a checkup") is None


# --- T018: append-only transcript + call_turn log ---------------------------
def test_t018_turn_logged_and_immutable(repo):
    from backend.voice.adapter_guarantees import TranscriptLogger
    sess = CallSession(clinic_id="goldsmith-0001", inbound_number="+15553334444")
    repo.create_call_session(sess)
    logger = TranscriptLogger(repo)
    turn = CallTurn(call_session_id=sess.id, seq=1, role=TurnRole.CALLER,
                    text="Booking please", started_at=datetime.now(timezone.utc).isoformat())
    logger.log_turn(turn)
    rows = repo.get_turns(sess.id)
    assert len(rows) == 1

    tbl = repo.tables["call_turn"]
    # UPDATE rejected by append-only trigger
    with pytest.raises(Exception):
        with repo.engine.begin() as conn:
            conn.execute(update(tbl).where(tbl.c.id == turn.id).values(text="tampered"))
    # DELETE rejected by append-only trigger
    with pytest.raises(Exception):
        with repo.engine.begin() as conn:
            conn.execute(delete(tbl).where(tbl.c.id == turn.id))
    # row unchanged
    assert repo.get_turns(sess.id)[0]["text"] == "Booking please"


def test_t018_transcript_retention_for_flagged(repo):
    from backend.voice.adapter_guarantees import TranscriptLogger
    sess = CallSession(clinic_id="goldsmith-0001", inbound_number="+15555556666")
    sess.consent_recorded_at = datetime.now(timezone.utc).isoformat()
    repo.create_call_session(sess)
    logger = TranscriptLogger(repo)
    logger.finalize_transcript(sess, "full text", vendor_attestation="DPA-1",
                               protocol_flagged=True)
    tr = repo.get_transcript(sess.id)
    assert tr and tr["vendor_no_training_attestation"] == "DPA-1"


# --- T019: barge-in detection + backchannel filter --------------------------
def test_t019_emergency_cuts_through_within_400ms():
    from backend.voice.barge_in import BargeInDetector
    d = BargeInDetector()
    r = d.detect(caller_text="emergency! my dog collapsed")
    assert r.barge_in is True and r.cut_through is True
    assert r.detect_latency_ms < 400


def test_t019_backchannel_does_not_misfire():
    from backend.voice.barge_in import BargeInDetector
    d = BargeInDetector()
    for bc in ("uh-huh", "mm-hmm", "yeah", "okay"):
        r = d.detect(caller_text=bc)
        assert r.barge_in is False, f"{bc!r} misfired as barge-in"
    # a real interruption still fires
    assert d.detect(caller_text="wait, stop, that's the wrong day").barge_in is True
