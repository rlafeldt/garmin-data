"""Garmin Connect authentication with token persistence."""

from __future__ import annotations

import os

import structlog
from garminconnect import Garmin
from supabase import Client

from biointelligence.automation.tokens import (
    load_tokens_from_supabase,
    save_tokens_to_supabase,
)
from biointelligence.config import Settings

log = structlog.get_logger()


def get_authenticated_client(
    settings: Settings,
    *,
    supabase_client: Client | None = None,
) -> Garmin:
    """Get an authenticated Garmin client, loading persisted tokens if available.

    Supports two modes:
    - CI mode (supabase_client provided): Load/save tokens from Supabase.
      Falls back to email/password if no tokens stored yet.
    - Local dev mode (supabase_client=None): Use filesystem token directory.

    Token refresh is saved immediately after auth, before returning,
    to ensure persistence even if later pipeline stages fail.

    Args:
        settings: Application settings with Garmin credentials and token directory.
        supabase_client: Optional Supabase client for CI token persistence.

    Returns:
        An authenticated Garmin client instance.

    Raises:
        GarminConnectAuthenticationError: If credentials are invalid.
    """
    if supabase_client is not None:
        return _auth_supabase(settings, supabase_client)

    return _auth_filesystem(settings)


def _auth_supabase(settings: Settings, supabase_client: Client) -> Garmin:
    """Authenticate via Supabase-stored tokens (CI mode)."""
    token_string = load_tokens_from_supabase(supabase_client)

    if token_string is not None:
        log.info("garmin_auth_supabase_token_load")
        client = Garmin()
        client.login(token_string)
    else:
        log.info("garmin_auth_email_login_ci", email=settings.garmin_email)
        client = Garmin(settings.garmin_email, settings.garmin_password)
        client.login()

    # Save refreshed tokens immediately (before extraction stage)
    save_tokens_to_supabase(supabase_client, client)
    log.info("garmin_auth_supabase_token_saved")

    return client


def _auth_filesystem(settings: Settings) -> Garmin:
    """Authenticate via filesystem tokens (local dev mode)."""
    token_dir = os.path.expanduser(settings.garmin_token_dir)

    if os.path.isdir(token_dir):
        log.info("garmin_auth_token_load", token_dir=token_dir)
        client = Garmin()
        client.login(token_dir)
    else:
        log.info("garmin_auth_email_login", email=settings.garmin_email)
        client = Garmin(settings.garmin_email, settings.garmin_password)
        client.login()
        # Persist tokens for subsequent runs
        os.makedirs(token_dir, mode=0o700, exist_ok=True)
        client.garth.dump(token_dir)
        os.chmod(token_dir, 0o700)
        log.info("garmin_auth_tokens_saved", token_dir=token_dir)

    return client
