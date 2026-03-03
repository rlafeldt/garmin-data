"""Per-category Garmin metric extraction with retry and error isolation."""

from __future__ import annotations

import datetime

import structlog
from garminconnect import (
    Garmin,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
)
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

log = structlog.get_logger()

# Map of metric category to garminconnect method name
ENDPOINTS: dict[str, str] = {
    "stats": "get_stats",
    "heart_rates": "get_heart_rates",
    "sleep": "get_sleep_data",
    "hrv": "get_hrv_data",
    "body_battery": "get_body_battery",
    "stress": "get_stress_data",
    "spo2": "get_spo2_data",
    "respiration": "get_respiration_data",
    "training_status": "get_training_status",
    "training_readiness": "get_training_readiness",
    "max_metrics": "get_max_metrics",
}


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    retry=retry_if_exception_type(
        (GarminConnectConnectionError, GarminConnectTooManyRequestsError)
    ),
)
def _fetch_with_retry(client: Garmin, method_name: str, *args: str) -> dict | list | None:
    """Call a garminconnect method with retry logic.

    Retries on connection errors and rate limiting with exponential backoff.

    Args:
        client: Authenticated Garmin client.
        method_name: Name of the garminconnect method to call.
        *args: Arguments to pass to the method.

    Returns:
        The API response (dict or list), or None if the response is empty.
    """
    method = getattr(client, method_name)
    return method(*args)


def extract_all_metrics(client: Garmin, target_date: datetime.date) -> dict:
    """Extract all metric categories for a date, handling per-category failures gracefully.

    Each endpoint is called independently. If one fails after retries, it is logged
    as a warning and set to None in the result dict. Other endpoints continue.

    Args:
        client: Authenticated Garmin client.
        target_date: The date to extract metrics for.

    Returns:
        Dict with keys for each metric category. Failed endpoints have None values.
        Activities key contains an empty list on failure.
    """
    date_str = target_date.isoformat()
    raw: dict = {}

    for key, method_name in ENDPOINTS.items():
        try:
            raw[key] = _fetch_with_retry(client, method_name, date_str)
        except Exception as e:
            log.warning("extraction_failed", metric=key, error=str(e))
            raw[key] = None

    # Activities use a different signature (date range)
    try:
        raw["activities"] = _fetch_with_retry(
            client, "get_activities_by_date", date_str, date_str
        )
    except Exception as e:
        log.warning("extraction_failed", metric="activities", error=str(e))
        raw["activities"] = []

    return raw
