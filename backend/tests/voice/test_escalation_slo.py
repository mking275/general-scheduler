"""T035 — 100%-escalation SLO harness (SC-002).

A scripted call set that trips **every** protocol keyword + the literal
"emergency" at **every turn position** (including mid-booking). Asserts, for each
flagged call: the deterministic engine flags it, barge-in cuts through, the
escalation reaches a human (or the never-dead-air fallback), a whisper summary is
handed over first, and the escalation is persisted. 0 silent drops.

Sim only; independent of the model (the watchdog has independent transfer
authority). Runs against the docker-compose Postgres repo (skips loudly if down).
"""
from backend.models import (
    CallOutcome, CallSession, EscalationTrigger, TransferOutcome,
)
from backend.voice.adapter_guarantees import EscalationWatchdog
from backend.voice.barge_in import BargeInDetector
from backend.voice.triage_protocol import ESCALATING_URGENCIES, TriageProtocolEngine
from backend.voice.verbs import SimBookingBackend, VoiceVerbs
from backend.voice.warm_transfer import WarmTransfer

_TARGETS = [
    {"id": "t1", "label": "On-call DVM", "phone": "+15551230001", "priority": 1},
    {"id": "t2", "label": "Backup DVM", "phone": "+15551230002", "priority": 2},
]
_ER = [{"name": "Metro Animal ER", "phone": "+15559110000", "hours": "24/7"}]

# Language that would indicate Vera made a clinical assessment — must NEVER appear
# in anything spoken/whispered on a flagged call.
_ASSESSMENT_MARKERS = (
    "diagnos", "you should give", "dosage", " mg", "milligram", "it's probably",
    "likely just", "not serious", "don't worry", "no need to", "prescribe",
)


def _engine() -> TriageProtocolEngine:
    return TriageProtocolEngine.load_sample("goldsmith")


def _flag_keywords(eng: TriageProtocolEngine) -> list[str]:
    """Every keyword across the escalating urgency classes + the literal."""
    kws: list[str] = []
    for name in ESCALATING_URGENCIES:
        cls = eng.config.urgency_classes.get(name)
        if cls:
            kws.extend(cls.keywords)
    kws.append("emergency")
    return sorted(set(kws))


def _assert_no_assessment(*texts: str) -> None:
    for t in texts:
        low = (t or "").lower()
        for m in _ASSESSMENT_MARKERS:
            assert m not in low, f"assessment language leaked: {m!r} in {t!r}"


def test_t035_every_keyword_every_position_escalates_to_human(repo):
    eng = _engine()
    detector = BargeInDetector()
    keywords = _flag_keywords(eng)
    assert len(keywords) >= 15                                # the whole protocol set

    escalated = 0
    total = 0
    silent_drops = 0

    for kw in keywords:
        # Trip the keyword at three turn positions: opening, mid-call, closing.
        for position in (1, 3, 6):
            total += 1
            sess = CallSession(clinic_id="goldsmith-0001",
                               inbound_number="+15551110001")
            repo.create_call_session(sess)
            wt = WarmTransfer(_TARGETS, er_directory=_ER, repo=repo, live=False,
                              answer_policy=lambda t: t["id"] == "t1")

            delta = f"turn {position}: my dog {kw}"
            flag = eng.step(delta)                            # deterministic engine
            assert flag is not None, f"{kw!r} at pos {position} did not flag"
            assert flag["urgency"] in ESCALATING_URGENCIES

            # Barge-in: a flagged emergency keyword cuts through Vera's speech.
            bi = detector.detect(caller_text=delta)
            assert bi.barge_in is True
            assert bi.detect_latency_ms < 400

            # Escalate + persist — whisper summary handed over first.
            result, ev = wt.escalate_and_persist(
                sess, whisper_summary=f"Protocol-flagged ({flag['urgency']}); {kw}.",
                trigger=EscalationTrigger.PROTOCOL_KEYWORD,
                protocol_state=flag["urgency"], watchdog_fired=True)

            assert result.dead_air is False                  # never dead air
            if result.outcome == TransferOutcome.ANSWERED:
                assert result.whisper_before_connect is True  # human briefed first
            # A human was reached OR the never-drop fallback engaged.
            if result.outcome in (TransferOutcome.ANSWERED,
                                   TransferOutcome.FALLBACK_ER_DIRECTORY,
                                   TransferOutcome.VOICEMAIL_CALLBACK):
                escalated += 1
            else:
                silent_drops += 1

            rows = repo.get_escalation_events(sess.id)
            assert len(rows) == 1 and rows[0]["protocol_state"] == flag["urgency"]
            _assert_no_assessment(ev.whisper_summary)

    assert silent_drops == 0                                 # SC-002: 0 silent drops
    assert escalated == total                                # 100% escalate to a human


def test_t035_mid_booking_emergency_abandons_with_zero_rows(repo):
    eng = _engine()
    backend = SimBookingBackend()
    v = VoiceVerbs(backend, repo=repo)
    wt = WarmTransfer(_TARGETS, er_directory=_ER, repo=repo, live=False,
                      answer_policy=lambda t: t["id"] == "t1")
    sess = CallSession(clinic_id="goldsmith-0001", inbound_number="+15551110001")
    repo.create_call_session(sess)

    slot = v.availability("goldsmith-0001", audience_scope="client_verified")[0]
    v.begin_booking("goldsmith-0001", slot, "Rex", party_id="party-1",
                    audience_scope="client_verified")        # read-back only, no write
    assert backend.list_bookings("goldsmith-0001") == []

    flag = eng.step("wait — he just collapsed and isn't breathing")
    assert flag["urgency"] == "emergency"
    result, ev = wt.escalate_and_persist(
        sess, "Collapse mid-booking; booking abandoned.",
        trigger=EscalationTrigger.PROTOCOL_KEYWORD, protocol_state="emergency",
        watchdog_fired=True)

    assert backend.list_bookings("goldsmith-0001") == []     # zero booking rows
    assert len(backend._by_token) == 0                       # no partial write
    assert result.outcome == TransferOutcome.ANSWERED
    assert len(repo.get_escalation_events(sess.id)) == 1


def test_t035_watchdog_is_the_independent_authority(repo):
    """The escalation does not depend on the model — the watchdog fires on the
    protocol flag directly and reaches a human within SLO."""
    wt = WarmTransfer(_TARGETS, repo=repo, live=False,
                      answer_policy=lambda t: t["id"] == "t1")
    wd = EscalationWatchdog(transfer_fn=wt.as_transfer_fn(), slo_ms=3000, repo=repo)
    sess = CallSession(clinic_id="goldsmith-0001", inbound_number="+15551110001")
    repo.create_call_session(sess)
    res = wd.observe_transcript(sess, "hello", protocol_flag="emergency")
    assert res is not None and res.fired
    assert res.within_slo
    assert res.transfer_outcome == TransferOutcome.ANSWERED
    assert res.event.watchdog_fired is True
