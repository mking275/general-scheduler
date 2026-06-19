"""
T016-T019 — WaitlistAgent (F014)
Matches waitlisted patients to cancelled/open slots and issues slot offers.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4


_URGENCY_RANK = {"asap": 0, "within_week": 1, "flexible": 2}


def _urgency_sort_key(entry: dict) -> tuple:
    urgency = entry.get("urgency", "flexible")
    join_date = entry.get("join_date", "")
    return (_URGENCY_RANK.get(urgency, 9), join_date)


class WaitlistAgent:
    """
    T016: Monitors the waitlist and open appointment slots.
    T017: get_active_waitlist — delegates to repository.
    T018: find_matching_slots — open/cancelled slots within next 7 days.
    T019: run_backfill — pairs waitlisted patients with open slots.
    """

    def __init__(self, db, log_fn=None):
        self._db = db
        self._log = log_fn or (lambda msg: None)

    def run_backfill(self, clinic_id: Optional[str] = None, look_ahead_days: int = 7) -> dict:
        """
        T019: Main backfill sweep.
        1. Fetch waitlist sorted by urgency + join_date.
        2. Find open or cancelled slots in the next N days.
        3. Pair and return matches.
        """
        self._log("WAITLIST AGENT: Starting backfill sweep")
        now = datetime.utcnow()
        cutoff = (now + timedelta(days=look_ahead_days)).isoformat()

        # 1. Fetch active waitlist
        waitlist = self._db.get_active_waitlist(clinic_id=clinic_id)
        waitlist.sort(key=_urgency_sort_key)
        self._log(f"WAITLIST AGENT: {len(waitlist)} patients on waitlist")

        # 2. Find open slots (scheduled + no patient_id, or status = 'cancelled')
        with self._db._get_conn() as conn:
            if clinic_id:
                rows = conn.execute(
                    """SELECT t.id, t.start_time, t.end_time, t.job_id, t.clinic_id
                       FROM timeblocks t
                       WHERE (t.patient_id IS NULL OR t.status = 'cancelled')
                         AND t.start_time > ?
                         AND t.start_time <= ?
                         AND t.clinic_id = ?
                       ORDER BY t.start_time ASC""",
                    (now.isoformat(), cutoff, clinic_id)
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT t.id, t.start_time, t.end_time, t.job_id, t.clinic_id
                       FROM timeblocks t
                       WHERE (t.patient_id IS NULL OR t.status = 'cancelled')
                         AND t.start_time > ?
                         AND t.start_time <= ?
                       ORDER BY t.start_time ASC""",
                    (now.isoformat(), cutoff)
                ).fetchall()
        open_slots = [dict(r) for r in rows]
        self._log(f"WAITLIST AGENT: {len(open_slots)} open slots found in next {look_ahead_days} days")

        # 3. Match
        matches = []
        used_slots = set()
        used_patients = set()

        for entry in waitlist:
            if entry["patient_id"] in used_patients:
                continue
            for slot in open_slots:
                if slot["id"] in used_slots:
                    continue
                # Simple procedure compatibility check — relaxed (any open slot works)
                match = {
                    "waitlist_entry_id": entry["id"],
                    "patient_id": entry["patient_id"],
                    "patient_name": entry.get("patient_name", ""),
                    "procedure_type": entry["procedure_type"],
                    "urgency": entry["urgency"],
                    "slot_timeblock_id": slot["id"],
                    "slot_start": slot["start_time"],
                    "slot_end": slot["end_time"],
                    "clinic_id": slot["clinic_id"],
                    "offer_id": str(uuid4()),
                }
                matches.append(match)
                used_slots.add(slot["id"])
                used_patients.add(entry["patient_id"])
                self._log(
                    f"WAITLIST AGENT: Match — {entry.get('patient_name','?')} ({entry['urgency']}) "
                    f"→ slot {slot['start_time'][:16]} [{slot['id'][:8]}]"
                )
                break  # one slot per patient per run

        self._log(f"WAITLIST AGENT: Backfill complete — {len(matches)} match(es) found")
        return {
            "waitlist_count": len(waitlist),
            "open_slots_count": len(open_slots),
            "matches_found": len(matches),
            "matches": matches,
        }
