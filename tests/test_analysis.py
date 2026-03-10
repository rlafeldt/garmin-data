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
)


@pytest.fixture(autouse=True)
def _reset_structlog():
    """Reset structlog configuration after each test to avoid cross-test pollution."""
    yield
    structlog.reset_defaults()


@pytest.fixture()
def fake_protocol() -> DailyProtocol:
    """A fully-populated DailyProtocol instance with narrative insight."""
    return DailyProtocol(
        date="2026-03-02",
        readiness_score=7,
        insight=(
            "BIOINTELLIGENCE — Mar 2, 2026\n\n"
            "Your recovery is solid. HRV at 48ms sits above baseline."
        ),
        insight_html=(
            "BIOINTELLIGENCE — Mar 2, 2026\n\n"
            "Your recovery is solid. HRV at 48ms sits [above baseline](https://example.com)."
        ),
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




# ---------------------------------------------------------------------------
# Phase 6 Plan 02: analyze_daily wiring for anomaly detection
# ---------------------------------------------------------------------------


class TestAnalyzeDailyAnomalyWiring:
    """Tests for analyze_daily orchestrating 28-day trends and anomaly detection."""

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

    @patch("biointelligence.analysis.engine.detect_anomalies")
    @patch("biointelligence.analysis.engine.fetch_trend_window")
    @patch("biointelligence.analysis.engine.compute_extended_trends")
    @patch("biointelligence.analysis.engine.PromptContext")
    @patch("biointelligence.analysis.engine.analyze_prompt")
    @patch("biointelligence.analysis.engine.get_anthropic_client")
    @patch("biointelligence.analysis.engine.assemble_prompt")
    @patch("biointelligence.analysis.engine.compute_trends")
    @patch("biointelligence.analysis.engine._fetch_activities")
    @patch("biointelligence.analysis.engine._fetch_daily_metrics")
    @patch("biointelligence.analysis.engine.load_health_profile")
    @patch("biointelligence.analysis.engine.get_supabase_client")
    def test_calls_compute_extended_trends_and_detect_anomalies(
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
        mock_compute_extended,
        mock_fetch_trend_window,
        mock_detect_anomalies,
        mock_settings,
        fake_protocol,
    ):
        """analyze_daily calls compute_extended_trends and detect_anomalies."""
        from biointelligence.analysis.engine import analyze_daily

        mock_supabase.return_value = MagicMock()
        mock_load_profile.return_value = MagicMock()
        mock_fetch_metrics.return_value = MagicMock()
        mock_fetch_activities.return_value = []
        mock_compute_trends.return_value = MagicMock()
        mock_compute_extended.return_value = MagicMock()
        mock_fetch_trend_window.return_value = []
        mock_detect_anomalies.return_value = MagicMock(alerts=[], metrics_checked=5)
        mock_prompt_context.return_value = MagicMock()
        mock_assemble_prompt.return_value = MagicMock(text="test", estimated_tokens=500)
        mock_get_client.return_value = MagicMock()
        mock_analyze_prompt.return_value = (
            fake_protocol,
            {"input_tokens": 3200, "output_tokens": 1800, "model": "claude-haiku-4-5-20251001"},
        )

        result = analyze_daily(datetime.date(2026, 3, 2), settings=mock_settings)

        assert result.success is True
        mock_compute_extended.assert_called_once()
        mock_detect_anomalies.assert_called_once()

    @patch("biointelligence.analysis.engine.detect_anomalies")
    @patch("biointelligence.analysis.engine.fetch_trend_window")
    @patch("biointelligence.analysis.engine.compute_extended_trends")
    @patch("biointelligence.analysis.engine.PromptContext")
    @patch("biointelligence.analysis.engine.analyze_prompt")
    @patch("biointelligence.analysis.engine.get_anthropic_client")
    @patch("biointelligence.analysis.engine.assemble_prompt")
    @patch("biointelligence.analysis.engine.compute_trends")
    @patch("biointelligence.analysis.engine._fetch_activities")
    @patch("biointelligence.analysis.engine._fetch_daily_metrics")
    @patch("biointelligence.analysis.engine.load_health_profile")
    @patch("biointelligence.analysis.engine.get_supabase_client")
    def test_passes_extended_trends_and_anomaly_to_prompt_context(
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
        mock_compute_extended,
        mock_fetch_trend_window,
        mock_detect_anomalies,
        mock_settings,
        fake_protocol,
    ):
        """analyze_daily passes extended_trends and anomaly_result to PromptContext."""
        from biointelligence.analysis.engine import analyze_daily

        extended_result = MagicMock(name="extended_trends")
        anomaly_result = MagicMock(name="anomaly_result", alerts=[], metrics_checked=3)

        mock_supabase.return_value = MagicMock()
        mock_load_profile.return_value = MagicMock()
        mock_fetch_metrics.return_value = MagicMock()
        mock_fetch_activities.return_value = []
        mock_compute_trends.return_value = MagicMock()
        mock_compute_extended.return_value = extended_result
        mock_fetch_trend_window.return_value = [{"date": "2026-03-01"}]
        mock_detect_anomalies.return_value = anomaly_result
        mock_prompt_context.return_value = MagicMock()
        mock_assemble_prompt.return_value = MagicMock(text="test", estimated_tokens=500)
        mock_get_client.return_value = MagicMock()
        mock_analyze_prompt.return_value = (
            fake_protocol,
            {"input_tokens": 3200, "output_tokens": 1800, "model": "claude-haiku-4-5-20251001"},
        )

        analyze_daily(datetime.date(2026, 3, 2), settings=mock_settings)

        # Verify PromptContext was called with extended_trends and anomaly_result
        call_kwargs = mock_prompt_context.call_args
        assert call_kwargs.kwargs.get("extended_trends") is extended_result
        assert call_kwargs.kwargs.get("anomaly_result") is anomaly_result

    @patch("biointelligence.analysis.engine.detect_anomalies")
    @patch("biointelligence.analysis.engine.fetch_trend_window")
    @patch("biointelligence.analysis.engine.compute_extended_trends")
    @patch("biointelligence.analysis.engine.PromptContext")
    @patch("biointelligence.analysis.engine.analyze_prompt")
    @patch("biointelligence.analysis.engine.get_anthropic_client")
    @patch("biointelligence.analysis.engine.assemble_prompt")
    @patch("biointelligence.analysis.engine.compute_trends")
    @patch("biointelligence.analysis.engine._fetch_activities")
    @patch("biointelligence.analysis.engine._fetch_daily_metrics")
    @patch("biointelligence.analysis.engine.load_health_profile")
    @patch("biointelligence.analysis.engine.get_supabase_client")
    def test_graceful_degradation_when_extended_trends_fails(
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
        mock_compute_extended,
        mock_fetch_trend_window,
        mock_detect_anomalies,
        mock_settings,
        fake_protocol,
    ):
        """analyze_daily still succeeds when compute_extended_trends fails."""
        from biointelligence.analysis.engine import analyze_daily

        mock_supabase.return_value = MagicMock()
        mock_load_profile.return_value = MagicMock()
        mock_fetch_metrics.return_value = MagicMock()
        mock_fetch_activities.return_value = []
        mock_compute_trends.return_value = MagicMock()
        # Extended trends throws an exception
        mock_compute_extended.side_effect = ConnectionError("Supabase timeout")
        mock_prompt_context.return_value = MagicMock()
        mock_assemble_prompt.return_value = MagicMock(text="test", estimated_tokens=500)
        mock_get_client.return_value = MagicMock()
        mock_analyze_prompt.return_value = (
            fake_protocol,
            {"input_tokens": 3200, "output_tokens": 1800, "model": "claude-haiku-4-5-20251001"},
        )

        result = analyze_daily(datetime.date(2026, 3, 2), settings=mock_settings)

        # Should still succeed -- graceful degradation
        assert result.success is True
        assert result.protocol is not None
        # PromptContext should be called with None for extended_trends and anomaly_result
        call_kwargs = mock_prompt_context.call_args
        assert call_kwargs.kwargs.get("extended_trends") is None
        assert call_kwargs.kwargs.get("anomaly_result") is None
