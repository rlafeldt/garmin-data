"""Analysis engine orchestration: AnalysisResult model and analyze_daily function.

Orchestrates the full analysis flow: load profile + metrics + trends,
assemble prompt, call Claude API, and return a structured AnalysisResult.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import structlog
from pydantic import BaseModel
from supabase import Client

from biointelligence.analysis.client import analyze_prompt, get_anthropic_client
from biointelligence.anomaly.detector import detect_anomalies
from biointelligence.config import Settings, get_settings
from biointelligence.garmin.models import Activity, DailyMetrics
from biointelligence.profile.loader import load_health_profile
from biointelligence.prompt.assembler import assemble_prompt
from biointelligence.prompt.models import DailyProtocol, PromptContext
from biointelligence.storage.supabase import get_supabase_client
from biointelligence.trends.compute import (
    compute_extended_trends,
    compute_trends,
    fetch_trend_window,
)

log = structlog.get_logger()


class AnalysisResult(BaseModel):
    """Result of a pipeline analysis run.

    Follows the IngestionResult pattern from pipeline.py. Contains the
    validated DailyProtocol (or None on failure), token usage metadata,
    and success/error status.
    """

    date: date
    protocol: DailyProtocol | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    model: str
    success: bool
    error: str | None = None


def _fetch_daily_metrics(supabase_client: Client, target_date: date) -> DailyMetrics:
    """Fetch daily metrics for a specific date from Supabase.

    Args:
        supabase_client: Supabase client instance.
        target_date: The date to fetch metrics for.

    Returns:
        A validated DailyMetrics instance.

    Raises:
        ValueError: If no metrics found for the target date.
    """
    response = (
        supabase_client.table("daily_metrics")
        .select("*")
        .eq("date", target_date.isoformat())
        .execute()
    )

    if not response.data:
        msg = f"No daily metrics found for {target_date.isoformat()}"
        raise ValueError(msg)

    return DailyMetrics.model_validate(response.data[0])


def _fetch_activities(supabase_client: Client, target_date: date) -> list[Activity]:
    """Fetch activities for a specific date from Supabase.

    Args:
        supabase_client: Supabase client instance.
        target_date: The date to fetch activities for.

    Returns:
        A list of validated Activity instances (may be empty).
    """
    response = (
        supabase_client.table("activities")
        .select("*")
        .eq("date", target_date.isoformat())
        .execute()
    )

    return [Activity.model_validate(row) for row in response.data]


def analyze_daily(target_date: date, settings: Settings | None = None) -> AnalysisResult:
    """Run the complete analysis pipeline for a single date.

    Orchestration stages:
        1. Load health profile from YAML
        2. Fetch daily metrics and activities from Supabase
        3. Compute 7-day trends from Supabase
        3b. Compute 28-day extended trends (graceful degradation)
        3c. Fetch 28-day raw rows for consecutive day checks
        3d. Run anomaly detection
        4. Assemble Claude prompt from all data sources
        5. Call Claude API with structured output
        6. Return AnalysisResult with protocol and metadata

    Args:
        target_date: The date to analyze.
        settings: Optional settings override. Uses get_settings() if not provided.

    Returns:
        AnalysisResult with success status, protocol (if successful),
        token usage, and error message (if failed).
    """
    if settings is None:
        settings = get_settings()

    log.info("analysis_start", date=target_date.isoformat())

    try:
        # Step 1: Load health profile
        profile = load_health_profile(Path(settings.health_profile_path))

        # Step 2: Fetch data from Supabase
        supabase_client = get_supabase_client(settings)
        today_metrics = _fetch_daily_metrics(supabase_client, target_date)
        activities = _fetch_activities(supabase_client, target_date)

        # Step 3: Compute 7-day trends
        trends = compute_trends(supabase_client, target_date)

        # Step 3b-3d: Extended trends and anomaly detection (graceful degradation)
        extended_trends = None
        anomaly_result = None
        try:
            extended_trends = compute_extended_trends(supabase_client, target_date)
            trend_rows_28d = fetch_trend_window(
                supabase_client, target_date, window_days=28,
            )
            anomaly_result = detect_anomalies(
                today_metrics, extended_trends, trend_rows_28d,
            )
            log.info(
                "anomaly_detection_complete",
                alerts=len(anomaly_result.alerts),
                metrics_checked=anomaly_result.metrics_checked,
            )
        except Exception as exc:
            log.warning(
                "anomaly_detection_failed",
                error=str(exc),
                date=target_date.isoformat(),
            )
            extended_trends = None
            anomaly_result = None

        # Step 4: Assemble prompt
        context = PromptContext(
            today_metrics=today_metrics,
            trends=trends,
            profile=profile,
            activities=activities,
            target_date=target_date,
            extended_trends=extended_trends,
            anomaly_result=anomaly_result,
        )
        prompt = assemble_prompt(context)

        # Step 5: Call Claude API
        anthropic_client = get_anthropic_client(settings)
        protocol, metadata = analyze_prompt(
            anthropic_client, prompt, settings.claude_model
        )

        log.info(
            "analysis_daily_complete",
            date=target_date.isoformat(),
            input_tokens=metadata["input_tokens"],
            output_tokens=metadata["output_tokens"],
            model=settings.claude_model,
        )

        return AnalysisResult(
            date=target_date,
            protocol=protocol,
            input_tokens=metadata["input_tokens"],
            output_tokens=metadata["output_tokens"],
            model=settings.claude_model,
            success=True,
        )

    except Exception as e:
        log.error(
            "analysis_daily_failed",
            date=target_date.isoformat(),
            error=str(e),
        )
        return AnalysisResult(
            date=target_date,
            model=settings.claude_model,
            success=False,
            error=str(e),
        )
