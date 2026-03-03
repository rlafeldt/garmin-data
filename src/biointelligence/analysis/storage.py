"""Supabase storage for daily analysis protocols."""

from __future__ import annotations

import structlog
from supabase import Client
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from biointelligence.analysis.engine import AnalysisResult

log = structlog.get_logger()


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    retry=retry_if_exception_type((ConnectionError, TimeoutError)),
)
def upsert_daily_protocol(client: Client, result: AnalysisResult) -> None:
    """Upsert a daily protocol record to Supabase, keyed on date.

    Uses on_conflict="date" so running analysis twice for the same date
    overwrites the existing protocol rather than creating a duplicate.

    Args:
        client: Supabase client instance.
        result: AnalysisResult with a populated DailyProtocol.
    """
    date_iso = result.date.isoformat()
    log.info("upsert_daily_protocol", date=date_iso)

    record = {
        "date": date_iso,
        "protocol": result.protocol.model_dump(mode="json"),
        "model": result.model,
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
    }

    client.table("daily_protocols").upsert(record, on_conflict="date").execute()

    log.info("upsert_daily_protocol_done", date=date_iso)
