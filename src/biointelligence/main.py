"""CLI entry point for the BioIntelligence data ingestion and analysis pipeline."""

from __future__ import annotations

import argparse
import sys
import zoneinfo
from datetime import date, datetime, timedelta

import structlog

from biointelligence.logging import configure_logging
from biointelligence.pipeline import run_analysis, run_delivery, run_ingestion

log = structlog.get_logger()


def _get_yesterday(tz_name: str = "Europe/Berlin") -> date:
    """Get yesterday's date in the given timezone.

    Args:
        tz_name: IANA timezone name.

    Returns:
        Yesterday's date in the specified timezone.
    """
    tz = zoneinfo.ZoneInfo(tz_name)
    now_local = datetime.now(tz)
    yesterday = now_local - timedelta(days=1)
    return yesterday.date()


def main(argv: list[str] | None = None) -> int:
    """Run the data ingestion (and optionally analysis) pipeline from the command line.

    Args:
        argv: Command line arguments. Defaults to sys.argv[1:].

    Returns:
        Exit code: 0 on success, 1 on failure.
    """
    parser = argparse.ArgumentParser(
        prog="biointelligence",
        description=(
            "Ingest daily Garmin biometric data into Supabase"
            " and optionally run AI analysis."
        ),
    )
    parser.add_argument(
        "--date",
        type=lambda s: datetime.strptime(s, "%Y-%m-%d").date(),
        default=None,
        help="Target date in YYYY-MM-DD format (default: yesterday in Europe/Berlin)",
    )
    parser.add_argument(
        "--json-log",
        action="store_true",
        default=False,
        help="Output logs as JSON (default: colored console)",
    )
    parser.add_argument(
        "--analyze",
        action="store_true",
        default=False,
        help="Run analysis after ingestion (requires ANTHROPIC_API_KEY)",
    )
    parser.add_argument(
        "--deliver",
        action="store_true",
        default=False,
        help="Send protocol email after analysis (requires RESEND_API_KEY)",
    )

    args = parser.parse_args(argv)

    # --deliver implies --analyze (delivery requires a protocol)
    if args.deliver:
        args.analyze = True

    configure_logging(json_output=args.json_log)

    target_date = args.date if args.date is not None else _get_yesterday()

    log.info("cli_start", date=target_date.isoformat())

    try:
        result = run_ingestion(target_date)
    except Exception:
        log.exception("pipeline_failed", date=target_date.isoformat())
        return 1

    if not result.success:
        log.error("pipeline_unsuccessful", date=target_date.isoformat())
        return 1

    print(
        f"Ingestion complete for {result.date}: "
        f"completeness={result.completeness.score:.1%}, "
        f"activities={result.activity_count}, "
        f"no_wear={result.completeness.is_no_wear}"
    )

    if args.analyze:
        try:
            analysis_result = run_analysis(target_date)
        except Exception:
            log.exception("analysis_failed", date=target_date.isoformat())
            return 1

        if not analysis_result.success:
            log.error("analysis_unsuccessful", date=target_date.isoformat())
            return 1

        print(
            f"Analysis complete for {target_date}: "
            f"model={analysis_result.model}, "
            f"tokens={analysis_result.input_tokens}in/{analysis_result.output_tokens}out"
        )

        if args.deliver:
            try:
                delivery_result = run_delivery(analysis_result)
            except Exception:
                log.exception("delivery_failed", date=target_date.isoformat())
                return 1

            if not delivery_result.success:
                log.error(
                    "delivery_unsuccessful",
                    date=target_date.isoformat(),
                    error=delivery_result.error,
                )
                return 1

            print(
                f"Delivery complete for {target_date}: "
                f"email_id={delivery_result.email_id}"
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())
