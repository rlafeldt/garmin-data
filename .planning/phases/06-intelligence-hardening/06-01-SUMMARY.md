---
phase: 06-intelligence-hardening
plan: 01
subsystem: analysis
tags: [anomaly-detection, z-scores, convergence-patterns, statistics, pydantic, trends]

# Dependency graph
requires:
  - phase: 03-analysis-engine
    provides: TrendResult, MetricTrend, compute_trends, TRENDED_METRICS models
provides:
  - "MetricTrend with stddev field for 28-day baseline computation"
  - "compute_extended_trends() function for 28-day trend windows"
  - "TREND_FIELDS expanded with 4 additional convergence pattern columns"
  - "anomaly/ package with models, 5 convergence patterns, and detect_anomalies orchestrator"
  - "Z-score-based personal baseline anomaly detection"
  - "Single-metric extreme outlier detection at 2.5/3.0 SD thresholds"
  - "Multi-metric convergence detection over 3+ consecutive days"
affects: [06-02, prompt, analysis-engine, delivery-renderer]

# Tech tracking
tech-stack:
  added: [statistics.stdev]
  patterns: [z-score-based-anomaly-detection, convergence-pattern-definitions, derived-metrics]

key-files:
  created:
    - src/biointelligence/anomaly/__init__.py
    - src/biointelligence/anomaly/models.py
    - src/biointelligence/anomaly/patterns.py
    - src/biointelligence/anomaly/detector.py
    - tests/test_anomaly.py
  modified:
    - src/biointelligence/trends/models.py
    - src/biointelligence/trends/compute.py
    - src/biointelligence/trends/__init__.py
    - tests/test_trends.py

key-decisions:
  - "2.5 SD for WARNING and 3.0 SD for CRITICAL single-metric outlier thresholds"
  - "1.0 SD per metric within convergence patterns (lower bar since convergence IS the signal)"
  - "body_battery_drain derived as (body_battery_max - body_battery_min) for stress escalation pattern"
  - "Combined stddev for drain uses sqrt(max_stddev^2 + min_stddev^2) approximation"
  - "statistics.stdev (sample) not pstdev (population) for 28-day rolling window"

patterns-established:
  - "Z-score personal baselines: compute_z_score(current, mean, stddev) with stddev=0 guard"
  - "Convergence pattern definitions: ConvergencePattern model with MetricCheck list"
  - "Consecutive day checks: last N rows all must deviate, None breaks streak"
  - "Derived metrics: special-case handling in detector for computed values (body_battery_drain)"

requirements-completed: [TRND-02, TRND-03]

# Metrics
duration: 8min
completed: 2026-03-04
---

# Phase 6 Plan 1: Extended Trends and Anomaly Detection Summary

**28-day extended trend computation with stddev baselines and server-side anomaly detection using z-scores, 5 convergence patterns, and single-metric extreme outlier detection**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-04T16:30:34Z
- **Completed:** 2026-03-04T16:38:52Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments
- Extended MetricTrend with stddev field and created compute_extended_trends() for 28-day baseline computation with configurable minimum data points (14)
- Built complete anomaly detection module: AlertSeverity/Alert/AnomalyResult models, 5 hardcoded convergence patterns, and detect_anomalies orchestrator
- Z-score computation against personal baselines with graceful edge case handling (stddev=0, None values, insufficient data)
- 71 new+updated tests covering all behaviors: z-scores, outliers, convergence, consecutive day checks, model serialization

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend MetricTrend with stddev and add compute_extended_trends**
   - `30ce125` (test: add failing tests for extended trends with stddev)
   - `f09f1eb` (feat: extend MetricTrend with stddev and add compute_extended_trends)
2. **Task 2: Create anomaly detection module with models, patterns, and detector**
   - `9ec2bf9` (test: add failing tests for anomaly detection module)
   - `192816b` (feat: create anomaly detection module with models, patterns, and detector)

_Note: TDD tasks have test commit (RED) followed by implementation commit (GREEN)._

## Files Created/Modified
- `src/biointelligence/trends/models.py` - Added stddev field to MetricTrend, expanded TRENDED_METRICS with 4 new convergence metrics
- `src/biointelligence/trends/compute.py` - Added compute_extended_trends(), expanded TREND_FIELDS with 4 new columns, imported stdev
- `src/biointelligence/trends/__init__.py` - Exported compute_extended_trends
- `src/biointelligence/anomaly/__init__.py` - Lazy imports for detect_anomalies, AnomalyResult, Alert, AlertSeverity
- `src/biointelligence/anomaly/models.py` - AlertSeverity, Alert, MetricCheck, ConvergencePattern, AnomalyResult Pydantic models
- `src/biointelligence/anomaly/patterns.py` - 5 hardcoded convergence patterns with metric checks and suggested actions
- `src/biointelligence/anomaly/detector.py` - compute_z_score, consecutive day checks, outlier alerts, convergence checks, detect_anomalies orchestrator
- `tests/test_trends.py` - 24 new tests for extended trends, stddev, TREND_FIELDS expansion
- `tests/test_anomaly.py` - 27 tests for z-scores, outliers, convergence, models, exports

## Decisions Made
- Used 2.5 SD for WARNING and 3.0 SD for CRITICAL single-metric outlier thresholds (conservative, only fires on genuine statistical outliers per SWC research)
- Used 1.0 SD per metric within convergence patterns (lower bar since multi-metric convergence over 3+ days is itself the signal)
- Derived body_battery_drain as (body_battery_max - body_battery_min) for stress escalation pattern, with combined stddev approximation
- Used statistics.stdev (sample) over pstdev (population) since 28-day window is a sample of ongoing biometric trajectory
- rest_stress_minutes set as lower_is_better=False (higher = more relaxation = better)
- Lazy imports in anomaly/__init__.py via __getattr__ pattern (matching analysis/, delivery/, prompt/ modules)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated existing test for expanded TRENDED_METRICS**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** Existing test `test_compute_trends_includes_all_seven_metrics` hardcoded expected 7 metric names, but TRENDED_METRICS now has 11
- **Fix:** Updated test to dynamically check against `set(TRENDED_METRICS.keys())` instead of hardcoded set
- **Files modified:** tests/test_trends.py
- **Verification:** All 252 existing tests still pass
- **Committed in:** f09f1eb (Task 1 GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Necessary adaptation of existing test to new metric count. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Extended trends and anomaly detection module ready for integration into analysis pipeline (Plan 06-02)
- detect_anomalies() accepts DailyMetrics + TrendResult + trend_rows, returns AnomalyResult with Alert list
- Convergence patterns reference all metrics now available in TREND_FIELDS
- All 279 tests pass with zero regressions

## Self-Check: PASSED

All 9 files verified present. All 4 commits verified in git log.

---
*Phase: 06-intelligence-hardening*
*Completed: 2026-03-04*
