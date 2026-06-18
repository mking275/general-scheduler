from typing import List
from datetime import datetime, timedelta, date, time
from .models import Job, Resource, TimeBlock
from .interfaces import BaseSolver

class HeuristicSolver(BaseSolver):
    def solve(self, job: Job, resources: List[Resource], existing_timeblocks: List[TimeBlock]) -> TimeBlock:
        # Validate hard skills
        for skill in job.required_skills:
            valid_resources = [r for r in resources if skill in r.hard_skills]
            if not valid_resources:
                raise ValueError(f"Constraint Failed: No resource has skill '{skill}'")

        resource_ids = {r.id for r in resources}
        duration = timedelta(minutes=job.estimated_duration)

        # Determine search anchor from parsed date/time, or fall back to now
        now = datetime.now()
        target_date: date = job.scheduled_date or now.date()

        if job.scheduled_time:
            # Start exactly at the requested time on the target date
            anchor = datetime.combine(target_date, job.scheduled_time)
            if anchor < now:
                # Requested time is in the past — shift to tomorrow same time
                anchor = datetime.combine(target_date + timedelta(days=1), job.scheduled_time)
        else:
            if target_date == now.date():
                # Today: start from the next 30-min boundary
                minutes = now.minute
                round_up = 30 - (minutes % 30) if minutes % 30 != 0 else 30
                anchor = now.replace(second=0, microsecond=0) + timedelta(minutes=round_up)
            else:
                # Future date: start at 8 AM
                anchor = datetime.combine(target_date, time(8, 0))

        for _ in range(16):  # Check up to 16 slots (8 hours in 30-min steps)
            candidate_end = anchor + duration
            collision = False

            for tb in existing_timeblocks:
                # Check time overlap
                overlap = anchor < tb.end_time and candidate_end > tb.start_time
                if overlap:
                    # Check resource overlap
                    if resource_ids & set(tb.resource_ids):
                        collision = True
                        break

            if not collision:
                return TimeBlock(
                    job_id=job.id,
                    resource_ids=list(resource_ids),
                    start_time=anchor,
                    end_time=candidate_end
                )

            anchor += timedelta(minutes=30)

        raise ValueError("Constraint Failed: No available slot found in the next 8 hours")
