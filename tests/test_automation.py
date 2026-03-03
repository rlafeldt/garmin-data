"""Tests for automation module: token persistence, run logging, failure notification."""

from __future__ import annotations

import datetime
from unittest.mock import MagicMock, patch

import pytest
import structlog


@pytest.fixture(autouse=True)
def _reset_structlog():
    """Reset structlog configuration after each test to avoid cross-test pollution."""
    yield
    structlog.reset_defaults()


@pytest.fixture()
def mock_settings(monkeypatch):
    """Create mock settings with all required fields."""
    monkeypatch.setenv("GARMIN_EMAIL", "test@garmin.com")
    monkeypatch.setenv("GARMIN_PASSWORD", "testpass")
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "testkey")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("RESEND_API_KEY", "re_test_key_123")
    monkeypatch.setenv("SENDER_EMAIL", "protocol@example.com")
    monkeypatch.setenv("RECIPIENT_EMAIL", "user@example.com")

    from biointelligence.config import Settings

    return Settings(_env_file=None)


class TestTokenPersistence:
    """Tests for Supabase token persistence functions."""

    def test_load_returns_token_data_when_exists(self):
        """load_tokens_from_supabase returns token_data string when row exists."""
        from biointelligence.automation.tokens import load_tokens_from_supabase

        mock_client = MagicMock()
        fake_token = "a" * 600  # base64 token string > 512 chars
        mock_client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
            "token_data": fake_token,
        }

        result = load_tokens_from_supabase(mock_client)

        mock_client.table.assert_called_once_with("garmin_tokens")
        assert result == fake_token

    def test_load_returns_none_when_empty(self):
        """load_tokens_from_supabase returns None when garmin_tokens table is empty."""
        from biointelligence.automation.tokens import load_tokens_from_supabase

        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = None

        result = load_tokens_from_supabase(mock_client)

        assert result is None

    def test_save_calls_dumps_and_upserts(self):
        """save_tokens_to_supabase calls garmin.garth.dumps() and upserts to garmin_tokens."""
        from biointelligence.automation.tokens import save_tokens_to_supabase

        mock_client = MagicMock()
        mock_garmin = MagicMock()
        fake_token = "b" * 600
        mock_garmin.garth.dumps.return_value = fake_token

        save_tokens_to_supabase(mock_client, mock_garmin)

        mock_garmin.garth.dumps.assert_called_once()
        mock_client.table.assert_called_once_with("garmin_tokens")
        upsert_call = mock_client.table.return_value.upsert
        upsert_call.assert_called_once()
        upsert_data = upsert_call.call_args[0][0]
        assert upsert_data["id"] == "primary"
        assert upsert_data["token_data"] == fake_token
        assert "updated_at" in upsert_data

    def test_save_includes_updated_at_timestamp(self):
        """save_tokens_to_supabase includes updated_at in upserted data."""
        from biointelligence.automation.tokens import save_tokens_to_supabase

        mock_client = MagicMock()
        mock_garmin = MagicMock()
        mock_garmin.garth.dumps.return_value = "c" * 600

        save_tokens_to_supabase(mock_client, mock_garmin)

        upsert_data = mock_client.table.return_value.upsert.call_args[0][0]
        # updated_at should be an ISO-format datetime string
        assert "updated_at" in upsert_data
        # Verify it parses as a valid ISO datetime
        datetime.datetime.fromisoformat(upsert_data["updated_at"])


class TestRunLog:
    """Tests for pipeline run logging."""

    def test_pipeline_run_log_model_fields(self):
        """PipelineRunLog model has all expected fields with defaults."""
        from biointelligence.automation.run_log import PipelineRunLog

        run_log = PipelineRunLog(
            date=datetime.date(2026, 3, 2),
            status="success",
            duration_seconds=42.5,
            started_at="2026-03-02T06:00:00Z",
        )

        assert run_log.date == datetime.date(2026, 3, 2)
        assert run_log.status == "success"
        assert run_log.failed_stage is None
        assert run_log.error_message is None
        assert run_log.duration_seconds == 42.5
        assert run_log.started_at == "2026-03-02T06:00:00Z"

    def test_pipeline_run_log_failure_fields(self):
        """PipelineRunLog model stores failure details."""
        from biointelligence.automation.run_log import PipelineRunLog

        run_log = PipelineRunLog(
            date=datetime.date(2026, 3, 2),
            status="failure",
            failed_stage="ingestion",
            error_message="Connection timeout",
            duration_seconds=5.0,
            started_at="2026-03-02T06:00:00Z",
        )

        assert run_log.status == "failure"
        assert run_log.failed_stage == "ingestion"
        assert run_log.error_message == "Connection timeout"

    def test_log_pipeline_run_upserts_to_table(self):
        """log_pipeline_run upserts to pipeline_runs table with on_conflict='date'."""
        from biointelligence.automation.run_log import PipelineRunLog, log_pipeline_run

        mock_client = MagicMock()
        run_log = PipelineRunLog(
            date=datetime.date(2026, 3, 2),
            status="success",
            duration_seconds=42.5,
            started_at="2026-03-02T06:00:00Z",
        )

        log_pipeline_run(mock_client, run_log)

        mock_client.table.assert_called_once_with("pipeline_runs")
        upsert_call = mock_client.table.return_value.upsert
        upsert_call.assert_called_once()
        upsert_data = upsert_call.call_args[0][0]
        assert upsert_data["date"] == "2026-03-02"
        assert upsert_data["status"] == "success"
        # Verify on_conflict="date"
        upsert_kwargs = upsert_call.call_args[1]
        assert upsert_kwargs.get("on_conflict") == "date"
        upsert_call.return_value.execute.assert_called_once()


class TestFailureNotification:
    """Tests for failure notification email."""

    @patch("biointelligence.automation.notify.send_email")
    def test_sends_email_on_non_delivery_failure(self, mock_send_email, mock_settings):
        """send_failure_notification sends email when failed_stage is not 'delivery'."""
        from biointelligence.automation.notify import send_failure_notification

        send_failure_notification(
            target_date=datetime.date(2026, 3, 2),
            failed_stage="ingestion",
            error_message="Connection timeout",
            settings=mock_settings,
        )

        mock_send_email.assert_called_once()
        call_kwargs = mock_send_email.call_args[1]
        assert call_kwargs["subject"] == "Pipeline Failed -- 2026-03-02"
        assert "ingestion" in call_kwargs["text"]
        assert "Connection timeout" in call_kwargs["text"]
        assert call_kwargs["target_date"] == datetime.date(2026, 3, 2)
        assert call_kwargs["settings"] is mock_settings

    @patch("biointelligence.automation.notify.send_email")
    def test_suppresses_notification_for_delivery_failure(
        self, mock_send_email, mock_settings
    ):
        """send_failure_notification does NOT send email when failed_stage is 'delivery'."""
        from biointelligence.automation.notify import send_failure_notification

        send_failure_notification(
            target_date=datetime.date(2026, 3, 2),
            failed_stage="delivery",
            error_message="Resend API error",
            settings=mock_settings,
        )

        mock_send_email.assert_not_called()

    @patch("biointelligence.automation.notify.send_email")
    def test_catches_send_email_exceptions(self, mock_send_email, mock_settings):
        """send_failure_notification catches exceptions from send_email (best-effort)."""
        from biointelligence.automation.notify import send_failure_notification

        mock_send_email.side_effect = Exception("Resend down")

        # Should NOT raise -- failure notification is best-effort
        send_failure_notification(
            target_date=datetime.date(2026, 3, 2),
            failed_stage="analysis",
            error_message="Model error",
            settings=mock_settings,
        )

        mock_send_email.assert_called_once()

    @patch("biointelligence.automation.notify.send_email")
    def test_email_body_includes_github_actions_url(
        self, mock_send_email, mock_settings, monkeypatch
    ):
        """send_failure_notification includes GitHub Actions run URL in email body."""
        from biointelligence.automation.notify import send_failure_notification

        monkeypatch.setenv("GITHUB_SERVER_URL", "https://github.com")
        monkeypatch.setenv("GITHUB_REPOSITORY", "user/repo")
        monkeypatch.setenv("GITHUB_RUN_ID", "12345")

        send_failure_notification(
            target_date=datetime.date(2026, 3, 2),
            failed_stage="ingestion",
            error_message="Timeout",
            settings=mock_settings,
        )

        call_kwargs = mock_send_email.call_args[1]
        assert "https://github.com/user/repo/actions/runs/12345" in call_kwargs["text"]

    @patch("biointelligence.automation.notify.send_email")
    def test_email_html_wraps_text_in_pre(self, mock_send_email, mock_settings):
        """send_failure_notification wraps plain-text body in <pre> tags for HTML."""
        from biointelligence.automation.notify import send_failure_notification

        send_failure_notification(
            target_date=datetime.date(2026, 3, 2),
            failed_stage="ingestion",
            error_message="Some <script>alert('xss')</script> error",
            settings=mock_settings,
        )

        call_kwargs = mock_send_email.call_args[1]
        assert call_kwargs["html"].startswith("<pre>")
        assert call_kwargs["html"].endswith("</pre>")
        # HTML should be escaped
        assert "<script>" not in call_kwargs["html"]
        assert "&lt;script&gt;" in call_kwargs["html"]
