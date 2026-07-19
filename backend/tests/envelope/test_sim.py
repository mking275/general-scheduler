"""Feature 009 — T008 dual-mode env resolver acceptance.

- is_live()==False with no creds;
- the resolver returns the sim vault + sim extraction adapters by default;
- ONBOARDING_LIVE=true selects the live seams (asserted by construction, not
  exercised).
"""
import pytest

from backend.envelope import sim
from backend.envelope.sim import (
    LiveExtractionSeam, LiveVaultSeam, SeamMode, is_live, resolve_extraction_port,
    resolve_mode, resolve_vault,
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for k in ("ONBOARDING_LIVE", "ONBOARDING_VAULT_URL", "ONBOARDING_TRANSFER_CREDENTIAL",
              "GEMINI_API_KEY", "GOOGLE_API_KEY"):
        monkeypatch.delenv(k, raising=False)


def test_is_live_false_with_no_creds():
    assert is_live() is False
    assert resolve_mode() == SeamMode.SIM


def test_resolver_returns_sim_seams_by_default(tmp_path):
    from backend.envelope.vault import SimVault
    from backend.envelope.extraction_port import SimExtractionPort
    v = resolve_vault(root=str(tmp_path))
    x = resolve_extraction_port()
    assert isinstance(v, SimVault)
    assert isinstance(x, SimExtractionPort)


def test_force_flag_selects_live_seams_by_construction(monkeypatch):
    monkeypatch.setenv("ONBOARDING_LIVE", "true")
    assert is_live() is True
    assert resolve_mode() == SeamMode.LIVE
    v = resolve_vault()
    x = resolve_extraction_port()
    assert isinstance(v, LiveVaultSeam)
    assert isinstance(x, LiveExtractionSeam)
    # selected by construction, NOT exercised — any call raises
    with pytest.raises(RuntimeError):
        v.write(b"x")


def test_force_false_overrides_cred_autodetect(monkeypatch):
    monkeypatch.setenv("ONBOARDING_VAULT_URL", "https://vault")
    monkeypatch.setenv("ONBOARDING_TRANSFER_CREDENTIAL", "secret")
    monkeypatch.setenv("GEMINI_API_KEY", "key")
    monkeypatch.setenv("ONBOARDING_LIVE", "false")
    assert is_live() is False
