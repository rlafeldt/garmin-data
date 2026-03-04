"""WhatsApp sender via Meta Cloud API with tenacity retry for Daily Protocol delivery."""

from __future__ import annotations

from datetime import date

import httpx
import structlog
from tenacity import (
    RetryError,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from biointelligence.config import Settings
from biointelligence.delivery.sender import DeliveryResult

log = structlog.get_logger()

WHATSAPP_API_URL = "https://graph.facebook.com/v21.0/{phone_number_id}/messages"

_RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})


def _is_retryable(exc: BaseException) -> bool:
    """Determine if an exception is retryable.

    Retryable: httpx.TransportError, httpx.HTTPStatusError with 429/5xx.
    Not retryable: HTTPStatusError with 401/400, all other exceptions.
    """
    if isinstance(exc, httpx.TransportError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in _RETRYABLE_STATUS_CODES
    return False


@retry(
    retry=retry_if_exception(_is_retryable),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=4, max=60),
)
def _send_via_whatsapp(url: str, headers: dict, payload: dict) -> dict:
    """POST to the WhatsApp Cloud API with tenacity retry on transient errors.

    Args:
        url: Full API URL with phone_number_id.
        headers: Request headers with Authorization Bearer token.
        payload: JSON payload with template data.

    Returns:
        Response JSON dict containing message ID.
    """
    response = httpx.post(url, headers=headers, json=payload, timeout=30.0)
    response.raise_for_status()
    return response.json()


def send_whatsapp(
    body_text: str,
    target_date: date,
    settings: Settings,
) -> DeliveryResult:
    """Send a WhatsApp message via the Meta Cloud API.

    Builds a template-based payload using the daily_protocol template
    and sends it to the configured recipient phone number.

    Args:
        body_text: Rendered WhatsApp message body text.
        target_date: Date the protocol is for.
        settings: Application settings with WhatsApp configuration.

    Returns:
        DeliveryResult with message_id on success, error on failure.
    """
    url = WHATSAPP_API_URL.format(
        phone_number_id=settings.whatsapp_phone_number_id,
    )

    headers = {
        "Authorization": f"Bearer {settings.whatsapp_access_token}",
        "Content-Type": "application/json",
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": settings.whatsapp_recipient_phone,
        "type": "template",
        "template": {
            "name": "daily_protocol",
            "language": {"code": "en"},
            "components": [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": body_text},
                    ],
                },
            ],
        },
    }

    try:
        response_data = _send_via_whatsapp(url, headers, payload)
        message_id = response_data["messages"][0]["id"]

        log.info(
            "whatsapp_sent",
            date=target_date.isoformat(),
            message_id=message_id,
        )

        return DeliveryResult(
            date=target_date,
            email_id=message_id,
            success=True,
        )
    except RetryError as e:
        cause = e.last_attempt.exception() if e.last_attempt else e
        error_msg = str(cause) if cause else str(e)

        log.error(
            "whatsapp_send_failed",
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
            "whatsapp_send_failed",
            date=target_date.isoformat(),
            error=str(e),
        )

        return DeliveryResult(
            date=target_date,
            success=False,
            error=str(e),
        )
