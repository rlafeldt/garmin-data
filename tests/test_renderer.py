"""Tests for email rendering: Settings extension, delivery lazy imports, HTML and plain-text renderers."""

from __future__ import annotations

import datetime

import pytest

from biointelligence.prompt.models import DailyProtocol


@pytest.fixture()
def fake_protocol() -> DailyProtocol:
    """A populated DailyProtocol with narrative insight for renderer tests."""
    return DailyProtocol(
        date="2026-03-02",
        readiness_score=7,
        insight=(
            "BIOINTELLIGENCE — Mar 2, 2026\n\n"
            "Your recovery is tracking well after yesterday's Zone 2 ride. "
            "HRV at 48ms sits above your 7-day baseline of 44ms.\n\n"
            "1. Deep sleep hit 1h42m — above the 1.5h target\n"
            "2. Body Battery recharged to 72 overnight\n"
            "3. RHR stable at 54 bpm\n\n"
            "All signals point to readiness for moderate training.\n\n"
            "*Recommendation:* Zone 2 cycling, 75 min, HR cap 150. "
            "Magnesium bisglycinate 400mg before bed."
        ),
        insight_html=(
            "BIOINTELLIGENCE — Mar 2, 2026\n\n"
            "Your recovery is tracking well after yesterday's Zone 2 ride. "
            "HRV at 48ms sits [above your 7-day baseline](https://pubmed.example.com/hrv) of 44ms.\n\n"
            "1. Deep sleep hit 1h42m — above the [1.5h target](https://pubmed.example.com/sleep)\n"
            "2. Body Battery recharged to 72 overnight\n"
            "3. RHR stable at 54 bpm\n\n"
            "All signals point to readiness for moderate training.\n\n"
            "*Recommendation:* Zone 2 cycling, 75 min, HR cap 150. "
            "[Magnesium bisglycinate](https://biointelligence.store/magnesium-bisglycinate) "
            "400mg before bed."
        ),
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
# Task 5a: _markdown_to_html helper tests
# ---------------------------------------------------------------------------


class TestMarkdownToHtml:
    """Tests for _markdown_to_html helper."""

    def test_converts_bold_asterisks(self):
        from biointelligence.delivery.renderer import _markdown_to_html

        result = _markdown_to_html("This is *bold* text")
        assert "<strong>bold</strong>" in result
        assert "*bold*" not in result

    def test_converts_markdown_links(self):
        from biointelligence.delivery.renderer import _markdown_to_html

        result = _markdown_to_html("See [this study](https://example.com)")
        assert '<a href="https://example.com"' in result
        assert ">this study</a>" in result
        assert "[this study]" not in result

    def test_escapes_html_in_text(self):
        from biointelligence.delivery.renderer import _markdown_to_html

        result = _markdown_to_html("Test <script>alert('xss')</script>")
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_preserves_line_breaks(self):
        from biointelligence.delivery.renderer import _markdown_to_html

        result = _markdown_to_html("Line one\nLine two")
        assert "<br" in result or "</p>" in result

    def test_converts_numbered_lists(self):
        from biointelligence.delivery.renderer import _markdown_to_html

        result = _markdown_to_html("1. First point\n2. Second point")
        assert "1." in result
        assert "2." in result


# ---------------------------------------------------------------------------
# Task 2: HTML and plain-text renderer tests (rewritten for narrative)
# ---------------------------------------------------------------------------


class TestRenderHtml:
    """Tests for narrative render_html function."""

    def test_returns_doctype_html(self, fake_protocol):
        from biointelligence.delivery.renderer import render_html
        result = render_html(fake_protocol, datetime.date(2026, 3, 2))
        assert "<!DOCTYPE html" in result

    def test_contains_readiness_score(self, fake_protocol):
        from biointelligence.delivery.renderer import render_html
        result = render_html(fake_protocol, datetime.date(2026, 3, 2))
        assert "7" in result
        assert "/10" in result

    def test_contains_narrative_content(self, fake_protocol):
        from biointelligence.delivery.renderer import render_html
        result = render_html(fake_protocol, datetime.date(2026, 3, 2))
        assert "recovery is tracking well" in result
        assert "HRV at 48ms" in result
        assert "Zone 2 cycling" in result

    def test_converts_markdown_links_to_html(self, fake_protocol):
        from biointelligence.delivery.renderer import render_html
        result = render_html(fake_protocol, datetime.date(2026, 3, 2))
        assert "href=" in result
        assert "pubmed.example.com" in result
        assert "biointelligence.store" in result

    def test_no_details_tags(self, fake_protocol):
        from biointelligence.delivery.renderer import render_html
        result = render_html(fake_protocol, datetime.date(2026, 3, 2))
        assert "<details>" not in result

    def test_html_escapes_dynamic_content(self):
        from biointelligence.delivery.renderer import render_html
        protocol = DailyProtocol(
            date="2026-03-02",
            readiness_score=7,
            insight="Test <script>alert('xss')</script>",
            insight_html="Test <script>alert('xss')</script>",
        )
        result = render_html(protocol, datetime.date(2026, 3, 2))
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_no_old_domain_sections(self, fake_protocol):
        from biointelligence.delivery.renderer import render_html
        result = render_html(fake_protocol, datetime.date(2026, 3, 2))
        assert ">Sleep<" not in result
        assert ">Recovery<" not in result
        assert ">Nutrition<" not in result
        assert ">Supplementation<" not in result

    def test_includes_footer(self, fake_protocol):
        from biointelligence.delivery.renderer import render_html
        result = render_html(fake_protocol, datetime.date(2026, 3, 2))
        assert "2026" in result

    def test_data_quality_banner_when_present(self):
        from biointelligence.delivery.renderer import render_html
        protocol = DailyProtocol(
            date="2026-03-02",
            readiness_score=5,
            insight="Limited data today.",
            insight_html="Limited data today.",
            data_quality_notes="Missing HRV data from last 2 days.",
        )
        result = render_html(protocol, datetime.date(2026, 3, 2))
        assert "Missing HRV data" in result


class TestRenderText:
    """Tests for narrative render_text function."""

    def test_contains_narrative(self, fake_protocol):
        from biointelligence.delivery.renderer import render_text
        result = render_text(fake_protocol, datetime.date(2026, 3, 2))
        assert "recovery is tracking well" in result
        assert "HRV at 48ms" in result

    def test_is_plain_text(self, fake_protocol):
        from biointelligence.delivery.renderer import render_text
        result = render_text(fake_protocol, datetime.date(2026, 3, 2))
        assert "<html" not in result
        assert "<p " not in result


class TestBuildSubject:
    """Tests for build_subject function."""

    def test_subject_contains_biointelligence_branding(self, fake_protocol):
        from biointelligence.delivery.renderer import build_subject
        subject = build_subject(fake_protocol, datetime.date(2026, 3, 2))
        assert "Biointelligence" in subject

    def test_subject_contains_readiness_score(self, fake_protocol):
        from biointelligence.delivery.renderer import build_subject
        subject = build_subject(fake_protocol, datetime.date(2026, 3, 2))
        assert "7/10" in subject

    def test_subject_contains_date(self, fake_protocol):
        from biointelligence.delivery.renderer import build_subject
        subject = build_subject(fake_protocol, datetime.date(2026, 3, 2))
        assert "março" in subject
        assert "2026" in subject
