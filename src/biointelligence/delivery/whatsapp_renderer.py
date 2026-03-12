"""WhatsApp text renderer from DailyProtocol.

The insight field is used directly as the message body. Only appends a
profile completeness nudge when applicable. Designed for the WhatsApp
Cloud API body-only template (up to 32,768 chars).
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone

from biointelligence.prompt.models import DailyProtocol

logger = logging.getLogger(__name__)

MAX_BODY_CHARS = 32768

# Step number to human-readable name mapping for nudges
_STEP_NAMES: dict[int, str] = {
    1: "perfil biológico",
    2: "saúde e medicamentos",
    3: "metabolismo e nutrição",
    4: "treino e sono",
    5: "biometria base",
    6: "envio de dados e consentimento",
}


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
        f"*Complete seu {step_name}* para insights mais personalizados\n"
        f"{app_url}/onboarding/step-{first_step}"
    )


NUDGE_COOLDOWN_DAYS = 7


def should_send_nudge(settings: "Settings") -> bool:
    """Check if enough time has elapsed since the last nudge.

    Returns True if last_nudge_sent_at is None or older than 7 days.
    Returns False on any exception (safe default: suppress nudge).
    """
    try:
        from biointelligence.storage.supabase import get_supabase_client

        client = get_supabase_client(settings)
        response = (
            client.table("onboarding_profiles")
            .select("last_nudge_sent_at")
            .limit(1)
            .execute()
        )
        if not response.data:
            return True  # No profile row yet -- allow nudge
        last_sent = response.data[0].get("last_nudge_sent_at")
        if last_sent is None:
            return True  # Never sent
        last_dt = datetime.fromisoformat(last_sent.replace("Z", "+00:00"))
        elapsed = datetime.now(tz=timezone.utc) - last_dt
        return elapsed.total_seconds() > NUDGE_COOLDOWN_DAYS * 86400
    except Exception:
        logger.warning("nudge_cooldown_check_failed")
        return False  # Safe default: don't nudge on error


def record_nudge_sent(settings: "Settings") -> None:
    """Persist the current timestamp as last_nudge_sent_at. Best-effort."""
    try:
        from biointelligence.storage.supabase import get_supabase_client

        client = get_supabase_client(settings)
        now_iso = datetime.now(tz=timezone.utc).isoformat()
        client.table("onboarding_profiles").update(
            {"last_nudge_sent_at": now_iso}
        ).gte("created_at", "1970-01-01").execute()
    except Exception:
        logger.warning("nudge_timestamp_update_failed")


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
    """Render DailyProtocol insight as WhatsApp message.

    The insight text IS the message body. Only appends a profile
    completeness nudge when applicable.
    """
    lines: list[str] = [protocol.insight]

    if incomplete_steps:
        nudge = _render_profile_nudge(
            incomplete_steps, "https://biointelligence.vercel.app"
        )
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
