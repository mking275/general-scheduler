"""Feature 011 — T005 entity_ref mapper (research D2).

PIMS stable-id -> ``{type}:{stable_id}`` keys. Display names live in the fact
PAYLOAD, **never in the key** — names-as-keys break on surname collisions, PIMS
name edits, and put PII in every log line and index (the reason VetAgent does
not consume Thoth's conversation-derived ``worker:juan_garcia`` name-keys).

Namespaces (board-confirmed):
  household:vah_*   (synthesized — VetAgent household)
  client:ezyvet_c*  (ezyVet client / party stable id)
  patient:ezyvet_p* (ezyVet patient stable id)
  staff:*           (staff/login id)
  clinic:*          (tenant)
"""
from __future__ import annotations

import hashlib
import re

PIMS_PREFIX = "ezyvet"


def _digits(raw: str) -> str:
    """Extract the stable numeric core of a PIMS id, tolerant of a leading
    type letter (``c123`` -> ``123``) or an already-namespaced value."""
    s = str(raw).strip()
    # tolerate an already-built ref being passed back in
    if ":" in s:
        s = s.split(":", 1)[1]
    if s.startswith(f"{PIMS_PREFIX}_"):
        s = s[len(PIMS_PREFIX) + 1:]
    s = re.sub(r"^[a-zA-Z]+", "", s)  # strip a leading c/p type letter
    return s or str(raw).strip()


def client_ref(pims_client_id: str) -> str:
    return f"client:{PIMS_PREFIX}_c{_digits(pims_client_id)}"


def patient_ref(pims_patient_id: str) -> str:
    return f"patient:{PIMS_PREFIX}_p{_digits(pims_patient_id)}"


def staff_ref(staff_user_id: str) -> str:
    return f"staff:{str(staff_user_id).strip()}"


def clinic_ref(clinic_id: str) -> str:
    return f"clinic:{str(clinic_id).strip()}"


def synth_household_ref(seed: str) -> str:
    """Synthesize a STABLE ``household:vah_*`` key from a deterministic seed
    (e.g. the source PIMS client id). Same seed -> same household key, so the
    migration and any red-team replay are reproducible. No name enters the key."""
    token = hashlib.sha1(str(seed).encode("utf-8")).hexdigest()[:12]
    return f"household:vah_{token}"


def parse(entity_ref: str) -> tuple[str, str]:
    """Split ``{type}:{stable_id}`` -> ``(type, stable_id)``."""
    if ":" not in entity_ref:
        raise ValueError(f"not an entity_ref: {entity_ref!r}")
    t, sid = entity_ref.split(":", 1)
    return t, sid


def ref_type(entity_ref: str) -> str:
    return parse(entity_ref)[0]
