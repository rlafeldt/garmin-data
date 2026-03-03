"""Pydantic models for Garmin data normalization and completeness scoring."""

from __future__ import annotations

from datetime import date as DateType
from typing import Any

from pydantic import BaseModel


class DailyMetrics(BaseModel):
    """Normalized daily metrics for Supabase storage.

    All metric fields are Optional to handle partial Garmin data gracefully.
    The raw_data field preserves the full API response for debugging.
    """

    date: DateType

    # Sleep
    total_sleep_seconds: int | None = None
    deep_sleep_seconds: int | None = None
    light_sleep_seconds: int | None = None
    rem_sleep_seconds: int | None = None
    awake_seconds: int | None = None
    sleep_score: int | None = None

    # HRV
    hrv_overnight_avg: float | None = None
    hrv_overnight_max: float | None = None
    hrv_status: str | None = None

    # Body Battery
    body_battery_morning: int | None = None
    body_battery_max: int | None = None
    body_battery_min: int | None = None

    # Heart Rate
    resting_hr: int | None = None
    max_hr: int | None = None
    avg_hr: int | None = None

    # Stress
    avg_stress_level: int | None = None
    high_stress_minutes: int | None = None
    rest_stress_minutes: int | None = None

    # Training
    training_load_7d: float | None = None
    training_status: str | None = None
    vo2_max: float | None = None

    # General
    steps: int | None = None
    calories_total: int | None = None
    calories_active: int | None = None
    intensity_minutes: int | None = None
    spo2_avg: float | None = None
    respiration_rate_avg: float | None = None

    # Metadata
    raw_data: dict[str, Any] | None = None
    is_no_wear: bool = False
    completeness_score: float | None = None


class Activity(BaseModel):
    """Normalized activity record."""

    date: DateType
    activity_type: str
    name: str | None = None
    duration_seconds: int | None = None
    distance_meters: float | None = None
    avg_hr: int | None = None
    max_hr: int | None = None
    calories: int | None = None
    training_effect_aerobic: float | None = None
    training_effect_anaerobic: float | None = None
    vo2_max_activity: float | None = None
    raw_data: dict[str, Any] | None = None


class CompletenessResult(BaseModel):
    """Result of data completeness assessment."""

    score: float
    critical_present: int
    critical_total: int
    missing_critical: list[str]
    is_no_wear: bool


# Critical fields used for completeness scoring
CRITICAL_FIELDS = [
    "total_sleep_seconds",
    "hrv_overnight_avg",
    "body_battery_morning",
    "resting_hr",
    "avg_stress_level",
    "steps",
]

# Supplementary fields for overall score calculation
SUPPLEMENTARY_FIELDS = [
    "deep_sleep_seconds",
    "light_sleep_seconds",
    "rem_sleep_seconds",
    "sleep_score",
    "hrv_status",
    "body_battery_max",
    "body_battery_min",
    "max_hr",
    "avg_hr",
    "high_stress_minutes",
    "rest_stress_minutes",
    "training_load_7d",
    "vo2_max",
    "calories_total",
    "spo2_avg",
    "respiration_rate_avg",
]


def _safe_get(data: dict | None, *keys: str, default: Any = None) -> Any:
    """Safely traverse nested dicts, returning default if any key is missing."""
    current = data
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
        if current is None:
            return default
    return current


def _extract_body_battery(bb_data: list | None) -> tuple[int | None, int | None, int | None]:
    """Extract morning, max, and min body battery from the body battery list.

    The first reading is taken as the morning value. Max and min are computed
    across all readings.
    """
    if not bb_data or not isinstance(bb_data, list):
        return None, None, None

    levels = [
        entry.get("bodyBatteryLevel")
        for entry in bb_data
        if isinstance(entry, dict) and entry.get("bodyBatteryLevel") is not None
    ]
    if not levels:
        return None, None, None

    return levels[0], max(levels), min(levels)


def _to_minutes(seconds: int | None) -> int | None:
    """Convert seconds to whole minutes."""
    if seconds is None:
        return None
    return seconds // 60


def normalize_daily_metrics(raw_data: dict, target_date: DateType) -> DailyMetrics:
    """Map raw Garmin JSON response dicts to typed DailyMetrics model.

    Handles missing endpoints (None values) gracefully. All fields default to None
    when the source data is unavailable.

    Args:
        raw_data: Dict with keys for each metric category from extract_all_metrics.
        target_date: The date these metrics are for.

    Returns:
        A DailyMetrics instance with normalized fields.
    """
    stats = raw_data.get("stats")
    sleep = raw_data.get("sleep")
    hrv = raw_data.get("hrv")
    body_battery = raw_data.get("body_battery")
    stress = raw_data.get("stress")
    spo2 = raw_data.get("spo2")
    respiration = raw_data.get("respiration")
    training_status = raw_data.get("training_status")
    max_metrics = raw_data.get("max_metrics")
    heart_rates = raw_data.get("heart_rates")

    # Extract body battery values
    bb_morning, bb_max, bb_min = _extract_body_battery(body_battery)

    # Extract intensity minutes
    moderate = _safe_get(stats, "moderateIntensityMinutes", default=0) or 0
    vigorous = _safe_get(stats, "vigorousIntensityMinutes", default=0) or 0
    intensity_minutes = (moderate + vigorous) if stats else None

    # Extract stress durations (convert seconds to minutes)
    high_stress_minutes = _to_minutes(_safe_get(stress, "highStressDuration"))
    rest_stress_minutes = _to_minutes(_safe_get(stress, "restStressDuration"))

    return DailyMetrics(
        date=target_date,
        # Sleep
        total_sleep_seconds=_safe_get(sleep, "dailySleepDTO", "sleepTimeSeconds"),
        deep_sleep_seconds=_safe_get(sleep, "dailySleepDTO", "deepSleepSeconds"),
        light_sleep_seconds=_safe_get(sleep, "dailySleepDTO", "lightSleepSeconds"),
        rem_sleep_seconds=_safe_get(sleep, "dailySleepDTO", "remSleepSeconds"),
        awake_seconds=_safe_get(sleep, "dailySleepDTO", "awakeSleepSeconds"),
        sleep_score=_safe_get(sleep, "dailySleepDTO", "sleepScores", "overallScore"),
        # HRV
        hrv_overnight_avg=_safe_get(hrv, "hrvSummary", "lastNightAvg"),
        hrv_overnight_max=_safe_get(hrv, "hrvSummary", "lastNight5MinHigh"),
        hrv_status=_safe_get(hrv, "hrvSummary", "status"),
        # Body Battery
        body_battery_morning=bb_morning,
        body_battery_max=bb_max,
        body_battery_min=bb_min,
        # Heart Rate (prefer stats, fall back to heart_rates endpoint)
        resting_hr=(
            _safe_get(stats, "restingHeartRate")
            or _safe_get(heart_rates, "restingHeartRate")
        ),
        max_hr=(
            _safe_get(stats, "maxHeartRate")
            or _safe_get(heart_rates, "maxHeartRate")
        ),
        avg_hr=_safe_get(stats, "averageHeartRate"),
        # Stress
        avg_stress_level=_safe_get(stress, "overallStressLevel"),
        high_stress_minutes=high_stress_minutes,
        rest_stress_minutes=rest_stress_minutes,
        # Training
        training_load_7d=_safe_get(training_status, "load"),
        training_status=_safe_get(training_status, "trainingStatusFeedback"),
        vo2_max=_safe_get(max_metrics, "generic", "vo2MaxPreciseValue"),
        # General
        steps=_safe_get(stats, "totalSteps"),
        calories_total=_safe_get(stats, "totalKilocalories"),
        calories_active=_safe_get(stats, "activeKilocalories"),
        intensity_minutes=intensity_minutes,
        spo2_avg=_safe_get(spo2, "averageSpO2"),
        respiration_rate_avg=_safe_get(respiration, "avgWakingRespirationValue"),
        # Metadata
        raw_data=raw_data,
    )


def normalize_activities(raw_activities: list, target_date: DateType) -> list[Activity]:
    """Normalize raw Garmin activity data to Activity models.

    Args:
        raw_activities: List of raw activity dicts from Garmin API.
        target_date: The date these activities are for.

    Returns:
        List of normalized Activity instances.
    """
    if not raw_activities:
        return []

    activities = []
    for raw in raw_activities:
        activity = Activity(
            date=target_date,
            activity_type=_safe_get(raw, "activityType", "typeKey", default="unknown"),
            name=raw.get("activityName"),
            duration_seconds=int(raw["duration"]) if raw.get("duration") is not None else None,
            distance_meters=raw.get("distance"),
            avg_hr=raw.get("averageHR"),
            max_hr=raw.get("maxHR"),
            calories=raw.get("calories"),
            training_effect_aerobic=raw.get("aerobicTrainingEffect"),
            training_effect_anaerobic=raw.get("anaerobicTrainingEffect"),
            vo2_max_activity=raw.get("vO2MaxValue"),
            raw_data=raw,
        )
        activities.append(activity)

    return activities


def assess_completeness(record: DailyMetrics) -> CompletenessResult:
    """Assess data completeness of a daily metrics record.

    Uses critical fields (sleep, HRV, body battery, resting HR, stress, steps) as
    primary indicators. Supplementary fields contribute to overall score.

    A no-wear day is detected when ALL critical fields are None.

    Args:
        record: A DailyMetrics instance to assess.

    Returns:
        CompletenessResult with score, missing fields, and no-wear flag.
    """
    data = record.model_dump()

    critical_present = sum(1 for f in CRITICAL_FIELDS if data.get(f) is not None)
    supplementary_present = sum(1 for f in SUPPLEMENTARY_FIELDS if data.get(f) is not None)

    total = len(CRITICAL_FIELDS) + len(SUPPLEMENTARY_FIELDS)
    present = critical_present + supplementary_present
    score = present / total if total > 0 else 0.0

    missing = [f for f in CRITICAL_FIELDS if data.get(f) is None]
    is_no_wear = critical_present == 0

    return CompletenessResult(
        score=score,
        critical_present=critical_present,
        critical_total=len(CRITICAL_FIELDS),
        missing_critical=missing,
        is_no_wear=is_no_wear,
    )
