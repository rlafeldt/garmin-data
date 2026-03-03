# Phase 3: Analysis Engine - Research

**Researched:** 2026-03-03
**Domain:** Claude API integration, structured JSON output, Pydantic validation, retry logic
**Confidence:** HIGH

## Summary

Phase 3 connects the assembled prompt from Phase 2 to the Anthropic Claude API and produces a validated DailyProtocol JSON object. The existing codebase provides a complete input pipeline (`assemble_prompt()` returns an `AssembledPrompt` with XML-tagged text) and a complete output schema (`DailyProtocol` Pydantic model with 5 domain sub-models). The analysis engine bridges these two: send the prompt to Claude Haiku 4.5 with structured output enforcement, parse the response into `DailyProtocol`, log token usage, store the result in Supabase, and handle degraded data gracefully.

The Anthropic Python SDK now supports structured outputs as a GA feature with direct Pydantic model integration via `client.messages.parse()`. This is the ideal approach: pass the `DailyProtocol` model directly as `output_format`, and the SDK handles schema transformation, constrained decoding, and response validation automatically. This eliminates the need for manual JSON parsing, regex extraction, or retry-on-invalid-JSON logic that was originally anticipated.

**Primary recommendation:** Use `anthropic` SDK with `client.messages.parse(output_format=DailyProtocol)` for guaranteed schema-compliant responses. Wrap in tenacity retry for transient API errors. Store protocol JSON in Supabase with upsert-by-date pattern matching existing `daily_metrics` table.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- Haiku 4.5 as the default model for v1 -- cheapest option (~$0.01/day), sufficient for structured output from a well-crafted prompt
- Config-driven model choice via CLAUDE_MODEL env var in .env -- easy to upgrade to Sonnet if quality is insufficient without code changes
- ANTHROPIC_API_KEY in .env alongside existing Garmin and Supabase credentials
- Log token usage (input/output tokens) per call for cost awareness -- no hard spend cap for a personal tool
- Balanced voice: data-grounded but readable. Lead with the recommendation, follow with the why. Professional but human -- not clinical, not overly casual
- Brief reasoning (2-3 sentences per domain): quick why behind each recommendation, scannable on a morning read
- Always cite specific numbers when they drive the recommendation -- 'HRV 42ms (down from 48ms 7-day avg)' builds trust in the analysis
- Action-first overall summary: lead with what to do today, details in domain sections below
- Borderline readiness: lean toward modified training rather than full rest -- 'do the ride but cap at zone 2 and cut duration' assumes you want to train
- Safety flags only for alarming multi-metric convergence -- sustained HRV crash + resting HR spike + sleep collapse over 3+ days. Don't cry wolf on single bad nights.
- Supplements: adjust within existing stack only -- timing, dosing based on data. Never suggest new supplements
- Nutrition: mix of specific targets and principles -- specific calorie/macro targets when training demands are clear, directional guidance on lighter days
- Partial data: still generate all 5 domains with clear caveats on data-limited sections -- never skip a domain entirely
- No-wear days: generate protocol from 7-day trends + health profile -- something is better than nothing, clearly labeled as trend-based
- Parse failure: retry up to 3 times on invalid JSON, then fail gracefully and log raw response for debugging
- Store full DailyProtocol JSON in Supabase -- enables protocol history, trend in recommendations, weekly summaries later

### Claude's Discretion
- Exact Anthropic SDK client setup and configuration
- Retry backoff strategy and timing
- JSON parsing and validation approach (Pydantic parse vs regex extraction)
- Error logging format (follow existing structlog conventions)
- Supabase table schema for protocol storage
- Temperature and other API parameters
- Whether to use streaming or non-streaming API calls

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TRNG-01 | Assess daily readiness from Body Battery, HRV, resting HR, sleep quality | DailyProtocol.training.readiness_score + readiness_summary fields; prompt already contains analysis_directives for training assessment; sports_science grounding covers HRV interpretation |
| TRNG-02 | Interpret training load with acute-to-chronic ratio, flag overreaching | DailyProtocol.training.training_load_assessment; prompt grounding covers ACWR 0.8-1.3 sweet spot; 7-day trend data feeds load analysis |
| TRNG-03 | Recommend intensity zone, type, and duration based on readiness + load | DailyProtocol.training.recommended_intensity/type/duration_minutes; analysis_directives encode recommendation logic |
| TRNG-04 | Surface stress patterns, connect to training/sleep recommendations | DailyProtocol.recovery.stress_impact; daily metrics include avg_stress_level, high_stress_minutes; directives cross-reference stress |
| SLEP-01 | Analyze sleep architecture quality (deep, REM, awake) | DailyProtocol.sleep.architecture_notes + quality_assessment; metrics include all sleep stage seconds + sleep_score |
| SLEP-02 | Actionable sleep optimization tied to prior-day data | DailyProtocol.sleep.optimization_tips; analysis_directives specify data-driven tips referencing chronotype and environment |
| NUTR-01 | Caloric targets, macro ratios, meal timing from profile + training | DailyProtocol.nutrition covers caloric_target, macro_focus, meal_timing_notes; profile includes diet preferences + metabolic rate |
| NUTR-02 | Hydration targets based on training and recovery | DailyProtocol.nutrition.hydration_target; analysis_directives specify training-day vs rest-day adjustment |
| SUPP-01 | Supplement timing/dosing tied to biometric state and lab values | DailyProtocol.supplementation.adjustments + timing_notes; profile includes full supplement stack with conditional dosing rules |
| SUPP-02 | Conservative advice with reasoning, state assumptions when labs unavailable | DailyProtocol.supplementation.reasoning; user decision: adjust within existing stack only, never suggest new |
| SAFE-02 | Flag concerning patterns, recommend consulting healthcare professional | Analysis engine must detect multi-metric convergence; user decision: only flag alarming 3+ day sustained patterns |
| SAFE-03 | Acknowledge uncertainty, state assumptions when data ambiguous | DailyProtocol.data_quality_notes field; partial data handling generates caveats per domain |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| anthropic | >=0.80.0 | Claude API client with structured output support | Official SDK; `messages.parse()` with Pydantic models is GA for Haiku 4.5 |
| pydantic | (existing) | DailyProtocol output schema + validation | Already used throughout; SDK `parse()` accepts Pydantic BaseModel directly |
| tenacity | (existing) | Retry with exponential backoff on API errors | Already used for Supabase retries; same pattern for Claude API |
| structlog | (existing) | Structured logging for token usage, errors | Already configured project-wide |
| pydantic-settings | (existing) | ANTHROPIC_API_KEY + CLAUDE_MODEL config | Extend existing Settings class |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| supabase | (existing) | Store DailyProtocol JSON in new table | Protocol persistence for history |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `messages.parse()` structured output | Manual JSON parsing + Pydantic `model_validate_json()` | Manual approach requires JSON extraction from response text, regex fallback, retry-on-parse-error. Structured output guarantees schema compliance at the API level. Use `parse()`. |
| Non-streaming API | Streaming API | Streaming adds complexity for no benefit here -- single daily call, response is ~2K tokens, latency is not user-facing. Use non-streaming. |
| Temperature 0 | Temperature 0.3-0.5 | Temperature 0 maximizes determinism but may reduce recommendation variety. Temperature 0.3 is a reasonable balance for analytical output. Discretion area -- recommend 0.3. |

**Installation:**
```bash
uv add anthropic
```

## Architecture Patterns

### Recommended Project Structure
```
src/biointelligence/
├── analysis/                # NEW -- Phase 3 module
│   ├── __init__.py          # Public API: analyze_daily()
│   ├── client.py            # Anthropic client factory + API call wrapper
│   ├── engine.py            # Core analysis orchestration
│   └── storage.py           # Protocol Supabase persistence
├── config.py                # EXTEND -- add ANTHROPIC_API_KEY, CLAUDE_MODEL
├── pipeline.py              # EXTEND -- add run_analysis() function
├── prompt/                  # EXISTING -- consumed by analysis engine
│   ├── models.py            # DailyProtocol already defined here
│   └── assembler.py         # assemble_prompt() already defined here
└── ...
```

### Pattern 1: Anthropic Client Factory with Structured Output
**What:** Create an Anthropic client and call `messages.parse()` with the DailyProtocol Pydantic model for guaranteed schema-compliant output.
**When to use:** Every analysis call.
**Example:**
```python
# Source: https://platform.claude.com/docs/en/build-with-claude/structured-outputs
import anthropic
from biointelligence.prompt.models import DailyProtocol

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

response = client.messages.parse(
    model=settings.claude_model,
    max_tokens=4096,
    temperature=0.3,
    messages=[{"role": "user", "content": assembled_prompt.text}],
    output_format=DailyProtocol,
)

protocol: DailyProtocol = response.parsed_output
input_tokens = response.usage.input_tokens
output_tokens = response.usage.output_tokens
```

### Pattern 2: Tenacity Retry for Transient API Errors
**What:** Wrap the Claude API call in tenacity retry matching existing Supabase retry pattern.
**When to use:** Every API call -- handles rate limits, timeouts, transient failures.
**Example:**
```python
# Source: Existing pattern in storage/supabase.py
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential
import anthropic

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=4, max=60),
    retry=retry_if_exception_type((
        anthropic.RateLimitError,
        anthropic.InternalServerError,
        anthropic.APIConnectionError,
    )),
)
def call_claude(client, model, prompt_text, max_tokens=4096, temperature=0.3):
    return client.messages.parse(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        messages=[{"role": "user", "content": prompt_text}],
        output_format=DailyProtocol,
    )
```

### Pattern 3: AnalysisResult Pydantic Model (follows IngestionResult pattern)
**What:** Return a structured result from `run_analysis()` like existing `IngestionResult`.
**When to use:** Pipeline integration.
**Example:**
```python
from pydantic import BaseModel
from datetime import date

class AnalysisResult(BaseModel):
    """Result of a pipeline analysis run."""
    date: date
    protocol: DailyProtocol
    input_tokens: int
    output_tokens: int
    model: str
    success: bool
    error: str | None = None
```

### Pattern 4: Supabase Protocol Storage (upsert-by-date)
**What:** Store the full DailyProtocol JSON in a `daily_protocols` table, keyed on date.
**When to use:** After successful Claude API call.
**Example:**
```python
# Follows existing upsert_daily_metrics pattern
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    retry=retry_if_exception_type((ConnectionError, TimeoutError)),
)
def upsert_daily_protocol(client, protocol: DailyProtocol, metadata: dict) -> None:
    record = {
        "date": protocol.date,
        "protocol": protocol.model_dump(mode="json"),
        "model": metadata["model"],
        "input_tokens": metadata["input_tokens"],
        "output_tokens": metadata["output_tokens"],
        "created_at": metadata.get("created_at"),
    }
    client.table("daily_protocols").upsert(record, on_conflict="date").execute()
```

### Anti-Patterns to Avoid
- **Manually parsing JSON from Claude's response text:** With structured outputs GA for Haiku 4.5, never use regex or `json.loads()` on raw response. Use `messages.parse()`.
- **Skipping token usage logging:** Always log `response.usage.input_tokens` and `response.usage.output_tokens` for cost tracking.
- **Retrying on parse validation errors:** With constrained decoding, schema violations are impossible (unless `stop_reason` is `"max_tokens"` or `"refusal"`). Retry only on transient API errors.
- **Hardcoding model name:** Use `settings.claude_model` from env var, not a string literal.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON schema enforcement | Manual JSON parsing + regex extraction + retry on invalid JSON | `client.messages.parse(output_format=DailyProtocol)` | SDK uses constrained decoding at the API level -- structurally impossible to get invalid JSON |
| Retry with backoff | Custom sleep loops | `tenacity` with `wait_exponential` | Already used in project; handles jitter, max attempts, exception filtering |
| API error classification | Manual HTTP status checking | Anthropic SDK typed exceptions (`RateLimitError`, `InternalServerError`, etc.) | SDK provides granular exception types for retry logic |
| Schema transformation | Manual `additionalProperties: false` injection, constraint removal | SDK `transform_schema()` (called automatically by `parse()`) | SDK handles Pydantic model -> JSON Schema -> API-compatible schema automatically |
| Token counting | Character-based heuristic for output | `response.usage.input_tokens` / `output_tokens` | Exact counts from API response; no guessing needed |

**Key insight:** The Anthropic SDK's structured output support with Pydantic eliminates the largest complexity in this phase. The `messages.parse()` method handles schema transformation, constrained decoding, and response validation -- the analysis engine is primarily orchestration code, not parsing code.

## Common Pitfalls

### Pitfall 1: max_tokens Too Low for DailyProtocol
**What goes wrong:** Response gets cut off (`stop_reason: "max_tokens"`), producing incomplete/invalid JSON even with structured outputs.
**Why it happens:** DailyProtocol has 5 domains with reasoning fields -- output is typically 1500-3000 tokens. Setting max_tokens too low (e.g., 1024) will truncate.
**How to avoid:** Set `max_tokens=4096` as default. Check `response.stop_reason` -- if `"max_tokens"`, log a warning and retry with higher limit.
**Warning signs:** `stop_reason` is `"max_tokens"` instead of `"end_turn"`.

### Pitfall 2: Structured Output Schema Limitations
**What goes wrong:** The DailyProtocol Pydantic model uses `Field(..., ge=1, le=10)` for `readiness_score`. Structured outputs do NOT support `minimum`/`maximum` constraints.
**Why it happens:** Anthropic's constrained decoding supports basic JSON Schema types but not numerical constraints.
**How to avoid:** The SDK's `transform_schema()` (called automatically by `parse()`) strips unsupported constraints and adds them to field descriptions. The SDK then validates the response against the original Pydantic model client-side. This works transparently. However, be aware that Claude might occasionally produce out-of-range values that pass API-level validation but fail Pydantic validation.
**Warning signs:** `ValidationError` from Pydantic after `parse()` -- the SDK raises this if response violates Pydantic constraints.

### Pitfall 3: Not Handling Refusals
**What goes wrong:** Claude refuses a request for safety reasons (`stop_reason: "refusal"`). The response does not match the schema.
**Why it happens:** Even with structured outputs, Claude's safety properties take precedence. Unlikely for health analysis prompts, but possible if concerning data triggers safety filters.
**How to avoid:** Check `response.stop_reason` explicitly. If `"refusal"`, log the refusal content and fail gracefully rather than trying to parse.
**Warning signs:** `stop_reason` is `"refusal"` instead of `"end_turn"`.

### Pitfall 4: Grammar Compilation Latency on First Call
**What goes wrong:** First API call with a new schema takes significantly longer than subsequent calls.
**Why it happens:** Anthropic compiles the JSON schema into a grammar on first use, cached for 24 hours.
**How to avoid:** Accept first-call latency (not user-facing for a daily pipeline). The grammar cache persists across calls with the same schema structure.
**Warning signs:** First daily call taking 10-30 seconds; subsequent calls taking 3-8 seconds.

### Pitfall 5: Optional Fields and Schema Complexity Limits
**What goes wrong:** Structured outputs have a limit of 24 optional parameters across all schemas.
**Why it happens:** Optional parameters double grammar state space.
**How to avoid:** The DailyProtocol model has only 1 optional field (`data_quality_notes`). This is well within limits. If future schema evolution adds many optional fields, watch the 24-parameter limit.
**Warning signs:** 400 error mentioning "Schema is too complex for compilation."

### Pitfall 6: Forgetting to Log Token Usage
**What goes wrong:** No visibility into API costs. User decision explicitly requires logging token usage per call.
**Why it happens:** Easy to focus on the response and forget the metadata.
**How to avoid:** Always extract and log `response.usage.input_tokens` and `response.usage.output_tokens` immediately after API call.
**Warning signs:** No token usage in logs; surprise API bill.

## Code Examples

Verified patterns from official sources:

### Complete Analysis Engine Call
```python
# Source: https://platform.claude.com/docs/en/build-with-claude/structured-outputs
# Combined with existing project patterns

import anthropic
import structlog
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from biointelligence.config import Settings
from biointelligence.prompt.models import AssembledPrompt, DailyProtocol

log = structlog.get_logger()


def get_anthropic_client(settings: Settings) -> anthropic.Anthropic:
    """Create an Anthropic client from settings."""
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=4, max=60),
    retry=retry_if_exception_type((
        anthropic.RateLimitError,
        anthropic.InternalServerError,
        anthropic.APIConnectionError,
    )),
)
def analyze_prompt(
    client: anthropic.Anthropic,
    prompt: AssembledPrompt,
    model: str,
    max_tokens: int = 4096,
    temperature: float = 0.3,
) -> tuple[DailyProtocol, dict]:
    """Send assembled prompt to Claude and return validated DailyProtocol.

    Returns:
        Tuple of (DailyProtocol, metadata dict with token usage).
    """
    response = client.messages.parse(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        messages=[{"role": "user", "content": prompt.text}],
        output_format=DailyProtocol,
    )

    # Check stop reason
    if response.stop_reason == "max_tokens":
        log.warning("analysis_truncated", stop_reason="max_tokens")
    if response.stop_reason == "refusal":
        log.error("analysis_refused", stop_reason="refusal")
        raise ValueError("Claude refused the analysis request")

    protocol = response.parsed_output
    metadata = {
        "model": model,
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "stop_reason": response.stop_reason,
    }

    log.info(
        "analysis_complete",
        model=model,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        stop_reason=response.stop_reason,
    )

    return protocol, metadata
```

### Settings Extension
```python
# Source: Existing config.py pattern
class Settings(BaseSettings):
    # ... existing fields ...

    # Anthropic
    anthropic_api_key: str
    claude_model: str = "claude-haiku-4-5-20250514"
```

### Supabase Table Schema (daily_protocols)
```sql
-- Follows existing daily_metrics table pattern
CREATE TABLE daily_protocols (
    id BIGSERIAL PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    protocol JSONB NOT NULL,
    model TEXT NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for date lookups
CREATE INDEX idx_daily_protocols_date ON daily_protocols(date);
```

### Pipeline Integration
```python
# Source: Existing pipeline.py pattern
class AnalysisResult(BaseModel):
    """Result of a pipeline analysis run."""
    date: date
    protocol: DailyProtocol
    input_tokens: int
    output_tokens: int
    model: str
    success: bool


def run_analysis(target_date: date, settings: Settings | None = None) -> AnalysisResult:
    """Run the analysis pipeline for a single date.

    Stages:
        1. Load health profile and metrics
        2. Compute trends
        3. Assemble prompt
        4. Call Claude API with structured output
        5. Store protocol in Supabase
    """
    # ... orchestration code ...
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Beta structured outputs (`output_format` + beta header) | GA structured outputs (`output_config.format`) | Feb 2026 | No beta headers needed; `messages.parse()` with `output_format` is the SDK convenience method (SDK translates internally) |
| Manual JSON parsing + regex extraction | `client.messages.parse(output_format=PydanticModel)` | Nov 2025 (beta), Feb 2026 (GA) | Eliminates retry-on-parse-error, regex fallback, JSON extraction logic |
| Tool-use trick for structured output | Native `json_schema` output format | Nov 2025 | Cleaner API; constrained decoding instead of tool-use workaround |

**Deprecated/outdated:**
- Beta header `anthropic-beta: structured-outputs-2025-11-13` -- still works but deprecated. Use GA `output_config.format` or SDK `messages.parse()`.
- Tool-use trick for structured JSON -- replaced by native structured output support.

## Open Questions

1. **Exact Haiku 4.5 model string for API calls**
   - What we know: Model is `claude-haiku-4-5-20250514` based on Anthropic naming convention. The user wants config-driven model via CLAUDE_MODEL env var.
   - What's unclear: Whether a newer Haiku date stamp exists. The model string should be verified during implementation.
   - Recommendation: Use `claude-haiku-4-5-20250514` as default, configurable via env var. The SDK will return a clear error if the model string is invalid.

2. **Pydantic validation after structured output parse**
   - What we know: SDK `parse()` uses constrained decoding at API level AND validates against Pydantic model client-side. The `readiness_score` field has `ge=1, le=10` -- these constraints are stripped from the sent schema but enforced client-side by the SDK.
   - What's unclear: How frequently Haiku 4.5 produces values that pass API-level schema validation but fail Pydantic constraints (e.g., readiness_score=0).
   - Recommendation: Keep the Pydantic constraints. If `ValidationError` occurs, catch it, log the raw response, and retry once. This should be rare with a well-crafted prompt.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-mock (existing) |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/test_analysis.py -x` |
| Full suite command | `uv run pytest tests/ -x` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TRNG-01 | Readiness assessment in protocol output | unit | `uv run pytest tests/test_analysis.py::TestAnalyzePrompt::test_protocol_has_training_readiness -x` | No -- Wave 0 |
| TRNG-02 | Training load assessment populated | unit | `uv run pytest tests/test_analysis.py::TestAnalyzePrompt::test_protocol_has_training_load -x` | No -- Wave 0 |
| TRNG-03 | Recommended intensity/type/duration populated | unit | `uv run pytest tests/test_analysis.py::TestAnalyzePrompt::test_protocol_has_training_recommendation -x` | No -- Wave 0 |
| TRNG-04 | Stress impact in recovery section | unit | `uv run pytest tests/test_analysis.py::TestAnalyzePrompt::test_protocol_has_stress_impact -x` | No -- Wave 0 |
| SLEP-01 | Sleep architecture analysis populated | unit | `uv run pytest tests/test_analysis.py::TestAnalyzePrompt::test_protocol_has_sleep_analysis -x` | No -- Wave 0 |
| SLEP-02 | Sleep optimization tips non-empty | unit | `uv run pytest tests/test_analysis.py::TestAnalyzePrompt::test_protocol_has_sleep_tips -x` | No -- Wave 0 |
| NUTR-01 | Caloric target + macro focus populated | unit | `uv run pytest tests/test_analysis.py::TestAnalyzePrompt::test_protocol_has_nutrition -x` | No -- Wave 0 |
| NUTR-02 | Hydration target populated | unit | `uv run pytest tests/test_analysis.py::TestAnalyzePrompt::test_protocol_has_hydration -x` | No -- Wave 0 |
| SUPP-01 | Supplementation adjustments non-empty | unit | `uv run pytest tests/test_analysis.py::TestAnalyzePrompt::test_protocol_has_supplements -x` | No -- Wave 0 |
| SUPP-02 | Supplementation reasoning non-empty | unit | `uv run pytest tests/test_analysis.py::TestAnalyzePrompt::test_protocol_has_supplement_reasoning -x` | No -- Wave 0 |
| SAFE-02 | Protocol includes data_quality_notes when data ambiguous | unit | `uv run pytest tests/test_analysis.py::TestDegradedData::test_partial_data_includes_caveats -x` | No -- Wave 0 |
| SAFE-03 | Protocol states assumptions when data missing | unit | `uv run pytest tests/test_analysis.py::TestDegradedData::test_no_wear_uses_trends -x` | No -- Wave 0 |

### Testing Strategy
All tests mock the Anthropic API call (never call the real API in tests). Tests verify:
1. **Client factory:** Correct client initialization from settings
2. **API call structure:** Correct model, max_tokens, temperature, output_format passed
3. **Response handling:** Stop reason checking, token usage extraction
4. **Protocol validation:** All 5 domains populated, reasoning fields non-empty
5. **Error handling:** Retry on transient errors, graceful failure on refusals
6. **Storage:** Protocol upserted to Supabase with correct schema
7. **Pipeline integration:** `run_analysis()` orchestrates all steps correctly

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_analysis.py -x`
- **Per wave merge:** `uv run pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_analysis.py` -- covers all analysis engine tests (TRNG-01 through SAFE-03)
- [ ] Mock fixtures: fake `DailyProtocol` response, mock `anthropic.Anthropic` client
- [ ] Framework install: `uv add anthropic` -- new dependency

## Sources

### Primary (HIGH confidence)
- [Anthropic Structured Outputs Documentation (GA)](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) -- Full API reference for `output_config.format`, `messages.parse()`, Pydantic integration, JSON schema limitations, schema complexity limits, stop reasons
- [Anthropic Python SDK on PyPI](https://pypi.org/project/anthropic/) -- Version >=0.80.0 supports GA structured outputs
- [Anthropic Pricing Page](https://platform.claude.com/docs/en/about-claude/pricing) -- Haiku 4.5: $1 input / $5 output per million tokens

### Secondary (MEDIUM confidence)
- [Anthropic SDK GitHub](https://github.com/anthropics/anthropic-sdk-python) -- Latest releases, changelog
- Existing project code: `storage/supabase.py`, `pipeline.py`, `config.py` -- Established patterns for retry, settings, pipeline results

### Tertiary (LOW confidence)
- None -- all findings verified against official documentation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- `anthropic` SDK is the official client; structured outputs GA confirmed for Haiku 4.5 in official docs
- Architecture: HIGH -- follows established project patterns (tenacity retry, pydantic-settings, Supabase upsert, IngestionResult model)
- Pitfalls: HIGH -- schema limitations, stop reasons, and complexity limits documented in official Anthropic docs

**Research date:** 2026-03-03
**Valid until:** 2026-04-03 (stable -- Anthropic SDK and structured outputs are GA)
