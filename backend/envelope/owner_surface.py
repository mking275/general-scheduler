"""Feature 009 — T026 owner/manager-only reconciliation surface + group ack.

The reconciliation report is the **only** trust surface allowed during onboarding
and it is **owner/manager-audience-only** (the invisible-adoption guard, FR-029 —
reusing 011's audience vocabulary at the surface edge; no staff audience is ever
reachable). Activation requires a **group-level acknowledgment**, with drill-down
from the group rollup to each individual practice's reconciliation (FR-018).

The owner-acknowledgment is recorded as an **append** — a fresh
``ReconciliationReport`` version carrying ``owner_acknowledged=True`` — never an
in-place update (``ReconciliationReport`` is append-only). A **blocking** practice
(unexplained AR variance) is surfaced red and is **not** acknowledged/activatable;
the group ack acknowledges only the non-blocking practices.

Owner-facing delivery reuses the shipped ``sms_gateway`` outbound leg.
"""
from __future__ import annotations

from typing import Any, Optional

from backend.models import ReconciliationReport

_OWNER_AUDIENCES = ("owner", "manager")


class OwnerSurface:
    def __init__(self, repo, sms_gateway: Optional[Any] = None):
        self.repo = repo
        self._sms = sms_gateway

    # ------------------------------------------------------------------ #
    #  Audience-scoped read (owner/manager only — no staff surface)
    # ------------------------------------------------------------------ #
    def latest_report(self, practice_id: str,
                      audience: str = "owner") -> Optional[dict]:
        if audience not in _OWNER_AUDIENCES:
            raise PermissionError(
                f"reconciliation report is owner/manager-only; audience={audience!r} "
                f"is not a permitted onboarding surface (FR-029)")
        reports = self.repo.get_reconciliation_reports(practice_id)
        return reports[-1] if reports else None

    def group_report(self, clinic_id: str, practice_ids: list[str],
                     audience: str = "owner") -> dict[str, Any]:
        """The group rollup with drill-down to each practice's reconciliation."""
        drill_down = {pid: self.latest_report(pid, audience) for pid in practice_ids}
        blocking = sorted(pid for pid, r in drill_down.items() if r and r.get("blocking"))
        acknowledged = sorted(pid for pid, r in drill_down.items()
                              if r and r.get("owner_acknowledged"))
        return {
            "clinic_id": clinic_id, "audience": audience,
            "practice_ids": sorted(practice_ids),
            "blocking": blocking, "acknowledged": acknowledged,
            "drill_down": drill_down,   # group -> per-practice reconciliation
        }

    # ------------------------------------------------------------------ #
    #  Group-level acknowledgment (append-only; skips blocking practices)
    # ------------------------------------------------------------------ #
    def acknowledge_group(self, clinic_id: str, practice_ids: list[str],
                          acknowledged_by: str, audience: str = "owner"
                          ) -> dict[str, list[str]]:
        if audience not in _OWNER_AUDIENCES:
            raise PermissionError("only owner/manager may acknowledge a group")
        acknowledged: list[str] = []
        held: list[str] = []
        for pid in practice_ids:
            latest = self.latest_report(pid, audience)
            if latest is None:
                continue
            if latest.get("blocking"):
                held.append(pid)                 # red — never acknowledged
                continue
            self._append_ack_version(latest, acknowledged_by)
            acknowledged.append(pid)
        return {"acknowledged": sorted(acknowledged), "held": sorted(held)}

    def is_activatable(self, practice_id: str) -> bool:
        """A practice is activatable only once its latest report is acknowledged
        and not blocking."""
        latest = self.latest_report(practice_id)
        return bool(latest and latest.get("owner_acknowledged")
                    and not latest.get("blocking"))

    def _append_ack_version(self, latest: dict, acknowledged_by: str) -> str:
        data = {k: v for k, v in latest.items() if k not in ("id", "created_at")}
        data["owner_acknowledged"] = True
        ack = ReconciliationReport(**data)
        self.repo.append_reconciliation_report(ack)
        return ack.id

    # ------------------------------------------------------------------ #
    #  Owner-facing delivery — reuse the sms_gateway outbound leg
    # ------------------------------------------------------------------ #
    def notify_owner(self, to: str, body: str) -> Any:
        gateway = self._sms
        if gateway is None:
            from backend.sms_gateway import SMSGateway
            gateway = SMSGateway()
        return gateway.send_sms(to, body)
