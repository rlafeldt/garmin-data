"""HTML and plain-text email rendering from DailyProtocol."""

from __future__ import annotations

import html
from datetime import date

from biointelligence.anomaly.models import Alert, AlertSeverity
from biointelligence.prompt.models import (
    DailyProtocol,
    NutritionGuidance,
    RecoveryAssessment,
    SleepAnalysis,
    SupplementationPlan,
    TrainingRecommendation,
)

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

# Alert banner colors
_ALERT_WARNING_BG = "#fef9c3"
_ALERT_WARNING_BORDER = "#eab308"
_ALERT_CRITICAL_BG = "#fef2f2"
_ALERT_CRITICAL_BORDER = "#ef4444"


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


# ---------------------------------------------------------------------------
# Section renderers (HTML)
# ---------------------------------------------------------------------------


def _render_readiness_dashboard(protocol: DailyProtocol, color: str) -> str:
    """Render the readiness dashboard section."""
    score = protocol.training.readiness_score
    label = _readiness_label(score)
    summary = _e(protocol.training.readiness_summary)

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
      <tr>
        <td align="center" style="padding-bottom: 8px;">
          <p style="margin: 0; font-size: 15px; line-height: 1.5; \
color: {_TEXT_COLOR}; font-family: {_FONT_STACK};">{summary}</p>
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


def _render_alert_banners(alerts: list[Alert]) -> str:
    """Render alert banners for the top of the email.

    Returns empty string if alerts list is empty. Each alert gets a
    colored left border and background based on severity.
    """
    if not alerts:
        return ""

    parts: list[str] = []
    for alert in alerts:
        if alert.severity == AlertSeverity.CRITICAL:
            bg = _ALERT_CRITICAL_BG
            border = _ALERT_CRITICAL_BORDER
        else:
            bg = _ALERT_WARNING_BG
            border = _ALERT_WARNING_BORDER

        parts.append(f"""\
<tr>
  <td style="padding: 8px 24px;">
    <table role="presentation" cellpadding="0" cellspacing="0" width="100%" \
style="background-color: {bg}; border-left: 4px solid {border}; border-radius: 6px;">
      <tr>
        <td style="padding: 12px 16px;">
          <p style="margin: 0 0 4px 0; font-size: 14px; font-weight: 700; \
color: {border}; font-family: {_FONT_STACK};">{_e(alert.title)}</p>
          <p style="margin: 0 0 4px 0; font-size: 13px; line-height: 1.5; \
color: {_TEXT_COLOR}; font-family: {_FONT_STACK};">{_e(alert.description)}</p>
          <p style="margin: 0; font-size: 13px; line-height: 1.5; \
color: {_MUTED_COLOR}; font-family: {_FONT_STACK};">\
<strong>Action:</strong> {_e(alert.suggested_action)}</p>
        </td>
      </tr>
    </table>
  </td>
</tr>""")

    return "\n".join(parts)


def _render_domain_section(title: str, headline: str, content: str) -> str:
    """Wrap a domain's content in a section with headline and expandable details."""
    return f"""\
<tr>
  <td style="padding: 0 24px;">
    <table role="presentation" cellpadding="0" cellspacing="0" width="100%" \
style="border-top: 1px solid {_BORDER_COLOR};">
      <tr>
        <td style="padding-top: 20px; padding-bottom: 4px;">
          <h2 style="margin: 0; font-size: 18px; font-weight: 600; \
color: {_TEXT_COLOR}; font-family: {_FONT_STACK};">{_e(title)}</h2>
        </td>
      </tr>
      <tr>
        <td style="padding-bottom: 4px;">
          <p style="margin: 0; font-size: 15px; font-weight: 600; \
line-height: 1.5; color: {_TEXT_COLOR}; \
font-family: {_FONT_STACK};">{_e(headline)}</p>
        </td>
      </tr>
      <tr>
        <td style="padding-bottom: 20px;">
          <details>
            <summary style="font-size: 13px; color: {_MUTED_COLOR}; \
cursor: pointer; font-family: {_FONT_STACK}; padding: 4px 0;">Show details</summary>
{content}
          </details>
        </td>
      </tr>
    </table>
  </td>
</tr>"""


def _kv(label: str, value: str) -> str:
    """Render a key-value pair as bold label + value."""
    return (
        f'<p style="margin: 0 0 4px 0; font-size: 14px; '
        f"line-height: 1.5; color: {_TEXT_COLOR}; "
        f'font-family: {_FONT_STACK};">'
        f"<strong>{_e(label)}:</strong> {_e(value)}</p>"
    )


def _reasoning(text: str) -> str:
    """Render reasoning paragraph in muted style."""
    return (
        f'<p style="margin: 8px 0 0 0; font-size: 13px; '
        f"line-height: 1.5; color: {_MUTED_COLOR}; "
        f'font-family: {_FONT_STACK};">{_e(text)}</p>'
    )


def _list_items(items: list[str]) -> str:
    """Render a list of items as HTML."""
    if not items:
        return ""
    li = "".join(
        f'<li style="margin-bottom: 2px; font-size: 14px; '
        f"line-height: 1.5; color: {_TEXT_COLOR}; "
        f'font-family: {_FONT_STACK};">{_e(item)}</li>'
        for item in items
    )
    return f'<ul style="margin: 4px 0 0 0; padding-left: 20px;">{li}</ul>'


def _render_sleep(sleep: SleepAnalysis) -> str:
    """Render sleep domain content."""
    parts = [
        _kv("Quality", sleep.quality_assessment),
        _kv("Architecture", sleep.architecture_notes),
    ]
    if sleep.optimization_tips:
        parts.append(
            '<p style="margin: 4px 0 2px 0; font-size: 14px; '
            f"line-height: 1.5; color: {_TEXT_COLOR}; "
            f'font-family: {_FONT_STACK};">'
            "<strong>Optimization Tips:</strong></p>"
        )
        parts.append(_list_items(sleep.optimization_tips))
    parts.append(_reasoning(sleep.reasoning))
    return "\n".join(parts)


def _render_recovery(recovery: RecoveryAssessment) -> str:
    """Render recovery domain content."""
    parts = [
        _kv("Status", recovery.recovery_status),
        _kv("HRV", recovery.hrv_interpretation),
        _kv("Body Battery", recovery.body_battery_assessment),
        _kv("Stress", recovery.stress_impact),
    ]
    if recovery.recommendations:
        parts.append(
            '<p style="margin: 4px 0 2px 0; font-size: 14px; '
            f"line-height: 1.5; color: {_TEXT_COLOR}; "
            f'font-family: {_FONT_STACK};">'
            "<strong>Recommendations:</strong></p>"
        )
        parts.append(_list_items(recovery.recommendations))
    parts.append(_reasoning(recovery.reasoning))
    return "\n".join(parts)


def _render_training(training: TrainingRecommendation) -> str:
    """Render training domain content."""
    parts = [
        _kv("Readiness", training.readiness_summary),
        _kv("Intensity", training.recommended_intensity),
        _kv("Type", training.recommended_type),
        _kv("Duration", f"{training.recommended_duration_minutes} min"),
        _kv("Load Assessment", training.training_load_assessment),
        _reasoning(training.reasoning),
    ]
    return "\n".join(parts)


def _render_nutrition(nutrition: NutritionGuidance) -> str:
    """Render nutrition domain content."""
    parts = [
        _kv("Caloric Target", nutrition.caloric_target),
        _kv("Macro Focus", nutrition.macro_focus),
        _kv("Hydration", nutrition.hydration_target),
        _kv("Meal Timing", nutrition.meal_timing_notes),
        _reasoning(nutrition.reasoning),
    ]
    return "\n".join(parts)


def _render_supplementation(supp: SupplementationPlan) -> str:
    """Render supplementation domain content."""
    parts: list[str] = []
    if supp.adjustments:
        parts.append(
            '<p style="margin: 0 0 2px 0; font-size: 14px; '
            f"line-height: 1.5; color: {_TEXT_COLOR}; "
            f'font-family: {_FONT_STACK};">'
            "<strong>Adjustments:</strong></p>"
        )
        parts.append(_list_items(supp.adjustments))
    parts.append(_kv("Timing", supp.timing_notes))
    parts.append(_reasoning(supp.reasoning))
    return "\n".join(parts)


def _render_why_this_matters(summary: str) -> str:
    """Render the 'Why This Matters' closing synthesis section."""
    return f"""\
<tr>
  <td style="padding: 0 24px;">
    <table role="presentation" cellpadding="0" cellspacing="0" width="100%" \
style="border-top: 1px solid {_BORDER_COLOR};">
      <tr>
        <td style="padding-top: 20px; padding-bottom: 4px;">
          <h2 style="margin: 0; font-size: 18px; font-weight: 600; \
color: {_TEXT_COLOR}; font-family: {_FONT_STACK};">Why This Matters</h2>
        </td>
      </tr>
      <tr>
        <td style="padding-bottom: 24px;">
          <p style="margin: 0; font-size: 14px; line-height: 1.6; \
color: {_TEXT_COLOR}; font-family: {_FONT_STACK};">{_e(summary)}</p>
        </td>
      </tr>
    </table>
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
    """Render DailyProtocol into a styled HTML email string.

    Produces a table-based layout with inline CSS for email client
    compatibility. All dynamic text is HTML-escaped.
    """
    color = _readiness_color(protocol.training.readiness_score)

    sections = [
        _render_alert_banners(protocol.alerts),
        _render_readiness_dashboard(protocol, color),
        _render_data_quality_banner(protocol.data_quality_notes),
        _render_domain_section(
            "Sleep", protocol.sleep.headline,
            _render_sleep(protocol.sleep),
        ),
        _render_domain_section(
            "Recovery", protocol.recovery.headline,
            _render_recovery(protocol.recovery),
        ),
        _render_domain_section(
            "Training", protocol.training.headline,
            _render_training(protocol.training),
        ),
        _render_domain_section(
            "Nutrition", protocol.nutrition.headline,
            _render_nutrition(protocol.nutrition),
        ),
        _render_domain_section(
            "Supplementation", protocol.supplementation.headline,
            _render_supplementation(protocol.supplementation),
        ),
        _render_why_this_matters(protocol.overall_summary),
        _render_footer(target_date),
    ]
    body = "\n".join(s for s in sections if s)
    return _wrap_html(body)


def render_text(protocol: DailyProtocol, target_date: date) -> str:
    """Render DailyProtocol as plain text for Apple Watch and text-only clients.

    Purpose-built plain text (NOT stripped HTML).
    """
    score = protocol.training.readiness_score
    formatted_date = _format_date(target_date)

    lines: list[str] = [
        f"DAILY PROTOCOL \u2014 {target_date:%B %-d, %Y}",
        f"Readiness: {score}/10",
        "",
    ]

    # Alert section at top when alerts exist
    if protocol.alerts:
        lines.append("ALERTS")
        for alert in protocol.alerts:
            lines.append(
                f"- [{alert.severity.value.upper()}] {alert.title}: "
                f"{alert.description} -- Action: {alert.suggested_action}"
            )
        lines.append("")

    lines.extend([
        "QUICK SUMMARY",
        f"  Sleep: {protocol.sleep.headline}",
        f"  Recovery: {protocol.recovery.headline}",
        f"  Training: {protocol.training.headline}",
        f"  Nutrition: {protocol.nutrition.headline}",
        f"  Supplements: {protocol.supplementation.headline}",
        "",
    ])

    if protocol.data_quality_notes and protocol.data_quality_notes.strip():
        lines.extend([
            "DATA QUALITY",
            protocol.data_quality_notes,
            "",
        ])

    # Sleep
    lines.extend([
        "SLEEP",
        f"Quality: {protocol.sleep.quality_assessment}",
        f"Architecture: {protocol.sleep.architecture_notes}",
    ])
    for tip in protocol.sleep.optimization_tips:
        lines.append(f"  - {tip}")
    lines.extend([protocol.sleep.reasoning, ""])

    # Recovery
    lines.extend([
        "RECOVERY",
        f"Status: {protocol.recovery.recovery_status}",
        f"HRV: {protocol.recovery.hrv_interpretation}",
        f"Body Battery: {protocol.recovery.body_battery_assessment}",
        f"Stress: {protocol.recovery.stress_impact}",
    ])
    for rec in protocol.recovery.recommendations:
        lines.append(f"  - {rec}")
    lines.extend([protocol.recovery.reasoning, ""])

    # Training
    lines.extend([
        "TRAINING",
        f"Readiness: {protocol.training.readiness_summary}",
        f"Intensity: {protocol.training.recommended_intensity}",
        f"Type: {protocol.training.recommended_type}",
        f"Duration: {protocol.training.recommended_duration_minutes} min",
        f"Load: {protocol.training.training_load_assessment}",
        protocol.training.reasoning,
        "",
    ])

    # Nutrition
    lines.extend([
        "NUTRITION",
        f"Calories: {protocol.nutrition.caloric_target}",
        f"Macros: {protocol.nutrition.macro_focus}",
        f"Hydration: {protocol.nutrition.hydration_target}",
        f"Timing: {protocol.nutrition.meal_timing_notes}",
        protocol.nutrition.reasoning,
        "",
    ])

    # Supplementation
    lines.append("SUPPLEMENTATION")
    for adj in protocol.supplementation.adjustments:
        lines.append(f"  - {adj}")
    lines.extend([
        f"Timing: {protocol.supplementation.timing_notes}",
        protocol.supplementation.reasoning,
        "",
    ])

    # Why This Matters
    lines.extend([
        "WHY THIS MATTERS",
        protocol.overall_summary,
        "",
    ])

    # Footer
    lines.append(f"Data from: {formatted_date}")

    return "\n".join(lines)


def build_subject(protocol: DailyProtocol, target_date: date) -> str:
    """Build email subject line.

    Format: Daily Protocol -- {Mon D, YYYY} -- Readiness: {score}/10
    Uses em-dash (Resend handles encoding).
    """
    formatted = _format_date(target_date)
    score = protocol.training.readiness_score
    return f"Daily Protocol \u2014 {formatted} \u2014 Readiness: {score}/10"
