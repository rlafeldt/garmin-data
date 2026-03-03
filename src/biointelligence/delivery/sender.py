"""Resend email sender with tenacity retry for Daily Protocol delivery."""

from __future__ import annotations

from datetime import date

import resend
import structlog
from pydantic import BaseModel
from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from biointelligence.config import Settings

log = structlog.get_logger()


class DeliveryResult(BaseModel):
    """Result of a protocol delivery attempt."""

    date: date
    email_id: str | None = None
    success: bool
    error: str | None = None


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=4, max=60),
    retry=retry_if_exception_type(Exception),
)
def _send_via_resend(params: dict) -> dict:
    """Send email via Resend with tenacity retry on transient errors.

    Args:
        params: Resend email parameters dict.

    Returns:
        Response dict containing email ID.
    """
    return resend.Emails.send(params)


def send_email(
    html: str,
    text: str,
    subject: str,
    target_date: date,
    settings: Settings,
) -> DeliveryResult:
    """Send an email via the Resend API.

    Sets the API key per-call (not at module level) for test isolation.
    Uses tenacity retry on transient errors (429, 500).

    Args:
        html: HTML email body.
        text: Plain-text email body.
        subject: Email subject line.
        target_date: Date the protocol is for.
        settings: Application settings with Resend configuration.

    Returns:
        DeliveryResult with email_id on success, error on failure.
    """
    # Set API key per-call (pitfall 3: not at module level for test isolation)
    resend.api_key = settings.resend_api_key

    params = {
        "from": f"BioIntelligence <{settings.sender_email}>",
        "to": [settings.recipient_email],
        "subject": subject,
        "html": html,
        "text": text,
    }

    try:
        response = _send_via_resend(params)
        email_id = response["id"]

        log.info(
            "email_sent",
            date=target_date.isoformat(),
            email_id=email_id,
        )

        return DeliveryResult(
            date=target_date,
            email_id=email_id,
            success=True,
        )
    except RetryError as e:
        # Extract the underlying exception from tenacity's RetryError
        cause = e.last_attempt.exception() if e.last_attempt else e
        error_msg = str(cause) if cause else str(e)

        log.error(
            "email_send_failed",
            date=target_date.isoformat(),
            error=error_msg,
        )

        return DeliveryResult(
            date=target_date,
            success=False,
            error=error_msg,
        )
    except Exception as e:
        log.error(
            "email_send_failed",
            date=target_date.isoformat(),
            error=str(e),
        )

        return DeliveryResult(
            date=target_date,
            success=False,
            error=str(e),
        )
