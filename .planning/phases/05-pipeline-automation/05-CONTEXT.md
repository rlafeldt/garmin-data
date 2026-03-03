# Phase 5: Pipeline Automation - Context

**Gathered:** 2026-03-03
**Status:** Ready for planning

<domain>
## Phase Boundary

The entire pull-analyze-deliver pipeline runs automatically each morning via GitHub Actions without manual intervention. Covers scheduling, Garmin token persistence across runs, failure notification, pipeline run logging, and manual dispatch. Intelligence hardening (28-day trends, anomaly detection) is a separate phase.

</domain>

<decisions>
## Implementation Decisions

### Scheduling approach
- GitHub Actions workflow with cron schedule
- Cron triggers at 7:00 AM CET (~6:00 UTC winter / ~5:00 UTC summer)
- workflow_dispatch trigger for manual runs — accepts optional `--date` parameter for re-processing specific dates
- Existing CLI `--deliver` flag chains the full pipeline (ingestion -> analysis -> delivery) — workflow invokes this
- `--json-log` flag enabled in CI for structured log output

### Garmin token persistence
- Store serialized garth OAuth tokens in a Supabase table (not local files, not GitHub cache)
- Pipeline reads tokens from Supabase at start, writes refreshed tokens back after successful auth
- Eliminates cache eviction risk (GitHub caches expire after 7 days of inactivity)
- Garmin tokens refresh ~yearly — storage durability matters more than access speed

### Failure notifications
- Failure email sent via Resend (reuses existing Resend setup — zero new dependencies)
- Email content: which stage failed (ingestion/analysis/delivery), error message, target date, link to check GitHub Actions logs
- Only fires after all retries are exhausted — no noise for transient issues that tenacity recovers from
- Delivery stage failure (Resend itself down): fall back to GitHub Actions built-in failure notification only — can't email about email failure

### Retry & recovery
- No pipeline-level retry — rely on existing tenacity retries within each stage (Garmin API, Supabase, Claude API, Resend)
- No auto catch-up — each run processes yesterday only; missed days require manual re-run via workflow_dispatch
- Garmin auth token expiry treated same as any other failure — standard notification, manual re-authentication
- Pipeline remains idempotent — safe to re-run for the same date without side effects (upsert semantics throughout)

### Monitoring & observability
- Primary health signal: Daily Protocol email arrives in inbox
- Supabase run log table for historical tracking — one row per pipeline run
- Run log captures essentials only: date, overall status (success/failure), failed stage (if any), duration, timestamp
- Structured logs (--json-log) retained in GitHub Actions (90-day retention) — no external log service
- No dashboards or alerting infrastructure — personal tool, email arrival is sufficient

### Claude's Discretion
- Supabase table schema for token storage and run log
- GitHub Actions workflow YAML structure and job configuration
- How to serialize/deserialize garth tokens for Supabase storage
- Failure email template design (plain text is fine)
- Exact cron expression accounting for UTC offset and DST
- Whether to use a single workflow job or split into multiple jobs

</decisions>

<specifics>
## Specific Ideas

- The CLI already supports `--deliver --json-log --date YYYY-MM-DD` — the GitHub Actions workflow is essentially a thin wrapper around this command
- Garmin token persistence in Supabase solves the STATE.md blocker ("GitHub Actions token persistence approach needs design")
- workflow_dispatch with date input enables both testing and catch-up without any auto-catch-up complexity
- The run log table enables future features (weekly summary of pipeline health, uptime tracking) without blocking v1

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `main.py` CLI: `--deliver` chains ingestion -> analysis -> delivery, `--json-log` for structured output, `--date` for specific dates
- `pipeline.py`: `run_ingestion()`, `run_analysis()`, `run_delivery()` — complete pipeline functions with proper error handling
- `Settings` class (config.py): pydantic-settings with .env loading — all secrets (Garmin, Supabase, Anthropic, Resend) already configured
- `send_email()` in delivery/sender.py: Resend integration with retry — reusable for failure notification emails
- `get_supabase_client()` in storage/supabase.py: existing Supabase client factory — reuse for token storage and run logging
- structlog configured throughout with JSON output option

### Established Patterns
- pydantic-settings with .env for configuration — GitHub Actions sets env vars from secrets
- tenacity for retry logic on all external API calls (Garmin, Supabase, Claude, Resend)
- Pydantic models for all data structures — run log and token storage models follow this
- Pipeline functions return result models (IngestionResult, AnalysisResult, DeliveryResult) with success flags

### Integration Points
- `garmin_token_dir` in Settings (currently `~/.garminconnect`): needs adaptation to read/write from Supabase instead of local filesystem
- CLI `main()` returns exit code 0/1 — GitHub Actions uses this for success/failure detection
- Supabase: two new tables needed (token storage, run log)
- delivery/sender.py: extend or add a function for failure notification email (simpler than Daily Protocol email)

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 05-pipeline-automation*
*Context gathered: 2026-03-03*
