"""Garmin Connect data extraction and normalization."""

from biointelligence.garmin.client import get_authenticated_client
from biointelligence.garmin.extractors import extract_all_metrics
from biointelligence.garmin.models import (
    Activity,
    CompletenessResult,
    DailyMetrics,
    assess_completeness,
    normalize_activities,
    normalize_daily_metrics,
)

__all__ = [
    "get_authenticated_client",
    "extract_all_metrics",
    "DailyMetrics",
    "Activity",
    "CompletenessResult",
    "normalize_daily_metrics",
    "normalize_activities",
    "assess_completeness",
]
