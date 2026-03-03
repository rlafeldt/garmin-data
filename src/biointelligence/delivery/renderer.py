"""HTML and plain-text email rendering from DailyProtocol."""

from __future__ import annotations

from datetime import date

from biointelligence.prompt.models import DailyProtocol


def render_html(protocol: DailyProtocol, target_date: date) -> str:
    """Render DailyProtocol into a styled HTML email string."""
    raise NotImplementedError


def render_text(protocol: DailyProtocol, target_date: date) -> str:
    """Render DailyProtocol as plain text for Apple Watch and text-only clients."""
    raise NotImplementedError


def build_subject(protocol: DailyProtocol, target_date: date) -> str:
    """Build email subject line."""
    raise NotImplementedError
