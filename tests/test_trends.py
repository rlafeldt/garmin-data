"""Tests for 7-day rolling trend computation and direction analysis."""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import MagicMock

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

    def test_compute_trends_includes_all_seven_metrics(self, mock_client: MagicMock) -> None:
        result = compute_trends(mock_client, date(2026, 3, 2))
        expected = {
            "hrv_overnight_avg",
            "resting_hr",
            "sleep_score",
            "total_sleep_seconds",
            "body_battery_morning",
            "avg_stress_level",
            "training_load_7d",
        }
        assert set(result.metrics.keys()) == expected

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

    def test_seven_metrics_defined(self) -> None:
        assert len(TRENDED_METRICS) == 7

    def test_lower_is_better_metrics(self) -> None:
        assert TRENDED_METRICS["resting_hr"]["lower_is_better"] is True
        assert TRENDED_METRICS["avg_stress_level"]["lower_is_better"] is True

    def test_higher_is_better_metrics(self) -> None:
        for name in ("hrv_overnight_avg", "sleep_score", "total_sleep_seconds",
                      "body_battery_morning", "training_load_7d"):
            assert TRENDED_METRICS[name]["lower_is_better"] is False, f"{name} should not be lower_is_better"
