"""Feature 009 — T008 dual-mode env resolver.

Mirrors ``backend/sms_gateway.py`` / ``backend/voice/sim.py`` auto-detect: an
``ONBOARDING_LIVE`` force flag plus credential presence decides ``is_live()``.
With no credentials the whole envelope stack runs in **simulation** — zero live
subprocessor / secure-transfer / real-PII calls.

Two seams a live intake slots behind:

  * **vault** — sim encrypted-at-rest store (``vault.SimVault``) vs the live
    clinic-owned vault / secure-file-transfer intake.
  * **extraction subprocessor** — sim no-retention stub
    (``extraction_port.SimExtractionPort``) vs the live DPA'd Gemini
    subprocessor.

The live seams are selected **by construction** when ``ONBOARDING_LIVE=true``;
they are never *exercised* in this build (the live flip + DPA confirmation is
counsel-gated Pilot-Activation).
"""
from __future__ import annotations

import logging
import os
from enum import Enum
from typing import Any, Optional

try:  # load .env like sms_gateway does (no-op if python-dotenv absent)
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))
except ImportError:
    pass

logger = logging.getLogger("vpma.envelope.sim")


class SeamMode(str, Enum):
    SIM = "sim"
    LIVE = "live"


def is_live() -> bool:
    """True only if the live secure-transfer + extraction-subprocessor
    credentials are present (or ``ONBOARDING_LIVE=true`` forces it). Defaults to
    False -> simulation."""
    force = os.getenv("ONBOARDING_LIVE", "").strip().lower()
    if force == "false":
        return False
    if force == "true":
        return True
    # Auto-detect: need a secure-transfer endpoint AND an extraction-model key.
    transfer_ok = bool(
        os.getenv("ONBOARDING_VAULT_URL", "").strip()
        and os.getenv("ONBOARDING_TRANSFER_CREDENTIAL", "").strip()
    )
    model_ok = bool(
        os.getenv("GEMINI_API_KEY", "").strip()
        or os.getenv("GOOGLE_API_KEY", "").strip()
    )
    live = transfer_ok and model_ok
    if not live:
        logger.warning(
            "ENVELOPE: SIMULATION mode — no live secure-transfer/extraction "
            "credentials found. Set ONBOARDING_VAULT_URL + "
            "ONBOARDING_TRANSFER_CREDENTIAL + GEMINI_API_KEY (or "
            "ONBOARDING_LIVE=true) for live (counsel-gated Pilot-Activation)."
        )
    return live


def resolve_mode() -> SeamMode:
    return SeamMode.LIVE if is_live() else SeamMode.SIM


# --------------------------------------------------------------------------- #
#  Live seam placeholders — selected by construction, NEVER exercised in build.
#  Any method call raises: the live flip is counsel-gated Pilot-Activation.
# --------------------------------------------------------------------------- #
class _LiveSeamNotActivated(RuntimeError):
    pass


class LiveVaultSeam:
    """Placeholder for the live clinic-owned vault + secure-file-transfer
    intake. Constructing it is the 'live selected by construction' assertion;
    calling it raises until the counsel-gated Pilot-Activation flip."""
    mode = SeamMode.LIVE

    def __getattr__(self, name: str):
        raise _LiveSeamNotActivated(
            "live vault seam not activated in this build (Pilot-Activation)"
        )


class LiveExtractionSeam:
    """Placeholder for the live DPA'd Gemini extraction subprocessor."""
    mode = SeamMode.LIVE

    def __getattr__(self, name: str):
        raise _LiveSeamNotActivated(
            "live extraction seam not activated in this build (Pilot-Activation)"
        )


# --------------------------------------------------------------------------- #
#  Seam resolvers
# --------------------------------------------------------------------------- #
def resolve_vault(root: Optional[str] = None, **kwargs) -> Any:
    """Return the vault seam: the sim encrypted-at-rest store by default, the
    live clinic-owned vault when ``ONBOARDING_LIVE=true``."""
    if is_live():
        return LiveVaultSeam()
    from backend.envelope.vault import SimVault
    return SimVault(root=root, **kwargs)


def resolve_extraction_port(**kwargs) -> Any:
    """Return the extraction seam: the sim no-retention stub by default, the
    live DPA'd Gemini subprocessor when ``ONBOARDING_LIVE=true``."""
    if is_live():
        return LiveExtractionSeam()
    from backend.envelope.extraction_port import SimExtractionPort
    return SimExtractionPort(**kwargs)
