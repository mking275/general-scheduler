from ..models import TimeBlock, Job, Resource, Patient
from typing import List, Optional

class DispatchAgent:
    def format_response(self, tb: TimeBlock, job: Job, resources: List[Resource], logs: List[str]) -> dict:
        return {
            "status": "success",
            "timeblock_id": str(tb.id),
            "job": job.model_dump(),
            "resources": [r.model_dump() for r in resources],
            "start_time": tb.start_time.isoformat(),
            "end_time": tb.end_time.isoformat(),
            "patient_id": tb.patient_id,
            "intake_status": tb.intake_status,
            "followup_status": tb.followup_status,
            "risk_level": tb.risk_level,
            "status": tb.status,
            "verbose_log": logs
        }
