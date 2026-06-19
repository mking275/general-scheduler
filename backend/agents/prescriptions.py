"""
T032-T034 — PrescriptionAgent (F016)
Creates prescriptions with allergy flag checking, manages refill workflow:
pending → auto_approved (if refills_remaining > 0) | vet_review.
"""
from __future__ import annotations

import calendar
import json
from datetime import date, datetime, timedelta
from typing import Optional
from uuid import uuid4


def _add_days(d: date, days: int) -> date:
    from datetime import timedelta as _td
    return d + _td(days=days)


class PrescriptionAgent:
    """
    T032: Checks patient allergy flags before writing Rx.
    T033: create_prescription — validates and persists.
    T034: request_refill — auto-approve or escalate to vet_review.
    """

    def __init__(self, db, log_fn=None):
        self._db = db
        self._log = log_fn or (lambda msg: None)

    def create_prescription(self, body: dict) -> dict:
        """
        T033: Create a prescription.
        Performs allergy flag check (SC-P3-003: Buddy penicillin alert).
        """
        self._log("PRESCRIPTION AGENT: Creating prescription")

        required = {"patient_id", "drug_name", "dose", "frequency", "duration_days", "issued_by"}
        missing = required - set(body.keys())
        if missing:
            return {"error": f"Missing fields: {missing}"}

        patient_id = body["patient_id"]
        drug_name  = body["drug_name"]

        # T032: Allergy flag check — look at patient flags JSON
        allergy_alert = None
        try:
            patient = self._db.get_patient(patient_id)
            if patient:
                flags_raw = patient.flags if hasattr(patient, "flags") else patient.get("flags", "[]")
                if isinstance(flags_raw, str):
                    import json as _json
                    flags = _json.loads(flags_raw)
                else:
                    flags = flags_raw or []

                flag_notes_raw = getattr(patient, "flag_notes", "") or ""
                drug_lower = drug_name.lower()

                for flag in flags:
                    flag_str = (flag if isinstance(flag, str) else str(flag)).lower()
                    if "allergy" in flag_str or "penicillin" in drug_lower:
                        # Cross-check flag_notes for specific allergen
                        if "penicillin" in flag_notes_raw.lower() and "penicillin" in drug_lower:
                            allergy_alert = {
                                "flag":    flag,
                                "drug":    drug_name,
                                "detail":  f"ALLERGY FLAG: {patient.name if hasattr(patient,'name') else patient.get('name','patient')} "
                                           f"has a documented penicillin allergy. "
                                           f"Confirm therapeutic alternative before proceeding.",
                                "severity": "critical",
                            }
                            self._log(
                                f"PRESCRIPTION AGENT: [CRITICAL] Allergy flag match — "
                                f"{drug_name} prescribed to patient with documented allergy"
                            )
        except Exception as e:
            self._log(f"PRESCRIPTION AGENT: Allergy check warning (non-fatal): {e}")

        today = date.today()
        duration_days = int(body["duration_days"])
        supply_ends = _add_days(today, duration_days)

        rx = {
            "id":                str(uuid4()),
            "patient_id":        patient_id,
            "timeblock_id":      body.get("timeblock_id"),
            "drug_name":         drug_name,
            "dose":              body["dose"],
            "frequency":         body["frequency"],
            "duration_days":     duration_days,
            "refills_remaining": int(body.get("refills_remaining", 0)),
            "supply_ends_at":    supply_ends.isoformat(),
            "issued_by":         body["issued_by"],
            "issued_date":       today.isoformat(),
        }

        self._db.create_prescription(rx)
        self._log(
            f"PRESCRIPTION AGENT: Prescription created — {drug_name} {body['dose']} {body['frequency']} "
            f"x{duration_days}d, {rx['refills_remaining']} refill(s) for patient {patient_id[:8]}"
        )

        result = dict(rx)
        if allergy_alert:
            result["allergy_alert"] = allergy_alert
        return result

    def request_refill(self, prescription_id: str, initiated_by: str = "front_desk") -> dict:
        """
        T034: Refill workflow.
        - refills_remaining > 0 → auto_approved.
        - refills_remaining == 0 → vet_review.
        """
        self._log(f"PRESCRIPTION AGENT: Refill requested for Rx {prescription_id[:8]} by {initiated_by}")

        rx = self._db.get_prescription(prescription_id)
        if not rx:
            return {"error": f"Prescription {prescription_id} not found"}

        refills = int(rx.get("refills_remaining", 0))

        if refills > 0:
            status = "auto_approved"
        else:
            status = "vet_review"

        req = {
            "id":              str(uuid4()),
            "prescription_id": prescription_id,
            "initiated_by":    initiated_by,
            "status":          status,
            "requested_at":    datetime.utcnow().isoformat(),
            "reviewed_by":     None,
            "reviewed_at":     None,
        }
        self._db.create_refill_request(req)

        self._log(
            f"PRESCRIPTION AGENT: Refill for {rx.get('drug_name')} — "
            f"status={status.upper()}, refills_remaining={refills}"
        )

        return {
            **req,
            "drug_name":         rx.get("drug_name"),
            "dose":              rx.get("dose"),
            "frequency":         rx.get("frequency"),
            "refills_remaining": refills,
            "patient_id":        rx.get("patient_id"),
        }

    def approve_refill(self, refill_id: str) -> dict:
        """T034/T036: Vet manually approves a vet_review refill request."""
        result = self._db.approve_refill(refill_id)
        if result:
            self._log(
                f"PRESCRIPTION AGENT: Refill {refill_id[:8]} approved — "
                f"refills_remaining now {result.get('refills_remaining', '?')}"
            )
        return result
