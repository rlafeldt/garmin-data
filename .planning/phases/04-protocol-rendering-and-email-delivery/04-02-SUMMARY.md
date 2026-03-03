---
phase: 04-protocol-rendering-and-email-delivery
plan: 02
subsystem: delivery
tags: [resend, email-sender, tenacity-retry, pipeline-orchestration, cli]

# Dependency graph
requires:
  - phase: 04-protocol-rendering-and-email-delivery
    plan: 01
    provides: render_html, render_text, build_subject renderers; Settings with Resend config fields; delivery/ package scaffold
  - phase: 03-analysis-engine
    provides: AnalysisResult model with DailyProtocol
provides:
  - send_email() wrapping Resend SDK with tenacity retry and DeliveryResult model
  - run_delivery() pipeline function orchestrating render + send
  - CLI --deliver flag triggering delivery after analysis
affects: [05-pipeline-automation]

# Tech tracking
tech-stack:
  added: [resend 2.23.0]
  patterns: [per-call API key setting for test isolation, RetryError unwrapping for user-facing error messages, --deliver implies --analyze flag chaining]

key-files:
  created:
    - src/biointelligence/delivery/sender.py
    - tests/test_sender.py
  modified:
    - src/biointelligence/pipeline.py
    - src/biointelligence/main.py
    - tests/test_pipeline.py
    - pyproject.toml

key-decisions:
  - "resend.api_key set per-call inside send_email (not at module level) for test isolation per RESEARCH.md pitfall 3"
  - "RetryError unwrapping extracts last_attempt exception for user-facing error messages"
  - "--deliver implies --analyze via flag chaining (args.deliver sets args.analyze = True)"
  - "run_delivery guards both success=False and protocol=None before calling renderers"

patterns-established:
  - "Per-call API key pattern: set resend.api_key inside function, not at import time"
  - "Tenacity wait patching in tests: override retry.wait for instant test execution"
  - "Flag chaining: higher-level flags auto-enable prerequisites (--deliver implies --analyze)"

requirements-completed: [PROT-03]

# Metrics
duration: 4min
completed: 2026-03-03
---

# Phase 4 Plan 02: Email Sending and Delivery Pipeline Summary

**Resend email sender with tenacity retry, run_delivery pipeline orchestrator, and CLI --deliver flag with 17 new tests**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-03T21:39:15Z
- **Completed:** 2026-03-03T21:43:56Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- send_email wraps Resend SDK with tenacity retry (3 attempts, exponential backoff), sets API key per-call for test isolation
- DeliveryResult Pydantic model follows IngestionResult/AnalysisResult pattern with date, email_id, success, error
- RetryError handling extracts underlying exception message for meaningful error reporting
- run_delivery orchestrates full render_html + render_text + build_subject + send_email flow with guard against failed analysis
- CLI --deliver flag works, auto-enables --analyze, prints email_id on success, returns exit 1 on failure
- 17 new tests (9 sender + 8 pipeline) bringing total suite to 202 tests, all passing

## Task Commits

Each task was committed atomically:

1. **Task 1: Resend sender with retry and DeliveryResult model** - `9874ef9` (feat)
2. **Task 2: Pipeline run_delivery function and CLI --deliver flag** - `8e1c729` (feat)

## Files Created/Modified
- `src/biointelligence/delivery/sender.py` - Resend email sender with tenacity retry and DeliveryResult model
- `tests/test_sender.py` - 9 unit tests for DeliveryResult, send_email, retry behavior
- `src/biointelligence/pipeline.py` - Extended with run_delivery orchestrator function
- `src/biointelligence/main.py` - Extended with --deliver CLI flag and delivery flow
- `tests/test_pipeline.py` - Extended with 8 tests for run_delivery and CLI --deliver
- `pyproject.toml` - Added resend 2.23.0 dependency

## Decisions Made
- Set resend.api_key per-call inside send_email function (not at module level) for test isolation, following RESEARCH.md pitfall 3 guidance
- RetryError unwrapping via last_attempt.exception() provides user-facing error messages instead of opaque tenacity wrapper text
- --deliver flag auto-enables --analyze via `if args.deliver: args.analyze = True` (delivery requires a protocol from analysis)
- run_delivery guards both `not analysis_result.success` and `analysis_result.protocol is None` to avoid AttributeError on None protocol

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] RetryError wrapping obscured error messages**
- **Found during:** Task 1 (send_email implementation)
- **Issue:** When all retries exhaust, tenacity raises RetryError which wraps the original exception. The error message shown to users was "RetryError[<Future...>]" instead of the actual API error
- **Fix:** Added explicit `except RetryError` handler that extracts `e.last_attempt.exception()` for the underlying error message
- **Files modified:** src/biointelligence/delivery/sender.py
- **Verification:** test_returns_failure_on_api_error passes with "API connection failed" in error
- **Committed in:** 9874ef9 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Essential for error reporting correctness. No scope creep.

## Issues Encountered

None.

## User Setup Required

The following external service configuration is required before using --deliver:

**Resend (transactional email):**
1. Create account at resend.com
2. Add and verify sending domain (Dashboard -> Domains -> Add Domain -> add DKIM/SPF DNS records)
3. Create API key (Dashboard -> API Keys -> Create API Key)
4. Set environment variables:
   - `RESEND_API_KEY` - from Resend Dashboard
   - `SENDER_EMAIL` - verified domain email (e.g., protocol@yourdomain.com)
   - `RECIPIENT_EMAIL` - personal email for receiving protocols

## Next Phase Readiness
- Full delivery chain complete: render -> send -> CLI integration
- Phase 4 fully complete (2/2 plans done)
- Ready for Phase 5 Pipeline Automation (scheduling, GitHub Actions, failure notifications)
- 202 total tests passing, no regressions

---
*Phase: 04-protocol-rendering-and-email-delivery*
*Completed: 2026-03-03*
