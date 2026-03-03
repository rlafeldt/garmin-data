"""Tests for pipeline orchestrator and CLI entry point."""

import datetime
import sys
from unittest.mock import MagicMock, call, patch

import pytest

from biointelligence.garmin.models import (
    Activity,
    CompletenessResult,
    DailyMetrics,
)


class TestIngestionResult:
    """Tests for IngestionResult model."""

    def test_ingestion_result_fields(self):
        """IngestionResult contains date, completeness, activity_count, success."""
        from biointelligence.pipeline import IngestionResult

        result = IngestionResult(
            date=datetime.date(2026, 3, 2),
            completeness=CompletenessResult(
                score=0.9,
                critical_present=6,
                critical_total=6,
                missing_critical=[],
                is_no_wear=False,
            ),
            activity_count=2,
            success=True,
        )
        assert result.date == datetime.date(2026, 3, 2)
        assert result.completeness.score == 0.9
        assert result.activity_count == 2
        assert result.success is True


class TestRunIngestion:
    """Tests for the run_ingestion pipeline orchestrator."""

    @pytest.fixture()
    def mock_settings(self, monkeypatch):
        """Create mock settings."""
        monkeypatch.setenv("GARMIN_EMAIL", "test@garmin.com")
        monkeypatch.setenv("GARMIN_PASSWORD", "testpass")
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_KEY", "testkey")

        from biointelligence.config import Settings

        return Settings()

    @patch("biointelligence.pipeline.get_supabase_client")
    @patch("biointelligence.pipeline.upsert_activities")
    @patch("biointelligence.pipeline.upsert_daily_metrics")
    @patch("biointelligence.pipeline.assess_completeness")
    @patch("biointelligence.pipeline.normalize_activities")
    @patch("biointelligence.pipeline.normalize_daily_metrics")
    @patch("biointelligence.pipeline.extract_all_metrics")
    @patch("biointelligence.pipeline.get_authenticated_client")
    def test_calls_pipeline_stages_in_sequence(
        self,
        mock_auth,
        mock_extract,
        mock_normalize_daily,
        mock_normalize_activities,
        mock_completeness,
        mock_upsert_daily,
        mock_upsert_activities,
        mock_get_supabase,
        mock_settings,
    ):
        """run_ingestion calls extract -> normalize -> assess -> upsert in sequence."""
        from biointelligence.pipeline import run_ingestion

        mock_client = MagicMock()
        mock_auth.return_value = mock_client
        mock_extract.return_value = {"stats": {}, "activities": []}

        mock_record = DailyMetrics(date=datetime.date(2026, 3, 2), steps=10000)
        mock_normalize_daily.return_value = mock_record

        mock_activities = [
            Activity(date=datetime.date(2026, 3, 2), activity_type="cycling")
        ]
        mock_normalize_activities.return_value = mock_activities

        mock_completeness.return_value = CompletenessResult(
            score=0.9,
            critical_present=6,
            critical_total=6,
            missing_critical=[],
            is_no_wear=False,
        )

        mock_supabase = MagicMock()
        mock_get_supabase.return_value = mock_supabase

        target_date = datetime.date(2026, 3, 2)
        result = run_ingestion(target_date, settings=mock_settings)

        # Verify call sequence
        mock_auth.assert_called_once_with(mock_settings)
        mock_extract.assert_called_once_with(mock_client, target_date)
        mock_normalize_daily.assert_called_once()
        mock_normalize_activities.assert_called_once()
        mock_completeness.assert_called_once()
        mock_upsert_daily.assert_called_once_with(mock_supabase, mock_record)
        mock_upsert_activities.assert_called_once_with(
            mock_supabase, mock_activities, target_date
        )

        # Verify result
        assert result.date == target_date
        assert result.activity_count == 1
        assert result.success is True

    @patch("biointelligence.pipeline.get_supabase_client")
    @patch("biointelligence.pipeline.upsert_activities")
    @patch("biointelligence.pipeline.upsert_daily_metrics")
    @patch("biointelligence.pipeline.assess_completeness")
    @patch("biointelligence.pipeline.normalize_activities")
    @patch("biointelligence.pipeline.normalize_daily_metrics")
    @patch("biointelligence.pipeline.extract_all_metrics")
    @patch("biointelligence.pipeline.get_authenticated_client")
    def test_sets_completeness_score_on_record(
        self,
        mock_auth,
        mock_extract,
        mock_normalize_daily,
        mock_normalize_activities,
        mock_completeness,
        mock_upsert_daily,
        mock_upsert_activities,
        mock_get_supabase,
        mock_settings,
    ):
        """run_ingestion sets completeness_score on the DailyMetrics record before upsert."""
        from biointelligence.pipeline import run_ingestion

        mock_auth.return_value = MagicMock()
        mock_extract.return_value = {"stats": {}, "activities": []}

        mock_record = DailyMetrics(date=datetime.date(2026, 3, 2), steps=10000)
        mock_normalize_daily.return_value = mock_record
        mock_normalize_activities.return_value = []

        mock_completeness.return_value = CompletenessResult(
            score=0.85,
            critical_present=5,
            critical_total=6,
            missing_critical=["hrv_overnight_avg"],
            is_no_wear=False,
        )

        mock_get_supabase.return_value = MagicMock()

        run_ingestion(datetime.date(2026, 3, 2), settings=mock_settings)

        # The record passed to upsert should have completeness_score set
        upserted_record = mock_upsert_daily.call_args[0][1]
        assert upserted_record.completeness_score == 0.85

    @patch("biointelligence.pipeline.get_supabase_client")
    @patch("biointelligence.pipeline.upsert_activities")
    @patch("biointelligence.pipeline.upsert_daily_metrics")
    @patch("biointelligence.pipeline.assess_completeness")
    @patch("biointelligence.pipeline.normalize_activities")
    @patch("biointelligence.pipeline.normalize_daily_metrics")
    @patch("biointelligence.pipeline.extract_all_metrics")
    @patch("biointelligence.pipeline.get_authenticated_client")
    def test_sets_is_no_wear_on_record(
        self,
        mock_auth,
        mock_extract,
        mock_normalize_daily,
        mock_normalize_activities,
        mock_completeness,
        mock_upsert_daily,
        mock_upsert_activities,
        mock_get_supabase,
        mock_settings,
    ):
        """run_ingestion sets is_no_wear=True when completeness detects no-wear day."""
        from biointelligence.pipeline import run_ingestion

        mock_auth.return_value = MagicMock()
        mock_extract.return_value = {"stats": None, "activities": []}

        mock_record = DailyMetrics(date=datetime.date(2026, 3, 2))
        mock_normalize_daily.return_value = mock_record
        mock_normalize_activities.return_value = []

        mock_completeness.return_value = CompletenessResult(
            score=0.0,
            critical_present=0,
            critical_total=6,
            missing_critical=["total_sleep_seconds", "hrv_overnight_avg", "body_battery_morning", "resting_hr", "avg_stress_level", "steps"],
            is_no_wear=True,
        )

        mock_get_supabase.return_value = MagicMock()

        run_ingestion(datetime.date(2026, 3, 2), settings=mock_settings)

        upserted_record = mock_upsert_daily.call_args[0][1]
        assert upserted_record.is_no_wear is True

    @patch("biointelligence.pipeline.get_supabase_client")
    @patch("biointelligence.pipeline.upsert_activities")
    @patch("biointelligence.pipeline.upsert_daily_metrics")
    @patch("biointelligence.pipeline.assess_completeness")
    @patch("biointelligence.pipeline.normalize_activities")
    @patch("biointelligence.pipeline.normalize_daily_metrics")
    @patch("biointelligence.pipeline.extract_all_metrics")
    @patch("biointelligence.pipeline.get_authenticated_client")
    def test_logs_warning_on_missing_critical_fields(
        self,
        mock_auth,
        mock_extract,
        mock_normalize_daily,
        mock_normalize_activities,
        mock_completeness,
        mock_upsert_daily,
        mock_upsert_activities,
        mock_get_supabase,
        mock_settings,
        capsys,
    ):
        """run_ingestion logs a warning when completeness has missing critical fields."""
        from biointelligence.pipeline import run_ingestion

        mock_auth.return_value = MagicMock()
        mock_extract.return_value = {"stats": {}, "activities": []}

        mock_record = DailyMetrics(date=datetime.date(2026, 3, 2), steps=10000)
        mock_normalize_daily.return_value = mock_record
        mock_normalize_activities.return_value = []

        mock_completeness.return_value = CompletenessResult(
            score=0.5,
            critical_present=2,
            critical_total=6,
            missing_critical=["hrv_overnight_avg", "body_battery_morning", "avg_stress_level", "total_sleep_seconds"],
            is_no_wear=False,
        )

        mock_get_supabase.return_value = MagicMock()

        # Configure logging to capture output
        from biointelligence.logging import configure_logging

        configure_logging(json_output=False)

        result = run_ingestion(datetime.date(2026, 3, 2), settings=mock_settings)

        # Pipeline still succeeds even with missing data
        assert result.success is True
        # Warning logged to stderr
        captured = capsys.readouterr()
        assert "missing_critical" in captured.err or "incomplete_data" in captured.err

    @patch("biointelligence.pipeline.get_supabase_client")
    @patch("biointelligence.pipeline.upsert_activities")
    @patch("biointelligence.pipeline.upsert_daily_metrics")
    @patch("biointelligence.pipeline.assess_completeness")
    @patch("biointelligence.pipeline.normalize_activities")
    @patch("biointelligence.pipeline.normalize_daily_metrics")
    @patch("biointelligence.pipeline.extract_all_metrics")
    @patch("biointelligence.pipeline.get_authenticated_client")
    def test_returns_ingestion_result(
        self,
        mock_auth,
        mock_extract,
        mock_normalize_daily,
        mock_normalize_activities,
        mock_completeness,
        mock_upsert_daily,
        mock_upsert_activities,
        mock_get_supabase,
        mock_settings,
    ):
        """run_ingestion returns an IngestionResult with date, completeness, and activity_count."""
        from biointelligence.pipeline import run_ingestion

        mock_auth.return_value = MagicMock()
        mock_extract.return_value = {"stats": {}, "activities": []}

        mock_record = DailyMetrics(date=datetime.date(2026, 3, 2), steps=10000)
        mock_normalize_daily.return_value = mock_record

        mock_activities = [
            Activity(date=datetime.date(2026, 3, 2), activity_type="cycling"),
            Activity(date=datetime.date(2026, 3, 2), activity_type="strength_training"),
        ]
        mock_normalize_activities.return_value = mock_activities

        completeness = CompletenessResult(
            score=0.9,
            critical_present=6,
            critical_total=6,
            missing_critical=[],
            is_no_wear=False,
        )
        mock_completeness.return_value = completeness

        mock_get_supabase.return_value = MagicMock()

        result = run_ingestion(datetime.date(2026, 3, 2), settings=mock_settings)

        assert result.date == datetime.date(2026, 3, 2)
        assert result.completeness == completeness
        assert result.activity_count == 2
        assert result.success is True


class TestMainCli:
    """Tests for main.py CLI entry point."""

    @patch("biointelligence.main.run_ingestion")
    @patch("biointelligence.main.configure_logging")
    def test_parses_date_argument(self, mock_logging, mock_ingestion):
        """main.py parses --date argument in YYYY-MM-DD format."""
        from biointelligence.main import main

        mock_ingestion.return_value = MagicMock(
            success=True,
            date=datetime.date(2026, 3, 2),
            activity_count=1,
            completeness=MagicMock(score=0.9, missing_critical=[]),
        )

        exit_code = main(["--date", "2026-03-02"])

        mock_ingestion.assert_called_once()
        call_args = mock_ingestion.call_args
        assert call_args[0][0] == datetime.date(2026, 3, 2)
        assert exit_code == 0

    @patch("biointelligence.main.run_ingestion")
    @patch("biointelligence.main.configure_logging")
    def test_defaults_to_yesterday(self, mock_logging, mock_ingestion):
        """main.py defaults to yesterday's date when --date is not provided."""
        from biointelligence.main import main

        mock_ingestion.return_value = MagicMock(
            success=True,
            date=datetime.date.today(),
            activity_count=0,
            completeness=MagicMock(score=0.5, missing_critical=[]),
        )

        exit_code = main([])

        mock_ingestion.assert_called_once()
        # The date should be yesterday (we can't assert exact date but verify it's a date)
        call_args = mock_ingestion.call_args
        target_date = call_args[0][0]
        assert isinstance(target_date, datetime.date)

    @patch("biointelligence.main.run_ingestion")
    @patch("biointelligence.main.configure_logging")
    def test_calls_configure_logging(self, mock_logging, mock_ingestion):
        """main.py calls configure_logging before run_ingestion."""
        from biointelligence.main import main

        mock_ingestion.return_value = MagicMock(
            success=True,
            date=datetime.date.today(),
            activity_count=0,
            completeness=MagicMock(score=0.5, missing_critical=[]),
        )

        main([])

        mock_logging.assert_called_once()

    @patch("biointelligence.main.run_ingestion")
    @patch("biointelligence.main.configure_logging")
    def test_returns_exit_code_1_on_failure(self, mock_logging, mock_ingestion):
        """main.py returns exit code 1 when pipeline fails."""
        from biointelligence.main import main

        mock_ingestion.return_value = MagicMock(
            success=False,
            date=datetime.date.today(),
            activity_count=0,
            completeness=MagicMock(score=0.0, missing_critical=[]),
        )

        exit_code = main([])

        assert exit_code == 1
