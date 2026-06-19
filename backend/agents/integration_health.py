"""
Integration Health Agent  —  T009 (W-01 / W-02 fixes applied)

Responsibilities:
  - Encrypt / decrypt credentials using Fernet AES-128-CBC (cryptography lib)
  - Persist encryption key to backend/.vpma_key  (W-01)
  - Run simulated connectivity tests for each integration
  - Update integration_statuses table
  - Emit Verbose Log entries
"""

from __future__ import annotations

import json
import os
import time
import hmac
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet

# ── W-01: Key persistence ────────────────────────────────────────────────────

_KEY_PATH = Path(__file__).parent.parent / ".vpma_key"


def _load_or_create_key() -> bytes:
    if _KEY_PATH.exists():
        return _KEY_PATH.read_bytes().strip()
    key = Fernet.generate_key()
    _KEY_PATH.write_bytes(key)
    return key


_FERNET = Fernet(_load_or_create_key())


def encrypt(raw: str) -> str:
    return _FERNET.encrypt(raw.encode()).decode()


def decrypt(token: str) -> str:
    return _FERNET.decrypt(token.encode()).decode()


# ── Connectivity test stubs ───────────────────────────────────────────────────

_KNOWN_TEST_SECRETS: dict[str, str] = {
    "idexx":    "demo-idexx-secret",
    "antech":   "demo-antech-key",
    "heska":    "demo-heska-secret",
    "vetscan":  "demo-vetscan-device",
    "imaging":  "demo-imaging-secret",
    "twilio":   "demo-twilio-sid",
    "sendgrid": "demo-sendgrid-key",
    "stripe":   "demo-stripe-key",
    "ezyvet":   "demo-ezyvet-key",
}


def _simulate_connectivity(integration_id: str, creds: dict[str, str]) -> tuple[bool, int, str]:
    """
    Returns (success, latency_ms, error_message).
    For demo: any non-empty credential set passes.  'wrong' anywhere in a
    value simulates a bad credential.
    """
    t0 = time.monotonic()
    # Simulate a tiny network delay
    import random
    time.sleep(random.uniform(0.05, 0.18))
    latency_ms = int((time.monotonic() - t0) * 1000)

    if not creds:
        return False, latency_ms, "No credentials provided"

    for k, v in creds.items():
        if "wrong" in v.lower() or "bad" in v.lower() or "invalid" in v.lower():
            return False, latency_ms, f"{integration_id.upper()} returned 401 Unauthorized — check {k}"

    return True, latency_ms, ""


# ── Public agent function ─────────────────────────────────────────────────────

def run_connectivity_test(
    repo,
    clinic_id: str,
    integration_id: str,
    raw_credentials: dict[str, str],
    log_fn=None,
) -> dict:
    """
    1. Simulate connectivity test.
    2. On success: encrypt + save credentials, set status='connected'.
    3. On failure: do NOT save, set status='disconnected'.
    4. Upsert integration_statuses row.
    5. Emit verbose log entries.

    Returns status dict.
    """
    from ..models import IntegrationStatus

    success, latency_ms, error_msg = _simulate_connectivity(integration_id, raw_credentials)
    now = datetime.utcnow().isoformat()

    if success:
        # Encrypt and persist each credential key
        for key_name, raw_value in raw_credentials.items():
            encrypted = encrypt(raw_value)
            repo.save_integration_credential(clinic_id, integration_id, key_name, encrypted)

        status_val = "connected"
        if log_fn:
            log_fn(f"CREDENTIALS AGENT: {integration_id.upper()} configured · connectivity test passed")
    else:
        # Do NOT persist credentials on failure (spec: FR-INT-001)
        status_val = "disconnected"
        if log_fn:
            log_fn(f"CREDENTIALS AGENT: {integration_id.upper()} connectivity test FAILED — {error_msg}")

    status = IntegrationStatus(
        clinic_id=clinic_id,
        integration_id=integration_id,
        status=status_val,
        latency_ms=latency_ms,
        error_message=error_msg,
        last_checked_at=now,
    )
    repo.upsert_integration_status(status)

    return {
        "integration_id": integration_id,
        "status": status_val,
        "latency_ms": latency_ms,
        "error_message": error_msg,
        "last_checked_at": now,
    }


def mark_integration_degraded(
    repo,
    clinic_id: str,
    integration_id: str,
    error_msg: str,
    log_fn=None,
) -> None:
    """Called organically when any integration call fails during normal operation."""
    from ..models import IntegrationStatus

    now = datetime.utcnow().isoformat()
    status = IntegrationStatus(
        clinic_id=clinic_id,
        integration_id=integration_id,
        status="degraded",
        latency_ms=0,
        error_message=error_msg,
        last_checked_at=now,
    )
    repo.upsert_integration_status(status)
    if log_fn:
        log_fn(f"HEALTH AGENT: {integration_id.upper()} connection lost — {error_msg}")
