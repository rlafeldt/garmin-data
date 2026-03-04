"""Pydantic models for prompt assembly and DailyProtocol output schema."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from biointelligence.anomaly.models import Alert, AnomalyResult
from biointelligence.garmin.models import Activity, DailyMetrics
from biointelligence.profile.models import HealthProfile
from biointelligence.trends.models import TrendResult


class PromptContext(BaseModel):
    """All data sources needed to assemble a Claude prompt."""

    today_metrics: DailyMetrics
    trends: TrendResult
    profile: HealthProfile
    activities: list[Activity]
    target_date: date
    extended_trends: TrendResult | None = None
    anomaly_result: AnomalyResult | None = None


class AssembledPrompt(BaseModel):
    """Result of prompt assembly with metadata."""

    text: str
    estimated_tokens: int
    sections_included: list[str]
    sections_trimmed: list[str]


# ---------------------------------------------------------------------------
# DailyProtocol output schema -- defines what Claude should return.
# Preliminary schema; Phase 3 may refine field names and add fields.
# ---------------------------------------------------------------------------


class TrainingRecommendation(BaseModel):
    """Training guidance based on readiness and load."""

    headline: str
    readiness_score: int = Field(..., ge=1, le=10, description="Overall readiness 1-10")
    readiness_summary: str
    recommended_intensity: str
    recommended_type: str
    recommended_duration_minutes: int
    training_load_assessment: str
    reasoning: str


class RecoveryAssessment(BaseModel):
    """Recovery status derived from HRV, body battery, and stress."""

    headline: str
    recovery_status: str
    hrv_interpretation: str
    body_battery_assessment: str
    stress_impact: str
    recommendations: list[str]
    reasoning: str


class SleepAnalysis(BaseModel):
    """Sleep quality and optimization analysis."""

    headline: str
    quality_assessment: str
    architecture_notes: str
    optimization_tips: list[str]
    reasoning: str


class NutritionGuidance(BaseModel):
    """Daily nutrition recommendations."""

    headline: str
    caloric_target: str
    macro_focus: str
    hydration_target: str
    meal_timing_notes: str
    reasoning: str


class SupplementationPlan(BaseModel):
    """Supplement adjustments for the day."""

    headline: str
    adjustments: list[str]
    timing_notes: str
    reasoning: str


class DailyProtocol(BaseModel):
    """Complete daily protocol output schema for Claude.

    Defines the 5-domain structured response: training, recovery, sleep,
    nutrition, and supplementation. Each domain includes a reasoning field
    to capture Claude's analytical chain.
    """

    date: str
    training: TrainingRecommendation
    recovery: RecoveryAssessment
    sleep: SleepAnalysis
    nutrition: NutritionGuidance
    supplementation: SupplementationPlan
    overall_summary: str
    data_quality_notes: str | None = None
    alerts: list[Alert] = Field(default_factory=list)
