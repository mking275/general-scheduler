"""
availability_agent.py — Slot availability computation for the VPMA Online Booking Portal.

Responsibilities:
  - Enumerate candidate slots for a given clinic, resource, date range, and
    appointment type.
  - Filter out slots blocked by existing timeblocks and active slot_holds.
  - Generate deterministic UUID5 slot IDs from (resource_id, start_datetime_iso).
  - Return SlotAvailabilityItem list ranked chronologically (Phase 1).

Does NOT do: AI slot ranking (Phase 2), no-show risk scoring (Phase 2).

Logging prefix: VERA (Availability):
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, time as dt_time
from typing import Optional

log = logging.getLogger(__name__)

# ── Business-hour defaults (used when clinic has no schedule on file) ──────
_DEFAULT_OPEN_HOUR = 8    # 08:00
_DEFAULT_CLOSE_HOUR = 17  # 17:00
_DEFAULT_SLOT_DAYS = list(range(0, 5))  # Monday–Friday (0=Mon, 6=Sun)

# Namespace for deterministic slot UUIDs (shared with spec)
_SLOT_NS = uuid.NAMESPACE_URL


def _make_slot_id(resource_id: str, start_dt: datetime) -> str:
    """Return a deterministic UUID5 for a (resource_id, start_datetime) pair."""
    key = f"{resource_id}:{start_dt.isoformat()}"
    return str(uuid.uuid5(_SLOT_NS, key))


def _human_vet_name(resource: dict, show_full: bool = True) -> tuple[str, str]:
    """Return (vet_name, vet_display_name) from a resource row."""
    full = resource.get("name", "Unknown Vet")
    # Attempt to extract last name for display form "Dr. Smith"
    parts = full.split()
    if len(parts) >= 2 and parts[0].startswith("Dr"):
        display = f"Dr. {parts[-1]}"
    else:
        display = full
    name = full if show_full else "Vet"
    return name, (display if show_full else "Vet")


class AvailabilityAgent:
    """Compute open appointment slots for a clinic / resource / date range."""

    def __init__(self, db, log_fn=None):
        """
        Args:
            db: Repository instance (InMemoryRepository).
            log_fn: Optional callable(str) for verbose agent log entries.
        """
        self._db = db
        self._log = log_fn or (lambda msg: None)

    def get_slots(
        self,
        clinic_id: str,
        appointment_type_id: str,
        duration_minutes: int,
        start_date: datetime,
        end_date: datetime,
        resource_id: Optional[str] = None,
        max_slots: int = 30,
        buffer_minutes: int = 10,
        hidden_vet_ids: Optional[list] = None,
    ) -> list[dict]:
        """
        Return a list of available SlotAvailabilityItem dicts for the given
        clinic/date-range, ranked chronologically.

        Args:
            clinic_id:            Clinic UUID.
            appointment_type_id:  e.g. "wellness".
            duration_minutes:     Length of each slot.
            start_date:           Earliest slot start (inclusive, UTC/local naive).
            end_date:             Latest slot end (inclusive).
            resource_id:          If provided, limit to this vet only.
            max_slots:            Maximum number of slots to return.
            buffer_minutes:       Pad each booked block by this many minutes when
                                  checking for slot clearance.
            hidden_vet_ids:       Resource IDs to exclude.

        Returns:
            List of slot dicts (fields match SlotAvailabilityItem).
        """
        self._log(f"VERA (Availability): computing slots clinic={clinic_id} "
                  f"type={appointment_type_id} duration={duration_minutes}m "
                  f"range={start_date.date()}–{end_date.date()}")

        hidden = set(hidden_vet_ids or [])

        # Gather vet resources for this clinic
        if resource_id:
            resource_rows = self._db.get_resources_for_clinic(clinic_id)
            resources = [r for r in resource_rows if r["id"] == resource_id]
        else:
            resources = self._db.get_resources_for_clinic(clinic_id)

        # Exclude hidden vets
        resources = [r for r in resources if r["id"] not in hidden]

        if not resources:
            self._log("VERA (Availability): no eligible resources found")
            return []

        slots: list[dict] = []
        slot_duration = timedelta(minutes=duration_minutes)
        buffer_td = timedelta(minutes=buffer_minutes)

        # Iterate each resource
        for resource in resources:
            if len(slots) >= max_slots:
                break

            rid = resource["id"]
            vet_name, vet_display = _human_vet_name(resource, show_full=True)

            # Pull existing bookings for this resource over the search range
            existing = self._db.get_timeblocks_for_date_range(
                rid,
                start_date.isoformat(),
                (end_date + timedelta(hours=24)).isoformat(),
            )

            # Build a sorted list of (start, end) busy windows with buffer
            busy: list[tuple[datetime, datetime]] = []
            for tb in existing:
                try:
                    tb_start = datetime.fromisoformat(tb["start_time"])
                    tb_end = datetime.fromisoformat(tb["end_time"])
                except (ValueError, TypeError):
                    continue
                busy.append((tb_start - buffer_td, tb_end + buffer_td))
            busy.sort(key=lambda x: x[0])

            # Walk each day in range and enumerate candidate slots
            current_date = start_date.date()
            end_date_d = end_date.date()
            while current_date <= end_date_d and len(slots) < max_slots:
                day_of_week = current_date.weekday()
                if day_of_week in _DEFAULT_SLOT_DAYS:
                    open_dt = datetime.combine(current_date, dt_time(_DEFAULT_OPEN_HOUR, 0))
                    close_dt = datetime.combine(current_date, dt_time(_DEFAULT_CLOSE_HOUR, 0))

                    candidate = open_dt
                    while candidate + slot_duration <= close_dt and len(slots) < max_slots:
                        cand_end = candidate + slot_duration

                        # Skip slots that have already passed
                        if candidate <= datetime.utcnow():
                            candidate += slot_duration
                            continue

                        # Check against busy windows
                        overlaps = any(
                            b_start < cand_end and b_end > candidate
                            for b_start, b_end in busy
                        )
                        if not overlaps:
                            slot_id = _make_slot_id(rid, candidate)
                            slots.append({
                                "slot_id": slot_id,
                                "resource_id": rid,
                                "vet_name": vet_name,
                                "vet_display_name": vet_display,
                                "start_datetime": candidate.isoformat(),
                                "end_datetime": cand_end.isoformat(),
                                "duration_minutes": duration_minutes,
                                "rank": 0,          # filled below
                                "rank_label": "Soonest Available",
                                "rank_explanation": "Earliest available opening",
                                "no_show_risk_label": None,  # Phase 2
                            })

                        candidate += slot_duration

                current_date += timedelta(days=1)

        # Sort all results chronologically and assign ranks
        slots.sort(key=lambda s: s["start_datetime"])
        for i, s in enumerate(slots[:max_slots], start=1):
            s["rank"] = i

        self._log(f"VERA (Availability): returned {len(slots[:max_slots])} slots")
        return slots[:max_slots]
