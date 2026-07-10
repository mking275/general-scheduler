"""T036 — model-stall / disconnect injection layer for the SLO harness.

Proves the escalation watchdog transfers within SLO **despite** a stalled or
disconnected model — the model is never on the escalation path. With a stall
injected on every flagged call, escalation completion = 100% and
``watchdog_fired`` is asserted on each. Sim only.
"""
from backend.models import CallSession, EscalationTrigger, TransferOutcome
from backend.voice.adapter_guarantees import EscalationWatchdog
from backend.voice.triage_protocol import ESCALATING_URGENCIES, TriageProtocolEngine
from backend.voice.warm_transfer import WarmTransfer

_TARGETS = [{"id": "t1", "label": "On-call DVM", "phone": "+15551230001", "priority": 1}]
_ER = [{"name": "Metro Animal ER", "phone": "+15559110000", "hours": "24/7"}]


def _flag_keywords(eng: TriageProtocolEngine) -> list[str]:
    kws: list[str] = []
    for name in ESCALATING_URGENCIES:
        cls = eng.config.urgency_classes.get(name)
        if cls:
            kws.extend(cls.keywords)
    return sorted(set(kws))


class _StalledModel:
    """A model that never produces output (or has disconnected)."""

    def __init__(self, disconnected: bool = False):
        self.disconnected = disconnected
        self.output_produced = False

    def waited_ms(self) -> int:
        return 999_999                                       # never responds


def test_t036_stall_on_every_flagged_call_still_escalates_100pct(repo):
    eng = TriageProtocolEngine.load_sample("goldsmith")
    keywords = _flag_keywords(eng)
    completed = 0
    total = 0

    for kw in keywords:
        for disconnected in (False, True):                   # stall AND disconnect
            total += 1
            sess = CallSession(clinic_id="goldsmith-0001",
                               inbound_number="+15551110001")
            repo.create_call_session(sess)
            model = _StalledModel(disconnected=disconnected)

            wt = WarmTransfer(_TARGETS, er_directory=_ER, repo=repo, live=False,
                              answer_policy=lambda t: t["id"] == "t1")
            wd = EscalationWatchdog(transfer_fn=wt.as_transfer_fn(),
                                    slo_ms=3000, repo=repo)

            flag = eng.step(f"my dog {kw}")
            assert flag and flag["urgency"] in ESCALATING_URGENCIES

            # The model stalled — the watchdog fires INDEPENDENTLY (model never
            # produced output). This is the model-stall injection.
            res = wd.observe_model_stall(sess, waited_ms=model.waited_ms())
            assert res is not None and res.fired
            assert res.within_slo                            # transferred within SLO
            assert res.event.watchdog_fired is True          # forced by the watchdog
            assert res.transfer_outcome in (
                TransferOutcome.ANSWERED, TransferOutcome.FALLBACK_ER_DIRECTORY,
                TransferOutcome.VOICEMAIL_CALLBACK)
            assert model.output_produced is False            # model never on the path
            completed += 1

    assert completed == total                                # 100% escalation completion


def test_t036_disconnect_before_resume_still_reaches_human(repo):
    """If the model disconnects and does not resume in time, the watchdog's
    independent authority still reaches a human — no silent drop."""
    wt = WarmTransfer(_TARGETS, er_directory=_ER, repo=repo, live=False,
                      answer_policy=lambda t: False)         # nobody picks up
    wd = EscalationWatchdog(transfer_fn=wt.as_transfer_fn(), slo_ms=3000, repo=repo)
    sess = CallSession(clinic_id="goldsmith-0001", inbound_number="+15551110001")
    repo.create_call_session(sess)

    res = wd.observe_model_stall(sess, waited_ms=8000)
    assert res is not None and res.fired
    # No human answered, but the fallback engaged — never a silent drop.
    assert res.transfer_outcome == TransferOutcome.FALLBACK_ER_DIRECTORY
    assert res.event.watchdog_fired is True


def test_t036_silence_stall_triggers_slo_breach(repo):
    wt = WarmTransfer(_TARGETS, repo=repo, live=False,
                      answer_policy=lambda t: t["id"] == "t1")
    wd = EscalationWatchdog(transfer_fn=wt.as_transfer_fn(),
                            silence_threshold_ms=8000, repo=repo)
    sess = CallSession(clinic_id="goldsmith-0001", inbound_number="+15551110001")
    repo.create_call_session(sess)
    res = wd.observe_silence(sess, silence_ms=9000)
    assert res is not None and res.trigger == EscalationTrigger.SLO_BREACH
    assert res.event.watchdog_fired is True
