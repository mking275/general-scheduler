"""Phase 1 (Setup) verification — T001, T002, T003."""
import os

import pytest
import yaml

from backend.tests.voice.conftest import CONFIG_VOICE


# --- T001 ------------------------------------------------------------------
def test_t001_package_imports():
    import backend.voice  # noqa: F401
    import backend.voice.shims  # noqa: F401


# --- T002 ------------------------------------------------------------------
def test_t002_models_import_and_enums():
    from backend.models import (
        CallSession, CallTurn, CallTranscript, EscalationEvent,
        RefillRequestDraft, ClinicVoiceConfig, OnCallTarget, TriageProtocol,
        CallOutcome, GateDecision, VerificationState, EscalationTrigger,
        TransferOutcome, ModelProvider,
    )
    assert CallOutcome.BOOKED.value == "booked"
    assert {d.value for d in GateDecision} == {"advise", "propose", "do", "reject", "escalate"}
    assert VerificationState.SOFT_CONFIRMED.value == "soft_confirmed"
    assert EscalationTrigger.LOW_CONFIDENCE.value == "low_confidence"
    assert ModelProvider.GEMINI_LIVE.value == "gemini_live"


def test_t002_refill_status_admits_only_draft():
    from backend.models import RefillRequestDraft

    ok = RefillRequestDraft(call_session_id="c", party_id="p", patient_ref="Rex",
                            drug_name_asserted="apoquel")
    assert ok.status == "draft_vet_review"
    with pytest.raises(Exception):
        RefillRequestDraft(call_session_id="c", party_id="p", patient_ref="Rex",
                           drug_name_asserted="apoquel", status="auto_approved")


# --- T003 ------------------------------------------------------------------
def test_t003_disclosure_script():
    with open(os.path.join(CONFIG_VOICE, "disclosure_script.en.txt")) as f:
        text = f.read().lower()
    assert "ai" in text
    assert "recorded" in text or "transcribed" in text
    assert "emergency" in text


def test_t003_clinic_voice_config():
    with open(os.path.join(CONFIG_VOICE, "clinic_voice_config.goldsmith.yaml")) as f:
        cfg = yaml.safe_load(f)
    assert "after_hours_window" in cfg
    assert cfg["low_confidence_threshold"] == 0.6
    assert cfg["slo_latency_ms"] == 3000


def test_t003_triage_sample_unsigned():
    with open(os.path.join(CONFIG_VOICE, "triage_protocol.goldsmith.sample.yaml")) as f:
        proto = yaml.safe_load(f)
    assert proto["signed_by"] is None and proto["signed_at"] is None
    assert proto["slo"]["escalation_on_flag"] == 1.0


def test_t003_pricing_fixture():
    pricing_path = os.path.join(_pricing_dir(), "pricing.yml")
    with open(pricing_path) as f:
        pricing = yaml.safe_load(f)
    for prov in ("gemini_live", "openai_realtime"):
        p = pricing["providers"][prov]
        assert "audio_in_usd_per_min" in p
        assert "audio_out_usd_per_min" in p
        assert "text_usd_per_1k_tokens" in p


def _pricing_dir():
    import backend.voice
    return os.path.join(os.path.dirname(backend.voice.__file__), "config")
