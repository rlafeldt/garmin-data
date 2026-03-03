# Phase 5: Pipeline Automation - Research

**Researched:** 2026-03-03
**Domain:** GitHub Actions scheduling, Garmin OAuth token persistence, pipeline observability
**Confidence:** HIGH

## Summary

Phase 5 wraps the existing CLI pipeline (`biointelligence --deliver --json-log`) in a GitHub Actions scheduled workflow. The CLI already handles the full ingestion-analysis-delivery chain with proper exit codes and structured logging. The primary technical challenges are: (1) persisting Garmin OAuth tokens across ephemeral CI runs using Supabase instead of the filesystem, (2) configuring GitHub Actions cron with correct UTC offset for CET morning delivery, and (3) adding failure notification emails via the existing Resend integration.

The codebase is well-structured for this phase. The `garth` library (underlying `garminconnect`) provides `dumps()` and `loads()` methods that serialize OAuth tokens to/from base64-encoded JSON strings, making Supabase storage straightforward. The existing `send_email()` function in `delivery/sender.py` can be reused for failure notifications. The pipeline is already idempotent (upsert semantics throughout), so manual re-runs via `workflow_dispatch` are safe by design.

**Primary recommendation:** Use a single GitHub Actions job that invokes `uv run biointelligence --deliver --json-log`, with garth token persistence via Supabase `garmin_tokens` table, a `pipeline_runs` log table, and failure email via the existing Resend sender.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- GitHub Actions workflow with cron schedule triggering at 7:00 AM CET (~6:00 UTC winter / ~5:00 UTC summer)
- workflow_dispatch trigger for manual runs with optional `--date` parameter
- Existing CLI `--deliver` flag chains the full pipeline; workflow invokes this
- `--json-log` flag enabled in CI for structured log output
- Garmin tokens stored in Supabase table (not local files, not GitHub cache)
- Pipeline reads tokens from Supabase at start, writes refreshed tokens back after successful auth
- Failure email via Resend (reuses existing setup, zero new dependencies)
- Failure email content: which stage failed, error message, target date, link to GitHub Actions logs
- Only fires after all retries exhausted
- Delivery stage failure falls back to GitHub Actions built-in failure notification only
- No pipeline-level retry -- rely on existing tenacity retries within each stage
- No auto catch-up -- each run processes yesterday only; missed days require manual re-run
- Garmin auth token expiry treated same as any other failure
- Pipeline remains idempotent (upsert semantics throughout)
- Primary health signal: Daily Protocol email arrives in inbox
- Supabase run log table for historical tracking (one row per pipeline run)
- Run log captures: date, overall status, failed stage (if any), duration, timestamp
- Structured logs (--json-log) retained in GitHub Actions (90-day retention)
- No dashboards or alerting infrastructure

### Claude's Discretion
- Supabase table schema for token storage and run log
- GitHub Actions workflow YAML structure and job configuration
- How to serialize/deserialize garth tokens for Supabase storage
- Failure email template design (plain text is fine)
- Exact cron expression accounting for UTC offset and DST
- Whether to use a single workflow job or split into multiple jobs

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| AUTO-01 | Daily pipeline runs automatically via cron or scheduled task (pull -> analyze -> deliver) without manual intervention | GitHub Actions cron schedule + `uv run biointelligence --deliver --json-log` invocation; garth token persistence via Supabase enables headless auth |
| AUTO-02 | Pipeline handles failures gracefully with retry logic and sends notification if daily protocol cannot be generated | Existing tenacity retries on all stages; new failure notification email via Resend `send_email()`; run log table for audit trail |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| GitHub Actions | N/A | CI/CD scheduling and execution | Free for public repos, built-in cron + workflow_dispatch, secrets management |
| astral-sh/setup-uv | v7 | Install uv in GitHub Actions runner | Official action from uv maintainers, supports caching and Python version pinning |
| garth | (transitive via garminconnect) | OAuth token serialization | `dumps()`/`loads()` methods produce base64-encoded JSON strings ideal for DB storage |
| resend | >=2.23.0 | Failure notification email | Already integrated in delivery/sender.py with tenacity retry |
| supabase | (existing) | Token persistence + run log | Already integrated in storage/supabase.py with existing patterns |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| structlog | (existing) | Structured JSON logging in CI | `--json-log` flag already implemented, retained in GitHub Actions logs |
| tenacity | (existing) | Retry logic on all external calls | Already configured on Garmin, Supabase, Claude, Resend calls |
| pydantic | (existing) | Run log and token storage models | Follow project pattern of Pydantic models for all data structures |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Supabase for tokens | GitHub Actions cache | Cache eviction after 7 days of inactivity -- tokens would be lost on vacation |
| Supabase for tokens | GitHub Actions secrets (manual update) | Cannot programmatically refresh -- tokens expire after ~1 year |
| Single workflow job | Multi-job workflow | Single job is simpler; no need for artifact passing between jobs; CLI already chains stages |
| GitHub Actions cron | Local crontab on always-on machine | Requires dedicated server; GitHub Actions is already the CI platform |

**Installation:**
No new dependencies required. All libraries are already in `pyproject.toml`. The GitHub Actions workflow uses `astral-sh/setup-uv@v7` and `actions/checkout@v4`.

## Architecture Patterns

### Recommended Project Structure
```
.github/
  workflows/
    daily-pipeline.yml    # Cron + workflow_dispatch workflow
src/biointelligence/
  automation/
    __init__.py           # Lazy imports (project pattern)
    tokens.py             # load_tokens_from_supabase(), save_tokens_to_supabase()
    run_log.py            # log_pipeline_run(), PipelineRunLog model
    notify.py             # send_failure_notification()
  garmin/
    client.py             # Modified: support token string (Supabase) in addition to token dir
  config.py               # New settings: notification_email (optional, defaults to recipient_email)
  pipeline.py             # Modified: wrap full pipeline with run logging and failure notification
  main.py                 # Modified: add top-level exception handler for failure notification
```

### Pattern 1: Garth Token Serialization via Supabase
**What:** Store garth OAuth tokens as a base64-encoded string in a single Supabase row, keyed by a fixed identifier.
**When to use:** Every pipeline run reads tokens at startup and writes refreshed tokens after successful Garmin auth.
**Example:**
```python
# Source: garth http.py (verified from GitHub source)
# garth.Client.dumps() -> base64-encoded JSON string of [oauth1_dict, oauth2_dict]
# garth.Client.loads(s: str) -> restores both tokens from base64 string

# garminconnect Garmin class exposes garth as self.garth
# Garmin.login(tokenstore) accepts:
#   - File path (<=512 chars) -> self.garth.load(path)
#   - Base64 string (>512 chars) -> self.garth.loads(string)

def load_tokens_from_supabase(client: Client) -> str | None:
    """Fetch garth token string from Supabase."""
    result = (
        client.table("garmin_tokens")
        .select("token_data")
        .eq("id", "primary")
        .maybe_single()
        .execute()
    )
    return result.data["token_data"] if result.data else None

def save_tokens_to_supabase(client: Client, garmin: Garmin) -> None:
    """Persist refreshed garth tokens to Supabase."""
    token_data = garmin.garth.dumps()  # base64-encoded JSON string
    client.table("garmin_tokens").upsert(
        {"id": "primary", "token_data": token_data, "updated_at": "now()"},
        on_conflict="id",
    ).execute()
```

### Pattern 2: GitHub Actions Workflow with Dual Triggers
**What:** Single workflow file with both `schedule` (cron) and `workflow_dispatch` (manual) triggers. The manual trigger accepts an optional date input.
**When to use:** The main workflow file.
**Example:**
```yaml
# Source: GitHub Actions docs (events-that-trigger-workflows)
name: Daily Pipeline

on:
  schedule:
    # 6:00 UTC = 7:00 CET (winter) / 7:00 CEST handled by pipeline's timezone logic
    - cron: '0 6 * * *'
  workflow_dispatch:
    inputs:
      date:
        description: 'Target date (YYYY-MM-DD). Leave empty for yesterday.'
        required: false
        type: string

jobs:
  run-pipeline:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v7
        with:
          python-version: "3.12"
          enable-cache: true
          cache-dependency-glob: |
            **/pyproject.toml
            **/uv.lock
      - name: Run pipeline
        env:
          GARMIN_EMAIL: ${{ secrets.GARMIN_EMAIL }}
          GARMIN_PASSWORD: ${{ secrets.GARMIN_PASSWORD }}
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          RESEND_API_KEY: ${{ secrets.RESEND_API_KEY }}
          SENDER_EMAIL: ${{ secrets.SENDER_EMAIL }}
          RECIPIENT_EMAIL: ${{ secrets.RECIPIENT_EMAIL }}
        run: |
          ARGS="--deliver --json-log"
          if [ -n "${{ github.event.inputs.date }}" ]; then
            ARGS="$ARGS --date ${{ github.event.inputs.date }}"
          fi
          uv run biointelligence $ARGS
```

### Pattern 3: Pipeline Run Logging
**What:** Record each pipeline execution in a Supabase `pipeline_runs` table for historical tracking.
**When to use:** Wrapping the main pipeline execution in main.py or pipeline.py.
**Example:**
```python
# Follows existing Pydantic model pattern
class PipelineRunLog(BaseModel):
    """Record of a pipeline execution."""
    date: date                         # Target date processed
    status: str                        # "success" or "failure"
    failed_stage: str | None = None    # "ingestion", "analysis", "delivery", or None
    duration_seconds: float            # Wall clock time
    started_at: str                    # ISO timestamp
    error_message: str | None = None   # Error details if failed

def log_pipeline_run(client: Client, run_log: PipelineRunLog) -> None:
    """Upsert pipeline run to Supabase, keyed on date."""
    client.table("pipeline_runs").upsert(
        run_log.model_dump(mode="json"),
        on_conflict="date",
    ).execute()
```

### Pattern 4: Failure Notification Email
**What:** Send a plain-text email via Resend when the pipeline fails after all retries.
**When to use:** In the top-level exception handler in main.py, only when all retries are exhausted.
**Example:**
```python
def send_failure_notification(
    target_date: date,
    failed_stage: str,
    error_message: str,
    settings: Settings,
) -> None:
    """Send failure notification email via Resend.

    Reuses the existing send_email infrastructure. For delivery-stage failures
    (Resend itself down), this will also fail -- caller should catch and log.
    """
    github_run_url = os.environ.get(
        "GITHUB_SERVER_URL", "https://github.com"
    ) + "/" + os.environ.get(
        "GITHUB_REPOSITORY", ""
    ) + "/actions/runs/" + os.environ.get(
        "GITHUB_RUN_ID", ""
    )

    text = (
        f"BioIntelligence pipeline failed\n\n"
        f"Date: {target_date.isoformat()}\n"
        f"Failed stage: {failed_stage}\n"
        f"Error: {error_message}\n\n"
        f"GitHub Actions: {github_run_url}\n"
    )

    # Reuse existing Resend integration
    send_email(
        html=f"<pre>{html_escape(text)}</pre>",
        text=text,
        subject=f"Pipeline Failed -- {target_date.isoformat()}",
        target_date=target_date,
        settings=settings,
    )
```

### Anti-Patterns to Avoid
- **Storing tokens in GitHub Actions cache:** Cache eviction after 7 days of inactivity means tokens disappear during vacations. Supabase has no such limitation.
- **Pipeline-level retry orchestration:** The project already uses tenacity at every external call site. Adding another retry layer around the full pipeline creates confusion about which level handles what.
- **Auto catch-up for missed days:** Complex state management for minimal value. Manual `workflow_dispatch` with `--date` is simpler and explicit.
- **Multiple GitHub Actions jobs for pipeline stages:** Unnecessary complexity. The CLI already chains stages. Multiple jobs would require artifact passing between steps.
- **Setting `garth` tokens at module import time:** Follow the project pattern of per-call configuration (like `resend.api_key` in sender.py) to maintain test isolation.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| OAuth token serialization | Custom JSON serialization of garth internals | `garth.Client.dumps()` / `loads()` | Base64-encoded JSON string; handles both OAuth1 and OAuth2 tokens atomically |
| Retry logic | Custom retry loops in the workflow | Existing tenacity decorators on all external calls | Already configured with exponential backoff on Garmin, Supabase, Claude, Resend |
| CI/CD scheduling | Custom cron daemon, systemd timer | GitHub Actions `schedule` event | Free, managed, includes secrets management, log retention, failure notifications |
| Python environment setup | Manual pip install in CI | `astral-sh/setup-uv@v7` with `uv run` | Handles Python version, caching, dependency resolution; 10-100x faster than pip |
| Environment configuration | Custom secret injection | GitHub Actions secrets + pydantic-settings | Settings class reads env vars automatically; GitHub Actions injects secrets as env vars |

**Key insight:** The existing codebase already handles nearly all the hard problems (retry, idempotency, structured logging, email delivery). This phase is primarily a thin orchestration wrapper.

## Common Pitfalls

### Pitfall 1: GitHub Actions Cron UTC Confusion
**What goes wrong:** Cron expressions in GitHub Actions are always evaluated in UTC. CET is UTC+1 in winter, UTC+2 in summer (CEST). A fixed cron of `0 6 * * *` (6:00 UTC) delivers at 7:00 CET in winter but 8:00 CEST in summer.
**Why it happens:** GitHub Actions does not support timezone-aware cron expressions.
**How to avoid:** Use `0 5 * * *` (5:00 UTC = 7:00 CEST summer, 6:00 CET winter) as a compromise that delivers at 6-7 AM year-round. Or use two cron entries to cover both DST windows. The pipeline's `_get_yesterday()` already handles timezone correctly for date calculation. The delivery time shifting by 1 hour seasonally is acceptable for a personal tool.
**Warning signs:** Email arrives at unexpected times after DST transition.

### Pitfall 2: Garmin Token Bootstrap (First Run)
**What goes wrong:** The Supabase `garmin_tokens` table is empty on first run. The pipeline needs initial tokens seeded.
**Why it happens:** Garmin requires interactive email/password login for the first authentication. This cannot happen in headless CI.
**How to avoid:** Run the pipeline locally once (`uv run biointelligence --deliver`) which authenticates via email/password and saves tokens to `~/.garminconnect`. Then extract the base64 token string using `garth.Client.dumps()` and seed it into the Supabase table. Provide a one-time seed script or CLI command.
**Warning signs:** First CI run fails with authentication error.

### Pitfall 3: Token Write-Back After Partial Failure
**What goes wrong:** Pipeline reads tokens, authenticates successfully (garth refreshes OAuth2 internally), but then fails during a later stage. If tokens aren't saved back, the old tokens may be stale for the next run.
**Why it happens:** OAuth2 token refresh happens transparently during `client.login()`. If the refreshed token isn't persisted, the next run uses the pre-refresh token.
**How to avoid:** Save tokens back to Supabase immediately after successful Garmin authentication, before proceeding to data extraction. This ensures token refresh is persisted even if later stages fail.
**Warning signs:** Pipeline starts failing after a period of working, with OAuth errors.

### Pitfall 4: GitHub Actions Schedule Drift
**What goes wrong:** Scheduled workflows can be delayed by 10-30 minutes during high-load periods on GitHub's infrastructure.
**Why it happens:** GitHub Actions documentation explicitly warns about delays during "periods of high loads of GitHub Actions workflow runs" especially "at the start of every hour."
**How to avoid:** Schedule at an off-peak minute (e.g., `:03` or `:17` instead of `:00`). For a personal morning protocol, a 15-minute delay is acceptable.
**Warning signs:** Email arrives significantly later than expected time.

### Pitfall 5: Supabase Row-Level Security (RLS)
**What goes wrong:** Supabase tables have RLS enabled by default. API calls return empty results even when data exists.
**Why it happens:** New tables in Supabase have RLS enabled, and without policies the service key bypasses RLS but the anon key does not.
**How to avoid:** The project already uses `supabase_key` (presumably the service role key based on existing working storage). Ensure new tables (`garmin_tokens`, `pipeline_runs`) either have RLS disabled or have appropriate policies. Since this is a personal single-user tool, disabling RLS on these tables is acceptable.
**Warning signs:** Token load returns None even though data was inserted.

### Pitfall 6: `lru_cache` on `get_settings()` in CI
**What goes wrong:** The `get_settings()` function uses `@lru_cache` which caches the first Settings instance. In CI, environment variables are set before the process starts, so this is fine. But if tests modify env vars, the cached settings won't reflect changes.
**Why it happens:** `lru_cache` is permanent for the process lifetime.
**How to avoid:** This is already handled correctly in tests via `Settings(_env_file=None)` with explicit `monkeypatch.setenv`. No action needed for CI -- just awareness.
**Warning signs:** Tests pass individually but fail when run together.

## Code Examples

Verified patterns from the existing codebase and official sources:

### Garth Token Serialization (from garth source code)
```python
# garth/http.py - Client class methods:
#
# def dumps(self) -> str:
#     r = [asdict(self.oauth1_token), asdict(self.oauth2_token)]
#     s = json.dumps(r)
#     return base64.b64encode(s.encode()).decode()
#
# def loads(self, s: str):
#     r = json.loads(base64.b64decode(s))
#     self.oauth1_token = OAuth1Token(**r[0])
#     self.oauth2_token = OAuth2Token(**r[1])
#     self.configure(...)
#
# garminconnect Garmin class:
#   self.garth is a garth.Client instance
#   Garmin.login(tokenstore) auto-detects:
#     - len(tokenstore) <= 512: treat as file path -> self.garth.load(path)
#     - len(tokenstore) > 512: treat as base64 string -> self.garth.loads(string)
```

### Supabase Upsert Pattern (from existing codebase)
```python
# Source: storage/supabase.py and analysis/storage.py (project pattern)
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    retry=retry_if_exception_type((ConnectionError, TimeoutError)),
)
def upsert_to_table(client: Client, table: str, data: dict, conflict_key: str) -> None:
    client.table(table).upsert(data, on_conflict=conflict_key).execute()
```

### GitHub Actions Environment Variables (from project config.py)
```python
# Source: config.py -- Settings class uses pydantic-settings
# All env vars are automatically read by Settings:
#   GARMIN_EMAIL, GARMIN_PASSWORD, SUPABASE_URL, SUPABASE_KEY,
#   ANTHROPIC_API_KEY, RESEND_API_KEY, SENDER_EMAIL, RECIPIENT_EMAIL
# GitHub Actions secrets -> env: mapping provides all values
```

### Existing Pipeline Exit Codes (from main.py)
```python
# Source: main.py -- CLI returns 0 on success, 1 on failure
# GitHub Actions detects non-zero exit codes as step failure
# This is already the correct interface for CI integration
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| pip install in CI | `uv run` with `astral-sh/setup-uv` | 2024-2025 | 10-100x faster dependency installation, built-in caching |
| actions/setup-python + pip | astral-sh/setup-uv with python-version | 2025 | Single action handles both Python and package management |
| actions/checkout@v3 | actions/checkout@v4 | 2024 | Node.js 20 runtime, faster checkout |
| garth manual JSON file handling | garth.dumps()/loads() with base64 | Stable since garth 0.4+ | Single string encapsulates both OAuth tokens |
| workflow_dispatch max 10 inputs | workflow_dispatch supports 25 inputs | Dec 2025 | More flexibility for manual triggers (we only need 1 input) |

**Deprecated/outdated:**
- `actions/checkout@v3`: Use v4 (Node.js 20 runtime)
- `actions/setup-python` alone: Use `astral-sh/setup-uv@v7` which handles both Python and uv
- GitHub Actions cache for token persistence: 7-day eviction makes it unreliable for infrequently-refreshed tokens

## Supabase Schema Recommendations

### garmin_tokens table
```sql
CREATE TABLE garmin_tokens (
    id TEXT PRIMARY KEY DEFAULT 'primary',  -- Single-row table, fixed key
    token_data TEXT NOT NULL,               -- Base64-encoded garth dumps() output
    updated_at TIMESTAMPTZ DEFAULT now()
);
-- No RLS needed (service key access, single-user tool)
```

### pipeline_runs table
```sql
CREATE TABLE pipeline_runs (
    date DATE PRIMARY KEY,                  -- One run per date (idempotent)
    status TEXT NOT NULL,                   -- 'success' or 'failure'
    failed_stage TEXT,                      -- 'ingestion', 'analysis', 'delivery', or NULL
    error_message TEXT,                     -- Error details if failed
    duration_seconds REAL,                  -- Wall clock time
    started_at TIMESTAMPTZ NOT NULL,        -- When the run began
    created_at TIMESTAMPTZ DEFAULT now()
);
-- No RLS needed (service key access, single-user tool)
```

## Cron Expression Analysis

| Expression | UTC Time | CET (Winter) | CEST (Summer) | Notes |
|------------|----------|--------------|---------------|-------|
| `0 6 * * *` | 06:00 | 07:00 | 08:00 | Exact in winter, 1h late in summer |
| `0 5 * * *` | 05:00 | 06:00 | 07:00 | Exact in summer, 1h early in winter |
| `0 5 * * *` | 05:00 | 06:00 | 07:00 | **Recommended**: 6-7 AM year-round |

**Recommendation:** Use `0 5 * * *` (5:00 UTC). This delivers at 7:00 CEST in summer and 6:00 CET in winter. Both are acceptable "morning" times. Avoid `:00` minute mark -- use `3 5 * * *` (5:03 UTC) to dodge peak-hour GitHub Actions contention.

## Single Job vs. Multi-Job Decision

**Recommendation: Single job.**

Rationale:
- The CLI already chains ingestion -> analysis -> delivery via `--deliver`
- No benefit to splitting into separate jobs -- all stages need the same secrets and Python environment
- Multi-job would require artifact passing (token state, analysis results) between jobs
- Single job means simpler YAML and faster execution (no job startup overhead)
- Failure notification can be a final step that runs `if: failure()`

## Open Questions

1. **Garmin MFA and Token Bootstrap**
   - What we know: garth requires initial email/password login; tokens refresh transparently after that; tokens last approximately 1 year
   - What's unclear: Whether the user's Garmin account has MFA enabled (STATE.md flags this as a concern)
   - Recommendation: Document the bootstrap process. If MFA is enabled, the user must run locally once to complete MFA flow, then extract tokens. A seed script/CLI command simplifies this.

2. **DST Cron Handling Preference**
   - What we know: No way to set timezone in GitHub Actions cron. Fixed UTC cron shifts by 1 hour at DST transitions.
   - What's unclear: Whether the user prefers consistent UTC time (email shifts) or wants two cron entries
   - Recommendation: Use single `3 5 * * *` expression. 6-7 AM year-round is acceptable for a personal tool. Document the DST behavior.

3. **Supabase Table Creation**
   - What we know: Project uses Supabase with existing tables (daily_metrics, activities, daily_protocols)
   - What's unclear: Whether tables are created via migrations, Supabase dashboard, or SQL scripts
   - Recommendation: Provide SQL CREATE TABLE statements in the plan. User can execute via Supabase SQL editor (matches personal tool approach).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest with pytest-mock |
| Config file | `pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `uv run pytest tests/ -x -q` |
| Full suite command | `uv run pytest tests/ -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AUTO-01 | Token load from Supabase | unit | `uv run pytest tests/test_automation.py::TestTokenPersistence -x` | No -- Wave 0 |
| AUTO-01 | Token save to Supabase after auth | unit | `uv run pytest tests/test_automation.py::TestTokenPersistence -x` | No -- Wave 0 |
| AUTO-01 | Modified garmin client uses Supabase tokens | unit | `uv run pytest tests/test_client.py::TestSupabaseTokenAuth -x` | No -- Wave 0 |
| AUTO-01 | Pipeline runs via CLI with --deliver | unit | `uv run pytest tests/test_pipeline.py -x` (existing, extended) | Yes (partial) |
| AUTO-02 | Failure notification email sent on pipeline error | unit | `uv run pytest tests/test_automation.py::TestFailureNotification -x` | No -- Wave 0 |
| AUTO-02 | Pipeline run logged to Supabase | unit | `uv run pytest tests/test_automation.py::TestRunLog -x` | No -- Wave 0 |
| AUTO-02 | Delivery failure falls back to GH Actions notification | unit | `uv run pytest tests/test_automation.py::TestFailureNotification -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/ -x -q`
- **Per wave merge:** `uv run pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_automation.py` -- covers token persistence, run logging, failure notification
- [ ] Extend `tests/test_client.py` -- covers Supabase token auth path in garmin client
- [ ] Extend `tests/test_pipeline.py` -- covers run logging integration in pipeline

## Sources

### Primary (HIGH confidence)
- [garth/http.py source](https://github.com/matin/garth/blob/main/src/garth/http.py) - `dumps()`/`loads()` methods verified: base64-encoded JSON of [oauth1_dict, oauth2_dict]
- [garminconnect source](https://github.com/cyberjunky/python-garminconnect) - `Garmin.login(tokenstore)` auto-detects path vs base64 string by length (<=512 = path, >512 = base64)
- [GitHub Actions workflow syntax](https://docs.github.com/actions/using-workflows/workflow-syntax-for-github-actions) - cron in UTC, minimum 5-minute interval, workflow_dispatch inputs
- [GitHub Actions events](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows) - schedule delay warnings, workflow_dispatch up to 25 inputs
- [astral-sh/setup-uv](https://github.com/astral-sh/setup-uv) - v7, enable-cache, python-version support
- Project source code: `pipeline.py`, `main.py`, `config.py`, `garmin/client.py`, `delivery/sender.py`, `storage/supabase.py` -- existing patterns verified

### Secondary (MEDIUM confidence)
- [Supabase Python upsert docs](https://supabase.com/docs/reference/python/upsert) - upsert with on_conflict parameter
- [GitHub Actions Supabase guide](https://supabase.com/docs/guides/functions/examples/github-actions) - secrets management pattern

### Tertiary (LOW confidence)
- Garmin token refresh frequency (~1 year) -- based on community reports, not official documentation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already in use, no new dependencies needed
- Architecture: HIGH -- straightforward wrapper around existing CLI, garth API verified from source
- Pitfalls: HIGH -- DST behavior documented, token bootstrap well understood, GitHub Actions cron limitations documented
- Supabase schema: MEDIUM -- follows project patterns but specific column choices are recommendations
- Garmin token lifetime: LOW -- community-reported ~1 year, not officially documented

**Research date:** 2026-03-03
**Valid until:** 2026-04-03 (30 days -- stable domain, no fast-moving dependencies)
