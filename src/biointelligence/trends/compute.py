"""7-day rolling trend computation with split-half direction analysis."""

from __future__ import annotations

from datetime import date, timedelta
from statistics import mean

import structlog
from supabase import Client
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from biointelligence.trends.models import (
    TRENDED_METRICS,
    MetricTrend,
    TrendDirection,
    TrendResult,
)

log = structlog.get_logger()

# Columns to SELECT from daily_metrics for trend computation.
TREND_FIELDS = (
    "date,hrv_overnight_avg,resting_hr,sleep_score,"
    "total_sleep_seconds,body_battery_morning,avg_stress_level,training_load_7d,"
    "is_no_wear"
)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    retry=retry_if_exception_type((ConnectionError, TimeoutError)),
)
def fetch_trend_window(
    client: Client, target_date: date, window_days: int = 7
) -> list[dict]:
    """Fetch daily metrics for a trend computation window from Supabase.

    Uses .gte(start) and .lt(target_date) for an exclusive-end window,
    giving exactly `window_days` days before target_date.

    Args:
        client: Supabase client instance.
        target_date: The reference date (exclusive upper bound).
        window_days: Number of days in the trend window (default 7).

    Returns:
        List of daily metric rows as dicts.
    """
    start = target_date - timedelta(days=window_days)

    log.info(
        "fetch_trend_window",
        start=start.isoformat(),
        end=target_date.isoformat(),
        window_days=window_days,
    )

    response = (
        client.table("daily_metrics")
        .select(TREND_FIELDS)
        .gte("date", start.isoformat())
        .lt("date", target_date.isoformat())
        .eq("is_no_wear", False)
        .order("date", desc=False)
        .execute()
    )
    return response.data


def compute_direction(
    values: list[float],
    lower_is_better: bool = False,
    min_data_points: int = 4,
    threshold: float = 0.05,
) -> TrendDirection:
    """Compute trend direction via split-half comparison.

    Splits the values into first and second halves, computes their means,
    and determines if the metric is improving, declining, or stable based
    on the percentage change exceeding the threshold.

    For lower_is_better metrics (resting HR, stress), a decrease is IMPROVING.

    Args:
        values: Ordered list of metric values (oldest to newest).
        lower_is_better: If True, a decrease is considered IMPROVING.
        min_data_points: Minimum number of values required (default 4).
        threshold: Percentage change threshold for direction (default 5%).

    Returns:
        TrendDirection indicating the metric's trajectory.
    """
    if len(values) < min_data_points:
        return TrendDirection.INSUFFICIENT

    mid = len(values) // 2
    first_half = mean(values[:mid])
    second_half = mean(values[mid:])

    if first_half == 0:
        return TrendDirection.STABLE

    pct_change = (second_half - first_half) / abs(first_half)

    # Invert direction for lower-is-better metrics
    if lower_is_better:
        pct_change = -pct_change

    if pct_change > threshold:
        return TrendDirection.IMPROVING
    if pct_change < -threshold:
        return TrendDirection.DECLINING
    return TrendDirection.STABLE


def compute_trends(client: Client, target_date: date) -> TrendResult:
    """Compute 7-day rolling trends for all trended metrics.

    Fetches the trend window from Supabase, then for each trended metric:
    extracts non-None values, computes avg/min/max statistics, and determines
    the trend direction using split-half comparison.

    Args:
        client: Supabase client instance.
        target_date: The reference date (trends computed for the 7 days before).

    Returns:
        TrendResult with per-metric statistics and directions.
    """
    window_start = target_date - timedelta(days=7)
    rows = fetch_trend_window(client, target_date)

    log.info("compute_trends", target_date=target_date.isoformat(), data_points=len(rows))

    metrics: dict[str, MetricTrend] = {}

    for metric_name, config in TRENDED_METRICS.items():
        # Extract non-None values for this metric
        values = [
            row[metric_name]
            for row in rows
            if row.get(metric_name) is not None
        ]

        if not values:
            metrics[metric_name] = MetricTrend()
            continue

        direction = compute_direction(
            values, lower_is_better=config["lower_is_better"]
        )

        metrics[metric_name] = MetricTrend(
            avg=mean(values),
            min_val=min(values),
            max_val=max(values),
            direction=direction,
        )

    log.info(
        "trends_computed",
        target_date=target_date.isoformat(),
        directions={name: trend.direction.value for name, trend in metrics.items()},
    )

    return TrendResult(
        window_start=window_start,
        window_end=target_date,
        data_points=len(rows),
        metrics=metrics,
    )
