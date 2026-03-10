"""Tests for WhatsApp text renderer from DailyProtocol."""

from __future__ import annotations

import datetime

import pytest

from biointelligence.prompt.models import DailyProtocol


EXAMPLE_INSIGHT = (
    "BIOINTELLIGENCE — Mar 2, 2026\n\n"
    "Your body is in an extended recovery trough. Training Readiness hit "
    "11/100 on Feb 28, and the March 1 session loaded on incomplete recovery.\n\n"
    "1. HRV plateaued at 63ms — 7% below Monday, not recovering\n"
    "2. Body Battery stuck in the 50s — never above 55 despite two rest days\n"
    "3. Deep sleep dropped from 1h08m to 33m\n"
    "4. RHR stable at 47 — cardiac fatigue isn't the issue\n\n"
    "This points to autonomic fatigue without cardiovascular fatigue.\n\n"
    "*Recommendation:* No intensity until Body Battery >70 and HRV returns "
    "to 68-74ms. Zone 1 only (HR <150) if active."
)


@pytest.fixture()
def fake_protocol() -> DailyProtocol:
    """A populated DailyProtocol with narrative insight."""
    return DailyProtocol(
        date="2026-03-02",
        readiness_score=4,
        insight=EXAMPLE_INSIGHT,
        insight_html=EXAMPLE_INSIGHT,  # same for simplicity in tests
        data_quality_notes=None,
    )


class TestRenderWhatsApp:
    """Tests for the narrative WhatsApp renderer."""

    def test_returns_string(self, fake_protocol):
        from biointelligence.delivery.whatsapp_renderer import render_whatsapp

        result = render_whatsapp(fake_protocol, datetime.date(2026, 3, 2))
        assert isinstance(result, str)

    def test_contains_insight_text(self, fake_protocol):
        """Output contains the full insight narrative."""
        from biointelligence.delivery.whatsapp_renderer import render_whatsapp

        result = render_whatsapp(fake_protocol, datetime.date(2026, 3, 2))
        assert "BIOINTELLIGENCE" in result
        assert "recovery trough" in result
        assert "HRV plateaued at 63ms" in result
        assert "*Recommendation:*" in result

    def test_insight_is_the_body(self, fake_protocol):
        """The insight text IS the message body (not wrapped in extra structure)."""
        from biointelligence.delivery.whatsapp_renderer import render_whatsapp

        result = render_whatsapp(fake_protocol, datetime.date(2026, 3, 2))
        assert result.startswith("BIOINTELLIGENCE")

    def test_output_under_max_chars(self, fake_protocol):
        from biointelligence.delivery.whatsapp_renderer import render_whatsapp

        result = render_whatsapp(fake_protocol, datetime.date(2026, 3, 2))
        assert len(result) <= 32768

    def test_no_old_domain_sections(self, fake_protocol):
        """Old emoji section headers should not appear."""
        from biointelligence.delivery.whatsapp_renderer import render_whatsapp

        result = render_whatsapp(fake_protocol, datetime.date(2026, 3, 2))
        assert "\U0001f634 *Sleep*" not in result
        assert "\U0001f49a *Recovery*" not in result
        assert "\U0001f525 *Training*" not in result
        assert "\U0001f37d\ufe0f *Nutrition*" not in result
        assert "\U0001f48a *Supplementation*" not in result
        assert "*Why This Matters*" not in result


class TestRenderProfileNudge:
    """Tests for profile completeness nudge rendering."""

    def test_returns_empty_string_when_all_complete(self):
        """No nudge when there are no incomplete steps."""
        from biointelligence.delivery.whatsapp_renderer import _render_profile_nudge

        result = _render_profile_nudge([], "https://app.example.com")
        assert result == ""

    def test_returns_nudge_for_first_incomplete_step(self):
        """Returns nudge text with deep-link for the first incomplete step."""
        from biointelligence.delivery.whatsapp_renderer import _render_profile_nudge

        result = _render_profile_nudge([3, 5], "https://app.example.com")
        assert "metabolic & nutrition" in result.lower() or "metabolic" in result.lower()
        assert "https://app.example.com/onboarding/step-3" in result
        # Should NOT contain the second incomplete step
        assert "step-5" not in result

    def test_nudge_contains_separator(self):
        """Nudge starts with separator for visual distinction."""
        from biointelligence.delivery.whatsapp_renderer import _render_profile_nudge

        result = _render_profile_nudge([1], "https://app.example.com")
        assert "---" in result

    def test_nudge_maps_step_numbers_correctly(self):
        """Each step number maps to the correct human-readable name."""
        from biointelligence.delivery.whatsapp_renderer import _render_profile_nudge

        # Step 1: biological profile
        result = _render_profile_nudge([1], "https://app.example.com")
        assert "biological profile" in result.lower()

        # Step 4: training & sleep
        result = _render_profile_nudge([4], "https://app.example.com")
        assert "training" in result.lower()

    def test_render_whatsapp_includes_nudge_when_incomplete(self, fake_protocol):
        """render_whatsapp appends nudge when incomplete_steps is provided."""
        from biointelligence.delivery.whatsapp_renderer import render_whatsapp

        result = render_whatsapp(fake_protocol, datetime.date(2026, 3, 2), incomplete_steps=[2])
        assert "health" in result.lower()
        assert "step-2" in result

    def test_render_whatsapp_no_nudge_without_incomplete_steps(self, fake_protocol):
        """render_whatsapp does not append nudge when incomplete_steps is empty."""
        from biointelligence.delivery.whatsapp_renderer import render_whatsapp

        result = render_whatsapp(fake_protocol, datetime.date(2026, 3, 2), incomplete_steps=[])
        assert "step-" not in result

    def test_render_whatsapp_backwards_compatible(self, fake_protocol):
        """render_whatsapp works without incomplete_steps argument."""
        from biointelligence.delivery.whatsapp_renderer import render_whatsapp

        result = render_whatsapp(fake_protocol, datetime.date(2026, 3, 2))
        assert result.startswith("BIOINTELLIGENCE")
        assert "step-" not in result


class TestNudgeRateLimiting:
    """Tests for should_send_nudge and record_nudge_sent rate-limiting functions."""

    def test_should_send_nudge_true_when_never_sent(self):
        """should_send_nudge returns True when last_nudge_sent_at is None (never sent)."""
        from unittest.mock import MagicMock, patch

        from biointelligence.delivery.whatsapp_renderer import should_send_nudge

        mock_settings = MagicMock()
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [{"last_nudge_sent_at": None}]
        mock_client.table.return_value.select.return_value.limit.return_value.execute.return_value = mock_response

        with patch("biointelligence.storage.supabase.get_supabase_client", return_value=mock_client):
            assert should_send_nudge(mock_settings) is True

    def test_should_send_nudge_true_when_cooldown_elapsed(self):
        """should_send_nudge returns True when last_nudge_sent_at is 8 days ago."""
        from unittest.mock import MagicMock, patch

        from biointelligence.delivery.whatsapp_renderer import should_send_nudge

        mock_settings = MagicMock()
        mock_client = MagicMock()
        mock_response = MagicMock()
        eight_days_ago = (datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=8)).isoformat()
        mock_response.data = [{"last_nudge_sent_at": eight_days_ago}]
        mock_client.table.return_value.select.return_value.limit.return_value.execute.return_value = mock_response

        with patch("biointelligence.storage.supabase.get_supabase_client", return_value=mock_client):
            assert should_send_nudge(mock_settings) is True

    def test_should_send_nudge_false_within_cooldown(self):
        """should_send_nudge returns False when last_nudge_sent_at is 3 days ago."""
        from unittest.mock import MagicMock, patch

        from biointelligence.delivery.whatsapp_renderer import should_send_nudge

        mock_settings = MagicMock()
        mock_client = MagicMock()
        mock_response = MagicMock()
        three_days_ago = (datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=3)).isoformat()
        mock_response.data = [{"last_nudge_sent_at": three_days_ago}]
        mock_client.table.return_value.select.return_value.limit.return_value.execute.return_value = mock_response

        with patch("biointelligence.storage.supabase.get_supabase_client", return_value=mock_client):
            assert should_send_nudge(mock_settings) is False

    def test_should_send_nudge_false_at_exactly_7_days(self):
        """should_send_nudge returns False when last_nudge_sent_at is exactly 7 days ago (boundary)."""
        from unittest.mock import MagicMock, patch

        import biointelligence.delivery.whatsapp_renderer as wr

        fixed_now = datetime.datetime(2026, 3, 5, 12, 0, 0, tzinfo=datetime.timezone.utc)
        exactly_7_days = (fixed_now - datetime.timedelta(days=7)).isoformat()

        mock_settings = MagicMock()
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [{"last_nudge_sent_at": exactly_7_days}]
        mock_client.table.return_value.select.return_value.limit.return_value.execute.return_value = mock_response

        original_datetime = wr.datetime

        class FrozenDatetime(original_datetime):
            @classmethod
            def now(cls, tz=None):
                return fixed_now

        with (
            patch("biointelligence.storage.supabase.get_supabase_client", return_value=mock_client),
            patch.object(wr, "datetime", FrozenDatetime),
        ):
            assert wr.should_send_nudge(mock_settings) is False

    def test_should_send_nudge_true_at_7_days_plus_1_second(self):
        """should_send_nudge returns True when last_nudge_sent_at is 7 days + 1 second ago."""
        from unittest.mock import MagicMock, patch

        import biointelligence.delivery.whatsapp_renderer as wr

        fixed_now = datetime.datetime(2026, 3, 5, 12, 0, 0, tzinfo=datetime.timezone.utc)
        seven_days_plus = (fixed_now - datetime.timedelta(days=7, seconds=1)).isoformat()

        mock_settings = MagicMock()
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [{"last_nudge_sent_at": seven_days_plus}]
        mock_client.table.return_value.select.return_value.limit.return_value.execute.return_value = mock_response

        original_datetime = wr.datetime

        class FrozenDatetime(original_datetime):
            @classmethod
            def now(cls, tz=None):
                return fixed_now

        with (
            patch("biointelligence.storage.supabase.get_supabase_client", return_value=mock_client),
            patch.object(wr, "datetime", FrozenDatetime),
        ):
            assert wr.should_send_nudge(mock_settings) is True

    def test_should_send_nudge_false_on_exception(self):
        """should_send_nudge returns False on Supabase query exception (safe default)."""
        from unittest.mock import MagicMock, patch

        from biointelligence.delivery.whatsapp_renderer import should_send_nudge

        mock_settings = MagicMock()

        with patch("biointelligence.storage.supabase.get_supabase_client", side_effect=Exception("DB error")):
            assert should_send_nudge(mock_settings) is False

    def test_record_nudge_sent_updates_timestamp(self):
        """record_nudge_sent updates last_nudge_sent_at on the onboarding_profiles row."""
        from unittest.mock import MagicMock, patch

        from biointelligence.delivery.whatsapp_renderer import record_nudge_sent

        mock_settings = MagicMock()
        mock_client = MagicMock()

        with patch("biointelligence.storage.supabase.get_supabase_client", return_value=mock_client):
            record_nudge_sent(mock_settings)

        mock_client.table.assert_called_once_with("onboarding_profiles")
        mock_client.table.return_value.update.assert_called_once()
        update_arg = mock_client.table.return_value.update.call_args[0][0]
        assert "last_nudge_sent_at" in update_arg
        mock_client.table.return_value.update.return_value.gte.assert_called_once()
        mock_client.table.return_value.update.return_value.gte.return_value.execute.assert_called_once()

    def test_record_nudge_sent_no_raise_on_exception(self):
        """record_nudge_sent does not raise on Supabase write exception (best-effort)."""
        from unittest.mock import MagicMock, patch

        from biointelligence.delivery.whatsapp_renderer import record_nudge_sent

        mock_settings = MagicMock()

        with patch("biointelligence.storage.supabase.get_supabase_client", side_effect=Exception("DB error")):
            # Should not raise
            record_nudge_sent(mock_settings)


class TestRenderWhatsAppCharLimit:
    """Tests for the 32,768 character limit guard."""

    def test_output_under_max_chars(self, fake_protocol):
        """Output does not exceed 32,768 characters for a normal protocol."""
        from biointelligence.delivery.whatsapp_renderer import render_whatsapp

        result = render_whatsapp(fake_protocol, datetime.date(2026, 3, 2))
        assert len(result) <= 32768
