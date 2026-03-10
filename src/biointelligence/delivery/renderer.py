"""HTML and plain-text email rendering from DailyProtocol."""

from __future__ import annotations

import html
import re
from datetime import date

from biointelligence.prompt.models import DailyProtocol

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_FONT_STACK = (
    "-apple-system, BlinkMacSystemFont, 'Segoe UI', "
    "Roboto, Helvetica, Arial, sans-serif"
)
_BG_COLOR = "#f4f4f5"
_CARD_COLOR = "#ffffff"
_TEXT_COLOR = "#18181b"
_MUTED_COLOR = "#71717a"
_BORDER_COLOR = "#e4e4e7"

# Traffic light colors
_GREEN = "#22c55e"
_YELLOW = "#eab308"
_RED = "#ef4444"

# Data quality banner
_BANNER_BG = "#fef3c7"
_BANNER_TEXT = "#92400e"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _e(text: str) -> str:
    """HTML-escape dynamic text content."""
    return html.escape(str(text))


def _readiness_color(score: int) -> str:
    """Return hex color for readiness score traffic light."""
    if score >= 8:
        return _GREEN
    if score >= 5:
        return _YELLOW
    return _RED


def _readiness_label(score: int) -> str:
    """Return text label for readiness score."""
    if score >= 8:
        return "High Readiness"
    if score >= 5:
        return "Moderate Readiness"
    return "Low Readiness"


def _format_date(d: date) -> str:
    """Format date as 'Mar 2, 2026' (without leading zero on day)."""
    return d.strftime("%b %-d, %Y")


def _markdown_to_html(text: str) -> str:
    """Convert narrative markdown to email-safe HTML.

    Handles: *bold* -> <strong>, [text](url) -> <a href>, escaping,
    and paragraph/line-break formatting. Processes in correct order
    to avoid double-escaping.
    """
    # Split into paragraphs on double newlines
    paragraphs = text.split("\n\n")
    html_parts: list[str] = []

    for para in paragraphs:
        # HTML-escape first (before adding our own HTML)
        escaped = html.escape(para)

        # Convert markdown links: [text](url)
        escaped = re.sub(
            r'\[([^\]]+)\]\(([^)]+)\)',
            lambda m: (
                f'<a href="{m.group(2)}" style="color: #2563eb; '
                f'text-decoration: underline;">{m.group(1)}</a>'
            ),
            escaped,
        )

        # Convert *bold* to <strong> (WhatsApp-style asterisks)
        escaped = re.sub(
            r'\*([^*]+)\*',
            r'<strong>\1</strong>',
            escaped,
        )

        # Convert single newlines to <br>
        escaped = escaped.replace("\n", "<br>\n")

        html_parts.append(
            f'<p style="margin: 0 0 16px 0; font-size: 15px; '
            f'line-height: 1.6; color: {_TEXT_COLOR}; '
            f'font-family: {_FONT_STACK};">{escaped}</p>'
        )

    return "\n".join(html_parts)


# ---------------------------------------------------------------------------
# Section renderers (HTML)
# ---------------------------------------------------------------------------


def _render_readiness_dashboard(protocol: DailyProtocol, color: str) -> str:
    """Render the readiness dashboard section."""
    score = protocol.readiness_score
    label = _readiness_label(score)
    return f"""\
<tr>
  <td style="padding: 32px 24px 16px 24px;">
    <table role="presentation" cellpadding="0" cellspacing="0" width="100%">
      <tr>
        <td align="center" style="padding-bottom: 8px;">
          <span style="font-size: 48px; font-weight: 700; color: {color}; \
font-family: {_FONT_STACK};">{score}</span>
          <span style="font-size: 20px; color: {_MUTED_COLOR}; \
font-family: {_FONT_STACK};">/10</span>
        </td>
      </tr>
      <tr>
        <td align="center" style="padding-bottom: 12px;">
          <span style="font-size: 14px; font-weight: 600; color: {color}; \
text-transform: uppercase; letter-spacing: 1px; \
font-family: {_FONT_STACK};">{_e(label)}</span>
        </td>
      </tr>
    </table>
  </td>
</tr>"""


def _render_data_quality_banner(notes: str | None) -> str:
    """Render data quality warning banner. Returns empty string if clean."""
    if not notes or not notes.strip():
        return ""
    return f"""\
<tr>
  <td style="padding: 0 24px 16px 24px;">
    <table role="presentation" cellpadding="0" cellspacing="0" width="100%" \
style="background-color: {_BANNER_BG}; border-radius: 6px;">
      <tr>
        <td style="padding: 12px 16px;">
          <p style="margin: 0; font-size: 13px; line-height: 1.5; \
color: {_BANNER_TEXT}; font-family: {_FONT_STACK};">\
<strong>Data Quality:</strong> {_e(notes)}</p>
        </td>
      </tr>
    </table>
  </td>
</tr>"""


def _render_narrative(insight_html: str) -> str:
    """Render narrative insight as HTML email body section."""
    converted = _markdown_to_html(insight_html)
    return f"""\
<tr>
  <td style="padding: 16px 24px 24px 24px;">
    {converted}
  </td>
</tr>"""


def _render_footer(target_date: date) -> str:
    """Render footer with data timestamp."""
    formatted = _format_date(target_date)
    return f"""\
<tr>
  <td style="padding: 16px 24px 24px 24px; \
border-top: 1px solid {_BORDER_COLOR};">
    <p style="margin: 0; font-size: 12px; color: {_MUTED_COLOR}; \
text-align: center; font-family: {_FONT_STACK};">\
Data from: {formatted}</p>
  </td>
</tr>"""


def _wrap_html(body_content: str) -> str:
    """Wrap email body in standard HTML email structure."""
    return f"""\
<!DOCTYPE html>
<html lang="en" xmlns="http://www.w3.org/1999/xhtml">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <title>Daily Protocol</title>
    <!--[if mso]>
    <noscript>
        <xml>
            <o:OfficeDocumentSettings>
                <o:PixelsPerInch>96</o:PixelsPerInch>
            </o:OfficeDocumentSettings>
        </xml>
    </noscript>
    <![endif]-->
</head>
<body style="margin: 0; padding: 0; background-color: {_BG_COLOR}; \
font-family: {_FONT_STACK};">
    <table role="presentation" cellpadding="0" cellspacing="0" \
width="100%" style="background-color: {_BG_COLOR};">
        <tr>
            <td align="center" style="padding: 24px 16px;">
                <table role="presentation" cellpadding="0" cellspacing="0" \
width="600" style="background-color: {_CARD_COLOR}; \
border-radius: 8px; overflow: hidden;">
                    {body_content}
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def render_html(protocol: DailyProtocol, target_date: date) -> str:
    """Render DailyProtocol narrative into a styled HTML email."""
    color = _readiness_color(protocol.readiness_score)
    sections = [
        _render_readiness_dashboard(protocol, color),
        _render_data_quality_banner(protocol.data_quality_notes),
        _render_narrative(protocol.insight_html),
        _render_footer(target_date),
    ]
    body = "\n".join(s for s in sections if s)
    return _wrap_html(body)


def render_text(protocol: DailyProtocol, target_date: date) -> str:
    """Render DailyProtocol as plain text for text-only clients."""
    return protocol.insight


def build_subject(protocol: DailyProtocol, target_date: date) -> str:
    """Build email subject line."""
    formatted = _format_date(target_date)
    score = protocol.readiness_score
    return f"Biointelligence \u2014 {formatted} \u2014 Readiness: {score}/10"
