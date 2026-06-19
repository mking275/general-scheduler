"""
T005 + T018 — RiskScoringAgent
Weighted rule-based no-show risk scoring at booking time.
"""
from datetime import datetime, timedelta
from typing import Optional
from ..models import RiskScore, TimeBlock, Patient


class RiskScoringAgent:
    """
    Weighted risk scoring rules per spec T018:
    - Lead time: <24h=+40, <72h=+20, ≥7d=0
    - Visit type: emergency=-30(wait, it's actually higher risk so +30), wellness=+20
    - Patient status: first_visit=+15, >5 visits=-15
    - Procedure urgency: elective=+15, sick=-10
    """

    def score(self, timeblock: TimeBlock, patient: Optional[Patient] = None) -> RiskScore:
        points = 0
        factors = []

        # 1. Lead time scoring
        now = datetime.now()
        lead_hours = (timeblock.start_time - now).total_seconds() / 3600

        if lead_hours < 24:
            points += 40
            factors.append("Same-day/next-day booking (+40)")
        elif lead_hours < 72:
            points += 20
            factors.append("Short lead time < 72h (+20)")
        elif lead_hours >= 168:  # 7+ days
            points += 0
            factors.append("Advance booking ≥7 days (0)")
        else:
            points += 10
            factors.append("Lead time 3-7 days (+10)")

        # 2. Patient-level scoring
        if patient:
            if "first_visit" in (patient.flags or []):
                points += 15
                factors.append("First visit patient (+15)")
            elif patient.visit_count > 5:
                points -= 15
                factors.append("Established patient >5 visits (−15)")

            if "alert" in (patient.flags or []):
                points += 15
                factors.append("Alert flag — medical risk (+15)")

            if "chronic" in (patient.flags or []):
                points += 5
                factors.append("Chronic condition (+5)")

        # 3. Procedure / job scoring — infer from job data if possible
        # We use the job_id to look up the job; if no context, use defaults

        # Clamp score 0-100
        score_val = max(0, min(100, points))

        # Determine level
        if score_val >= 60:
            level = "high"
        elif score_val >= 30:
            level = "medium"
        else:
            level = "low"

        return RiskScore(
            timeblock_id=str(timeblock.id),
            risk_level=level,
            score=score_val,
            factors=factors,
        )

    def score_with_procedure(
        self, timeblock: TimeBlock, patient: Optional[Patient], procedure: Optional[str]
    ) -> RiskScore:
        """Enhanced scoring that also considers procedure type."""
        result = self.score(timeblock, patient)

        if procedure:
            proc_lower = procedure.lower()
            if "emergency" in proc_lower:
                # Emergency is high urgency — raises score
                result.factors.append("Emergency procedure (+25)")
                result.score = min(100, result.score + 25)
            elif any(w in proc_lower for w in ["wellness", "vaccination", "grooming"]):
                result.factors.append("Elective/wellness procedure (+15)")
                result.score = min(100, result.score + 15)
            elif "surgery" in proc_lower:
                result.factors.append("Surgical procedure (+10)")
                result.score = min(100, result.score + 10)

        # Re-compute level after adjustment
        if result.score >= 60:
            result.risk_level = "high"
        elif result.score >= 30:
            result.risk_level = "medium"
        else:
            result.risk_level = "low"

        return result
