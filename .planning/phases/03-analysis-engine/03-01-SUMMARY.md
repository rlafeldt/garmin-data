---
phase: 03-analysis-engine
plan: 01
subsystem: analysis
tags: [anthropic, claude-api, structured-output, retry, pydantic, tdd]
dependency_graph:
  requires:
    - prompt/assembler.py (AssembledPrompt input)
    - prompt/models.py (DailyProtocol output schema)
    - config.py (Settings with env vars)
    - profile/loader.py (health profile loading)
    - trends/compute.py (7-day trend computation)
    - storage/supabase.py (data fetching)
  provides:
    - analysis/client.py (Anthropic client factory + structured output call)
    - analysis/engine.py (AnalysisResult model + analyze_daily orchestration)
    - analysis/__init__.py (public API: analyze_daily, AnalysisResult)
  affects:
    - config.py (extended with anthropic_api_key, claude_model)
    - tests/test_client.py (added ANTHROPIC_API_KEY to env fixtures)
    - tests/test_storage.py (added ANTHROPIC_API_KEY to env fixtures)
    - tests/test_pipeline.py (added ANTHROPIC_API_KEY to env fixtures)
tech_stack:
  added:
    - anthropic>=0.84.0
  patterns:
    - client.messages.parse(output_format=DailyProtocol) for structured output
    - tenacity retry for transport errors (RateLimitError, InternalServerError, APIConnectionError)
    - Explicit retry loop for parse failures (ValidationError) per user decision
    - AnalysisResult model following IngestionResult pattern
key_files:
  created:
    - src/biointelligence/analysis/__init__.py
    - src/biointelligence/analysis/client.py
    - src/biointelligence/analysis/engine.py
    - tests/test_analysis.py
  modified:
    - src/biointelligence/config.py
    - pyproject.toml
    - tests/test_client.py
    - tests/test_storage.py
    - tests/test_pipeline.py
decisions:
  - "Used messages.parse() with output_format=DailyProtocol for structured output (SDK GA feature)"
  - "Two-layer retry: tenacity for transport errors, explicit loop for ValidationError parse failures"
  - "Temperature 0.3 and max_tokens 4096 as defaults (configurable via function args)"
  - "Lazy imports in __init__.py via __getattr__ pattern (matching prompt/ module)"
metrics:
  duration: 7min
  completed: "2026-03-03T20:07:33Z"
---

# Phase 03 Plan 01: Analysis Engine Core Summary

Anthropic client factory with structured output via messages.parse(output_format=DailyProtocol), two-layer retry (tenacity for transport + explicit loop for parse failures), and analyze_daily orchestration returning AnalysisResult

## What Was Built

### analysis/client.py -- Anthropic Client and Structured Output Call
- `get_anthropic_client(settings)`: Factory creating Anthropic client from settings.anthropic_api_key
- `analyze_prompt(client, prompt, model)`: Sends assembled prompt to Claude, returns (DailyProtocol, metadata) tuple
  - Uses `client.messages.parse(output_format=DailyProtocol)` for guaranteed schema-compliant output
  - Layer 1: tenacity decorator retries on RateLimitError, InternalServerError, APIConnectionError (3 attempts, exponential backoff)
  - Layer 2: explicit loop retries up to 3 times on pydantic ValidationError with raw response logging
  - Detects refusal stop_reason (raises ValueError) and max_tokens truncation (logs warning)
  - Logs token usage (input/output) via structlog on every successful call

### analysis/engine.py -- Orchestration and Result Model
- `AnalysisResult(BaseModel)`: date, protocol, input_tokens, output_tokens, model, success, error (follows IngestionResult pattern)
- `analyze_daily(target_date, settings)`: Full orchestration pipeline:
  1. Load health profile from YAML
  2. Fetch daily metrics and activities from Supabase
  3. Compute 7-day trends
  4. Assemble Claude prompt via assemble_prompt()
  5. Call Claude API via analyze_prompt()
  6. Return AnalysisResult with success/error status
- Helper functions `_fetch_daily_metrics()` and `_fetch_activities()` for Supabase queries

### config.py -- Settings Extension
- Added `anthropic_api_key: str` (required, from ANTHROPIC_API_KEY env var)
- Added `claude_model: str = "claude-haiku-4-5-20250514"` (default Haiku 4.5, from CLAUDE_MODEL env var)

### tests/test_analysis.py -- 30 Tests with Mocked Anthropic Client
- TestGetAnthropicClient (1 test): client factory with API key
- TestAnalyzePrompt (8 tests): parameters, return values, token logging, refusal, max_tokens, retry on transport errors, retry on ValidationError, re-raise after 3 failures
- TestSettingsExtension (3 tests): anthropic_api_key required, claude_model default, claude_model override
- TestAnalysisResult (3 tests): full fields, failure case, defaults
- TestAnalyzeDaily (3 tests): happy path, error handling, logging
- TestProtocolDomains (12 tests): all 12 requirement IDs verified via field assertions

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 (RED) | e7dc5e1 | Failing tests for client, retry, Settings |
| 1 (GREEN) | 664da63 | Implement client factory, structured output, retry, Settings |
| 2 (RED) | 83179fd | Failing tests for engine orchestration and protocol domains |
| 2 (GREEN) | 76efbed | Implement engine orchestration with AnalysisResult |

## Test Results

- `uv run pytest tests/test_analysis.py -x -v`: 30 passed
- `uv run pytest tests/ -x`: 140 passed (30 new + 110 existing)
- `uv run ruff check src/biointelligence/analysis/`: All checks passed
- Module import verification: OK

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Added ANTHROPIC_API_KEY to existing test fixtures**
- **Found during:** Task 1 GREEN phase
- **Issue:** Adding required `anthropic_api_key` field to Settings broke 3 existing test files that create Settings instances without the new field
- **Fix:** Added `monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")` to all Settings-constructing fixtures in test_client.py, test_storage.py, test_pipeline.py
- **Files modified:** tests/test_client.py, tests/test_storage.py, tests/test_pipeline.py
- **Commit:** 664da63

**2. [Rule 1 - Bug] Fixed ruff F841 unused variable warning**
- **Found during:** Task 1 GREEN phase
- **Issue:** `last_error` variable in client.py was assigned but never read (ruff F841)
- **Fix:** Removed the unused variable assignment
- **Files modified:** src/biointelligence/analysis/client.py
- **Commit:** 664da63

**3. [Rule 1 - Bug] Added PromptContext mock to engine tests**
- **Found during:** Task 2 GREEN phase
- **Issue:** Engine tests failed because mocked return values (MagicMock) were being passed to PromptContext Pydantic model which validates input types
- **Fix:** Added `@patch("biointelligence.analysis.engine.PromptContext")` to all analyze_daily tests
- **Files modified:** tests/test_analysis.py
- **Commit:** 76efbed

## Decisions Made

1. **Structured output via messages.parse()**: Used SDK GA structured output feature with `output_format=DailyProtocol` instead of manual JSON parsing
2. **Two-layer retry strategy**: Tenacity for transport errors (automatic), explicit loop for parse failures (per user decision to retry up to 3 times with raw response logging)
3. **Temperature 0.3**: Balance between determinism and recommendation variety for analytical output
4. **max_tokens 4096**: Sufficient headroom for 5-domain DailyProtocol output (~1500-3000 tokens typical)

## Requirements Coverage

| Req ID | Test | Status |
|--------|------|--------|
| TRNG-01 | test_trng01_readiness_score | PASS |
| TRNG-02 | test_trng02_training_load_assessment | PASS |
| TRNG-03 | test_trng03_training_recommendations | PASS |
| TRNG-04 | test_trng04_stress_impact | PASS |
| SLEP-01 | test_slep01_sleep_architecture | PASS |
| SLEP-02 | test_slep02_sleep_optimization | PASS |
| NUTR-01 | test_nutr01_nutrition_guidance | PASS |
| NUTR-02 | test_nutr02_hydration_target | PASS |
| SUPP-01 | test_supp01_supplement_adjustments | PASS |
| SUPP-02 | test_supp02_supplement_reasoning | PASS |
| SAFE-02 | test_safe02_data_quality_notes | PASS |
| SAFE-03 | test_safe02_data_quality_notes | PASS |

## Self-Check: PASSED

All 5 created files verified on disk. All 4 commit hashes verified in git log.
