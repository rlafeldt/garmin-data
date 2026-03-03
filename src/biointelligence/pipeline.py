"""Pipeline orchestrator: extract -> validate -> store -> analyze."""

from __future__ import annotations

from datetime import date

import structlog
from pydantic import BaseModel

from biointelligence.analysis.engine import AnalysisResult, analyze_daily
from biointelligence.analysis.storage import upsert_daily_protocol
from biointelligence.config import Settings, get_settings
from biointelligence.garmin.client import get_authenticated_client
from biointelligence.garmin.extractors import extract_all_metrics
from biointelligence.garmin.models import (
    CompletenessResult,
    assess_completeness,
    normalize_activities,
    normalize_daily_metrics,
)
from biointelligence.storage.supabase import (
    get_supabase_client,
    upsert_activities,
    upsert_daily_metrics,
)

log = structlog.get_logger()


class IngestionResult(BaseModel):
    """Result of a pipeline ingestion run."""

    date: date
    completeness: CompletenessResult
    activity_count: int
    success: bool


def run_ingestion(
    target_date: date, settings: Settings | None = None
) -> IngestionResult:
    """Run the complete data ingestion pipeline for a single date.

    Stages:
        1. Authenticate with Garmin Connect
        2. Extract all metric categories for the target date
        3. Normalize raw data via Pydantic models
        4. Assess completeness and flag no-wear days
        5. Upsert to Supabase

    Args:
        target_date: The date to ingest data for.
        settings: Optional settings override. Uses get_settings() if not provided.

    Returns:
        IngestionResult with date, completeness, activity_count, and success flag.
    """
    if settings is None:
        settings = get_settings()

    log.info("pipeline_start", date=target_date.isoformat())

    # Step 1: Authenticate
    garmin_client = get_authenticated_client(settings)

    # Step 2: Extract
    raw_data = extract_all_metrics(garmin_client, target_date)

    # Step 3: Normalize
    daily_record = normalize_daily_metrics(raw_data, target_date)
    activities = normalize_activities(raw_data.get("activities", []), target_date)

    # Step 4: Assess completeness
    completeness = assess_completeness(daily_record)
    daily_record.completeness_score = completeness.score
    daily_record.is_no_wear = completeness.is_no_wear

    if completeness.missing_critical:
        log.warning(
            "incomplete_data",
            date=target_date.isoformat(),
            missing_critical=completeness.missing_critical,
            score=completeness.score,
        )

    # Step 5: Store
    supabase_client = get_supabase_client(settings)
    upsert_daily_metrics(supabase_client, daily_record)
    upsert_activities(supabase_client, activities, target_date)

    result = IngestionResult(
        date=target_date,
        completeness=completeness,
        activity_count=len(activities),
        success=True,
    )

    log.info(
        "pipeline_complete",
        date=target_date.isoformat(),
        completeness_score=completeness.score,
        activity_count=len(activities),
        is_no_wear=completeness.is_no_wear,
    )

    return result


def run_analysis(
    target_date: date, settings: Settings | None = None
) -> AnalysisResult:
    """Run the complete analysis pipeline for a single date.

    Orchestrates the full analysis flow: call Claude API for daily protocol
    generation, then persist the result to Supabase. Skips storage if
    analysis fails to avoid partial writes.

    Args:
        target_date: The date to analyze.
        settings: Optional settings override. Uses get_settings() if not provided.

    Returns:
        AnalysisResult with protocol, token usage, and success status.
    """
    if settings is None:
        settings = get_settings()

    log.info("analysis_pipeline_start", date=target_date.isoformat())

    result = analyze_daily(target_date, settings)

    if result.success and result.protocol is not None:
        supabase_client = get_supabase_client(settings)
        upsert_daily_protocol(supabase_client, result)

        log.info(
            "analysis_pipeline_complete",
            date=target_date.isoformat(),
            model=result.model,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
        )
    else:
        log.error(
            "analysis_pipeline_failed",
            date=target_date.isoformat(),
            error=result.error,
        )

    return result
