# Phase 2: Health Profile and Prompt Assembly - Context

**Gathered:** 2026-03-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Load personal health profile from a YAML config file, compute 7-day rolling trend statistics from stored Supabase data, and assemble a structured Claude prompt with XML-tagged sections. The output is a complete prompt string ready for Phase 3's Claude API call. Analysis logic, protocol generation, and email delivery are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Health profile content
- Comprehensive reference profile with all PROF-01 sections filled in detail: biometrics (age, sex, weight, height, body fat %), training goals, medical history, metabolic profile, diet preferences, current supplements, sleep context, and lab values
- Lab values typed with dates and reference ranges — each entry includes value, unit, test date, and reference range (e.g., `vitamin_d: {value: 42, unit: ng/mL, date: 2025-11, range: '30-100'}`). Claude can flag stale values and calibrate supplement doses.
- Structured training context included: current training phase (base/build/peak/recovery), weekly volume targets, race goals with dates, injury history, preferred training types (cycling and strength from Phase 1 context)
- Full supplement stack with timing, form, and conditional dosing rules (e.g., `magnesium_glycinate: {dose: 400mg, form: glycinate, timing: evening, condition: 'increase to 600mg on high-stress days'}`)

### Trend computation
- Core readiness metrics only get 7-day rolling trends: HRV overnight avg, resting HR, sleep score, total sleep duration, body battery morning, avg stress level, training load 7d
- Statistics per trended metric: 7-day average, trend direction (improving/declining/stable), min, max
- Trend direction via split-half comparison: average of first half vs second half of window, >5% change = improving/declining, otherwise stable
- Minimum 4 of 7 days of data required for trend computation; below that, trend marked as "insufficient data"
- No-wear days (from Phase 1 `is_no_wear` flag) excluded from trend windows
- All other DailyMetrics fields passed as today-only values without trend context

### Prompt architecture
- Structured directive style: each analysis domain (training, recovery, sleep, nutrition, supplementation) gets specific instructions telling Claude exactly what to analyze and what to recommend
- Sports science grounding via 3-5 core framework reference blocks embedded in the prompt: HRV interpretation model, sleep architecture guidelines, acute-to-chronic load ratio thresholds, periodization principles. Short anchors, not exhaustive references.
- Yesterday's activities included as a dedicated prompt section (type, duration, intensity, training effect) — connects today's readiness to prior training. Uses existing Phase 1 Activity model data.
- Output format specified as JSON schema with examples — defines the DailyProtocol structure that Phase 3 will validate against. Guarantees parseable, structured output.

### Token budget
- Target prompt size: ~4K-6K tokens
- Token counting via word-based heuristic (~1 token per 4 characters). No external tokenizer dependency. Calibrate with actual Claude API token usage in Phase 3.
- Trimming priority when over budget: 1) Today's metrics (never cut) 2) Health profile (never cut) 3) Activities 4) 7-day trends 5) Sports science grounding. Grounding is most compressible.
- Only pre-computed normalized values in the prompt — raw Garmin JSON stays in Supabase for debugging, never enters the prompt

### Claude's Discretion
- Exact YAML schema structure for the health profile (section names, nesting)
- XML tag naming conventions for prompt sections
- Specific sports science framework content and phrasing
- Exact DailyProtocol JSON schema field names and nesting
- SQL query design for fetching trend data from Supabase
- Pydantic model design for health profile and prompt assembly
- Error handling and logging patterns (follow Phase 1 structlog conventions)

</decisions>

<specifics>
## Specific Ideas

- Prompt should produce consistent, reliable output across runs — structured directive over open-ended
- Lab values with dates allow Claude to flag "your vitamin D was tested 8 months ago" type staleness
- Conditional supplement dosing lets Claude say "increase magnesium tonight" based on today's stress data
- Training context (periodization phase, race goals) grounds recommendations beyond what Garmin metrics alone reveal
- Activities section connects readiness to actual training — "yesterday you did a hard cycling session, so..."

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `DailyMetrics` model (garmin/models.py): 25+ fields covering all metric categories — trend computation queries against these exact field names
- `Activity` model (garmin/models.py): captures type, duration, HR, training effect — directly usable for activity summary prompt section
- `CompletenessResult` and `assess_completeness()`: completeness scoring and no-wear detection — trend computation uses `is_no_wear` flag
- `Settings` class (config.py): pydantic-settings with .env loading — health profile YAML loading follows same pattern
- `get_supabase_client()` (storage/supabase.py): existing Supabase client factory with tenacity retries

### Established Patterns
- Pydantic models for all data structures (DailyMetrics, Activity, Settings) — health profile and prompt models should follow this
- structlog for all logging — maintain throughout Phase 2
- pydantic-settings with .env for configuration — YAML profile is a new config type alongside .env
- tenacity for retry logic on Supabase calls — reuse for trend data fetching
- `X | None` type syntax (modern Python, ruff UP045)

### Integration Points
- Supabase `daily_metrics` table: trend computation queries SELECT from this table with date range filters
- Supabase `activities` table: yesterday's activities fetched for prompt section
- `run_ingestion()` pipeline (pipeline.py): Phase 2 adds a parallel entry point (prompt assembly) that reads from the same Supabase tables that ingestion writes to
- Config: new YAML health profile file alongside existing .env — Settings class may need extension or a separate ProfileConfig class

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-health-profile-and-prompt-assembly*
*Context gathered: 2026-03-03*
