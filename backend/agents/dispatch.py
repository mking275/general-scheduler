from ..models import TimeBlock, Job, Resource
from typing import List

class DispatchAgent:
    def format_response(self, tb: TimeBlock, job: Job, resources: List[Resource], logs: List[str]) -> dict:
        return {
            "status": "success",
            "timeblock_id": str(tb.id),
            "job": job.model_dump(),
            "resources": [r.model_dump() for r in resources],
            "start_time": tb.start_time.isoformat(),
            "end_time": tb.end_time.isoformat(),
            "verbose_log": logs
        }
