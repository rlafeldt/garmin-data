---
phase: 05-pipeline-automation
plan: 02
subsystem: automation
tags: [github-actions, cron, supabase, pipeline, cli, pydantic]

# Dependency graph
requires:
  - phase: 05-pipeline-automation
    plan: 01
    provides: automation/ package (token persistence, run logging, failure notification), dual-mode Garmin client
  - phase: 04-protocol-rendering-and-email-delivery
    provides: run_delivery pipeline function and DeliveryResult model
provides:
  - "run_full_pipeline orchestrator composing ingestion -> analysis -> delivery with timing, run logging, and failure notification"
  - "CLI --deliver flag wired to run_full_pipeline for end-to-end execution"
  - "GitHub Actions daily-pipeline.yml with cron (5:03 UTC) and workflow_dispatch triggers"
  - "Supabase DDL for garmin_tokens, pipeline_runs, and daily_protocols tables"
affects: [06-intelligence-hardening, pipeline-monitoring]

# Tech tracking
tech-stack:
  added: [github-actions, astral-sh/setup-uv]
  patterns: [pipeline-orchestrator, ci-token-fallback, cron-scheduling]

key-files:
  created:
    - .github/workflows/daily-pipeline.yml
    - sql/05-pipeline-automation.sql
  modified:
    - src/biointelligence/pipeline.py
    - src/biointelligence/main.py
    - src/biointelligence/garmin/client.py
    - src/biointelligence/analysis/client.py
    - src/biointelligence/config.py
    - pyproject.toml
    - tests/test_pipeline.py
    - tests/test_analysis.py
    - tests/test_analysis_storage.py

key-decisions:
  - "run_full_pipeline wraps ingestion/analysis/delivery with timing, run logging, and best-effort failure notification"
  - "CLI --deliver delegates entirely to run_full_pipeline (replaces sequential try/except chain)"
  - "GitHub Actions cron at 5:03 UTC (off-peak minute) for 6-7 AM CET/CEST daily execution"
  - "Single-job workflow -- CLI already chains stages, no need for multi-job orchestration"
  - "Token fallback: when stored Supabase token expires, fall back to email/password re-auth"
  - "CLI entry point registered in pyproject.toml for uv run biointelligence invocation"

patterns-established:
  - "Pipeline orchestrator: single function composes all stages with timing, logging, and notification"
  - "CI token fallback: expired stored tokens trigger email/password re-auth automatically"
  - "GitHub Actions workflow_dispatch with optional date input for manual catch-up runs"

requirements-completed: [AUTO-01, AUTO-02]

# Metrics
duration: ~20min (includes human verification and additional fixes)
completed: 2026-03-04
---

# Phase 5 Plan 2: Pipeline Orchestrator and CI Summary

**run_full_pipeline orchestrator with GitHub Actions daily cron, Supabase DDL, and end-to-end verified automated Daily Protocol delivery**

## Performance

- **Duration:** ~20 min (includes human verification of end-to-end pipeline in GitHub Actions)
- **Started:** 2026-03-04T05:30:00Z
- **Completed:** 2026-03-04T05:52:00Z
- **Tasks:** 3 (2 auto + 1 human-verify checkpoint)
- **Files modified:** 12

## Accomplishments
- Built run_full_pipeline orchestrator composing ingestion, analysis, and delivery with timing, run logging, and failure notification
- Wired CLI --deliver to run_full_pipeline for single-command end-to-end execution
- Created GitHub Actions workflow with daily cron (5:03 UTC) and manual workflow_dispatch with optional date
- Provided Supabase DDL for garmin_tokens, pipeline_runs, and daily_protocols tables (with RLS enabled)
- Verified end-to-end in GitHub Actions: Garmin auth (token fallback), ingestion, Claude analysis, email delivery, run logging
- Pipeline is fully autonomous -- Daily Protocol email arrives each morning without manual intervention

## Task Commits

Each task was committed atomically:

1. **Task 1: Add run_full_pipeline and wire into CLI** - `a8d8192` (test) + `f76a1eb` (feat)
2. **Task 2: Create GitHub Actions workflow and Supabase DDL** - `2243f13` (feat)
3. **Task 3: Verify end-to-end pipeline automation** - checkpoint (human-verify, approved)

Additional fixes applied during verification:
- `8a4252b` fix(05-02): register CLI entry point in pyproject.toml
- `ed691cb` fix(05-02): fall back to email/password when stored Garmin token expires
- `e2b00cf` fix(05-02): use correct Haiku model ID claude-haiku-4-5-20251001

_Note: Task 1 used TDD (RED: failing tests, GREEN: implementation)_

## Files Created/Modified
- `.github/workflows/daily-pipeline.yml` - GitHub Actions workflow with cron and workflow_dispatch triggers
- `sql/05-pipeline-automation.sql` - DDL for garmin_tokens, pipeline_runs, daily_protocols tables
- `src/biointelligence/pipeline.py` - run_full_pipeline orchestrator with PipelineResult model
- `src/biointelligence/main.py` - CLI --deliver wired to run_full_pipeline, entry point fix
- `src/biointelligence/garmin/client.py` - Token expiry fallback to email/password re-auth
- `src/biointelligence/analysis/client.py` - Corrected Haiku model ID
- `src/biointelligence/config.py` - Updated model ID default
- `pyproject.toml` - Registered CLI entry point for uv run biointelligence
- `tests/test_pipeline.py` - Tests for run_full_pipeline (success, failure stages, logging, notification)
- `tests/test_analysis.py` - Updated model ID references
- `tests/test_analysis_storage.py` - Updated model ID references

## Decisions Made
- run_full_pipeline wraps ingestion/analysis/delivery with timing, run logging, and best-effort failure notification
- CLI --deliver delegates entirely to run_full_pipeline (replaces sequential try/except chain in main.py)
- GitHub Actions cron at 5:03 UTC (off-peak minute) for 6-7 AM CET/CEST daily execution
- Single-job workflow -- CLI already chains stages, no need for multi-job orchestration in GitHub Actions
- Token fallback: when stored Supabase token expires, fall back to email/password re-auth automatically
- CLI entry point registered in pyproject.toml [project.scripts] for uv run biointelligence invocation

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Registered CLI entry point in pyproject.toml**
- **Found during:** Task 3 (end-to-end verification)
- **Issue:** `uv run biointelligence` failed in GitHub Actions -- no CLI entry point was registered
- **Fix:** Added `[project.scripts] biointelligence = "biointelligence.main:main"` to pyproject.toml and fixed main() return type
- **Files modified:** pyproject.toml, src/biointelligence/main.py
- **Commit:** `8a4252b`

**2. [Rule 1 - Bug] Fixed Garmin token expiry fallback**
- **Found during:** Task 3 (end-to-end verification)
- **Issue:** When stored Garmin OAuth tokens expired in Supabase, pipeline crashed instead of falling back to email/password auth
- **Fix:** Added try/except around token-based auth in client.py, falls back to email/password on failure
- **Files modified:** src/biointelligence/garmin/client.py
- **Commit:** `ed691cb`

**3. [Rule 1 - Bug] Corrected Haiku model ID**
- **Found during:** Task 3 (end-to-end verification)
- **Issue:** Analysis engine used incorrect Claude model identifier, causing API errors
- **Fix:** Updated model ID to `claude-haiku-4-5-20251001` in client.py, config.py, and all affected tests
- **Files modified:** src/biointelligence/analysis/client.py, src/biointelligence/config.py, tests/test_analysis.py, tests/test_analysis_storage.py, tests/test_pipeline.py
- **Commit:** `e2b00cf`

---

**Total deviations:** 3 auto-fixed (1 blocking, 2 bugs)
**Impact on plan:** All fixes were necessary for end-to-end pipeline execution. No scope creep.

## Issues Encountered
- GitHub Actions required CLI entry point in pyproject.toml (not just importable module) -- fixed inline
- Stored Garmin OAuth tokens can expire between runs -- added fallback to email/password re-auth
- Claude model ID had changed since initial implementation -- corrected to claude-haiku-4-5-20251001

## User Setup Required

External services were configured during verification:
- **GitHub Actions:** 8 secrets added (GARMIN_EMAIL, GARMIN_PASSWORD, SUPABASE_URL, SUPABASE_KEY, ANTHROPIC_API_KEY, RESEND_API_KEY, SENDER_EMAIL, RECIPIENT_EMAIL)
- **Supabase:** Tables created via SQL DDL (garmin_tokens, pipeline_runs, daily_protocols with RLS enabled)
- **Garmin tokens:** Initial tokens seeded in Supabase garmin_tokens table

## Next Phase Readiness
- Pipeline is fully autonomous -- Daily Protocol delivered each morning via GitHub Actions cron
- Phase 6 (Intelligence Hardening) can build on top of accumulated daily data in pipeline_runs and daily_protocols tables
- 28-day trend windows require 2+ weeks of accumulated data from automated pipeline runs

## Self-Check: PASSED

All 11 referenced files exist on disk. All 6 commit hashes verified in git log.

---
*Phase: 05-pipeline-automation*
*Completed: 2026-03-04*
