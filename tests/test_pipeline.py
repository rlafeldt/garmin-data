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
from biointelligence.prompt.models import (
    DailyProtocol,
    NutritionGuidance,
    RecoveryAssessment,
    SleepAnalysis,
    SupplementationPlan,
    TrainingRecommendation,
)


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
    """A populated DailyProtocol for run_analysis tests."""
    return DailyProtocol(
        date="2026-03-02",
        training=TrainingRecommendation(
            readiness_score=7,
            readiness_summary="Good recovery.",
            recommended_intensity="Zone 2",
            recommended_type="Cycling",
            recommended_duration_minutes=75,
            training_load_assessment="Optimal.",
            reasoning="HRV above baseline.",
        ),
        recovery=RecoveryAssessment(
            recovery_status="Well recovered",
            hrv_interpretation="HRV 48ms above average.",
            body_battery_assessment="Body battery 72.",
            stress_impact="Stress 32 normal.",
            recommendations=["Light mobility"],
            reasoning="Solid recovery.",
        ),
        sleep=SleepAnalysis(
            quality_assessment="Good quality.",
            architecture_notes="Deep 1h42m.",
            optimization_tips=["Consistent bedtime"],
            reasoning="Score 82.",
        ),
        nutrition=NutritionGuidance(
            caloric_target="2,800 kcal",
            macro_focus="Higher carb.",
            hydration_target="3.2L",
            meal_timing_notes="Pre-ride 2h.",
            reasoning="Moderate fueling.",
        ),
        supplementation=SupplementationPlan(
            adjustments=["Creatine 5g"],
            timing_notes="Magnesium before bed.",
            reasoning="Standard stack.",
        ),
        overall_summary="Good day for Zone 2.",
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
            model="claude-haiku-4-5-20250514",
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
            model="claude-haiku-4-5-20250514",
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
            model="claude-haiku-4-5-20250514",
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
            model="claude-haiku-4-5-20250514",
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
            model="claude-haiku-4-5-20250514",
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
            model="claude-haiku-4-5-20250514",
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
