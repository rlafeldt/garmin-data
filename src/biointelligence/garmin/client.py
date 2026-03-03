"""Garmin Connect authentication with token persistence."""

import os

import structlog
from garminconnect import Garmin

from biointelligence.config import Settings

log = structlog.get_logger()


def get_authenticated_client(settings: Settings) -> Garmin:
    """Get an authenticated Garmin client, loading persisted tokens if available.

    Args:
        settings: Application settings with Garmin credentials and token directory.

    Returns:
        An authenticated Garmin client instance.

    Raises:
        GarminConnectAuthenticationError: If credentials are invalid.
    """
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
