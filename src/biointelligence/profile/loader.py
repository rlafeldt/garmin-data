"""Health profile loading: Supabase-first with YAML fallback."""

from __future__ import annotations

from pathlib import Path

import structlog
import yaml

from biointelligence.profile.models import HealthProfile
from biointelligence.profile.onboarding_mapper import map_onboarding_to_health_profile
from biointelligence.storage.supabase import get_supabase_client

log = structlog.get_logger()


def load_health_profile(
    path: Path, settings: "Settings | None" = None,
) -> HealthProfile:
    """Load health profile from Supabase onboarding data, with YAML fallback.

    Queries the onboarding_profiles table in Supabase first. If data exists,
    maps it to a HealthProfile using the onboarding mapper. If the query
    returns no data or fails, falls back to loading from the YAML file.

    Args:
        path: Path to the YAML health profile configuration file (fallback).
        settings: Optional settings override. Uses get_settings() if not
            provided.

    Returns:
        A validated HealthProfile instance.

    Raises:
        FileNotFoundError: If YAML fallback is needed and file does not exist.
        pydantic.ValidationError: If the loaded content fails validation.
    """
    if settings is None:
        from biointelligence.config import get_settings
        settings = get_settings()

    # Try Supabase first
    try:
        supabase_client = get_supabase_client(settings)
        response = (
            supabase_client.table("onboarding_profiles")
            .select("*")
            .limit(1)
            .execute()
        )
        if response.data:
            log.info("health_profile_loaded_from_supabase")
            return map_onboarding_to_health_profile(response.data[0])
        log.info("no_onboarding_data_in_supabase_falling_back_to_yaml")
    except Exception as exc:
        log.warning("supabase_profile_load_failed", error=str(exc))

    # YAML fallback
    log.info("loading_health_profile", path=str(path))

    with open(path) as f:
        raw = yaml.safe_load(f)

    profile = HealthProfile.model_validate(raw)
    log.info(
        "health_profile_loaded",
        sections=list(raw.keys()),
        supplements=len(profile.supplements),
        lab_values=len(profile.lab_values),
    )
    return profile
