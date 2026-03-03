"""Tests for Garmin metric extraction with retry and error isolation."""

import datetime
from unittest.mock import MagicMock

from garminconnect import GarminConnectConnectionError, GarminConnectTooManyRequestsError

from biointelligence.garmin.extractors import _fetch_with_retry, extract_all_metrics


class TestFetchWithRetry:
    """Tests for the retry-decorated fetch helper."""

    def test_successful_fetch(self):
        """A successful fetch returns the API response."""
        mock_client = MagicMock()
        mock_client.get_stats.return_value = {"steps": 10000}

        result = _fetch_with_retry(mock_client, "get_stats", "2026-03-02")

        assert result == {"steps": 10000}
        mock_client.get_stats.assert_called_once_with("2026-03-02")

    def test_retries_on_connection_error(self):
        """Retry is triggered on GarminConnectConnectionError."""
        mock_client = MagicMock()
        mock_client.get_stats.side_effect = [
            GarminConnectConnectionError("Connection failed"),
            {"steps": 10000},
        ]

        result = _fetch_with_retry(mock_client, "get_stats", "2026-03-02")

        assert result == {"steps": 10000}
        assert mock_client.get_stats.call_count == 2

    def test_retries_on_too_many_requests(self):
        """Retry is triggered on GarminConnectTooManyRequestsError."""
        mock_client = MagicMock()
        mock_client.get_stats.side_effect = [
            GarminConnectTooManyRequestsError("Rate limited"),
            {"steps": 5000},
        ]

        result = _fetch_with_retry(mock_client, "get_stats", "2026-03-02")

        assert result == {"steps": 5000}
        assert mock_client.get_stats.call_count == 2


class TestExtractAllMetrics:
    """Tests for the full metric extraction pipeline."""

    def test_calls_all_11_endpoints_plus_activities(self):
        """All 11 metric endpoints and activities are called."""
        mock_client = MagicMock()
        # Set up all method returns
        mock_client.get_stats.return_value = {"totalSteps": 10000}
        mock_client.get_heart_rates.return_value = {"restingHeartRate": 52}
        mock_client.get_sleep_data.return_value = {"dailySleepDTO": {}}
        mock_client.get_hrv_data.return_value = {"hrvSummary": {}}
        mock_client.get_body_battery.return_value = [{"bodyBatteryLevel": 85}]
        mock_client.get_stress_data.return_value = {"overallStressLevel": 35}
        mock_client.get_spo2_data.return_value = {"averageSpO2": 96.5}
        mock_client.get_respiration_data.return_value = {"avgWakingRespirationValue": 15.0}
        mock_client.get_training_status.return_value = {"trainingStatusFeedback": "PRODUCTIVE"}
        mock_client.get_training_readiness.return_value = {"score": 72}
        mock_client.get_max_metrics.return_value = {"generic": {"vo2MaxPreciseValue": 52.0}}
        mock_client.get_activities_by_date.return_value = []

        target_date = datetime.date(2026, 3, 2)
        raw = extract_all_metrics(mock_client, target_date)

        # Verify all 11 endpoints + activities were called
        assert "stats" in raw
        assert "heart_rates" in raw
        assert "sleep" in raw
        assert "hrv" in raw
        assert "body_battery" in raw
        assert "stress" in raw
        assert "spo2" in raw
        assert "respiration" in raw
        assert "training_status" in raw
        assert "training_readiness" in raw
        assert "max_metrics" in raw
        assert "activities" in raw

        mock_client.get_stats.assert_called_once_with("2026-03-02")
        mock_client.get_activities_by_date.assert_called_once_with("2026-03-02", "2026-03-02")

    def test_per_category_error_isolation(self):
        """When one endpoint fails, others still succeed."""
        mock_client = MagicMock()
        mock_client.get_stats.return_value = {"totalSteps": 10000}
        mock_client.get_heart_rates.side_effect = Exception("Server error")
        mock_client.get_sleep_data.return_value = {"dailySleepDTO": {}}
        mock_client.get_hrv_data.side_effect = Exception("Timeout")
        mock_client.get_body_battery.return_value = [{"bodyBatteryLevel": 85}]
        mock_client.get_stress_data.return_value = {"overallStressLevel": 35}
        mock_client.get_spo2_data.return_value = {"averageSpO2": 96.5}
        mock_client.get_respiration_data.return_value = {"avgWakingRespirationValue": 15.0}
        mock_client.get_training_status.return_value = {"trainingStatusFeedback": "PRODUCTIVE"}
        mock_client.get_training_readiness.return_value = {"score": 72}
        mock_client.get_max_metrics.return_value = {"generic": {}}
        mock_client.get_activities_by_date.return_value = []

        target_date = datetime.date(2026, 3, 2)
        raw = extract_all_metrics(mock_client, target_date)

        # Successful endpoints have data
        assert raw["stats"] == {"totalSteps": 10000}
        assert raw["sleep"] == {"dailySleepDTO": {}}
        assert raw["body_battery"] == [{"bodyBatteryLevel": 85}]

        # Failed endpoints return None
        assert raw["heart_rates"] is None
        assert raw["hrv"] is None

    def test_failed_endpoints_return_none(self):
        """Failed endpoints set None in the raw dict, not raise."""
        mock_client = MagicMock()
        # All endpoints fail
        for method_name in [
            "get_stats", "get_heart_rates", "get_sleep_data", "get_hrv_data",
            "get_body_battery", "get_stress_data", "get_spo2_data",
            "get_respiration_data", "get_training_status", "get_training_readiness",
            "get_max_metrics",
        ]:
            getattr(mock_client, method_name).side_effect = Exception("Failed")
        mock_client.get_activities_by_date.side_effect = Exception("Failed")

        target_date = datetime.date(2026, 3, 2)
        raw = extract_all_metrics(mock_client, target_date)

        # All metric endpoints should be None
        for key in [
            "stats", "heart_rates", "sleep", "hrv", "body_battery",
            "stress", "spo2", "respiration", "training_status",
            "training_readiness", "max_metrics",
        ]:
            assert raw[key] is None, f"{key} should be None when endpoint fails"

        # Activities should be empty list when failed
        assert raw["activities"] == []
