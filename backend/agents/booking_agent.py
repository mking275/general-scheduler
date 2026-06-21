"""
booking_agent.py — Booking confirmation, cancellation, and hold management.

Responsibilities:
  - Orchestrate the atomic SQLite transaction that converts a soft-hold into a
    confirmed timeblock, booking_token, and intake_token.
  - Arm the T-48h and T-2h reminder pipeline via existing ReminderAgent.
  - Expose cancel_booking for POST /public/bookings/{token}/cancel.
  - Compute flexibility_score for waitlist entries.

Does NOT do: AI slot ranking (Phase 2), risk scoring (Phase 2), SMS/email
delivery (delegated to intake_delivery_agent.py).

Logging prefix: VERA (Booking):
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4

log = logging.getLogger(__name__)

# ── Lifecycle states in order ───────────────────────────────────────────────
LIFECYCLE_STATES = [
    ("booked",          "Appointment Confirmed"),
    ("intake_sent",     "Pre-Visit Form Sent"),
    ("intake_complete", "Pre-Visit Form Complete"),
    ("confirmed",       "Appointment Confirmed"),
    ("in_progress",     "In Progress"),
    ("complete",        "Visit Complete"),
    ("follow_up_sent",  "Follow-Up Sent"),
]

# ── Valid urgency values ────────────────────────────────────────────────────
VALID_URGENCY = {"wellness", "routine", "urgent", "emergency"}

# ── Portal base URL (hardcoded for Phase 1; env-configurable in Phase 2) ───
PORTAL_BASE_URL = "https://book.vpma.app"


class BookingAgent:
    def __init__(self, db, log_fn=None):
        """
        Args:
            db:     Repository instance (InMemoryRepository from repository.py).
            log_fn: Callable(str) for verbose log entries; defaults to no-op.
        """
        self._db = db
        self._log = log_fn or (lambda msg: None)

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def confirm_booking(
        self,
        session_token: str,
        hold_id: str,
        patient_id: str,
        appointment_type_id: str,
        urgency: str,
        notes: Optional[str],
        sms_consent: bool,
    ) -> dict:
        """
        Atomically confirm a booking from a soft-hold.

        Steps:
          1. Validate hold exists, belongs to session, not expired.
          2. Final slot availability double-check.
          3. Create timeblock, booking_token, intake_token in one SQLite transaction.
          4. Delete soft-hold and increment owner booking count.
          5. Return booking_token_id and intake_token_id.

        Returns:
            dict with keys: booking_token_id, intake_token_id, timeblock_id,
                            start_datetime, end_datetime, resource_id, clinic_id,
                            owner_id

        Raises:
            ValueError: If hold not found, expired, or slot taken.
        """
        now = datetime.utcnow()

        # Step 1 — Validate hold
        hold = self._db.get_slot_hold(hold_id)
        if not hold:
            raise ValueError("Hold not found")
        if hold.get("session_token") != session_token:
            raise ValueError("Hold does not belong to this session")
        if hold.get("expires_at", "") < now.isoformat():
            raise ValueError("Hold expired")

        session = self._db.get_session(session_token)
        if not session:
            raise ValueError("Session invalid")
        owner_id = session.get("owner_id")
        if not owner_id:
            raise ValueError("Session has no associated owner")

        resource_id = hold["resource_id"]
        start_dt = hold["start_datetime"]
        end_dt = hold["end_datetime"]
        clinic_id = hold["clinic_id"]

        # Step 2 — Final availability check
        available = self._db.check_slot_available(
            resource_id, start_dt, end_dt,
            exclude_session_token=session_token
        )
        if not available:
            raise ValueError("Slot no longer available — possible double-booking")

        # Trim notes
        if notes:
            notes = notes[:300]

        # Step 3 — Create timeblock, booking_token, intake_token
        timeblock_id = str(uuid4())
        booking_token_id = str(uuid4())
        intake_token_id = str(uuid4())
        job_id = str(uuid4())
        now_iso = now.isoformat()

        try:
            start_dt_obj = datetime.fromisoformat(start_dt)
        except (ValueError, TypeError):
            start_dt_obj = now

        booking_expires_at = (start_dt_obj + timedelta(days=30)).isoformat()
        intake_expires_at = (now + timedelta(days=7)).isoformat()

        # Create timeblock
        from ..repository import _get_conn as _gc
        import sqlite3
        with _gc() as conn:
            try:
                conn.execute("BEGIN")

                conn.execute("""
                    INSERT INTO timeblocks
                    (id, job_id, resource_ids, start_time, end_time, patient_id,
                     intake_status, status, clinic_id, source, urgency,
                     client_notes, appointment_type_id)
                    VALUES (?,?,?,?,?,?,'not_started','scheduled',?,
                            'online_portal',?,?,?)
                """, (
                    timeblock_id, job_id,
                    json.dumps([resource_id]),
                    start_dt, end_dt, patient_id,
                    clinic_id, urgency, notes or "", appointment_type_id,
                ))

                # Booking token
                conn.execute("""
                    INSERT INTO booking_tokens
                    (token, timeblock_id, owner_id, clinic_id, created_at, expires_at)
                    VALUES (?,?,?,?,?,?)
                """, (booking_token_id, timeblock_id, owner_id, clinic_id,
                      now_iso, booking_expires_at))

                # Intake token
                conn.execute("""
                    INSERT INTO intake_tokens
                    (token, timeblock_id, owner_id, appointment_type, used,
                     created_at, expires_at)
                    VALUES (?,?,?,?,0,?,?)
                """, (intake_token_id, timeblock_id, owner_id,
                      appointment_type_id, now_iso, intake_expires_at))

                # Link tokens to timeblock
                conn.execute("""
                    UPDATE timeblocks
                    SET intake_token_id=?, booking_token_id=?
                    WHERE id=?
                """, (intake_token_id, booking_token_id, timeblock_id))

                # Update session
                conn.execute("""
                    UPDATE owner_sessions
                    SET last_active_at=?
                    WHERE token=?
                """, (now_iso, session_token))

                # Delete soft-hold
                conn.execute("DELETE FROM slot_holds WHERE id=?", (hold_id,))

                # Increment owner booking count
                conn.execute("""
                    UPDATE owners SET booking_count = COALESCE(booking_count, 0) + 1
                    WHERE id=?
                """, (owner_id,))

                conn.execute("COMMIT")
            except sqlite3.IntegrityError as exc:
                conn.execute("ROLLBACK")
                raise ValueError(f"Double-booking conflict: {exc}") from exc
            except Exception as exc:
                conn.execute("ROLLBACK")
                raise ValueError(f"Transaction failed: {exc}") from exc

        self._log(
            f"VERA (Booking): booking_confirmed timeblock={timeblock_id[:8]} "
            f"token={booking_token_id[:8]} clinic={clinic_id[:8]} owner={owner_id[:8]}"
        )

        return {
            "booking_token_id": booking_token_id,
            "intake_token_id": intake_token_id,
            "timeblock_id": timeblock_id,
            "start_datetime": start_dt,
            "end_datetime": end_dt,
            "resource_id": resource_id,
            "clinic_id": clinic_id,
            "owner_id": owner_id,
        }

    def arm_reminders(
        self,
        timeblock_id: str,
        booking_token_id: str,
        owner_id: str,
        appointment_datetime: datetime,
    ) -> None:
        """
        Arm T-48h and T-2h SMS reminders via the existing ReminderAgent.

        This is called as a BackgroundTask after confirm_booking. Failures are
        logged but not raised so they don't affect the HTTP response.
        """
        try:
            from .reminders import ReminderAgent
            reminder_agent = ReminderAgent(self._db, log_fn=self._log)

            t48 = appointment_datetime - timedelta(hours=48)
            t2 = appointment_datetime - timedelta(hours=2)

            for send_at_dt, label in [(t48, "T-48h"), (t2, "T-2h")]:
                if send_at_dt > datetime.utcnow():
                    reminder_agent.schedule_reminder(
                        timeblock_id=timeblock_id,
                        owner_id=owner_id,
                        send_at=send_at_dt.isoformat(),
                        label=label,
                    )
                    self._log(
                        f"VERA (Booking): reminder armed {label} "
                        f"send_at={send_at_dt.isoformat()} tb={timeblock_id[:8]}"
                    )
        except Exception as exc:
            self._log(f"VERA (Booking): reminder arm failed — {exc}")

    def cancel_booking(
        self,
        booking_token_id: str,
        reason: str,
        notes: Optional[str] = None,
    ) -> dict:
        """
        Cancel a confirmed booking.

        Steps:
          1. Validate booking token exists.
          2. Mark the linked timeblock status='cancelled'.
          3. Log cancellation.

        Returns:
            dict with cancelled booking info.

        Raises:
            ValueError: If token not found.
        """
        token_row = self._db.get_booking_token(booking_token_id)
        if not token_row:
            raise ValueError("Booking token not found")

        timeblock_id = token_row["timeblock_id"]
        from ..repository import _get_conn as _gc
        with _gc() as conn:
            conn.execute(
                "UPDATE timeblocks SET status='cancelled' WHERE id=?",
                (timeblock_id,)
            )

        self._log(
            f"VERA (Booking): booking_cancelled token={booking_token_id[:8]} "
            f"reason={reason}"
        )

        return {
            "booking_token_id": booking_token_id,
            "timeblock_id": timeblock_id,
            "status": "cancelled",
            "cancelled_reason": reason,
            "cancelled_notes": notes,
        }

    # ------------------------------------------------------------------ #
    #  Lifecycle Builder                                                   #
    # ------------------------------------------------------------------ #

    @staticmethod
    def build_lifecycle(current_state: str) -> list[dict]:
        """
        Return the lifecycle array for BookingStatusResponse.

        States before and including current_state are marked completed=True.
        """
        state_order = [s for s, _ in LIFECYCLE_STATES]
        try:
            current_idx = state_order.index(current_state)
        except ValueError:
            current_idx = 0

        lifecycle = []
        for i, (state, label) in enumerate(LIFECYCLE_STATES):
            lifecycle.append({
                "state": state,
                "label": label,
                "completed": i <= current_idx,
                "completed_at": None,   # Phase 2: populate from audit log
            })
        return lifecycle

    # ------------------------------------------------------------------ #
    #  Waitlist Helpers                                                    #
    # ------------------------------------------------------------------ #

    @staticmethod
    def compute_flexibility_score(time_preferences: list[str], urgency: str) -> float:
        """
        Compute a numeric flexibility score for waitlist ordering.
        Higher = more flexible = lower priority for urgent slots.
        """
        pref_score = len(time_preferences)  # more prefs = more flexible
        urgency_map = {"asap": 0, "urgent": 1, "routine": 2, "wellness": 3}
        urgency_weight = urgency_map.get(urgency, 2)
        return float(pref_score + urgency_weight)
