"""Definições de padrões de convergência para detecção de anomalias multi-métricas.

Cinco padrões detectam desvios simultâneos em múltiplas métricas de saúde
por 3+ dias consecutivos, usando linhas de base pessoais (média de 28 dias + desvio-padrão).
"""

from __future__ import annotations

from biointelligence.anomaly.models import AlertSeverity, ConvergencePattern, MetricCheck

CONVERGENCE_PATTERNS: list[ConvergencePattern] = [
    # Padrão 1: Convergência HRV + FC + Sono
    ConvergencePattern(
        name="hrv_hr_sleep",
        description=(
            "HRV em queda, frequência cardíaca de repouso elevada e qualidade de sono "
            "comprometida por 3+ dias consecutivos — indica estresse sistêmico ou início de doença."
        ),
        suggested_action=(
            "Priorize a recuperação: estenda o sono em 30-60 min, evite treino de alta intensidade "
            "e monitore sintomas de doença."
        ),
        metrics=[
            MetricCheck(metric_name="hrv_overnight_avg", direction="below", threshold_stddev=1.0),
            MetricCheck(metric_name="resting_hr", direction="above", threshold_stddev=1.0),
            MetricCheck(metric_name="sleep_score", direction="below", threshold_stddev=1.0),
        ],
        severity=AlertSeverity.CRITICAL,
    ),
    # Padrão 2: Sinais de overtraining
    ConvergencePattern(
        name="overtraining",
        description=(
            "Carga de treino elevada enquanto HRV cai e Body Battery não recupera "
            "por 3+ dias consecutivos — padrão clássico de overtraining."
        ),
        suggested_action=(
            "Considere um dia de descanso ou sessão leve em zona 1. Reduza o volume de "
            "treino em 30-50% nos próximos 2-3 dias."
        ),
        metrics=[
            MetricCheck(metric_name="training_load_7d", direction="above", threshold_stddev=1.0),
            MetricCheck(metric_name="hrv_overnight_avg", direction="below", threshold_stddev=1.0),
            MetricCheck(
                metric_name="body_battery_morning", direction="below", threshold_stddev=1.0,
            ),
        ],
        severity=AlertSeverity.CRITICAL,
    ),
    # Padrão 3: Acúmulo de débito de sono
    ConvergencePattern(
        name="sleep_debt",
        description=(
            "Score de sono, duração total e sono profundo em queda "
            "por 3+ dias consecutivos — débito de sono se acumulando."
        ),
        suggested_action=(
            "Antecipe o horário de dormir hoje. Evite cafeína após 14h e telas "
            "30 min antes de deitar. Considere um cochilo curto se possível."
        ),
        metrics=[
            MetricCheck(metric_name="sleep_score", direction="below", threshold_stddev=1.0),
            MetricCheck(metric_name="total_sleep_seconds", direction="below", threshold_stddev=1.0),
            MetricCheck(metric_name="deep_sleep_seconds", direction="below", threshold_stddev=1.0),
        ],
        severity=AlertSeverity.WARNING,
    ),
    # Padrão 4: Escalada de estresse
    # NOTA: body_battery_drain é uma métrica derivada (body_battery_max - body_battery_min),
    # tratada como caso especial no detector.
    ConvergencePattern(
        name="stress_escalation",
        description=(
            "Nível médio de estresse subindo, tempo de relaxamento caindo e drenagem de "
            "Body Battery acelerando por 3+ dias consecutivos — resposta ao estresse escalando."
        ),
        suggested_action=(
            "Inclua recuperação intencional: exercícios respiratórios, caminhada na natureza ou "
            "meditação. Reduza compromissos quando possível."
        ),
        metrics=[
            MetricCheck(metric_name="avg_stress_level", direction="above", threshold_stddev=1.0),
            MetricCheck(metric_name="rest_stress_minutes", direction="below", threshold_stddev=1.0),
            MetricCheck(metric_name="body_battery_drain", direction="above", threshold_stddev=1.0),
        ],
        severity=AlertSeverity.WARNING,
    ),
    # Padrão 5: Estagnação da recuperação
    ConvergencePattern(
        name="recovery_stall",
        description=(
            "Carga matinal do Body Battery baixa, frequência cardíaca de repouso subindo e "
            "HRV estagnado ou em queda por 3+ dias consecutivos — recuperação estagnada."
        ),
        suggested_action=(
            "Foque em higiene do sono e nutrição. Considere suplementação de magnésio "
            "e garanta ingestão adequada de proteína para recuperação."
        ),
        metrics=[
            MetricCheck(
                metric_name="body_battery_morning", direction="below", threshold_stddev=1.0,
            ),
            MetricCheck(metric_name="resting_hr", direction="above", threshold_stddev=1.0),
            MetricCheck(metric_name="hrv_overnight_avg", direction="below", threshold_stddev=1.0),
        ],
        severity=AlertSeverity.WARNING,
    ),
]
