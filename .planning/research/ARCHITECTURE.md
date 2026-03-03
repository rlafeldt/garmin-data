# Architecture Patterns

**Domain:** Personal health AI agent -- biometric data pipeline with LLM analysis
**Researched:** 2026-03-03

## Recommended Architecture

```
                           SCHEDULING LAYER
                     (cron / GitHub Actions / APScheduler)
                                  |
                                  v
  +----------------------------------------------------------------+
  |                     PIPELINE ORCHESTRATOR                       |
  |                  (main.py -- sequential steps)                  |
  +----------------------------------------------------------------+
       |              |                |               |
       v              v                v               v
  +---------+   +-----------+   +------------+   +-----------+
  | EXTRACT |   | TRANSFORM |   |  ANALYZE   |   |  DELIVER  |
  | Garmin  |   | Normalize |   | Claude API |   |  Email    |
  | Connect |   | + Store   |   | Structured |   |  (Resend) |
  | (garth) |   | (Supabase)|   |  Output    |   |           |
  +---------+   +-----------+   +------------+   +-----------+
       |              |                |               |
       v              v                v               v
  ~/.garminconnect  Supabase        Supabase         User's
  token store       PostgreSQL      (read history)   inbox
                    (write daily)   + config file
```

This is a classic **ETL+A (Extract, Transform, Load, Act)** pipeline with four sequential stages. The simplicity is deliberate -- a single-user personal tool does not need message queues, worker pools, or microservices. A single Python script running sequentially handles the entire daily flow.

### Why Sequential, Not Event-Driven

The pipeline runs once daily with a deterministic input (yesterday's Garmin data). There is no real-time streaming, no concurrent users, no fan-out. A sequential pipeline is easier to debug, easier to retry on failure, and has fewer failure modes. If the Garmin extract fails, the pipeline stops -- there is nothing downstream to process. This matches the problem perfectly.

---

## Component Boundaries

| Component | Responsibility | Inputs | Outputs | Communicates With |
|-----------|---------------|--------|---------|-------------------|
| **Scheduler** | Triggers daily pipeline at configured time | Clock / cron expression | Pipeline invocation | Pipeline Orchestrator |
| **Pipeline Orchestrator** | Coordinates stages, handles top-level errors, logging | Trigger signal | Completion status, error reports | All stages sequentially |
| **Garmin Extractor** | Authenticates with Garmin Connect, pulls all daily metrics | Date, stored auth tokens | Raw Garmin API responses (dicts) | garminconnect/garth library |
| **Data Normalizer** | Validates, normalizes, and stores daily metrics | Raw Garmin dicts | Validated Pydantic models | Supabase client |
| **Supabase Storage** | Persists daily snapshots and historical data | Validated models | Stored rows, historical query results | PostgreSQL via supabase-py |
| **Health Profile** | Provides static user context (goals, labs, medical) | Config file (YAML/TOML) | Profile dict for prompt assembly | Loaded at pipeline start |
| **Prompt Assembler** | Builds the Claude API prompt from data + profile + history | Today's data, rolling history, health profile | Complete prompt string | Claude API |
| **Analysis Engine** | Calls Claude API, validates structured response | Assembled prompt, JSON schema | Daily Protocol (structured) | Anthropic Python SDK |
| **Email Renderer** | Converts structured protocol to HTML email | Daily Protocol JSON | HTML email body | Resend API |
| **Delivery** | Sends the email | HTML body, recipient | Delivery confirmation | Resend Python SDK |

### Component Isolation Principle

Each component should be a standalone Python module that can be tested independently. The pipeline orchestrator calls them in sequence but each module knows nothing about the others. This enables:

- Testing the Garmin extractor with mock API responses
- Testing normalization with fixture data
- Testing prompt assembly without calling Claude
- Testing email rendering without sending

---

## Data Flow

### Stage 1: Extract (Garmin Connect)

```
garminconnect library (via garth auth)
  |
  |-- get_stats(date)              -> daily summary (steps, calories, etc.)
  |-- get_heart_rates(date)        -> HR data incl. resting HR
  |-- get_sleep_data(date)         -> sleep stages, duration, score
  |-- get_hrv_data(date)           -> HRV overnight readings
  |-- get_body_battery(date)       -> body battery charge/drain
  |-- get_stress_data(date)        -> stress score breakdown
  |-- get_spo2_data(date)          -> blood oxygen
  |-- get_respiration_data(date)   -> respiration rate
  |-- get_training_status(date)    -> training load, VO2 max, readiness
  |-- get_activities_fordate(date) -> activities list with details
  |
  v
  Raw dict per metric category (11+ API calls)
```

**Authentication flow:**
1. On first run: interactive login with email/password (+ MFA if enabled)
2. Tokens saved to `~/.garminconnect` (OAuth1 token valid ~1 year via garth)
3. Subsequent runs: load saved tokens, garth auto-refreshes OAuth2 token
4. On token expiry (~1 year): re-authenticate interactively once

**CRITICAL:** Disable MFA on the Garmin account used for automation OR authenticate once with MFA and save tokens. There is a known issue (GitHub issue #312) where MFA accounts fail on token refresh with "OAuth1 token is required for OAuth2 refresh." The safest path for automated daily runs is a non-MFA account with saved tokens.

**Error handling for extract:**
- Rate limiting (429): Retry with exponential backoff via tenacity
- Auth failure (401/403): Log error, alert user, skip pipeline run
- Connection error: Retry up to 3 times, then fail gracefully
- Partial data: Proceed with available data, flag missing metrics

### Stage 2: Transform + Store (Normalize and Persist)

```
Raw Garmin dicts
  |
  v
Pydantic validation models
  |-- DailySummary(date, steps, calories, floors, distance, ...)
  |-- SleepData(date, total_sleep_seconds, deep_seconds, light_seconds,
  |             rem_seconds, awake_seconds, sleep_score, spo2_avg, resp_rate)
  |-- HRVData(date, overnight_avg, overnight_max, seven_day_avg, status)
  |-- BodyBattery(date, morning_charge, max_charge, min_charge, drain_rate)
  |-- HeartRate(date, resting_hr, max_hr, min_hr, avg_hr)
  |-- StressData(date, avg_stress, high_stress_minutes, rest_stress_minutes, ...)
  |-- TrainingLoad(date, seven_day_load, training_status, vo2_max, ...)
  |-- Activities(date, list[Activity])
  |
  v
Supabase PostgreSQL (upsert by date)
  |-- daily_metrics table (denormalized daily snapshot)
  |-- activities table (one row per activity)
```

**Why Pydantic for normalization:**
- Type coercion: Garmin API returns mixed types (strings, ints, nulls unpredictably)
- Validation: Catches missing or nonsensical values before storage
- Documentation: Models serve as living documentation of the data schema
- Serialization: Easy conversion to dicts for Supabase insertion and prompt building

**Schema design for Supabase:**

Use a **wide denormalized table** for daily metrics rather than normalized EAV (entity-attribute-value). Rationale: single-user system with ~365 rows/year. Query patterns are always "get last N days of everything." A wide table with one row per date is simplest to query, simplest to feed into prompts, and will never hit scale concerns (decades of data = ~15K rows).

```sql
-- Core daily metrics table
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
    spo2_avg FLOAT,
    respiration_rate_avg FLOAT,

    -- Metadata
    raw_data JSONB,  -- full Garmin response for debugging
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
```

**Why store raw_data as JSONB:** Garmin's API evolves. New fields appear, field names change. Storing the raw response means you never lose data and can reprocess historical entries if the schema changes.

**Upsert pattern:** Use `ON CONFLICT (date) DO UPDATE` for daily_metrics. The pipeline may run multiple times per day (retries, manual runs). Upsert ensures idempotent writes.

### Stage 3: Analyze (Claude API)

```
Prompt Assembly:
  |
  |-- SYSTEM PROMPT (static)
  |   |-- Role definition (sports science + health expert panel)
  |   |-- Safety boundaries (never diagnose, flag for professional review)
  |   |-- Output schema definition (5 domains + summary + alerts)
  |   |-- Reasoning instructions (explain the "why" behind each recommendation)
  |
  |-- USER MESSAGE (dynamic, assembled per run)
  |   |-- <health_profile> ... </health_profile>    (from config file)
  |   |-- <todays_data> ... </todays_data>           (today's metrics)
  |   |-- <recent_history> ... </recent_history>     (rolling 14-day window)
  |   |-- <trends> ... </trends>                     (computed deltas/averages)
  |   |-- <request>Produce today's Daily Protocol</request>
  |
  v
Claude API call (anthropic Python SDK)
  |-- model: claude-sonnet-4-5 (cost-effective for daily use)
  |-- max_tokens: 4096
  |-- output_config.format: json_schema (structured output)
  |
  v
Validated JSON response matching DailyProtocol schema
```

**Prompt architecture pattern: Context Window as Database**

The key insight is that the LLM prompt IS the analysis engine. There is no separate analytics layer. The prompt assembler's job is to pack the context window with the right data in the right format so Claude can reason over it.

**Structured output schema for the Daily Protocol:**

```json
{
  "type": "object",
  "properties": {
    "date": { "type": "string" },
    "executive_summary": { "type": "string" },
    "overall_status": {
      "type": "string",
      "enum": ["optimal", "good", "caution", "recovery_needed", "alert"]
    },
    "training": {
      "type": "object",
      "properties": {
        "recommendation": { "type": "string" },
        "intensity": { "type": "string" },
        "rationale": { "type": "string" },
        "suggested_activities": {
          "type": "array",
          "items": { "type": "string" }
        }
      },
      "required": ["recommendation", "intensity", "rationale"]
    },
    "recovery": {
      "type": "object",
      "properties": {
        "status": { "type": "string" },
        "hrv_assessment": { "type": "string" },
        "body_battery_assessment": { "type": "string" },
        "recommendations": {
          "type": "array",
          "items": { "type": "string" }
        }
      },
      "required": ["status", "recommendations"]
    },
    "sleep": {
      "type": "object",
      "properties": {
        "assessment": { "type": "string" },
        "debt_status": { "type": "string" },
        "recommendations": {
          "type": "array",
          "items": { "type": "string" }
        }
      },
      "required": ["assessment", "recommendations"]
    },
    "nutrition": {
      "type": "object",
      "properties": {
        "caloric_target": { "type": "string" },
        "macro_guidance": { "type": "string" },
        "hydration_target": { "type": "string" },
        "specific_recommendations": {
          "type": "array",
          "items": { "type": "string" }
        }
      },
      "required": ["specific_recommendations"]
    },
    "supplementation": {
      "type": "object",
      "properties": {
        "recommendations": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "supplement": { "type": "string" },
              "dose": { "type": "string" },
              "timing": { "type": "string" },
              "rationale": { "type": "string" }
            },
            "required": ["supplement", "dose", "timing", "rationale"]
          }
        }
      },
      "required": ["recommendations"]
    },
    "alerts": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "severity": {
            "type": "string",
            "enum": ["info", "warning", "critical"]
          },
          "message": { "type": "string" },
          "action": { "type": "string" }
        },
        "required": ["severity", "message", "action"]
      }
    }
  },
  "required": [
    "date", "executive_summary", "overall_status",
    "training", "recovery", "sleep", "nutrition",
    "supplementation", "alerts"
  ]
}
```

**Why Claude structured outputs instead of free-text parsing:**
- Guaranteed valid JSON -- no parsing failures
- Schema enforcement -- every required field present
- Type safety -- enums constrain values to expected set
- Downstream reliability -- email renderer always gets predictable input

**Why claude-sonnet-4-5 for daily runs:**
- Cost: ~$3/1M input tokens vs ~$15/1M for Opus. At ~3K tokens/prompt + ~2K output daily, yearly cost is under $2 with Sonnet vs ~$10 with Opus
- Quality: Sonnet is more than sufficient for structured health data interpretation. The reasoning is pattern-matching over known sports science, not novel discovery
- Speed: Faster response time means the morning pipeline completes quicker

**Prompt engineering patterns for this domain:**

1. **Role anchoring:** "You are a panel of experts: a sports scientist, a sleep researcher, a registered dietitian, and an endocrinologist. Synthesize your perspectives into a single coherent protocol."

2. **Data-first prompting:** Place all biometric data ABOVE the instructions. Claude processes long-context inputs better when data precedes the query (documented in Anthropic's best practices).

3. **XML-tagged sections:** Use `<health_profile>`, `<todays_data>`, `<recent_history>`, `<trends>` tags to unambiguously separate data categories. Claude handles XML tags natively for parsing structured input.

4. **Trend computation before prompting:** Compute rolling averages, deltas, and trend directions in Python before including in the prompt. Do not ask the LLM to do arithmetic -- it is unreliable at math. Present pre-computed trends like "HRV 7-day average: 52ms, today: 44ms, delta: -15.4%".

5. **Safety guardrails in system prompt:** Explicit instructions to never diagnose, to flag concerning patterns for professional review, and to state uncertainty when data is ambiguous.

### Stage 4: Deliver (Email via Resend)

```
DailyProtocol JSON
  |
  v
HTML Template Engine (Jinja2)
  |-- Base template with responsive email CSS
  |-- Section templates for each domain
  |-- Alert banner template (for critical alerts)
  |-- Color-coded status indicators
  |
  v
Rendered HTML email
  |
  v
Resend API (resend Python SDK)
  |-- from: "BioIntelligence <daily@yourdomain.com>"
  |-- to: configured recipient
  |-- subject: "Daily Protocol -- March 3, 2026 [STATUS]"
  |
  v
Delivery confirmation or error
```

**Why Resend over SMTP:**
- No SMTP server to manage or monitor
- Better deliverability (SPF/DKIM/DMARC handled by Resend)
- Simple Python SDK (`resend.Emails.send(params)`)
- Free tier: 3,000 emails/month (daily use = 30-31/month, well within limits)
- Error responses with clear status codes for retry logic

**Why Jinja2 for email templates:**
- Python standard for templating
- Conditional rendering (show alert banner only when alerts exist)
- Loop over supplement recommendations, activity suggestions
- Separation of data (JSON) from presentation (HTML)

---

## Patterns to Follow

### Pattern 1: Pipeline as a Sequence of Pure-ish Functions

**What:** Each pipeline stage is a function that takes explicit inputs and returns explicit outputs. No global state, no side effects beyond database writes and API calls.

**When:** Always. This is the core architectural pattern.

**Example:**

```python
# pipeline.py -- orchestrator

def run_daily_pipeline(date: datetime.date) -> PipelineResult:
    """Run the complete daily pipeline for a given date."""

    # Stage 1: Extract
    raw_data = extract_garmin_data(date)

    # Stage 2: Transform + Store
    daily_metrics = normalize_and_store(raw_data, date)

    # Stage 3: Analyze
    history = fetch_rolling_history(date, window_days=14)
    profile = load_health_profile()
    protocol = analyze_with_claude(daily_metrics, history, profile, date)

    # Stage 4: Deliver
    delivery_result = send_daily_email(protocol, date)

    return PipelineResult(
        date=date,
        metrics_stored=True,
        protocol=protocol,
        email_sent=delivery_result.success,
    )
```

### Pattern 2: Retry with Tenacity on External Calls

**What:** Wrap all external API calls (Garmin, Claude, Resend, Supabase) with retry decorators using exponential backoff.

**When:** Every external call. These are the failure points.

**Example:**

```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type((ConnectionError, TimeoutError)),
)
def extract_garmin_data(date: datetime.date) -> dict:
    """Pull all metrics from Garmin Connect for a given date."""
    api = get_garmin_client()
    return {
        "stats": api.get_stats(date.isoformat()),
        "sleep": api.get_sleep_data(date.isoformat()),
        "hrv": api.get_hrv_data(date.isoformat()),
        # ... etc
    }
```

### Pattern 3: Idempotent Writes

**What:** Every database write uses upsert. Running the pipeline twice for the same date produces the same result.

**When:** All Supabase writes.

**Why:** The pipeline will be retried on failure. Manual re-runs should be safe. Idempotency eliminates "did this already run?" complexity.

### Pattern 4: Config File for Health Profile

**What:** Store the health profile as a YAML or TOML file in the repository (or alongside it), not in the database.

**When:** v1 (single user).

**Why:** Easier to edit than a database row. Version-controlled changes. No UI needed. The profile changes rarely (lab results every few months, goals every few weeks).

**Example structure:**

```yaml
# health_profile.yaml
personal:
  age: 35
  sex: male
  weight_kg: 82
  height_cm: 180

goals:
  primary: endurance_performance
  secondary: body_composition
  target_events:
    - name: "Half marathon"
      date: "2026-06-15"

medical:
  conditions: []
  medications: []
  injuries:
    - area: "left knee"
      status: "recovered, monitor under load"

labs:
  date: "2026-01-15"
  vitamin_d: 31  # ng/mL
  ferritin: 85   # ng/mL
  b12: 450       # pg/mL
  hba1c: 5.2     # %
  testosterone: 620  # ng/dL
  tsh: 2.1       # mIU/L
  crp: 0.4       # mg/L

diet:
  framework: omnivore
  restrictions: []
  meal_timing: "16:8 intermittent fasting"

supplements:
  current:
    - name: "Vitamin D3"
      dose: "4000 IU"
      timing: "morning with fat"
    - name: "Magnesium Glycinate"
      dose: "400mg"
      timing: "before bed"
    - name: "Creatine Monohydrate"
      dose: "5g"
      timing: "post-workout"

sleep:
  target_hours: 7.5
  typical_bedtime: "22:30"
  typical_wake: "06:00"
  environment: "dark, cool, quiet"
  disruptions: []
```

### Pattern 5: Computed Trends Before LLM

**What:** Calculate rolling averages, deltas, and trend directions in Python and include the computed values in the prompt.

**When:** Always, for any numerical comparison or trend.

**Why:** LLMs are unreliable at arithmetic. A 7-day rolling average computed in Python is exact. Asking Claude to "calculate the 7-day average" from raw data will sometimes produce wrong numbers.

**Example:**

```python
def compute_trends(history: list[DailyMetrics]) -> dict:
    """Compute trends from rolling history for prompt inclusion."""
    if len(history) < 2:
        return {"insufficient_data": True}

    hrv_values = [d.hrv_overnight_avg for d in history if d.hrv_overnight_avg]
    sleep_values = [d.total_sleep_seconds for d in history if d.total_sleep_seconds]

    return {
        "hrv_7d_avg": mean(hrv_values[-7:]),
        "hrv_14d_avg": mean(hrv_values),
        "hrv_trend": "declining" if hrv_values[-1] < hrv_values[-7] else "stable_or_rising",
        "hrv_today_vs_7d_pct": ((hrv_values[-1] - mean(hrv_values[-7:])) / mean(hrv_values[-7:])) * 100,
        "sleep_7d_avg_hours": mean(sleep_values[-7:]) / 3600,
        "sleep_debt_hours": max(0, 7.5 * 7 - sum(sleep_values[-7:]) / 3600),
        # ... more computed trends
    }
```

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Microservices for a Single-User Pipeline

**What:** Splitting the pipeline into separate deployed services (ingestion service, analysis service, delivery service) communicating over HTTP or queues.

**Why bad:** Massive operational overhead for zero benefit. Single user, single daily run, ~30 seconds total execution. Microservices add deployment complexity, network failure modes, monitoring burden, and debugging difficulty.

**Instead:** One Python package, one entry point, sequential execution. If it needs to scale to multi-user later, extract services then.

### Anti-Pattern 2: Real-Time Streaming Architecture

**What:** Setting up Kafka, Redis Streams, or similar for "real-time" Garmin data processing.

**Why bad:** Garmin data is inherently batch -- it syncs once after the device uploads (usually overnight). There is no real-time stream to process. A daily batch job matches the data availability pattern.

**Instead:** Simple daily cron trigger. If sub-daily updates are desired later, increase cron frequency to every 6 hours.

### Anti-Pattern 3: Asking the LLM to Do Math

**What:** Including raw data arrays in the prompt and asking Claude to "calculate the 7-day rolling average" or "determine the percentage change."

**Why bad:** LLMs make arithmetic errors. The error rate increases with larger number sets. You will get plausible-sounding but numerically wrong trend assessments.

**Instead:** Compute all statistics, averages, deltas, and trend directions in Python. Present pre-computed summaries to the LLM for interpretation only.

### Anti-Pattern 4: Storing Config in the Database

**What:** Putting the health profile in Supabase and building CRUD operations around it for v1.

**Why bad:** Over-engineering for a single user. You need to build insert/update logic, possibly a UI, handle schema migrations for profile changes. A YAML file achieves the same thing with a text editor.

**Instead:** YAML/TOML config file. Migrate to database storage when/if multi-user support is added.

### Anti-Pattern 5: Overly Granular Database Schema

**What:** Normalized schema with separate tables per metric type (sleep_metrics, hrv_metrics, stress_metrics, etc.) joined by date.

**Why bad:** Every query requires multiple JOINs. Prompt assembly becomes complex. For ~365 rows/year with ~30 columns, a wide table is simpler and faster.

**Instead:** Single `daily_metrics` table with one row per date. Store raw JSONB alongside structured columns for future flexibility.

---

## Deployment Architecture

### Recommended: GitHub Actions Scheduled Workflow

For a single-user personal tool, GitHub Actions provides free, reliable cron scheduling without managing infrastructure.

```yaml
# .github/workflows/daily-pipeline.yml
name: Daily BioIntelligence Pipeline
on:
  schedule:
    - cron: '30 5 * * *'  # 5:30 AM UTC daily (adjust for timezone)
  workflow_dispatch: {}     # manual trigger for testing

jobs:
  run-pipeline:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: python -m biointelligence.pipeline
        env:
          GARMIN_EMAIL: ${{ secrets.GARMIN_EMAIL }}
          GARMIN_PASSWORD: ${{ secrets.GARMIN_PASSWORD }}
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          RESEND_API_KEY: ${{ secrets.RESEND_API_KEY }}
```

**Garmin token persistence in CI:** GitHub Actions runners are ephemeral. The Garmin OAuth tokens stored at `~/.garminconnect` will not persist between runs. Solutions:
1. **Store tokens as a GitHub secret** (base64-encoded) and restore them at runtime
2. **Store tokens in Supabase** (encrypted) and fetch them at pipeline start
3. **Re-authenticate each run** (only works without MFA, and risks rate limiting)

Recommended: Option 2 (store in Supabase). The tokens are small (~1KB), update rarely (~yearly), and Supabase is already in the stack.

### Alternative: Local Cron or VPS

If GitHub Actions token handling proves difficult, a lightweight VPS (DigitalOcean $4/mo) or a Raspberry Pi running a system cron job is the simplest deployment model. Tokens persist naturally on the filesystem.

---

## Scalability Considerations

| Concern | At 1 user (v1) | At 10 users (future) | At 1K users (distant future) |
|---------|----------------|---------------------|------------------------------|
| **Data volume** | 365 rows/year, trivial | 3,650 rows/year, still trivial | 365K rows/year, need partitioning |
| **API costs** | ~$2/year Claude, free tier Resend | ~$20/year, still free Resend | ~$2K/year, paid Resend plan |
| **Garmin auth** | 1 token, simple | 10 tokens, need per-user management | 1K tokens, official Garmin API needed |
| **Pipeline execution** | 30s sequential, fine | 5min sequential, fine | Need parallel execution, task queue |
| **Database** | Supabase free tier | Supabase free tier | Supabase paid tier |

At single-user scale, every concern is trivial. The architecture should not pre-optimize for scale that may never arrive.

---

## Suggested Build Order

The pipeline has clear dependencies that dictate the build sequence:

```
Phase 1: Garmin Extract + Normalize
  (you need data before you can do anything else)
    |
    v
Phase 2: Supabase Storage + Historical Query
  (you need stored history before trend analysis)
    |
    v
Phase 3: Health Profile Config + Prompt Assembly
  (you need all inputs before calling Claude)
    |
    v
Phase 4: Claude Analysis Engine + Structured Output
  (you need the protocol before you can deliver it)
    |
    v
Phase 5: Email Rendering + Delivery
  (you need rendered output before sending)
    |
    v
Phase 6: Scheduling + Error Handling + Monitoring
  (automation layer wraps the working pipeline)
```

**Rationale for this order:**

1. **Data first:** Without Garmin data flowing, nothing else can be tested with real inputs. Start here to validate the garminconnect library works with the target account and all needed metrics are accessible.

2. **Storage second:** Once data flows, persist it immediately. This unlocks historical queries and trend computation. Testing the pipeline manually before adding scheduling is crucial.

3. **Profile + Prompt third:** The prompt assembler depends on both stored history and the health profile. Building these together lets you iterate on prompt quality with real data.

4. **Analysis fourth:** With prompt assembly working, the Claude API integration is a focused task: call the API, validate the structured response, handle errors.

5. **Delivery fifth:** Once you have a validated protocol JSON, rendering it to HTML and sending via Resend is straightforward.

6. **Scheduling last:** Automation wraps a working pipeline. Adding cron/scheduling to a broken pipeline just automates failures. Get the pipeline working end-to-end manually first, then automate.

---

## Sources

- [python-garminconnect GitHub](https://github.com/cyberjunky/python-garminconnect) -- API methods, auth flow, token management
- [garth (Garmin SSO auth)](https://github.com/matin/garth) -- OAuth1/OAuth2 token lifecycle
- [garminconnect MFA issue #312](https://github.com/cyberjunky/python-garminconnect/issues/312) -- Known MFA token refresh failure
- [Supabase Python client docs](https://supabase.com/docs/reference/python/introduction) -- Database client patterns
- [supabase-py GitHub](https://github.com/supabase/supabase-py) -- Sync/async client architecture
- [Claude API structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) -- JSON schema enforcement
- [Claude prompting best practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices) -- Data-first prompting, XML tags
- [Resend Python SDK](https://resend.com/docs/send-with-python) -- Email delivery integration
- [Tenacity retry library](https://github.com/jd/tenacity) -- Retry decorators with backoff
- [APScheduler docs](https://apscheduler.readthedocs.io/en/3.x/userguide.html) -- Python job scheduling
- [PostgreSQL time-series best practices (Alibaba Cloud)](https://www.alibabacloud.com/blog/best-practices-for-postgresql-time-series-database-design_599374) -- Schema design
- [GitHub Actions scheduled workflows](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#schedule) -- Cron-based CI/CD
