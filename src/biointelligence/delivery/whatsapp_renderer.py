"""WhatsApp text renderer from DailyProtocol.

Transforms a DailyProtocol into WhatsApp-formatted text with emoji headers,
*bold* keys, condensed reasoning, and alert banners. Designed for the
WhatsApp Cloud API body-only template (up to 32,768 chars).
"""

from __future__ import annotations

import logging
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

logger = logging.getLogger(__name__)

MAX_BODY_CHARS = 32768

# Step number to human-readable name mapping for nudges
_STEP_NAMES: dict[int, str] = {
    1: "biological profile",
    2: "health & medications",
    3: "metabolic & nutrition",
    4: "training & sleep",
    5: "baseline biometrics",
    6: "data upload & consent",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _format_date(d: date) -> str:
    """Format date as 'Mar 2, 2026' (without leading zero on day)."""
    return d.strftime("%b %-d, %Y")


def _trim_reasoning(text: str) -> str:
    """Trim reasoning to first 2 sentences.

    Splits on '. ' boundaries and keeps up to 2 sentences.
    Ensures the result ends with a period.
    """
    # Split on sentence boundaries (period followed by space)
    parts = text.split(". ")
    if len(parts) <= 2:
        # Already 2 or fewer sentences
        return text.rstrip()
    # Take first 2 parts, rejoin with '. '
    trimmed = ". ".join(parts[:2])
    if not trimmed.endswith("."):
        trimmed += "."
    return trimmed


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------


def _render_alerts(alerts: list[Alert]) -> list[str]:
    """Render alert banners in WhatsApp format.

    Returns empty list if no alerts. Each alert gets a severity tag,
    title, description, and action line.
    """
    if not alerts:
        return []

    lines: list[str] = []
    for alert in alerts:
        severity_label = alert.severity.value.upper()
        lines.append(f"*[{severity_label}] {alert.title}*")
        lines.append(alert.description)
        lines.append(f"Action: {alert.suggested_action}")
        lines.append("")
    return lines


def _render_sleep(sleep: SleepAnalysis) -> list[str]:
    """Render sleep domain section."""
    return [
        "\U0001f634 *Sleep*",
        f"*Quality:* {sleep.quality_assessment}",
        f"*Architecture:* {sleep.architecture_notes}",
        _trim_reasoning(sleep.reasoning),
        "",
    ]


def _render_recovery(recovery: RecoveryAssessment) -> list[str]:
    """Render recovery domain section."""
    return [
        "\U0001f49a *Recovery*",
        f"*Status:* {recovery.recovery_status}",
        f"*HRV:* {recovery.hrv_interpretation}",
        f"*Body Battery:* {recovery.body_battery_assessment}",
        _trim_reasoning(recovery.reasoning),
        "",
    ]


def _render_training(training: TrainingRecommendation) -> list[str]:
    """Render training domain section."""
    return [
        "\U0001f525 *Training*",
        f"*Intensity:* {training.recommended_intensity}",
        f"*Type:* {training.recommended_type}",
        f"*Duration:* {training.recommended_duration_minutes} min",
        _trim_reasoning(training.reasoning),
        "",
    ]


def _render_nutrition(nutrition: NutritionGuidance) -> list[str]:
    """Render nutrition domain section."""
    return [
        "\U0001f37d\ufe0f *Nutrition*",
        f"*Calories:* {nutrition.caloric_target}",
        f"*Macros:* {nutrition.macro_focus}",
        f"*Hydration:* {nutrition.hydration_target}",
        _trim_reasoning(nutrition.reasoning),
        "",
    ]


def _render_supplementation(supp: SupplementationPlan) -> list[str]:
    """Render supplementation domain section."""
    lines: list[str] = ["\U0001f48a *Supplementation*"]
    for adj in supp.adjustments:
        lines.append(f"- {adj}")
    lines.append(f"*Timing:* {supp.timing_notes}")
    lines.append(_trim_reasoning(supp.reasoning))
    lines.append("")
    return lines


# ---------------------------------------------------------------------------
# Profile nudge
# ---------------------------------------------------------------------------


def _render_profile_nudge(incomplete_steps: list[int], app_url: str) -> str:
    """Render a profile completeness nudge for WhatsApp.

    Shows a nudge for the first incomplete onboarding step only, with a
    deep-link to that specific step in the onboarding app.

    Args:
        incomplete_steps: Step numbers where step_N_complete is False.
        app_url: Base URL of the deployed onboarding app.

    Returns:
        Formatted nudge text, or empty string if all steps complete.
    """
    if not incomplete_steps:
        return ""

    first_step = incomplete_steps[0]
    step_name = _STEP_NAMES.get(first_step, f"step {first_step}")

    return (
        f"---\n"
        f"*Complete your {step_name}* for more personalised insights\n"
        f"{app_url}/onboarding/step-{first_step}"
    )


def get_incomplete_steps(settings: "Settings") -> list[int]:
    """Query Supabase for incomplete onboarding steps.

    Args:
        settings: Application settings with Supabase credentials.

    Returns:
        List of step numbers where step_N_complete is False.
        Returns empty list on any exception (graceful degradation).
    """
    try:
        from biointelligence.storage.supabase import get_supabase_client

        client = get_supabase_client(settings)
        response = (
            client.table("onboarding_profiles")
            .select("*")
            .limit(1)
            .execute()
        )

        if not response.data:
            return []

        profile = response.data[0]
        incomplete: list[int] = []
        for n in range(1, 7):
            if not profile.get(f"step_{n}_complete", False):
                incomplete.append(n)

        return incomplete
    except Exception:
        logger.warning("Failed to query profile completeness")
        return []


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def render_whatsapp(
    protocol: DailyProtocol,
    target_date: date,
    *,
    incomplete_steps: list[int] | None = None,
) -> str:
    """Render DailyProtocol into WhatsApp-formatted text.

    Produces a message with emoji section headers, *bold* keys, condensed
    reasoning (1-2 sentences per domain), and a closing synthesis section.
    Optionally appends a profile completeness nudge.

    Domain order: Sleep -> Recovery -> Training -> Nutrition -> Supplementation.

    Args:
        protocol: The DailyProtocol to render.
        target_date: Date the protocol is for.
        incomplete_steps: Optional list of incomplete onboarding step numbers.

    Returns:
        WhatsApp-formatted text string.
    """
    formatted_date = _format_date(target_date)
    score = protocol.training.readiness_score

    lines: list[str] = [
        f"*Daily Protocol* -- {formatted_date}",
        f"Readiness: *{score}/10*",
        "",
    ]

    # Alert banners (before domain sections)
    alert_lines = _render_alerts(protocol.alerts)
    if alert_lines:
        lines.extend(alert_lines)

    # Domain sections in order
    lines.extend(_render_sleep(protocol.sleep))
    lines.extend(_render_recovery(protocol.recovery))
    lines.extend(_render_training(protocol.training))
    lines.extend(_render_nutrition(protocol.nutrition))
    lines.extend(_render_supplementation(protocol.supplementation))

    # Why This Matters
    lines.append("*Why This Matters*")
    lines.append(protocol.overall_summary)

    # Profile completeness nudge (when incomplete steps provided)
    if incomplete_steps:
        nudge = _render_profile_nudge(incomplete_steps, "https://biointelligence.vercel.app")
        if nudge:
            lines.append("")
            lines.append(nudge)

    result = "\n".join(lines)

    if len(result) > MAX_BODY_CHARS:
        logger.warning(
            "WhatsApp message exceeds %d chars: %d chars",
            MAX_BODY_CHARS,
            len(result),
        )

    return result
