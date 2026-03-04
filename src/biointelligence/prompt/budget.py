"""Token estimation and budget-aware section trimming.

Uses a ~4 characters per token heuristic (no external tokenizer dependency).
Trimming follows a priority order, removing lowest-priority sections first
while protecting critical sections (today's metrics and health profile).
"""

from __future__ import annotations

import structlog

log = structlog.get_logger()

# Section priority from lowest (trimmed first) to highest (trimmed last).
# The last two entries (health_profile, today_metrics) are NEVER trimmed.
SECTION_PRIORITY: list[str] = [
    "sports_science",
    "yesterday_activities",
    "trends_28d",
    "trends_7d",
    "anomalies",
    "analysis_directives",
    "output_format",
    "health_profile",
    "today_metrics",
]

# Sections that must never be removed regardless of budget pressure.
NEVER_TRIM: set[str] = {"health_profile", "today_metrics"}

# Default token budget (increased for 28-day trends and anomaly sections).
DEFAULT_TOKEN_BUDGET: int = 7000


def estimate_tokens(text: str) -> int:
    """Estimate token count using ~4 characters per token heuristic.

    Args:
        text: The text to estimate tokens for.

    Returns:
        Estimated token count.
    """
    return len(text) // 4


def trim_to_budget(
    sections: dict[str, str],
    budget: int = DEFAULT_TOKEN_BUDGET,
) -> tuple[dict[str, str], list[str]]:
    """Trim sections to fit within token budget.

    Iterates through SECTION_PRIORITY from lowest priority upward,
    removing sections until the total estimated tokens fits within budget.
    Never removes NEVER_TRIM sections.

    Args:
        sections: Dict mapping section tag names to their text content.
        budget: Maximum allowed token count.

    Returns:
        Tuple of (remaining sections dict, list of trimmed section names).
    """
    total_tokens = sum(estimate_tokens(content) for content in sections.values())

    if total_tokens <= budget:
        return sections, []

    remaining = dict(sections)
    trimmed: list[str] = []

    for section_name in SECTION_PRIORITY:
        if section_name in NEVER_TRIM:
            continue
        if section_name not in remaining:
            continue

        log.warning(
            "trimming_section",
            section=section_name,
            section_tokens=estimate_tokens(remaining[section_name]),
            total_tokens=total_tokens,
            budget=budget,
        )

        total_tokens -= estimate_tokens(remaining.pop(section_name))
        trimmed.append(section_name)

        if total_tokens <= budget:
            break

    return remaining, trimmed
