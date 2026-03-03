"""Supabase client and storage operations for daily metrics and activities."""

from __future__ import annotations

from datetime import date

import structlog
from supabase import Client, create_client
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from biointelligence.config import Settings
from biointelligence.garmin.models import Activity, DailyMetrics

log = structlog.get_logger()


def get_supabase_client(settings: Settings) -> Client:
    """Create and return a Supabase client.

    Args:
        settings: Application settings with Supabase URL and key.

    Returns:
        An initialized Supabase client.
    """
    return create_client(settings.supabase_url, settings.supabase_key)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    retry=retry_if_exception_type((ConnectionError, TimeoutError)),
)
def upsert_daily_metrics(client: Client, record: DailyMetrics) -> None:
    """Upsert a daily metrics record to Supabase, keyed on date.

    Uses on_conflict="date" so running the pipeline twice for the same date
    overwrites the existing row rather than creating a duplicate.

    Args:
        client: Supabase client instance.
        record: DailyMetrics to upsert.
    """
    data = record.model_dump(mode="json")
    log.info("upsert_daily_metrics", date=data["date"])

    client.table("daily_metrics").upsert(
        data, on_conflict="date"
    ).execute()

    log.info("upsert_daily_metrics_done", date=data["date"])


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    retry=retry_if_exception_type((ConnectionError, TimeoutError)),
)
def upsert_activities(
    client: Client, activities: list[Activity], target_date: date
) -> None:
    """Upsert activities for a date using delete-then-insert strategy.

    Deletes all existing activities for the target date, then inserts the new
    list. This ensures idempotent behavior on re-runs.

    Args:
        client: Supabase client instance.
        activities: List of Activity records to insert.
        target_date: The date to delete/insert activities for.
    """
    date_iso = target_date.isoformat()
    log.info("upsert_activities", date=date_iso, count=len(activities))

    # Delete existing activities for this date
    client.table("activities").delete().eq("date", date_iso).execute()

    # Insert new activities (skip if empty)
    if activities:
        records = [a.model_dump(mode="json") for a in activities]
        client.table("activities").insert(records).execute()

    log.info("upsert_activities_done", date=date_iso, count=len(activities))
