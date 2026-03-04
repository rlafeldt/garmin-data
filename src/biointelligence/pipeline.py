"""Pipeline orchestrator: extract -> validate -> store -> analyze -> deliver."""

from __future__ import annotations

import time
from datetime import UTC, date, datetime

import structlog
from garminconnect import Garmin
from pydantic import BaseModel

from biointelligence.analysis.engine import AnalysisResult, analyze_daily
from biointelligence.analysis.storage import upsert_daily_protocol
from biointelligence.automation.notify import send_failure_notification
from biointelligence.automation.run_log import PipelineRunLog, log_pipeline_run
from biointelligence.config import Settings, get_settings
from biointelligence.delivery.renderer import build_subject, render_html, render_text
from biointelligence.delivery.sender import DeliveryResult, send_email
from biointelligence.delivery.whatsapp_renderer import render_whatsapp
from biointelligence.delivery.whatsapp_sender import send_whatsapp
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


class PipelineResult(BaseModel):
    """Result of a full pipeline run (ingestion + analysis + delivery)."""

    date: date
    success: bool
    failed_stage: str | None = None
    duration_seconds: float
    error: str | None = None


def run_ingestion(
    target_date: date,
    settings: Settings | None = None,
    *,
    garmin_client: Garmin | None = None,
) -> IngestionResult:
    """Run the complete data ingestion pipeline for a single date.

    Stages:
        1. Authenticate with Garmin Connect (skipped if garmin_client provided)
        2. Extract all metric categories for the target date
        3. Normalize raw data via Pydantic models
        4. Assess completeness and flag no-wear days
        5. Upsert to Supabase

    Args:
        target_date: The date to ingest data for.
        settings: Optional settings override. Uses get_settings() if not provided.
        garmin_client: Optional pre-authenticated Garmin client. If provided,
            skips authentication (avoids double-auth when called from
            run_full_pipeline).

    Returns:
        IngestionResult with date, completeness, activity_count, and success flag.
    """
    if settings is None:
        settings = get_settings()

    log.info("pipeline_start", date=target_date.isoformat())

    # Step 1: Authenticate (skip if pre-authenticated client provided)
    if garmin_client is None:
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


def run_delivery(
    analysis_result: AnalysisResult, settings: Settings | None = None
) -> DeliveryResult:
    """Render and deliver the Daily Protocol via WhatsApp (preferred) or email (fallback).

    Orchestrates the full delivery flow: guard against failed analysis,
    try WhatsApp delivery first when configured, fall back to email on
    failure or when WhatsApp is not configured.

    Args:
        analysis_result: Result from run_analysis with DailyProtocol.
        settings: Optional settings override. Uses get_settings() if not provided.

    Returns:
        DeliveryResult with message/email_id on success, error on failure.
    """
    if settings is None:
        settings = get_settings()

    log.info("delivery_pipeline_start", date=analysis_result.date.isoformat())

    # Guard: skip delivery if analysis failed or no protocol available
    if not analysis_result.success or analysis_result.protocol is None:
        log.warning(
            "delivery_pipeline_skipped",
            date=analysis_result.date.isoformat(),
            reason="No protocol available for delivery",
        )
        return DeliveryResult(
            date=analysis_result.date,
            success=False,
            error="No protocol available for delivery",
        )

    protocol = analysis_result.protocol
    target_date = analysis_result.date

    # WhatsApp-first delivery (when configured)
    if settings.whatsapp_access_token:
        whatsapp_text = render_whatsapp(protocol, target_date)
        result = send_whatsapp(whatsapp_text, target_date, settings)

        if result.success:
            log.info(
                "delivery_pipeline_complete",
                date=target_date.isoformat(),
                channel="whatsapp",
                message_id=result.email_id,
            )
            return result

        log.warning(
            "whatsapp_failed_falling_back_to_email",
            date=target_date.isoformat(),
            error=result.error,
        )

    # Email fallback (or primary when WhatsApp not configured)
    html_content = render_html(protocol, target_date)
    text_content = render_text(protocol, target_date)
    subject = build_subject(protocol, target_date)

    result = send_email(
        html=html_content,
        text=text_content,
        subject=subject,
        target_date=target_date,
        settings=settings,
    )

    if result.success:
        log.info(
            "delivery_pipeline_complete",
            date=target_date.isoformat(),
            channel="email",
            email_id=result.email_id,
        )
    else:
        log.error(
            "delivery_pipeline_failed",
            date=target_date.isoformat(),
            error=result.error,
        )

    return result


def run_full_pipeline(
    target_date: date, settings: Settings | None = None
) -> PipelineResult:
    """Run the complete pipeline: ingestion -> analysis -> delivery.

    Orchestrates all stages with timing, run logging to Supabase, and
    failure notification via email. Each error is caught and recorded;
    run logging and notification failures are best-effort (logged as
    warnings, never mask the pipeline result).

    Args:
        target_date: The date to process.
        settings: Optional settings override. Uses get_settings() if not provided.

    Returns:
        PipelineResult with success status, failed_stage, duration, and error.
    """
    if settings is None:
        settings = get_settings()

    started_at = datetime.now(tz=UTC).isoformat()
    t0 = time.monotonic()

    log.info("full_pipeline_start", date=target_date.isoformat())

    # Get shared Supabase client for run logging and token persistence
    supabase_client = get_supabase_client(settings)

    # Authenticate Garmin once with Supabase token persistence
    garmin_client = get_authenticated_client(
        settings, supabase_client=supabase_client
    )

    failed_stage: str | None = None
    error_message: str | None = None

    # Stage 1: Ingestion
    try:
        ingestion_result = run_ingestion(
            target_date, settings, garmin_client=garmin_client
        )
        if not ingestion_result.success:
            failed_stage = "ingestion"
            error_message = "Ingestion returned success=False"
    except Exception as exc:
        failed_stage = "ingestion"
        error_message = str(exc)

    # Stage 2: Analysis
    if failed_stage is None:
        try:
            analysis_result = run_analysis(target_date, settings)
            if not analysis_result.success:
                failed_stage = "analysis"
                error_message = analysis_result.error or "Analysis returned success=False"
        except Exception as exc:
            failed_stage = "analysis"
            error_message = str(exc)

    # Stage 3: Delivery
    if failed_stage is None:
        try:
            delivery_result = run_delivery(analysis_result, settings)
            if not delivery_result.success:
                failed_stage = "delivery"
                error_message = delivery_result.error or "Delivery returned success=False"
        except Exception as exc:
            failed_stage = "delivery"
            error_message = str(exc)

    duration = time.monotonic() - t0
    success = failed_stage is None

    # Send failure notification (best-effort)
    if not success:
        try:
            send_failure_notification(
                target_date=target_date,
                failed_stage=failed_stage,
                error_message=error_message,
                settings=settings,
            )
        except Exception:
            log.exception(
                "full_pipeline_notification_failed",
                date=target_date.isoformat(),
            )

    # Log pipeline run to Supabase (best-effort)
    run_log = PipelineRunLog(
        date=target_date,
        status="success" if success else "failure",
        failed_stage=failed_stage,
        error_message=error_message,
        duration_seconds=round(duration, 2),
        started_at=started_at,
    )
    try:
        log_pipeline_run(supabase_client, run_log)
    except Exception:
        log.exception(
            "full_pipeline_run_log_failed",
            date=target_date.isoformat(),
        )

    log.info(
        "full_pipeline_complete",
        date=target_date.isoformat(),
        success=success,
        failed_stage=failed_stage,
        duration_seconds=round(duration, 2),
    )

    return PipelineResult(
        date=target_date,
        success=success,
        failed_stage=failed_stage,
        duration_seconds=round(duration, 2),
        error=error_message,
    )
