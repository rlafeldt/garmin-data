"""Pipeline run logging to Supabase for observability."""

from __future__ import annotations

from datetime import date

import structlog
from pydantic import BaseModel
from supabase import Client
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

log = structlog.get_logger()


class PipelineRunLog(BaseModel):
    """Record of a single pipeline execution."""

    date: date
    status: str
    failed_stage: str | None = None
    error_message: str | None = None
    duration_seconds: float
    started_at: str


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    retry=retry_if_exception_type((ConnectionError, TimeoutError)),
)
def log_pipeline_run(client: Client, run_log: PipelineRunLog) -> None:
    """Upsert a pipeline run record to Supabase.

    Uses on_conflict="date" so re-running for the same date overwrites
    the existing record.

    Args:
        client: Supabase client instance.
        run_log: PipelineRunLog with execution details.
    """
    data = run_log.model_dump(mode="json")
    log.info("pipeline_run_log", date=data["date"], status=data["status"])

    client.table("pipeline_runs").upsert(
        data, on_conflict="date"
    ).execute()

    log.info("pipeline_run_log_done", date=data["date"])
