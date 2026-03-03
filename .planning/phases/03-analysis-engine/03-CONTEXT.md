# Phase 3: Analysis Engine - Context

**Gathered:** 2026-03-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Claude API integration that takes the assembled prompt from Phase 2 and produces a validated DailyProtocol JSON covering training, recovery, sleep, nutrition, and supplementation with safety guardrails. The output is a validated DailyProtocol object ready for Phase 4's rendering and email delivery. Protocol rendering, email delivery, and pipeline automation are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Claude model selection
- Haiku 4.5 as the default model for v1 — cheapest option (~$0.01/day), sufficient for structured output from a well-crafted prompt
- Config-driven model choice via CLAUDE_MODEL env var in .env — easy to upgrade to Sonnet if quality is insufficient without code changes
- ANTHROPIC_API_KEY in .env alongside existing Garmin and Supabase credentials
- Log token usage (input/output tokens) per call for cost awareness — no hard spend cap for a personal tool

### Protocol tone & personality
- Balanced voice: data-grounded but readable. Lead with the recommendation, follow with the why. Professional but human — not clinical, not overly casual
- Brief reasoning (2-3 sentences per domain): quick why behind each recommendation, scannable on a morning read
- Always cite specific numbers when they drive the recommendation — 'HRV 42ms (down from 48ms 7-day avg)' builds trust in the analysis
- Action-first overall summary: lead with what to do today, details in domain sections below

### Recommendation conservatism
- Borderline readiness: lean toward modified training rather than full rest — 'do the ride but cap at zone 2 and cut duration' assumes you want to train
- Safety flags only for alarming multi-metric convergence — sustained HRV crash + resting HR spike + sleep collapse over 3+ days. Don't cry wolf on single bad nights.
- Supplements: adjust within existing stack only — timing, dosing based on data. Never suggest new supplements. Safest approach for automated recommendations.
- Nutrition: mix of specific targets and principles — specific calorie/macro targets when training demands are clear, directional guidance on lighter days

### Degraded data handling
- Partial data: still generate all 5 domains with clear caveats on data-limited sections — never skip a domain entirely
- No-wear days: generate protocol from 7-day trends + health profile — something is better than nothing, clearly labeled as trend-based
- Parse failure: retry up to 3 times on invalid JSON, then fail gracefully and log raw response for debugging
- Store full DailyProtocol JSON in Supabase — enables protocol history, trend in recommendations, weekly summaries later. Minimal storage cost.

### Claude's Discretion
- Exact Anthropic SDK client setup and configuration
- Retry backoff strategy and timing
- JSON parsing and validation approach (Pydantic parse vs regex extraction)
- Error logging format (follow existing structlog conventions)
- Supabase table schema for protocol storage
- Temperature and other API parameters
- Whether to use streaming or non-streaming API calls

</decisions>

<specifics>
## Specific Ideas

- The DailyProtocol Pydantic model already exists in prompt/models.py with all 5 domain sub-models and reasoning fields — Phase 3 should validate Claude's response against this exact schema
- The prompt assembler (prompt/assembler.py) already produces XML-tagged prompts with analysis_directives and output_format sections — Phase 3 consumes the AssembledPrompt.text directly
- Token budget (~4K-6K tokens) was designed in Phase 2 — Phase 3 should log actual API token usage to calibrate the Phase 2 heuristic
- The pipeline.py currently only has run_ingestion() — Phase 3 adds a parallel run_analysis() function that reads from the same Supabase tables

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `DailyProtocol` model (prompt/models.py): complete output schema with 5 domain sub-models + reasoning fields — Claude's response validates against this
- `AssembledPrompt` model (prompt/models.py): carries prompt text + metadata — input to the analysis engine
- `PromptContext` model (prompt/models.py): bundles all data sources needed for prompt assembly
- `assemble_prompt()` function (prompt/assembler.py): produces the full XML-tagged prompt ready for Claude
- `Settings` class (config.py): pydantic-settings with .env loading — extend with ANTHROPIC_API_KEY and CLAUDE_MODEL
- `get_supabase_client()` (storage/supabase.py): existing Supabase client factory with tenacity retries
- structlog configured throughout — all new modules should use structlog.get_logger()

### Established Patterns
- Pydantic models for all data structures — DailyProtocol and sub-models follow this
- pydantic-settings with .env for configuration — new API settings follow same pattern
- tenacity for retry logic on external API calls (Supabase, Garmin) — reuse for Claude API
- `X | None` type syntax (modern Python, ruff UP045)
- Pipeline functions return Pydantic result models (IngestionResult pattern)

### Integration Points
- `assemble_prompt()` is the input: takes PromptContext, returns AssembledPrompt
- `DailyProtocol` is the output: Claude's JSON response validates against this model
- Settings: needs new fields (ANTHROPIC_API_KEY, CLAUDE_MODEL) in config.py
- Supabase: new table for protocol storage (daily_protocols or similar)
- Pipeline: new run_analysis() alongside existing run_ingestion()
- Trend computation (trends/compute.py): used by prompt assembly, feeds into analysis indirectly

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-analysis-engine*
*Context gathered: 2026-03-03*
