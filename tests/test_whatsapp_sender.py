"""Tests for WhatsApp sender with retry logic via Meta Cloud API."""

from __future__ import annotations

import datetime
from unittest.mock import MagicMock, patch

import httpx
import pytest
import structlog


@pytest.fixture(autouse=True)
def _reset_structlog():
    """Reset structlog configuration after each test to avoid cross-test pollution."""
    yield
    structlog.reset_defaults()


@pytest.fixture()
def mock_settings(monkeypatch):
    """Create mock settings with WhatsApp configuration."""
    monkeypatch.setenv("GARMIN_EMAIL", "test@garmin.com")
    monkeypatch.setenv("GARMIN_PASSWORD", "testpass")
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "testkey")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "wa_test_token_123")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "1234567890")
    monkeypatch.setenv("WHATSAPP_RECIPIENT_PHONE", "+491701234567")

    from biointelligence.config import Settings

    return Settings(_env_file=None)


# ---------------------------------------------------------------------------
# Settings WhatsApp fields
# ---------------------------------------------------------------------------


class TestSettingsWhatsApp:
    """Tests for Settings WhatsApp configuration fields."""

    def test_settings_loads_whatsapp_access_token(self, monkeypatch):
        """Settings loads WHATSAPP_ACCESS_TOKEN from env."""
        monkeypatch.setenv("GARMIN_EMAIL", "test@example.com")
        monkeypatch.setenv("GARMIN_PASSWORD", "secret")
        monkeypatch.setenv("SUPABASE_URL", "https://abc.supabase.co")
        monkeypatch.setenv("SUPABASE_KEY", "test-key")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
        monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "wa_token_abc")

        from biointelligence.config import Settings

        settings = Settings(_env_file=None)
        assert settings.whatsapp_access_token == "wa_token_abc"

    def test_settings_whatsapp_access_token_defaults_empty(self, monkeypatch):
        """Settings defaults whatsapp_access_token to empty string when not set."""
        monkeypatch.setenv("GARMIN_EMAIL", "test@example.com")
        monkeypatch.setenv("GARMIN_PASSWORD", "secret")
        monkeypatch.setenv("SUPABASE_URL", "https://abc.supabase.co")
        monkeypatch.setenv("SUPABASE_KEY", "test-key")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")

        from biointelligence.config import Settings

        settings = Settings(_env_file=None)
        assert settings.whatsapp_access_token == ""

    def test_settings_loads_whatsapp_phone_number_id(self, monkeypatch):
        """Settings loads WHATSAPP_PHONE_NUMBER_ID from env."""
        monkeypatch.setenv("GARMIN_EMAIL", "test@example.com")
        monkeypatch.setenv("GARMIN_PASSWORD", "secret")
        monkeypatch.setenv("SUPABASE_URL", "https://abc.supabase.co")
        monkeypatch.setenv("SUPABASE_KEY", "test-key")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
        monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "9876543210")

        from biointelligence.config import Settings

        settings = Settings(_env_file=None)
        assert settings.whatsapp_phone_number_id == "9876543210"

    def test_settings_whatsapp_phone_number_id_defaults_empty(self, monkeypatch):
        """Settings defaults whatsapp_phone_number_id to empty string when not set."""
        monkeypatch.setenv("GARMIN_EMAIL", "test@example.com")
        monkeypatch.setenv("GARMIN_PASSWORD", "secret")
        monkeypatch.setenv("SUPABASE_URL", "https://abc.supabase.co")
        monkeypatch.setenv("SUPABASE_KEY", "test-key")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")

        from biointelligence.config import Settings

        settings = Settings(_env_file=None)
        assert settings.whatsapp_phone_number_id == ""

    def test_settings_loads_whatsapp_recipient_phone(self, monkeypatch):
        """Settings loads WHATSAPP_RECIPIENT_PHONE from env."""
        monkeypatch.setenv("GARMIN_EMAIL", "test@example.com")
        monkeypatch.setenv("GARMIN_PASSWORD", "secret")
        monkeypatch.setenv("SUPABASE_URL", "https://abc.supabase.co")
        monkeypatch.setenv("SUPABASE_KEY", "test-key")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
        monkeypatch.setenv("WHATSAPP_RECIPIENT_PHONE", "+491701234567")

        from biointelligence.config import Settings

        settings = Settings(_env_file=None)
        assert settings.whatsapp_recipient_phone == "+491701234567"

    def test_settings_whatsapp_recipient_phone_defaults_empty(self, monkeypatch):
        """Settings defaults whatsapp_recipient_phone to empty string when not set."""
        monkeypatch.setenv("GARMIN_EMAIL", "test@example.com")
        monkeypatch.setenv("GARMIN_PASSWORD", "secret")
        monkeypatch.setenv("SUPABASE_URL", "https://abc.supabase.co")
        monkeypatch.setenv("SUPABASE_KEY", "test-key")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")

        from biointelligence.config import Settings

        settings = Settings(_env_file=None)
        assert settings.whatsapp_recipient_phone == ""


# ---------------------------------------------------------------------------
# send_whatsapp function
# ---------------------------------------------------------------------------


class TestSendWhatsApp:
    """Tests for send_whatsapp function."""

    @patch("biointelligence.delivery.whatsapp_sender.httpx")
    def test_calls_api_with_correct_url(self, mock_httpx, mock_settings):
        """send_whatsapp POSTs to https://graph.facebook.com/v21.0/{phone_number_id}/messages."""
        from biointelligence.delivery.whatsapp_sender import send_whatsapp

        mock_response = MagicMock()
        mock_response.json.return_value = {"messages": [{"id": "wamid.abc123"}]}
        mock_response.raise_for_status = MagicMock()
        mock_httpx.post.return_value = mock_response

        send_whatsapp(
            body_text="Hello World",
            target_date=datetime.date(2026, 3, 2),
            settings=mock_settings,
        )

        call_args = mock_httpx.post.call_args
        assert "graph.facebook.com/v21.0/1234567890/messages" in call_args[0][0]

    @patch("biointelligence.delivery.whatsapp_sender.httpx")
    def test_sends_correct_headers(self, mock_httpx, mock_settings):
        """send_whatsapp sends Authorization: Bearer {token} and Content-Type: application/json."""
        from biointelligence.delivery.whatsapp_sender import send_whatsapp

        mock_response = MagicMock()
        mock_response.json.return_value = {"messages": [{"id": "wamid.abc123"}]}
        mock_response.raise_for_status = MagicMock()
        mock_httpx.post.return_value = mock_response

        send_whatsapp(
            body_text="Hello World",
            target_date=datetime.date(2026, 3, 2),
            settings=mock_settings,
        )

        call_args = mock_httpx.post.call_args
        headers = call_args[1]["headers"]
        assert headers["Authorization"] == "Bearer wa_test_token_123"
        assert headers["Content-Type"] == "application/json"

    @patch("biointelligence.delivery.whatsapp_sender.httpx")
    def test_sends_template_payload(self, mock_httpx, mock_settings):
        """send_whatsapp sends correct template payload with messaging_product, to, type, template."""
        from biointelligence.delivery.whatsapp_sender import send_whatsapp

        mock_response = MagicMock()
        mock_response.json.return_value = {"messages": [{"id": "wamid.abc123"}]}
        mock_response.raise_for_status = MagicMock()
        mock_httpx.post.return_value = mock_response

        send_whatsapp(
            body_text="Test body text",
            target_date=datetime.date(2026, 3, 2),
            settings=mock_settings,
        )

        call_args = mock_httpx.post.call_args
        payload = call_args[1]["json"]
        assert payload["messaging_product"] == "whatsapp"
        assert payload["to"] == "+491701234567"
        assert payload["type"] == "template"
        assert payload["template"]["name"] == "daily_protocol"
        assert payload["template"]["language"]["code"] == "en"
        # Body parameter should contain the body_text
        components = payload["template"]["components"]
        body_component = [c for c in components if c["type"] == "body"][0]
        assert body_component["parameters"][0]["text"] == "Test body text"

    @patch("biointelligence.delivery.whatsapp_sender.httpx")
    def test_returns_success_with_message_id(self, mock_httpx, mock_settings):
        """On success: returns DeliveryResult(success=True, email_id=message_id_from_response)."""
        from biointelligence.delivery.whatsapp_sender import send_whatsapp

        mock_response = MagicMock()
        mock_response.json.return_value = {"messages": [{"id": "wamid.success456"}]}
        mock_response.raise_for_status = MagicMock()
        mock_httpx.post.return_value = mock_response

        result = send_whatsapp(
            body_text="Hello World",
            target_date=datetime.date(2026, 3, 2),
            settings=mock_settings,
        )

        assert result.success is True
        assert result.email_id == "wamid.success456"
        assert result.date == datetime.date(2026, 3, 2)
        assert result.error is None

    @patch("biointelligence.delivery.whatsapp_sender._send_via_whatsapp")
    def test_retries_on_transient_error(self, mock_send, mock_settings):
        """On transient failure (429, 5xx, TransportError): retries up to 3 times."""
        from biointelligence.delivery.whatsapp_sender import send_whatsapp

        # Simulate retries exhausted (RetryError wrapping a transient error)
        mock_send.side_effect = httpx.HTTPStatusError(
            "429 Too Many Requests",
            request=MagicMock(),
            response=MagicMock(status_code=429),
        )

        result = send_whatsapp(
            body_text="Hello",
            target_date=datetime.date(2026, 3, 2),
            settings=mock_settings,
        )

        # Should have tried and failed
        assert result.success is False
        assert result.error is not None

    @patch("biointelligence.delivery.whatsapp_sender.httpx.post")
    def test_permanent_failure_no_retry(self, mock_post, mock_settings):
        """On permanent failure (401, 400): fails immediately without retry."""
        from biointelligence.delivery.whatsapp_sender import (
            _send_via_whatsapp,
            send_whatsapp,
        )

        # Patch tenacity wait to 0
        original_wait = _send_via_whatsapp.retry.wait
        _send_via_whatsapp.retry.wait = lambda *args, **kwargs: 0

        try:
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "401 Unauthorized",
                request=MagicMock(),
                response=mock_response,
            )
            mock_post.return_value = mock_response

            result = send_whatsapp(
                body_text="Hello",
                target_date=datetime.date(2026, 3, 2),
                settings=mock_settings,
            )

            assert result.success is False
            assert result.error is not None
            # Should NOT have retried -- only 1 call
            assert mock_post.call_count == 1
        finally:
            _send_via_whatsapp.retry.wait = original_wait

    @patch("biointelligence.delivery.whatsapp_sender.httpx.post")
    def test_retries_exhausted_returns_failure(self, mock_post, mock_settings):
        """On all retries exhausted: returns DeliveryResult(success=False, error=...) -- does not raise."""
        from biointelligence.delivery.whatsapp_sender import (
            _send_via_whatsapp,
            send_whatsapp,
        )

        # Patch tenacity wait to 0
        original_wait = _send_via_whatsapp.retry.wait
        _send_via_whatsapp.retry.wait = lambda *args, **kwargs: 0

        try:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "500 Internal Server Error",
                request=MagicMock(),
                response=mock_response,
            )
            mock_post.return_value = mock_response

            result = send_whatsapp(
                body_text="Hello",
                target_date=datetime.date(2026, 3, 2),
                settings=mock_settings,
            )

            # Should return failure without raising
            assert result.success is False
            assert "500" in result.error or "Internal Server Error" in result.error
            assert result.email_id is None
            # Should have retried 3 times
            assert mock_post.call_count == 3
        finally:
            _send_via_whatsapp.retry.wait = original_wait


# ---------------------------------------------------------------------------
# _is_retryable classification
# ---------------------------------------------------------------------------


class TestIsRetryable:
    """Tests for _is_retryable retry classification."""

    def test_transport_error_is_retryable(self):
        """TransportError is retryable."""
        from biointelligence.delivery.whatsapp_sender import _is_retryable

        exc = httpx.TransportError("Connection reset")
        assert _is_retryable(exc) is True

    def test_429_is_retryable(self):
        """HTTPStatusError with 429 is retryable."""
        from biointelligence.delivery.whatsapp_sender import _is_retryable

        response = MagicMock()
        response.status_code = 429
        exc = httpx.HTTPStatusError("429", request=MagicMock(), response=response)
        assert _is_retryable(exc) is True

    def test_500_is_retryable(self):
        """HTTPStatusError with 500 is retryable."""
        from biointelligence.delivery.whatsapp_sender import _is_retryable

        response = MagicMock()
        response.status_code = 500
        exc = httpx.HTTPStatusError("500", request=MagicMock(), response=response)
        assert _is_retryable(exc) is True

    def test_502_is_retryable(self):
        """HTTPStatusError with 502 is retryable."""
        from biointelligence.delivery.whatsapp_sender import _is_retryable

        response = MagicMock()
        response.status_code = 502
        exc = httpx.HTTPStatusError("502", request=MagicMock(), response=response)
        assert _is_retryable(exc) is True

    def test_503_is_retryable(self):
        """HTTPStatusError with 503 is retryable."""
        from biointelligence.delivery.whatsapp_sender import _is_retryable

        response = MagicMock()
        response.status_code = 503
        exc = httpx.HTTPStatusError("503", request=MagicMock(), response=response)
        assert _is_retryable(exc) is True

    def test_504_is_retryable(self):
        """HTTPStatusError with 504 is retryable."""
        from biointelligence.delivery.whatsapp_sender import _is_retryable

        response = MagicMock()
        response.status_code = 504
        exc = httpx.HTTPStatusError("504", request=MagicMock(), response=response)
        assert _is_retryable(exc) is True

    def test_401_not_retryable(self):
        """HTTPStatusError with 401 is NOT retryable."""
        from biointelligence.delivery.whatsapp_sender import _is_retryable

        response = MagicMock()
        response.status_code = 401
        exc = httpx.HTTPStatusError("401", request=MagicMock(), response=response)
        assert _is_retryable(exc) is False

    def test_400_not_retryable(self):
        """HTTPStatusError with 400 is NOT retryable."""
        from biointelligence.delivery.whatsapp_sender import _is_retryable

        response = MagicMock()
        response.status_code = 400
        exc = httpx.HTTPStatusError("400", request=MagicMock(), response=response)
        assert _is_retryable(exc) is False

    def test_generic_exception_not_retryable(self):
        """Generic exceptions are NOT retryable."""
        from biointelligence.delivery.whatsapp_sender import _is_retryable

        exc = ValueError("some error")
        assert _is_retryable(exc) is False
