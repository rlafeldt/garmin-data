"""YAML loading and Pydantic validation for health profiles."""

from __future__ import annotations

from pathlib import Path

import structlog
import yaml

from biointelligence.profile.models import HealthProfile

log = structlog.get_logger()


def load_health_profile(path: Path) -> HealthProfile:
    """Load and validate a health profile from a YAML file.

    Args:
        path: Path to the YAML health profile configuration file.

    Returns:
        A validated HealthProfile instance.

    Raises:
        FileNotFoundError: If the YAML file does not exist.
        pydantic.ValidationError: If the YAML content fails validation.
    """
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
