"""Feature 009 — T012 ExtractionPort no-retention acceptance.

- the sim extraction adapter processes fixture content and retains ZERO raw
  source bytes/frames after the call returns (no-retention assertion);
- is_live() gates any real subprocessor connect;
- no live PII crosses the port in the build.
"""
from backend.envelope.extraction_port import ExtractionPort, SimExtractionPort
from backend.envelope import sim
from backend.tests.envelope.fixtures.ezyvet_synthetic_export import generate_practice_export


def test_sim_port_typechecks():
    assert isinstance(SimExtractionPort(), ExtractionPort)


def test_extract_retains_zero_raw_bytes():
    port = SimExtractionPort()
    exp = generate_practice_export("p1", seed=7, variant="complete")
    result = port.extract(exp.raw_bytes())
    assert "clients" in result.entities
    assert result.entities["clients"]["row_count"] > 0
    assert result.variant_hint == "complete_v1"
    # NO-RETENTION: nothing retained after the call returns
    assert port.retained_raw_count() == 0
    # repeated calls never accumulate retained content
    port.extract(exp.raw_bytes())
    assert port.retained_raw_count() == 0


def test_sim_port_never_connects():
    assert SimExtractionPort().is_connected() is False


def test_is_live_gates_subprocessor(monkeypatch):
    for k in ("ONBOARDING_LIVE", "ONBOARDING_VAULT_URL",
              "ONBOARDING_TRANSFER_CREDENTIAL", "GEMINI_API_KEY", "GOOGLE_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    # default: sim port, no live connect
    assert sim.is_live() is False
    assert isinstance(sim.resolve_extraction_port(), SimExtractionPort)


def test_corrupt_export_fails_specifically():
    port = SimExtractionPort()
    result = port.extract(b"not a zip at all")
    assert result.corrupt is True
    assert result.error
    assert result.entities == {}
