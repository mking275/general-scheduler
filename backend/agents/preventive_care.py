"""
T027-T029 — PreventiveCareAgent (F015)
Records vaccinations/treatments, computes next due dates, and identifies overdue care.
"""
from __future__ import annotations

import calendar
from datetime import date, datetime
from typing import Optional
from uuid import uuid4


def _add_months(d: date, months: int) -> date:
    """Reliably add N months to a date object."""
    y = d.year + (d.month - 1 + months) // 12
    m = (d.month - 1 + months) % 12 + 1
    day = min(d.day, calendar.monthrange(y, m)[1])
    return date(y, m, day)


class PreventiveCareAgent:
    """
    T027: Monitors care protocol compliance per patient.
    T028: record_care_event — saves administered care and computes next_due_date.
    T029: get_overdue_care — delegates to repository.
    """

    def __init__(self, db, log_fn=None):
        self._db = db
        self._log = log_fn or (lambda msg: None)

    def record_care_event(self, body: dict) -> dict:
        """
        T028: Record a care event and compute next_due_date from protocol interval.
        Required body fields: patient_id, protocol_id, administered_date
        Optional: timeblock_id, batch_number, administered_by
        """
        self._log("PREVENTIVE CARE AGENT: Recording care event")

        required = {"patient_id", "protocol_id", "administered_date"}
        missing = required - set(body.keys())
        if missing:
            return {"error": f"Missing fields: {missing}"}

        protocol = self._db.get_care_protocol(body["protocol_id"])
        if not protocol:
            return {"error": f"Protocol {body['protocol_id']} not found"}

        interval_months = int(protocol.get("interval_months", 12))
        admin_date = date.fromisoformat(body["administered_date"][:10])
        next_due   = _add_months(admin_date, interval_months)

        event = {
            "id":               str(uuid4()),
            "patient_id":       body["patient_id"],
            "protocol_id":      body["protocol_id"],
            "timeblock_id":     body.get("timeblock_id"),
            "administered_date": admin_date.isoformat(),
            "next_due_date":    next_due.isoformat(),
            "batch_number":     body.get("batch_number", ""),
            "administered_by":  body.get("administered_by", ""),
        }

        self._db.create_care_event(event)
        self._log(
            f"PREVENTIVE CARE AGENT: Recorded {protocol.get('protocol_name')} for patient {body['patient_id'][:8]} — "
            f"next due {next_due.isoformat()}"
        )

        return {
            **event,
            "protocol_name": protocol.get("protocol_name"),
            "interval_months": interval_months,
        }

    def get_overdue_summary(self) -> dict:
        """T029: Return overdue care items with a human-readable summary."""
        self._log("PREVENTIVE CARE AGENT: Checking for overdue care")
        items = self._db.get_overdue_care()
        self._log(f"PREVENTIVE CARE AGENT: {len(items)} overdue care item(s) found")
        return {
            "overdue_count": len(items),
            "items": items,
        }
