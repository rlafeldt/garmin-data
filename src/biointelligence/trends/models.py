"""Pydantic models for rolling trend computation (7-day and 28-day windows)."""

from __future__ import annotations

from datetime import date
from enum import StrEnum

from pydantic import BaseModel


class TrendDirection(StrEnum):
    """Direction of a metric trend over a time window."""

    IMPROVING = "improving"
    DECLINING = "declining"
    STABLE = "stable"
    INSUFFICIENT = "insufficient_data"


class MetricTrend(BaseModel):
    """Trend statistics for a single metric."""

    avg: float | None = None
    min_val: float | None = None
    max_val: float | None = None
    stddev: float | None = None
    direction: TrendDirection = TrendDirection.INSUFFICIENT


class TrendResult(BaseModel):
    """Aggregated trend results for all trended metrics over a time window."""

    window_start: date
    window_end: date
    data_points: int
    metrics: dict[str, MetricTrend]


# Configuration: which metrics are trended and their directionality.
# lower_is_better=True means a decrease in value is IMPROVING (e.g., resting HR).
TRENDED_METRICS: dict[str, dict[str, bool]] = {
    "hrv_overnight_avg": {"lower_is_better": False},
    "resting_hr": {"lower_is_better": True},
    "sleep_score": {"lower_is_better": False},
    "total_sleep_seconds": {"lower_is_better": False},
    "body_battery_morning": {"lower_is_better": False},
    "avg_stress_level": {"lower_is_better": True},
    "training_load_7d": {"lower_is_better": False},
    "deep_sleep_seconds": {"lower_is_better": False},
    "rest_stress_minutes": {"lower_is_better": False},
    "body_battery_max": {"lower_is_better": False},
    "body_battery_min": {"lower_is_better": False},
}
