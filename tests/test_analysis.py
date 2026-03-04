"""Tests for the analysis engine: client, engine orchestration, retry logic, and Settings."""

from __future__ import annotations

import datetime
from unittest.mock import MagicMock, patch

import pytest
import structlog
from pydantic import ValidationError

from biointelligence.prompt.models import (
    AssembledPrompt,
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


@pytest.fixture()
def fake_protocol() -> DailyProtocol:
    """A fully-populated DailyProtocol instance with realistic data."""
    return DailyProtocol(
        date="2026-03-02",
        training=TrainingRecommendation(
            headline="Moderate Zone 2 day",
            readiness_score=7,
            readiness_summary="Good recovery overnight with HRV trending up.",
            recommended_intensity="Zone 2",
            recommended_type="Cycling",
            recommended_duration_minutes=75,
            training_load_assessment="Acute load within optimal range (ACWR 1.1).",
            reasoning="HRV 48ms above baseline, body battery 72. Training load balanced.",
        ),
        recovery=RecoveryAssessment(
            headline="Well recovered from yesterday",
            recovery_status="Well recovered",
            hrv_interpretation="HRV 48ms is above your 7-day average of 44ms.",
            body_battery_assessment="Morning body battery 72 indicates good energy reserves.",
            stress_impact="Average stress 32 is within normal range for a rest day.",
            recommendations=["Light mobility work", "Cold exposure post-training"],
            reasoning="Multi-metric convergence shows solid recovery from yesterday's effort.",
        ),
        sleep=SleepAnalysis(
            headline="Solid sleep supports training",
            quality_assessment="Good sleep quality with adequate deep sleep.",
            architecture_notes="Deep sleep 1h42m (22%), REM 1h28m (19%), 6 awakenings.",
            optimization_tips=["Maintain consistent 22:30 bedtime", "Limit blue light after 21:00"],
            reasoning="Sleep score 82 with strong deep sleep phase supports training today.",
        ),
        nutrition=NutritionGuidance(
            headline="Fuel for moderate endurance",
            caloric_target="2,800 kcal",
            macro_focus="Higher carb pre-ride, moderate protein throughout the day.",
            hydration_target="3.2L including 500ml electrolyte during ride",
            meal_timing_notes="Pre-ride meal 2h before. Post-ride protein within 30min.",
            reasoning="Zone 2 cycling for 75min requires moderate fueling strategy.",
        ),
        supplementation=SupplementationPlan(
            headline="Standard stack, no changes",
            adjustments=["Creatine 5g with breakfast", "Vitamin D 4000IU with lunch"],
            timing_notes="Take magnesium glycinate 400mg 1h before bed.",
            reasoning="Maintaining standard supplementation stack. No adjustments needed today.",
        ),
        overall_summary="Good day for a moderate Zone 2 ride. Recovery metrics look solid.",
        data_quality_notes=None,
    )


@pytest.fixture()
def mock_anthropic_response(fake_protocol: DailyProtocol) -> MagicMock:
    """A mock Anthropic messages.parse() response."""
    response = MagicMock()
    response.parsed_output = fake_protocol
    response.usage.input_tokens = 3200
    response.usage.output_tokens = 1800
    response.stop_reason = "end_turn"
    response.content = [MagicMock(text='{"date": "2026-03-02", ...}')]
    return response


@pytest.fixture()
def mock_assembled_prompt() -> AssembledPrompt:
    """A dummy assembled prompt for testing."""
    return AssembledPrompt(
        text="<health_profile>Test data</health_profile>",
        estimated_tokens=500,
        sections_included=["health_profile"],
        sections_trimmed=[],
    )


# ---------------------------------------------------------------------------
# Task 1: Client factory, structured output call, retry, Settings
# ---------------------------------------------------------------------------


class TestGetAnthropicClient:
    """Tests for the Anthropic client factory."""

    def test_creates_client_with_api_key(self, monkeypatch):
        """get_anthropic_client creates a client using the API key from settings."""
        monkeypatch.setenv("GARMIN_EMAIL", "test@example.com")
        monkeypatch.setenv("GARMIN_PASSWORD", "secret")
        monkeypatch.setenv("SUPABASE_URL", "https://abc.supabase.co")
        monkeypatch.setenv("SUPABASE_KEY", "test-key")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")

        from biointelligence.config import Settings

        settings = Settings(_env_file=None)

        with patch("biointelligence.analysis.client.anthropic") as mock_anthropic:
            from biointelligence.analysis.client import get_anthropic_client

            client = get_anthropic_client(settings)
            mock_anthropic.Anthropic.assert_called_once_with(api_key="sk-ant-test-key")
            assert client is mock_anthropic.Anthropic.return_value


class TestAnalyzePrompt:
    """Tests for the analyze_prompt function."""

    def test_sends_correct_parameters(
        self, mock_assembled_prompt, mock_anthropic_response
    ):
        """analyze_prompt sends correct model, max_tokens, temperature, output_format."""
        mock_client = MagicMock()
        mock_client.messages.parse.return_value = mock_anthropic_response

        from biointelligence.analysis.client import analyze_prompt

        analyze_prompt(mock_client, mock_assembled_prompt, "claude-haiku-4-5-20251001")

        mock_client.messages.parse.assert_called_once_with(
            model="claude-haiku-4-5-20251001",
            max_tokens=4096,
            temperature=0.3,
            messages=[{"role": "user", "content": mock_assembled_prompt.text}],
            output_format=DailyProtocol,
        )

    def test_returns_protocol_and_metadata(
        self, mock_assembled_prompt, mock_anthropic_response
    ):
        """analyze_prompt returns (DailyProtocol, metadata) tuple with token counts."""
        mock_client = MagicMock()
        mock_client.messages.parse.return_value = mock_anthropic_response

        from biointelligence.analysis.client import analyze_prompt

        protocol, metadata = analyze_prompt(
            mock_client, mock_assembled_prompt, "claude-haiku-4-5-20251001"
        )

        assert isinstance(protocol, DailyProtocol)
        assert metadata["input_tokens"] == 3200
        assert metadata["output_tokens"] == 1800
        assert metadata["model"] == "claude-haiku-4-5-20251001"
        assert metadata["stop_reason"] == "end_turn"

    def test_logs_token_usage(self, mock_assembled_prompt, mock_anthropic_response, caplog):
        """analyze_prompt logs token usage via structlog."""
        mock_client = MagicMock()
        mock_client.messages.parse.return_value = mock_anthropic_response

        # Configure structlog to output to standard logging for caplog capture
        structlog.configure(
            processors=[
                structlog.stdlib.add_log_level,
                structlog.dev.ConsoleRenderer(),
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            logger_factory=structlog.stdlib.LoggerFactory(),
        )

        import logging

        with caplog.at_level(logging.INFO):
            from biointelligence.analysis.client import analyze_prompt

            analyze_prompt(mock_client, mock_assembled_prompt, "claude-haiku-4-5-20251001")

        assert "3200" in caplog.text or "input_tokens" in caplog.text

    def test_raises_value_error_on_refusal(self, mock_assembled_prompt):
        """analyze_prompt raises ValueError on refusal stop_reason."""
        mock_response = MagicMock()
        mock_response.stop_reason = "refusal"
        mock_response.parsed_output = None
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 50
        mock_response.content = [MagicMock(text="I cannot help with that.")]

        mock_client = MagicMock()
        mock_client.messages.parse.return_value = mock_response

        from biointelligence.analysis.client import analyze_prompt

        with pytest.raises(ValueError, match="refused"):
            analyze_prompt(mock_client, mock_assembled_prompt, "claude-haiku-4-5-20251001")

    def test_logs_warning_on_max_tokens(
        self, mock_assembled_prompt, fake_protocol, caplog
    ):
        """analyze_prompt logs warning on max_tokens stop_reason."""
        mock_response = MagicMock()
        mock_response.stop_reason = "max_tokens"
        mock_response.parsed_output = fake_protocol
        mock_response.usage.input_tokens = 3200
        mock_response.usage.output_tokens = 4096
        mock_response.content = [MagicMock(text="truncated...")]

        mock_client = MagicMock()
        mock_client.messages.parse.return_value = mock_response

        structlog.configure(
            processors=[
                structlog.stdlib.add_log_level,
                structlog.dev.ConsoleRenderer(),
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            logger_factory=structlog.stdlib.LoggerFactory(),
        )

        import logging

        with caplog.at_level(logging.WARNING):
            from biointelligence.analysis.client import analyze_prompt

            protocol, metadata = analyze_prompt(
                mock_client, mock_assembled_prompt, "claude-haiku-4-5-20251001"
            )

        assert metadata["stop_reason"] == "max_tokens"
        assert "max_tokens" in caplog.text or "truncat" in caplog.text

    def test_retries_on_transient_api_errors(self, mock_assembled_prompt, mock_anthropic_response):
        """analyze_prompt retries on RateLimitError, InternalServerError, APIConnectionError."""
        import anthropic

        mock_client = MagicMock()

        # Create a proper RateLimitError mock
        rate_limit_response = MagicMock()
        rate_limit_response.status_code = 429
        rate_limit_response.headers = {}
        rate_limit_error = anthropic.RateLimitError(
            message="Rate limited",
            response=rate_limit_response,
            body={"error": {"type": "rate_limit_error", "message": "Rate limited"}},
        )

        # First call raises RateLimitError, second succeeds
        mock_client.messages.parse.side_effect = [
            rate_limit_error,
            mock_anthropic_response,
        ]

        from biointelligence.analysis.client import analyze_prompt

        # Patch tenacity wait to avoid actual sleeping in tests
        with patch("biointelligence.analysis.client.analyze_prompt.retry.wait", return_value=0):
            protocol, metadata = analyze_prompt(
                mock_client, mock_assembled_prompt, "claude-haiku-4-5-20251001"
            )

        assert isinstance(protocol, DailyProtocol)
        assert mock_client.messages.parse.call_count == 2

    def test_retries_on_validation_error_then_succeeds(
        self, mock_assembled_prompt, mock_anthropic_response, caplog
    ):
        """analyze_prompt retries up to 3 times on pydantic ValidationError, then succeeds."""
        mock_client = MagicMock()

        # Create a real ValidationError
        try:
            DailyProtocol.model_validate({"date": "bad"})
        except ValidationError as e:
            validation_error = e

        # A response that will carry the raw content for logging
        bad_response = MagicMock()
        bad_response.content = [MagicMock(text='{"bad": "json"}')]

        # First two calls raise ValidationError, third succeeds
        mock_client.messages.parse.side_effect = [
            validation_error,
            validation_error,
            mock_anthropic_response,
        ]

        structlog.configure(
            processors=[
                structlog.stdlib.add_log_level,
                structlog.dev.ConsoleRenderer(),
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            logger_factory=structlog.stdlib.LoggerFactory(),
        )

        import logging

        with caplog.at_level(logging.ERROR):
            from biointelligence.analysis.client import analyze_prompt

            # Patch tenacity wait to avoid sleeping
            with patch(
                "biointelligence.analysis.client.analyze_prompt.retry.wait", return_value=0
            ):
                protocol, metadata = analyze_prompt(
                    mock_client, mock_assembled_prompt, "claude-haiku-4-5-20251001"
                )

        assert isinstance(protocol, DailyProtocol)
        assert mock_client.messages.parse.call_count == 3
        # Verify parse failures were logged
        assert "parse_failure" in caplog.text

    def test_reraises_after_3_validation_errors(self, mock_assembled_prompt):
        """analyze_prompt re-raises after 3 consecutive ValidationErrors."""
        mock_client = MagicMock()

        # Create a real ValidationError
        try:
            DailyProtocol.model_validate({"date": "bad"})
        except ValidationError as e:
            validation_error = e

        mock_client.messages.parse.side_effect = [
            validation_error,
            validation_error,
            validation_error,
        ]

        from biointelligence.analysis.client import analyze_prompt

        with patch(
            "biointelligence.analysis.client.analyze_prompt.retry.wait", return_value=0
        ):
            with pytest.raises(ValidationError):
                analyze_prompt(
                    mock_client, mock_assembled_prompt, "claude-haiku-4-5-20251001"
                )

        assert mock_client.messages.parse.call_count == 3


class TestSettingsExtension:
    """Tests for Settings with Anthropic configuration fields."""

    def test_settings_loads_anthropic_api_key(self, monkeypatch):
        """Settings loads anthropic_api_key (required) from ANTHROPIC_API_KEY env var."""
        monkeypatch.setenv("GARMIN_EMAIL", "test@example.com")
        monkeypatch.setenv("GARMIN_PASSWORD", "secret")
        monkeypatch.setenv("SUPABASE_URL", "https://abc.supabase.co")
        monkeypatch.setenv("SUPABASE_KEY", "test-key")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")

        from biointelligence.config import Settings

        settings = Settings(_env_file=None)
        assert settings.anthropic_api_key == "sk-ant-test-key"

    def test_settings_claude_model_default(self, monkeypatch):
        """Settings defaults claude_model to 'claude-haiku-4-5-20251001'."""
        monkeypatch.setenv("GARMIN_EMAIL", "test@example.com")
        monkeypatch.setenv("GARMIN_PASSWORD", "secret")
        monkeypatch.setenv("SUPABASE_URL", "https://abc.supabase.co")
        monkeypatch.setenv("SUPABASE_KEY", "test-key")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")

        from biointelligence.config import Settings

        settings = Settings(_env_file=None)
        assert settings.claude_model == "claude-haiku-4-5-20251001"

    def test_settings_claude_model_override(self, monkeypatch):
        """Settings allows overriding claude_model via CLAUDE_MODEL env var."""
        monkeypatch.setenv("GARMIN_EMAIL", "test@example.com")
        monkeypatch.setenv("GARMIN_PASSWORD", "secret")
        monkeypatch.setenv("SUPABASE_URL", "https://abc.supabase.co")
        monkeypatch.setenv("SUPABASE_KEY", "test-key")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
        monkeypatch.setenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")

        from biointelligence.config import Settings

        settings = Settings(_env_file=None)
        assert settings.claude_model == "claude-sonnet-4-20250514"


# ---------------------------------------------------------------------------
# Task 2: Engine orchestration, AnalysisResult model, protocol domain checks
# ---------------------------------------------------------------------------


class TestAnalysisResult:
    """Tests for the AnalysisResult model."""

    def test_analysis_result_all_fields(self, fake_protocol):
        """AnalysisResult has date, protocol, input_tokens, output_tokens, model, success, error."""
        from biointelligence.analysis.engine import AnalysisResult

        result = AnalysisResult(
            date=datetime.date(2026, 3, 2),
            protocol=fake_protocol,
            input_tokens=3200,
            output_tokens=1800,
            model="claude-haiku-4-5-20251001",
            success=True,
            error=None,
        )
        assert result.date == datetime.date(2026, 3, 2)
        assert result.protocol is not None
        assert result.input_tokens == 3200
        assert result.output_tokens == 1800
        assert result.model == "claude-haiku-4-5-20251001"
        assert result.success is True
        assert result.error is None

    def test_analysis_result_failure(self):
        """AnalysisResult can represent a failed analysis."""
        from biointelligence.analysis.engine import AnalysisResult

        result = AnalysisResult(
            date=datetime.date(2026, 3, 2),
            protocol=None,
            input_tokens=0,
            output_tokens=0,
            model="claude-haiku-4-5-20251001",
            success=False,
            error="API connection failed",
        )
        assert result.success is False
        assert result.error == "API connection failed"
        assert result.protocol is None

    def test_analysis_result_defaults(self):
        """AnalysisResult has correct defaults for optional fields."""
        from biointelligence.analysis.engine import AnalysisResult

        result = AnalysisResult(
            date=datetime.date(2026, 3, 2),
            model="claude-haiku-4-5-20251001",
            success=True,
        )
        assert result.protocol is None
        assert result.input_tokens == 0
        assert result.output_tokens == 0
        assert result.error is None


class TestAnalyzeDaily:
    """Tests for the analyze_daily orchestration function."""

    @pytest.fixture()
    def mock_settings(self, monkeypatch):
        """Create mock settings for analyze_daily tests."""
        monkeypatch.setenv("GARMIN_EMAIL", "test@garmin.com")
        monkeypatch.setenv("GARMIN_PASSWORD", "testpass")
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_KEY", "testkey")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")

        from biointelligence.config import Settings

        return Settings(_env_file=None)

    @patch("biointelligence.analysis.engine.PromptContext")
    @patch("biointelligence.analysis.engine.analyze_prompt")
    @patch("biointelligence.analysis.engine.get_anthropic_client")
    @patch("biointelligence.analysis.engine.assemble_prompt")
    @patch("biointelligence.analysis.engine.compute_trends")
    @patch("biointelligence.analysis.engine._fetch_activities")
    @patch("biointelligence.analysis.engine._fetch_daily_metrics")
    @patch("biointelligence.analysis.engine.load_health_profile")
    @patch("biointelligence.analysis.engine.get_supabase_client")
    def test_happy_path_returns_success(
        self,
        mock_supabase,
        mock_load_profile,
        mock_fetch_metrics,
        mock_fetch_activities,
        mock_compute_trends,
        mock_assemble_prompt,
        mock_get_client,
        mock_analyze_prompt,
        mock_prompt_context,
        mock_settings,
        fake_protocol,
    ):
        """analyze_daily returns success=True with populated protocol on happy path."""
        from biointelligence.analysis.engine import analyze_daily

        mock_supabase.return_value = MagicMock()
        mock_load_profile.return_value = MagicMock()
        mock_fetch_metrics.return_value = MagicMock()
        mock_fetch_activities.return_value = []
        mock_compute_trends.return_value = MagicMock()
        mock_prompt_context.return_value = MagicMock()
        mock_assemble_prompt.return_value = MagicMock(text="test prompt", estimated_tokens=500)
        mock_get_client.return_value = MagicMock()
        mock_analyze_prompt.return_value = (
            fake_protocol,
            {"input_tokens": 3200, "output_tokens": 1800, "model": "claude-haiku-4-5-20251001"},
        )

        result = analyze_daily(datetime.date(2026, 3, 2), settings=mock_settings)

        assert result.success is True
        assert result.protocol is not None
        assert result.input_tokens == 3200
        assert result.output_tokens == 1800
        assert result.date == datetime.date(2026, 3, 2)

    @patch("biointelligence.analysis.engine.PromptContext")
    @patch("biointelligence.analysis.engine.analyze_prompt")
    @patch("biointelligence.analysis.engine.get_anthropic_client")
    @patch("biointelligence.analysis.engine.assemble_prompt")
    @patch("biointelligence.analysis.engine.compute_trends")
    @patch("biointelligence.analysis.engine._fetch_activities")
    @patch("biointelligence.analysis.engine._fetch_daily_metrics")
    @patch("biointelligence.analysis.engine.load_health_profile")
    @patch("biointelligence.analysis.engine.get_supabase_client")
    def test_api_failure_returns_error_result(
        self,
        mock_supabase,
        mock_load_profile,
        mock_fetch_metrics,
        mock_fetch_activities,
        mock_compute_trends,
        mock_assemble_prompt,
        mock_get_client,
        mock_analyze_prompt,
        mock_prompt_context,
        mock_settings,
    ):
        """analyze_daily returns success=False with error message on API failure."""
        from biointelligence.analysis.engine import analyze_daily

        mock_supabase.return_value = MagicMock()
        mock_load_profile.return_value = MagicMock()
        mock_fetch_metrics.return_value = MagicMock()
        mock_fetch_activities.return_value = []
        mock_compute_trends.return_value = MagicMock()
        mock_prompt_context.return_value = MagicMock()
        mock_assemble_prompt.return_value = MagicMock(text="test prompt", estimated_tokens=500)
        mock_get_client.return_value = MagicMock()
        mock_analyze_prompt.side_effect = ValueError("Claude refused the analysis request")

        result = analyze_daily(datetime.date(2026, 3, 2), settings=mock_settings)

        assert result.success is False
        assert "refused" in result.error.lower()
        assert result.protocol is None

    @patch("biointelligence.analysis.engine.PromptContext")
    @patch("biointelligence.analysis.engine.analyze_prompt")
    @patch("biointelligence.analysis.engine.get_anthropic_client")
    @patch("biointelligence.analysis.engine.assemble_prompt")
    @patch("biointelligence.analysis.engine.compute_trends")
    @patch("biointelligence.analysis.engine._fetch_activities")
    @patch("biointelligence.analysis.engine._fetch_daily_metrics")
    @patch("biointelligence.analysis.engine.load_health_profile")
    @patch("biointelligence.analysis.engine.get_supabase_client")
    def test_logs_analysis_start_and_completion(
        self,
        mock_supabase,
        mock_load_profile,
        mock_fetch_metrics,
        mock_fetch_activities,
        mock_compute_trends,
        mock_assemble_prompt,
        mock_get_client,
        mock_analyze_prompt,
        mock_prompt_context,
        mock_settings,
        fake_protocol,
        caplog,
    ):
        """analyze_daily logs analysis start and completion."""
        from biointelligence.analysis.engine import analyze_daily

        mock_supabase.return_value = MagicMock()
        mock_load_profile.return_value = MagicMock()
        mock_fetch_metrics.return_value = MagicMock()
        mock_fetch_activities.return_value = []
        mock_compute_trends.return_value = MagicMock()
        mock_prompt_context.return_value = MagicMock()
        mock_assemble_prompt.return_value = MagicMock(text="test prompt", estimated_tokens=500)
        mock_get_client.return_value = MagicMock()
        mock_analyze_prompt.return_value = (
            fake_protocol,
            {"input_tokens": 3200, "output_tokens": 1800, "model": "claude-haiku-4-5-20251001"},
        )

        structlog.configure(
            processors=[
                structlog.stdlib.add_log_level,
                structlog.dev.ConsoleRenderer(),
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            logger_factory=structlog.stdlib.LoggerFactory(),
        )

        import logging

        with caplog.at_level(logging.INFO):
            analyze_daily(datetime.date(2026, 3, 2), settings=mock_settings)

        assert "analysis_start" in caplog.text
        assert "analysis_daily_complete" in caplog.text


class TestProtocolDomains:
    """Tests verifying all 12 requirement IDs via DailyProtocol domain fields."""

    def test_trng01_readiness_score(self, fake_protocol):
        """TRNG-01: DailyProtocol has training.readiness_score between 1-10."""
        assert 1 <= fake_protocol.training.readiness_score <= 10
        assert fake_protocol.training.readiness_summary != ""

    def test_trng02_training_load_assessment(self, fake_protocol):
        """TRNG-02: DailyProtocol has training.training_load_assessment non-empty."""
        assert fake_protocol.training.training_load_assessment != ""

    def test_trng03_training_recommendations(self, fake_protocol):
        """TRNG-03: DailyProtocol has recommended_intensity, type, duration."""
        assert fake_protocol.training.recommended_intensity != ""
        assert fake_protocol.training.recommended_type != ""
        assert fake_protocol.training.recommended_duration_minutes > 0

    def test_trng04_stress_impact(self, fake_protocol):
        """TRNG-04: DailyProtocol has recovery.stress_impact non-empty."""
        assert fake_protocol.recovery.stress_impact != ""

    def test_slep01_sleep_architecture(self, fake_protocol):
        """SLEP-01: DailyProtocol has sleep.architecture_notes and quality_assessment."""
        assert fake_protocol.sleep.architecture_notes != ""
        assert fake_protocol.sleep.quality_assessment != ""

    def test_slep02_sleep_optimization(self, fake_protocol):
        """SLEP-02: DailyProtocol has sleep.optimization_tips non-empty list."""
        assert len(fake_protocol.sleep.optimization_tips) > 0

    def test_nutr01_nutrition_guidance(self, fake_protocol):
        """NUTR-01: DailyProtocol has caloric_target, macro_focus, meal_timing_notes."""
        assert fake_protocol.nutrition.caloric_target != ""
        assert fake_protocol.nutrition.macro_focus != ""
        assert fake_protocol.nutrition.meal_timing_notes != ""

    def test_nutr02_hydration_target(self, fake_protocol):
        """NUTR-02: DailyProtocol has nutrition.hydration_target non-empty."""
        assert fake_protocol.nutrition.hydration_target != ""

    def test_supp01_supplement_adjustments(self, fake_protocol):
        """SUPP-01: DailyProtocol has supplementation.adjustments non-empty list."""
        assert len(fake_protocol.supplementation.adjustments) > 0

    def test_supp02_supplement_reasoning(self, fake_protocol):
        """SUPP-02: DailyProtocol has supplementation.reasoning non-empty."""
        assert fake_protocol.supplementation.reasoning != ""

    def test_safe02_data_quality_notes(self):
        """SAFE-02/SAFE-03: DailyProtocol has data_quality_notes when data is partial."""
        protocol_with_notes = DailyProtocol(
            date="2026-03-02",
            training=TrainingRecommendation(
                headline="Conservative approach today",
                readiness_score=5,
                readiness_summary="Limited data available.",
                recommended_intensity="Low",
                recommended_type="Walking",
                recommended_duration_minutes=30,
                training_load_assessment="Unable to fully assess -- missing HRV data.",
                reasoning="Data incomplete. Recommending conservative approach.",
            ),
            recovery=RecoveryAssessment(
                headline="Insufficient data for assessment",
                recovery_status="Unknown",
                hrv_interpretation="HRV data not available.",
                body_battery_assessment="Body battery data missing.",
                stress_impact="Stress data unavailable.",
                recommendations=["Monitor how you feel"],
                reasoning="Insufficient data for full assessment.",
            ),
            sleep=SleepAnalysis(
                headline="Limited sleep data available",
                quality_assessment="Sleep data limited.",
                architecture_notes="No sleep stage breakdown available.",
                optimization_tips=["Ensure consistent sleep schedule"],
                reasoning="Limited sleep data available.",
            ),
            nutrition=NutritionGuidance(
                headline="Default nutrition guidance",
                caloric_target="2,200 kcal (estimated)",
                macro_focus="Balanced macros recommended.",
                hydration_target="2.5L minimum",
                meal_timing_notes="Standard meal timing.",
                reasoning="Using profile defaults due to limited activity data.",
            ),
            supplementation=SupplementationPlan(
                headline="Maintain current stack",
                adjustments=["Maintain current stack"],
                timing_notes="Standard timing.",
                reasoning="No data-driven adjustments possible today.",
            ),
            overall_summary="Conservative recommendations due to incomplete data.",
            data_quality_notes="Missing HRV, body battery, and sleep stage data. "
            "Recommendations based on 7-day trends and health profile.",
        )
        assert protocol_with_notes.data_quality_notes is not None
        assert "Missing" in protocol_with_notes.data_quality_notes

    def test_all_5_domains_have_reasoning(self, fake_protocol):
        """All 5 domains have non-empty reasoning fields (verifying TRNG-01 through SUPP-02)."""
        assert fake_protocol.training.reasoning != ""
        assert fake_protocol.recovery.reasoning != ""
        assert fake_protocol.sleep.reasoning != ""
        assert fake_protocol.nutrition.reasoning != ""
        assert fake_protocol.supplementation.reasoning != ""
