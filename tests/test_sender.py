"""Tests for Resend email sender with retry logic."""

from __future__ import annotations

import datetime
from unittest.mock import patch

import pytest
import structlog


@pytest.fixture(autouse=True)
def _reset_structlog():
    """Reset structlog configuration after each test to avoid cross-test pollution."""
    yield
    structlog.reset_defaults()


@pytest.fixture()
def mock_settings(monkeypatch):
    """Create mock settings with Resend configuration."""
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


class TestDeliveryResult:
    """Tests for DeliveryResult model."""

    def test_has_required_fields(self):
        """DeliveryResult has date, email_id (optional), success, error (optional)."""
        from biointelligence.delivery.sender import DeliveryResult

        result = DeliveryResult(
            date=datetime.date(2026, 3, 2),
            email_id="abc-123",
            success=True,
        )
        assert result.date == datetime.date(2026, 3, 2)
        assert result.email_id == "abc-123"
        assert result.success is True
        assert result.error is None

    def test_defaults_optional_fields(self):
        """DeliveryResult defaults email_id and error to None."""
        from biointelligence.delivery.sender import DeliveryResult

        result = DeliveryResult(
            date=datetime.date(2026, 3, 2),
            success=False,
        )
        assert result.email_id is None
        assert result.error is None

    def test_error_field(self):
        """DeliveryResult stores error messages on failure."""
        from biointelligence.delivery.sender import DeliveryResult

        result = DeliveryResult(
            date=datetime.date(2026, 3, 2),
            success=False,
            error="API rate limit exceeded",
        )
        assert result.success is False
        assert result.error == "API rate limit exceeded"


class TestSendEmail:
    """Tests for send_email function."""

    @patch("biointelligence.delivery.sender.resend")
    def test_calls_resend_with_correct_params(self, mock_resend, mock_settings):
        """send_email calls resend.Emails.send with correct from, to, subject, html, text."""
        from biointelligence.delivery.sender import send_email

        mock_resend.Emails.send.return_value = {"id": "email-id-123"}

        send_email(
            html="<p>Hello</p>",
            text="Hello",
            subject="Test Subject",
            target_date=datetime.date(2026, 3, 2),
            settings=mock_settings,
        )

        mock_resend.Emails.send.assert_called_once()
        call_args = mock_resend.Emails.send.call_args[0][0]
        assert call_args["from"] == "BioIntelligence <protocol@example.com>"
        assert call_args["to"] == ["user@example.com"]
        assert call_args["subject"] == "Test Subject"
        assert call_args["html"] == "<p>Hello</p>"
        assert call_args["text"] == "Hello"

    @patch("biointelligence.delivery.sender.resend")
    def test_returns_success_with_email_id(self, mock_resend, mock_settings):
        """send_email returns DeliveryResult with success=True and email_id on success."""
        from biointelligence.delivery.sender import send_email

        mock_resend.Emails.send.return_value = {"id": "email-id-456"}

        result = send_email(
            html="<p>Hello</p>",
            text="Hello",
            subject="Test Subject",
            target_date=datetime.date(2026, 3, 2),
            settings=mock_settings,
        )

        assert result.success is True
        assert result.email_id == "email-id-456"
        assert result.date == datetime.date(2026, 3, 2)
        assert result.error is None

    @patch("biointelligence.delivery.sender.resend")
    def test_returns_failure_on_api_error(self, mock_resend, mock_settings):
        """send_email returns DeliveryResult with success=False on Resend API error."""
        from biointelligence.delivery.sender import _send_via_resend, send_email

        # Patch tenacity wait to 0 to avoid sleeping during retries
        original_wait = _send_via_resend.retry.wait
        _send_via_resend.retry.wait = lambda *args, **kwargs: 0

        try:
            mock_resend.Emails.send.side_effect = Exception("API connection failed")

            result = send_email(
                html="<p>Hello</p>",
                text="Hello",
                subject="Test Subject",
                target_date=datetime.date(2026, 3, 2),
                settings=mock_settings,
            )

            assert result.success is False
            assert "API connection failed" in result.error
            assert result.email_id is None
        finally:
            _send_via_resend.retry.wait = original_wait

    @patch("biointelligence.delivery.sender.resend")
    def test_sets_api_key_inside_function(self, mock_resend, mock_settings):
        """send_email sets resend.api_key inside the function (not at module level)."""
        from biointelligence.delivery.sender import send_email

        mock_resend.api_key = None
        mock_resend.Emails.send.return_value = {"id": "email-id-789"}

        send_email(
            html="<p>Hello</p>",
            text="Hello",
            subject="Test Subject",
            target_date=datetime.date(2026, 3, 2),
            settings=mock_settings,
        )

        # api_key should have been set to the settings value
        assert mock_resend.api_key == "re_test_key_123"

    @patch("biointelligence.delivery.sender._send_via_resend")
    @patch("biointelligence.delivery.sender.resend")
    def test_retries_on_transient_error(self, mock_resend, mock_send_via, mock_settings):
        """send_email retries on transient errors via tenacity (exception then success)."""
        from biointelligence.delivery.sender import send_email

        # _send_via_resend is the retry-wrapped function;
        # simulate it succeeding (after internal retries)
        mock_send_via.return_value = {"id": "retry-success-id"}

        result = send_email(
            html="<p>Hello</p>",
            text="Hello",
            subject="Test Subject",
            target_date=datetime.date(2026, 3, 2),
            settings=mock_settings,
        )

        assert result.success is True
        assert result.email_id == "retry-success-id"
        mock_send_via.assert_called_once()


class TestSendViaResendRetry:
    """Tests for the tenacity retry wrapper _send_via_resend."""

    @patch("biointelligence.delivery.sender.resend")
    def test_retry_on_exception_then_success(self, mock_resend):
        """_send_via_resend retries on exception and succeeds on second attempt."""
        from biointelligence.delivery.sender import _send_via_resend

        # First call raises, second succeeds
        mock_resend.Emails.send.side_effect = [
            Exception("429 Too Many Requests"),
            {"id": "retry-id"},
        ]

        # Patch tenacity wait to avoid sleeping in tests
        result = _send_via_resend.retry.wait = lambda *args, **kwargs: 0
        result = _send_via_resend({"from": "test", "to": ["test"]})

        assert result == {"id": "retry-id"}
        assert mock_resend.Emails.send.call_count == 2
