"""Phase E — warm transfer + overflow fallback (T029..T031). Sim only."""
import pytest

from backend.models import (
    CallSession, EscalationTrigger, TransferOutcome,
)

_TARGETS = [
    {"id": "t1", "label": "On-call DVM", "phone": "+15551230001", "priority": 1},
    {"id": "t2", "label": "Backup DVM", "phone": "+15551230002", "priority": 2},
]
_ER = [{"name": "Metro Animal ER", "phone": "+15559110000", "hours": "24/7"}]


class _FakeSMS:
    def __init__(self):
        self.sent = []

    def send_sms(self, to, body):
        self.sent.append((to, body))
        return {"to": to, "body": body, "simulated": True}


# =========================================================================== #
#  T029 — warm transfer: whisper BEFORE connect; priority order
# =========================================================================== #
def test_t029_whisper_before_connect_to_highest_priority():
    from backend.voice.warm_transfer import WarmTransfer
    wt = WarmTransfer(_TARGETS, live=False)
    sess = CallSession(clinic_id="goldsmith-0001", inbound_number="+15551110001")
    res = wt.transfer(sess, whisper_summary="Caller reports dog collapsed; possible emergency.")
    assert res.outcome == TransferOutcome.ANSWERED
    assert res.whisper_before_connect is True           # human briefed before caller bridged
    assert res.target["id"] == "t1"                     # highest priority (priority=1)
    assert res.dead_air is False


def test_t029_priority_order_picks_backup_when_primary_absent():
    from backend.voice.warm_transfer import WarmTransfer
    # Only the backup (priority 2) answers.
    wt = WarmTransfer(_TARGETS, live=False,
                      answer_policy=lambda t: t["id"] == "t2")
    sess = CallSession(clinic_id="c", inbound_number="+1")
    res = wt.transfer(sess, "summary")
    assert res.outcome == TransferOutcome.ANSWERED
    assert res.target["id"] == "t2"
    assert res.attempts == ["On-call DVM", "Backup DVM"]  # tried in priority order


def test_t029_plugs_into_watchdog_as_transfer_authority():
    from backend.voice.adapter_guarantees import EscalationWatchdog
    from backend.voice.warm_transfer import WarmTransfer
    wt = WarmTransfer(_TARGETS, live=False)
    wd = EscalationWatchdog(transfer_fn=wt.as_transfer_fn(), slo_ms=3000)
    sess = CallSession(clinic_id="c", inbound_number="+1")
    res = wd.observe_transcript(sess, "this is an emergency")
    assert res is not None and res.fired
    assert res.transfer_outcome == TransferOutcome.ANSWERED


# =========================================================================== #
#  T030 — ER-directory + callback on no-answer; voicemail last resort
# =========================================================================== #
def test_t030_no_answer_falls_through_to_er_directory_and_callback():
    from backend.voice.warm_transfer import WarmTransfer
    sms = _FakeSMS()
    wt = WarmTransfer(_TARGETS, sms_gateway=sms, er_directory=_ER, live=False,
                      answer_policy=lambda t: False)      # nobody answers
    sess = CallSession(clinic_id="goldsmith-0001", inbound_number="+15551110001")
    res = wt.transfer(sess, "summary")
    assert res.outcome == TransferOutcome.FALLBACK_ER_DIRECTORY
    assert res.er_directory_read is True
    assert res.callback_promised is True
    assert res.fallback_path == "er_directory_readout+callback"
    assert res.dead_air is False
    assert len(sms.sent) == 1                             # callback promise sent


def test_t030_voicemail_callback_last_resort_never_dead_air():
    from backend.voice.warm_transfer import WarmTransfer
    sms = _FakeSMS()
    # No targets answer AND no ER directory -> voicemail + callback.
    wt = WarmTransfer(_TARGETS, sms_gateway=sms, er_directory=[], live=False,
                      answer_policy=lambda t: False)
    sess = CallSession(clinic_id="c", inbound_number="+15551110001")
    res = wt.transfer(sess, "summary")
    assert res.outcome == TransferOutcome.VOICEMAIL_CALLBACK
    assert res.callback_promised is True
    assert res.dead_air is False


def test_t030_loads_targets_from_clinic_config():
    import os
    import yaml
    from backend.voice.warm_transfer import targets_from_config, er_directory_from_config
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    with open(os.path.join(repo_root, "config", "voice",
                           "clinic_voice_config.goldsmith.yaml")) as f:
        cfg = yaml.safe_load(f)
    targets = targets_from_config(cfg)
    assert targets and targets[0]["priority"] == 1
    assert er_directory_from_config(cfg)                  # ER directory present


# =========================================================================== #
#  T031 — escalation-event persistence + no-partial-write on abandoned booking
# =========================================================================== #
def test_t031_escalation_event_persisted_with_fallback_path(repo):
    from backend.voice.warm_transfer import WarmTransfer
    sms = _FakeSMS()
    wt = WarmTransfer(_TARGETS, sms_gateway=sms, er_directory=_ER, repo=repo,
                      live=False, answer_policy=lambda t: False)
    sess = CallSession(clinic_id="goldsmith-0001", inbound_number="+15551110001")
    repo.create_call_session(sess)
    result, ev = wt.escalate_and_persist(
        sess, "Caller: dog collapsed mid-call.",
        trigger=EscalationTrigger.PROTOCOL_KEYWORD, protocol_state="emergency",
        watchdog_fired=True)
    rows = repo.get_escalation_events(sess.id)
    assert len(rows) == 1
    assert rows[0]["fallback_path"] == "er_directory_readout+callback"
    assert rows[0]["transfer_outcome"] == "fallback_er_directory"
    assert rows[0]["watchdog_fired"] is True


def test_t031_mid_booking_emergency_leaves_zero_booking_rows(repo):
    """A mid-booking emergency abandons the booking with ZERO rows written and
    records an escalation_event with the fallback path taken (FR-016 edge)."""
    from backend.voice.verbs import VoiceVerbs, SimBookingBackend
    from backend.voice.triage_protocol import TriageProtocolEngine
    from backend.voice.warm_transfer import WarmTransfer

    backend = SimBookingBackend()
    v = VoiceVerbs(backend, repo=repo)
    eng = TriageProtocolEngine.load_sample("goldsmith")
    wt = WarmTransfer(_TARGETS, er_directory=_ER, repo=repo, live=False,
                      answer_policy=lambda t: t["id"] == "t1")

    sess = CallSession(clinic_id="goldsmith-0001", inbound_number="+15551110001")
    repo.create_call_session(sess)

    # Phase 1: read-back produced — NO write yet.
    slot = v.availability("goldsmith-0001", audience_scope="client_verified")[0]
    read_back = v.begin_booking("goldsmith-0001", slot, "Rex", party_id="party-1",
                                audience_scope="client_verified")
    assert backend.list_bookings("goldsmith-0001") == []      # nothing written

    # Mid-booking, the caller reports an emergency -> protocol flags -> abandon.
    flag = eng.step("wait, he just collapsed")
    assert flag and flag["urgency"] == "emergency"
    # The booking is ABANDONED — commit_booking is never called.
    result, ev = wt.escalate_and_persist(
        sess, "Caller reported collapse mid-booking; booking abandoned.",
        trigger=EscalationTrigger.PROTOCOL_KEYWORD, protocol_state=flag["urgency"],
        watchdog_fired=True)

    # Zero booking rows, and the escalation is recorded with its fallback path.
    assert backend.list_bookings("goldsmith-0001") == []
    assert len(v.backend._by_token) == 0                      # truly no partial write
    events = repo.get_escalation_events(sess.id)
    assert len(events) == 1 and events[0]["protocol_state"] == "emergency"
    assert result.outcome == TransferOutcome.ANSWERED
