"""T006 inbound dual-mode + simulator verification (zero network)."""
import os

from backend.models import InboundMessage
from backend.relationship.inbound_sim import InboundSimulator


def test_t006_is_live_false_with_no_creds(monkeypatch):
    for k in ("INBOUND_LIVE", "TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_FROM_NUMBER"):
        monkeypatch.delenv(k, raising=False)
    sim = InboundSimulator()
    assert sim.is_live() is False


def test_t006_force_flag(monkeypatch):
    monkeypatch.setenv("INBOUND_LIVE", "true")
    assert InboundSimulator().is_live() is True
    monkeypatch.setenv("INBOUND_LIVE", "false")
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "x")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "y")
    monkeypatch.setenv("TWILIO_FROM_NUMBER", "z")
    assert InboundSimulator().is_live() is False   # force wins over creds


def test_t006_harness_posts_through_seam_no_network(monkeypatch):
    monkeypatch.delenv("INBOUND_LIVE", raising=False)
    seen = []
    sim = InboundSimulator(handler=lambda m: seen.append(m) or "handled")
    msg = InboundMessage(clinic_id="c1", from_identifier_normalized="5551110001",
                         body="STOP")
    result = sim.post(msg)
    assert result == "handled"
    assert seen == [msg]
    assert sim.received == [msg]     # captured in the sim seam, no network call
