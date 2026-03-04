"""Hardcoded convergence pattern definitions for multi-metric anomaly detection.

Five patterns detect simultaneous deviations across multiple health metrics
over 3+ consecutive days, using personal baselines (28-day mean + stddev).
"""

from __future__ import annotations

from biointelligence.anomaly.models import AlertSeverity, ConvergencePattern, MetricCheck

CONVERGENCE_PATTERNS: list[ConvergencePattern] = [
    # Pattern 1: HRV + HR + Sleep convergence
    ConvergencePattern(
        name="hrv_hr_sleep",
        description=(
            "HRV declining, resting heart rate elevated, and sleep quality poor "
            "for 3+ consecutive days -- indicates systemic stress or early illness."
        ),
        suggested_action=(
            "Prioritize recovery: extend sleep by 30-60 min, avoid high-intensity training, "
            "and monitor for illness symptoms."
        ),
        metrics=[
            MetricCheck(metric_name="hrv_overnight_avg", direction="below", threshold_stddev=1.0),
            MetricCheck(metric_name="resting_hr", direction="above", threshold_stddev=1.0),
            MetricCheck(metric_name="sleep_score", direction="below", threshold_stddev=1.0),
        ],
        severity=AlertSeverity.CRITICAL,
    ),
    # Pattern 2: Overtraining signals
    ConvergencePattern(
        name="overtraining",
        description=(
            "Training load elevated while HRV declining and Body Battery not recovering "
            "for 3+ consecutive days -- classic overtraining pattern."
        ),
        suggested_action=(
            "Consider a rest day or light zone 1 session. Reduce training volume "
            "by 30-50% for the next 2-3 days."
        ),
        metrics=[
            MetricCheck(metric_name="training_load_7d", direction="above", threshold_stddev=1.0),
            MetricCheck(metric_name="hrv_overnight_avg", direction="below", threshold_stddev=1.0),
            MetricCheck(
                metric_name="body_battery_morning", direction="below", threshold_stddev=1.0,
            ),
        ],
        severity=AlertSeverity.CRITICAL,
    ),
    # Pattern 3: Sleep debt accumulation
    ConvergencePattern(
        name="sleep_debt",
        description=(
            "Sleep score, total sleep duration, and deep sleep all declining "
            "for 3+ consecutive days -- sleep debt is accumulating."
        ),
        suggested_action=(
            "Set an earlier bedtime tonight. Avoid caffeine after 2 PM and screens "
            "30 min before bed. Consider a short nap if possible."
        ),
        metrics=[
            MetricCheck(metric_name="sleep_score", direction="below", threshold_stddev=1.0),
            MetricCheck(metric_name="total_sleep_seconds", direction="below", threshold_stddev=1.0),
            MetricCheck(metric_name="deep_sleep_seconds", direction="below", threshold_stddev=1.0),
        ],
        severity=AlertSeverity.WARNING,
    ),
    # Pattern 4: Stress escalation
    # NOTE: body_battery_drain is a derived metric (body_battery_max - body_battery_min),
    # handled as a special case in the detector.
    ConvergencePattern(
        name="stress_escalation",
        description=(
            "Average stress level rising, relaxation time dropping, and Body Battery drain "
            "accelerating for 3+ consecutive days -- stress response escalating."
        ),
        suggested_action=(
            "Schedule deliberate recovery: breathing exercises, walk in nature, or "
            "meditation. Reduce commitments where possible."
        ),
        metrics=[
            MetricCheck(metric_name="avg_stress_level", direction="above", threshold_stddev=1.0),
            MetricCheck(metric_name="rest_stress_minutes", direction="below", threshold_stddev=1.0),
            MetricCheck(metric_name="body_battery_drain", direction="above", threshold_stddev=1.0),
        ],
        severity=AlertSeverity.WARNING,
    ),
    # Pattern 5: Recovery stall
    ConvergencePattern(
        name="recovery_stall",
        description=(
            "Body Battery morning charge low, resting heart rate creeping up, and HRV "
            "flat or declining for 3+ consecutive days -- recovery is stalling."
        ),
        suggested_action=(
            "Focus on sleep hygiene and nutrition. Consider magnesium supplementation "
            "and ensure adequate protein intake for recovery."
        ),
        metrics=[
            MetricCheck(
                metric_name="body_battery_morning", direction="below", threshold_stddev=1.0,
            ),
            MetricCheck(metric_name="resting_hr", direction="above", threshold_stddev=1.0),
            MetricCheck(metric_name="hrv_overnight_avg", direction="below", threshold_stddev=1.0),
        ],
        severity=AlertSeverity.WARNING,
    ),
]
