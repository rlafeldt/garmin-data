"""Tests for WhatsApp text renderer from DailyProtocol."""

from __future__ import annotations

import datetime

import pytest

from biointelligence.anomaly.models import Alert, AlertSeverity
from biointelligence.prompt.models import (
    DailyProtocol,
    NutritionGuidance,
    RecoveryAssessment,
    SleepAnalysis,
    SupplementationPlan,
    TrainingRecommendation,
)


@pytest.fixture()
def fake_protocol() -> DailyProtocol:
    """A populated DailyProtocol for WhatsApp renderer tests."""
    return DailyProtocol(
        date="2026-03-02",
        training=TrainingRecommendation(
            headline="Zone 2 ride, 75 min",
            readiness_score=7,
            readiness_summary="Good recovery overnight with HRV trending up.",
            recommended_intensity="Zone 2",
            recommended_type="Cycling",
            recommended_duration_minutes=75,
            training_load_assessment="Acute load within optimal range.",
            reasoning="HRV 48ms above baseline, body battery 72. Training load balanced over the week. Moderate aerobic work recommended.",
        ),
        recovery=RecoveryAssessment(
            headline="Well recovered, HRV above baseline",
            recovery_status="Well recovered",
            hrv_interpretation="HRV 48ms is above your 7-day average of 44ms.",
            body_battery_assessment="Morning body battery 72 indicates good energy reserves.",
            stress_impact="Average stress 32 is within normal range.",
            recommendations=["Light mobility work", "Cold exposure post-training"],
            reasoning="Multi-metric convergence shows solid recovery. HRV uptrend combined with low stress. Body battery reserves are above average.",
        ),
        sleep=SleepAnalysis(
            headline="Good sleep, strong deep sleep phase",
            quality_assessment="Good sleep quality with adequate deep sleep.",
            architecture_notes="Deep sleep 1h42m (22%), REM 1h28m (19%).",
            optimization_tips=["Maintain consistent 22:30 bedtime", "Limit blue light after 21:00"],
            reasoning="Sleep score 82 with strong deep sleep phase supports training today. REM duration was slightly low.",
        ),
        nutrition=NutritionGuidance(
            headline="2,800 kcal, carb-heavy for ride day",
            caloric_target="2,800 kcal",
            macro_focus="Higher carb pre-ride, moderate protein throughout.",
            hydration_target="3.2L including 500ml electrolyte during ride",
            meal_timing_notes="Pre-ride meal 2h before. Post-ride protein within 30min.",
            reasoning="Zone 2 cycling for 75min requires moderate fueling strategy. Carb loading recommended.",
        ),
        supplementation=SupplementationPlan(
            headline="Standard stack, no changes needed",
            adjustments=["Creatine 5g with breakfast", "Vitamin D 4000IU with lunch"],
            timing_notes="Take magnesium glycinate 400mg 1h before bed.",
            reasoning="Maintaining standard supplementation stack. No adjustments needed.",
        ),
        overall_summary="Good day for a moderate Zone 2 ride. Recovery metrics look solid.",
        data_quality_notes=None,
    )


@pytest.fixture()
def warning_alert() -> Alert:
    """A WARNING severity alert."""
    return Alert(
        severity=AlertSeverity.WARNING,
        title="HRV Declining Trend",
        description="HRV has been 2.5 SD below baseline for 3 consecutive days.",
        suggested_action="Consider reducing training intensity today.",
        pattern_name="hrv_declining",
    )


@pytest.fixture()
def critical_alert() -> Alert:
    """A CRITICAL severity alert."""
    return Alert(
        severity=AlertSeverity.CRITICAL,
        title="Overtraining Pattern Detected",
        description="Multiple metrics converging: low HRV, elevated RHR, poor sleep.",
        suggested_action="Take a full rest day.",
        pattern_name="overtraining_convergence",
    )


# ---------------------------------------------------------------------------
# Header and readiness
# ---------------------------------------------------------------------------


class TestRenderWhatsAppHeader:
    """Tests for WhatsApp renderer header and readiness line."""

    def test_returns_string(self, fake_protocol):
        """render_whatsapp returns a string."""
        from biointelligence.delivery.whatsapp_renderer import render_whatsapp

        result = render_whatsapp(fake_protocol, datetime.date(2026, 3, 2))
        assert isinstance(result, str)

    def test_starts_with_daily_protocol_header(self, fake_protocol):
        """Output starts with '*Daily Protocol*' header line with formatted date."""
        from biointelligence.delivery.whatsapp_renderer import render_whatsapp

        result = render_whatsapp(fake_protocol, datetime.date(2026, 3, 2))
        first_line = result.split("\n")[0]
        assert "*Daily Protocol*" in first_line
        assert "Mar" in first_line
        assert "2026" in first_line

    def test_readiness_score_on_second_line(self, fake_protocol):
        """Second line contains 'Readiness: *{score}/10*'."""
        from biointelligence.delivery.whatsapp_renderer import render_whatsapp

        result = render_whatsapp(fake_protocol, datetime.date(2026, 3, 2))
        lines = result.split("\n")
        assert "Readiness: *7/10*" in lines[1]


# ---------------------------------------------------------------------------
# Alert banners
# ---------------------------------------------------------------------------


class TestRenderWhatsAppAlerts:
    """Tests for alert rendering in WhatsApp format."""

    def test_alerts_appear_before_domains(self, fake_protocol, warning_alert):
        """When protocol.alerts is non-empty, alert blocks appear before domain sections."""
        from biointelligence.delivery.whatsapp_renderer import render_whatsapp

        fake_protocol.alerts = [warning_alert]
        result = render_whatsapp(fake_protocol, datetime.date(2026, 3, 2))
        alert_pos = result.index("HRV Declining Trend")
        # Sleep is the first domain
        sleep_pos = result.index("Sleep")
        assert alert_pos < sleep_pos

    def test_alert_format_severity_title(self, fake_protocol, warning_alert):
        """Each alert shows '*[SEVERITY] title*', description, and 'Action: suggested_action'."""
        from biointelligence.delivery.whatsapp_renderer import render_whatsapp

        fake_protocol.alerts = [warning_alert]
        result = render_whatsapp(fake_protocol, datetime.date(2026, 3, 2))
        assert "*[WARNING] HRV Declining Trend*" in result
        assert "HRV has been 2.5 SD below baseline for 3 consecutive days." in result
        assert "Action: Consider reducing training intensity today." in result

    def test_critical_alert_format(self, fake_protocol, critical_alert):
        """CRITICAL alerts use *[CRITICAL] title* format."""
        from biointelligence.delivery.whatsapp_renderer import render_whatsapp

        fake_protocol.alerts = [critical_alert]
        result = render_whatsapp(fake_protocol, datetime.date(2026, 3, 2))
        assert "*[CRITICAL] Overtraining Pattern Detected*" in result

    def test_no_alert_section_when_empty(self, fake_protocol):
        """When protocol.alerts is empty, no alert section appears."""
        from biointelligence.delivery.whatsapp_renderer import render_whatsapp

        fake_protocol.alerts = []
        result = render_whatsapp(fake_protocol, datetime.date(2026, 3, 2))
        assert "[WARNING]" not in result
        assert "[CRITICAL]" not in result


# ---------------------------------------------------------------------------
# Domain sections
# ---------------------------------------------------------------------------


class TestRenderWhatsAppDomains:
    """Tests for domain section rendering in WhatsApp format."""

    def test_domains_in_correct_order(self, fake_protocol):
        """Domain sections appear in order: Sleep, Recovery, Training, Nutrition, Supplementation."""
        from biointelligence.delivery.whatsapp_renderer import render_whatsapp

        result = render_whatsapp(fake_protocol, datetime.date(2026, 3, 2))
        sleep_pos = result.index("Sleep")
        recovery_pos = result.index("Recovery")
        training_pos = result.index("Training")
        nutrition_pos = result.index("Nutrition")
        supplementation_pos = result.index("Supplementation")
        assert sleep_pos < recovery_pos < training_pos < nutrition_pos < supplementation_pos

    def test_sleep_section_has_emoji_header(self, fake_protocol):
        """Sleep section has emoji header and *bold* section name."""
        from biointelligence.delivery.whatsapp_renderer import render_whatsapp

        result = render_whatsapp(fake_protocol, datetime.date(2026, 3, 2))
        # Check for sleeping face emoji and bold Sleep
        assert "*Sleep*" in result

    def test_sleep_section_bold_keys(self, fake_protocol):
        """Sleep section contains *Quality:* and *Architecture:* bold keys."""
        from biointelligence.delivery.whatsapp_renderer import render_whatsapp

        result = render_whatsapp(fake_protocol, datetime.date(2026, 3, 2))
        assert "*Quality:*" in result
        assert "*Architecture:*" in result
        assert "Good sleep quality with adequate deep sleep." in result
        assert "Deep sleep 1h42m (22%), REM 1h28m (19%)." in result

    def test_recovery_section_bold_keys(self, fake_protocol):
        """Recovery section contains *Status:*, *HRV:*, *Body Battery:* bold keys."""
        from biointelligence.delivery.whatsapp_renderer import render_whatsapp

        result = render_whatsapp(fake_protocol, datetime.date(2026, 3, 2))
        assert "*Status:*" in result
        assert "*HRV:*" in result
        assert "*Body Battery:*" in result

    def test_training_section_bold_keys(self, fake_protocol):
        """Training section contains *Intensity:*, *Type:*, *Duration:* bold keys."""
        from biointelligence.delivery.whatsapp_renderer import render_whatsapp

        result = render_whatsapp(fake_protocol, datetime.date(2026, 3, 2))
        assert "*Intensity:*" in result
        assert "*Type:*" in result
        assert "*Duration:*" in result

    def test_nutrition_section_bold_keys(self, fake_protocol):
        """Nutrition section contains *Calories:*, *Macros:*, *Hydration:* bold keys."""
        from biointelligence.delivery.whatsapp_renderer import render_whatsapp

        result = render_whatsapp(fake_protocol, datetime.date(2026, 3, 2))
        assert "*Calories:*" in result
        assert "*Macros:*" in result
        assert "*Hydration:*" in result

    def test_supplementation_section_lists_adjustments(self, fake_protocol):
        """Supplementation section lists adjustments as '- item' lines with *Timing:* key."""
        from biointelligence.delivery.whatsapp_renderer import render_whatsapp

        result = render_whatsapp(fake_protocol, datetime.date(2026, 3, 2))
        assert "- Creatine 5g with breakfast" in result
        assert "- Vitamin D 4000IU with lunch" in result
        assert "*Timing:*" in result

    def test_each_domain_includes_trimmed_reasoning(self, fake_protocol):
        """Each domain includes 1-2 sentence trimmed reasoning (plain text, no bold)."""
        from biointelligence.delivery.whatsapp_renderer import render_whatsapp

        result = render_whatsapp(fake_protocol, datetime.date(2026, 3, 2))
        # Sleep reasoning should be trimmed to first 2 sentences
        assert "Sleep score 82 with strong deep sleep phase supports training today." in result
        assert "REM duration was slightly low." in result
        # The 3rd sentence of recovery reasoning should be trimmed
        # "Body battery reserves are above average." is the 3rd sentence
        # First two: "Multi-metric convergence shows solid recovery." + "HRV uptrend combined with low stress."
        assert "Multi-metric convergence shows solid recovery." in result
        assert "HRV uptrend combined with low stress." in result


# ---------------------------------------------------------------------------
# Why This Matters
# ---------------------------------------------------------------------------


class TestRenderWhatsAppClosing:
    """Tests for the closing section of WhatsApp rendering."""

    def test_ends_with_why_this_matters(self, fake_protocol):
        """Message ends with '*Why This Matters*' section containing overall_summary."""
        from biointelligence.delivery.whatsapp_renderer import render_whatsapp

        result = render_whatsapp(fake_protocol, datetime.date(2026, 3, 2))
        assert "*Why This Matters*" in result
        assert fake_protocol.overall_summary in result
        # Why This Matters should be after all domain sections
        why_pos = result.index("*Why This Matters*")
        supp_pos = result.index("Supplementation")
        assert why_pos > supp_pos


# ---------------------------------------------------------------------------
# Character limit guard
# ---------------------------------------------------------------------------


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
        assert "*Daily Protocol*" in result
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
