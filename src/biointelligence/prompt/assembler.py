"""Função principal de montagem do prompt.

Conecta o perfil de saúde, métricas do dia, tendências de 7 dias,
atividades do dia anterior, fundamentação em ciência do esporte,
diretivas de análise e o schema de saída DailyProtocol em um único
prompt com tags XML.
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
    lines: list[str] = [f"Data: {metrics.date.isoformat()}"]

    # Sono
    sleep_lines: list[str] = []
    if metrics.total_sleep_seconds is not None:
        hours = metrics.total_sleep_seconds // 3600
        minutes = (metrics.total_sleep_seconds % 3600) // 60
        sleep_lines.append(f"  Sono total: {hours}h {minutes}min")
    if metrics.deep_sleep_seconds is not None:
        h, m = divmod(metrics.deep_sleep_seconds, 3600)
        sleep_lines.append(f"  Sono profundo: {h}h {(m % 3600) // 60}min")
    if metrics.light_sleep_seconds is not None:
        h = metrics.light_sleep_seconds // 3600
        m = (metrics.light_sleep_seconds % 3600) // 60
        sleep_lines.append(f"  Sono leve: {h}h {m}min")
    if metrics.rem_sleep_seconds is not None:
        h = metrics.rem_sleep_seconds // 3600
        m = (metrics.rem_sleep_seconds % 3600) // 60
        sleep_lines.append(f"  Sono REM: {h}h {m}min")
    if metrics.awake_seconds is not None:
        sleep_lines.append(f"  Tempo acordado: {metrics.awake_seconds // 60}min")
    if metrics.sleep_score is not None:
        sleep_lines.append(f"  Score de sono: {metrics.sleep_score}")
    if sleep_lines:
        lines.append("Sono:")
        lines.extend(sleep_lines)

    # HRV
    hrv_lines: list[str] = []
    if metrics.hrv_overnight_avg is not None:
        hrv_lines.append(f"  Média noturna: {metrics.hrv_overnight_avg}")
    if metrics.hrv_overnight_max is not None:
        hrv_lines.append(f"  Máximo noturno: {metrics.hrv_overnight_max}")
    if metrics.hrv_status is not None:
        hrv_lines.append(f"  Status: {metrics.hrv_status}")
    if hrv_lines:
        lines.append("HRV:")
        lines.extend(hrv_lines)

    # Body Battery
    bb_lines: list[str] = []
    if metrics.body_battery_morning is not None:
        bb_lines.append(f"  Manhã: {metrics.body_battery_morning}")
    if metrics.body_battery_max is not None:
        bb_lines.append(f"  Máx: {metrics.body_battery_max}")
    if metrics.body_battery_min is not None:
        bb_lines.append(f"  Mín: {metrics.body_battery_min}")
    if bb_lines:
        lines.append("Body Battery:")
        lines.extend(bb_lines)

    # Frequência Cardíaca
    hr_lines: list[str] = []
    if metrics.resting_hr is not None:
        hr_lines.append(f"  Repouso: {metrics.resting_hr} bpm")
    if metrics.avg_hr is not None:
        hr_lines.append(f"  Média: {metrics.avg_hr} bpm")
    if metrics.max_hr is not None:
        hr_lines.append(f"  Máx: {metrics.max_hr} bpm")
    if hr_lines:
        lines.append("Frequência Cardíaca:")
        lines.extend(hr_lines)

    # Estresse
    stress_lines: list[str] = []
    if metrics.avg_stress_level is not None:
        stress_lines.append(f"  Nível médio: {metrics.avg_stress_level}")
    if metrics.high_stress_minutes is not None:
        stress_lines.append(f"  Estresse alto: {metrics.high_stress_minutes}min")
    if metrics.rest_stress_minutes is not None:
        stress_lines.append(f"  Estresse em repouso: {metrics.rest_stress_minutes}min")
    if stress_lines:
        lines.append("Estresse:")
        lines.extend(stress_lines)

    # Treino
    training_lines: list[str] = []
    if metrics.training_load_7d is not None:
        training_lines.append(f"  Carga 7 dias: {metrics.training_load_7d}")
    if metrics.training_status is not None:
        training_lines.append(f"  Status: {metrics.training_status}")
    if metrics.vo2_max is not None:
        training_lines.append(f"  VO2 Max: {metrics.vo2_max}")
    if training_lines:
        lines.append("Treino:")
        lines.extend(training_lines)

    # Geral
    general_lines: list[str] = []
    if metrics.steps is not None:
        general_lines.append(f"  Passos: {metrics.steps}")
    if metrics.calories_total is not None:
        general_lines.append(f"  Calorias totais: {metrics.calories_total}")
    if metrics.calories_active is not None:
        general_lines.append(f"  Calorias ativas: {metrics.calories_active}")
    if metrics.intensity_minutes is not None:
        general_lines.append(f"  Minutos de intensidade: {metrics.intensity_minutes}")
    if metrics.spo2_avg is not None:
        general_lines.append(f"  SpO2 média: {metrics.spo2_avg}%")
    if metrics.respiration_rate_avg is not None:
        general_lines.append(f"  Taxa respiratória: {metrics.respiration_rate_avg}")
    if general_lines:
        lines.append("Geral:")
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
            "Dados insuficientes para análise de tendências "
            f"(menos de 4 dias de dados disponíveis). "
            f"Pontos de dados: {trends.data_points}."
        )

    lines: list[str] = [
        f"Janela: {trends.window_start.isoformat()} a {trends.window_end.isoformat()}",
        f"Pontos de dados: {trends.data_points}",
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
            "Tendências de 28 dias: dados insuficientes "
            "(menos de 14 dias disponíveis)."
        )

    all_insufficient = all(
        m.direction == TrendDirection.INSUFFICIENT for m in trends.metrics.values()
    )
    if all_insufficient:
        return (
            "Tendências de 28 dias: dados insuficientes "
            f"(menos de 14 dias disponíveis). "
            f"Pontos de dados: {trends.data_points}."
        )

    lines: list[str] = [
        f"Janela: {trends.window_start.isoformat()} a {trends.window_end.isoformat()}",
        f"Pontos de dados: {trends.data_points}",
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
            "Nenhuma anomalia detectada. "
            "Todas as métricas dentro das linhas de base pessoais normais."
        )

    lines: list[str] = [
        f"ANOMALIAS DETECTADAS ({len(anomaly_result.alerts)} alertas):",
        "",
    ]
    for alert in anomaly_result.alerts:
        lines.append(
            f"- [{alert.severity.value.upper()}] {alert.title}: {alert.description}"
        )

    lines.append("")
    lines.append(
        "Interprete cada anomalia no contexto clínico. "
        "Preencha o campo de alertas na resposta conforme necessário."
    )

    return "\n".join(lines)


def _format_activities(activities: list[Activity]) -> str:
    """Format yesterday's activities as human-readable text.

    If no activities, outputs a note about no recorded activities.
    """
    if not activities:
        return "Nenhuma atividade registrada ontem."

    lines: list[str] = []
    for act in activities:
        parts = [f"{act.activity_type}"]
        if act.name:
            parts[0] += f": {act.name}"
        if act.duration_seconds is not None:
            parts.append(f"duração: {act.duration_seconds // 60}min")
        if act.avg_hr is not None:
            parts.append(f"fc_média: {act.avg_hr}")
        if act.max_hr is not None:
            parts.append(f"fc_máx: {act.max_hr}")
        if act.calories is not None:
            parts.append(f"calorias: {act.calories}")
        if act.training_effect_aerobic is not None:
            parts.append(f"efeito_aeróbico: {act.training_effect_aerobic}")
        if act.training_effect_anaerobic is not None:
            parts.append(f"efeito_anaeróbico: {act.training_effect_anaerobic}")
        lines.append(" | ".join(parts))

    return "\n".join(lines)


def _format_profile(profile: HealthProfile) -> str:
    """Format health profile as prompt-friendly text.

    Uses model_dump(mode='json') for consistent serialization, then
    formats as readable text with sections.
    """
    data = profile.model_dump(mode="json")
    lines: list[str] = []

    # Biometria
    bio = data["biometrics"]
    lines.append("Biometria:")
    lines.append(f"  Idade: {bio['age']}")
    lines.append(f"  Sexo: {bio['sex']}")
    lines.append(f"  Peso: {bio['weight_kg']} kg")
    lines.append(f"  Altura: {bio['height_cm']} cm")
    if bio.get("body_fat_pct") is not None:
        lines.append(f"  Gordura corporal: {bio['body_fat_pct']}%")
    if bio.get("primary_sport") is not None:
        lines.append(f"  Esporte principal: {bio['primary_sport']}")
    if bio.get("primary_goals"):
        lines.append(f"  Objetivos: {', '.join(bio['primary_goals'])}")

    # Contexto Hormonal (onboarding)
    if bio.get("hormonal_status") is not None:
        lines.append("Contexto Hormonal:")
        lines.append(f"  Status: {bio['hormonal_status']}")
        if bio.get("cycle_phase") is not None:
            lines.append(f"  Fase do ciclo: {bio['cycle_phase']}")

    # Treino
    training = data["training"]
    lines.append("Contexto de Treino:")
    lines.append(f"  Fase: {training['phase']}")
    lines.append(f"  Volume semanal: {training['weekly_volume_hours']} horas")
    lines.append(f"  Modalidades preferidas: {', '.join(training['preferred_types'])}")
    for goal in training.get("race_goals", []):
        lines.append(f"  Meta de competição: {goal['event']} ({goal['date']}, prioridade {goal['priority']})")
    for inj in training.get("injury_history", []):
        note = f" - {inj['notes']}" if inj.get("notes") else ""
        lines.append(f"  Lesão: {inj['area']} ({inj['status']}{note})")

    # Médico
    medical = data["medical"]
    if medical.get("conditions"):
        lines.append(f"Condições médicas: {', '.join(medical['conditions'])}")
    if medical.get("medications"):
        lines.append(f"Medicamentos: {', '.join(medical['medications'])}")
    if medical.get("allergies"):
        lines.append(f"Alergias: {', '.join(medical['allergies'])}")

    # Metabólico
    metabolic = data["metabolic"]
    if metabolic.get("resting_metabolic_rate") is not None:
        lines.append(f"Taxa metabólica de repouso: {metabolic['resting_metabolic_rate']} kcal")
    if metabolic.get("glucose_response"):
        lines.append(f"Resposta glicêmica: {metabolic['glucose_response']}")
    if metabolic.get("dietary_pattern") is not None:
        lines.append(f"  Padrão alimentar: {metabolic['dietary_pattern']}")
    if metabolic.get("eating_window") is not None:
        lines.append(f"  Janela alimentar: {metabolic['eating_window']}")
    if metabolic.get("caffeine_intake") is not None:
        lines.append(f"  Consumo de cafeína: {metabolic['caffeine_intake']}")
    if metabolic.get("caffeine_cutoff") is not None:
        lines.append(f"  Corte de cafeína: {metabolic['caffeine_cutoff']}")
    if metabolic.get("alcohol_consumption") is not None:
        lines.append(f"  Consumo de álcool: {metabolic['alcohol_consumption']}")
    if metabolic.get("metabolic_flexibility_signals") is not None:
        lines.append("  Sinais de Flexibilidade Metabólica:")
        for signal_name, signal_value in metabolic["metabolic_flexibility_signals"].items():
            lines.append(f"    {signal_name}: {signal_value}")

    # Dieta
    diet = data["diet"]
    lines.append(f"Preferência alimentar: {diet['preference']}")
    if diet.get("restrictions"):
        lines.append(f"  Restrições: {', '.join(diet['restrictions'])}")
    if diet.get("meal_timing"):
        lines.append(f"  Horário das refeições: {diet['meal_timing']}")

    # Suplementos
    if data.get("supplements"):
        lines.append("Suplementos:")
        for supp in data["supplements"]:
            line = f"  {supp['name']}: {supp['dose']} ({supp['form']}) - {supp['timing']}"
            if supp.get("condition"):
                line += f" [Condição: {supp['condition']}]"
            lines.append(line)

    # Contexto de sono
    sleep = data.get("sleep_context", {})
    sleep_parts: list[str] = []
    if sleep.get("chronotype"):
        sleep_parts.append(f"cronotipo: {sleep['chronotype']}")
    if sleep.get("target_bedtime"):
        sleep_parts.append(f"horário-alvo para dormir: {sleep['target_bedtime']}")
    if sleep.get("target_wake"):
        sleep_parts.append(f"horário-alvo para acordar: {sleep['target_wake']}")
    if sleep.get("environment_notes"):
        sleep_parts.append(f"ambiente: {sleep['environment_notes']}")
    if sleep_parts:
        lines.append("Contexto de sono: " + ", ".join(sleep_parts))
    if sleep.get("sleep_schedule_consistency") is not None:
        lines.append(f"  Consistência do horário de sono: {sleep['sleep_schedule_consistency']}")
    if sleep.get("average_sleep_duration") is not None:
        lines.append(f"  Duração média de sono: {sleep['average_sleep_duration']}")
    if sleep.get("subjective_recovery_waking") is not None:
        lines.append(f"  Recuperação ao acordar: {sleep['subjective_recovery_waking']}/10")

    # Exames laboratoriais
    if data.get("lab_values"):
        lines.append("Exames Laboratoriais:")
        for name, lab in data["lab_values"].items():
            lines.append(
                f"  {name}: {lab['value']} {lab['unit']} "
                f"(data: {lab['date']}, faixa: {lab['range']})"
            )

    return "\n".join(lines)


def _format_output_schema() -> str:
    """Generate the DailyProtocol JSON schema with instructions.

    Uses Pydantic's model_json_schema() to auto-generate the schema.
    """
    schema = DailyProtocol.model_json_schema()
    schema_str = json.dumps(schema, indent=2)

    return (
        "Retorne sua análise como JSON válido seguindo o esquema abaixo. "
        "Não inclua nenhum texto fora do objeto JSON.\n\n"
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
    # Build analysis directives (always include anomaly interpretation)
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
