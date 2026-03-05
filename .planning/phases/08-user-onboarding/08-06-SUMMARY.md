---
phase: 08-user-onboarding
plan: 06
subsystem: pipeline
tags: [nudge-rate-limiting, supabase, whatsapp-nudges, onboarding]

# Dependency graph
requires:
  - phase: 08-05
    provides: "WhatsApp nudge rendering, get_incomplete_steps, pipeline nudge wiring"
provides:
  - "7-day rate-limited WhatsApp nudge delivery via should_send_nudge cooldown"
  - "Supabase-persisted last_nudge_sent_at timestamp for nudge frequency tracking"
  - "record_nudge_sent for post-delivery timestamp persistence"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns: [supabase-persisted-cooldown, safe-default-on-error, gte-epoch-universal-filter]

key-files:
  created: []
  modified:
    - src/biointelligence/delivery/whatsapp_renderer.py
    - src/biointelligence/pipeline.py
    - supabase/onboarding-ddl.sql
    - tests/test_whatsapp_renderer.py
    - tests/test_pipeline.py

key-decisions:
  - "7-day cooldown uses strict > comparison (exactly 7 days still within cooldown)"
  - "Safe default on any DB error: suppress nudge rather than risk spamming"
  - "record_nudge_sent uses .gte('created_at', '1970-01-01') as universal filter for single-row update"
  - "datetime imported at module level (stdlib, no need for lazy import) for easier test mocking"

patterns-established:
  - "Supabase-persisted cooldown: query timestamp, compare elapsed, update after action"
  - "Safe default pattern: return False on exception to suppress unwanted behavior"

requirements-completed: [ONBD-02]

# Metrics
duration: 5min
completed: 2026-03-05
---

# Phase 8 Plan 6: WhatsApp Nudge Rate Limiting Summary

**7-day cooldown for WhatsApp profile nudges using Supabase-persisted last_nudge_sent_at timestamp with safe-default error handling**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-05T20:48:47Z
- **Completed:** 2026-03-05T20:54:02Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Added should_send_nudge() with 7-day cooldown check against Supabase last_nudge_sent_at
- Added record_nudge_sent() for best-effort timestamp persistence after nudge delivery
- Wired rate-limited nudge logic into pipeline run_delivery with cooldown gating
- DDL updated with last_nudge_sent_at column on onboarding_profiles
- 14 new tests (8 rate-limiting + 6 pipeline cooldown), all 433 tests pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Add nudge rate-limiting functions and DDL update (TDD)**
   - `a11b0d7` (test) - Failing tests for should_send_nudge and record_nudge_sent
   - `850a0d5` (feat) - should_send_nudge, record_nudge_sent, DDL column
2. **Task 2: Wire rate-limited nudges into pipeline run_delivery (TDD)**
   - `e50d799` (test) - Failing tests for pipeline nudge cooldown
   - `dfe3220` (feat) - Pipeline wiring, existing test updates

## Files Created/Modified
- `src/biointelligence/delivery/whatsapp_renderer.py` - Added NUDGE_COOLDOWN_DAYS, should_send_nudge(), record_nudge_sent() functions
- `src/biointelligence/pipeline.py` - run_delivery gates get_incomplete_steps behind should_send_nudge, calls record_nudge_sent after WhatsApp success
- `supabase/onboarding-ddl.sql` - ALTER TABLE adds last_nudge_sent_at TIMESTAMPTZ column
- `tests/test_whatsapp_renderer.py` - 8 new tests in TestNudgeRateLimiting class
- `tests/test_pipeline.py` - 6 new tests in TestRunDeliveryNudgeCooldown, 2 existing tests updated with should_send_nudge mock

## Decisions Made
- 7-day cooldown uses strict `>` comparison so exactly 7 days is still within cooldown (sends at 7 days + 1 second)
- Safe default: should_send_nudge returns False on any DB error to prevent spamming
- record_nudge_sent uses `.gte("created_at", "1970-01-01")` as universal filter for the single-row update (established pattern in codebase)
- Moved datetime/timezone imports to module level (stdlib, no lazy import needed) for deterministic test mocking of boundary cases

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test mocking for lazy imports**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** Tests patched `biointelligence.delivery.whatsapp_renderer.get_supabase_client` but function uses lazy import from `biointelligence.storage.supabase`
- **Fix:** Changed patch target to `biointelligence.storage.supabase.get_supabase_client`
- **Files modified:** tests/test_whatsapp_renderer.py
- **Committed in:** 850a0d5

**2. [Rule 1 - Bug] Fixed boundary test timing non-determinism**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** Boundary tests for exactly 7 days failed due to microsecond drift between timestamp creation and evaluation
- **Fix:** Used FrozenDatetime subclass to freeze time, moved datetime imports to module level for patchability
- **Files modified:** src/biointelligence/delivery/whatsapp_renderer.py, tests/test_whatsapp_renderer.py
- **Committed in:** 850a0d5

---

**Total deviations:** 2 auto-fixed (2 bugs in test setup)
**Impact on plan:** Both fixes were necessary for test correctness. No scope creep.

## Issues Encountered
None beyond the auto-fixed test issues above.

## User Setup Required
**Database migration required.** Run the ALTER TABLE statement from `supabase/onboarding-ddl.sql` on the production Supabase instance:
```sql
ALTER TABLE onboarding_profiles
  ADD COLUMN IF NOT EXISTS last_nudge_sent_at TIMESTAMPTZ DEFAULT NULL;
```

## Next Phase Readiness
- ONBD-02 "max once per week" nudge requirement fully satisfied
- Gap closure complete -- all verification gaps from 08-05 addressed
- Phase 8 fully complete (6/6 plans executed)

## Self-Check: PASSED

All 5 modified files verified present. All 4 task commits verified in git log.

---
*Phase: 08-user-onboarding*
*Completed: 2026-03-05*
