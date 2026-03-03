"""Garmin OAuth token persistence via Supabase for headless CI execution."""

from __future__ import annotations

from datetime import UTC, datetime

import structlog
from garminconnect import Garmin
from supabase import Client
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

log = structlog.get_logger()


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    retry=retry_if_exception_type((ConnectionError, TimeoutError)),
)
def load_tokens_from_supabase(client: Client) -> str | None:
    """Load Garmin OAuth tokens from Supabase garmin_tokens table.

    Args:
        client: Supabase client instance.

    Returns:
        Base64-encoded token string if found, None if table is empty.
    """
    log.info("garmin_tokens_load_start")

    response = (
        client.table("garmin_tokens")
        .select("token_data")
        .eq("id", "primary")
        .maybe_single()
        .execute()
    )

    if response.data is None:
        log.info("garmin_tokens_load_empty")
        return None

    token_data = response.data["token_data"]
    log.info("garmin_tokens_load_success", token_length=len(token_data))
    return token_data


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    retry=retry_if_exception_type((ConnectionError, TimeoutError)),
)
def save_tokens_to_supabase(client: Client, garmin: Garmin) -> None:
    """Save refreshed Garmin OAuth tokens to Supabase.

    Calls garmin.garth.dumps() to serialize both OAuth1 and OAuth2 tokens
    as a base64 string, then upserts to garmin_tokens table.

    Args:
        client: Supabase client instance.
        garmin: Authenticated Garmin client with valid tokens.
    """
    token_data = garmin.garth.dumps()
    updated_at = datetime.now(tz=UTC).isoformat()

    log.info("garmin_tokens_save", token_length=len(token_data))

    client.table("garmin_tokens").upsert(
        {
            "id": "primary",
            "token_data": token_data,
            "updated_at": updated_at,
        },
        on_conflict="id",
    ).execute()

    log.info("garmin_tokens_save_done")
