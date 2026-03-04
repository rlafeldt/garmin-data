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
            headline="Zone 2 ride, 75 min — readiness is solid",
            readiness_score=7,
            readiness_summary="Good recovery overnight with HRV trending up.",
            recommended_intensity="Zone 2",
            recommended_type="Cycling",
            recommended_duration_minutes=75,
            training_load_assessment="Acute load within optimal range.",
            reasoning="HRV 48ms above baseline, body battery 72. Training load balanced.",
        ),
        recovery=RecoveryAssessment(
            headline="Well recovered, HRV above baseline",
            recovery_status="Well recovered",
            hrv_interpretation="HRV 48ms is above your 7-day average of 44ms.",
            body_battery_assessment="Morning body battery 72 indicates good energy reserves.",
            stress_impact="Average stress 32 is within normal range.",
            recommendations=["Light mobility work", "Cold exposure post-training"],
            reasoning="Multi-metric convergence shows solid recovery.",
        ),
        sleep=SleepAnalysis(
            headline="Good sleep, strong deep sleep phase",
            quality_assessment="Good sleep quality with adequate deep sleep.",
            architecture_notes="Deep sleep 1h42m (22%), REM 1h28m (19%).",
            optimization_tips=["Maintain consistent 22:30 bedtime", "Limit blue light after 21:00"],
            reasoning="Sleep score 82 with strong deep sleep phase supports training today.",
        ),
        nutrition=NutritionGuidance(
            headline="2,800 kcal, carb-heavy for ride day",
            caloric_target="2,800 kcal",
            macro_focus="Higher carb pre-ride, moderate protein throughout.",
            hydration_target="3.2L including 500ml electrolyte during ride",
            meal_timing_notes="Pre-ride meal 2h before. Post-ride protein within 30min.",
            reasoning="Zone 2 cycling for 75min requires moderate fueling strategy.",
        ),
        supplementation=SupplementationPlan(
            headline="Standard stack, no changes needed",
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


# ---------------------------------------------------------------------------
# Task 2: HTML and plain-text renderer tests
# ---------------------------------------------------------------------------


class TestRenderHtml:
    """Tests for render_html function."""

    def test_returns_doctype_html(self, fake_protocol):
        """render_html returns string containing '<!DOCTYPE html'."""
        from biointelligence.delivery.renderer import render_html

        html = render_html(fake_protocol, datetime.date(2026, 3, 2))
        assert "<!DOCTYPE html" in html

    def test_contains_all_five_domain_headings_in_order(self, fake_protocol):
        """render_html contains all 5 domain section headings in narrative order."""
        from biointelligence.delivery.renderer import render_html

        html = render_html(fake_protocol, datetime.date(2026, 3, 2))
        # All 5 headings must appear
        assert "Sleep" in html
        assert "Recovery" in html
        assert "Training" in html
        assert "Nutrition" in html
        assert "Supplementation" in html
        # Verify narrative order: Sleep < Recovery < Training < Nutrition < Supplementation
        sleep_pos = html.index("Sleep")
        recovery_pos = html.index("Recovery")
        training_pos = html.index("Training")
        nutrition_pos = html.index("Nutrition")
        supplementation_pos = html.index("Supplementation")
        assert sleep_pos < recovery_pos < training_pos < nutrition_pos < supplementation_pos

    def test_includes_reasoning_for_each_domain(self, fake_protocol):
        """render_html includes reasoning text for each domain (PROT-02)."""
        from biointelligence.delivery.renderer import render_html

        html = render_html(fake_protocol, datetime.date(2026, 3, 2))
        assert fake_protocol.training.reasoning in html
        assert fake_protocol.recovery.reasoning in html
        assert fake_protocol.sleep.reasoning in html
        assert fake_protocol.nutrition.reasoning in html
        assert fake_protocol.supplementation.reasoning in html

    def test_contains_readiness_dashboard_with_score(self, fake_protocol):
        """render_html contains readiness dashboard with score and key numbers."""
        from biointelligence.delivery.renderer import render_html

        html = render_html(fake_protocol, datetime.date(2026, 3, 2))
        # Score should appear
        assert "7" in html
        assert "/10" in html
        # Readiness summary should appear
        assert "Good recovery overnight" in html

    def test_traffic_light_green_for_high_score(self, fake_protocol):
        """render_html has green (#22c55e) color for readiness score 8-10."""
        from biointelligence.delivery.renderer import render_html

        fake_protocol.training.readiness_score = 9
        html = render_html(fake_protocol, datetime.date(2026, 3, 2))
        assert "#22c55e" in html

    def test_traffic_light_yellow_for_medium_score(self, fake_protocol):
        """render_html has yellow (#eab308) color for readiness score 5-7."""
        from biointelligence.delivery.renderer import render_html

        # Score 7 is yellow
        html = render_html(fake_protocol, datetime.date(2026, 3, 2))
        assert "#eab308" in html

    def test_traffic_light_red_for_low_score(self, fake_protocol):
        """render_html has red (#ef4444) color for readiness score 1-4."""
        from biointelligence.delivery.renderer import render_html

        fake_protocol.training.readiness_score = 3
        html = render_html(fake_protocol, datetime.date(2026, 3, 2))
        assert "#ef4444" in html

    def test_shows_data_quality_banner_when_notes_present(self, fake_protocol):
        """render_html shows data quality banner when data_quality_notes is non-empty."""
        from biointelligence.delivery.renderer import render_html

        fake_protocol.data_quality_notes = "Missing HRV data from last 2 days."
        html = render_html(fake_protocol, datetime.date(2026, 3, 2))
        assert "Missing HRV data from last 2 days." in html
        # Banner should use warning colors
        assert "#fef3c7" in html or "#92400e" in html

    def test_hides_data_quality_banner_when_none(self, fake_protocol):
        """render_html hides data quality banner when data_quality_notes is None."""
        from biointelligence.delivery.renderer import render_html

        fake_protocol.data_quality_notes = None
        html = render_html(fake_protocol, datetime.date(2026, 3, 2))
        assert "#fef3c7" not in html
        assert "Data Quality" not in html

    def test_hides_data_quality_banner_when_empty_whitespace(self, fake_protocol):
        """render_html hides data quality banner when data_quality_notes is whitespace."""
        from biointelligence.delivery.renderer import render_html

        fake_protocol.data_quality_notes = "   "
        html = render_html(fake_protocol, datetime.date(2026, 3, 2))
        assert "#fef3c7" not in html

    def test_includes_why_this_matters_section(self, fake_protocol):
        """render_html includes 'Why This Matters' section with overall_summary (PROT-04)."""
        from biointelligence.delivery.renderer import render_html

        html = render_html(fake_protocol, datetime.date(2026, 3, 2))
        assert "Why This Matters" in html
        assert fake_protocol.overall_summary in html

    def test_includes_footer_with_date(self, fake_protocol):
        """render_html includes footer with target_date formatted."""
        from biointelligence.delivery.renderer import render_html

        html = render_html(fake_protocol, datetime.date(2026, 3, 2))
        assert "Mar" in html
        assert "2026" in html

    def test_html_escapes_dynamic_content(self):
        """render_html escapes special characters in dynamic text."""
        from biointelligence.delivery.renderer import render_html

        protocol = DailyProtocol(
            date="2026-03-02",
            training=TrainingRecommendation(
                headline="Test.",
                readiness_score=7,
                readiness_summary="Test <script>alert('xss')</script>",
                recommended_intensity="Zone 2",
                recommended_type="Cycling",
                recommended_duration_minutes=75,
                training_load_assessment="OK.",
                reasoning="Test.",
            ),
            recovery=RecoveryAssessment(
                headline="OK.",
                recovery_status="OK",
                hrv_interpretation="OK",
                body_battery_assessment="OK",
                stress_impact="OK",
                recommendations=["rest"],
                reasoning="OK.",
            ),
            sleep=SleepAnalysis(
                headline="OK.",
                quality_assessment="OK",
                architecture_notes="OK",
                optimization_tips=["sleep"],
                reasoning="OK.",
            ),
            nutrition=NutritionGuidance(
                headline="OK.",
                caloric_target="2000",
                macro_focus="balanced",
                hydration_target="2L",
                meal_timing_notes="normal",
                reasoning="OK.",
            ),
            supplementation=SupplementationPlan(
                headline="OK.",
                adjustments=["none"],
                timing_notes="none",
                reasoning="OK.",
            ),
            overall_summary="Summary.",
        )
        html = render_html(protocol, datetime.date(2026, 3, 2))
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_contains_details_tags_for_expandable_sections(self, fake_protocol):
        """render_html wraps domain details in <details> tags."""
        from biointelligence.delivery.renderer import render_html

        html = render_html(fake_protocol, datetime.date(2026, 3, 2))
        assert html.count("<details>") == 5
        assert html.count("</details>") == 5
        assert "Show details" in html

    def test_headlines_appear_in_html(self, fake_protocol):
        """render_html includes headline text for each domain."""
        from biointelligence.delivery.renderer import render_html

        html = render_html(fake_protocol, datetime.date(2026, 3, 2))
        assert fake_protocol.sleep.headline in html
        assert fake_protocol.recovery.headline in html
        assert fake_protocol.training.headline in html
        assert fake_protocol.nutrition.headline in html
        assert fake_protocol.supplementation.headline in html


class TestRenderText:
    """Tests for render_text function."""

    def test_produces_plain_text_with_header(self, fake_protocol):
        """render_text produces readable plain-text with DAILY PROTOCOL header."""
        from biointelligence.delivery.renderer import render_text

        text = render_text(fake_protocol, datetime.date(2026, 3, 2))
        assert "DAILY PROTOCOL" in text
        assert "7/10" in text

    def test_contains_all_five_domain_sections(self, fake_protocol):
        """render_text contains all 5 domain sections."""
        from biointelligence.delivery.renderer import render_text

        text = render_text(fake_protocol, datetime.date(2026, 3, 2))
        assert "SLEEP" in text
        assert "RECOVERY" in text
        assert "TRAINING" in text
        assert "NUTRITION" in text
        assert "SUPPLEMENTATION" in text

    def test_contains_quick_summary_with_headlines(self, fake_protocol):
        """render_text includes QUICK SUMMARY block with all 5 headlines."""
        from biointelligence.delivery.renderer import render_text

        text = render_text(fake_protocol, datetime.date(2026, 3, 2))
        assert "QUICK SUMMARY" in text
        assert fake_protocol.sleep.headline in text
        assert fake_protocol.recovery.headline in text
        assert fake_protocol.training.headline in text
        assert fake_protocol.nutrition.headline in text
        assert fake_protocol.supplementation.headline in text

    def test_includes_why_this_matters(self, fake_protocol):
        """render_text includes WHY THIS MATTERS section."""
        from biointelligence.delivery.renderer import render_text

        text = render_text(fake_protocol, datetime.date(2026, 3, 2))
        assert "WHY THIS MATTERS" in text
        assert fake_protocol.overall_summary in text

    def test_includes_data_quality_when_present(self, fake_protocol):
        """render_text includes data quality section when notes present."""
        from biointelligence.delivery.renderer import render_text

        fake_protocol.data_quality_notes = "Missing HRV data."
        text = render_text(fake_protocol, datetime.date(2026, 3, 2))
        assert "DATA QUALITY" in text
        assert "Missing HRV data." in text

    def test_omits_data_quality_when_none(self, fake_protocol):
        """render_text omits data quality section when notes are None."""
        from biointelligence.delivery.renderer import render_text

        fake_protocol.data_quality_notes = None
        text = render_text(fake_protocol, datetime.date(2026, 3, 2))
        assert "DATA QUALITY" not in text

    def test_includes_footer_with_date(self, fake_protocol):
        """render_text includes footer with data timestamp."""
        from biointelligence.delivery.renderer import render_text

        text = render_text(fake_protocol, datetime.date(2026, 3, 2))
        assert "2026" in text


class TestBuildSubject:
    """Tests for build_subject function."""

    def test_subject_line_format(self, fake_protocol):
        """build_subject returns 'Daily Protocol -- {date} -- Readiness: {score}/10'."""
        from biointelligence.delivery.renderer import build_subject

        subject = build_subject(fake_protocol, datetime.date(2026, 3, 2))
        assert "Daily Protocol" in subject
        assert "Readiness: 7/10" in subject
        assert "Mar" in subject
        assert "2026" in subject
        # Should use em-dash
        assert "\u2014" in subject
