"""Tests for anomaly detection module: z-scores, outliers, convergence patterns."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from biointelligence.trends.models import MetricTrend, TrendDirection, TrendResult


def _make_trend_result(
    metrics: dict[str, MetricTrend] | None = None,
    window_start: date | None = None,
    window_end: date | None = None,
) -> TrendResult:
    """Helper to create a TrendResult with sensible defaults."""
    return TrendResult(
        window_start=window_start or date(2026, 2, 2),
        window_end=window_end or date(2026, 3, 2),
        data_points=28,
        metrics=metrics or {},
    )


def _make_baseline_trend(
    avg: float = 50.0,
    stddev: float = 5.0,
    direction: TrendDirection = TrendDirection.STABLE,
) -> MetricTrend:
    """Helper to create a MetricTrend with baseline values."""
    return MetricTrend(
        avg=avg,
        min_val=avg - 2 * stddev,
        max_val=avg + 2 * stddev,
        stddev=stddev,
        direction=direction,
    )


class TestComputeZScore:
    """Test z-score computation."""

    def test_correct_z_score_positive(self) -> None:
        from biointelligence.anomaly.detector import compute_z_score

        # (65 - 50) / 5 = 3.0
        assert compute_z_score(65.0, 50.0, 5.0) == pytest.approx(3.0)

    def test_correct_z_score_negative(self) -> None:
        from biointelligence.anomaly.detector import compute_z_score

        # (35 - 50) / 5 = -3.0
        assert compute_z_score(35.0, 50.0, 5.0) == pytest.approx(-3.0)

    def test_correct_z_score_zero(self) -> None:
        from biointelligence.anomaly.detector import compute_z_score

        # (50 - 50) / 5 = 0.0
        assert compute_z_score(50.0, 50.0, 5.0) == pytest.approx(0.0)

    def test_returns_zero_when_stddev_is_zero(self) -> None:
        from biointelligence.anomaly.detector import compute_z_score

        assert compute_z_score(65.0, 50.0, 0.0) == 0.0

    def test_fractional_z_score(self) -> None:
        from biointelligence.anomaly.detector import compute_z_score

        # (52.5 - 50) / 5 = 0.5
        assert compute_z_score(52.5, 50.0, 5.0) == pytest.approx(0.5)


class TestSingleMetricOutlier:
    """Test single-metric extreme outlier detection."""

    def test_warning_at_2_5_stddev(self) -> None:
        from biointelligence.anomaly.detector import detect_anomalies
        from biointelligence.anomaly.models import AlertSeverity

        # HRV at 2.6 stddev above mean -> WARNING
        metrics = {"hrv_overnight_avg": _make_baseline_trend(avg=50.0, stddev=5.0)}
        trends = _make_trend_result(metrics=metrics)

        class FakeMetrics:
            hrv_overnight_avg = 63.0  # z = (63-50)/5 = 2.6

        result = detect_anomalies(FakeMetrics(), trends, [])
        warning_alerts = [a for a in result.alerts if a.severity == AlertSeverity.WARNING]
        assert len(warning_alerts) >= 1

    def test_critical_at_3_0_stddev(self) -> None:
        from biointelligence.anomaly.detector import detect_anomalies
        from biointelligence.anomaly.models import AlertSeverity

        # HRV at 3.1 stddev above mean -> CRITICAL
        metrics = {"hrv_overnight_avg": _make_baseline_trend(avg=50.0, stddev=5.0)}
        trends = _make_trend_result(metrics=metrics)

        class FakeMetrics:
            hrv_overnight_avg = 65.5  # z = (65.5-50)/5 = 3.1

        result = detect_anomalies(FakeMetrics(), trends, [])
        critical_alerts = [a for a in result.alerts if a.severity == AlertSeverity.CRITICAL]
        assert len(critical_alerts) >= 1

    def test_no_outlier_within_2_5_stddev(self) -> None:
        from biointelligence.anomaly.detector import detect_anomalies

        # HRV at 1.5 stddev -> no alert
        metrics = {"hrv_overnight_avg": _make_baseline_trend(avg=50.0, stddev=5.0)}
        trends = _make_trend_result(metrics=metrics)

        class FakeMetrics:
            hrv_overnight_avg = 57.5  # z = (57.5-50)/5 = 1.5

        result = detect_anomalies(FakeMetrics(), trends, [])
        outlier_alerts = [a for a in result.alerts if a.pattern_name == "single_metric_outlier"]
        assert len(outlier_alerts) == 0

    def test_outlier_pattern_name(self) -> None:
        from biointelligence.anomaly.detector import detect_anomalies

        metrics = {"hrv_overnight_avg": _make_baseline_trend(avg=50.0, stddev=5.0)}
        trends = _make_trend_result(metrics=metrics)

        class FakeMetrics:
            hrv_overnight_avg = 63.0  # z = 2.6

        result = detect_anomalies(FakeMetrics(), trends, [])
        assert any(a.pattern_name == "single_metric_outlier" for a in result.alerts)


class TestConvergencePatterns:
    """Test convergence pattern detection across 3+ consecutive days."""

    def _make_rows_for_pattern(
        self,
        n_days: int = 5,
        hrv: float = 35.0,
        resting_hr: float = 65.0,
        sleep_score: float = 60.0,
        total_sleep_seconds: float = 20000.0,
        deep_sleep_seconds: float = 3000.0,
        body_battery_morning: float = 40.0,
        avg_stress_level: float = 50.0,
        rest_stress_minutes: float = 100.0,
        training_load_7d: float = 700.0,
        body_battery_max: float = 70.0,
        body_battery_min: float = 10.0,
    ) -> list[dict]:
        """Create rows with consistent anomalous values over n_days."""
        rows = []
        base_date = date(2026, 3, 1)
        for i in range(n_days):
            rows.append({
                "date": (base_date - timedelta(days=n_days - 1 - i)).isoformat(),
                "hrv_overnight_avg": hrv,
                "resting_hr": resting_hr,
                "sleep_score": sleep_score,
                "total_sleep_seconds": total_sleep_seconds,
                "deep_sleep_seconds": deep_sleep_seconds,
                "body_battery_morning": body_battery_morning,
                "avg_stress_level": avg_stress_level,
                "rest_stress_minutes": rest_stress_minutes,
                "training_load_7d": training_load_7d,
                "body_battery_max": body_battery_max,
                "body_battery_min": body_battery_min,
            })
        return rows

    def _make_standard_baselines(self) -> dict[str, MetricTrend]:
        """Create baseline trends for all standard metrics."""
        return {
            "hrv_overnight_avg": _make_baseline_trend(avg=50.0, stddev=5.0),
            "resting_hr": _make_baseline_trend(avg=55.0, stddev=3.0),
            "sleep_score": _make_baseline_trend(avg=80.0, stddev=5.0),
            "total_sleep_seconds": _make_baseline_trend(avg=27000.0, stddev=2000.0),
            "deep_sleep_seconds": _make_baseline_trend(avg=5400.0, stddev=600.0),
            "body_battery_morning": _make_baseline_trend(avg=70.0, stddev=10.0),
            "avg_stress_level": _make_baseline_trend(avg=30.0, stddev=5.0),
            "rest_stress_minutes": _make_baseline_trend(avg=200.0, stddev=30.0),
            "training_load_7d": _make_baseline_trend(avg=500.0, stddev=50.0),
            "body_battery_max": _make_baseline_trend(avg=90.0, stddev=5.0),
            "body_battery_min": _make_baseline_trend(avg=20.0, stddev=5.0),
        }

    def test_hrv_hr_sleep_pattern_fires_on_3_consecutive_days(self) -> None:
        """Pattern 1: HRV below + resting HR above + sleep_score below for 3+ days."""
        from biointelligence.anomaly.detector import detect_anomalies

        baselines = self._make_standard_baselines()
        trends = _make_trend_result(metrics=baselines)

        # HRV well below (z < -1), resting_hr well above (z > 1), sleep_score well below (z < -1)
        rows = self._make_rows_for_pattern(
            n_days=5,
            hrv=38.0,        # z = (38-50)/5 = -2.4 (below 1 SD)
            resting_hr=62.0,  # z = (62-55)/3 = 2.33 (above 1 SD)
            sleep_score=70.0,  # z = (70-80)/5 = -2.0 (below 1 SD)
        )

        class FakeMetrics:
            hrv_overnight_avg = 38.0

        result = detect_anomalies(FakeMetrics(), trends, rows)
        convergence_alerts = [a for a in result.alerts if a.pattern_name != "single_metric_outlier"]
        assert len(convergence_alerts) >= 1

    def test_pattern_does_not_fire_with_fewer_than_3_days(self) -> None:
        """Convergence pattern should NOT fire with only 2 consecutive anomalous days."""
        from biointelligence.anomaly.detector import detect_anomalies

        baselines = self._make_standard_baselines()
        trends = _make_trend_result(metrics=baselines)

        # Only 2 anomalous days, plus 3 normal days before
        rows = []
        base_date = date(2026, 3, 1)
        for i in range(3):
            rows.append({
                "date": (base_date - timedelta(days=4 - i)).isoformat(),
                "hrv_overnight_avg": 50.0,  # Normal
                "resting_hr": 55.0,  # Normal
                "sleep_score": 80.0,  # Normal
                "total_sleep_seconds": 27000.0,
                "deep_sleep_seconds": 5400.0,
                "body_battery_morning": 70.0,
                "avg_stress_level": 30.0,
                "rest_stress_minutes": 200.0,
                "training_load_7d": 500.0,
                "body_battery_max": 90.0,
                "body_battery_min": 20.0,
            })
        for i in range(2):
            rows.append({
                "date": (base_date - timedelta(days=1 - i)).isoformat(),
                "hrv_overnight_avg": 38.0,  # Anomalous
                "resting_hr": 62.0,  # Anomalous
                "sleep_score": 70.0,  # Anomalous
                "total_sleep_seconds": 27000.0,
                "deep_sleep_seconds": 5400.0,
                "body_battery_morning": 70.0,
                "avg_stress_level": 30.0,
                "rest_stress_minutes": 200.0,
                "training_load_7d": 500.0,
                "body_battery_max": 90.0,
                "body_battery_min": 20.0,
            })

        class FakeMetrics:
            hrv_overnight_avg = 38.0

        result = detect_anomalies(FakeMetrics(), trends, rows)
        convergence_alerts = [a for a in result.alerts if a.pattern_name != "single_metric_outlier"]
        # Pattern 1 (HRV+HR+Sleep) and Pattern 5 (Recovery stall) should not fire -- only 2 days
        pattern_names = {a.pattern_name for a in convergence_alerts}
        assert "hrv_hr_sleep" not in pattern_names

    def test_pattern_does_not_fire_when_one_metric_normal(self) -> None:
        """Convergence should NOT fire if one metric in the pattern is within range."""
        from biointelligence.anomaly.detector import detect_anomalies

        baselines = self._make_standard_baselines()
        trends = _make_trend_result(metrics=baselines)

        # HRV below, resting_hr NORMAL, sleep_score below -> HRV+HR+Sleep pattern should NOT fire
        rows = self._make_rows_for_pattern(
            n_days=5,
            hrv=38.0,         # z = -2.4 (anomalous, below)
            resting_hr=55.0,  # z = 0.0 (normal, NOT above threshold)
            sleep_score=70.0,  # z = -2.0 (anomalous, below)
        )

        class FakeMetrics:
            hrv_overnight_avg = 38.0

        result = detect_anomalies(FakeMetrics(), trends, rows)
        convergence_alerts = [a for a in result.alerts if a.pattern_name == "hrv_hr_sleep"]
        assert len(convergence_alerts) == 0

    def test_none_values_break_consecutive_streak(self) -> None:
        """None values in metric data should break the consecutive day streak."""
        from biointelligence.anomaly.detector import detect_anomalies

        baselines = self._make_standard_baselines()
        trends = _make_trend_result(metrics=baselines)

        rows = []
        base_date = date(2026, 3, 1)
        # 2 anomalous days
        for i in range(2):
            rows.append({
                "date": (base_date - timedelta(days=4 - i)).isoformat(),
                "hrv_overnight_avg": 38.0,
                "resting_hr": 62.0,
                "sleep_score": 70.0,
                "total_sleep_seconds": 27000.0,
                "deep_sleep_seconds": 5400.0,
                "body_battery_morning": 70.0,
                "avg_stress_level": 30.0,
                "rest_stress_minutes": 200.0,
                "training_load_7d": 500.0,
                "body_battery_max": 90.0,
                "body_battery_min": 20.0,
            })
        # 1 day with None HRV (breaks streak)
        rows.append({
            "date": (base_date - timedelta(days=2)).isoformat(),
            "hrv_overnight_avg": None,
            "resting_hr": 62.0,
            "sleep_score": 70.0,
            "total_sleep_seconds": 27000.0,
            "deep_sleep_seconds": 5400.0,
            "body_battery_morning": 70.0,
            "avg_stress_level": 30.0,
            "rest_stress_minutes": 200.0,
            "training_load_7d": 500.0,
            "body_battery_max": 90.0,
            "body_battery_min": 20.0,
        })
        # 2 more anomalous days
        for i in range(2):
            rows.append({
                "date": (base_date - timedelta(days=1 - i)).isoformat(),
                "hrv_overnight_avg": 38.0,
                "resting_hr": 62.0,
                "sleep_score": 70.0,
                "total_sleep_seconds": 27000.0,
                "deep_sleep_seconds": 5400.0,
                "body_battery_morning": 70.0,
                "avg_stress_level": 30.0,
                "rest_stress_minutes": 200.0,
                "training_load_7d": 500.0,
                "body_battery_max": 90.0,
                "body_battery_min": 20.0,
            })

        class FakeMetrics:
            hrv_overnight_avg = 38.0

        result = detect_anomalies(FakeMetrics(), trends, rows)
        # HRV+HR+Sleep pattern should not fire -- None breaks the 3-day streak
        pattern_names = {a.pattern_name for a in result.alerts if a.pattern_name != "single_metric_outlier"}
        assert "hrv_hr_sleep" not in pattern_names

    def test_five_convergence_patterns_defined(self) -> None:
        """All 5 hardcoded convergence patterns are defined."""
        from biointelligence.anomaly.patterns import CONVERGENCE_PATTERNS

        assert len(CONVERGENCE_PATTERNS) == 5

    def test_overtraining_pattern_fires(self) -> None:
        """Pattern 2: training_load above + HRV below + body_battery_morning below."""
        from biointelligence.anomaly.detector import detect_anomalies

        baselines = self._make_standard_baselines()
        trends = _make_trend_result(metrics=baselines)

        rows = self._make_rows_for_pattern(
            n_days=5,
            training_load_7d=600.0,    # z = (600-500)/50 = 2.0 (above 1 SD)
            hrv=38.0,                  # z = (38-50)/5 = -2.4 (below 1 SD)
            body_battery_morning=50.0,  # z = (50-70)/10 = -2.0 (below 1 SD)
        )

        class FakeMetrics:
            hrv_overnight_avg = 38.0
            training_load_7d = 600.0
            body_battery_morning = 50.0

        result = detect_anomalies(FakeMetrics(), trends, rows)
        pattern_names = {a.pattern_name for a in result.alerts}
        assert "overtraining" in pattern_names

    def test_sleep_debt_pattern_fires(self) -> None:
        """Pattern 3: sleep_score below + total_sleep below + deep_sleep below."""
        from biointelligence.anomaly.detector import detect_anomalies

        baselines = self._make_standard_baselines()
        trends = _make_trend_result(metrics=baselines)

        rows = self._make_rows_for_pattern(
            n_days=5,
            sleep_score=70.0,          # z = (70-80)/5 = -2.0 (below 1 SD)
            total_sleep_seconds=22000.0,  # z = (22000-27000)/2000 = -2.5 (below 1 SD)
            deep_sleep_seconds=3600.0,    # z = (3600-5400)/600 = -3.0 (below 1 SD)
        )

        class FakeMetrics:
            sleep_score = 70.0
            total_sleep_seconds = 22000.0
            deep_sleep_seconds = 3600.0

        result = detect_anomalies(FakeMetrics(), trends, rows)
        pattern_names = {a.pattern_name for a in result.alerts}
        assert "sleep_debt" in pattern_names


class TestDetectAnomalies:
    """Test the detect_anomalies orchestrator."""

    def test_returns_empty_alerts_when_all_normal(self) -> None:
        from biointelligence.anomaly.detector import detect_anomalies

        metrics = {"hrv_overnight_avg": _make_baseline_trend(avg=50.0, stddev=5.0)}
        trends = _make_trend_result(metrics=metrics)

        class FakeMetrics:
            hrv_overnight_avg = 50.0  # z = 0.0, normal

        rows = [{"hrv_overnight_avg": 50.0} for _ in range(5)]
        result = detect_anomalies(FakeMetrics(), trends, rows)
        assert len(result.alerts) == 0

    def test_returns_combined_outlier_and_convergence_alerts(self) -> None:
        from biointelligence.anomaly.detector import detect_anomalies

        baselines = {
            "hrv_overnight_avg": _make_baseline_trend(avg=50.0, stddev=5.0),
            "resting_hr": _make_baseline_trend(avg=55.0, stddev=3.0),
            "sleep_score": _make_baseline_trend(avg=80.0, stddev=5.0),
            "total_sleep_seconds": _make_baseline_trend(avg=27000.0, stddev=2000.0),
            "deep_sleep_seconds": _make_baseline_trend(avg=5400.0, stddev=600.0),
            "body_battery_morning": _make_baseline_trend(avg=70.0, stddev=10.0),
            "avg_stress_level": _make_baseline_trend(avg=30.0, stddev=5.0),
            "rest_stress_minutes": _make_baseline_trend(avg=200.0, stddev=30.0),
            "training_load_7d": _make_baseline_trend(avg=500.0, stddev=50.0),
            "body_battery_max": _make_baseline_trend(avg=90.0, stddev=5.0),
            "body_battery_min": _make_baseline_trend(avg=20.0, stddev=5.0),
        }
        trends = _make_trend_result(metrics=baselines)

        # Today: HRV extremely low (triggers single-metric outlier AND convergence)
        class FakeMetrics:
            hrv_overnight_avg = 35.0    # z = -3.0 (CRITICAL outlier)
            resting_hr = 62.0           # z = 2.33 (convergence)
            sleep_score = 70.0          # z = -2.0 (convergence)
            total_sleep_seconds = 27000.0
            deep_sleep_seconds = 5400.0
            body_battery_morning = 70.0
            avg_stress_level = 30.0
            rest_stress_minutes = 200.0
            training_load_7d = 500.0
            body_battery_max = 90.0
            body_battery_min = 20.0

        base_date = date(2026, 3, 1)
        rows = []
        for i in range(5):
            rows.append({
                "date": (base_date - timedelta(days=4 - i)).isoformat(),
                "hrv_overnight_avg": 35.0,
                "resting_hr": 62.0,
                "sleep_score": 70.0,
                "total_sleep_seconds": 27000.0,
                "deep_sleep_seconds": 5400.0,
                "body_battery_morning": 70.0,
                "avg_stress_level": 30.0,
                "rest_stress_minutes": 200.0,
                "training_load_7d": 500.0,
                "body_battery_max": 90.0,
                "body_battery_min": 20.0,
            })

        result = detect_anomalies(FakeMetrics(), trends, rows)
        pattern_names = {a.pattern_name for a in result.alerts}
        # Should have at least one single-metric outlier and one convergence
        assert "single_metric_outlier" in pattern_names
        assert len(result.alerts) >= 2

    def test_metrics_checked_count(self) -> None:
        from biointelligence.anomaly.detector import detect_anomalies

        baselines = {
            "hrv_overnight_avg": _make_baseline_trend(avg=50.0, stddev=5.0),
            "resting_hr": _make_baseline_trend(avg=55.0, stddev=3.0),
        }
        trends = _make_trend_result(metrics=baselines)

        class FakeMetrics:
            hrv_overnight_avg = 50.0
            resting_hr = 55.0

        result = detect_anomalies(FakeMetrics(), trends, [])
        assert result.metrics_checked == 2


class TestAlertModel:
    """Test Alert model serialization."""

    def test_alert_serializes_correctly(self) -> None:
        from biointelligence.anomaly.models import Alert, AlertSeverity

        alert = Alert(
            severity=AlertSeverity.WARNING,
            title="Test Alert",
            description="A test description",
            suggested_action="Take a rest day",
            pattern_name="test_pattern",
        )
        data = alert.model_dump()
        assert data["severity"] == "warning"
        assert data["title"] == "Test Alert"
        assert data["description"] == "A test description"
        assert data["suggested_action"] == "Take a rest day"
        assert data["pattern_name"] == "test_pattern"

    def test_anomaly_result_includes_metrics_checked(self) -> None:
        from biointelligence.anomaly.models import AnomalyResult

        result = AnomalyResult(metrics_checked=5)
        assert result.metrics_checked == 5
        assert result.alerts == []

    def test_anomaly_result_default_alerts_empty(self) -> None:
        from biointelligence.anomaly.models import AnomalyResult

        result = AnomalyResult()
        assert result.alerts == []
        assert result.metrics_checked == 0

    def test_alert_severity_enum_values(self) -> None:
        from biointelligence.anomaly.models import AlertSeverity

        assert AlertSeverity.WARNING == "warning"
        assert AlertSeverity.CRITICAL == "critical"


class TestAnomalyPackageExports:
    """Test that the anomaly package exposes the correct public API."""

    def test_detect_anomalies_exported(self) -> None:
        from biointelligence.anomaly import detect_anomalies

        assert callable(detect_anomalies)

    def test_anomaly_result_exported(self) -> None:
        from biointelligence.anomaly import AnomalyResult

        assert AnomalyResult is not None

    def test_alert_exported(self) -> None:
        from biointelligence.anomaly import Alert

        assert Alert is not None

    def test_alert_severity_exported(self) -> None:
        from biointelligence.anomaly import AlertSeverity

        assert AlertSeverity is not None
