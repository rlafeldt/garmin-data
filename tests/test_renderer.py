"""Tests for email rendering: Settings extension, delivery lazy imports, HTML and plain-text renderers."""

from __future__ import annotations

import datetime

import pytest

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
    """A populated DailyProtocol for renderer tests."""
    return DailyProtocol(
        date="2026-03-02",
        training=TrainingRecommendation(
            readiness_score=7,
            readiness_summary="Good recovery overnight with HRV trending up.",
            recommended_intensity="Zone 2",
            recommended_type="Cycling",
            recommended_duration_minutes=75,
            training_load_assessment="Acute load within optimal range.",
            reasoning="HRV 48ms above baseline, body battery 72. Training load balanced.",
        ),
        recovery=RecoveryAssessment(
            recovery_status="Well recovered",
            hrv_interpretation="HRV 48ms is above your 7-day average of 44ms.",
            body_battery_assessment="Morning body battery 72 indicates good energy reserves.",
            stress_impact="Average stress 32 is within normal range.",
            recommendations=["Light mobility work", "Cold exposure post-training"],
            reasoning="Multi-metric convergence shows solid recovery.",
        ),
        sleep=SleepAnalysis(
            quality_assessment="Good sleep quality with adequate deep sleep.",
            architecture_notes="Deep sleep 1h42m (22%), REM 1h28m (19%).",
            optimization_tips=["Maintain consistent 22:30 bedtime", "Limit blue light after 21:00"],
            reasoning="Sleep score 82 with strong deep sleep phase supports training today.",
        ),
        nutrition=NutritionGuidance(
            caloric_target="2,800 kcal",
            macro_focus="Higher carb pre-ride, moderate protein throughout.",
            hydration_target="3.2L including 500ml electrolyte during ride",
            meal_timing_notes="Pre-ride meal 2h before. Post-ride protein within 30min.",
            reasoning="Zone 2 cycling for 75min requires moderate fueling strategy.",
        ),
        supplementation=SupplementationPlan(
            adjustments=["Creatine 5g with breakfast", "Vitamin D 4000IU with lunch"],
            timing_notes="Take magnesium glycinate 400mg 1h before bed.",
            reasoning="Maintaining standard supplementation stack.",
        ),
        overall_summary="Good day for a moderate Zone 2 ride. Recovery metrics look solid.",
        data_quality_notes=None,
    )


# ---------------------------------------------------------------------------
# Task 1: Settings extension tests
# ---------------------------------------------------------------------------


class TestSettingsResendFields:
    """Tests for Settings with Resend configuration fields."""

    def test_settings_loads_resend_api_key(self, monkeypatch):
        """Settings loads resend_api_key from RESEND_API_KEY env var (defaults to empty string)."""
        monkeypatch.setenv("GARMIN_EMAIL", "test@example.com")
        monkeypatch.setenv("GARMIN_PASSWORD", "secret")
        monkeypatch.setenv("SUPABASE_URL", "https://abc.supabase.co")
        monkeypatch.setenv("SUPABASE_KEY", "test-key")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
        monkeypatch.setenv("RESEND_API_KEY", "re_test_123")

        from biointelligence.config import Settings

        settings = Settings(_env_file=None)
        assert settings.resend_api_key == "re_test_123"

    def test_settings_resend_api_key_defaults_empty(self, monkeypatch):
        """Settings defaults resend_api_key to empty string when not set."""
        monkeypatch.setenv("GARMIN_EMAIL", "test@example.com")
        monkeypatch.setenv("GARMIN_PASSWORD", "secret")
        monkeypatch.setenv("SUPABASE_URL", "https://abc.supabase.co")
        monkeypatch.setenv("SUPABASE_KEY", "test-key")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")

        from biointelligence.config import Settings

        settings = Settings(_env_file=None)
        assert settings.resend_api_key == ""

    def test_settings_loads_sender_email(self, monkeypatch):
        """Settings loads sender_email from SENDER_EMAIL env var (defaults to empty string)."""
        monkeypatch.setenv("GARMIN_EMAIL", "test@example.com")
        monkeypatch.setenv("GARMIN_PASSWORD", "secret")
        monkeypatch.setenv("SUPABASE_URL", "https://abc.supabase.co")
        monkeypatch.setenv("SUPABASE_KEY", "test-key")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
        monkeypatch.setenv("SENDER_EMAIL", "protocol@example.com")

        from biointelligence.config import Settings

        settings = Settings(_env_file=None)
        assert settings.sender_email == "protocol@example.com"

    def test_settings_sender_email_defaults_empty(self, monkeypatch):
        """Settings defaults sender_email to empty string when not set."""
        monkeypatch.setenv("GARMIN_EMAIL", "test@example.com")
        monkeypatch.setenv("GARMIN_PASSWORD", "secret")
        monkeypatch.setenv("SUPABASE_URL", "https://abc.supabase.co")
        monkeypatch.setenv("SUPABASE_KEY", "test-key")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")

        from biointelligence.config import Settings

        settings = Settings(_env_file=None)
        assert settings.sender_email == ""

    def test_settings_loads_recipient_email(self, monkeypatch):
        """Settings loads recipient_email from RECIPIENT_EMAIL env var (defaults to empty string)."""
        monkeypatch.setenv("GARMIN_EMAIL", "test@example.com")
        monkeypatch.setenv("GARMIN_PASSWORD", "secret")
        monkeypatch.setenv("SUPABASE_URL", "https://abc.supabase.co")
        monkeypatch.setenv("SUPABASE_KEY", "test-key")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
        monkeypatch.setenv("RECIPIENT_EMAIL", "user@example.com")

        from biointelligence.config import Settings

        settings = Settings(_env_file=None)
        assert settings.recipient_email == "user@example.com"

    def test_settings_recipient_email_defaults_empty(self, monkeypatch):
        """Settings defaults recipient_email to empty string when not set."""
        monkeypatch.setenv("GARMIN_EMAIL", "test@example.com")
        monkeypatch.setenv("GARMIN_PASSWORD", "secret")
        monkeypatch.setenv("SUPABASE_URL", "https://abc.supabase.co")
        monkeypatch.setenv("SUPABASE_KEY", "test-key")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")

        from biointelligence.config import Settings

        settings = Settings(_env_file=None)
        assert settings.recipient_email == ""


class TestDeliveryLazyImports:
    """Tests for delivery/__init__.py lazy import pattern."""

    def test_exports_render_html(self):
        """delivery/__init__.py exports render_html via lazy import."""
        from biointelligence.delivery import render_html

        assert callable(render_html)

    def test_exports_render_text(self):
        """delivery/__init__.py exports render_text via lazy import."""
        from biointelligence.delivery import render_text

        assert callable(render_text)

    def test_raises_attribute_error_for_unknown(self):
        """delivery/__init__.py raises AttributeError for unknown attributes."""
        import biointelligence.delivery

        with pytest.raises(AttributeError):
            _ = biointelligence.delivery.nonexistent_attribute
