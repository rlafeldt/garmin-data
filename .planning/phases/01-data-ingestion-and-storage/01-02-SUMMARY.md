---
phase: 01-data-ingestion-and-storage
plan: 02
subsystem: database
tags: [supabase, pipeline, cli, upsert, idempotent, argparse, tenacity]

# Dependency graph
requires:
  - phase: 01-01
    provides: "Garmin auth client, metric extractors, Pydantic models, completeness scoring"
provides:
  - "Supabase schema DDL for daily_metrics and activities tables"
  - "Supabase storage client with upsert_daily_metrics and upsert_activities"
  - "Pipeline orchestrator: extract -> validate -> store (run_ingestion)"
  - "CLI entry point via python -m biointelligence with --date argument"
  - "End-to-end verified data flow: Garmin -> Pydantic -> Supabase"
affects: [02-health-profile-and-prompt-assembly]

# Tech tracking
tech-stack:
  added: [supabase-py, argparse]
  patterns: [delete-then-insert for activity idempotency, upsert with on_conflict for metrics, pipeline orchestration pattern, CLI with argparse and timezone-aware defaults]

key-files:
  created:
    - src/biointelligence/storage/__init__.py
    - src/biointelligence/storage/supabase.py
    - src/biointelligence/storage/schema.sql
    - src/biointelligence/pipeline.py
    - src/biointelligence/main.py
    - src/biointelligence/__main__.py
    - tests/test_storage.py
    - tests/test_pipeline.py
  modified: []

key-decisions:
  - "Activities use delete-then-insert by date for idempotency (not upsert, since activities lack a unique key)"
  - "Daily metrics use upsert with on_conflict='date' for idempotency"
  - "Pipeline orchestrator as single run_ingestion function composing all steps"
  - "CLI defaults to yesterday in Europe/Berlin timezone"

patterns-established:
  - "Delete-then-insert pattern for child records without natural unique key"
  - "Pipeline orchestration: extract -> normalize -> assess -> store with structured logging"
  - "CLI entry point via __main__.py for python -m module invocation"

requirements-completed: [DATA-06, DATA-07]

# Metrics
duration: ~15min
completed: 2026-03-03
---

# Phase 1 Plan 02: Supabase Storage and Pipeline Summary

**Supabase storage with upsert idempotency, pipeline orchestrator wiring Garmin extraction to persistence, and CLI entry point -- end-to-end verified with real data**

## Performance

- **Duration:** ~15 min (across checkpoint)
- **Started:** 2026-03-03T17:15:27Z
- **Completed:** 2026-03-03T18:08:43Z
- **Tasks:** 2 (1 TDD implementation + 1 human verification)
- **Files created:** 8

## Accomplishments
- Supabase schema DDL with daily_metrics (upsert by date) and activities tables, indexes, and update trigger
- Storage client with tenacity retry for transient Supabase errors
- Pipeline orchestrator composing extract -> normalize -> assess completeness -> store
- CLI entry point accepting --date argument, defaulting to yesterday (Europe/Berlin)
- End-to-end verification passed: ingestion, Supabase data presence, idempotency (no duplicates), activities storage, and default date behavior

## Task Commits

Each task was committed atomically (TDD: RED then GREEN):

1. **Task 1 (RED): Failing tests for storage, pipeline, and CLI** - `2f0f6d5` (test)
2. **Task 1 (GREEN): Supabase storage layer, pipeline orchestrator, CLI entry point** - `07d4ea4` (feat)
3. **Task 2: End-to-end verification with real Garmin data** - Human-verify checkpoint (no commit, verified by user)

## Files Created/Modified
- `src/biointelligence/storage/schema.sql` - DDL for daily_metrics and activities tables with indexes and triggers
- `src/biointelligence/storage/supabase.py` - Supabase client with get_supabase_client, upsert_daily_metrics, upsert_activities (tenacity retry)
- `src/biointelligence/storage/__init__.py` - Package exports for storage module
- `src/biointelligence/pipeline.py` - Pipeline orchestrator with run_ingestion and IngestionResult
- `src/biointelligence/main.py` - CLI entry point with argparse (--date, --json-log)
- `src/biointelligence/__main__.py` - Module entry point for `python -m biointelligence`
- `tests/test_storage.py` - Unit tests for Supabase storage functions (mocked client)
- `tests/test_pipeline.py` - Unit tests for pipeline orchestration and CLI argument parsing

## Decisions Made
- Activities use delete-then-insert by date for idempotency (activities lack a natural unique key beyond date + activity_type + start_time, making upsert fragile)
- Daily metrics use standard upsert with on_conflict='date' since date is the unique constraint
- Pipeline is a single `run_ingestion` function that orchestrates all steps rather than a class-based approach
- CLI defaults to yesterday in Europe/Berlin timezone using zoneinfo

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None - all unit tests passed on first GREEN implementation, and all 5 end-to-end verification tests confirmed by user.

## User Setup Required

External services were configured during the checkpoint verification:

**Already completed:**
- Garmin Connect credentials set in `.env` (GARMIN_EMAIL, GARMIN_PASSWORD)
- Supabase project created with URL and key in `.env` (SUPABASE_URL, SUPABASE_KEY)
- Schema SQL executed in Supabase SQL Editor
- MFA disabled on Garmin Connect account

## Next Phase Readiness
- Phase 1 complete: full data pipeline from Garmin to Supabase is operational
- Phase 2 can query Supabase daily_metrics and activities tables for trend computation
- All data flows through validated Pydantic models with completeness scoring
- CLI provides manual trigger: `uv run python -m biointelligence --date YYYY-MM-DD`

## Self-Check: PASSED

- All 8 created files verified present on disk
- Both task commits verified in git history (2f0f6d5, 07d4ea4)
- End-to-end verification approved by user (5/5 tests passed)

---
*Phase: 01-data-ingestion-and-storage*
*Completed: 2026-03-03*
