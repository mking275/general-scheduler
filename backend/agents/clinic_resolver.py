"""
T005 — ClinicResolver agent.
Provides vet-clinic availability checking, next-available-date scanning,
and formatted conflict messages (FR-013).
"""
from datetime import date, timedelta
from typing import Optional


class ClinicResolver:
    """Agent that resolves clinic availability and surfaces scheduling conflicts."""

    def get_default_clinic_id(self) -> Optional[str]:
        from ..repository import db
        clinic = db.get_default_clinic()
        return clinic.id if clinic else None

    def is_vet_available_at_clinic(
        self, vet_id: str, clinic_id: str, check_date: date
    ) -> bool:
        """Return True if the vet has an assignment at clinic_id on the weekday of check_date."""
        from ..repository import db
        day_name = check_date.strftime("%A")  # e.g. "Monday"
        vets = db.get_vets_available_at_clinic(clinic_id, day_name)
        return any(str(v.id) == vet_id for v in vets)

    def get_next_available_date(
        self,
        vet_id: str,
        clinic_id: str,
        from_date: date,
        lookahead_days: int = 14,
    ) -> Optional[date]:
        """Scan up to lookahead_days days starting from the day after from_date."""
        for i in range(1, lookahead_days + 1):
            check = from_date + timedelta(days=i)
            if self.is_vet_available_at_clinic(vet_id, clinic_id, check):
                return check
        return None

    def format_conflict_message(
        self,
        vet_name: str,
        blocking_clinic_name: str,
        target_clinic_name: str,
        next_date: Optional[date],
    ) -> str:
        """Build the human-readable conflict message per FR-013."""
        msg = f"{vet_name} is at {blocking_clinic_name} today"
        if next_date:
            msg += (
                f" — next available at {target_clinic_name} is "
                f"{next_date.strftime('%A %Y-%m-%d')}"
            )
        else:
            msg += (
                f" — no availability found at {target_clinic_name} in the next 14 days"
            )
        return msg
