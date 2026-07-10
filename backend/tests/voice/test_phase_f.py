"""Phase F — telemetry + consent/attestation + morning briefing (T032..T034).

Sim only; the repo fixture uses the docker-compose Postgres (skips loudly if
down). No live calls.
"""
from datetime import datetime, timedelta, timezone

from backend.models import (
    CallOutcome, CallSession, CallTranscript, CallTurn, EscalationEvent,
    EscalationTrigger, ModelProvider, RefillRequestDraft, TransferOutcome,
    TurnRole, VerificationState,
)


class _FakeSMS:
    def __init__(self):
        self.sent = []

    def send_sms(self, to, body):
        self.sent.append((to, body))
        return {"to": to, "body": body, "simulated": True}


def _now():
    return datetime.now(timezone.utc)


# =========================================================================== #
#  T032 — CallTelemetry: cost from pricing.yml, p50/p95, containment metric
# =========================================================================== #
def test_t032_cost_priced_from_pricing_yml():
    from backend.voice.telemetry import compute_cost_usd, load_pricing
    pricing = load_pricing()
    # gemini_live: 0.010 in + 0.024 out per min, 0.0005/1k tokens.
    cost = compute_cost_usd(ModelProvider.GEMINI_LIVE, audio_in_min=2.0,
                            audio_out_min=1.0, text_tokens=1000)
    expected = 2.0 * 0.010 + 1.0 * 0.024 + 1.0 * 0.0005
    assert abs(cost - expected) < 1e-9
    # provider swap changes the price (openai is pricier).
    oai = compute_cost_usd(ModelProvider.OPENAI_REALTIME, 2.0, 1.0, 1000, pricing=pricing)
    assert oai > cost


def test_t032_sim_call_emits_cost_and_p50_p95():
    from backend.voice.telemetry import build_call_telemetry
    sess = CallSession(clinic_id="goldsmith-0001", inbound_number="+15551110001",
                       model_provider=ModelProvider.GEMINI_LIVE,
                       call_outcome=CallOutcome.CONTAINED, containment_flag=True,
                       session_resume_count=1)
    turns = [CallTurn(call_session_id=sess.id, seq=i, role=TurnRole.VERA,
                      latency_ms=lat)
             for i, lat in enumerate([120, 200, 350, 900, 1500], start=1)]
    tel = build_call_telemetry(sess, turns, audio_in_min=1.5, audio_out_min=0.8)
    assert tel.cost_usd > 0                                   # priced from pricing.yml
    assert tel.turn_latency_p50_ms <= tel.turn_latency_p95_ms
    assert tel.turn_latency_p95_ms >= 900                     # tail reflected
    assert tel.model_provider == "gemini_live"
    assert tel.session_resume_count == 1
    assert tel.containment_flag is True


def test_t032_containment_flag_true_for_contained_and_booked():
    # booked ⊆ contained (F2): both non-emergency outcomes carry containment_flag.
    contained = CallSession(clinic_id="c", inbound_number="+1",
                            call_outcome=CallOutcome.CONTAINED, containment_flag=True)
    booked = CallSession(clinic_id="c", inbound_number="+2",
                         call_outcome=CallOutcome.BOOKED, containment_flag=True)
    assert contained.containment_flag and booked.containment_flag


def test_t032_sc004_containment_rate_over_non_emergency():
    from backend.voice.telemetry import containment_rate
    sessions = [
        CallSession(clinic_id="c", inbound_number="+1",
                    call_outcome=CallOutcome.CONTAINED, containment_flag=True),
        CallSession(clinic_id="c", inbound_number="+2",
                    call_outcome=CallOutcome.BOOKED, containment_flag=True),
        CallSession(clinic_id="c", inbound_number="+3",
                    call_outcome=CallOutcome.DEFLECTED, containment_flag=False),
        # An escalated (emergency) call is EXCLUDED from the denominator.
        CallSession(clinic_id="c", inbound_number="+4",
                    call_outcome=CallOutcome.ESCALATED, containment_flag=False),
    ]
    rate = containment_rate(sessions)
    assert abs(rate - (2 / 3)) < 1e-9                         # 2 contained / 3 non-emergency


def test_t032_telemetry_persists_cost_to_session(repo):
    from backend.voice.telemetry import build_call_telemetry
    sess = CallSession(clinic_id="goldsmith-0001", inbound_number="+15551110009",
                       model_provider=ModelProvider.GEMINI_LIVE,
                       started_at=_now().isoformat())
    repo.create_call_session(sess)
    build_call_telemetry(sess, [], audio_in_min=1.0, audio_out_min=0.5, repo=repo)
    row = repo.get_call_session(sess.id)
    assert row["cost_usd"] is not None and float(row["cost_usd"]) > 0


# =========================================================================== #
#  T033 — consent + no-training attestation on call_transcript
# =========================================================================== #
def test_t033_transcript_carries_consent_record_and_attestation(repo):
    from backend.voice.adapter_guarantees import TranscriptLogger, load_disclosure
    sess = CallSession(clinic_id="goldsmith-0001", inbound_number="+15551112222",
                       consent_recorded_at=_now().isoformat())
    repo.create_call_session(sess)
    logger = TranscriptLogger(repo)
    logger.finalize_transcript(sess, "full transcript text",
                               vendor_attestation="DPA-goldsmith-2026",
                               protocol_flagged=False)
    tr = repo.get_transcript(sess.id)
    assert tr is not None
    cr = tr["consent_record"]
    assert cr["disclosure_at"] == sess.consent_recorded_at
    # The exact disclosure TEXT served is recorded, not just a flag.
    assert cr["disclosure_text"] == load_disclosure("en")
    assert "AI" in cr["disclosure_text"]
    assert tr["vendor_no_training_attestation"] == "DPA-goldsmith-2026"


def test_t033_flagged_call_retained_at_least_6_months(repo):
    from backend.voice.adapter_guarantees import TranscriptLogger
    sess = CallSession(clinic_id="goldsmith-0001", inbound_number="+15551113333",
                       consent_recorded_at=_now().isoformat())
    repo.create_call_session(sess)
    TranscriptLogger(repo).finalize_transcript(
        sess, "flagged call", vendor_attestation="DPA-1", protocol_flagged=True)
    tr = repo.get_transcript(sess.id)
    retained = tr["retained_until"]
    retained_dt = retained if isinstance(retained, datetime) else datetime.fromisoformat(str(retained))
    if retained_dt.tzinfo is None:
        retained_dt = retained_dt.replace(tzinfo=timezone.utc)
    assert retained_dt >= _now() + timedelta(days=182)        # >= ~6 months


# =========================================================================== #
#  T034 — morning-briefing overnight rollup
# =========================================================================== #
def test_t034_overnight_rollup_projects_outcomes_and_follow_ups(repo):
    from backend.voice.morning_briefing import MorningBriefing
    clinic = "goldsmith-brief-0001"
    base = _now()

    # One session of each call_outcome, overnight.
    outcomes = {
        CallOutcome.CONTAINED: True,
        CallOutcome.BOOKED: True,
        CallOutcome.DEFLECTED: False,
        CallOutcome.ESCALATED: False,
    }
    sessions = {}
    for i, (oc, contained) in enumerate(outcomes.items()):
        s = CallSession(clinic_id=clinic, inbound_number=f"+1555000{i:04d}",
                        call_outcome=oc, containment_flag=contained,
                        cost_usd=0.05, started_at=(base + timedelta(minutes=i)).isoformat())
        repo.create_call_session(s)
        sessions[oc] = s

    # The escalated call: a no-answer fallback -> call-back owed.
    repo.create_escalation_event(EscalationEvent(
        call_session_id=sessions[CallOutcome.ESCALATED].id,
        trigger=EscalationTrigger.PROTOCOL_KEYWORD, protocol_state="emergency",
        transfer_outcome=TransferOutcome.FALLBACK_ER_DIRECTORY,
        fallback_path="er_directory_readout+callback", watchdog_fired=True,
        triggered_at=base.isoformat()))
    # The contained call left a refill draft awaiting the vet.
    repo.create_refill_draft(RefillRequestDraft(
        call_session_id=sessions[CallOutcome.CONTAINED].id, party_id="party-1",
        patient_ref="Rex", drug_name_asserted="Apoquel",
        refills_remaining_at_capture=2))

    sms = _FakeSMS()
    mb = MorningBriefing(repo, sms_gateway=sms)
    out = mb.deliver(clinic, to="+15559990000",
                     since=(base - timedelta(hours=1)).isoformat(),
                     until=(base + timedelta(hours=1)).isoformat())
    briefing = out["briefing"]

    # Every outcome present.
    seen = {r.call_outcome for r in briefing.rows}
    assert seen == {"contained", "booked", "deflected", "escalated"}
    assert briefing.total_calls == 4
    assert briefing.contained == 2                            # contained + booked
    assert briefing.escalations == 1
    assert briefing.callbacks_owed == 1                       # the no-answer fallback
    assert briefing.pending_refills == 1

    # Flagged follow-ups surfaced on their rows.
    esc_row = next(r for r in briefing.rows if r.call_outcome == "escalated")
    assert esc_row.callback_owed is True and esc_row.escalations == 1
    con_row = next(r for r in briefing.rows if r.call_outcome == "contained")
    assert con_row.refill_drafts_pending == 1

    # Delivered via the reused sms_gateway outbound leg.
    assert len(sms.sent) == 1
    assert "briefing" in sms.sent[0][1].lower()
