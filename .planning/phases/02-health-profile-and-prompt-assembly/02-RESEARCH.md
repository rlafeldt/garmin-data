# Phase 2: Health Profile and Prompt Assembly - Research

**Researched:** 2026-03-03
**Domain:** YAML configuration loading, Supabase time-series queries, Claude prompt engineering
**Confidence:** HIGH

## Summary

Phase 2 adds three distinct capabilities to the existing BioIntelligence pipeline: (1) loading a personal health profile from a YAML config file via Pydantic validation, (2) computing 7-day rolling trend statistics from the Supabase `daily_metrics` table, and (3) assembling a structured Claude prompt with XML-tagged sections that stays within a ~4K-6K token budget. All three are well-understood domains with mature tooling already available in the project.

The existing codebase provides strong foundations: Pydantic v2 (2.12.5) for model validation, supabase-py (2.28.0) for database queries with filter chaining, structlog for logging, and PyYAML (6.0.3, available as transitive dependency). No new major dependencies are required. The pattern of `yaml.safe_load()` + `BaseModel.model_validate()` is the standard Pydantic v2 approach for YAML loading. Supabase's `.select().gte().lte().eq().order()` chain handles the 7-day trend query directly. Token estimation uses a ~4 characters/token heuristic per the user's decision, avoiding external tokenizer dependencies.

**Primary recommendation:** Keep the YAML-to-Pydantic pattern simple (PyYAML + `model_validate`), use a single Supabase query for the 7-day window with Python-side aggregation, and structure the prompt as a multi-section XML document with clear tag boundaries. No new dependencies needed beyond PyYAML as an explicit dependency.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions

**Health profile content:**
- Comprehensive reference profile with all PROF-01 sections filled in detail: biometrics (age, sex, weight, height, body fat %), training goals, medical history, metabolic profile, diet preferences, current supplements, sleep context, and lab values
- Lab values typed with dates and reference ranges -- each entry includes value, unit, test date, and reference range (e.g., `vitamin_d: {value: 42, unit: ng/mL, date: 2025-11, range: '30-100'}`). Claude can flag stale values and calibrate supplement doses.
- Structured training context included: current training phase (base/build/peak/recovery), weekly volume targets, race goals with dates, injury history, preferred training types (cycling and strength from Phase 1 context)
- Full supplement stack with timing, form, and conditional dosing rules (e.g., `magnesium_glycinate: {dose: 400mg, form: glycinate, timing: evening, condition: 'increase to 600mg on high-stress days'}`)

**Trend computation:**
- Core readiness metrics only get 7-day rolling trends: HRV overnight avg, resting HR, sleep score, total sleep duration, body battery morning, avg stress level, training load 7d
- Statistics per trended metric: 7-day average, trend direction (improving/declining/stable), min, max
- Trend direction via split-half comparison: average of first half vs second half of window, >5% change = improving/declining, otherwise stable
- Minimum 4 of 7 days of data required for trend computation; below that, trend marked as "insufficient data"
- No-wear days (from Phase 1 `is_no_wear` flag) excluded from trend windows
- All other DailyMetrics fields passed as today-only values without trend context

**Prompt architecture:**
- Structured directive style: each analysis domain (training, recovery, sleep, nutrition, supplementation) gets specific instructions telling Claude exactly what to analyze and what to recommend
- Sports science grounding via 3-5 core framework reference blocks embedded in the prompt: HRV interpretation model, sleep architecture guidelines, acute-to-chronic load ratio thresholds, periodization principles. Short anchors, not exhaustive references.
- Yesterday's activities included as a dedicated prompt section (type, duration, intensity, training effect) -- connects today's readiness to prior training. Uses existing Phase 1 Activity model data.
- Output format specified as JSON schema with examples -- defines the DailyProtocol structure that Phase 3 will validate against. Guarantees parseable, structured output.

**Token budget:**
- Target prompt size: ~4K-6K tokens
- Token counting via word-based heuristic (~1 token per 4 characters). No external tokenizer dependency. Calibrate with actual Claude API token usage in Phase 3.
- Trimming priority when over budget: 1) Today's metrics (never cut) 2) Health profile (never cut) 3) Activities 4) 7-day trends 5) Sports science grounding. Grounding is most compressible.
- Only pre-computed normalized values in the prompt -- raw Garmin JSON stays in Supabase for debugging, never enters the prompt

### Claude's Discretion

- Exact YAML schema structure for the health profile (section names, nesting)
- XML tag naming conventions for prompt sections
- Specific sports science framework content and phrasing
- Exact DailyProtocol JSON schema field names and nesting
- SQL query design for fetching trend data from Supabase
- Pydantic model design for health profile and prompt assembly
- Error handling and logging patterns (follow Phase 1 structlog conventions)

### Deferred Ideas (OUT OF SCOPE)

None -- discussion stayed within phase scope

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PROF-01 | User defines personal health profile in a static YAML config file including age, sex, weight, height, body composition, training goals, medical history, metabolic profile, diet preferences, current supplements with dosages, sleep context, and relevant lab values | YAML loading pattern (PyYAML + Pydantic model_validate), nested Pydantic models for each profile section, field validators for lab value types |
| PROF-02 | Health profile is injected into every Claude API analysis call as structured context | Prompt assembly architecture with XML-tagged `<health_profile>` section, profile serialization to prompt-friendly format |
| TRND-01 | System feeds 7-day rolling trend context into the analysis prompt for longitudinal awareness | Supabase date-range query pattern (.gte/.lte/.eq filters), Python-side aggregation for split-half trend direction, trend model with avg/min/max/direction fields |
| TRND-04 | System prompt encodes sports science frameworks (periodization models, HRV interpretation, sleep architecture research) for grounded recommendations | XML-tagged `<sports_science>` section with 3-5 framework blocks, token-budget-aware trimming (lowest priority), static string templates |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PyYAML | 6.0.3 | YAML file parsing | Already available as transitive dep; standard Python YAML library |
| pydantic | 2.12.5 | Health profile model validation | Already used project-wide for DailyMetrics, Activity, Settings |
| supabase-py | 2.28.0 | Trend data queries from daily_metrics table | Already used for storage in Phase 1 |
| structlog | 25.5.0 | Structured logging throughout | Already established as project logging standard |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pydantic-settings | 2.13.1 | Settings class with .env loading | Already used; extend for YAML profile path config |
| tenacity | 9.1.4 | Retry logic on Supabase queries | Already used in Phase 1 storage layer; reuse for trend queries |
| pathlib (stdlib) | n/a | YAML file path resolution | Health profile file path handling |
| datetime (stdlib) | n/a | Date arithmetic for 7-day window | Trend window calculation |
| statistics (stdlib) | n/a | Mean calculation for trends | Avoid hand-rolling average computation |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| PyYAML + model_validate | pydantic-yaml library | Extra dependency for minimal benefit; standard pattern is simpler |
| PyYAML + model_validate | strictyaml (already installed) | Stricter typing but incompatible with Pydantic model_validate flow; PyYAML is the standard path |
| Word-based token heuristic | anthropic client.messages.count_tokens() | Requires API call; user explicitly decided on heuristic approach |
| Python-side aggregation | Supabase RPC/SQL functions | Over-engineering for 7 rows; Python aggregation is simpler and testable |

### Dependency Note

PyYAML (6.0.3) is already available as a transitive dependency but should be added as an explicit dependency in `pyproject.toml` since the project directly imports it:

```bash
uv add pyyaml
```

No other new dependencies are required.

## Architecture Patterns

### Recommended Project Structure
```
src/biointelligence/
    config.py               # Existing Settings + new HEALTH_PROFILE_PATH setting
    profile/
        __init__.py
        models.py           # Pydantic models: HealthProfile, Biometrics, LabValue, Supplement, etc.
        loader.py           # load_health_profile(path) -> HealthProfile
    trends/
        __init__.py
        models.py           # TrendResult, MetricTrend, TrendDirection enum
        compute.py          # compute_trends(client, target_date) -> TrendResult
    prompt/
        __init__.py
        models.py           # PromptContext, AssembledPrompt
        assembler.py        # assemble_prompt(metrics, trends, profile, activities) -> AssembledPrompt
        templates.py        # Sports science grounding text blocks, directive templates
        budget.py           # estimate_tokens(text), trim_to_budget(sections, limit)
```

### Pattern 1: YAML Loading with Pydantic Validation

**What:** Load YAML file with `yaml.safe_load()`, validate with `BaseModel.model_validate()`.
**When to use:** Loading the health profile configuration.
**Example:**
```python
# Source: Pydantic v2 official docs + PyYAML standard pattern
from pathlib import Path
import yaml
from pydantic import BaseModel

class LabValue(BaseModel):
    value: float
    unit: str
    date: str
    range: str

class Biometrics(BaseModel):
    age: int
    sex: str
    weight_kg: float
    height_cm: float
    body_fat_pct: float | None = None

class HealthProfile(BaseModel):
    biometrics: Biometrics
    training_goals: TrainingGoals
    medical_history: MedicalHistory
    metabolic_profile: MetabolicProfile
    diet: DietPreferences
    supplements: list[Supplement]
    sleep_context: SleepContext
    lab_values: dict[str, LabValue]

def load_health_profile(path: Path) -> HealthProfile:
    """Load and validate health profile from YAML file."""
    with open(path) as f:
        raw = yaml.safe_load(f)
    return HealthProfile.model_validate(raw)
```

### Pattern 2: Supabase Date-Range Query with No-Wear Exclusion

**What:** Query 7 days of daily_metrics, excluding no-wear days, for trend computation.
**When to use:** Fetching the trend window data.
**Example:**
```python
# Source: Supabase Python docs (using-filters, order)
from datetime import date, timedelta
from supabase import Client

TREND_FIELDS = (
    "date,hrv_overnight_avg,resting_hr,sleep_score,"
    "total_sleep_seconds,body_battery_morning,avg_stress_level,training_load_7d,"
    "is_no_wear"
)

def fetch_trend_window(client: Client, target_date: date, window_days: int = 7) -> list[dict]:
    """Fetch daily metrics for trend computation window."""
    start = target_date - timedelta(days=window_days)
    response = (
        client.table("daily_metrics")
        .select(TREND_FIELDS)
        .gte("date", start.isoformat())
        .lt("date", target_date.isoformat())
        .eq("is_no_wear", False)
        .order("date", desc=False)
        .execute()
    )
    return response.data
```

### Pattern 3: Split-Half Trend Direction

**What:** Compute trend direction by comparing first-half vs second-half averages.
**When to use:** Determining if a metric is improving, declining, or stable.
**Example:**
```python
from enum import Enum
from statistics import mean

class TrendDirection(str, Enum):
    IMPROVING = "improving"
    DECLINING = "declining"
    STABLE = "stable"
    INSUFFICIENT = "insufficient_data"

def compute_direction(
    values: list[float], min_data_points: int = 4, threshold: float = 0.05
) -> TrendDirection:
    """Compute trend direction via split-half comparison."""
    if len(values) < min_data_points:
        return TrendDirection.INSUFFICIENT

    mid = len(values) // 2
    first_half = mean(values[:mid])
    second_half = mean(values[mid:])

    if first_half == 0:
        return TrendDirection.STABLE

    pct_change = (second_half - first_half) / abs(first_half)

    if pct_change > threshold:
        return TrendDirection.IMPROVING
    elif pct_change < -threshold:
        return TrendDirection.DECLINING
    return TrendDirection.STABLE
```

**Note on directionality:** For resting HR and stress level, a *decrease* is actually "improving". The compute function should accept a `lower_is_better` flag to invert the direction for these metrics.

### Pattern 4: XML-Tagged Prompt Assembly

**What:** Build the Claude prompt as concatenated XML-tagged sections.
**When to use:** Assembling the final prompt from all data sources.
**Example:**
```python
# Source: Anthropic Claude prompt engineering best practices
def assemble_prompt(
    today_metrics: DailyMetrics,
    trends: TrendResult,
    profile: HealthProfile,
    activities: list[Activity],
    grounding: str,
    output_schema: str,
) -> str:
    sections = []

    sections.append("<health_profile>\n" + profile.to_prompt_text() + "\n</health_profile>")
    sections.append("<today_metrics>\n" + format_metrics(today_metrics) + "\n</today_metrics>")
    sections.append("<trends_7d>\n" + format_trends(trends) + "\n</trends_7d>")
    sections.append("<yesterday_activities>\n" + format_activities(activities) + "\n</yesterday_activities>")
    sections.append("<sports_science>\n" + grounding + "\n</sports_science>")
    sections.append("<analysis_directives>\n" + DIRECTIVES + "\n</analysis_directives>")
    sections.append("<output_format>\n" + output_schema + "\n</output_format>")

    return "\n\n".join(sections)
```

### Pattern 5: Token Budget Estimation and Trimming

**What:** Estimate token count via character heuristic and trim low-priority sections.
**When to use:** Ensuring the assembled prompt fits within ~4K-6K token target.
**Example:**
```python
def estimate_tokens(text: str) -> int:
    """Estimate token count using ~4 chars/token heuristic."""
    return len(text) // 4

TRIM_PRIORITY = [
    "sports_science",      # Most compressible
    "trends_7d",           # Next to trim
    "yesterday_activities", # Then activities
    # health_profile and today_metrics are NEVER trimmed
]
```

### Anti-Patterns to Avoid
- **Putting raw Garmin JSON in the prompt:** The user explicitly decided only pre-computed normalized values enter the prompt. Raw JSON stays in Supabase.
- **Using Supabase RPC for simple aggregation:** Computing avg/min/max/direction over 7 rows in Python is simpler, more testable, and avoids Supabase function management overhead.
- **Adding an external tokenizer dependency:** The user decided on a character heuristic. Do not add tiktoken, anthropic tokenizer, or similar packages.
- **Making the health profile dynamic/database-stored:** The profile is a static YAML file. Do not over-engineer with a web UI or database storage for v1.
- **Using generic XML tags:** Tag names should be descriptive and match their content domain (e.g., `<health_profile>` not `<context1>`).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| YAML parsing | Custom YAML tokenizer/parser | `yaml.safe_load()` | Edge cases around YAML spec are extensive (anchors, multi-line strings, type coercion) |
| Config validation | Manual type checking on YAML dict | Pydantic `model_validate()` | Automatic type coercion, validation errors, nested model support |
| Mean/statistics | `sum(vals)/len(vals)` | `statistics.mean()` | Handles edge cases, consistent with stdlib |
| Date arithmetic | Manual day counting | `datetime.timedelta(days=7)` | Handles month/year boundaries correctly |
| JSON serialization for prompt | Manual string concatenation of values | Pydantic `model_dump(mode="json")` | Consistent date/enum serialization |

**Key insight:** Phase 2's value is in the *integration* (connecting stored data to a well-structured prompt), not in building novel data processing. Every subcomponent has a standard library or existing project solution.

## Common Pitfalls

### Pitfall 1: YAML Type Coercion Surprises
**What goes wrong:** PyYAML's `safe_load` interprets `yes`/`no`, `on`/`off` as booleans; dates like `2025-11` may become datetime objects; unquoted numbers become ints/floats.
**Why it happens:** YAML 1.1 spec has aggressive type inference.
**How to avoid:** Always quote ambiguous values in the YAML file (dates, ranges like `'30-100'`, values like `'yes'`). Pydantic validation will catch type mismatches, but clearer YAML prevents confusion.
**Warning signs:** Lab value dates parsing as datetime instead of string; ranges parsing as integers.

### Pitfall 2: Trend Computation with All None Values
**What goes wrong:** A metric may be None for all 7 days (e.g., HRV not available on some devices). Computing mean of empty list raises StatisticsError.
**Why it happens:** Not all Garmin devices capture all metrics; partial data is expected.
**How to avoid:** Filter out None values before aggregation. Check `len(valid_values) >= min_data_points` before computing statistics. Return `TrendDirection.INSUFFICIENT` when data is sparse.
**Warning signs:** `StatisticsError: mean requires at least one data point` in logs.

### Pitfall 3: Inverted Trend Direction for "Lower is Better" Metrics
**What goes wrong:** Resting HR dropping from 55 to 50 is *improving*, but naive split-half comparison reports it as "declining" because the value decreased.
**Why it happens:** The default assumption is higher = improving.
**How to avoid:** Define a `lower_is_better` attribute per trended metric. Invert the comparison for resting_hr and avg_stress_level.
**Warning signs:** "Declining resting HR" when the user is actually getting fitter.

### Pitfall 4: Off-by-One in Date Window
**What goes wrong:** Fetching 8 days or 6 days instead of 7 due to inclusive/exclusive date boundaries.
**Why it happens:** Confusion between `.gte()` (inclusive start) and `.lt()` (exclusive end) vs `.lte()` (inclusive end).
**How to avoid:** Use `.gte(start)` and `.lt(target_date)` where `start = target_date - timedelta(days=7)`. This gives exactly the 7 days before target_date, not including target_date itself.
**Warning signs:** Trend window containing today's (incomplete) data, or missing a day.

### Pitfall 5: Token Budget Exceeded Without Warning
**What goes wrong:** The assembled prompt is 8K+ tokens because the health profile is very detailed or many activities occurred yesterday.
**Why it happens:** No budget check before sending to Claude API.
**How to avoid:** Always estimate tokens after assembly. Log a warning when approaching budget. Implement trimming logic that removes low-priority sections (sports science grounding first).
**Warning signs:** Claude API returning truncated responses or exceeding cost expectations.

### Pitfall 6: Supabase Query Returning No Data for Fresh Deployments
**What goes wrong:** On first deployment or when there are fewer than 7 days of data, the trend query returns empty results.
**Why it happens:** System is new, only 1-3 days of ingested data exist.
**How to avoid:** Gracefully handle <4 data points by returning "insufficient data" for all trends. The prompt should still be assembled with today's metrics and the health profile -- just without trend context.
**Warning signs:** Trends section empty in the assembled prompt during the first week of use.

## Code Examples

### Complete Health Profile YAML Schema
```yaml
# health_profile.yaml
biometrics:
  age: 35
  sex: male
  weight_kg: 82.0
  height_cm: 183.0
  body_fat_pct: 15.5

training:
  phase: build          # base / build / peak / recovery
  weekly_volume_hours: 8.0
  preferred_types:
    - cycling
    - strength_training
  race_goals:
    - event: "Gran Fondo"
      date: "2026-06-15"
      priority: A
  injury_history:
    - area: left_knee
      status: resolved
      notes: "IT band, resolved 2025"

medical:
  conditions: []
  medications: []
  allergies: []

metabolic:
  resting_metabolic_rate: 1850
  glucose_response: normal

diet:
  preference: balanced
  restrictions: []
  meal_timing: "3 meals + pre/post workout"

supplements:
  - name: magnesium_glycinate
    dose: "400mg"
    form: glycinate
    timing: evening
    condition: "increase to 600mg on high-stress days"
  - name: vitamin_d3
    dose: "4000IU"
    form: liquid
    timing: morning
    condition: null
  - name: omega_3
    dose: "2g EPA/DHA"
    form: triglyceride
    timing: "with meals"
    condition: null
  - name: creatine
    dose: "5g"
    form: monohydrate
    timing: "post-workout"
    condition: null

sleep_context:
  chronotype: intermediate
  target_bedtime: "22:30"
  target_wake: "06:30"
  environment_notes: "cool room, blackout curtains"

lab_values:
  vitamin_d:
    value: 42
    unit: "ng/mL"
    date: "2025-11"
    range: "30-100"
  ferritin:
    value: 85
    unit: "ng/mL"
    date: "2025-11"
    range: "30-300"
  testosterone_total:
    value: 650
    unit: "ng/dL"
    date: "2025-11"
    range: "300-1000"
  hba1c:
    value: 5.2
    unit: "%"
    date: "2025-11"
    range: "4.0-5.6"
```

### Pydantic Health Profile Models
```python
# Source: Pydantic v2 docs + project conventions
from __future__ import annotations
from pathlib import Path
from pydantic import BaseModel, field_validator
import yaml

class LabValue(BaseModel):
    value: float
    unit: str
    date: str
    range: str

class Supplement(BaseModel):
    name: str
    dose: str
    form: str
    timing: str
    condition: str | None = None

class RaceGoal(BaseModel):
    event: str
    date: str
    priority: str

class Injury(BaseModel):
    area: str
    status: str
    notes: str | None = None

class Biometrics(BaseModel):
    age: int
    sex: str
    weight_kg: float
    height_cm: float
    body_fat_pct: float | None = None

class TrainingContext(BaseModel):
    phase: str  # base / build / peak / recovery
    weekly_volume_hours: float
    preferred_types: list[str]
    race_goals: list[RaceGoal] = []
    injury_history: list[Injury] = []

    @field_validator("phase")
    @classmethod
    def validate_phase(cls, v: str) -> str:
        allowed = {"base", "build", "peak", "recovery"}
        if v not in allowed:
            msg = f"phase must be one of {allowed}"
            raise ValueError(msg)
        return v

class MedicalHistory(BaseModel):
    conditions: list[str] = []
    medications: list[str] = []
    allergies: list[str] = []

class MetabolicProfile(BaseModel):
    resting_metabolic_rate: int | None = None
    glucose_response: str | None = None

class DietPreferences(BaseModel):
    preference: str
    restrictions: list[str] = []
    meal_timing: str | None = None

class SleepContext(BaseModel):
    chronotype: str | None = None
    target_bedtime: str | None = None
    target_wake: str | None = None
    environment_notes: str | None = None

class HealthProfile(BaseModel):
    biometrics: Biometrics
    training: TrainingContext
    medical: MedicalHistory
    metabolic: MetabolicProfile
    diet: DietPreferences
    supplements: list[Supplement]
    sleep_context: SleepContext
    lab_values: dict[str, LabValue] = {}

def load_health_profile(path: Path) -> HealthProfile:
    with open(path) as f:
        raw = yaml.safe_load(f)
    return HealthProfile.model_validate(raw)
```

### Trend Computation
```python
# Source: Project patterns + Supabase Python docs
from datetime import date, timedelta
from enum import Enum
from statistics import mean
from pydantic import BaseModel
from supabase import Client

TRENDED_METRICS = {
    "hrv_overnight_avg": {"lower_is_better": False},
    "resting_hr": {"lower_is_better": True},
    "sleep_score": {"lower_is_better": False},
    "total_sleep_seconds": {"lower_is_better": False},
    "body_battery_morning": {"lower_is_better": False},
    "avg_stress_level": {"lower_is_better": True},
    "training_load_7d": {"lower_is_better": False},
}

class TrendDirection(str, Enum):
    IMPROVING = "improving"
    DECLINING = "declining"
    STABLE = "stable"
    INSUFFICIENT = "insufficient_data"

class MetricTrend(BaseModel):
    avg: float | None = None
    min_val: float | None = None
    max_val: float | None = None
    direction: TrendDirection = TrendDirection.INSUFFICIENT

class TrendResult(BaseModel):
    window_start: date
    window_end: date
    data_points: int
    metrics: dict[str, MetricTrend]
```

### Supabase Query for Today's Metrics
```python
# Fetch today's complete metrics for prompt injection
def fetch_today_metrics(client: Client, target_date: date) -> dict | None:
    response = (
        client.table("daily_metrics")
        .select("*")
        .eq("date", target_date.isoformat())
        .execute()
    )
    if response.data:
        return response.data[0]
    return None
```

### Supabase Query for Yesterday's Activities
```python
# Fetch yesterday's activities for the prompt section
def fetch_yesterday_activities(client: Client, target_date: date) -> list[dict]:
    yesterday = target_date - timedelta(days=1)
    response = (
        client.table("activities")
        .select("activity_type,name,duration_seconds,avg_hr,max_hr,calories,training_effect_aerobic,training_effect_anaerobic")
        .eq("date", yesterday.isoformat())
        .execute()
    )
    return response.data
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Pydantic v1 `parse_obj()` | Pydantic v2 `model_validate()` | 2023 (Pydantic v2 release) | Use `model_validate()` not deprecated `parse_obj` |
| `from typing import Optional` | `X \| None` union syntax | Python 3.10+ | Project already uses this (ruff UP045) |
| PyYAML `yaml.load()` | `yaml.safe_load()` | Long-standing | Never use `yaml.load()` -- arbitrary code execution risk |
| Manual JSON schema strings | Pydantic `model_json_schema()` | Pydantic v2 | Can auto-generate the DailyProtocol JSON schema for the output format section |

**Deprecated/outdated:**
- `pydantic.parse_raw_as()`, `parse_file_as()`: Removed in Pydantic v2. Use `model_validate()` with pre-loaded data.
- `yaml.load(f)`: Unsafe. Always use `yaml.safe_load()`.

## Open Questions

1. **Exact DailyProtocol JSON schema**
   - What we know: The output format section needs a JSON schema that Phase 3 validates against. Field names include training, recovery, sleep, nutrition, supplementation domains with reasoning chains.
   - What's unclear: Exact field names and nesting depth for v1. This will be finalized when Phase 3 is planned.
   - Recommendation: Define a preliminary Pydantic model for DailyProtocol now. Use `model_json_schema()` to generate the JSON schema string for the prompt. Phase 3 can refine it.

2. **Sports science grounding content**
   - What we know: 3-5 framework blocks needed: HRV interpretation, sleep architecture, ACWR thresholds, periodization principles.
   - What's unclear: Exact phrasing and level of detail for each block.
   - Recommendation: Write short anchors (3-5 sentences each) that provide Claude with key thresholds and interpretation rules. These are static strings in a templates module. Can be refined iteratively.

3. **Health profile YAML file location**
   - What we know: It's a static file alongside the existing `.env`.
   - What's unclear: Should it be `health_profile.yaml` in project root, or configurable via `.env`?
   - Recommendation: Add a `HEALTH_PROFILE_PATH` setting to the Settings class with a default of `health_profile.yaml` (relative to CWD). This follows the existing config pattern.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 + pytest-mock 3.15.1 |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/ -x -q` |
| Full suite command | `uv run pytest tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PROF-01 | YAML health profile loads and validates all sections | unit | `uv run pytest tests/test_profile.py -x` | Wave 0 |
| PROF-01 | Invalid YAML raises clear validation errors | unit | `uv run pytest tests/test_profile.py::TestProfileValidation -x` | Wave 0 |
| PROF-02 | Health profile content appears in assembled prompt | unit | `uv run pytest tests/test_prompt.py::TestPromptAssembly -x` | Wave 0 |
| TRND-01 | 7-day trends computed correctly from mock data | unit | `uv run pytest tests/test_trends.py::TestTrendComputation -x` | Wave 0 |
| TRND-01 | Split-half direction computed correctly (improving/declining/stable) | unit | `uv run pytest tests/test_trends.py::TestTrendDirection -x` | Wave 0 |
| TRND-01 | No-wear days excluded from trend window | unit | `uv run pytest tests/test_trends.py::TestNoWearExclusion -x` | Wave 0 |
| TRND-01 | Insufficient data (<4 points) returns "insufficient_data" | unit | `uv run pytest tests/test_trends.py::TestInsufficientData -x` | Wave 0 |
| TRND-01 | Lower-is-better metrics (resting HR, stress) report correct direction | unit | `uv run pytest tests/test_trends.py::TestLowerIsBetter -x` | Wave 0 |
| TRND-04 | Sports science grounding present in assembled prompt | unit | `uv run pytest tests/test_prompt.py::TestSportsScienceGrounding -x` | Wave 0 |
| ALL | Assembled prompt within token budget | unit | `uv run pytest tests/test_prompt.py::TestTokenBudget -x` | Wave 0 |
| ALL | Assembled prompt contains all required XML sections | unit | `uv run pytest tests/test_prompt.py::TestPromptStructure -x` | Wave 0 |
| ALL | Supabase queries for trend/metrics/activities called correctly | unit | `uv run pytest tests/test_trends.py::TestDataFetching -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/ -x -q`
- **Per wave merge:** `uv run pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_profile.py` -- health profile loading and validation tests
- [ ] `tests/test_trends.py` -- trend computation, direction, data fetching tests
- [ ] `tests/test_prompt.py` -- prompt assembly, token budget, structure tests
- [ ] `tests/fixtures/health_profile.yaml` -- sample YAML fixture for tests
- [ ] `tests/fixtures/trend_data.json` -- mock Supabase response fixtures for trend tests
- [ ] `health_profile.yaml` -- reference health profile config (also serves as documentation)

## Sources

### Primary (HIGH confidence)
- Pydantic v2 official docs - `model_validate()`, `model_json_schema()`, `BaseModel`, `field_validator`
- Supabase Python docs (https://supabase.com/docs/reference/python/using-filters) - filter operators, query chaining, order, select
- Anthropic Claude docs (https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/use-xml-tags) - XML tag best practices, prompt structuring
- Existing codebase (garmin/models.py, config.py, storage/supabase.py, pipeline.py) - established patterns

### Secondary (MEDIUM confidence)
- PyYAML documentation - safe_load behavior, YAML type coercion rules
- Anthropic token counting docs (https://platform.claude.com/docs/en/build-with-claude/token-counting) - ~4 chars/token heuristic validation

### Tertiary (LOW confidence)
- Sports science framework content (to be authored) - HRV interpretation thresholds, ACWR ratios, sleep architecture guidelines will need domain expert review

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries already installed and used in Phase 1; patterns verified against official docs
- Architecture: HIGH - Straightforward integration of YAML loading, Supabase queries, and string assembly; no novel patterns
- Pitfalls: HIGH - Common issues well-documented (YAML coercion, None handling, date boundaries); project-specific pitfalls derived from actual model fields
- Trend computation: HIGH - Simple math (mean, split-half comparison) on small data sets; well-understood
- Prompt structure: MEDIUM - XML tag approach is Anthropic-recommended; exact content/phrasing of sports science grounding and directives will need iteration in Phase 3

**Research date:** 2026-03-03
**Valid until:** 2026-04-03 (stable domain, no fast-moving dependencies)
