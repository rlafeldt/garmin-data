"""Failure notification email via Resend for pipeline error awareness."""

from __future__ import annotations

import os
from datetime import date
from html import escape as html_escape

import structlog

from biointelligence.config import Settings
from biointelligence.delivery.sender import send_email

log = structlog.get_logger()


def send_failure_notification(
    target_date: date,
    failed_stage: str,
    error_message: str,
    settings: Settings,
) -> None:
    """Send a failure notification email when the pipeline fails.

    Suppresses notification when failed_stage is "delivery" (cannot email
    about email failure -- Resend may be down).

    This is best-effort: exceptions from send_email are caught and logged,
    never re-raised, to avoid masking the original pipeline error.

    Args:
        target_date: The date the pipeline was running for.
        failed_stage: Pipeline stage that failed (ingestion, analysis, delivery).
        error_message: Error description.
        settings: Application settings with Resend configuration.
    """
    if failed_stage == "delivery":
        log.warning(
            "failure_notification_suppressed",
            reason="Cannot notify for delivery stage failure -- Resend may be down",
            failed_stage=failed_stage,
            date=target_date.isoformat(),
        )
        return

    # Build GitHub Actions run URL from environment
    server_url = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
    repository = os.environ.get("GITHUB_REPOSITORY", "unknown/unknown")
    run_id = os.environ.get("GITHUB_RUN_ID", "0")
    actions_url = f"{server_url}/{repository}/actions/runs/{run_id}"

    subject = f"Pipeline Failed -- {target_date.isoformat()}"

    text = (
        f"Pipeline failure report\n"
        f"=======================\n\n"
        f"Date: {target_date.isoformat()}\n"
        f"Failed stage: {failed_stage}\n"
        f"Error: {error_message}\n\n"
        f"GitHub Actions run: {actions_url}\n"
    )

    html = f"<pre>{html_escape(text)}</pre>"

    log.info(
        "failure_notification_sending",
        date=target_date.isoformat(),
        failed_stage=failed_stage,
    )

    try:
        send_email(
            html=html,
            text=text,
            subject=subject,
            target_date=target_date,
            settings=settings,
        )
        log.info("failure_notification_sent", date=target_date.isoformat())
    except Exception:
        log.exception(
            "failure_notification_failed",
            date=target_date.isoformat(),
            failed_stage=failed_stage,
        )
