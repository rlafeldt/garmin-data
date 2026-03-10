"""Pydantic models for prompt assembly and DailyProtocol output schema."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from biointelligence.anomaly.models import AnomalyResult
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


class DailyProtocol(BaseModel):
    """Daily insight output schema for Claude.

    Claude produces a single integrated narrative that weaves metrics,
    cross-domain synthesis, and recommendations into cohesive prose.
    Two variants: plain text (WhatsApp) and markdown with links (email).
    """

    date: str
    readiness_score: int = Field(
        ..., ge=1, le=10, description="Overall readiness 1-10"
    )
    insight: str = Field(
        ...,
        description=(
            "Complete narrative insight for WhatsApp. Plain text, no markdown "
            "links. Uses *bold* for WhatsApp formatting. 150-250 words."
        ),
    )
    insight_html: str = Field(
        ...,
        description=(
            "Same narrative with markdown links on study claims and supplement "
            "names. Links use [descriptive text](url) format."
        ),
    )
    data_quality_notes: str | None = None
