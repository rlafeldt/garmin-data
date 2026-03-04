"""Main prompt assembly function.

Wires together health profile, today's metrics, 7-day trends,
yesterday's activities, sports science grounding, analysis directives,
and the DailyProtocol output schema into a single XML-tagged prompt.
"""

from __future__ import annotations

import json

import structlog

from biointelligence.anomaly.models import AnomalyResult
from biointelligence.garmin.models import Activity, DailyMetrics
from biointelligence.profile.models import HealthProfile
from biointelligence.prompt.budget import DEFAULT_TOKEN_BUDGET, estimate_tokens, trim_to_budget
from biointelligence.prompt.models import AssembledPrompt, DailyProtocol, PromptContext
from biointelligence.prompt.templates import (
    ANALYSIS_DIRECTIVES,
    ANOMALY_INTERPRETATION_DIRECTIVES,
    SPORTS_SCIENCE_GROUNDING,
)
from biointelligence.trends.models import TrendDirection, TrendResult

log = structlog.get_logger()

# Ordered section tags for the assembled prompt.
SECTION_ORDER: list[str] = [
    "health_profile",
    "today_metrics",
    "trends_7d",
    "trends_28d",
    "anomalies",
    "yesterday_activities",
    "sports_science",
    "analysis_directives",
    "output_format",
]


def _format_metrics(metrics: DailyMetrics) -> str:
    """Format today's metrics as human-readable key-value text.

    Groups metrics by category and skips None values. Converts
    total_sleep_seconds to hours:minutes for readability.
    """
    lines: list[str] = [f"Date: {metrics.date.isoformat()}"]

    # Sleep
    sleep_lines: list[str] = []
    if metrics.total_sleep_seconds is not None:
        hours = metrics.total_sleep_seconds // 3600
        minutes = (metrics.total_sleep_seconds % 3600) // 60
        sleep_lines.append(f"  Total sleep: {hours}h {minutes}min")
    if metrics.deep_sleep_seconds is not None:
        h, m = divmod(metrics.deep_sleep_seconds, 3600)
        sleep_lines.append(f"  Deep sleep: {h}h {(m % 3600) // 60}min")
    if metrics.light_sleep_seconds is not None:
        h = metrics.light_sleep_seconds // 3600
        m = (metrics.light_sleep_seconds % 3600) // 60
        sleep_lines.append(f"  Light sleep: {h}h {m}min")
    if metrics.rem_sleep_seconds is not None:
        h = metrics.rem_sleep_seconds // 3600
        m = (metrics.rem_sleep_seconds % 3600) // 60
        sleep_lines.append(f"  REM sleep: {h}h {m}min")
    if metrics.awake_seconds is not None:
        sleep_lines.append(f"  Awake time: {metrics.awake_seconds // 60}min")
    if metrics.sleep_score is not None:
        sleep_lines.append(f"  Sleep score: {metrics.sleep_score}")
    if sleep_lines:
        lines.append("Sleep:")
        lines.extend(sleep_lines)

    # HRV
    hrv_lines: list[str] = []
    if metrics.hrv_overnight_avg is not None:
        hrv_lines.append(f"  Overnight avg: {metrics.hrv_overnight_avg}")
    if metrics.hrv_overnight_max is not None:
        hrv_lines.append(f"  Overnight max: {metrics.hrv_overnight_max}")
    if metrics.hrv_status is not None:
        hrv_lines.append(f"  Status: {metrics.hrv_status}")
    if hrv_lines:
        lines.append("HRV:")
        lines.extend(hrv_lines)

    # Body Battery
    bb_lines: list[str] = []
    if metrics.body_battery_morning is not None:
        bb_lines.append(f"  Morning: {metrics.body_battery_morning}")
    if metrics.body_battery_max is not None:
        bb_lines.append(f"  Max: {metrics.body_battery_max}")
    if metrics.body_battery_min is not None:
        bb_lines.append(f"  Min: {metrics.body_battery_min}")
    if bb_lines:
        lines.append("Body Battery:")
        lines.extend(bb_lines)

    # Heart Rate
    hr_lines: list[str] = []
    if metrics.resting_hr is not None:
        hr_lines.append(f"  Resting: {metrics.resting_hr} bpm")
    if metrics.avg_hr is not None:
        hr_lines.append(f"  Average: {metrics.avg_hr} bpm")
    if metrics.max_hr is not None:
        hr_lines.append(f"  Max: {metrics.max_hr} bpm")
    if hr_lines:
        lines.append("Heart Rate:")
        lines.extend(hr_lines)

    # Stress
    stress_lines: list[str] = []
    if metrics.avg_stress_level is not None:
        stress_lines.append(f"  Average level: {metrics.avg_stress_level}")
    if metrics.high_stress_minutes is not None:
        stress_lines.append(f"  High stress: {metrics.high_stress_minutes}min")
    if metrics.rest_stress_minutes is not None:
        stress_lines.append(f"  Rest stress: {metrics.rest_stress_minutes}min")
    if stress_lines:
        lines.append("Stress:")
        lines.extend(stress_lines)

    # Training
    training_lines: list[str] = []
    if metrics.training_load_7d is not None:
        training_lines.append(f"  7-day load: {metrics.training_load_7d}")
    if metrics.training_status is not None:
        training_lines.append(f"  Status: {metrics.training_status}")
    if metrics.vo2_max is not None:
        training_lines.append(f"  VO2 Max: {metrics.vo2_max}")
    if training_lines:
        lines.append("Training:")
        lines.extend(training_lines)

    # General
    general_lines: list[str] = []
    if metrics.steps is not None:
        general_lines.append(f"  Steps: {metrics.steps}")
    if metrics.calories_total is not None:
        general_lines.append(f"  Total calories: {metrics.calories_total}")
    if metrics.calories_active is not None:
        general_lines.append(f"  Active calories: {metrics.calories_active}")
    if metrics.intensity_minutes is not None:
        general_lines.append(f"  Intensity minutes: {metrics.intensity_minutes}")
    if metrics.spo2_avg is not None:
        general_lines.append(f"  SpO2 avg: {metrics.spo2_avg}%")
    if metrics.respiration_rate_avg is not None:
        general_lines.append(f"  Respiration rate: {metrics.respiration_rate_avg}")
    if general_lines:
        lines.append("General:")
        lines.extend(general_lines)

    return "\n".join(lines)


def _format_trends(trends: TrendResult) -> str:
    """Format 7-day trend data as human-readable text.

    If all metrics have INSUFFICIENT direction, outputs a note about
    insufficient data instead.
    """
    all_insufficient = all(
        m.direction == TrendDirection.INSUFFICIENT for m in trends.metrics.values()
    )
    if all_insufficient:
        return (
            "Insufficient data for trend analysis "
            f"(fewer than 4 days of data available). "
            f"Data points: {trends.data_points}."
        )

    lines: list[str] = [
        f"Window: {trends.window_start.isoformat()} to {trends.window_end.isoformat()}",
        f"Data points: {trends.data_points}",
        "",
    ]

    for name, metric in sorted(trends.metrics.items()):
        parts = [f"{name}:"]
        if metric.avg is not None:
            parts.append(f"avg={metric.avg:.1f}")
        if metric.min_val is not None:
            parts.append(f"min={metric.min_val:.1f}")
        if metric.max_val is not None:
            parts.append(f"max={metric.max_val:.1f}")
        parts.append(f"direction={metric.direction.value}")
        lines.append(" ".join(parts))

    return "\n".join(lines)


def _format_extended_trends(trends: TrendResult | None) -> str:
    """Format 28-day extended trend data as compact summary.

    Includes mean, stddev, min, max, and direction per metric.
    Returns an "insufficient data" message when trends is None.
    """
    if trends is None:
        return (
            "28-day trends: Insufficient data "
            "(fewer than 14 days available)."
        )

    all_insufficient = all(
        m.direction == TrendDirection.INSUFFICIENT for m in trends.metrics.values()
    )
    if all_insufficient:
        return (
            "28-day trends: Insufficient data "
            f"(fewer than 14 days available). "
            f"Data points: {trends.data_points}."
        )

    lines: list[str] = [
        f"Window: {trends.window_start.isoformat()} to {trends.window_end.isoformat()}",
        f"Data points: {trends.data_points}",
        "",
    ]

    for name, metric in sorted(trends.metrics.items()):
        if metric.direction == TrendDirection.INSUFFICIENT:
            continue
        parts = [f"{name}:"]
        if metric.avg is not None:
            parts.append(f"avg={metric.avg:.1f}")
        if metric.stddev is not None:
            parts.append(f"stddev={metric.stddev:.1f}")
        if metric.min_val is not None:
            parts.append(f"min={metric.min_val:.1f}")
        if metric.max_val is not None:
            parts.append(f"max={metric.max_val:.1f}")
        parts.append(f"direction={metric.direction.value}")
        lines.append(" ".join(parts))

    return "\n".join(lines)


def _format_anomalies(anomaly_result: AnomalyResult | None) -> str:
    """Format anomaly detection results for the prompt.

    Lists detected alerts with severity, title, and description.
    Returns "no anomalies detected" when result is None or empty.
    """
    if anomaly_result is None or not anomaly_result.alerts:
        return (
            "No anomalies detected. "
            "All metrics within normal personal baselines."
        )

    lines: list[str] = [
        f"DETECTED ANOMALIES ({len(anomaly_result.alerts)} alerts):",
        "",
    ]
    for alert in anomaly_result.alerts:
        lines.append(
            f"- [{alert.severity.value.upper()}] {alert.title}: {alert.description}"
        )

    lines.append("")
    lines.append(
        "Interpret each anomaly in clinical context. "
        "Populate the alerts field in your response accordingly."
    )

    return "\n".join(lines)


def _format_activities(activities: list[Activity]) -> str:
    """Format yesterday's activities as human-readable text.

    If no activities, outputs a note about no recorded activities.
    """
    if not activities:
        return "No activities recorded yesterday."

    lines: list[str] = []
    for act in activities:
        parts = [f"{act.activity_type}"]
        if act.name:
            parts[0] += f": {act.name}"
        if act.duration_seconds is not None:
            parts.append(f"duration: {act.duration_seconds // 60}min")
        if act.avg_hr is not None:
            parts.append(f"avg_hr: {act.avg_hr}")
        if act.max_hr is not None:
            parts.append(f"max_hr: {act.max_hr}")
        if act.calories is not None:
            parts.append(f"calories: {act.calories}")
        if act.training_effect_aerobic is not None:
            parts.append(f"aerobic_effect: {act.training_effect_aerobic}")
        if act.training_effect_anaerobic is not None:
            parts.append(f"anaerobic_effect: {act.training_effect_anaerobic}")
        lines.append(" | ".join(parts))

    return "\n".join(lines)


def _format_profile(profile: HealthProfile) -> str:
    """Format health profile as prompt-friendly text.

    Uses model_dump(mode='json') for consistent serialization, then
    formats as readable text with sections.
    """
    data = profile.model_dump(mode="json")
    lines: list[str] = []

    # Biometrics
    bio = data["biometrics"]
    lines.append("Biometrics:")
    lines.append(f"  Age: {bio['age']}")
    lines.append(f"  Sex: {bio['sex']}")
    lines.append(f"  Weight: {bio['weight_kg']} kg")
    lines.append(f"  Height: {bio['height_cm']} cm")
    if bio.get("body_fat_pct") is not None:
        lines.append(f"  Body fat: {bio['body_fat_pct']}%")

    # Training
    training = data["training"]
    lines.append("Training Context:")
    lines.append(f"  Phase: {training['phase']}")
    lines.append(f"  Weekly volume: {training['weekly_volume_hours']} hours")
    lines.append(f"  Preferred types: {', '.join(training['preferred_types'])}")
    for goal in training.get("race_goals", []):
        lines.append(f"  Race goal: {goal['event']} ({goal['date']}, priority {goal['priority']})")
    for inj in training.get("injury_history", []):
        note = f" - {inj['notes']}" if inj.get("notes") else ""
        lines.append(f"  Injury: {inj['area']} ({inj['status']}{note})")

    # Medical
    medical = data["medical"]
    if medical.get("conditions"):
        lines.append(f"Medical conditions: {', '.join(medical['conditions'])}")
    if medical.get("medications"):
        lines.append(f"Medications: {', '.join(medical['medications'])}")
    if medical.get("allergies"):
        lines.append(f"Allergies: {', '.join(medical['allergies'])}")

    # Metabolic
    metabolic = data["metabolic"]
    if metabolic.get("resting_metabolic_rate") is not None:
        lines.append(f"Resting metabolic rate: {metabolic['resting_metabolic_rate']} kcal")
    if metabolic.get("glucose_response"):
        lines.append(f"Glucose response: {metabolic['glucose_response']}")

    # Diet
    diet = data["diet"]
    lines.append(f"Diet preference: {diet['preference']}")
    if diet.get("restrictions"):
        lines.append(f"  Restrictions: {', '.join(diet['restrictions'])}")
    if diet.get("meal_timing"):
        lines.append(f"  Meal timing: {diet['meal_timing']}")

    # Supplements
    if data.get("supplements"):
        lines.append("Supplements:")
        for supp in data["supplements"]:
            line = f"  {supp['name']}: {supp['dose']} ({supp['form']}) - {supp['timing']}"
            if supp.get("condition"):
                line += f" [Condition: {supp['condition']}]"
            lines.append(line)

    # Sleep context
    sleep = data.get("sleep_context", {})
    sleep_parts: list[str] = []
    if sleep.get("chronotype"):
        sleep_parts.append(f"chronotype: {sleep['chronotype']}")
    if sleep.get("target_bedtime"):
        sleep_parts.append(f"target bedtime: {sleep['target_bedtime']}")
    if sleep.get("target_wake"):
        sleep_parts.append(f"target wake: {sleep['target_wake']}")
    if sleep.get("environment_notes"):
        sleep_parts.append(f"environment: {sleep['environment_notes']}")
    if sleep_parts:
        lines.append("Sleep context: " + ", ".join(sleep_parts))

    # Lab values
    if data.get("lab_values"):
        lines.append("Lab Values:")
        for name, lab in data["lab_values"].items():
            lines.append(
                f"  {name}: {lab['value']} {lab['unit']} "
                f"(tested: {lab['date']}, range: {lab['range']})"
            )

    return "\n".join(lines)


def _format_output_schema() -> str:
    """Generate the DailyProtocol JSON schema with instructions.

    Uses Pydantic's model_json_schema() to auto-generate the schema.
    """
    schema = DailyProtocol.model_json_schema()
    schema_str = json.dumps(schema, indent=2)

    return (
        "Return your analysis as valid JSON matching the following schema. "
        "Do not include any text outside the JSON object.\n\n"
        f"Schema: DailyProtocol\n{schema_str}"
    )


def assemble_prompt(
    context: PromptContext,
    token_budget: int = DEFAULT_TOKEN_BUDGET,
) -> AssembledPrompt:
    """Assemble a structured Claude prompt from all data sources.

    Builds XML-tagged sections for health profile, today's metrics, 7-day
    trends, yesterday's activities, sports science grounding, analysis
    directives, and the DailyProtocol output schema. Applies token budget
    enforcement via priority-based trimming.

    Args:
        context: All data sources needed for prompt assembly.
        token_budget: Maximum allowed estimated tokens.

    Returns:
        AssembledPrompt with the full text, token estimate, and section metadata.
    """
    # Build analysis directives, appending anomaly interpretation when anomalies exist
    has_anomalies = (
        context.anomaly_result is not None
        and len(context.anomaly_result.alerts) > 0
    )
    directives = ANALYSIS_DIRECTIVES
    if has_anomalies:
        directives = ANALYSIS_DIRECTIVES + "\n\n" + ANOMALY_INTERPRETATION_DIRECTIVES

    # Build sections dict
    sections: dict[str, str] = {
        "health_profile": _format_profile(context.profile),
        "today_metrics": _format_metrics(context.today_metrics),
        "trends_7d": _format_trends(context.trends),
        "trends_28d": _format_extended_trends(context.extended_trends),
        "anomalies": _format_anomalies(context.anomaly_result),
        "yesterday_activities": _format_activities(context.activities),
        "sports_science": SPORTS_SCIENCE_GROUNDING,
        "analysis_directives": directives,
        "output_format": _format_output_schema(),
    }

    # Apply budget trimming
    remaining, trimmed = trim_to_budget(sections, budget=token_budget)

    # Assemble final text in defined order
    parts: list[str] = []
    for tag in SECTION_ORDER:
        if tag in remaining:
            parts.append(f"<{tag}>\n{remaining[tag]}\n</{tag}>")

    text = "\n\n".join(parts)
    tokens = estimate_tokens(text)

    sections_included = [tag for tag in SECTION_ORDER if tag in remaining]

    log.info(
        "prompt_assembled",
        estimated_tokens=tokens,
        sections_included=sections_included,
        sections_trimmed=trimmed,
        target_date=context.target_date.isoformat(),
    )

    return AssembledPrompt(
        text=text,
        estimated_tokens=tokens,
        sections_included=sections_included,
        sections_trimmed=trimmed,
    )
