"""Tests for prompt assembly, models, templates, and token budget."""

from __future__ import annotations

import json
from datetime import date

import pytest

from biointelligence.garmin.models import Activity, DailyMetrics
from biointelligence.profile.models import (
    Biometrics,
    DietPreferences,
    HealthProfile,
    LabValue,
    MedicalHistory,
    MetabolicProfile,
    SleepContext,
    Supplement,
    TrainingContext,
)
from biointelligence.anomaly.models import Alert, AlertSeverity, AnomalyResult
from biointelligence.prompt.assembler import assemble_prompt
from biointelligence.prompt.budget import (
    DEFAULT_TOKEN_BUDGET,
    NEVER_TRIM,
    SECTION_PRIORITY,
    estimate_tokens,
    trim_to_budget,
)
from biointelligence.prompt.models import (
    AssembledPrompt,
    DailyProtocol,
    NutritionGuidance,
    PromptContext,
    RecoveryAssessment,
    SleepAnalysis,
    SupplementationPlan,
    TrainingRecommendation,
)
from biointelligence.prompt.templates import (
    ANALYSIS_DIRECTIVES,
    SPORTS_SCIENCE_GROUNDING,
)
from biointelligence.trends.models import MetricTrend, TrendDirection, TrendResult


# ---------------------------------------------------------------------------
# Token estimation tests
# ---------------------------------------------------------------------------


class TestEstimateTokens:
    """Test the token estimation heuristic."""

    def test_returns_len_div_4_for_various_lengths(self) -> None:
        assert estimate_tokens("a" * 100) == 25
        assert estimate_tokens("b" * 400) == 100
        assert estimate_tokens("c" * 1000) == 250

    def test_handles_empty_string(self) -> None:
        assert estimate_tokens("") == 0


# ---------------------------------------------------------------------------
# Budget trimming tests
# ---------------------------------------------------------------------------


class TestTrimToBudget:
    """Test token-budget-aware section trimming."""

    def test_under_budget_returns_all_sections_unchanged(self) -> None:
        sections = {"today_metrics": "short", "health_profile": "short"}
        remaining, trimmed = trim_to_budget(sections, budget=1000)
        assert remaining == sections
        assert trimmed == []

    def test_removes_lowest_priority_section_first_when_over_budget(self) -> None:
        sections = {
            "today_metrics": "x" * 100,
            "health_profile": "x" * 100,
            "sports_science": "x" * 400,
        }
        # Budget so tight that sports_science must be removed
        remaining, trimmed = trim_to_budget(sections, budget=60)
        assert "sports_science" in trimmed
        assert "sports_science" not in remaining

    def test_trim_priority_order(self) -> None:
        """Verify trimming follows: sports_science first, then yesterday_activities, then trends_7d."""
        sections = {
            "today_metrics": "x" * 40,
            "health_profile": "x" * 40,
            "sports_science": "x" * 200,
            "yesterday_activities": "x" * 200,
            "trends_7d": "x" * 200,
        }
        # Budget allows metrics + profile + one more section
        remaining, trimmed = trim_to_budget(sections, budget=100)
        # sports_science should be trimmed first
        assert trimmed[0] == "sports_science"
        # yesterday_activities should be trimmed second
        assert trimmed[1] == "yesterday_activities"

    def test_never_removes_today_metrics_or_health_profile(self) -> None:
        sections = {
            "today_metrics": "x" * 200,
            "health_profile": "x" * 200,
            "sports_science": "x" * 200,
            "yesterday_activities": "x" * 200,
            "trends_7d": "x" * 200,
        }
        # Even with very tight budget, protected sections stay
        remaining, trimmed = trim_to_budget(sections, budget=10)
        assert "today_metrics" in remaining
        assert "health_profile" in remaining
        assert "today_metrics" not in trimmed
        assert "health_profile" not in trimmed


# ---------------------------------------------------------------------------
# DailyProtocol model tests
# ---------------------------------------------------------------------------


class TestDailyProtocol:
    """Test the DailyProtocol output schema model."""

    def test_validates_with_all_domains(self) -> None:
        protocol = DailyProtocol(
            date="2026-03-03",
            training=TrainingRecommendation(
                headline="Moderate training day",
                readiness_score=8,
                readiness_summary="Well recovered",
                recommended_intensity="moderate",
                recommended_type="cycling",
                recommended_duration_minutes=60,
                training_load_assessment="Balanced",
                reasoning="Good HRV and sleep",
            ),
            recovery=RecoveryAssessment(
                headline="Full recovery indicated",
                recovery_status="good",
                hrv_interpretation="Above baseline",
                body_battery_assessment="High morning charge",
                stress_impact="Low",
                recommendations=["Light stretching"],
                reasoning="Metrics indicate full recovery",
            ),
            sleep=SleepAnalysis(
                headline="Good sleep quality",
                quality_assessment="Good",
                architecture_notes="Adequate deep sleep",
                optimization_tips=["Maintain consistent bedtime"],
                reasoning="Sleep score above target",
            ),
            nutrition=NutritionGuidance(
                headline="Balanced nutrition day",
                caloric_target="2400 kcal",
                macro_focus="Balanced",
                hydration_target="3L",
                meal_timing_notes="Pre-workout carbs",
                reasoning="Moderate training day",
            ),
            supplementation=SupplementationPlan(
                headline="Standard dosing",
                adjustments=["Standard dosing"],
                timing_notes="Evening magnesium",
                reasoning="No special adjustments needed",
            ),
            overall_summary="Good day for moderate training",
        )
        assert protocol.training.readiness_score == 8
        assert protocol.date == "2026-03-03"
        assert protocol.data_quality_notes is None

    def test_model_json_schema_produces_valid_json(self) -> None:
        schema = DailyProtocol.model_json_schema()
        assert isinstance(schema, dict)
        # Should be serializable to JSON string
        schema_str = json.dumps(schema)
        assert len(schema_str) > 0
        # Should contain key fields
        assert "training" in schema_str
        assert "recovery" in schema_str
        assert "sleep" in schema_str
        assert "nutrition" in schema_str
        assert "supplementation" in schema_str


# ---------------------------------------------------------------------------
# Sports science grounding and directives tests
# ---------------------------------------------------------------------------


class TestSportsScienceGrounding:
    """Test that sports science grounding covers required frameworks."""

    def test_contains_hrv_interpretation(self) -> None:
        assert "HRV" in SPORTS_SCIENCE_GROUNDING or "hrv" in SPORTS_SCIENCE_GROUNDING.lower()

    def test_contains_sleep_architecture(self) -> None:
        lower = SPORTS_SCIENCE_GROUNDING.lower()
        assert "sleep" in lower
        assert "deep sleep" in lower or "rem" in lower

    def test_contains_acwr(self) -> None:
        lower = SPORTS_SCIENCE_GROUNDING.lower()
        assert "acute" in lower or "acwr" in lower
        assert "0.8" in SPORTS_SCIENCE_GROUNDING or "1.3" in SPORTS_SCIENCE_GROUNDING

    def test_contains_periodization(self) -> None:
        lower = SPORTS_SCIENCE_GROUNDING.lower()
        assert "periodization" in lower or "base" in lower


class TestAnalysisDirectives:
    """Test that analysis directives cover all 5 domains."""

    def test_contains_training_section(self) -> None:
        lower = ANALYSIS_DIRECTIVES.lower()
        assert "training" in lower

    def test_contains_recovery_section(self) -> None:
        lower = ANALYSIS_DIRECTIVES.lower()
        assert "recovery" in lower

    def test_contains_sleep_section(self) -> None:
        lower = ANALYSIS_DIRECTIVES.lower()
        assert "sleep" in lower

    def test_contains_nutrition_section(self) -> None:
        lower = ANALYSIS_DIRECTIVES.lower()
        assert "nutrition" in lower

    def test_contains_supplementation_section(self) -> None:
        lower = ANALYSIS_DIRECTIVES.lower()
        assert "supplementation" in lower or "supplement" in lower


# ---------------------------------------------------------------------------
# Test fixtures for assembler tests
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_profile() -> HealthProfile:
    """Create a mock health profile for testing."""
    return HealthProfile(
        biometrics=Biometrics(age=35, sex="male", weight_kg=82.0, height_cm=183.0, body_fat_pct=15.5),
        training=TrainingContext(
            phase="build",
            weekly_volume_hours=8.0,
            preferred_types=["cycling", "strength_training"],
        ),
        medical=MedicalHistory(),
        metabolic=MetabolicProfile(resting_metabolic_rate=1850, glucose_response="normal"),
        diet=DietPreferences(preference="balanced", meal_timing="3 meals + pre/post workout"),
        supplements=[
            Supplement(
                name="magnesium_glycinate",
                dose="400mg",
                form="glycinate",
                timing="evening",
                condition="increase to 600mg on high-stress days",
            ),
            Supplement(name="vitamin_d3", dose="4000IU", form="liquid", timing="morning"),
        ],
        sleep_context=SleepContext(
            chronotype="intermediate",
            target_bedtime="22:30",
            target_wake="06:30",
            environment_notes="cool room, blackout curtains",
        ),
        lab_values={
            "vitamin_d": LabValue(value=42.0, unit="ng/mL", date="2025-11", range="30-100"),
            "ferritin": LabValue(value=85.0, unit="ng/mL", date="2025-11", range="30-300"),
        },
    )


@pytest.fixture()
def mock_metrics() -> DailyMetrics:
    """Create mock daily metrics for testing."""
    return DailyMetrics(
        date=date(2026, 3, 3),
        total_sleep_seconds=28200,
        deep_sleep_seconds=5400,
        light_sleep_seconds=14400,
        rem_sleep_seconds=7200,
        sleep_score=82,
        hrv_overnight_avg=52.3,
        hrv_status="BALANCED",
        body_battery_morning=75,
        body_battery_max=95,
        body_battery_min=20,
        resting_hr=54,
        avg_hr=68,
        avg_stress_level=32,
        training_load_7d=450.0,
        steps=8500,
        calories_total=2200,
    )


@pytest.fixture()
def mock_trends() -> TrendResult:
    """Create mock trend results for testing."""
    return TrendResult(
        window_start=date(2026, 2, 24),
        window_end=date(2026, 3, 3),
        data_points=7,
        metrics={
            "hrv_overnight_avg": MetricTrend(avg=50.0, min_val=42.0, max_val=58.0, direction=TrendDirection.STABLE),
            "resting_hr": MetricTrend(avg=55.0, min_val=52.0, max_val=58.0, direction=TrendDirection.IMPROVING),
            "sleep_score": MetricTrend(avg=78.0, min_val=65.0, max_val=88.0, direction=TrendDirection.IMPROVING),
        },
    )


@pytest.fixture()
def mock_trends_insufficient() -> TrendResult:
    """Create mock trends with all INSUFFICIENT directions."""
    return TrendResult(
        window_start=date(2026, 2, 24),
        window_end=date(2026, 3, 3),
        data_points=2,
        metrics={
            "hrv_overnight_avg": MetricTrend(direction=TrendDirection.INSUFFICIENT),
            "resting_hr": MetricTrend(direction=TrendDirection.INSUFFICIENT),
            "sleep_score": MetricTrend(direction=TrendDirection.INSUFFICIENT),
        },
    )


@pytest.fixture()
def mock_activities() -> list[Activity]:
    """Create mock activities for testing."""
    return [
        Activity(
            date=date(2026, 3, 2),
            activity_type="cycling",
            name="Morning Ride",
            duration_seconds=3600,
            avg_hr=142,
            max_hr=168,
            calories=650,
            training_effect_aerobic=3.8,
            training_effect_anaerobic=1.2,
        ),
        Activity(
            date=date(2026, 3, 2),
            activity_type="strength_training",
            name="Upper Body",
            duration_seconds=2700,
            avg_hr=110,
            calories=320,
            training_effect_aerobic=2.0,
        ),
    ]


@pytest.fixture()
def mock_context(
    mock_metrics: DailyMetrics,
    mock_trends: TrendResult,
    mock_profile: HealthProfile,
    mock_activities: list[Activity],
) -> PromptContext:
    """Create a full PromptContext from fixture components."""
    return PromptContext(
        today_metrics=mock_metrics,
        trends=mock_trends,
        profile=mock_profile,
        activities=mock_activities,
        target_date=date(2026, 3, 3),
    )


# ---------------------------------------------------------------------------
# Prompt assembler tests
# ---------------------------------------------------------------------------


class TestAssemblePrompt:
    """Test the main assemble_prompt function."""

    def test_produces_assembled_prompt_with_nonempty_text(self, mock_context: PromptContext) -> None:
        result = assemble_prompt(mock_context)
        assert isinstance(result, AssembledPrompt)
        assert len(result.text) > 0
        assert result.estimated_tokens > 0

    def test_contains_health_profile_section(self, mock_context: PromptContext) -> None:
        result = assemble_prompt(mock_context)
        assert "<health_profile>" in result.text
        assert "</health_profile>" in result.text
        # Should contain actual profile data
        assert "82.0" in result.text or "82" in result.text  # weight_kg
        assert "male" in result.text

    def test_contains_today_metrics_section(self, mock_context: PromptContext) -> None:
        result = assemble_prompt(mock_context)
        assert "<today_metrics>" in result.text
        assert "</today_metrics>" in result.text
        assert "52.3" in result.text  # hrv_overnight_avg

    def test_contains_trends_section(self, mock_context: PromptContext) -> None:
        result = assemble_prompt(mock_context)
        assert "<trends_7d>" in result.text
        assert "</trends_7d>" in result.text
        assert "improving" in result.text.lower() or "stable" in result.text.lower()

    def test_contains_activities_section(self, mock_context: PromptContext) -> None:
        result = assemble_prompt(mock_context)
        assert "<yesterday_activities>" in result.text
        assert "</yesterday_activities>" in result.text
        assert "cycling" in result.text.lower()
        assert "Morning Ride" in result.text

    def test_contains_sports_science_section(self, mock_context: PromptContext) -> None:
        result = assemble_prompt(mock_context)
        assert "<sports_science>" in result.text
        assert "</sports_science>" in result.text

    def test_contains_analysis_directives_section(self, mock_context: PromptContext) -> None:
        result = assemble_prompt(mock_context)
        assert "<analysis_directives>" in result.text
        assert "</analysis_directives>" in result.text

    def test_contains_output_format_section(self, mock_context: PromptContext) -> None:
        result = assemble_prompt(mock_context)
        assert "<output_format>" in result.text
        assert "</output_format>" in result.text
        # Should contain DailyProtocol JSON schema
        assert "DailyProtocol" in result.text or "training" in result.text

    def test_estimated_tokens_within_budget(self, mock_context: PromptContext) -> None:
        result = assemble_prompt(mock_context)
        # Should be roughly within 4K-6K tokens for typical input
        assert result.estimated_tokens > 500  # not trivially small
        assert result.estimated_tokens <= 8000  # not absurdly large

    def test_budget_trimming_records_trimmed_sections(self, mock_context: PromptContext) -> None:
        # Use an artificially low budget to force trimming
        result = assemble_prompt(mock_context, token_budget=500)
        assert len(result.sections_trimmed) > 0

    def test_empty_activities_produces_valid_prompt(
        self,
        mock_metrics: DailyMetrics,
        mock_trends: TrendResult,
        mock_profile: HealthProfile,
    ) -> None:
        ctx = PromptContext(
            today_metrics=mock_metrics,
            trends=mock_trends,
            profile=mock_profile,
            activities=[],
            target_date=date(2026, 3, 3),
        )
        result = assemble_prompt(ctx)
        assert "<yesterday_activities>" in result.text
        assert "No activities recorded" in result.text

    def test_insufficient_trends_produces_valid_prompt(
        self,
        mock_metrics: DailyMetrics,
        mock_trends_insufficient: TrendResult,
        mock_profile: HealthProfile,
        mock_activities: list[Activity],
    ) -> None:
        ctx = PromptContext(
            today_metrics=mock_metrics,
            trends=mock_trends_insufficient,
            profile=mock_profile,
            activities=mock_activities,
            target_date=date(2026, 3, 3),
        )
        result = assemble_prompt(ctx)
        assert "<trends_7d>" in result.text
        assert "insufficient" in result.text.lower()

    def test_lab_values_appear_in_prompt(self, mock_context: PromptContext) -> None:
        result = assemble_prompt(mock_context)
        # Lab values from the health profile should appear
        assert "vitamin_d" in result.text or "Vitamin D" in result.text.title()
        assert "42" in result.text  # vitamin D value
        assert "ng/mL" in result.text
        assert "2025-11" in result.text

    def test_supplement_conditions_appear_in_prompt(self, mock_context: PromptContext) -> None:
        result = assemble_prompt(mock_context)
        # Conditional dosing rules should appear
        assert "increase to 600mg" in result.text or "high-stress" in result.text


# ---------------------------------------------------------------------------
# Phase 6 Plan 02: Extended PromptContext, DailyProtocol alerts, prompt
# sections for 28-day trends and anomalies, budget and template updates
# ---------------------------------------------------------------------------


class TestPromptContextExtended:
    """Test PromptContext with extended_trends and anomaly_result fields."""

    def test_accepts_extended_trends_field(
        self,
        mock_metrics: DailyMetrics,
        mock_trends: TrendResult,
        mock_profile: HealthProfile,
        mock_activities: list[Activity],
    ) -> None:
        extended = TrendResult(
            window_start=date(2026, 2, 3),
            window_end=date(2026, 3, 3),
            data_points=28,
            metrics={
                "hrv_overnight_avg": MetricTrend(
                    avg=50.0, min_val=40.0, max_val=60.0, stddev=5.0,
                    direction=TrendDirection.STABLE,
                ),
            },
        )
        ctx = PromptContext(
            today_metrics=mock_metrics,
            trends=mock_trends,
            profile=mock_profile,
            activities=mock_activities,
            target_date=date(2026, 3, 3),
            extended_trends=extended,
        )
        assert ctx.extended_trends is not None
        assert ctx.extended_trends.data_points == 28

    def test_accepts_anomaly_result_field(
        self,
        mock_metrics: DailyMetrics,
        mock_trends: TrendResult,
        mock_profile: HealthProfile,
        mock_activities: list[Activity],
    ) -> None:
        anomaly = AnomalyResult(
            alerts=[
                Alert(
                    severity=AlertSeverity.WARNING,
                    title="Test Alert",
                    description="Test",
                    suggested_action="Monitor",
                    pattern_name="test",
                ),
            ],
            metrics_checked=5,
        )
        ctx = PromptContext(
            today_metrics=mock_metrics,
            trends=mock_trends,
            profile=mock_profile,
            activities=mock_activities,
            target_date=date(2026, 3, 3),
            anomaly_result=anomaly,
        )
        assert ctx.anomaly_result is not None
        assert len(ctx.anomaly_result.alerts) == 1

    def test_extended_trends_defaults_to_none(
        self,
        mock_metrics: DailyMetrics,
        mock_trends: TrendResult,
        mock_profile: HealthProfile,
        mock_activities: list[Activity],
    ) -> None:
        ctx = PromptContext(
            today_metrics=mock_metrics,
            trends=mock_trends,
            profile=mock_profile,
            activities=mock_activities,
            target_date=date(2026, 3, 3),
        )
        assert ctx.extended_trends is None

    def test_anomaly_result_defaults_to_none(
        self,
        mock_metrics: DailyMetrics,
        mock_trends: TrendResult,
        mock_profile: HealthProfile,
        mock_activities: list[Activity],
    ) -> None:
        ctx = PromptContext(
            today_metrics=mock_metrics,
            trends=mock_trends,
            profile=mock_profile,
            activities=mock_activities,
            target_date=date(2026, 3, 3),
        )
        assert ctx.anomaly_result is None


class TestDailyProtocolAlerts:
    """Test DailyProtocol with alerts field."""

    def test_accepts_alerts_field(self) -> None:
        alerts = [
            Alert(
                severity=AlertSeverity.WARNING,
                title="HRV Low",
                description="HRV below baseline",
                suggested_action="Rest today",
                pattern_name="single_metric_outlier",
            ),
        ]
        protocol = DailyProtocol(
            date="2026-03-03",
            training=TrainingRecommendation(
                headline="Rest day",
                readiness_score=5,
                readiness_summary="Low readiness",
                recommended_intensity="low",
                recommended_type="walking",
                recommended_duration_minutes=30,
                training_load_assessment="Reduce",
                reasoning="HRV low",
            ),
            recovery=RecoveryAssessment(
                headline="Recovery needed",
                recovery_status="poor",
                hrv_interpretation="Low",
                body_battery_assessment="Low",
                stress_impact="High",
                recommendations=["Rest"],
                reasoning="Low HRV",
            ),
            sleep=SleepAnalysis(
                headline="Poor sleep",
                quality_assessment="Poor",
                architecture_notes="Low deep sleep",
                optimization_tips=["Earlier bedtime"],
                reasoning="Low score",
            ),
            nutrition=NutritionGuidance(
                headline="Recovery nutrition",
                caloric_target="2200 kcal",
                macro_focus="Protein",
                hydration_target="3L",
                meal_timing_notes="Regular",
                reasoning="Recovery day",
            ),
            supplementation=SupplementationPlan(
                headline="Increase magnesium",
                adjustments=["Extra magnesium"],
                timing_notes="Evening",
                reasoning="High stress",
            ),
            overall_summary="Rest day recommended",
            alerts=alerts,
        )
        assert len(protocol.alerts) == 1
        assert protocol.alerts[0].severity == AlertSeverity.WARNING

    def test_alerts_defaults_to_empty_list(self) -> None:
        protocol = DailyProtocol(
            date="2026-03-03",
            training=TrainingRecommendation(
                headline="Good day",
                readiness_score=8,
                readiness_summary="Good",
                recommended_intensity="moderate",
                recommended_type="cycling",
                recommended_duration_minutes=60,
                training_load_assessment="Balanced",
                reasoning="Good",
            ),
            recovery=RecoveryAssessment(
                headline="Well recovered",
                recovery_status="good",
                hrv_interpretation="Normal",
                body_battery_assessment="Good",
                stress_impact="Low",
                recommendations=["Stretch"],
                reasoning="Good",
            ),
            sleep=SleepAnalysis(
                headline="Good sleep",
                quality_assessment="Good",
                architecture_notes="OK",
                optimization_tips=["Consistent"],
                reasoning="Good",
            ),
            nutrition=NutritionGuidance(
                headline="Standard",
                caloric_target="2400",
                macro_focus="Balanced",
                hydration_target="3L",
                meal_timing_notes="Normal",
                reasoning="Normal",
            ),
            supplementation=SupplementationPlan(
                headline="Standard",
                adjustments=["Normal"],
                timing_notes="Normal",
                reasoning="Normal",
            ),
            overall_summary="Good day",
        )
        assert protocol.alerts == []

    def test_alerts_in_model_json_schema(self) -> None:
        schema = DailyProtocol.model_json_schema()
        schema_str = json.dumps(schema)
        assert "alerts" in schema_str


class TestFormatExtendedTrends:
    """Test _format_extended_trends formatter."""

    def test_formats_trends_with_stats(self) -> None:
        from biointelligence.prompt.assembler import _format_extended_trends

        trends = TrendResult(
            window_start=date(2026, 2, 3),
            window_end=date(2026, 3, 3),
            data_points=28,
            metrics={
                "hrv_overnight_avg": MetricTrend(
                    avg=50.0, min_val=40.0, max_val=60.0, stddev=5.0,
                    direction=TrendDirection.STABLE,
                ),
                "resting_hr": MetricTrend(
                    avg=55.0, min_val=50.0, max_val=60.0, stddev=3.0,
                    direction=TrendDirection.IMPROVING,
                ),
            },
        )
        result = _format_extended_trends(trends)
        assert "avg=" in result
        assert "stddev=" in result
        assert "direction=" in result

    def test_returns_insufficient_data_when_none(self) -> None:
        from biointelligence.prompt.assembler import _format_extended_trends

        result = _format_extended_trends(None)
        assert "insufficient" in result.lower() or "Insufficient" in result


class TestFormatAnomalies:
    """Test _format_anomalies formatter."""

    def test_formats_anomalies_with_alerts(self) -> None:
        from biointelligence.prompt.assembler import _format_anomalies

        anomaly = AnomalyResult(
            alerts=[
                Alert(
                    severity=AlertSeverity.WARNING,
                    title="HRV Extreme Outlier",
                    description="HRV is 2.8 SD below baseline",
                    suggested_action="Monitor closely",
                    pattern_name="single_metric_outlier",
                ),
                Alert(
                    severity=AlertSeverity.CRITICAL,
                    title="Overtraining Pattern",
                    description="Multiple metrics converging",
                    suggested_action="Rest today",
                    pattern_name="overtraining_convergence",
                ),
            ],
            metrics_checked=7,
        )
        result = _format_anomalies(anomaly)
        assert "DETECTED ANOMALIES" in result or "detected" in result.lower()
        assert "WARNING" in result or "warning" in result.lower()
        assert "CRITICAL" in result or "critical" in result.lower()
        assert "HRV Extreme Outlier" in result

    def test_returns_no_anomalies_when_empty(self) -> None:
        from biointelligence.prompt.assembler import _format_anomalies

        anomaly = AnomalyResult(alerts=[], metrics_checked=7)
        result = _format_anomalies(anomaly)
        assert "no anomalies" in result.lower() or "No anomalies" in result

    def test_returns_no_anomalies_when_none(self) -> None:
        from biointelligence.prompt.assembler import _format_anomalies

        result = _format_anomalies(None)
        assert "no anomalies" in result.lower() or "No anomalies" in result


class TestAssemblePromptExtended:
    """Test assemble_prompt with 28-day trends and anomalies."""

    @pytest.fixture()
    def mock_extended_trends(self) -> TrendResult:
        return TrendResult(
            window_start=date(2026, 2, 3),
            window_end=date(2026, 3, 3),
            data_points=28,
            metrics={
                "hrv_overnight_avg": MetricTrend(
                    avg=50.0, min_val=40.0, max_val=60.0, stddev=5.0,
                    direction=TrendDirection.STABLE,
                ),
            },
        )

    @pytest.fixture()
    def mock_anomaly_result(self) -> AnomalyResult:
        return AnomalyResult(
            alerts=[
                Alert(
                    severity=AlertSeverity.WARNING,
                    title="Test Alert",
                    description="Test description",
                    suggested_action="Monitor",
                    pattern_name="test_pattern",
                ),
            ],
            metrics_checked=5,
        )

    def test_includes_trends_28d_section(
        self,
        mock_metrics: DailyMetrics,
        mock_trends: TrendResult,
        mock_profile: HealthProfile,
        mock_activities: list[Activity],
        mock_extended_trends: TrendResult,
    ) -> None:
        ctx = PromptContext(
            today_metrics=mock_metrics,
            trends=mock_trends,
            profile=mock_profile,
            activities=mock_activities,
            target_date=date(2026, 3, 3),
            extended_trends=mock_extended_trends,
        )
        result = assemble_prompt(ctx)
        assert "<trends_28d>" in result.text
        assert "</trends_28d>" in result.text

    def test_includes_anomalies_section(
        self,
        mock_metrics: DailyMetrics,
        mock_trends: TrendResult,
        mock_profile: HealthProfile,
        mock_activities: list[Activity],
        mock_anomaly_result: AnomalyResult,
    ) -> None:
        ctx = PromptContext(
            today_metrics=mock_metrics,
            trends=mock_trends,
            profile=mock_profile,
            activities=mock_activities,
            target_date=date(2026, 3, 3),
            anomaly_result=mock_anomaly_result,
        )
        result = assemble_prompt(ctx)
        assert "<anomalies>" in result.text
        assert "</anomalies>" in result.text

    def test_backward_compatible_without_extended_fields(
        self, mock_context: PromptContext
    ) -> None:
        """Existing contexts without extended_trends/anomaly_result still work."""
        result = assemble_prompt(mock_context)
        assert isinstance(result, AssembledPrompt)
        assert len(result.text) > 0


class TestBudgetUpdates:
    """Test budget.py updates for phase 6."""

    def test_default_token_budget_is_7000(self) -> None:
        assert DEFAULT_TOKEN_BUDGET == 7000

    def test_section_priority_includes_anomalies(self) -> None:
        assert "anomalies" in SECTION_PRIORITY

    def test_section_priority_includes_trends_28d(self) -> None:
        assert "trends_28d" in SECTION_PRIORITY


class TestAnomalyDirectives:
    """Test anomaly interpretation directives in templates."""

    def test_anomaly_directives_exist(self) -> None:
        from biointelligence.prompt.templates import ANOMALY_INTERPRETATION_DIRECTIVES

        assert len(ANOMALY_INTERPRETATION_DIRECTIVES) > 0
        lower = ANOMALY_INTERPRETATION_DIRECTIVES.lower()
        assert "anomal" in lower
        assert "alert" in lower
