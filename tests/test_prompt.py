"""Tests for prompt assembly, models, templates, and token budget."""

from __future__ import annotations

import json
from datetime import date

import pytest

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
                readiness_score=8,
                readiness_summary="Well recovered",
                recommended_intensity="moderate",
                recommended_type="cycling",
                recommended_duration_minutes=60,
                training_load_assessment="Balanced",
                reasoning="Good HRV and sleep",
            ),
            recovery=RecoveryAssessment(
                recovery_status="good",
                hrv_interpretation="Above baseline",
                body_battery_assessment="High morning charge",
                stress_impact="Low",
                recommendations=["Light stretching"],
                reasoning="Metrics indicate full recovery",
            ),
            sleep=SleepAnalysis(
                quality_assessment="Good",
                architecture_notes="Adequate deep sleep",
                optimization_tips=["Maintain consistent bedtime"],
                reasoning="Sleep score above target",
            ),
            nutrition=NutritionGuidance(
                caloric_target="2400 kcal",
                macro_focus="Balanced",
                hydration_target="3L",
                meal_timing_notes="Pre-workout carbs",
                reasoning="Moderate training day",
            ),
            supplementation=SupplementationPlan(
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
