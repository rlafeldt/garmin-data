---
phase: 02-health-profile-and-prompt-assembly
plan: 02
subsystem: prompt-assembly
tags: [pydantic, xml-prompt, token-budget, sports-science, daily-protocol, structlog]

# Dependency graph
requires:
  - phase: 01-data-ingestion-and-storage
    provides: DailyMetrics model, Activity model, structlog logging
  - phase: 02-health-profile-and-prompt-assembly
    provides: HealthProfile model, TrendResult model, TrendDirection enum
provides:
  - PromptContext model aggregating all data sources for prompt assembly
  - AssembledPrompt model with text, token estimate, and section metadata
  - DailyProtocol 5-domain output schema (training, recovery, sleep, nutrition, supplementation)
  - assemble_prompt function producing XML-tagged Claude prompt
  - Sports science grounding blocks (HRV, sleep architecture, ACWR, periodization)
  - Analysis directives for all 5 domains
  - Token budget estimation and priority-based trimming
affects: [03-analysis-engine]

# Tech tracking
tech-stack:
  added: []
  patterns: [xml-tagged-prompt-sections, token-budget-trimming, pydantic-json-schema-output-spec]

key-files:
  created:
    - src/biointelligence/prompt/__init__.py
    - src/biointelligence/prompt/models.py
    - src/biointelligence/prompt/assembler.py
    - src/biointelligence/prompt/templates.py
    - src/biointelligence/prompt/budget.py
    - tests/test_prompt.py
  modified: []

key-decisions:
  - "Lazy import for assemble_prompt in __init__.py to avoid circular import issues"
  - "DailyProtocol uses model_json_schema() for auto-generated output format spec"

patterns-established:
  - "XML-tagged sections: <tag>\\ncontent\\n</tag> for structured prompt assembly"
  - "Priority-based budget trimming: lowest-value sections removed first, critical sections protected"
  - "Token estimation: len(text) // 4 heuristic, no external tokenizer"
  - "model_dump(mode='json') for consistent Pydantic serialization to prompt text"

requirements-completed: [PROF-02, TRND-04]

# Metrics
duration: 6min
completed: 2026-03-03
---

# Phase 2 Plan 02: Prompt Assembly Summary

**XML-tagged Claude prompt assembler with 7 sections, DailyProtocol JSON output schema, sports science grounding, and token budget enforcement (~4K-6K tokens)**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-03T19:12:02Z
- **Completed:** 2026-03-03T19:18:00Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Complete prompt assembler wiring health profile, today's metrics, 7-day trends, yesterday's activities, sports science grounding, analysis directives, and DailyProtocol output schema into XML-tagged sections
- DailyProtocol Pydantic model defining 5-domain output schema with readiness scores, recommendations, and reasoning chains for each domain
- Sports science grounding covering HRV interpretation, sleep architecture guidelines, ACWR thresholds, and periodization principles
- Token budget management with priority-based trimming (sports_science first, never trim metrics or profile)
- 31 prompt-specific tests plus 110 total tests passing across all phases

## Task Commits

Each task was committed atomically (TDD: test then feat):

1. **Task 1: Prompt models, sports science templates, and token budget management**
   - `5bcc1b0` (test) - Failing tests for models, templates, and budget
   - `8ef3e2e` (feat) - PromptContext, AssembledPrompt, DailyProtocol, templates, budget module
2. **Task 2: Prompt assembler wiring all data sources into XML-tagged prompt**
   - `1033bf8` (test) - Failing tests for assembler with fixtures
   - `c1b2437` (feat) - assemble_prompt function with all formatters

## Files Created/Modified
- `src/biointelligence/prompt/__init__.py` - Public exports: PromptContext, AssembledPrompt, DailyProtocol, assemble_prompt
- `src/biointelligence/prompt/models.py` - PromptContext, AssembledPrompt, DailyProtocol with 5 domain sub-models
- `src/biointelligence/prompt/assembler.py` - assemble_prompt and formatters for metrics, trends, activities, profile, output schema
- `src/biointelligence/prompt/templates.py` - SPORTS_SCIENCE_GROUNDING and ANALYSIS_DIRECTIVES constants
- `src/biointelligence/prompt/budget.py` - estimate_tokens, trim_to_budget, SECTION_PRIORITY, NEVER_TRIM
- `tests/test_prompt.py` - 31 tests for models, templates, budget, assembler, and edge cases

## Decisions Made
- Lazy import for assemble_prompt in __init__.py to avoid circular import potential -- uses __getattr__ pattern
- DailyProtocol uses Pydantic model_json_schema() to auto-generate the output format specification embedded in the prompt
- Formatters produce human-readable text (not raw JSON) for all sections -- sleep seconds converted to hours:minutes, metrics grouped by category

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- assemble_prompt ready for Phase 3's Claude API call
- DailyProtocol JSON schema defines the expected output format for response parsing
- All 110 tests passing (41 Phase 1 + 38 Phase 2 Plan 01 + 31 Phase 2 Plan 02)
- Phase 2 complete: health profile loading, trend computation, and prompt assembly all ready

## Self-Check: PASSED

All 6 created files verified on disk. All 4 task commits verified in git history.

---
*Phase: 02-health-profile-and-prompt-assembly*
*Completed: 2026-03-03*
