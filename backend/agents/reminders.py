"""
T008-T014 — ReminderAgent (F013)
Sends appointment reminders, tracks confirmation status, and manages reschedule requests.
Implements the 4-state confirmation flow: not_sent → sent → confirmed | reschedule_requested.

SMS is dispatched via sms_gateway.SMSGateway which uses Twilio when credentials are
present in .env (TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN / TWILIO_FROM_NUMBER).
When no credentials are set, the gateway falls back to simulation mode automatically.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import List, Optional

# Gateway singleton — handles live Twilio or simulation transparently
try:
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from sms_gateway import sms as _sms_gateway
except Exception:
    _sms_gateway = None  # type: ignore


# ── Confidence thresholds (SC-P3-002: confirmation rate >80% in demo) ──────
_REMINDER_WINDOW_HOURS_DEFAULT = 48   # send reminder N hours before appointment


class ReminderAgent:
    """
    Scans upcoming appointments and sends reminders within the look-ahead window.
    Updates confirmation_status on each timeblock.
    Emits verbose log via log_agent_step() for agent-driven UI transparency.
    """

    def __init__(self, db, log_fn=None, window_hours: int = _REMINDER_WINDOW_HOURS_DEFAULT):
        self._db = db
        self._log = log_fn or (lambda msg: None)
        self._window_hours = window_hours

    # ------------------------------------------------------------------ #
    #  Public API
    # ------------------------------------------------------------------ #

    def run_reminder_sweep(self, clinic_id: Optional[str] = None) -> dict:
        """
        T010: Main agent sweep — finds appointments due for reminders and dispatches them.
        Returns summary of actions taken.
        """
        self._log("REMINDER AGENT: Starting reminder sweep")
        now = datetime.utcnow()
        cutoff = (now + timedelta(hours=self._window_hours)).isoformat()

        # Pull all 'scheduled' timeblocks within the window that haven't been sent
        with self._db._get_conn() as conn:
            if clinic_id:
                rows = conn.execute(
                    """SELECT t.id, t.start_time, t.patient_id, t.confirmation_status,
                              p.name as patient_name, o.name as owner_name, o.phone, o.email,
                              t.job_id, t.clinic_id
                       FROM timeblocks t
                       LEFT JOIN patients p ON p.id = t.patient_id
                       LEFT JOIN owners o ON o.id = p.owner_id
                       WHERE t.status = 'scheduled'
                         AND t.confirmation_status IN ('not_sent', NULL)
                         AND t.start_time <= ?
                         AND t.start_time > ?
                         AND t.clinic_id = ?""",
                    (cutoff, now.isoformat(), clinic_id)
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT t.id, t.start_time, t.patient_id, t.confirmation_status,
                              p.name as patient_name, o.name as owner_name, o.phone, o.email,
                              t.job_id, t.clinic_id
                       FROM timeblocks t
                       LEFT JOIN patients p ON p.id = t.patient_id
                       LEFT JOIN owners o ON o.id = p.owner_id
                       WHERE t.status = 'scheduled'
                         AND (t.confirmation_status IS NULL OR t.confirmation_status = 'not_sent')
                         AND t.start_time <= ?
                         AND t.start_time > ?""",
                    (cutoff, now.isoformat())
                ).fetchall()

        appointments = [dict(r) for r in rows]
        self._log(f"REMINDER AGENT: Found {len(appointments)} appointment(s) needing reminders")

        sent = []
        skipped = []
        for appt in appointments:
            tb_id = appt["id"]
            patient_name = appt.get("patient_name") or "your pet"
            owner_name   = appt.get("owner_name") or ""
            start_time   = appt.get("start_time", "")

            # Resolve procedure from job
            procedure = "appointment"
            try:
                with self._db._get_conn() as conn:
                    job_row = conn.execute("SELECT data FROM jobs WHERE id=?", (appt["job_id"],)).fetchone()
                if job_row:
                    job_data = json.loads(job_row["data"])
                    procedure = job_data.get("procedure") or job_data.get("required_skills", ["appointment"])[0]
            except Exception:
                pass

            # Determine channel — prefer SMS if phone available
            phone  = appt.get("phone") or ""
            channel = "sms" if phone else "email"

            # ── Dispatch via real gateway (Twilio) or simulation fallback ──
            if channel == "sms" and _sms_gateway:
                receipt_obj = _sms_gateway.send_reminder(
                    to=phone,
                    owner_name=owner_name,
                    patient_name=patient_name,
                    procedure=procedure,
                    appt_date=start_time[:10],
                    appt_time=start_time[11:16],
                )
                receipt = {
                    **receipt_obj.to_dict(),
                    "timeblock_id": tb_id,
                    "recipient_name": owner_name or patient_name,
                }
                mode = "[LIVE]" if receipt_obj.simulated is False and not receipt_obj.error else "[SIMULATED]"
            else:
                # Email path — placeholder until SendGrid is wired
                from uuid import uuid4
                receipt = {
                    "dispatch_id": str(uuid4()),
                    "timeblock_id": tb_id,
                    "channel": "email",
                    "recipient_name": owner_name or patient_name,
                    "status": "simulated",
                    "sent_at": datetime.utcnow().isoformat(),
                    "simulated": True,
                }
                mode = "[SIMULATED-EMAIL]"

            self._log(
                f"REMINDER AGENT {mode}: Sent {channel.upper()} reminder to "
                f"{owner_name or patient_name} for {patient_name} ({procedure}) "
                f"on {start_time[:10]} [tb={tb_id[:8]}]"
            )

            # Mark as sent (unconfirmed) — confirmation comes via /api/reminders/{id}/confirm
            self._db.update_confirmation_status(tb_id, "sent", receipt.get("sent_at", datetime.utcnow().isoformat()))
            sent.append({"timeblock_id": tb_id, "receipt": receipt})

        self._log(
            f"REMINDER AGENT: Sweep complete — {len(sent)} sent, {len(skipped)} skipped"
        )
        return {"sent_count": len(sent), "skipped_count": len(skipped), "sent": sent}

    def confirm_appointment(self, timeblock_id: str, send_ack: bool = True) -> dict:
        """
        T012: Mark an appointment as confirmed by owner.
        Optionally sends a confirmation acknowledgement SMS back to the owner.
        """
        ts = datetime.utcnow().isoformat()
        self._db.update_confirmation_status(timeblock_id, "confirmed", ts)
        self._log(f"REMINDER AGENT: Appointment {timeblock_id[:8]} confirmed at {ts}")

        # Send "confirmed ✅" ack back to owner via SMS if gateway available
        if send_ack and _sms_gateway:
            try:
                with self._db._get_conn() as conn:
                    row = conn.execute(
                        """SELECT t.start_time, p.name as patient_name, o.phone, o.name as owner_name
                           FROM timeblocks t
                           LEFT JOIN patients p ON p.id = t.patient_id
                           LEFT JOIN owners o ON o.id = p.owner_id
                           WHERE t.id = ?""",
                        (timeblock_id,)
                    ).fetchone()
                if row and row["phone"]:
                    _sms_gateway.send_confirmation_ack(
                        to=row["phone"],
                        patient_name=row["patient_name"] or "your pet",
                        appt_date=row["start_time"][:10],
                        appt_time=row["start_time"][11:16],
                    )
                    self._log(f"REMINDER AGENT: Confirmation ack sent to {row['owner_name']} [tb={timeblock_id[:8]}]")
            except Exception as exc:
                self._log(f"REMINDER AGENT: Ack send failed (non-critical): {exc}")

        return {"timeblock_id": timeblock_id, "confirmation_status": "confirmed", "confirmed_at": ts}

    def request_reschedule(self, timeblock_id: str) -> dict:
        """
        T013: Owner requested reschedule — flag for front desk.
        """
        ts = datetime.utcnow().isoformat()
        self._db.update_confirmation_status(timeblock_id, "reschedule_requested")
        self._log(
            f"REMINDER AGENT: Reschedule requested for {timeblock_id[:8]} — added to action queue"
        )
        return {
            "timeblock_id": timeblock_id,
            "confirmation_status": "reschedule_requested",
            "flagged_at": ts,
        }

    def get_confirmation_status(self, timeblock_id: str) -> dict:
        """
        T014: Return current confirmation state for a timeblock.
        """
        with self._db._get_conn() as conn:
            row = conn.execute(
                "SELECT id, confirmation_status, confirmed_at, reminder_sent_at FROM timeblocks WHERE id=?",
                (timeblock_id,)
            ).fetchone()
        if not row:
            return {"error": "timeblock not found"}
        return dict(row)
