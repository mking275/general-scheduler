"""
T037-T039 — ForecastAgent (F019)
4-week capacity and revenue forecast using pure-Python linear regression
on historical completed appointment counts (no NumPy).
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Optional


# ── Capacity assumptions (overrideable via config) ─────────────────────────
_DEFAULT_CAPACITY_PER_WEEK    = 20   # slots per week (adjustable per clinic)
_DEFAULT_REVENUE_PER_SLOT     = 95.0  # USD average
_TREND_STRONG_GROWTH_PCT      = 5.0  # % growth/week → "strong_growth"
_TREND_ACTION_NEEDED_PCT      = -2.0  # % growth/week → "action_needed"


def _linear_regression(xs: List[float], ys: List[float]):
    """
    Pure Python OLS linear regression.
    Returns (slope, intercept).
    """
    n = len(xs)
    if n < 2:
        return (0.0, ys[0] if ys else 0.0)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    num   = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    denom = sum((x - mean_x) ** 2 for x in xs)
    slope = num / denom if denom != 0 else 0.0
    intercept = mean_y - slope * mean_x
    return slope, intercept


class ForecastAgent:
    """
    T037: Load historical weekly appointment counts.
    T038: Run pure-Python linear regression.
    T039: Project N weeks ahead with utilisation % and revenue estimate.
    """

    def __init__(self, db, log_fn=None,
                 capacity_per_week: int = _DEFAULT_CAPACITY_PER_WEEK,
                 revenue_per_slot: float = _DEFAULT_REVENUE_PER_SLOT):
        self._db = db
        self._log = log_fn or (lambda msg: None)
        self._capacity = capacity_per_week
        self._revenue  = revenue_per_slot

    def forecast(self, clinic_id: str, project_weeks: int = 4) -> dict:
        """
        T037-T039: Run forecast for a clinic.
        Returns ForecastResult-compatible dict.
        """
        verbose_log = []
        def _vlog(msg):
            verbose_log.append(msg)
            self._log(f"FORECAST AGENT: {msg}")

        _vlog(f"Starting forecast for clinic {clinic_id}")

        # 1. Fetch clinic metadata
        clinic_name = clinic_id
        try:
            clinic = self._db.get_clinic(clinic_id)
            if clinic:
                clinic_name = getattr(clinic, "name", None) or (clinic.get("name") if isinstance(clinic, dict) else clinic_id)
        except Exception:
            pass

        # 2. Load historical weekly counts (last 8 weeks)
        historical = self._db.get_historical_weekly_counts(clinic_id, weeks=8)
        _vlog(f"Loaded {len(historical)} historical week(s) of data")

        if not historical:
            # No data — return flat forecast at half capacity
            _vlog("No historical data — defaulting to flat 50% utilisation forecast")
            forecast_weeks = []
            for i in range(1, project_weeks + 1):
                projected = max(1, self._capacity // 2)
                util_pct  = round(projected / self._capacity * 100, 1)
                forecast_weeks.append({
                    "week_label":       f"W+{i}",
                    "booked_slots":     0,
                    "projected_slots":  projected,
                    "capacity_slots":   self._capacity,
                    "utilisation_pct":  util_pct,
                    "projected_revenue": round(projected * self._revenue, 2),
                })
            return {
                "clinic_id":      clinic_id,
                "clinic_name":    clinic_name,
                "trend":          "on_track",
                "forecast_weeks": forecast_weeks,
                "insight":        "Insufficient historical data — forecast defaults to 50% capacity utilisation.",
                "verbose_log":    verbose_log,
            }

        # 3. Convert to (x, y) pairs for regression
        xs = list(range(len(historical)))
        ys = [float(r.get("count", 0)) for r in historical]
        _vlog(f"Historical counts (oldest→newest): {[int(y) for y in ys]}")

        slope, intercept = _linear_regression(xs, ys)
        _vlog(f"Linear regression: slope={slope:.3f}, intercept={intercept:.3f}")

        # Trend classification based on slope vs capacity
        slope_pct = (slope / self._capacity * 100) if self._capacity else 0
        if slope_pct >= _TREND_STRONG_GROWTH_PCT:
            trend = "strong_growth"
        elif slope_pct <= _TREND_ACTION_NEEDED_PCT:
            trend = "action_needed"
        else:
            trend = "on_track"
        _vlog(f"Trend: {trend} (slope_pct={slope_pct:.2f}%/week)")

        # 4. Project forward
        last_x = len(historical) - 1
        forecast_weeks = []
        for i in range(1, project_weeks + 1):
            proj_x = last_x + i
            projected = max(0, round(slope * proj_x + intercept))
            projected = min(projected, self._capacity)  # cap at capacity
            util_pct  = round(projected / self._capacity * 100, 1) if self._capacity else 0
            revenue   = round(projected * self._revenue, 2)
            forecast_weeks.append({
                "week_label":        f"W+{i}",
                "booked_slots":      0,   # future — no confirmed bookings yet
                "projected_slots":   projected,
                "capacity_slots":    self._capacity,
                "utilisation_pct":   util_pct,
                "projected_revenue": revenue,
            })
            _vlog(f"Week W+{i}: projected={projected} slots, util={util_pct}%, revenue=${revenue:,.0f}")

        # 5. Insight string
        avg_hist = sum(ys) / len(ys)
        last_proj = forecast_weeks[-1]["projected_slots"]
        if trend == "strong_growth":
            insight = (
                f"Strong upward trend detected (+{slope:.1f} appts/week). "
                f"Consider adding vet availability or extending hours to meet projected demand."
            )
        elif trend == "action_needed":
            insight = (
                f"Declining appointment volume detected ({slope:.1f} appts/week). "
                f"Review marketing campaigns and consider targeted outreach to lapsing clients."
            )
        else:
            insight = (
                f"Appointment volume is stable. Average {avg_hist:.0f} appts/week over {len(historical)} weeks. "
                f"Projecting {last_proj} appts in week W+{project_weeks} at "
                f"{forecast_weeks[-1]['utilisation_pct']:.0f}% capacity."
            )

        _vlog(f"Forecast complete — insight: {insight[:80]}...")

        return {
            "clinic_id":      clinic_id,
            "clinic_name":    clinic_name,
            "trend":          trend,
            "forecast_weeks": forecast_weeks,
            "insight":        insight,
            "verbose_log":    verbose_log,
        }
