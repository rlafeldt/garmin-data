"""Tests for 7-day and 28-day trend computation and direction analysis."""

from __future__ import annotations

from datetime import date, timedelta
from statistics import stdev
from unittest.mock import MagicMock, patch

import pytest

from biointelligence.trends import TrendDirection, TrendResult, compute_trends
from biointelligence.trends.compute import compute_direction, fetch_trend_window
from biointelligence.trends.models import TRENDED_METRICS, MetricTrend


class TestComputeDirection:
    """Test split-half trend direction computation."""

    def test_improving_values(self) -> None:
        values = [40, 42, 44, 46, 48, 50, 52]
        assert compute_direction(values) == TrendDirection.IMPROVING

    def test_declining_values(self) -> None:
        values = [52, 50, 48, 46, 44, 42, 40]
        assert compute_direction(values) == TrendDirection.DECLINING

    def test_stable_values(self) -> None:
        # Values with < 5% change between halves
        values = [50, 51, 50, 49, 50, 51, 50]
        assert compute_direction(values) == TrendDirection.STABLE

    def test_insufficient_data(self) -> None:
        values = [40, 42, 44]  # Only 3, need at least 4
        assert compute_direction(values) == TrendDirection.INSUFFICIENT

    def test_lower_is_better_declining_is_improving(self) -> None:
        # Resting HR dropping from ~55 to ~50 should be IMPROVING
        values = [56, 55, 54, 53, 51, 50, 49]
        assert compute_direction(values, lower_is_better=True) == TrendDirection.IMPROVING

    def test_lower_is_better_increasing_is_declining(self) -> None:
        # Resting HR rising from ~50 to ~55 should be DECLINING
        values = [49, 50, 51, 52, 54, 55, 56]
        assert compute_direction(values, lower_is_better=True) == TrendDirection.DECLINING

    def test_all_zero_first_half_returns_stable(self) -> None:
        values = [0, 0, 0, 0, 5, 5, 5]
        assert compute_direction(values) == TrendDirection.STABLE

    def test_empty_values_returns_insufficient(self) -> None:
        assert compute_direction([]) == TrendDirection.INSUFFICIENT

    def test_exactly_four_points_works(self) -> None:
        values = [40, 42, 50, 52]
        result = compute_direction(values)
        assert result in {TrendDirection.IMPROVING, TrendDirection.DECLINING, TrendDirection.STABLE}


class TestComputeTrends:
    """Test trend computation with mocked Supabase client."""

    @pytest.fixture()
    def mock_client(self) -> MagicMock:
        """Create a mock Supabase client with realistic 7-day data."""
        client = MagicMock()
        mock_data = []
        base_date = date(2026, 3, 1)
        for i in range(7):
            d = base_date - timedelta(days=6 - i)
            mock_data.append({
                "date": d.isoformat(),
                "hrv_overnight_avg": 45.0 + i * 2,
                "resting_hr": 55 - i,
                "sleep_score": 75 + i,
                "total_sleep_seconds": 25200 + i * 300,
                "body_battery_morning": 60 + i * 3,
                "avg_stress_level": 35 - i,
                "training_load_7d": 400.0 + i * 20,
                "is_no_wear": False,
            })

        response = MagicMock()
        response.data = mock_data
        client.table.return_value.select.return_value.gte.return_value.lt.return_value.eq.return_value.order.return_value.execute.return_value = response
        return client

    @pytest.fixture()
    def empty_client(self) -> MagicMock:
        """Create a mock Supabase client returning empty results."""
        client = MagicMock()
        response = MagicMock()
        response.data = []
        client.table.return_value.select.return_value.gte.return_value.lt.return_value.eq.return_value.order.return_value.execute.return_value = response
        return client

    def test_compute_trends_returns_trend_result(self, mock_client: MagicMock) -> None:
        result = compute_trends(mock_client, date(2026, 3, 2))
        assert isinstance(result, TrendResult)

    def test_compute_trends_correct_window_dates(self, mock_client: MagicMock) -> None:
        target = date(2026, 3, 2)
        result = compute_trends(mock_client, target)
        assert result.window_end == target
        assert result.window_start == target - timedelta(days=7)

    def test_compute_trends_data_points(self, mock_client: MagicMock) -> None:
        result = compute_trends(mock_client, date(2026, 3, 2))
        assert result.data_points == 7

    def test_compute_trends_correct_avg_min_max(self, mock_client: MagicMock) -> None:
        result = compute_trends(mock_client, date(2026, 3, 2))
        hrv = result.metrics["hrv_overnight_avg"]
        # Values: 45, 47, 49, 51, 53, 55, 57
        assert hrv.avg == pytest.approx(51.0)
        assert hrv.min_val == pytest.approx(45.0)
        assert hrv.max_val == pytest.approx(57.0)

    def test_compute_trends_improving_direction(self, mock_client: MagicMock) -> None:
        result = compute_trends(mock_client, date(2026, 3, 2))
        # HRV increasing -> IMPROVING
        assert result.metrics["hrv_overnight_avg"].direction == TrendDirection.IMPROVING

    def test_compute_trends_lower_is_better_correct(self, mock_client: MagicMock) -> None:
        result = compute_trends(mock_client, date(2026, 3, 2))
        # Resting HR decreasing -> IMPROVING (lower is better)
        assert result.metrics["resting_hr"].direction == TrendDirection.IMPROVING
        # Stress decreasing -> IMPROVING (lower is better)
        assert result.metrics["avg_stress_level"].direction == TrendDirection.IMPROVING

    def test_compute_trends_includes_all_trended_metrics(self, mock_client: MagicMock) -> None:
        result = compute_trends(mock_client, date(2026, 3, 2))
        assert set(result.metrics.keys()) == set(TRENDED_METRICS.keys())

    def test_compute_trends_empty_response_all_insufficient(
        self, empty_client: MagicMock
    ) -> None:
        result = compute_trends(empty_client, date(2026, 3, 2))
        for metric_name, trend in result.metrics.items():
            assert trend.direction == TrendDirection.INSUFFICIENT, f"{metric_name} not INSUFFICIENT"
            assert trend.avg is None
            assert trend.min_val is None
            assert trend.max_val is None

    def test_compute_trends_filters_none_values(self) -> None:
        """Test that None values are skipped in aggregation."""
        client = MagicMock()
        mock_data = []
        base_date = date(2026, 3, 1)
        for i in range(7):
            d = base_date - timedelta(days=6 - i)
            row = {
                "date": d.isoformat(),
                "hrv_overnight_avg": 50.0 if i < 5 else None,
                "resting_hr": 55,
                "sleep_score": 80,
                "total_sleep_seconds": 27000,
                "body_battery_morning": 70,
                "avg_stress_level": 30,
                "training_load_7d": 500.0,
                "is_no_wear": False,
            }
            mock_data.append(row)

        response = MagicMock()
        response.data = mock_data
        client.table.return_value.select.return_value.gte.return_value.lt.return_value.eq.return_value.order.return_value.execute.return_value = response

        result = compute_trends(client, date(2026, 3, 2))
        # HRV should have 5 valid points, not 7
        hrv = result.metrics["hrv_overnight_avg"]
        assert hrv.avg == pytest.approx(50.0)
        assert hrv.min_val == pytest.approx(50.0)
        assert hrv.max_val == pytest.approx(50.0)


class TestFetchTrendWindow:
    """Test Supabase query construction for trend data fetching."""

    def test_fetch_calls_supabase_with_correct_parameters(self) -> None:
        client = MagicMock()
        response = MagicMock()
        response.data = []

        chain = client.table.return_value.select.return_value
        chain.gte.return_value.lt.return_value.eq.return_value.order.return_value.execute.return_value = response

        target = date(2026, 3, 2)
        fetch_trend_window(client, target)

        client.table.assert_called_once_with("daily_metrics")
        chain.gte.assert_called_once_with("date", "2026-02-23")
        chain.gte.return_value.lt.assert_called_once_with("date", "2026-03-02")
        chain.gte.return_value.lt.return_value.eq.assert_called_once_with("is_no_wear", False)

    def test_fetch_returns_response_data(self) -> None:
        client = MagicMock()
        expected = [{"date": "2026-03-01", "hrv_overnight_avg": 50}]
        response = MagicMock()
        response.data = expected

        client.table.return_value.select.return_value.gte.return_value.lt.return_value.eq.return_value.order.return_value.execute.return_value = response

        result = fetch_trend_window(client, date(2026, 3, 2))
        assert result == expected


class TestTrendedMetricsConfig:
    """Test TRENDED_METRICS configuration."""

    def test_eleven_metrics_defined(self) -> None:
        assert len(TRENDED_METRICS) == 11

    def test_lower_is_better_metrics(self) -> None:
        assert TRENDED_METRICS["resting_hr"]["lower_is_better"] is True
        assert TRENDED_METRICS["avg_stress_level"]["lower_is_better"] is True

    def test_higher_is_better_metrics(self) -> None:
        for name in ("hrv_overnight_avg", "sleep_score", "total_sleep_seconds",
                      "body_battery_morning", "training_load_7d"):
            assert TRENDED_METRICS[name]["lower_is_better"] is False, f"{name} should not be lower_is_better"

    def test_new_convergence_metrics_present(self) -> None:
        """Test that 4 additional metrics for convergence patterns are in TRENDED_METRICS."""
        for name in ("deep_sleep_seconds", "rest_stress_minutes",
                      "body_battery_max", "body_battery_min"):
            assert name in TRENDED_METRICS, f"{name} missing from TRENDED_METRICS"

    def test_new_convergence_metrics_directionality(self) -> None:
        """Test lower_is_better flags for the 4 new convergence metrics."""
        assert TRENDED_METRICS["deep_sleep_seconds"]["lower_is_better"] is False
        assert TRENDED_METRICS["rest_stress_minutes"]["lower_is_better"] is False
        assert TRENDED_METRICS["body_battery_max"]["lower_is_better"] is False
        assert TRENDED_METRICS["body_battery_min"]["lower_is_better"] is False


class TestMetricTrendStddev:
    """Test MetricTrend model extension with stddev field."""

    def test_stddev_field_defaults_to_none(self) -> None:
        trend = MetricTrend()
        assert trend.stddev is None

    def test_stddev_field_accepts_float(self) -> None:
        trend = MetricTrend(avg=50.0, stddev=5.2)
        assert trend.stddev == pytest.approx(5.2)

    def test_existing_fields_still_work(self) -> None:
        trend = MetricTrend(avg=50.0, min_val=40.0, max_val=60.0, direction=TrendDirection.IMPROVING)
        assert trend.avg == 50.0
        assert trend.min_val == 40.0
        assert trend.max_val == 60.0
        assert trend.direction == TrendDirection.IMPROVING
        assert trend.stddev is None


class TestTrendFieldsExpansion:
    """Test that TREND_FIELDS includes the 4 additional columns for convergence patterns."""

    def test_trend_fields_includes_deep_sleep(self) -> None:
        from biointelligence.trends.compute import TREND_FIELDS
        assert "deep_sleep_seconds" in TREND_FIELDS

    def test_trend_fields_includes_rest_stress(self) -> None:
        from biointelligence.trends.compute import TREND_FIELDS
        assert "rest_stress_minutes" in TREND_FIELDS

    def test_trend_fields_includes_body_battery_max(self) -> None:
        from biointelligence.trends.compute import TREND_FIELDS
        assert "body_battery_max" in TREND_FIELDS

    def test_trend_fields_includes_body_battery_min(self) -> None:
        from biointelligence.trends.compute import TREND_FIELDS
        assert "body_battery_min" in TREND_FIELDS


class TestComputeExtendedTrends:
    """Test 28-day extended trend computation with stddev."""

    @pytest.fixture()
    def mock_28d_client(self) -> MagicMock:
        """Create a mock Supabase client with realistic 28-day data."""
        client = MagicMock()
        mock_data = []
        base_date = date(2026, 3, 1)
        for i in range(28):
            d = base_date - timedelta(days=27 - i)
            mock_data.append({
                "date": d.isoformat(),
                "hrv_overnight_avg": 45.0 + (i % 7) * 2,
                "resting_hr": 55 - (i % 5),
                "sleep_score": 75 + (i % 6),
                "total_sleep_seconds": 25200 + (i % 4) * 300,
                "body_battery_morning": 60 + (i % 5) * 3,
                "avg_stress_level": 35 - (i % 4),
                "training_load_7d": 400.0 + (i % 6) * 20,
                "deep_sleep_seconds": 5400 + (i % 4) * 300,
                "rest_stress_minutes": 180 + (i % 5) * 10,
                "body_battery_max": 85 + (i % 4) * 3,
                "body_battery_min": 15 + (i % 3) * 5,
                "is_no_wear": False,
            })

        response = MagicMock()
        response.data = mock_data
        client.table.return_value.select.return_value.gte.return_value.lt.return_value.eq.return_value.order.return_value.execute.return_value = response
        return client

    @pytest.fixture()
    def sparse_client(self) -> MagicMock:
        """Create a mock Supabase client with only 10 days of data (< 14 min)."""
        client = MagicMock()
        mock_data = []
        base_date = date(2026, 3, 1)
        for i in range(10):
            d = base_date - timedelta(days=9 - i)
            mock_data.append({
                "date": d.isoformat(),
                "hrv_overnight_avg": 50.0 + i,
                "resting_hr": 55,
                "sleep_score": 80,
                "total_sleep_seconds": 27000,
                "body_battery_morning": 70,
                "avg_stress_level": 30,
                "training_load_7d": 500.0,
                "deep_sleep_seconds": 5400,
                "rest_stress_minutes": 200,
                "body_battery_max": 90,
                "body_battery_min": 20,
                "is_no_wear": False,
            })

        response = MagicMock()
        response.data = mock_data
        client.table.return_value.select.return_value.gte.return_value.lt.return_value.eq.return_value.order.return_value.execute.return_value = response
        return client

    @pytest.fixture()
    def exactly_14_client(self) -> MagicMock:
        """Create a mock Supabase client with exactly 14 days of data."""
        client = MagicMock()
        mock_data = []
        base_date = date(2026, 3, 1)
        for i in range(14):
            d = base_date - timedelta(days=13 - i)
            mock_data.append({
                "date": d.isoformat(),
                "hrv_overnight_avg": 45.0 + i,
                "resting_hr": 55 - (i % 5),
                "sleep_score": 75 + (i % 6),
                "total_sleep_seconds": 25200 + i * 100,
                "body_battery_morning": 60 + i,
                "avg_stress_level": 35 - (i % 4),
                "training_load_7d": 400.0 + i * 10,
                "deep_sleep_seconds": 5400 + i * 50,
                "rest_stress_minutes": 180 + i * 5,
                "body_battery_max": 85 + (i % 4),
                "body_battery_min": 15 + (i % 3),
                "is_no_wear": False,
            })

        response = MagicMock()
        response.data = mock_data
        client.table.return_value.select.return_value.gte.return_value.lt.return_value.eq.return_value.order.return_value.execute.return_value = response
        return client

    @pytest.fixture()
    def identical_values_client(self) -> MagicMock:
        """Create a mock Supabase client where all metric values are identical."""
        client = MagicMock()
        mock_data = []
        base_date = date(2026, 3, 1)
        for i in range(28):
            d = base_date - timedelta(days=27 - i)
            mock_data.append({
                "date": d.isoformat(),
                "hrv_overnight_avg": 50.0,
                "resting_hr": 55,
                "sleep_score": 80,
                "total_sleep_seconds": 27000,
                "body_battery_morning": 70,
                "avg_stress_level": 30,
                "training_load_7d": 500.0,
                "deep_sleep_seconds": 5400,
                "rest_stress_minutes": 200,
                "body_battery_max": 90,
                "body_battery_min": 20,
                "is_no_wear": False,
            })

        response = MagicMock()
        response.data = mock_data
        client.table.return_value.select.return_value.gte.return_value.lt.return_value.eq.return_value.order.return_value.execute.return_value = response
        return client

    def test_returns_trend_result(self, mock_28d_client: MagicMock) -> None:
        from biointelligence.trends.compute import compute_extended_trends

        result = compute_extended_trends(mock_28d_client, date(2026, 3, 2))
        assert isinstance(result, TrendResult)

    def test_28d_data_returns_stddev_populated(self, mock_28d_client: MagicMock) -> None:
        from biointelligence.trends.compute import compute_extended_trends

        result = compute_extended_trends(mock_28d_client, date(2026, 3, 2))
        for metric_name, trend in result.metrics.items():
            assert trend.stddev is not None, f"{metric_name} has None stddev"
            assert trend.stddev >= 0.0, f"{metric_name} has negative stddev"

    def test_28d_data_returns_avg_min_max(self, mock_28d_client: MagicMock) -> None:
        from biointelligence.trends.compute import compute_extended_trends

        result = compute_extended_trends(mock_28d_client, date(2026, 3, 2))
        for metric_name, trend in result.metrics.items():
            assert trend.avg is not None, f"{metric_name} has None avg"
            assert trend.min_val is not None, f"{metric_name} has None min_val"
            assert trend.max_val is not None, f"{metric_name} has None max_val"

    def test_insufficient_data_returns_insufficient_direction(
        self, sparse_client: MagicMock
    ) -> None:
        from biointelligence.trends.compute import compute_extended_trends

        result = compute_extended_trends(sparse_client, date(2026, 3, 2))
        for metric_name, trend in result.metrics.items():
            assert trend.direction == TrendDirection.INSUFFICIENT, (
                f"{metric_name} should be INSUFFICIENT with only 10 data points"
            )
            assert trend.avg is None
            assert trend.min_val is None
            assert trend.max_val is None
            assert trend.stddev is None

    def test_exactly_14_data_points_succeeds(
        self, exactly_14_client: MagicMock
    ) -> None:
        from biointelligence.trends.compute import compute_extended_trends

        result = compute_extended_trends(exactly_14_client, date(2026, 3, 2))
        assert result.data_points == 14
        for metric_name, trend in result.metrics.items():
            assert trend.direction != TrendDirection.INSUFFICIENT, (
                f"{metric_name} should not be INSUFFICIENT with 14 data points"
            )
            assert trend.stddev is not None

    def test_identical_values_produce_zero_stddev(
        self, identical_values_client: MagicMock
    ) -> None:
        from biointelligence.trends.compute import compute_extended_trends

        result = compute_extended_trends(identical_values_client, date(2026, 3, 2))
        for metric_name, trend in result.metrics.items():
            assert trend.stddev == pytest.approx(0.0), (
                f"{metric_name} should have stddev=0.0 with identical values"
            )

    def test_uses_sample_stdev_not_pstdev(self, mock_28d_client: MagicMock) -> None:
        """Verify compute_extended_trends uses statistics.stdev (sample) not pstdev."""
        from biointelligence.trends.compute import compute_extended_trends

        result = compute_extended_trends(mock_28d_client, date(2026, 3, 2))
        # Manually compute sample stdev for hrv_overnight_avg
        hrv_values = [45.0 + (i % 7) * 2 for i in range(28)]
        expected_stddev = stdev(hrv_values)
        assert result.metrics["hrv_overnight_avg"].stddev == pytest.approx(expected_stddev)

    def test_existing_compute_trends_still_works(self, mock_28d_client: MagicMock) -> None:
        """Ensure existing compute_trends function is not broken by new changes."""
        # Reuse 28d client for 7-day trends (it just returns whatever data is set)
        result = compute_trends(mock_28d_client, date(2026, 3, 2))
        assert isinstance(result, TrendResult)
        assert "hrv_overnight_avg" in result.metrics

    def test_window_dates_correct(self, mock_28d_client: MagicMock) -> None:
        from biointelligence.trends.compute import compute_extended_trends

        target = date(2026, 3, 2)
        result = compute_extended_trends(mock_28d_client, target)
        assert result.window_end == target
        assert result.window_start == target - timedelta(days=28)

    def test_data_points_count(self, mock_28d_client: MagicMock) -> None:
        from biointelligence.trends.compute import compute_extended_trends

        result = compute_extended_trends(mock_28d_client, date(2026, 3, 2))
        assert result.data_points == 28

    def test_includes_all_eleven_metrics(self, mock_28d_client: MagicMock) -> None:
        from biointelligence.trends.compute import compute_extended_trends

        result = compute_extended_trends(mock_28d_client, date(2026, 3, 2))
        assert set(result.metrics.keys()) == set(TRENDED_METRICS.keys())

    def test_exported_from_trends_package(self) -> None:
        """Verify compute_extended_trends is exported from trends/__init__.py."""
        from biointelligence.trends import compute_extended_trends

        assert callable(compute_extended_trends)
