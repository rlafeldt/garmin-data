"""Tests for configuration and Garmin authentication client."""

import os
from unittest.mock import MagicMock, patch

import pytest
from garminconnect import GarminConnectAuthenticationError
from pydantic import ValidationError

from biointelligence.config import Settings
from biointelligence.garmin.client import get_authenticated_client


class TestSettings:
    """Tests for Settings configuration loading."""

    def test_settings_loads_from_env_vars(self, monkeypatch):
        """Settings loads all expected fields from environment variables."""
        monkeypatch.setenv("GARMIN_EMAIL", "test@example.com")
        monkeypatch.setenv("GARMIN_PASSWORD", "secret123")
        monkeypatch.setenv("SUPABASE_URL", "https://abc.supabase.co")
        monkeypatch.setenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiJ9.test")
        monkeypatch.setenv("GARMIN_TOKEN_DIR", "/tmp/tokens")
        monkeypatch.setenv("TARGET_TIMEZONE", "America/New_York")
        monkeypatch.setenv("LOG_JSON", "true")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

        settings = Settings(_env_file=None)

        assert settings.garmin_email == "test@example.com"
        assert settings.garmin_password == "secret123"
        assert settings.supabase_url == "https://abc.supabase.co"
        assert settings.supabase_key == "eyJhbGciOiJIUzI1NiJ9.test"
        assert settings.garmin_token_dir == "/tmp/tokens"
        assert settings.target_timezone == "America/New_York"
        assert settings.log_json is True

    def test_settings_has_defaults(self, monkeypatch):
        """Settings provides sensible defaults for optional fields."""
        monkeypatch.setenv("GARMIN_EMAIL", "test@example.com")
        monkeypatch.setenv("GARMIN_PASSWORD", "secret123")
        monkeypatch.setenv("SUPABASE_URL", "https://abc.supabase.co")
        monkeypatch.setenv("SUPABASE_KEY", "key123")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        monkeypatch.delenv("TARGET_TIMEZONE", raising=False)
        monkeypatch.delenv("GARMIN_TOKEN_DIR", raising=False)
        monkeypatch.delenv("LOG_JSON", raising=False)

        settings = Settings(_env_file=None)

        assert settings.garmin_token_dir == "~/.garminconnect"
        assert settings.target_timezone == "Europe/Berlin"
        assert settings.log_json is False

    def test_settings_validates_required_fields(self, monkeypatch):
        """Settings raises validation error when required fields are missing."""
        # Clear all relevant env vars
        monkeypatch.delenv("GARMIN_EMAIL", raising=False)
        monkeypatch.delenv("GARMIN_PASSWORD", raising=False)
        monkeypatch.delenv("SUPABASE_URL", raising=False)
        monkeypatch.delenv("SUPABASE_KEY", raising=False)

        with pytest.raises(ValidationError):
            Settings(_env_file=None)


class TestGetAuthenticatedClient:
    """Tests for Garmin authentication client."""

    @pytest.fixture()
    def settings(self, monkeypatch):
        """Create a Settings instance with test values."""
        monkeypatch.setenv("GARMIN_EMAIL", "test@garmin.com")
        monkeypatch.setenv("GARMIN_PASSWORD", "testpass")
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_KEY", "testkey")
        monkeypatch.setenv("GARMIN_TOKEN_DIR", "/tmp/test-garmin-tokens")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        return Settings()

    @patch("biointelligence.garmin.client.Garmin")
    def test_loads_tokens_from_existing_dir(self, mock_garmin_class, settings, tmp_path):
        """Client loads persisted tokens when token directory exists."""
        settings.garmin_token_dir = str(tmp_path)
        mock_client = MagicMock()
        mock_garmin_class.return_value = mock_client

        result = get_authenticated_client(settings)

        mock_garmin_class.assert_called_once_with()
        mock_client.login.assert_called_once_with(str(tmp_path))
        assert result is mock_client

    @patch("biointelligence.garmin.client.Garmin")
    def test_falls_back_to_email_password_login(self, mock_garmin_class, settings, tmp_path):
        """Client uses email/password when no token directory exists."""
        nonexistent = str(tmp_path / "nonexistent")
        settings.garmin_token_dir = nonexistent
        mock_client = MagicMock()
        mock_garmin_class.return_value = mock_client

        result = get_authenticated_client(settings)

        mock_garmin_class.assert_called_once_with("test@garmin.com", "testpass")
        mock_client.login.assert_called_once_with()
        assert result is mock_client

    @patch("biointelligence.garmin.client.Garmin")
    def test_saves_tokens_after_login(self, mock_garmin_class, settings, tmp_path):
        """After email/password login, tokens are saved to disk with secure permissions."""
        token_dir = str(tmp_path / "new-tokens")
        settings.garmin_token_dir = token_dir
        mock_client = MagicMock()
        mock_garmin_class.return_value = mock_client

        get_authenticated_client(settings)

        mock_client.garth.dump.assert_called_once_with(token_dir)
        # Verify directory was created with 0o700 permissions
        assert os.path.isdir(token_dir)
        assert oct(os.stat(token_dir).st_mode)[-3:] == "700"

    @patch("biointelligence.garmin.client.Garmin")
    def test_raises_on_invalid_credentials(self, mock_garmin_class, settings, tmp_path):
        """GarminConnectAuthenticationError is raised cleanly for invalid credentials."""
        settings.garmin_token_dir = str(tmp_path / "nonexistent")
        mock_client = MagicMock()
        mock_garmin_class.return_value = mock_client
        mock_client.login.side_effect = GarminConnectAuthenticationError("Invalid credentials")

        with pytest.raises(GarminConnectAuthenticationError, match="Invalid credentials"):
            get_authenticated_client(settings)


class TestSupabaseTokenAuth:
    """Tests for Supabase-backed token authentication (CI mode)."""

    @pytest.fixture()
    def settings(self, monkeypatch):
        """Create a Settings instance with test values."""
        monkeypatch.setenv("GARMIN_EMAIL", "test@garmin.com")
        monkeypatch.setenv("GARMIN_PASSWORD", "testpass")
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_KEY", "testkey")
        monkeypatch.setenv("GARMIN_TOKEN_DIR", "/tmp/test-garmin-tokens")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        return Settings(_env_file=None)

    @patch("biointelligence.garmin.client.save_tokens_to_supabase")
    @patch("biointelligence.garmin.client.load_tokens_from_supabase")
    @patch("biointelligence.garmin.client.Garmin")
    def test_loads_tokens_from_supabase(
        self, mock_garmin_class, mock_load, mock_save, settings
    ):
        """When supabase_client provided and tokens exist, uses token string login."""
        fake_token = "x" * 600  # base64 token string > 512 chars
        mock_load.return_value = fake_token
        mock_client = MagicMock()
        mock_garmin_class.return_value = mock_client
        mock_supabase = MagicMock()

        result = get_authenticated_client(settings, supabase_client=mock_supabase)

        mock_load.assert_called_once_with(mock_supabase)
        mock_garmin_class.assert_called_once_with()
        mock_client.login.assert_called_once_with(fake_token)
        assert result is mock_client

    @patch("biointelligence.garmin.client.save_tokens_to_supabase")
    @patch("biointelligence.garmin.client.load_tokens_from_supabase")
    @patch("biointelligence.garmin.client.Garmin")
    def test_saves_tokens_after_supabase_auth(
        self, mock_garmin_class, mock_load, mock_save, settings
    ):
        """After Supabase token login, refreshed tokens are saved back."""
        mock_load.return_value = "y" * 600
        mock_client = MagicMock()
        mock_garmin_class.return_value = mock_client
        mock_supabase = MagicMock()

        get_authenticated_client(settings, supabase_client=mock_supabase)

        mock_save.assert_called_once_with(mock_supabase, mock_client)

    @patch("biointelligence.garmin.client.save_tokens_to_supabase")
    @patch("biointelligence.garmin.client.load_tokens_from_supabase")
    @patch("biointelligence.garmin.client.Garmin")
    def test_falls_back_to_email_when_no_supabase_tokens(
        self, mock_garmin_class, mock_load, mock_save, settings
    ):
        """When supabase_client provided but no tokens, falls back to email/password."""
        mock_load.return_value = None
        mock_client = MagicMock()
        mock_garmin_class.return_value = mock_client
        mock_supabase = MagicMock()

        result = get_authenticated_client(settings, supabase_client=mock_supabase)

        mock_garmin_class.assert_called_once_with(
            settings.garmin_email, settings.garmin_password
        )
        mock_client.login.assert_called_once_with()
        assert result is mock_client

    @patch("biointelligence.garmin.client.save_tokens_to_supabase")
    @patch("biointelligence.garmin.client.load_tokens_from_supabase")
    @patch("biointelligence.garmin.client.Garmin")
    def test_saves_tokens_to_supabase_after_email_login(
        self, mock_garmin_class, mock_load, mock_save, settings
    ):
        """After email/password fallback in CI mode, saves tokens to Supabase."""
        mock_load.return_value = None
        mock_client = MagicMock()
        mock_garmin_class.return_value = mock_client
        mock_supabase = MagicMock()

        get_authenticated_client(settings, supabase_client=mock_supabase)

        mock_save.assert_called_once_with(mock_supabase, mock_client)

    @patch("biointelligence.garmin.client.Garmin")
    def test_none_supabase_client_uses_filesystem(
        self, mock_garmin_class, settings, tmp_path
    ):
        """When supabase_client is None, existing filesystem behavior is preserved."""
        settings.garmin_token_dir = str(tmp_path)
        mock_client = MagicMock()
        mock_garmin_class.return_value = mock_client

        result = get_authenticated_client(settings, supabase_client=None)

        mock_garmin_class.assert_called_once_with()
        mock_client.login.assert_called_once_with(str(tmp_path))
        assert result is mock_client
