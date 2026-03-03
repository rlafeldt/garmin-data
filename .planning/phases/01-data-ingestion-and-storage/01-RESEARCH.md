# Phase 1: Data Ingestion and Storage - Research

**Researched:** 2026-03-03
**Domain:** Garmin biometric data ingestion, validation, and Supabase persistence
**Confidence:** HIGH

## Summary

Phase 1 establishes the data foundation for the entire BioIntelligence system. It covers pulling daily biometric data from Garmin Connect (training, recovery, sleep, stress, general metrics), validating data completeness, normalizing through Pydantic models, and persisting to Supabase PostgreSQL with idempotent upserts. Authentication must persist across runs via garth OAuth token management.

The technical risk is concentrated in two areas: (1) Garmin authentication reliability -- the unofficial API uses reverse-engineered OAuth that can break without notice, and MFA-enabled accounts have a known token refresh failure (Issue #312); (2) silent empty responses -- Garmin returns HTTP 200 with null/empty data when the watch has not synced or server-side processing is incomplete. Both require defensive coding patterns built into the ingestion layer from day one.

The stack is well-established: garminconnect 0.2.38 (Python) is the de facto standard for personal Garmin data access with 105+ endpoints, used by Home Assistant and thousands of users. Supabase's Python client (2.28.0) provides a clean REST-based upsert interface. The combination of tenacity for retries, structlog for structured logging, and Pydantic for validation gives a robust pipeline with minimal custom code.

**Primary recommendation:** Build a sequential extract-validate-store pipeline using garminconnect for extraction, Pydantic models for validation/normalization, and Supabase REST client for idempotent upsert by date. Persist garth OAuth tokens to disk, implement completeness checks before storage, and store raw JSONB alongside normalized columns.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Use personal Garmin account (not a dedicated automation account)
- MFA status unknown -- check during setup; disable MFA if enabled (required for reliable OAuth token refresh per Issue #312)
- Device: Garmin Fenix 7 series -- full sensor suite confirmed, all 11+ target metrics available
- Pull all available metric categories from day one -- training, recovery, sleep, stress, general metrics
- Activity data: summary level only (type, duration, distance, avg/max HR, training effect, training load, calories) -- no lap/split detail
- Primary training types: cycling and strength training (1-2 activities/day)
- Store whatever Garmin returns, flag gaps with nulls and log warnings -- never reject a whole day for missing metrics
- No-wear days: store a record with a no-data flag; trend calculations in later phases skip these days
- Pipeline timing: run at ~7:00 AM CET to allow overnight sleep data sync (user wakes 5-6 AM)
- Timezone: Europe/Berlin (CET/CEST) -- all timestamps normalized to UTC at ingestion, pipeline scheduling in local time
- Existing Supabase account -- create a dedicated project for BioIntelligence (clean isolation)
- Region: eu-central-1 (Frankfurt) -- closest to user
- Free tier -- 500 MB database is more than sufficient for single-user daily biometric data

### Claude's Discretion
- Exact Supabase table schema design (wide denormalized vs normalized -- research recommends wide with raw JSONB)
- Pydantic validation model structure for Garmin data normalization
- Retry strategy details (backoff timing, max retries)
- Logging format and levels
- Token persistence mechanism

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DATA-01 | Pull training activities, HR zones, training effect, training load, training status, VO2 max trend | garminconnect methods: get_stats(), get_heart_rates(), get_training_status(), get_max_metrics(), get_activities_by_date() -- all verified in library source |
| DATA-02 | Pull recovery metrics: overnight HRV, Body Battery, resting HR | garminconnect methods: get_hrv_data(), get_body_battery(), get_heart_rates() -- confirmed available for Fenix 7 |
| DATA-03 | Pull sleep data: duration, stages, score, SpO2, respiration rate | garminconnect methods: get_sleep_data(), get_spo2_data(), get_respiration_data() -- sleep data attributes overnight to wake-up date |
| DATA-04 | Pull stress data: all-day score, duration breakdown, relaxation time | garminconnect method: get_stress_data() -- returns avg_stress, high/medium/low stress minutes |
| DATA-05 | Pull general metrics: steps, intensity minutes, calories | garminconnect method: get_stats() -- returns steps, calories, intensity minutes in daily summary |
| DATA-06 | Validate data completeness, detect silent empty Garmin responses | Pydantic validation models + completeness scoring: count non-null fields, log warnings if below threshold |
| DATA-07 | Store in Supabase with wide denormalized schema and upsert-by-date idempotency | Supabase Python client .upsert() with on_conflict="date" on UNIQUE-constrained date column |
| DATA-08 | Garmin auth token persistence and refresh without manual intervention | garth library: OAuth1 tokens valid ~1 year, saved to ~/.garminconnect, auto-refresh of OAuth2 tokens |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.12+ | Runtime | All dependencies support 3.12; avoids 3.13 edge cases |
| garminconnect | 0.2.38 | Garmin Connect API wrapper | Only maintained unofficial Python client, 105+ endpoints, used by Home Assistant, actively maintained (Jan 2026 release) |
| garth | 0.5.x (transitive) | Garmin OAuth authentication | Installed with garminconnect; handles OAuth1/OAuth2 token persistence and auto-refresh |
| supabase | 2.28.0 | Supabase REST client | Official Python client for Supabase; REST-based upsert, no connection pooling needed |
| pydantic | 2.x (transitive) | Data validation & schemas | Installed with pydantic-settings; use for Garmin data models and normalization |
| pydantic-settings | 2.13.1 | Configuration (.env loading) | Type-safe settings from .env files; validates config at startup |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| structlog | 24.x+ | Structured logging | JSON logs for pipeline debugging; colored console in dev |
| tenacity | 9.x | Retry logic | Exponential backoff on Garmin API calls and Supabase writes |
| uv | latest | Package manager | Project init, dependency management, virtual environments |
| ruff | latest | Linting + formatting | Replaces flake8/black/isort; configure in pyproject.toml |
| pytest | latest | Testing | Mock Garmin API responses with saved JSON fixtures |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| supabase (REST) | psycopg2 + SQLAlchemy | Direct Postgres connection needed only for complex SQL; overkill for daily CRUD |
| structlog | loguru | Loguru is simpler but structlog's JSON output is better for pipeline debugging |
| garminconnect | garmy | garmy is newer with AI focus but fewer endpoints and less community usage |

**Installation:**
```bash
uv init biointelligence
cd biointelligence
uv add garminconnect supabase pydantic-settings structlog tenacity
uv add --dev ruff pytest pytest-mock mypy
```

## Architecture Patterns

### Recommended Project Structure
```
src/biointelligence/
    __init__.py
    main.py              # CLI entry point: run pipeline for a date
    config.py            # pydantic-settings: env vars, Supabase URL, etc.
    garmin/
        __init__.py
        client.py        # Garmin auth, token persistence, API wrapper
        extractors.py    # Per-category data extraction functions
        models.py        # Pydantic models for raw Garmin data normalization
    storage/
        __init__.py
        supabase.py      # Supabase client, upsert operations
        schema.sql       # Table creation DDL (run via Supabase SQL editor)
    pipeline.py          # Orchestrator: extract -> validate -> store
    logging.py           # structlog configuration
```

### Pattern 1: Sequential Extract-Validate-Store Pipeline
**What:** Each pipeline run extracts all metrics for a date, validates via Pydantic, and upserts to Supabase. Stages run sequentially -- failure in extraction stops the pipeline early.
**When to use:** Always. This is the core pattern for Phase 1.
**Example:**
```python
# Source: Architecture patterns from project research + garminconnect library source
import datetime
from garminconnect import Garmin

def run_ingestion(target_date: datetime.date) -> IngestionResult:
    """Run the complete data ingestion pipeline for a single date."""
    # Step 1: Authenticate (load persisted tokens)
    client = get_authenticated_client()

    # Step 2: Extract all metric categories
    raw_data = extract_all_metrics(client, target_date)

    # Step 3: Validate and normalize via Pydantic
    daily_record = normalize_daily_metrics(raw_data, target_date)
    activities = normalize_activities(raw_data.get("activities", []), target_date)

    # Step 4: Check completeness and log warnings
    completeness = assess_completeness(daily_record)
    if completeness.missing_critical:
        log.warning("incomplete_data", date=target_date, missing=completeness.missing_fields)

    # Step 5: Upsert to Supabase
    upsert_daily_metrics(daily_record)
    upsert_activities(activities, target_date)

    return IngestionResult(date=target_date, completeness=completeness)
```

### Pattern 2: Garmin Authentication with Token Persistence
**What:** Authenticate once interactively, persist tokens to disk, load tokens on subsequent runs. garth handles OAuth2 refresh automatically.
**When to use:** Every pipeline run.
**Example:**
```python
# Source: garminconnect README + garth GitHub docs
import os
from garminconnect import (
    Garmin,
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
)

TOKENDIR = os.path.expanduser("~/.garminconnect")

def get_authenticated_client() -> Garmin:
    """Get an authenticated Garmin client, loading persisted tokens."""
    if os.path.isdir(TOKENDIR):
        # Load persisted tokens (no password needed)
        client = Garmin()
        client.login(TOKENDIR)
    else:
        # First-time login (interactive)
        email = os.environ["GARMIN_EMAIL"]
        password = os.environ["GARMIN_PASSWORD"]
        client = Garmin(email, password)
        client.login()
        client.garth.dump(TOKENDIR)
        # Secure token files
        os.chmod(TOKENDIR, 0o700)
    return client
```

### Pattern 3: Per-Category Extraction with Individual Error Handling
**What:** Extract each metric category (sleep, HRV, stress, etc.) independently. If one fails, log a warning and continue -- never let a single API failure block the entire ingestion.
**When to use:** During the extraction phase.
**Example:**
```python
# Source: garminconnect __init__.py method signatures + project research
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    retry=retry_if_exception_type((GarminConnectConnectionError, GarminConnectTooManyRequestsError)),
)
def _fetch_with_retry(client: Garmin, method_name: str, date_str: str) -> dict | None:
    """Call a garminconnect method with retry logic."""
    method = getattr(client, method_name)
    return method(date_str)

def extract_all_metrics(client: Garmin, target_date: datetime.date) -> dict:
    """Extract all metric categories, handling per-category failures gracefully."""
    date_str = target_date.isoformat()  # "YYYY-MM-DD" format required
    raw = {}

    endpoints = {
        "stats": "get_stats",
        "heart_rates": "get_heart_rates",
        "sleep": "get_sleep_data",
        "hrv": "get_hrv_data",
        "body_battery": "get_body_battery",
        "stress": "get_stress_data",
        "spo2": "get_spo2_data",
        "respiration": "get_respiration_data",
        "training_status": "get_training_status",
        "training_readiness": "get_training_readiness",
        "max_metrics": "get_max_metrics",
    }

    for key, method_name in endpoints.items():
        try:
            raw[key] = _fetch_with_retry(client, method_name, date_str)
        except Exception as e:
            log.warning("extraction_failed", metric=key, error=str(e))
            raw[key] = None

    # Activities use a different signature (date range)
    try:
        raw["activities"] = client.get_activities_by_date(date_str, date_str)
    except Exception as e:
        log.warning("extraction_failed", metric="activities", error=str(e))
        raw["activities"] = []

    return raw
```

### Pattern 4: Supabase Upsert by Date
**What:** Use Supabase Python client's `.upsert()` with `on_conflict="date"` for idempotent writes. The `date` column has a UNIQUE constraint. Running the pipeline twice overwrites, never duplicates.
**When to use:** All database writes.
**Example:**
```python
# Source: Supabase Python docs (https://supabase.com/docs/reference/python/upsert)
from supabase import create_client

def upsert_daily_metrics(record: DailyMetrics) -> None:
    """Upsert a daily metrics record, keyed on date."""
    supabase = create_client(settings.supabase_url, settings.supabase_key)

    response = (
        supabase.table("daily_metrics")
        .upsert(
            record.model_dump(mode="json"),
            on_conflict="date",
        )
        .execute()
    )
```

### Pattern 5: Pydantic Models for Garmin Data Normalization
**What:** Define Pydantic models that map raw Garmin API JSON to typed, validated fields. Handle missing fields gracefully with `Optional` types and defaults of `None`.
**When to use:** Between extraction and storage.
**Example:**
```python
# Source: Garmin API field names from garminconnect source + Supabase schema design from research
from pydantic import BaseModel, Field
from datetime import date as DateType
from typing import Optional, Any

class DailyMetrics(BaseModel):
    """Normalized daily metrics for Supabase storage."""
    date: DateType

    # Sleep
    total_sleep_seconds: Optional[int] = None
    deep_sleep_seconds: Optional[int] = None
    light_sleep_seconds: Optional[int] = None
    rem_sleep_seconds: Optional[int] = None
    awake_seconds: Optional[int] = None
    sleep_score: Optional[int] = None

    # HRV
    hrv_overnight_avg: Optional[float] = None
    hrv_overnight_max: Optional[float] = None
    hrv_status: Optional[str] = None  # BALANCED, UNBALANCED, LOW, POOR

    # Body Battery
    body_battery_morning: Optional[int] = None
    body_battery_max: Optional[int] = None
    body_battery_min: Optional[int] = None

    # Heart Rate
    resting_hr: Optional[int] = None
    max_hr: Optional[int] = None
    avg_hr: Optional[int] = None

    # Stress
    avg_stress_level: Optional[int] = None
    high_stress_minutes: Optional[int] = None
    rest_stress_minutes: Optional[int] = None

    # Training
    training_load_7d: Optional[float] = None
    training_status: Optional[str] = None
    vo2_max: Optional[float] = None

    # General
    steps: Optional[int] = None
    calories_total: Optional[int] = None
    calories_active: Optional[int] = None
    intensity_minutes: Optional[int] = None
    spo2_avg: Optional[float] = None
    respiration_rate_avg: Optional[float] = None

    # Metadata
    raw_data: Optional[dict[str, Any]] = None  # Full Garmin response for debugging
    is_no_wear: bool = False  # Flag for days without device wear
    completeness_score: Optional[float] = None  # Fraction of non-null fields

class Activity(BaseModel):
    """Normalized activity record."""
    date: DateType
    activity_type: str
    name: Optional[str] = None
    duration_seconds: Optional[int] = None
    distance_meters: Optional[float] = None
    avg_hr: Optional[int] = None
    max_hr: Optional[int] = None
    calories: Optional[int] = None
    training_effect_aerobic: Optional[float] = None
    training_effect_anaerobic: Optional[float] = None
    vo2_max_activity: Optional[float] = None
    raw_data: Optional[dict[str, Any]] = None
```

### Anti-Patterns to Avoid
- **Re-authenticating from credentials every run:** Triggers Garmin rate limits (429 errors, 1-hour lockout). Always persist and reuse tokens.
- **Using INSERT instead of UPSERT:** Pipeline retries create duplicate rows. Always use upsert with date conflict resolution.
- **Rejecting entire days for partial data:** User decision is "store whatever Garmin returns, flag gaps." Never discard a day because one metric is missing.
- **Sending all raw API responses directly to Supabase:** Normalize through Pydantic first; store raw JSONB alongside for debugging but never as the primary data.
- **Ignoring HTTP 200 with empty/null body:** Garmin returns 200 even when data is unavailable. Always validate response content, not just status code.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| OAuth token management | Custom token refresh/persistence | garth (via garminconnect) | Handles OAuth1/OAuth2 lifecycle, token storage, auto-refresh; ~1 year validity |
| Retry with backoff | Custom while loops with sleep | tenacity decorators | Handles exponential backoff, max attempts, exception filtering, retry logging |
| Data validation | Manual dict key checking | Pydantic models with Optional fields | Type coercion, validation errors, serialization to dict for Supabase |
| Structured logging | print statements or logging.basicConfig | structlog with JSON renderer | Machine-parseable logs, context binding, development vs production renderers |
| Configuration management | Manual os.environ reads | pydantic-settings | .env file loading, type validation, default values, nested settings |
| Date format handling | String manipulation | datetime.date.isoformat() | garminconnect requires "YYYY-MM-DD" strings; use standard library |

**Key insight:** The garminconnect + garth combination handles the most complex part (Garmin SSO authentication) and returns plain Python dicts. Pydantic handles the next hardest part (normalizing inconsistent API responses). Supabase REST handles the storage. There is very little custom "glue" code needed.

## Common Pitfalls

### Pitfall 1: Garmin Authentication Breaks on MFA Accounts
**What goes wrong:** MFA-enabled Garmin accounts fail with "OAuth1 token is required for OAuth2 refresh" on token refresh (documented in GitHub Issue #312, Dec 2025).
**Why it happens:** Garmin changed their auth flow and the MFA path interacts differently with garth's token refresh mechanism.
**How to avoid:** User decided to check MFA status during setup and disable if enabled. Verify this on first run. Use non-MFA account for automation.
**Warning signs:** GarminConnectAuthenticationError after tokens were previously working; 401/403 responses.

### Pitfall 2: Silent Empty Responses from Garmin (HTTP 200, No Data)
**What goes wrong:** Garmin returns HTTP 200 with empty body, null values, or missing fields. The pipeline stores empty records that corrupt trend analysis.
**Why it happens:** Watch hasn't synced (Bluetooth), server-side processing lag (overnight metrics not ready until mid-morning), or endpoint migration.
**How to avoid:** Implement completeness scoring -- count non-null critical fields (HRV, sleep duration, Body Battery, stress, resting HR). Log a warning if below threshold. Pipeline runs at 7 AM CET per user decision, giving time for overnight sync.
**Warning signs:** Records with all-null metric fields; completeness score below 0.3; response JSON body under 100 bytes.

### Pitfall 3: Timezone and Date Boundary Confusion
**What goes wrong:** Sleep data spans two calendar dates. Garmin timestamps are inconsistent (UTC, local time, Unix timestamps). Data gets attributed to the wrong day.
**Why it happens:** Garmin's API returns different timestamp formats per endpoint. Sleep from Monday night is attributed to Tuesday's wake-up date.
**How to avoid:** Normalize all timestamps to UTC at ingestion. Follow Garmin's convention: sleep is attributed to the wake-up date. Store both the raw Garmin timestamp and normalized UTC. The user's timezone is Europe/Berlin (CET/CEST).
**Warning signs:** Days with zero sleep data adjacent to days with double sleep data; sudden 1-hour shifts twice yearly (DST).

### Pitfall 4: Rate Limiting on Garmin API
**What goes wrong:** Making too many API calls too quickly triggers 429 "Too Many Requests" errors with ~1 hour lockout.
**Why it happens:** Garmin rate limits the unofficial API at approximately 1 request per 5 minutes for some endpoints. Batch-fetching 11+ endpoints in quick succession can trigger this.
**How to avoid:** Use tenacity retry with exponential backoff (min=2s, max=60s). Batch all endpoint calls in a single authenticated session (no re-auth between calls). Add small delays between calls if needed (1-2 seconds). Never re-authenticate from credentials on retry.
**Warning signs:** GarminConnectTooManyRequestsError exceptions; HTTP 429 responses.

### Pitfall 5: Supabase Upsert Requires UNIQUE Constraint
**What goes wrong:** Calling `.upsert(on_conflict="date")` without a UNIQUE constraint on the `date` column throws PostgreSQL error 42P10.
**How to avoid:** Create the `date` column with `UNIQUE NOT NULL` in the table DDL. Run the schema SQL via Supabase SQL Editor before first pipeline run. The constraint must exist before any upsert call.
**Warning signs:** "there is no unique or exclusion constraint matching the ON CONFLICT specification" error.

### Pitfall 6: garminconnect Endpoint Deprecation
**What goes wrong:** Garmin migrates endpoints (e.g., "modern dashboard" changes). Library methods return different JSON structures or empty responses.
**Why it happens:** Garmin evolves their web frontend; backend endpoints change. Library updates lag by days/weeks.
**How to avoid:** Pin garminconnect version. Store raw JSONB responses alongside normalized data. Validate response shape via Pydantic (malformed data fails validation loudly). Subscribe to library releases for breaking changes.
**Warning signs:** Previously-populated fields becoming null; JSON structure changes; library changelog mentioning endpoint migrations.

## Code Examples

### Structlog Configuration for Pipeline
```python
# Source: structlog docs (https://www.structlog.org/en/stable/logging-best-practices.html)
import sys
import structlog

def configure_logging(json_output: bool = False) -> None:
    """Configure structlog for pipeline logging."""
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if json_output:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(0),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=True,
    )
```

### Completeness Assessment
```python
# Source: Project research PITFALLS.md + CONTEXT.md user decisions
def assess_completeness(record: DailyMetrics) -> CompletenessResult:
    """Assess data completeness of a daily record."""
    critical_fields = [
        "total_sleep_seconds", "hrv_overnight_avg", "body_battery_morning",
        "resting_hr", "avg_stress_level", "steps",
    ]
    supplementary_fields = [
        "deep_sleep_seconds", "light_sleep_seconds", "rem_sleep_seconds",
        "sleep_score", "hrv_status", "body_battery_max", "body_battery_min",
        "max_hr", "avg_hr", "high_stress_minutes", "rest_stress_minutes",
        "training_load_7d", "vo2_max", "calories_total", "spo2_avg",
        "respiration_rate_avg",
    ]

    data = record.model_dump()
    critical_present = sum(1 for f in critical_fields if data.get(f) is not None)
    supplementary_present = sum(1 for f in supplementary_fields if data.get(f) is not None)

    total = len(critical_fields) + len(supplementary_fields)
    present = critical_present + supplementary_present
    score = present / total if total > 0 else 0.0

    missing = [f for f in critical_fields if data.get(f) is None]

    # Detect no-wear: if ALL critical fields are null, flag as no-wear
    is_no_wear = critical_present == 0

    return CompletenessResult(
        score=score,
        critical_present=critical_present,
        critical_total=len(critical_fields),
        missing_critical=missing,
        is_no_wear=is_no_wear,
    )
```

### Supabase Table Schema (DDL)
```sql
-- Source: Architecture research ARCHITECTURE.md schema design
-- Run via Supabase SQL Editor before first pipeline run

-- Core daily metrics table (wide denormalized)
CREATE TABLE daily_metrics (
    id BIGSERIAL PRIMARY KEY,
    date DATE UNIQUE NOT NULL,

    -- Sleep
    total_sleep_seconds INTEGER,
    deep_sleep_seconds INTEGER,
    light_sleep_seconds INTEGER,
    rem_sleep_seconds INTEGER,
    awake_seconds INTEGER,
    sleep_score INTEGER,

    -- HRV
    hrv_overnight_avg FLOAT,
    hrv_overnight_max FLOAT,
    hrv_status TEXT,

    -- Body Battery
    body_battery_morning INTEGER,
    body_battery_max INTEGER,
    body_battery_min INTEGER,

    -- Heart Rate
    resting_hr INTEGER,
    max_hr INTEGER,
    avg_hr INTEGER,

    -- Stress
    avg_stress_level INTEGER,
    high_stress_minutes INTEGER,
    rest_stress_minutes INTEGER,

    -- Training
    training_load_7d FLOAT,
    training_status TEXT,
    vo2_max FLOAT,

    -- General
    steps INTEGER,
    calories_total INTEGER,
    calories_active INTEGER,
    intensity_minutes INTEGER,
    spo2_avg FLOAT,
    respiration_rate_avg FLOAT,

    -- Metadata
    raw_data JSONB,              -- Full Garmin responses for debugging/reprocessing
    is_no_wear BOOLEAN DEFAULT FALSE,
    completeness_score FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_daily_metrics_date ON daily_metrics(date DESC);

-- Activities table (1:many with date)
CREATE TABLE activities (
    id BIGSERIAL PRIMARY KEY,
    date DATE NOT NULL,
    activity_type TEXT NOT NULL,
    name TEXT,
    duration_seconds INTEGER,
    distance_meters FLOAT,
    avg_hr INTEGER,
    max_hr INTEGER,
    calories INTEGER,
    training_effect_aerobic FLOAT,
    training_effect_anaerobic FLOAT,
    vo2_max_activity FLOAT,
    raw_data JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_activities_date ON activities(date DESC);

-- updated_at trigger for daily_metrics
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER set_updated_at
    BEFORE UPDATE ON daily_metrics
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

### Configuration with pydantic-settings
```python
# Source: pydantic-settings docs + project conventions
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Application configuration loaded from .env file."""
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Garmin
    garmin_email: str
    garmin_password: str
    garmin_token_dir: str = "~/.garminconnect"

    # Supabase
    supabase_url: str
    supabase_key: str  # anon key or service_role key

    # Pipeline
    target_timezone: str = "Europe/Berlin"
    log_json: bool = False  # True for production, False for development
```

### Activities Upsert Strategy
```python
# Source: Supabase Python docs + idempotency requirements
def upsert_activities(activities: list[Activity], target_date: datetime.date) -> None:
    """Upsert activities for a date. Delete existing, then insert fresh."""
    supabase = create_client(settings.supabase_url, settings.supabase_key)

    # Delete existing activities for this date (idempotent re-run)
    supabase.table("activities").delete().eq("date", target_date.isoformat()).execute()

    # Insert new activities
    if activities:
        records = [a.model_dump(mode="json") for a in activities]
        supabase.table("activities").insert(records).execute()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| garminconnect 0.1.x with custom auth | garminconnect 0.2.x with garth | 2023-2024 | garth handles all OAuth; tokens valid ~1 year vs days |
| Garmin SSO username/password per request | Persistent OAuth1/OAuth2 tokens | garth 0.5.x | Eliminates rate limit triggers from re-authentication |
| pip + requirements.txt | uv (package manager) | 2024-2025 | 10-100x faster installs, lockfiles, replaces pip+venv+pyenv |
| Black + Flake8 + isort | ruff (all-in-one) | 2024-2025 | Single Rust-based tool, much faster |
| pydantic v1 | pydantic v2 | 2023 | Breaking changes in model syntax; use v2 only |
| supabase-py community fork | supabase 2.x official | 2024 | Official Python client, sync + async support |

**Deprecated/outdated:**
- `garminconnect < 0.2.0`: Used custom auth, no garth dependency. Do not use.
- `supabase-py` (old package name): Renamed to `supabase`. Install `supabase`, not `supabase-py`.
- Garmin Connect "classic" dashboard endpoints: Some have been migrated to "modern" dashboard. The library handles this but pin versions.

## Open Questions

1. **Exact Garmin API response JSON shapes for each endpoint**
   - What we know: Method signatures and URL patterns are documented in garminconnect source. Response fields are partially documented.
   - What's unclear: Exact JSON key names for each response vary by firmware/device. Fenix 7 may return additional fields not in the generic documentation.
   - Recommendation: Run the extraction once interactively and log the raw JSON responses. Build Pydantic models from actual observed data, not assumed schemas. This is a Wave 0 / first-task activity.

2. **garminconnect rate limit behavior with 11+ sequential calls**
   - What we know: ~1 request per 5 minutes is documented for "some endpoints." Batch daily pulls are recommended.
   - What's unclear: Whether all 11 metric endpoints trigger the same rate limit, or only certain ones. The library source doesn't differentiate.
   - Recommendation: Start with no inter-call delay. If 429 errors occur, add 1-2 second delays between calls. The tenacity retry decorator handles transient 429s.

3. **Supabase activities table idempotency approach**
   - What we know: daily_metrics uses upsert on date. Activities are 1:many (multiple per date).
   - What's unclear: Whether delete-then-insert or a composite unique constraint (date + activity_type + start_time) is cleaner.
   - Recommendation: Use delete-then-insert for simplicity. Activities are re-fetched in full each run; deleting existing and re-inserting is cleanly idempotent and avoids complex composite constraints.

4. **Token persistence path for future CI/CD deployment**
   - What we know: garth saves tokens to `~/.garminconnect`. GitHub Actions runners are ephemeral.
   - What's unclear: Best approach for Phase 5 (pipeline automation). Options: store tokens in Supabase, store as encrypted GitHub Secret, or use a persistent runner.
   - Recommendation: For Phase 1, use local filesystem (`~/.garminconnect`). Defer the CI/CD token persistence decision to Phase 5 planning.

## Sources

### Primary (HIGH confidence)
- [python-garminconnect GitHub](https://github.com/cyberjunky/python-garminconnect) -- API methods, auth flow, exception classes, v0.2.38 source code
- [garminconnect __init__.py source](https://github.com/cyberjunky/python-garminconnect/blob/master/garminconnect/__init__.py) -- Method signatures, URL patterns, date validation
- [garth GitHub](https://github.com/matin/garth) -- OAuth token persistence, auto-refresh, GARTH_HOME env var
- [Supabase Python upsert docs](https://supabase.com/docs/reference/python/upsert) -- Upsert syntax, on_conflict parameter, ignore_duplicates
- [Supabase Python client docs](https://supabase.com/docs/reference/python/start) -- Client initialization, table operations
- [structlog docs](https://www.structlog.org/en/stable/logging-best-practices.html) -- Configuration patterns, JSON vs console renderers
- [tenacity docs](https://tenacity.readthedocs.io/) -- Retry decorators, exponential backoff, exception filtering
- [garminconnect MFA Issue #312](https://github.com/cyberjunky/python-garminconnect/issues/312) -- MFA token refresh failure documented Dec 2025

### Secondary (MEDIUM confidence)
- [garminconnect rate limit Issue #213](https://github.com/cyberjunky/python-garminconnect/issues/213) -- Rate limit behavior and workarounds
- [Home Assistant Garmin integration](https://github.com/cyberjunky/home-assistant-garmin_connect) -- Validates which sensors/metrics are reliably available
- [Garmin Health API official docs](https://developer.garmin.com/gc-developer-program/health-api/) -- Field names and data structures (used as reference for unofficial API field naming)
- [supabase on PyPI](https://pypi.org/project/supabase/) -- Version 2.28.0, Feb 2026 release

### Tertiary (LOW confidence)
- Exact Garmin API response JSON shapes for Fenix 7 -- need empirical validation by running extraction

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries are well-documented, actively maintained, and have been used in this exact combination by the Home Assistant community
- Architecture: HIGH -- sequential pipeline, wide denormalized table, upsert by date are all established patterns from project research
- Pitfalls: HIGH -- all pitfalls sourced from documented GitHub issues, Garmin forum posts, and project research documents
- Garmin API response shapes: MEDIUM -- method signatures verified from source, but exact field names need empirical validation with target Fenix 7 device

**Research date:** 2026-03-03
**Valid until:** 2026-04-03 (30 days -- stable libraries, pinned versions)
