"""Anomaly detection orchestrator: z-scores, outliers, and convergence patterns.

Detects single-metric extreme outliers and multi-metric convergence patterns
using personal baselines from 28-day trend windows.
"""

from __future__ import annotations

from typing import Any

import structlog

from biointelligence.anomaly.models import Alert, AlertSeverity, AnomalyResult, ConvergencePattern
from biointelligence.anomaly.patterns import CONVERGENCE_PATTERNS
from biointelligence.trends.models import TRENDED_METRICS, MetricTrend, TrendResult

log = structlog.get_logger()

# Z-score thresholds for single-metric extreme outlier detection.
EXTREME_OUTLIER_WARNING = 2.5
EXTREME_OUTLIER_CRITICAL = 3.0


def compute_z_score(
    current_value: float,
    baseline_mean: float,
    baseline_stddev: float,
) -> float:
    """Compute z-score for a single metric against its personal baseline.

    Returns 0.0 if stddev is 0 (all values identical in baseline window).

    Args:
        current_value: Today's metric value.
        baseline_mean: 28-day rolling mean.
        baseline_stddev: 28-day rolling sample standard deviation.

    Returns:
        Z-score indicating how many standard deviations from mean.
    """
    if baseline_stddev == 0:
        return 0.0
    return (current_value - baseline_mean) / baseline_stddev


def _check_consecutive_days(
    rows: list[dict],
    metric_name: str,
    baseline_mean: float,
    baseline_stddev: float,
    direction: str,
    threshold: float,
    min_days: int = 3,
) -> bool:
    """Check if the last min_days rows all deviate in the given direction.

    For "body_battery_drain" special case: computes (body_battery_max - body_battery_min)
    from each row as a derived metric.

    Treats None values as non-anomalous (breaks the consecutive streak).

    Args:
        rows: Daily metric rows (oldest to newest).
        metric_name: Metric column name to check.
        baseline_mean: 28-day baseline mean for this metric.
        baseline_stddev: 28-day baseline stddev for this metric.
        direction: "below" or "above" -- expected deviation direction.
        threshold: Number of stddev from mean to qualify as anomalous.
        min_days: Minimum consecutive days required (default 3).

    Returns:
        True if the last min_days rows all deviate as specified.
    """
    recent = rows[-min_days:]
    if len(recent) < min_days:
        return False

    for row in recent:
        # Handle derived metric: body_battery_drain
        if metric_name == "body_battery_drain":
            bb_max = row.get("body_battery_max")
            bb_min = row.get("body_battery_min")
            if bb_max is None or bb_min is None:
                return False
            value = bb_max - bb_min
        else:
            value = row.get(metric_name)

        if value is None:
            return False

        z = compute_z_score(value, baseline_mean, baseline_stddev)

        if direction == "below" and z > -threshold:
            return False
        if direction == "above" and z < threshold:
            return False

    return True


def _make_outlier_alert(
    metric_name: str,
    current_value: float,
    z_score: float,
    trend: MetricTrend,
) -> Alert:
    """Create an Alert for a single-metric extreme outlier.

    Args:
        metric_name: Name of the metric.
        current_value: Today's value.
        z_score: Computed z-score.
        trend: Baseline MetricTrend with avg/stddev.

    Returns:
        Alert with appropriate severity and context.
    """
    config = TRENDED_METRICS.get(metric_name, {})
    lower_is_better = config.get("lower_is_better", False)

    severity = (
        AlertSeverity.CRITICAL
        if abs(z_score) >= EXTREME_OUTLIER_CRITICAL
        else AlertSeverity.WARNING
    )

    # Determine direction context
    direction_word = "above" if z_score > 0 else "below"

    # For lower-is-better metrics, interpret the direction
    if lower_is_better:
        quality = "worse than normal" if z_score > 0 else "better than normal"
    else:
        quality = "better than normal" if z_score > 0 else "worse than normal"

    readable_name = metric_name.replace("_", " ").title()

    return Alert(
        severity=severity,
        title=f"{readable_name} Extreme Outlier",
        description=(
            f"{readable_name} is {abs(z_score):.1f} standard deviations "
            f"{direction_word} your 28-day average ({quality}). "
            f"Current: {current_value:.1f}, Baseline: {trend.avg:.1f} +/- {trend.stddev:.1f}."
        ),
        suggested_action=(
            f"Monitor {readable_name.lower()} closely today. "
            "If this persists for multiple days, adjust your training and recovery plan."
        ),
        pattern_name="single_metric_outlier",
    )


def _get_metric_baseline(
    trends_28d: TrendResult,
    metric_name: str,
) -> tuple[float, float] | None:
    """Get baseline mean and stddev for a metric, handling body_battery_drain.

    For body_battery_drain: computes from body_battery_max and body_battery_min baselines.

    Returns:
        Tuple of (mean, stddev) or None if insufficient data.
    """
    if metric_name == "body_battery_drain":
        max_trend = trends_28d.metrics.get("body_battery_max")
        min_trend = trends_28d.metrics.get("body_battery_min")
        if (
            max_trend is None
            or min_trend is None
            or max_trend.avg is None
            or min_trend.avg is None
            or max_trend.stddev is None
            or min_trend.stddev is None
        ):
            return None
        drain_mean = max_trend.avg - min_trend.avg
        # Combined stddev approximation for drain (max - min)
        drain_stddev = (max_trend.stddev**2 + min_trend.stddev**2) ** 0.5
        if drain_stddev == 0:
            return None
        return drain_mean, drain_stddev

    trend = trends_28d.metrics.get(metric_name)
    if trend is None or trend.avg is None or trend.stddev is None:
        return None
    return trend.avg, trend.stddev


def _check_pattern(
    pattern: ConvergencePattern,
    trends_28d: TrendResult,
    trend_rows: list[dict],
) -> bool:
    """Check if a convergence pattern fires against current data.

    All metric checks in the pattern must pass for the last min_consecutive_days
    rows for the pattern to fire.

    Args:
        pattern: Convergence pattern definition.
        trends_28d: 28-day trend baselines.
        trend_rows: Raw 28-day window rows for consecutive-day checks.

    Returns:
        True if all metric checks pass for consecutive days.
    """
    for metric_check in pattern.metrics:
        baseline = _get_metric_baseline(trends_28d, metric_check.metric_name)
        if baseline is None:
            return False

        baseline_mean, baseline_stddev = baseline
        if baseline_stddev == 0:
            return False

        if not _check_consecutive_days(
            trend_rows,
            metric_check.metric_name,
            baseline_mean,
            baseline_stddev,
            metric_check.direction,
            metric_check.threshold_stddev,
            min_days=pattern.min_consecutive_days,
        ):
            return False

    return True


def _make_convergence_alert(pattern: ConvergencePattern) -> Alert:
    """Create an Alert from a convergence pattern.

    Args:
        pattern: The convergence pattern that fired.

    Returns:
        Alert with pattern details.
    """
    return Alert(
        severity=pattern.severity,
        title=pattern.name.replace("_", " ").title() + " Pattern Detected",
        description=pattern.description,
        suggested_action=pattern.suggested_action,
        pattern_name=pattern.name,
    )


def detect_anomalies(
    today_metrics: Any,
    trends_28d: TrendResult,
    trend_rows: list[dict],
) -> AnomalyResult:
    """Run all anomaly detection checks against 28-day baselines.

    Orchestrates both single-metric extreme outlier detection and multi-metric
    convergence pattern detection.

    Args:
        today_metrics: Today's DailyMetrics (or any object with metric attributes).
        trends_28d: 28-day trend baselines with mean/stddev per metric.
        trend_rows: Raw 28-day window rows for consecutive-day checks.

    Returns:
        AnomalyResult with detected alerts and metrics checked count.
    """
    alerts: list[Alert] = []
    metrics_checked = 0

    # 1. Single-metric extreme outlier checks
    for metric_name, trend in trends_28d.metrics.items():
        if trend.avg is None or trend.stddev is None or trend.stddev == 0:
            continue

        current = getattr(today_metrics, metric_name, None)
        if current is None:
            continue

        metrics_checked += 1
        z = compute_z_score(current, trend.avg, trend.stddev)

        if abs(z) >= EXTREME_OUTLIER_WARNING:
            alerts.append(_make_outlier_alert(metric_name, current, z, trend))

    # 2. Convergence pattern checks
    for pattern in CONVERGENCE_PATTERNS:
        if _check_pattern(pattern, trends_28d, trend_rows):
            alerts.append(_make_convergence_alert(pattern))

    log.info(
        "detect_anomalies",
        alerts_detected=len(alerts),
        metrics_checked=metrics_checked,
    )

    return AnomalyResult(alerts=alerts, metrics_checked=metrics_checked)
