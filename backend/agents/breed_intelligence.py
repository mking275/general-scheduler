"""
T022-T024 — BreedIntelligenceAgent (F018)
Analyses patient breed, age, and flags against the breed_protocols table
to return contextual clinical alerts for the vet.
"""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Optional


def _age_years(dob_str: str) -> float:
    """Compute age in fractional years from an ISO date string."""
    try:
        dob = date.fromisoformat(dob_str[:10])
        today = date.today()
        delta = today - dob
        return round(delta.days / 365.25, 2)
    except Exception:
        return 0.0


def _breed_matches(patient_breed: str, protocol_pattern: str) -> bool:
    """Case-insensitive substring match between patient breed and protocol pattern."""
    pattern = protocol_pattern.strip().lower()
    breed   = patient_breed.strip().lower()
    # Allow partial match (e.g. "Cavalier King Charles" matches "Cavalier King Charles Spaniel")
    return pattern in breed or breed in pattern


class BreedIntelligenceAgent:
    """
    T022: Load breed protocols from DB.
    T023: Match protocols to patient breed + age.
    T024: Return structured alerts with severity.
    """

    def __init__(self, db, log_fn=None):
        self._db = db
        self._log = log_fn or (lambda msg: None)

    def analyse(self, patient_id: str) -> dict:
        """
        Run breed intelligence analysis for a patient.
        Returns matched alerts with severity, title, detail, and age-gate status.
        """
        self._log(f"BREED INTELLIGENCE AGENT: Analysing patient {patient_id[:8]}")

        # Fetch patient
        patient = self._db.get_patient(patient_id)
        if not patient:
            self._log(f"BREED INTELLIGENCE AGENT: Patient {patient_id} not found")
            return {"patient_id": patient_id, "alerts": [], "error": "patient_not_found"}

        breed = patient.breed or ""
        age   = _age_years(patient.dob) if hasattr(patient, "dob") else 0.0

        # For raw dict (fallback)
        if isinstance(patient, dict):
            breed = patient.get("breed", "")
            age   = _age_years(patient.get("dob", ""))

        self._log(f"BREED INTELLIGENCE AGENT: {patient.name if hasattr(patient,'name') else patient.get('name','?')} — breed={breed!r}, age={age:.1f}y")

        # Load protocols
        protocols = self._db.get_breed_protocols()

        alerts = []
        for proto in protocols:
            if not _breed_matches(breed, proto.get("breed_pattern", "")):
                continue
            age_threshold = proto.get("age_threshold_years", 0) or 0
            age_gate_met = age >= age_threshold
            alert = {
                "protocol_id":  proto["id"],
                "flag_type":    proto.get("flag_type"),
                "title":        proto.get("title"),
                "detail":       proto.get("detail"),
                "severity":     proto.get("severity", "info"),
                "age_threshold_years": age_threshold,
                "patient_age_years": age,
                "age_gate_met": age_gate_met,
                "active": age_gate_met,
            }
            alerts.append(alert)
            severity = proto.get("severity", "info").upper()
            self._log(
                f"BREED INTELLIGENCE AGENT: [{severity}] {proto.get('title')} — "
                f"age_gate={'met' if age_gate_met else 'not yet'} ({age:.1f}y / {age_threshold}y)"
            )

        # Sort: critical first, then warning, then info; active alerts first
        _sev_order = {"critical": 0, "warning": 1, "info": 2}
        alerts.sort(key=lambda a: (_sev_order.get(a["severity"], 9), not a["active"]))

        patient_name = patient.name if hasattr(patient, "name") else patient.get("name", "")
        self._log(
            f"BREED INTELLIGENCE AGENT: Analysis complete — {len(alerts)} alert(s) for {patient_name}"
        )

        return {
            "patient_id":   patient_id,
            "patient_name": patient_name,
            "breed":        breed,
            "age_years":    age,
            "alerts_count": len(alerts),
            "alerts":       alerts,
        }
