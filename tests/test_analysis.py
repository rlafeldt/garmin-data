"""Tests for the analysis engine: client factory, structured output call, retry logic, and Settings."""

from __future__ import annotations

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
            readiness_score=7,
            readiness_summary="Good recovery overnight with HRV trending up.",
            recommended_intensity="Zone 2",
            recommended_type="Cycling",
            recommended_duration_minutes=75,
            training_load_assessment="Acute load within optimal range (ACWR 1.1).",
            reasoning="HRV 48ms above baseline, body battery 72. Training load balanced.",
        ),
        recovery=RecoveryAssessment(
            recovery_status="Well recovered",
            hrv_interpretation="HRV 48ms is above your 7-day average of 44ms.",
            body_battery_assessment="Morning body battery 72 indicates good energy reserves.",
            stress_impact="Average stress 32 is within normal range for a rest day.",
            recommendations=["Light mobility work", "Cold exposure post-training"],
            reasoning="Multi-metric convergence shows solid recovery from yesterday's effort.",
        ),
        sleep=SleepAnalysis(
            quality_assessment="Good sleep quality with adequate deep sleep.",
            architecture_notes="Deep sleep 1h42m (22%), REM 1h28m (19%), 6 awakenings.",
            optimization_tips=["Maintain consistent 22:30 bedtime", "Limit blue light after 21:00"],
            reasoning="Sleep score 82 with strong deep sleep phase supports training today.",
        ),
        nutrition=NutritionGuidance(
            caloric_target="2,800 kcal",
            macro_focus="Higher carb pre-ride, moderate protein throughout the day.",
            hydration_target="3.2L including 500ml electrolyte during ride",
            meal_timing_notes="Pre-ride meal 2h before. Post-ride protein within 30min.",
            reasoning="Zone 2 cycling for 75min requires moderate fueling strategy.",
        ),
        supplementation=SupplementationPlan(
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

        analyze_prompt(mock_client, mock_assembled_prompt, "claude-haiku-4-5-20250514")

        mock_client.messages.parse.assert_called_once_with(
            model="claude-haiku-4-5-20250514",
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
            mock_client, mock_assembled_prompt, "claude-haiku-4-5-20250514"
        )

        assert isinstance(protocol, DailyProtocol)
        assert metadata["input_tokens"] == 3200
        assert metadata["output_tokens"] == 1800
        assert metadata["model"] == "claude-haiku-4-5-20250514"
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

            analyze_prompt(mock_client, mock_assembled_prompt, "claude-haiku-4-5-20250514")

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
            analyze_prompt(mock_client, mock_assembled_prompt, "claude-haiku-4-5-20250514")

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
                mock_client, mock_assembled_prompt, "claude-haiku-4-5-20250514"
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
                mock_client, mock_assembled_prompt, "claude-haiku-4-5-20250514"
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
                    mock_client, mock_assembled_prompt, "claude-haiku-4-5-20250514"
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
                    mock_client, mock_assembled_prompt, "claude-haiku-4-5-20250514"
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
        """Settings defaults claude_model to 'claude-haiku-4-5-20250514'."""
        monkeypatch.setenv("GARMIN_EMAIL", "test@example.com")
        monkeypatch.setenv("GARMIN_PASSWORD", "secret")
        monkeypatch.setenv("SUPABASE_URL", "https://abc.supabase.co")
        monkeypatch.setenv("SUPABASE_KEY", "test-key")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")

        from biointelligence.config import Settings

        settings = Settings(_env_file=None)
        assert settings.claude_model == "claude-haiku-4-5-20250514"

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
