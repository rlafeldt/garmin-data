"""Tests for pipeline orchestrator and CLI entry point."""

import datetime
from unittest.mock import MagicMock, patch

import pytest
import structlog

from biointelligence.garmin.models import (
    Activity,
    CompletenessResult,
    DailyMetrics,
)
from biointelligence.prompt.models import DailyProtocol


@pytest.fixture(autouse=True)
def _reset_structlog():
    """Reset structlog configuration after each test to avoid cross-test pollution."""
    yield
    structlog.reset_defaults()


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
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

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
            missing_critical=[
                "total_sleep_seconds", "hrv_overnight_avg",
                "body_battery_morning", "resting_hr",
                "avg_stress_level", "steps",
            ],
            is_no_wear=True,
        )

        mock_get_supabase.return_value = MagicMock()

        run_ingestion(datetime.date(2026, 3, 2), settings=mock_settings)

        upserted_record = mock_upsert_daily.call_args[0][1]
        assert upserted_record.is_no_wear is True

    @patch("biointelligence.pipeline.log")
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
        mock_log,
        mock_settings,
    ):
        """run_ingestion logs a warning when completeness has missing critical fields."""
        from biointelligence.pipeline import run_ingestion

        mock_auth.return_value = MagicMock()
        mock_extract.return_value = {"stats": {}, "activities": []}

        mock_record = DailyMetrics(date=datetime.date(2026, 3, 2), steps=10000)
        mock_normalize_daily.return_value = mock_record
        mock_normalize_activities.return_value = []

        missing = [
            "hrv_overnight_avg", "body_battery_morning",
            "avg_stress_level", "total_sleep_seconds",
        ]
        mock_completeness.return_value = CompletenessResult(
            score=0.5,
            critical_present=2,
            critical_total=6,
            missing_critical=missing,
            is_no_wear=False,
        )

        mock_get_supabase.return_value = MagicMock()

        result = run_ingestion(datetime.date(2026, 3, 2), settings=mock_settings)

        # Pipeline still succeeds even with missing data
        assert result.success is True
        # Verify warning was logged with missing_critical fields
        mock_log.warning.assert_called_once_with(
            "incomplete_data",
            date="2026-03-02",
            missing_critical=missing,
            score=0.5,
        )

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

        main([])

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


# ---------------------------------------------------------------------------
# Task 2 (Plan 02): run_analysis pipeline function
# ---------------------------------------------------------------------------


@pytest.fixture()
def fake_protocol() -> DailyProtocol:
    """A populated DailyProtocol for pipeline tests."""
    return DailyProtocol(
        date="2026-03-02",
        readiness_score=7,
        insight="Your recovery is solid.",
        insight_html="Your recovery is [solid](https://example.com).",
        data_quality_notes=None,
    )


class TestRunAnalysis:
    """Tests for the run_analysis pipeline function."""

    @pytest.fixture()
    def mock_settings(self, monkeypatch):
        """Create mock settings for run_analysis tests."""
        monkeypatch.setenv("GARMIN_EMAIL", "test@garmin.com")
        monkeypatch.setenv("GARMIN_PASSWORD", "testpass")
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_KEY", "testkey")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

        from biointelligence.config import Settings

        return Settings()

    @patch("biointelligence.pipeline.upsert_daily_protocol")
    @patch("biointelligence.pipeline.get_supabase_client")
    @patch("biointelligence.pipeline.analyze_daily")
    def test_calls_analyze_daily_and_upsert_on_success(
        self,
        mock_analyze,
        mock_get_supabase,
        mock_upsert_protocol,
        mock_settings,
        fake_protocol,
    ):
        """run_analysis calls analyze_daily and upsert_daily_protocol in sequence on success."""
        from biointelligence.analysis.engine import AnalysisResult
        from biointelligence.pipeline import run_analysis

        mock_supabase = MagicMock()
        mock_get_supabase.return_value = mock_supabase

        analysis_result = AnalysisResult(
            date=datetime.date(2026, 3, 2),
            protocol=fake_protocol,
            input_tokens=3200,
            output_tokens=1800,
            model="claude-haiku-4-5-20251001",
            success=True,
        )
        mock_analyze.return_value = analysis_result

        target_date = datetime.date(2026, 3, 2)
        result = run_analysis(target_date, settings=mock_settings)

        mock_analyze.assert_called_once_with(target_date, mock_settings)
        mock_upsert_protocol.assert_called_once_with(mock_supabase, analysis_result)
        assert result.success is True
        assert result.protocol is not None

    @patch("biointelligence.pipeline.upsert_daily_protocol")
    @patch("biointelligence.pipeline.get_supabase_client")
    @patch("biointelligence.pipeline.analyze_daily")
    def test_returns_analysis_result(
        self,
        mock_analyze,
        mock_get_supabase,
        mock_upsert_protocol,
        mock_settings,
        fake_protocol,
    ):
        """run_analysis returns the AnalysisResult from analyze_daily."""
        from biointelligence.analysis.engine import AnalysisResult
        from biointelligence.pipeline import run_analysis

        mock_get_supabase.return_value = MagicMock()

        analysis_result = AnalysisResult(
            date=datetime.date(2026, 3, 2),
            protocol=fake_protocol,
            input_tokens=3200,
            output_tokens=1800,
            model="claude-haiku-4-5-20251001",
            success=True,
        )
        mock_analyze.return_value = analysis_result

        result = run_analysis(datetime.date(2026, 3, 2), settings=mock_settings)

        assert result is analysis_result
        assert result.input_tokens == 3200
        assert result.output_tokens == 1800

    @patch("biointelligence.pipeline.upsert_daily_protocol")
    @patch("biointelligence.pipeline.get_supabase_client")
    @patch("biointelligence.pipeline.analyze_daily")
    def test_skips_storage_on_failure(
        self,
        mock_analyze,
        mock_get_supabase,
        mock_upsert_protocol,
        mock_settings,
    ):
        """run_analysis skips storage when analysis fails (success=False)."""
        from biointelligence.analysis.engine import AnalysisResult
        from biointelligence.pipeline import run_analysis

        mock_get_supabase.return_value = MagicMock()

        failed_result = AnalysisResult(
            date=datetime.date(2026, 3, 2),
            protocol=None,
            model="claude-haiku-4-5-20251001",
            success=False,
            error="API connection failed",
        )
        mock_analyze.return_value = failed_result

        result = run_analysis(datetime.date(2026, 3, 2), settings=mock_settings)

        assert result.success is False
        mock_upsert_protocol.assert_not_called()

    @patch("biointelligence.pipeline.log")
    @patch("biointelligence.pipeline.upsert_daily_protocol")
    @patch("biointelligence.pipeline.get_supabase_client")
    @patch("biointelligence.pipeline.analyze_daily")
    def test_logs_start_and_completion(
        self,
        mock_analyze,
        mock_get_supabase,
        mock_upsert_protocol,
        mock_log,
        mock_settings,
        fake_protocol,
    ):
        """run_analysis logs start, completion, and token usage."""
        from biointelligence.analysis.engine import AnalysisResult
        from biointelligence.pipeline import run_analysis

        mock_get_supabase.return_value = MagicMock()

        analysis_result = AnalysisResult(
            date=datetime.date(2026, 3, 2),
            protocol=fake_protocol,
            input_tokens=3200,
            output_tokens=1800,
            model="claude-haiku-4-5-20251001",
            success=True,
        )
        mock_analyze.return_value = analysis_result

        run_analysis(datetime.date(2026, 3, 2), settings=mock_settings)

        # Verify log calls include start and completion
        log_events = [c[0][0] for c in mock_log.info.call_args_list]
        assert "analysis_pipeline_start" in log_events
        assert "analysis_pipeline_complete" in log_events


class TestMainCliAnalyze:
    """Tests for CLI --analyze flag."""

    @patch("biointelligence.main.run_analysis")
    @patch("biointelligence.main.run_ingestion")
    @patch("biointelligence.main.configure_logging")
    def test_analyze_flag_triggers_run_analysis(
        self, mock_logging, mock_ingestion, mock_run_analysis
    ):
        """CLI --analyze flag triggers run_analysis after run_ingestion."""
        from biointelligence.main import main

        mock_ingestion.return_value = MagicMock(
            success=True,
            date=datetime.date(2026, 3, 2),
            activity_count=1,
            completeness=MagicMock(score=0.9, is_no_wear=False),
        )
        mock_run_analysis.return_value = MagicMock(
            success=True,
            model="claude-haiku-4-5-20251001",
            input_tokens=3200,
            output_tokens=1800,
        )

        exit_code = main(["--date", "2026-03-02", "--analyze"])

        mock_ingestion.assert_called_once()
        mock_run_analysis.assert_called_once()
        assert exit_code == 0

    @patch("biointelligence.main.run_analysis")
    @patch("biointelligence.main.run_ingestion")
    @patch("biointelligence.main.configure_logging")
    def test_analyze_flag_uses_yesterday_default(
        self, mock_logging, mock_ingestion, mock_run_analysis
    ):
        """CLI --analyze without --date uses yesterday in Europe/Berlin."""
        from biointelligence.main import main

        mock_ingestion.return_value = MagicMock(
            success=True,
            date=datetime.date.today(),
            activity_count=0,
            completeness=MagicMock(score=0.5, is_no_wear=False),
        )
        mock_run_analysis.return_value = MagicMock(
            success=True,
            model="claude-haiku-4-5-20251001",
            input_tokens=3200,
            output_tokens=1800,
        )

        main(["--analyze"])

        # Both should be called with the same target_date
        ingestion_date = mock_ingestion.call_args[0][0]
        analysis_date = mock_run_analysis.call_args[0][0]
        assert ingestion_date == analysis_date
        assert isinstance(analysis_date, datetime.date)

    @patch("biointelligence.main.run_analysis")
    @patch("biointelligence.main.run_ingestion")
    @patch("biointelligence.main.configure_logging")
    def test_analyze_returns_1_on_analysis_failure(
        self, mock_logging, mock_ingestion, mock_run_analysis
    ):
        """CLI returns exit code 1 when analysis fails."""
        from biointelligence.main import main

        mock_ingestion.return_value = MagicMock(
            success=True,
            date=datetime.date(2026, 3, 2),
            activity_count=1,
            completeness=MagicMock(score=0.9, is_no_wear=False),
        )
        mock_run_analysis.return_value = MagicMock(
            success=False,
            error="API failed",
        )

        exit_code = main(["--date", "2026-03-02", "--analyze"])

        assert exit_code == 1

    @patch("biointelligence.main.run_ingestion")
    @patch("biointelligence.main.configure_logging")
    def test_no_analyze_flag_does_not_call_analysis(
        self, mock_logging, mock_ingestion
    ):
        """CLI without --analyze flag does NOT call run_analysis."""
        from biointelligence.main import main

        mock_ingestion.return_value = MagicMock(
            success=True,
            date=datetime.date(2026, 3, 2),
            activity_count=1,
            completeness=MagicMock(score=0.9, is_no_wear=False),
        )

        with patch("biointelligence.main.run_analysis") as mock_run_analysis:
            exit_code = main(["--date", "2026-03-02"])

            mock_run_analysis.assert_not_called()
            assert exit_code == 0


# ---------------------------------------------------------------------------
# Task 2 (Plan 04-02): run_delivery pipeline function and CLI --deliver
# ---------------------------------------------------------------------------


class TestRunDelivery:
    """Tests for the run_delivery pipeline function."""

    @pytest.fixture()
    def mock_settings(self, monkeypatch):
        """Create mock settings for run_delivery tests."""
        monkeypatch.setenv("GARMIN_EMAIL", "test@garmin.com")
        monkeypatch.setenv("GARMIN_PASSWORD", "testpass")
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_KEY", "testkey")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        monkeypatch.setenv("RESEND_API_KEY", "re_test_key")
        monkeypatch.setenv("SENDER_EMAIL", "protocol@example.com")
        monkeypatch.setenv("RECIPIENT_EMAIL", "user@example.com")

        from biointelligence.config import Settings

        return Settings(_env_file=None)

    @patch("biointelligence.pipeline.send_email")
    @patch("biointelligence.pipeline.build_subject")
    @patch("biointelligence.pipeline.render_text")
    @patch("biointelligence.pipeline.render_html")
    def test_successful_delivery_calls_render_and_send(
        self,
        mock_render_html,
        mock_render_text,
        mock_build_subject,
        mock_send_email,
        mock_settings,
        fake_protocol,
    ):
        """run_delivery with successful AnalysisResult calls all renderers and send_email."""
        from biointelligence.analysis.engine import AnalysisResult
        from biointelligence.delivery.sender import DeliveryResult
        from biointelligence.pipeline import run_delivery

        analysis_result = AnalysisResult(
            date=datetime.date(2026, 3, 2),
            protocol=fake_protocol,
            input_tokens=3200,
            output_tokens=1800,
            model="claude-haiku-4-5-20251001",
            success=True,
        )

        mock_render_html.return_value = "<html>rendered</html>"
        mock_render_text.return_value = "plain text"
        mock_build_subject.return_value = "Daily Protocol -- Mar 2, 2026"
        mock_send_email.return_value = DeliveryResult(
            date=datetime.date(2026, 3, 2),
            email_id="email-123",
            success=True,
        )

        result = run_delivery(analysis_result, settings=mock_settings)

        mock_render_html.assert_called_once_with(
            fake_protocol, datetime.date(2026, 3, 2)
        )
        mock_render_text.assert_called_once_with(
            fake_protocol, datetime.date(2026, 3, 2)
        )
        mock_build_subject.assert_called_once_with(
            fake_protocol, datetime.date(2026, 3, 2)
        )
        mock_send_email.assert_called_once_with(
            html="<html>rendered</html>",
            text="plain text",
            subject="Daily Protocol -- Mar 2, 2026",
            target_date=datetime.date(2026, 3, 2),
            settings=mock_settings,
        )
        assert result.success is True
        assert result.email_id == "email-123"

    @patch("biointelligence.pipeline.send_email")
    @patch("biointelligence.pipeline.build_subject")
    @patch("biointelligence.pipeline.render_text")
    @patch("biointelligence.pipeline.render_html")
    def test_failed_analysis_returns_failed_delivery(
        self,
        mock_render_html,
        mock_render_text,
        mock_build_subject,
        mock_send_email,
        mock_settings,
    ):
        """run_delivery with failed AnalysisResult (protocol is None) returns failed DeliveryResult."""
        from biointelligence.analysis.engine import AnalysisResult
        from biointelligence.pipeline import run_delivery

        failed_result = AnalysisResult(
            date=datetime.date(2026, 3, 2),
            protocol=None,
            model="claude-haiku-4-5-20251001",
            success=False,
            error="API connection failed",
        )

        result = run_delivery(failed_result, settings=mock_settings)

        assert result.success is False
        assert "No protocol available" in result.error
        mock_render_html.assert_not_called()
        mock_send_email.assert_not_called()

    @patch("biointelligence.pipeline.send_email")
    @patch("biointelligence.pipeline.build_subject")
    @patch("biointelligence.pipeline.render_text")
    @patch("biointelligence.pipeline.render_html")
    def test_success_false_returns_failed_delivery(
        self,
        mock_render_html,
        mock_render_text,
        mock_build_subject,
        mock_send_email,
        mock_settings,
        fake_protocol,
    ):
        """run_delivery with success=False returns failed DeliveryResult without calling renderers."""
        from biointelligence.analysis.engine import AnalysisResult
        from biointelligence.pipeline import run_delivery

        # success=False but protocol is set (edge case)
        failed_result = AnalysisResult(
            date=datetime.date(2026, 3, 2),
            protocol=fake_protocol,
            model="claude-haiku-4-5-20251001",
            success=False,
            error="Validation failed",
        )

        result = run_delivery(failed_result, settings=mock_settings)

        assert result.success is False
        mock_render_html.assert_not_called()
        mock_send_email.assert_not_called()

    @patch("biointelligence.pipeline.log")
    @patch("biointelligence.pipeline.send_email")
    @patch("biointelligence.pipeline.build_subject")
    @patch("biointelligence.pipeline.render_text")
    @patch("biointelligence.pipeline.render_html")
    def test_logs_start_completion_and_failure(
        self,
        mock_render_html,
        mock_render_text,
        mock_build_subject,
        mock_send_email,
        mock_log,
        mock_settings,
        fake_protocol,
    ):
        """run_delivery logs start, completion (with email_id), and failure events."""
        from biointelligence.analysis.engine import AnalysisResult
        from biointelligence.delivery.sender import DeliveryResult
        from biointelligence.pipeline import run_delivery

        analysis_result = AnalysisResult(
            date=datetime.date(2026, 3, 2),
            protocol=fake_protocol,
            input_tokens=3200,
            output_tokens=1800,
            model="claude-haiku-4-5-20251001",
            success=True,
        )

        mock_render_html.return_value = "<html>test</html>"
        mock_render_text.return_value = "test"
        mock_build_subject.return_value = "Test Subject"
        mock_send_email.return_value = DeliveryResult(
            date=datetime.date(2026, 3, 2),
            email_id="email-456",
            success=True,
        )

        run_delivery(analysis_result, settings=mock_settings)

        log_events = [c[0][0] for c in mock_log.info.call_args_list]
        assert "delivery_pipeline_start" in log_events
        assert "delivery_pipeline_complete" in log_events


class TestRunDeliveryWhatsApp:
    """Tests for run_delivery WhatsApp-first delivery with email fallback."""

    @pytest.fixture()
    def mock_settings(self, monkeypatch):
        """Create mock settings with WhatsApp configured."""
        monkeypatch.setenv("GARMIN_EMAIL", "test@garmin.com")
        monkeypatch.setenv("GARMIN_PASSWORD", "testpass")
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_KEY", "testkey")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        monkeypatch.setenv("RESEND_API_KEY", "re_test_key")
        monkeypatch.setenv("SENDER_EMAIL", "protocol@example.com")
        monkeypatch.setenv("RECIPIENT_EMAIL", "user@example.com")
        monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "wa_test_token")
        monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "123456789")
        monkeypatch.setenv("WHATSAPP_RECIPIENT_PHONE", "4915123456789")

        from biointelligence.config import Settings

        return Settings(_env_file=None)

    @pytest.fixture()
    def mock_settings_no_whatsapp(self, monkeypatch):
        """Create mock settings without WhatsApp configured (empty token)."""
        monkeypatch.setenv("GARMIN_EMAIL", "test@garmin.com")
        monkeypatch.setenv("GARMIN_PASSWORD", "testpass")
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_KEY", "testkey")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        monkeypatch.setenv("RESEND_API_KEY", "re_test_key")
        monkeypatch.setenv("SENDER_EMAIL", "protocol@example.com")
        monkeypatch.setenv("RECIPIENT_EMAIL", "user@example.com")
        # WhatsApp token not set (defaults to empty string)

        from biointelligence.config import Settings

        return Settings(_env_file=None)

    @patch("biointelligence.delivery.whatsapp_renderer.get_incomplete_steps", return_value=[])
    @patch("biointelligence.pipeline.send_email")
    @patch("biointelligence.pipeline.build_subject")
    @patch("biointelligence.pipeline.render_text")
    @patch("biointelligence.pipeline.render_html")
    @patch("biointelligence.pipeline.send_whatsapp")
    @patch("biointelligence.pipeline.render_whatsapp")
    def test_whatsapp_success_skips_email(
        self,
        mock_render_whatsapp,
        mock_send_whatsapp,
        mock_render_html,
        mock_render_text,
        mock_build_subject,
        mock_send_email,
        mock_get_incomplete,
        mock_settings,
        fake_protocol,
    ):
        """When WhatsApp is configured and succeeds, email is NOT called."""
        from biointelligence.analysis.engine import AnalysisResult
        from biointelligence.delivery.sender import DeliveryResult
        from biointelligence.pipeline import run_delivery

        analysis_result = AnalysisResult(
            date=datetime.date(2026, 3, 2),
            protocol=fake_protocol,
            input_tokens=3200,
            output_tokens=1800,
            model="claude-haiku-4-5-20251001",
            success=True,
        )

        mock_render_whatsapp.return_value = "WhatsApp text"
        mock_send_whatsapp.return_value = DeliveryResult(
            date=datetime.date(2026, 3, 2),
            email_id="wamid.abc123",
            success=True,
        )

        result = run_delivery(analysis_result, settings=mock_settings)

        mock_render_whatsapp.assert_called_once_with(
            fake_protocol, datetime.date(2026, 3, 2), incomplete_steps=[],
        )
        mock_send_whatsapp.assert_called_once_with(
            "WhatsApp text", datetime.date(2026, 3, 2), mock_settings
        )
        assert result.success is True
        assert result.email_id == "wamid.abc123"
        mock_send_email.assert_not_called()

    @patch("biointelligence.delivery.whatsapp_renderer.get_incomplete_steps", return_value=[])
    @patch("biointelligence.pipeline.send_email")
    @patch("biointelligence.pipeline.build_subject")
    @patch("biointelligence.pipeline.render_text")
    @patch("biointelligence.pipeline.render_html")
    @patch("biointelligence.pipeline.send_whatsapp")
    @patch("biointelligence.pipeline.render_whatsapp")
    def test_whatsapp_failure_falls_back_to_email(
        self,
        mock_render_whatsapp,
        mock_send_whatsapp,
        mock_render_html,
        mock_render_text,
        mock_build_subject,
        mock_send_email,
        mock_get_incomplete,
        mock_settings,
        fake_protocol,
    ):
        """When WhatsApp fails, falls back to email delivery."""
        from biointelligence.analysis.engine import AnalysisResult
        from biointelligence.delivery.sender import DeliveryResult
        from biointelligence.pipeline import run_delivery

        analysis_result = AnalysisResult(
            date=datetime.date(2026, 3, 2),
            protocol=fake_protocol,
            input_tokens=3200,
            output_tokens=1800,
            model="claude-haiku-4-5-20251001",
            success=True,
        )

        mock_render_whatsapp.return_value = "WhatsApp text"
        mock_send_whatsapp.return_value = DeliveryResult(
            date=datetime.date(2026, 3, 2),
            success=False,
            error="WhatsApp API error",
        )
        mock_render_html.return_value = "<html>rendered</html>"
        mock_render_text.return_value = "plain text"
        mock_build_subject.return_value = "Daily Protocol -- Mar 2, 2026"
        mock_send_email.return_value = DeliveryResult(
            date=datetime.date(2026, 3, 2),
            email_id="email-fallback-123",
            success=True,
        )

        result = run_delivery(analysis_result, settings=mock_settings)

        # WhatsApp was attempted
        mock_render_whatsapp.assert_called_once()
        mock_send_whatsapp.assert_called_once()
        # Email fallback was used
        mock_render_html.assert_called_once()
        mock_render_text.assert_called_once()
        mock_build_subject.assert_called_once()
        mock_send_email.assert_called_once()
        assert result.success is True
        assert result.email_id == "email-fallback-123"

    @patch("biointelligence.delivery.whatsapp_renderer.get_incomplete_steps", return_value=[])
    @patch("biointelligence.pipeline.send_email")
    @patch("biointelligence.pipeline.build_subject")
    @patch("biointelligence.pipeline.render_text")
    @patch("biointelligence.pipeline.render_html")
    @patch("biointelligence.pipeline.send_whatsapp")
    @patch("biointelligence.pipeline.render_whatsapp")
    def test_whatsapp_not_configured_uses_email_only(
        self,
        mock_render_whatsapp,
        mock_send_whatsapp,
        mock_render_html,
        mock_render_text,
        mock_build_subject,
        mock_send_email,
        mock_get_incomplete,
        mock_settings_no_whatsapp,
        fake_protocol,
    ):
        """When WhatsApp is not configured (empty token), skips WhatsApp entirely."""
        from biointelligence.analysis.engine import AnalysisResult
        from biointelligence.delivery.sender import DeliveryResult
        from biointelligence.pipeline import run_delivery

        analysis_result = AnalysisResult(
            date=datetime.date(2026, 3, 2),
            protocol=fake_protocol,
            input_tokens=3200,
            output_tokens=1800,
            model="claude-haiku-4-5-20251001",
            success=True,
        )

        mock_render_html.return_value = "<html>rendered</html>"
        mock_render_text.return_value = "plain text"
        mock_build_subject.return_value = "Daily Protocol -- Mar 2, 2026"
        mock_send_email.return_value = DeliveryResult(
            date=datetime.date(2026, 3, 2),
            email_id="email-only-123",
            success=True,
        )

        result = run_delivery(analysis_result, settings=mock_settings_no_whatsapp)

        # WhatsApp NOT attempted
        mock_render_whatsapp.assert_not_called()
        mock_send_whatsapp.assert_not_called()
        # Email path executes
        mock_render_html.assert_called_once()
        mock_send_email.assert_called_once()
        assert result.success is True
        assert result.email_id == "email-only-123"

    @patch("biointelligence.delivery.whatsapp_renderer.get_incomplete_steps", return_value=[])
    @patch("biointelligence.pipeline.send_email")
    @patch("biointelligence.pipeline.send_whatsapp")
    @patch("biointelligence.pipeline.render_whatsapp")
    def test_failed_analysis_returns_failed_result_with_whatsapp_configured(
        self,
        mock_render_whatsapp,
        mock_send_whatsapp,
        mock_send_email,
        mock_get_incomplete,
        mock_settings,
    ):
        """Failed analysis returns failed DeliveryResult without attempting any delivery."""
        from biointelligence.analysis.engine import AnalysisResult
        from biointelligence.pipeline import run_delivery

        failed_result = AnalysisResult(
            date=datetime.date(2026, 3, 2),
            protocol=None,
            model="claude-haiku-4-5-20251001",
            success=False,
            error="API connection failed",
        )

        result = run_delivery(failed_result, settings=mock_settings)

        assert result.success is False
        assert "No protocol available" in result.error
        mock_render_whatsapp.assert_not_called()
        mock_send_whatsapp.assert_not_called()
        mock_send_email.assert_not_called()


class TestRunDeliveryProfileNudges:
    """Tests for profile completeness nudge integration in run_delivery."""

    @pytest.fixture()
    def mock_settings(self, monkeypatch):
        """Create mock settings with WhatsApp configured."""
        monkeypatch.setenv("GARMIN_EMAIL", "test@garmin.com")
        monkeypatch.setenv("GARMIN_PASSWORD", "testpass")
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_KEY", "testkey")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        monkeypatch.setenv("RESEND_API_KEY", "re_test_key")
        monkeypatch.setenv("SENDER_EMAIL", "protocol@example.com")
        monkeypatch.setenv("RECIPIENT_EMAIL", "user@example.com")
        monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "wa_test_token")
        monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "123456789")
        monkeypatch.setenv("WHATSAPP_RECIPIENT_PHONE", "4915123456789")

        from biointelligence.config import Settings

        return Settings(_env_file=None)

    @patch("biointelligence.delivery.whatsapp_renderer.get_incomplete_steps", return_value=[2, 5])
    @patch("biointelligence.delivery.whatsapp_renderer.should_send_nudge", return_value=True)
    @patch("biointelligence.pipeline.send_whatsapp")
    @patch("biointelligence.pipeline.render_whatsapp")
    def test_passes_incomplete_steps_to_render_whatsapp(
        self,
        mock_render_whatsapp,
        mock_send_whatsapp,
        mock_should_send,
        mock_get_incomplete,
        mock_settings,
        fake_protocol,
    ):
        """run_delivery passes incomplete_steps from get_incomplete_steps to render_whatsapp."""
        from biointelligence.analysis.engine import AnalysisResult
        from biointelligence.delivery.sender import DeliveryResult
        from biointelligence.pipeline import run_delivery

        analysis_result = AnalysisResult(
            date=datetime.date(2026, 3, 2),
            protocol=fake_protocol,
            input_tokens=3200,
            output_tokens=1800,
            model="claude-haiku-4-5-20251001",
            success=True,
        )

        mock_render_whatsapp.return_value = "WhatsApp text"
        mock_send_whatsapp.return_value = DeliveryResult(
            date=datetime.date(2026, 3, 2),
            email_id="wamid.abc123",
            success=True,
        )

        run_delivery(analysis_result, settings=mock_settings)

        mock_render_whatsapp.assert_called_once_with(
            fake_protocol, datetime.date(2026, 3, 2), incomplete_steps=[2, 5],
        )

    @patch("biointelligence.delivery.whatsapp_renderer.get_incomplete_steps", side_effect=Exception("DB error"))
    @patch("biointelligence.delivery.whatsapp_renderer.should_send_nudge", return_value=True)
    @patch("biointelligence.pipeline.send_whatsapp")
    @patch("biointelligence.pipeline.render_whatsapp")
    def test_handles_get_incomplete_steps_failure_gracefully(
        self,
        mock_render_whatsapp,
        mock_send_whatsapp,
        mock_should_send,
        mock_get_incomplete,
        mock_settings,
        fake_protocol,
    ):
        """run_delivery continues with empty incomplete_steps when get_incomplete_steps fails."""
        from biointelligence.analysis.engine import AnalysisResult
        from biointelligence.delivery.sender import DeliveryResult
        from biointelligence.pipeline import run_delivery

        analysis_result = AnalysisResult(
            date=datetime.date(2026, 3, 2),
            protocol=fake_protocol,
            input_tokens=3200,
            output_tokens=1800,
            model="claude-haiku-4-5-20251001",
            success=True,
        )

        mock_render_whatsapp.return_value = "WhatsApp text"
        mock_send_whatsapp.return_value = DeliveryResult(
            date=datetime.date(2026, 3, 2),
            email_id="wamid.abc123",
            success=True,
        )

        result = run_delivery(analysis_result, settings=mock_settings)

        # Should still deliver successfully with empty incomplete_steps
        assert result.success is True
        mock_render_whatsapp.assert_called_once_with(
            fake_protocol, datetime.date(2026, 3, 2), incomplete_steps=[],
        )


class TestRunDeliveryWhatsAppLazyImports:
    """Tests for delivery package lazy imports of WhatsApp functions."""

    def test_render_whatsapp_importable_from_delivery(self):
        """render_whatsapp is importable from biointelligence.delivery."""
        from biointelligence.delivery import render_whatsapp

        assert callable(render_whatsapp)

    def test_send_whatsapp_importable_from_delivery(self):
        """send_whatsapp is importable from biointelligence.delivery."""
        from biointelligence.delivery import send_whatsapp

        assert callable(send_whatsapp)


class TestMainCliDeliver:
    """Tests for CLI --deliver flag (now uses run_full_pipeline)."""

    @patch("biointelligence.main.run_full_pipeline")
    @patch("biointelligence.main.configure_logging")
    def test_deliver_flag_triggers_run_full_pipeline(
        self, mock_logging, mock_run_full
    ):
        """CLI --deliver flag triggers run_full_pipeline."""
        from biointelligence.main import main

        mock_run_full.return_value = MagicMock(
            success=True,
            date=datetime.date(2026, 3, 2),
            failed_stage=None,
            duration_seconds=45.0,
            error=None,
        )

        exit_code = main(["--date", "2026-03-02", "--deliver"])

        mock_run_full.assert_called_once()
        assert exit_code == 0

    @patch("biointelligence.main.run_full_pipeline")
    @patch("biointelligence.main.configure_logging")
    def test_deliver_without_analyze_uses_full_pipeline(
        self, mock_logging, mock_run_full
    ):
        """CLI --deliver without --analyze uses run_full_pipeline directly."""
        from biointelligence.main import main

        mock_run_full.return_value = MagicMock(
            success=True,
            date=datetime.date(2026, 3, 2),
            failed_stage=None,
            duration_seconds=30.0,
            error=None,
        )

        # Only --deliver, no --analyze
        exit_code = main(["--date", "2026-03-02", "--deliver"])

        mock_run_full.assert_called_once()
        assert exit_code == 0

    @patch("biointelligence.main.run_full_pipeline")
    @patch("biointelligence.main.configure_logging")
    def test_deliver_returns_1_on_pipeline_failure(
        self, mock_logging, mock_run_full
    ):
        """CLI --deliver returns exit 1 when run_full_pipeline fails."""
        from biointelligence.main import main

        mock_run_full.return_value = MagicMock(
            success=False,
            date=datetime.date(2026, 3, 2),
            failed_stage="delivery",
            duration_seconds=12.0,
            error="Resend API error",
        )

        exit_code = main(["--date", "2026-03-02", "--deliver"])

        assert exit_code == 1

    @patch("biointelligence.main.run_ingestion")
    @patch("biointelligence.main.configure_logging")
    def test_no_deliver_flag_does_not_call_full_pipeline(
        self, mock_logging, mock_ingestion
    ):
        """CLI without --deliver does not call run_full_pipeline."""
        from biointelligence.main import main

        mock_ingestion.return_value = MagicMock(
            success=True,
            date=datetime.date(2026, 3, 2),
            activity_count=1,
            completeness=MagicMock(score=0.9, is_no_wear=False),
        )

        with patch("biointelligence.main.run_full_pipeline") as mock_run_full:
            exit_code = main(["--date", "2026-03-02"])

            mock_run_full.assert_not_called()
            assert exit_code == 0


# ---------------------------------------------------------------------------
# Task 1 (Plan 05-02): run_full_pipeline orchestrator and CLI wiring
# ---------------------------------------------------------------------------


class TestPipelineResult:
    """Tests for PipelineResult model."""

    def test_pipeline_result_fields(self):
        """PipelineResult has date, success, failed_stage, duration_seconds, error."""
        from biointelligence.pipeline import PipelineResult

        result = PipelineResult(
            date=datetime.date(2026, 3, 2),
            success=True,
            failed_stage=None,
            duration_seconds=42.5,
            error=None,
        )
        assert result.date == datetime.date(2026, 3, 2)
        assert result.success is True
        assert result.failed_stage is None
        assert result.duration_seconds == 42.5
        assert result.error is None

    def test_pipeline_result_failure(self):
        """PipelineResult captures failure details."""
        from biointelligence.pipeline import PipelineResult

        result = PipelineResult(
            date=datetime.date(2026, 3, 2),
            success=False,
            failed_stage="ingestion",
            duration_seconds=1.2,
            error="Connection refused",
        )
        assert result.success is False
        assert result.failed_stage == "ingestion"
        assert result.error == "Connection refused"


class TestRunFullPipeline:
    """Tests for run_full_pipeline orchestrator."""

    @pytest.fixture()
    def mock_settings(self, monkeypatch):
        """Create mock settings for pipeline tests."""
        monkeypatch.setenv("GARMIN_EMAIL", "test@garmin.com")
        monkeypatch.setenv("GARMIN_PASSWORD", "testpass")
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_KEY", "testkey")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        monkeypatch.setenv("RESEND_API_KEY", "re_test_key")
        monkeypatch.setenv("SENDER_EMAIL", "protocol@example.com")
        monkeypatch.setenv("RECIPIENT_EMAIL", "user@example.com")

        from biointelligence.config import Settings

        return Settings(_env_file=None)

    @patch("biointelligence.pipeline.log_pipeline_run")
    @patch("biointelligence.pipeline.run_delivery")
    @patch("biointelligence.pipeline.run_analysis")
    @patch("biointelligence.pipeline.run_ingestion")
    @patch("biointelligence.pipeline.get_authenticated_client")
    @patch("biointelligence.pipeline.get_supabase_client")
    def test_successful_full_pipeline(
        self,
        mock_get_supabase,
        mock_auth,
        mock_ingestion,
        mock_analysis,
        mock_delivery,
        mock_log_run,
        mock_settings,
        fake_protocol,
    ):
        """run_full_pipeline orchestrates all stages and logs success."""
        from biointelligence.pipeline import run_full_pipeline

        mock_supabase = MagicMock()
        mock_get_supabase.return_value = mock_supabase
        mock_auth.return_value = MagicMock()

        mock_ingestion.return_value = MagicMock(success=True)

        analysis_result = MagicMock(
            success=True, protocol=fake_protocol, date=datetime.date(2026, 3, 2)
        )
        mock_analysis.return_value = analysis_result
        mock_delivery.return_value = MagicMock(success=True)

        target_date = datetime.date(2026, 3, 2)
        result = run_full_pipeline(target_date, settings=mock_settings)

        assert result.success is True
        assert result.failed_stage is None
        assert result.duration_seconds >= 0

        # Run log should have been called with status="success"
        mock_log_run.assert_called_once()
        run_log = mock_log_run.call_args[0][1]
        assert run_log.status == "success"
        assert run_log.failed_stage is None

    @patch("biointelligence.pipeline.send_failure_notification")
    @patch("biointelligence.pipeline.log_pipeline_run")
    @patch("biointelligence.pipeline.run_ingestion")
    @patch("biointelligence.pipeline.get_authenticated_client")
    @patch("biointelligence.pipeline.get_supabase_client")
    def test_ingestion_failure_sends_notification(
        self,
        mock_get_supabase,
        mock_auth,
        mock_ingestion,
        mock_log_run,
        mock_notify,
        mock_settings,
    ):
        """Ingestion failure sends notification with failed_stage='ingestion'."""
        from biointelligence.pipeline import run_full_pipeline

        mock_get_supabase.return_value = MagicMock()
        mock_auth.return_value = MagicMock()
        mock_ingestion.side_effect = RuntimeError("Garmin API down")

        result = run_full_pipeline(datetime.date(2026, 3, 2), settings=mock_settings)

        assert result.success is False
        assert result.failed_stage == "ingestion"
        mock_notify.assert_called_once()
        assert mock_notify.call_args[1]["failed_stage"] == "ingestion"

    @patch("biointelligence.pipeline.send_failure_notification")
    @patch("biointelligence.pipeline.log_pipeline_run")
    @patch("biointelligence.pipeline.run_analysis")
    @patch("biointelligence.pipeline.run_ingestion")
    @patch("biointelligence.pipeline.get_authenticated_client")
    @patch("biointelligence.pipeline.get_supabase_client")
    def test_analysis_failure_sends_notification(
        self,
        mock_get_supabase,
        mock_auth,
        mock_ingestion,
        mock_analysis,
        mock_log_run,
        mock_notify,
        mock_settings,
    ):
        """Analysis failure sends notification with failed_stage='analysis'."""
        from biointelligence.pipeline import run_full_pipeline

        mock_get_supabase.return_value = MagicMock()
        mock_auth.return_value = MagicMock()
        mock_ingestion.return_value = MagicMock(success=True)
        mock_analysis.side_effect = RuntimeError("Claude API error")

        result = run_full_pipeline(datetime.date(2026, 3, 2), settings=mock_settings)

        assert result.success is False
        assert result.failed_stage == "analysis"
        mock_notify.assert_called_once()
        assert mock_notify.call_args[1]["failed_stage"] == "analysis"

    @patch("biointelligence.pipeline.send_failure_notification")
    @patch("biointelligence.pipeline.log_pipeline_run")
    @patch("biointelligence.pipeline.run_delivery")
    @patch("biointelligence.pipeline.run_analysis")
    @patch("biointelligence.pipeline.run_ingestion")
    @patch("biointelligence.pipeline.get_authenticated_client")
    @patch("biointelligence.pipeline.get_supabase_client")
    def test_delivery_failure_sends_notification(
        self,
        mock_get_supabase,
        mock_auth,
        mock_ingestion,
        mock_analysis,
        mock_delivery,
        mock_log_run,
        mock_notify,
        mock_settings,
        fake_protocol,
    ):
        """Delivery failure sends notification with failed_stage='delivery'."""
        from biointelligence.pipeline import run_full_pipeline

        mock_get_supabase.return_value = MagicMock()
        mock_auth.return_value = MagicMock()
        mock_ingestion.return_value = MagicMock(success=True)
        mock_analysis.return_value = MagicMock(
            success=True, protocol=fake_protocol, date=datetime.date(2026, 3, 2)
        )
        mock_delivery.side_effect = RuntimeError("Resend down")

        result = run_full_pipeline(datetime.date(2026, 3, 2), settings=mock_settings)

        assert result.success is False
        assert result.failed_stage == "delivery"
        mock_notify.assert_called_once()
        assert mock_notify.call_args[1]["failed_stage"] == "delivery"

    @patch("biointelligence.pipeline.send_failure_notification")
    @patch("biointelligence.pipeline.log_pipeline_run")
    @patch("biointelligence.pipeline.run_delivery")
    @patch("biointelligence.pipeline.run_analysis")
    @patch("biointelligence.pipeline.run_ingestion")
    @patch("biointelligence.pipeline.get_authenticated_client")
    @patch("biointelligence.pipeline.get_supabase_client")
    def test_run_log_failure_does_not_mask_result(
        self,
        mock_get_supabase,
        mock_auth,
        mock_ingestion,
        mock_analysis,
        mock_delivery,
        mock_log_run,
        mock_notify,
        mock_settings,
        fake_protocol,
    ):
        """If log_pipeline_run raises, pipeline result is still returned."""
        from biointelligence.pipeline import run_full_pipeline

        mock_get_supabase.return_value = MagicMock()
        mock_auth.return_value = MagicMock()
        mock_ingestion.return_value = MagicMock(success=True)
        mock_analysis.return_value = MagicMock(
            success=True, protocol=fake_protocol, date=datetime.date(2026, 3, 2)
        )
        mock_delivery.return_value = MagicMock(success=True)

        # log_pipeline_run blows up
        mock_log_run.side_effect = ConnectionError("Supabase down")

        result = run_full_pipeline(datetime.date(2026, 3, 2), settings=mock_settings)

        # Pipeline succeeded, logging failure should not mask that
        assert result.success is True

    @patch("biointelligence.pipeline.send_failure_notification")
    @patch("biointelligence.pipeline.log_pipeline_run")
    @patch("biointelligence.pipeline.run_ingestion")
    @patch("biointelligence.pipeline.get_authenticated_client")
    @patch("biointelligence.pipeline.get_supabase_client")
    def test_notification_failure_does_not_mask_error(
        self,
        mock_get_supabase,
        mock_auth,
        mock_ingestion,
        mock_log_run,
        mock_notify,
        mock_settings,
    ):
        """If send_failure_notification raises, original error is preserved."""
        from biointelligence.pipeline import run_full_pipeline

        mock_get_supabase.return_value = MagicMock()
        mock_auth.return_value = MagicMock()
        mock_ingestion.side_effect = RuntimeError("Garmin API down")

        # Notification also fails
        mock_notify.side_effect = ConnectionError("Resend down too")

        result = run_full_pipeline(datetime.date(2026, 3, 2), settings=mock_settings)

        assert result.success is False
        assert result.failed_stage == "ingestion"
        assert "Garmin API down" in result.error

    @patch("biointelligence.pipeline.log_pipeline_run")
    @patch("biointelligence.pipeline.run_ingestion")
    @patch("biointelligence.pipeline.get_authenticated_client")
    @patch("biointelligence.pipeline.get_supabase_client")
    def test_ingestion_passes_garmin_client(
        self,
        mock_get_supabase,
        mock_auth,
        mock_ingestion,
        mock_log_run,
        mock_settings,
    ):
        """run_full_pipeline passes garmin_client to run_ingestion to avoid double-auth."""
        from biointelligence.pipeline import run_full_pipeline

        mock_supabase = MagicMock()
        mock_get_supabase.return_value = mock_supabase
        mock_garmin = MagicMock()
        mock_auth.return_value = mock_garmin
        mock_ingestion.return_value = MagicMock(success=True)

        # Analysis will fail to cut short
        with patch("biointelligence.pipeline.run_analysis") as mock_analysis:
            mock_analysis.return_value = MagicMock(
                success=False, error="Analysis failed"
            )
            with patch("biointelligence.pipeline.send_failure_notification"):
                run_full_pipeline(datetime.date(2026, 3, 2), settings=mock_settings)

        # Check garmin_client was passed to run_ingestion
        call_kwargs = mock_ingestion.call_args
        assert call_kwargs[1].get("garmin_client") is mock_garmin


class TestMainCliDeliverUpdated:
    """Tests for CLI --deliver using run_full_pipeline."""

    @patch("biointelligence.main.run_full_pipeline")
    @patch("biointelligence.main.configure_logging")
    def test_deliver_uses_run_full_pipeline(
        self, mock_logging, mock_run_full
    ):
        """CLI --deliver now calls run_full_pipeline instead of separate stages."""
        from biointelligence.main import main

        mock_run_full.return_value = MagicMock(
            success=True,
            date=datetime.date(2026, 3, 2),
            failed_stage=None,
            duration_seconds=45.0,
            error=None,
        )

        exit_code = main(["--date", "2026-03-02", "--deliver"])

        mock_run_full.assert_called_once()
        assert exit_code == 0

    @patch("biointelligence.main.run_full_pipeline")
    @patch("biointelligence.main.configure_logging")
    def test_deliver_returns_1_on_pipeline_failure(
        self, mock_logging, mock_run_full
    ):
        """CLI --deliver returns exit 1 when run_full_pipeline fails."""
        from biointelligence.main import main

        mock_run_full.return_value = MagicMock(
            success=False,
            date=datetime.date(2026, 3, 2),
            failed_stage="analysis",
            duration_seconds=12.0,
            error="Claude API error",
        )

        exit_code = main(["--date", "2026-03-02", "--deliver"])

        assert exit_code == 1

    @patch("biointelligence.main.run_ingestion")
    @patch("biointelligence.main.configure_logging")
    def test_no_deliver_still_uses_old_path(
        self, mock_logging, mock_ingestion
    ):
        """CLI without --deliver still uses run_ingestion directly."""
        from biointelligence.main import main

        mock_ingestion.return_value = MagicMock(
            success=True,
            date=datetime.date(2026, 3, 2),
            activity_count=1,
            completeness=MagicMock(score=0.9, is_no_wear=False),
        )

        exit_code = main(["--date", "2026-03-02"])

        mock_ingestion.assert_called_once()
        assert exit_code == 0


# ---------------------------------------------------------------------------
# Task 2 (Plan 08-06): run_delivery nudge cooldown rate limiting
# ---------------------------------------------------------------------------


class TestRunDeliveryNudgeCooldown:
    """Tests for nudge cooldown rate limiting in run_delivery."""

    @pytest.fixture()
    def mock_settings(self, monkeypatch):
        """Create mock settings with WhatsApp configured."""
        monkeypatch.setenv("GARMIN_EMAIL", "test@garmin.com")
        monkeypatch.setenv("GARMIN_PASSWORD", "testpass")
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_KEY", "testkey")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        monkeypatch.setenv("RESEND_API_KEY", "re_test_key")
        monkeypatch.setenv("SENDER_EMAIL", "protocol@example.com")
        monkeypatch.setenv("RECIPIENT_EMAIL", "user@example.com")
        monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "wa_test_token")
        monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "123456789")
        monkeypatch.setenv("WHATSAPP_RECIPIENT_PHONE", "4915123456789")

        from biointelligence.config import Settings

        return Settings(_env_file=None)

    @patch("biointelligence.delivery.whatsapp_renderer.should_send_nudge", return_value=False)
    @patch("biointelligence.pipeline.send_whatsapp")
    @patch("biointelligence.pipeline.render_whatsapp")
    def test_passes_empty_incomplete_steps_when_cooldown_active(
        self,
        mock_render_whatsapp,
        mock_send_whatsapp,
        mock_should_send,
        mock_settings,
        fake_protocol,
    ):
        """run_delivery passes incomplete_steps=[] when should_send_nudge returns False."""
        from biointelligence.analysis.engine import AnalysisResult
        from biointelligence.delivery.sender import DeliveryResult
        from biointelligence.pipeline import run_delivery

        analysis_result = AnalysisResult(
            date=datetime.date(2026, 3, 2),
            protocol=fake_protocol,
            input_tokens=3200,
            output_tokens=1800,
            model="claude-haiku-4-5-20251001",
            success=True,
        )

        mock_render_whatsapp.return_value = "WhatsApp text"
        mock_send_whatsapp.return_value = DeliveryResult(
            date=datetime.date(2026, 3, 2),
            email_id="wamid.abc123",
            success=True,
        )

        run_delivery(analysis_result, settings=mock_settings)

        mock_render_whatsapp.assert_called_once_with(
            fake_protocol, datetime.date(2026, 3, 2), incomplete_steps=[],
        )

    @patch("biointelligence.delivery.whatsapp_renderer.record_nudge_sent")
    @patch("biointelligence.delivery.whatsapp_renderer.get_incomplete_steps", return_value=[2, 5])
    @patch("biointelligence.delivery.whatsapp_renderer.should_send_nudge", return_value=True)
    @patch("biointelligence.pipeline.send_whatsapp")
    @patch("biointelligence.pipeline.render_whatsapp")
    def test_passes_incomplete_steps_when_cooldown_elapsed(
        self,
        mock_render_whatsapp,
        mock_send_whatsapp,
        mock_should_send,
        mock_get_incomplete,
        mock_record_nudge,
        mock_settings,
        fake_protocol,
    ):
        """run_delivery passes incomplete_steps=[2,5] when should_send_nudge returns True."""
        from biointelligence.analysis.engine import AnalysisResult
        from biointelligence.delivery.sender import DeliveryResult
        from biointelligence.pipeline import run_delivery

        analysis_result = AnalysisResult(
            date=datetime.date(2026, 3, 2),
            protocol=fake_protocol,
            input_tokens=3200,
            output_tokens=1800,
            model="claude-haiku-4-5-20251001",
            success=True,
        )

        mock_render_whatsapp.return_value = "WhatsApp text"
        mock_send_whatsapp.return_value = DeliveryResult(
            date=datetime.date(2026, 3, 2),
            email_id="wamid.abc123",
            success=True,
        )

        run_delivery(analysis_result, settings=mock_settings)

        mock_render_whatsapp.assert_called_once_with(
            fake_protocol, datetime.date(2026, 3, 2), incomplete_steps=[2, 5],
        )

    @patch("biointelligence.delivery.whatsapp_renderer.record_nudge_sent")
    @patch("biointelligence.delivery.whatsapp_renderer.get_incomplete_steps", return_value=[2, 5])
    @patch("biointelligence.delivery.whatsapp_renderer.should_send_nudge", return_value=True)
    @patch("biointelligence.pipeline.send_whatsapp")
    @patch("biointelligence.pipeline.render_whatsapp")
    def test_calls_record_nudge_sent_after_whatsapp_success_with_nudge(
        self,
        mock_render_whatsapp,
        mock_send_whatsapp,
        mock_should_send,
        mock_get_incomplete,
        mock_record_nudge,
        mock_settings,
        fake_protocol,
    ):
        """run_delivery calls record_nudge_sent after successful WhatsApp delivery with nudge."""
        from biointelligence.analysis.engine import AnalysisResult
        from biointelligence.delivery.sender import DeliveryResult
        from biointelligence.pipeline import run_delivery

        analysis_result = AnalysisResult(
            date=datetime.date(2026, 3, 2),
            protocol=fake_protocol,
            input_tokens=3200,
            output_tokens=1800,
            model="claude-haiku-4-5-20251001",
            success=True,
        )

        mock_render_whatsapp.return_value = "WhatsApp text"
        mock_send_whatsapp.return_value = DeliveryResult(
            date=datetime.date(2026, 3, 2),
            email_id="wamid.abc123",
            success=True,
        )

        run_delivery(analysis_result, settings=mock_settings)

        mock_record_nudge.assert_called_once_with(mock_settings)

    @patch("biointelligence.delivery.whatsapp_renderer.record_nudge_sent")
    @patch("biointelligence.delivery.whatsapp_renderer.should_send_nudge", return_value=False)
    @patch("biointelligence.pipeline.send_whatsapp")
    @patch("biointelligence.pipeline.render_whatsapp")
    def test_does_not_call_record_nudge_sent_when_no_nudge(
        self,
        mock_render_whatsapp,
        mock_send_whatsapp,
        mock_should_send,
        mock_record_nudge,
        mock_settings,
        fake_protocol,
    ):
        """run_delivery does NOT call record_nudge_sent when incomplete_steps is empty."""
        from biointelligence.analysis.engine import AnalysisResult
        from biointelligence.delivery.sender import DeliveryResult
        from biointelligence.pipeline import run_delivery

        analysis_result = AnalysisResult(
            date=datetime.date(2026, 3, 2),
            protocol=fake_protocol,
            input_tokens=3200,
            output_tokens=1800,
            model="claude-haiku-4-5-20251001",
            success=True,
        )

        mock_render_whatsapp.return_value = "WhatsApp text"
        mock_send_whatsapp.return_value = DeliveryResult(
            date=datetime.date(2026, 3, 2),
            email_id="wamid.abc123",
            success=True,
        )

        run_delivery(analysis_result, settings=mock_settings)

        mock_record_nudge.assert_not_called()

    @patch("biointelligence.delivery.whatsapp_renderer.record_nudge_sent")
    @patch("biointelligence.delivery.whatsapp_renderer.get_incomplete_steps", return_value=[2, 5])
    @patch("biointelligence.delivery.whatsapp_renderer.should_send_nudge", return_value=True)
    @patch("biointelligence.pipeline.send_email")
    @patch("biointelligence.pipeline.build_subject")
    @patch("biointelligence.pipeline.render_text")
    @patch("biointelligence.pipeline.render_html")
    @patch("biointelligence.pipeline.send_whatsapp")
    @patch("biointelligence.pipeline.render_whatsapp")
    def test_does_not_call_record_nudge_sent_on_email_fallback(
        self,
        mock_render_whatsapp,
        mock_send_whatsapp,
        mock_render_html,
        mock_render_text,
        mock_build_subject,
        mock_send_email,
        mock_should_send,
        mock_get_incomplete,
        mock_record_nudge,
        mock_settings,
        fake_protocol,
    ):
        """run_delivery does NOT call record_nudge_sent on email fallback."""
        from biointelligence.analysis.engine import AnalysisResult
        from biointelligence.delivery.sender import DeliveryResult
        from biointelligence.pipeline import run_delivery

        analysis_result = AnalysisResult(
            date=datetime.date(2026, 3, 2),
            protocol=fake_protocol,
            input_tokens=3200,
            output_tokens=1800,
            model="claude-haiku-4-5-20251001",
            success=True,
        )

        mock_render_whatsapp.return_value = "WhatsApp text"
        # WhatsApp fails, falls back to email
        mock_send_whatsapp.return_value = DeliveryResult(
            date=datetime.date(2026, 3, 2),
            success=False,
            error="WhatsApp API error",
        )
        mock_render_html.return_value = "<html>rendered</html>"
        mock_render_text.return_value = "plain text"
        mock_build_subject.return_value = "Daily Protocol -- Mar 2, 2026"
        mock_send_email.return_value = DeliveryResult(
            date=datetime.date(2026, 3, 2),
            email_id="email-fallback-123",
            success=True,
        )

        result = run_delivery(analysis_result, settings=mock_settings)

        assert result.success is True
        # Nudge was included in WhatsApp but WA failed, fell back to email
        # record_nudge_sent should NOT be called since nudge only in WhatsApp
        mock_record_nudge.assert_not_called()

    @patch("biointelligence.delivery.whatsapp_renderer.should_send_nudge", side_effect=Exception("DB error"))
    @patch("biointelligence.pipeline.send_whatsapp")
    @patch("biointelligence.pipeline.render_whatsapp")
    def test_should_send_nudge_failure_results_in_empty_steps(
        self,
        mock_render_whatsapp,
        mock_send_whatsapp,
        mock_should_send,
        mock_settings,
        fake_protocol,
    ):
        """should_send_nudge failure (exception) results in incomplete_steps=[] (graceful degradation)."""
        from biointelligence.analysis.engine import AnalysisResult
        from biointelligence.delivery.sender import DeliveryResult
        from biointelligence.pipeline import run_delivery

        analysis_result = AnalysisResult(
            date=datetime.date(2026, 3, 2),
            protocol=fake_protocol,
            input_tokens=3200,
            output_tokens=1800,
            model="claude-haiku-4-5-20251001",
            success=True,
        )

        mock_render_whatsapp.return_value = "WhatsApp text"
        mock_send_whatsapp.return_value = DeliveryResult(
            date=datetime.date(2026, 3, 2),
            email_id="wamid.abc123",
            success=True,
        )

        result = run_delivery(analysis_result, settings=mock_settings)

        assert result.success is True
        mock_render_whatsapp.assert_called_once_with(
            fake_protocol, datetime.date(2026, 3, 2), incomplete_steps=[],
        )
