# Phase 6: Intelligence Hardening - Research

**Researched:** 2026-03-04
**Domain:** Longitudinal anomaly detection, multi-metric convergence alerting, extended trend computation
**Confidence:** HIGH

## Summary

Phase 6 extends the existing 7-day trend computation to 28-day windows and adds a deterministic, server-side anomaly detection layer that feeds detected patterns into the Claude analysis prompt. The existing codebase already has `fetch_trend_window()` with a `window_days` parameter and `compute_trends()` with split-half direction analysis -- these are directly reusable. The new work is: (1) extending MetricTrend with stddev for baseline computation, (2) building an anomaly detection module with z-score-based personal baselines and 5 hardcoded convergence patterns, (3) extending the prompt with `<trends_28d>` and `<anomalies>` sections, (4) adding an `alerts` field to DailyProtocol for structured alert output, and (5) rendering alert banners at the top of the email.

The statistical approach uses Python's `statistics` stdlib module (stdev/mean) for all computations -- no external dependencies needed. Z-scores are computed as `(value - mean) / stdev` where mean and stdev come from the 28-day rolling window. The sports science literature supports this approach: the "Smallest Worthwhile Change" (SWC) method uses mean +/- 0.5-1.0 SD as the threshold for meaningful deviation, with 30-day rolling averages as the reference baseline. This aligns perfectly with the 28-day window decision.

The implementation requires no new dependencies. All computation uses Python stdlib (`statistics.mean`, `statistics.stdev`), existing Pydantic models (extend, don't replace), and the established patterns (structlog, tenacity, Supabase queries). The main architectural decision is where the anomaly detection module lives -- a new `anomaly/` subpackage paralleling the existing `trends/` module is the cleanest approach.

**Primary recommendation:** Create an `anomaly/` module with models, detector, and patterns submodules. Extend MetricTrend with stddev. Add `compute_extended_trends()` that calls `fetch_trend_window(client, target_date, window_days=28)`. Wire anomaly detection into `analyze_daily()` between trend computation and prompt assembly.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions

**Alert presentation:**
- Top banner at the very top of the email, before the overall summary -- alerts are the first thing seen
- Two severity levels: Warning (yellow #eab308) and Critical (red #ef4444) -- matches existing traffic light color scheme
- No banner when nothing is flagged -- most days should be alert-free, clean email
- Each alert includes both detection description AND suggested action -- consistent with the protocol's action-first philosophy

**Alert sensitivity:**
- Personal baselines defined as rolling 28-day mean + standard deviation -- adapts as fitness changes over time
- Multi-metric convergence over 3+ consecutive days triggers standard alerts -- consistent with Phase 3's "don't cry wolf on single bad nights"
- Single-metric extreme outliers also get flagged as standalone alerts -- catches acute events even without multi-metric convergence
- Anomaly detection happens server-side in Python, deterministically -- feed detected anomalies into Claude prompt

**28-day trend visibility:**
- 28-day trends feed Claude silently -- do NOT show in email unless anomalous
- 7-day trends also stay hidden from email (current behavior preserved)
- Summary stats only in prompt: 28-day mean, stddev, direction, and any detected anomalies -- no raw daily values
- Minimum 14 of 28 days of data required for 28-day trend computation

**Metric convergence patterns (5 hardcoded):**
1. HRV + HR + Sleep: HRV decline + elevated resting HR + poor sleep efficiency
2. Overtraining signals: Training load rising + HRV declining + Body Battery not recovering
3. Sleep debt accumulation: Sleep score declining + total sleep dropping + deep sleep shrinking
4. Stress escalation: Avg stress rising + relaxation time dropping + Body Battery drain accelerating
5. Recovery stall: Body Battery morning charge plateauing low + resting HR creeping up + HRV flat/declining

**Additional locked decisions:**
- No alert history tracking -- stateless, each day's analysis is independent
- Server-side anomaly detection feeds INTO the prompt -- Claude interprets and recommends, Python detects

### Claude's Discretion
- Exact statistical threshold for single-metric extreme outliers (implementation decides appropriate stddev cutoff)
- Specific stddev thresholds for multi-metric convergence pattern detection
- Enhanced trend statistics beyond avg/min/max (stddev, percentiles, z-scores -- whatever anomaly detection needs)
- Token budget adjustments to accommodate 28-day trend data alongside existing sections
- Anomaly detection module architecture and code organization
- DailyProtocol schema extension for alert fields (top-level alerts list, Alert sub-model structure)
- Prompt template updates for anomaly detection directives
- SQL query design for 28-day window fetching

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TRND-02 | System computes 28-day extended trend windows for deeper pattern detection (HRV trajectory, resting HR creep, sleep debt accumulation) | Extended trend computation reuses existing `fetch_trend_window(client, target_date, window_days=28)` and `compute_direction()`. MetricTrend extended with `stddev` field. New `compute_extended_trends()` function. Summary stats (mean, stddev, direction) fed into prompt via `<trends_28d>` section. |
| TRND-03 | System detects multi-metric anomaly convergence (e.g., simultaneous HRV decline + elevated resting HR + poor sleep efficiency) and generates proactive alerts | New `anomaly/` module with z-score-based personal baselines from 28-day window. 5 hardcoded convergence patterns checking 3+ consecutive days. Single-metric extreme outlier detection. Detected anomalies fed into prompt `<anomalies>` section. Alert model added to DailyProtocol. Alert banners rendered at top of email. |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| statistics (stdlib) | Python 3.12 | mean, stdev, pstdev computation | Zero dependencies, sufficient for z-score/SWC computation |
| pydantic | existing | Alert, AnomalyResult, ExtendedMetricTrend models | Project standard for all data models |
| structlog | existing | Logging anomaly detection events | Project standard for structured logging |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| tenacity | existing | Retry on 28-day Supabase fetch | Already wraps `fetch_trend_window()` |
| supabase | existing | 28-day data window queries | Existing query pattern reused |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| statistics.stdev | numpy/scipy | Overkill for simple z-scores; adds heavy dependency for 2 function calls |
| Hardcoded patterns | ML anomaly detection (Isolation Forest, etc.) | Far too complex for 5 known patterns; requires training data; non-deterministic |
| Python-side z-scores | Supabase SQL window functions | Keeps logic testable in Python; SQL would be harder to unit test and maintain |

**Installation:**
No new dependencies required. All computation uses Python stdlib `statistics` module.

## Architecture Patterns

### Recommended Project Structure

```
src/biointelligence/
├── anomaly/              # NEW: anomaly detection module
│   ├── __init__.py       # Lazy imports (matching analysis/ pattern)
│   ├── models.py         # Alert, AnomalyResult, ConvergencePattern models
│   ├── detector.py       # detect_anomalies() orchestrator
│   └── patterns.py       # 5 hardcoded convergence pattern definitions
├── trends/
│   ├── models.py         # EXTEND: MetricTrend + stddev field
│   └── compute.py        # EXTEND: compute_extended_trends() function
├── prompt/
│   ├── models.py         # EXTEND: PromptContext + DailyProtocol
│   ├── assembler.py      # EXTEND: new sections, budget priority
│   ├── budget.py         # EXTEND: section priority list
│   └── templates.py      # EXTEND: anomaly interpretation directives
├── analysis/
│   └── engine.py         # EXTEND: wire anomaly detection into pipeline
└── delivery/
    └── renderer.py       # EXTEND: alert banner rendering
```

### Pattern 1: Extended Trend Computation

**What:** Reuse existing `fetch_trend_window()` with `window_days=28` and extend `MetricTrend` with `stddev` for baseline computation.

**When to use:** Computing 28-day baselines for anomaly detection.

**Example:**
```python
# In trends/models.py - extend MetricTrend
class MetricTrend(BaseModel):
    """Trend statistics for a single metric."""
    avg: float | None = None
    min_val: float | None = None
    max_val: float | None = None
    stddev: float | None = None  # NEW: for anomaly baselines
    direction: TrendDirection = TrendDirection.INSUFFICIENT

# In trends/compute.py - new function
def compute_extended_trends(
    client: Client, target_date: date, window_days: int = 28, min_data_points: int = 14
) -> TrendResult:
    """Compute extended trend window with stddev for anomaly baselines.

    Requires min_data_points (default 14) of valid data in the window.
    Uses the same fetch_trend_window() and compute_direction() as 7-day trends.
    """
    rows = fetch_trend_window(client, target_date, window_days=window_days)
    # ... compute avg, min, max, stddev, direction per metric
    # ... mark as INSUFFICIENT if < min_data_points valid values
```

### Pattern 2: Z-Score-Based Anomaly Detection

**What:** Compute z-scores against 28-day personal baselines to detect deviations.

**When to use:** Both single-metric extreme outlier detection and multi-metric convergence.

**Example:**
```python
from statistics import mean, stdev

def compute_z_score(current_value: float, baseline_mean: float, baseline_stddev: float) -> float:
    """Compute z-score for a single metric against its personal baseline.

    Returns 0.0 if stddev is 0 (all values identical).
    """
    if baseline_stddev == 0:
        return 0.0
    return (current_value - baseline_mean) / baseline_stddev
```

### Pattern 3: Convergence Pattern Detection

**What:** Hardcoded pattern definitions that check if multiple metrics simultaneously deviate from baselines over 3+ consecutive days.

**When to use:** The 5 locked convergence patterns from CONTEXT.md.

**Example:**
```python
class ConvergencePattern(BaseModel):
    """Definition of a multi-metric convergence pattern."""
    name: str
    description: str
    metrics: list[MetricCheck]  # Which metrics to check
    min_consecutive_days: int = 3
    severity: AlertSeverity  # WARNING or CRITICAL

class MetricCheck(BaseModel):
    """Single metric check within a convergence pattern."""
    metric_name: str           # e.g., "hrv_overnight_avg"
    direction: str             # "below" or "above" baseline
    threshold_stddev: float    # How many stddev from mean triggers
```

### Pattern 4: Stateless Daily Detection

**What:** Each day's anomaly detection is independent -- no alert history tracking. The 28-day window inherently captures persistence.

**When to use:** Always. The system detects anomalies fresh each run.

**Key insight:** "3+ consecutive days" detection uses the 28-day data window directly. Check the last 3 days of the window to see if all 3 are anomalous. No need for separate alert history storage.

**Example:**
```python
def _check_consecutive_days(
    rows: list[dict], metric_name: str, baseline_mean: float, baseline_stddev: float,
    direction: str, threshold: float, min_days: int = 3,
) -> bool:
    """Check if the last min_days all deviate from baseline in the given direction."""
    recent = rows[-min_days:]  # Last 3 days from the 28-day window
    if len(recent) < min_days:
        return False
    for row in recent:
        value = row.get(metric_name)
        if value is None:
            return False
        z = compute_z_score(value, baseline_mean, baseline_stddev)
        if direction == "below" and z > -threshold:
            return False
        if direction == "above" and z < threshold:
            return False
    return True
```

### Pattern 5: Alert Banner in Email

**What:** Alert banners rendered at the very top of the email, before the readiness dashboard. Warning uses yellow (#eab308), Critical uses red (#ef4444).

**When to use:** When DailyProtocol has non-empty `alerts` list.

**Example:**
```python
# In delivery/renderer.py
_ALERT_WARNING_BG = "#fef9c3"   # Light yellow background
_ALERT_WARNING_BORDER = "#eab308"  # Yellow border
_ALERT_CRITICAL_BG = "#fef2f2"  # Light red background
_ALERT_CRITICAL_BORDER = "#ef4444"  # Red border

def _render_alert_banners(alerts: list[Alert]) -> str:
    """Render alert banners at top of email. Returns empty string if no alerts."""
    if not alerts:
        return ""
    # Each alert: colored banner with severity icon, description, suggested action
```

### Anti-Patterns to Avoid
- **Fetching 28 days of raw data per-metric separately:** Use a single `fetch_trend_window(client, target_date, window_days=28)` call. The existing function already returns all TREND_FIELDS in one query.
- **Using population stddev (pstdev) instead of sample stddev:** With 14-28 data points, use `statistics.stdev()` (sample) not `statistics.pstdev()` (population). Sample stddev is more appropriate for rolling windows where the data is a sample of the individual's ongoing biometric trajectory.
- **Making anomaly detection probabilistic or ML-based:** The decision is deterministic Python-side detection. Keep it simple: z-scores against personal baselines.
- **Storing alert history for consecutive-day tracking:** The 28-day window already contains the last 3+ days. Check consecutive days within the window data, no separate storage needed.
- **Putting anomaly logic inside the prompt template:** Detection is Python-side, deterministic. Only the results (detected anomalies) go into the prompt for Claude to interpret.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Standard deviation | Manual sum-of-squares | `statistics.stdev()` | Handles edge cases (single value, empty), numerically stable |
| Mean computation | Manual sum/len | `statistics.mean()` | Already used in trends/compute.py |
| Supabase 28-day fetch | New query function | `fetch_trend_window(client, target_date, window_days=28)` | Already accepts window_days parameter with retry |
| Direction analysis | New algorithm | `compute_direction()` | Already handles lower_is_better, thresholds, min_data_points |
| HTML escaping | Manual string cleaning | `html.escape()` via existing `_e()` helper | Already established in renderer.py |

**Key insight:** The existing trends module was designed to be reusable. `fetch_trend_window()` accepts `window_days`, `compute_direction()` is generic. The 28-day extension is mostly parameterization, not new logic.

## Common Pitfalls

### Pitfall 1: Insufficient Data Handling for 28-Day Window
**What goes wrong:** Early in production (or after data gaps), fewer than 14 days of data exist. Attempting stddev on 0-1 values raises `StatisticsError`.
**Why it happens:** `statistics.stdev()` requires at least 2 data points; `statistics.mean()` requires at least 1.
**How to avoid:** Check `len(values) >= min_data_points` (14) before computing stats. Return `TrendDirection.INSUFFICIENT` and skip anomaly detection for that metric. The existing pattern in `compute_direction()` already does this check.
**Warning signs:** `StatisticsError: stdev requires at least two data points` in logs.

### Pitfall 2: Division by Zero in Z-Score
**What goes wrong:** If all 28 days have the same value (stddev = 0), z-score computation divides by zero.
**Why it happens:** Perfectly stable metrics (e.g., body_battery_morning always 75) yield stddev = 0.
**How to avoid:** Guard z-score computation: `if stddev == 0: return 0.0`. A z-score of 0 means "no deviation from mean," which is correct when there's no variance.
**Warning signs:** `ZeroDivisionError` in anomaly detection logs.

### Pitfall 3: Token Budget Overflow
**What goes wrong:** Adding `<trends_28d>` and `<anomalies>` sections pushes the prompt over the 6000-token budget, causing section trimming.
**Why it happens:** 28-day summary stats for 7 metrics + anomaly descriptions can add 200-400 tokens.
**How to avoid:** Keep 28-day trend format compact (same format as 7-day but with stddev added). Add `trends_28d` and `anomalies` to SECTION_PRIORITY at appropriate levels. `anomalies` should be high priority (above analysis_directives); `trends_28d` should be medium (similar to trends_7d). Consider bumping DEFAULT_TOKEN_BUDGET from 6000 to 7000.
**Warning signs:** `trimming_section` log entries for important sections.

### Pitfall 4: TREND_FIELDS Missing Needed Columns
**What goes wrong:** The convergence patterns need metrics not currently in `TREND_FIELDS` (e.g., `deep_sleep_seconds`, `rest_stress_minutes`, `body_battery_max`, `body_battery_min`).
**Why it happens:** Current `TREND_FIELDS` was designed for 7-day trends with 7 metrics. Convergence patterns reference additional metrics.
**How to avoid:** Extend `TREND_FIELDS` to include all metrics referenced by convergence patterns. Map convergence pattern metric references to actual column names in `daily_metrics`.
**Warning signs:** `KeyError` when accessing metrics in convergence pattern checks.

### Pitfall 5: Consecutive Day Check with Missing Data
**What goes wrong:** Checking "3 consecutive days" but some days have None values for a metric (e.g., no sleep data on a travel day).
**Why it happens:** The 28-day window already filters `is_no_wear=False`, but individual metrics can still be None.
**How to avoid:** In consecutive-day checks, treat None as "not anomalous" (i.e., break the consecutive streak). This is conservative -- only alert when we have evidence, not when data is missing.
**Warning signs:** False positive alerts on days with partial data.

### Pitfall 6: Convergence Pattern Metric Mapping
**What goes wrong:** CONTEXT.md uses human-readable names ("relaxation time dropping") that don't map directly to database column names.
**Why it happens:** The 5 patterns use domain language, not schema language.
**How to avoid:** Create an explicit mapping table. For example:
- "relaxation time" -> `rest_stress_minutes` (higher = more relaxation)
- "Body Battery drain accelerating" -> computed from `body_battery_max - body_battery_min` delta
- "deep sleep shrinking" -> `deep_sleep_seconds`
- "Body Battery morning charge" -> `body_battery_morning`
- "Body Battery not recovering" -> `body_battery_morning` staying low
**Warning signs:** Patterns that never fire because they check the wrong column.

## Code Examples

### Example 1: Extended MetricTrend with stddev
```python
# Source: Existing trends/models.py pattern + statistics stdlib
from statistics import mean, stdev

class MetricTrend(BaseModel):
    """Trend statistics for a single metric."""
    avg: float | None = None
    min_val: float | None = None
    max_val: float | None = None
    stddev: float | None = None  # NEW
    direction: TrendDirection = TrendDirection.INSUFFICIENT

# In compute function:
values = [row[metric_name] for row in rows if row.get(metric_name) is not None]
if len(values) >= min_data_points:
    metric_stddev = stdev(values) if len(values) >= 2 else 0.0
    metrics[metric_name] = MetricTrend(
        avg=mean(values),
        min_val=min(values),
        max_val=max(values),
        stddev=metric_stddev,
        direction=compute_direction(values, lower_is_better=config["lower_is_better"]),
    )
```

### Example 2: Alert Pydantic Models
```python
# Source: Existing DailyProtocol pattern in prompt/models.py
from enum import StrEnum

class AlertSeverity(StrEnum):
    WARNING = "warning"
    CRITICAL = "critical"

class Alert(BaseModel):
    """A proactive alert for the Daily Protocol."""
    severity: AlertSeverity
    title: str  # e.g., "HRV + Resting HR + Sleep Convergence"
    description: str  # What was detected
    suggested_action: str  # What to do about it
    pattern_name: str  # Which convergence pattern triggered this

class DailyProtocol(BaseModel):
    # ... existing fields ...
    alerts: list[Alert] = Field(default_factory=list)
```

### Example 3: Anomaly Detection Orchestrator
```python
# Source: Existing analyze_daily() orchestration pattern in analysis/engine.py
def detect_anomalies(
    today_metrics: DailyMetrics,
    trends_28d: TrendResult,
    trend_rows: list[dict],  # Raw 28-day window rows for consecutive-day checks
) -> AnomalyResult:
    """Run all anomaly detection checks against 28-day baselines.

    Returns AnomalyResult with detected single-metric outliers and
    convergence pattern alerts.
    """
    alerts: list[Alert] = []

    # 1. Single-metric extreme outlier checks
    for metric_name, trend in trends_28d.metrics.items():
        if trend.avg is None or trend.stddev is None or trend.stddev == 0:
            continue
        current = getattr(today_metrics, metric_name, None)
        if current is None:
            continue
        z = (current - trend.avg) / trend.stddev
        if abs(z) > EXTREME_OUTLIER_THRESHOLD:
            alerts.append(_make_outlier_alert(metric_name, current, z, trend))

    # 2. Convergence pattern checks
    for pattern in CONVERGENCE_PATTERNS:
        if _check_pattern(pattern, trends_28d, trend_rows):
            alerts.append(_make_convergence_alert(pattern))

    return AnomalyResult(alerts=alerts, metrics_checked=len(trends_28d.metrics))
```

### Example 4: Prompt Section for Anomalies
```python
# Source: Existing _format_trends() pattern in prompt/assembler.py
def _format_anomalies(anomaly_result: AnomalyResult) -> str:
    """Format detected anomalies for the prompt."""
    if not anomaly_result.alerts:
        return "No anomalies detected. All metrics within normal personal baselines."

    lines = [f"DETECTED ANOMALIES ({len(anomaly_result.alerts)} alerts):"]
    for alert in anomaly_result.alerts:
        lines.append(f"- [{alert.severity.upper()}] {alert.title}: {alert.description}")
    lines.append("")
    lines.append(
        "Interpret these anomalies in context. Provide actionable recommendations "
        "in the alerts field of your response. Focus on what the user should DO today."
    )
    return "\n".join(lines)
```

### Example 5: Alert Banner HTML Rendering
```python
# Source: Existing _render_data_quality_banner() pattern in delivery/renderer.py
def _render_alert_banners(alerts: list[Alert]) -> str:
    """Render alert banners at the very top of email."""
    if not alerts:
        return ""

    parts = []
    for alert in alerts:
        if alert.severity == AlertSeverity.CRITICAL:
            bg, border = _ALERT_CRITICAL_BG, _ALERT_CRITICAL_BORDER
        else:
            bg, border = _ALERT_WARNING_BG, _ALERT_WARNING_BORDER

        parts.append(f"""\
<tr>
  <td style="padding: 12px 24px 0 24px;">
    <table role="presentation" cellpadding="0" cellspacing="0" width="100%"
      style="background-color: {bg}; border-left: 4px solid {border}; border-radius: 6px;">
      <tr>
        <td style="padding: 12px 16px;">
          <p style="margin: 0 0 4px 0; font-size: 14px; font-weight: 600;
            color: {border}; font-family: {_FONT_STACK};">
            {_e(alert.title)}</p>
          <p style="margin: 0 0 4px 0; font-size: 13px; line-height: 1.5;
            color: {_TEXT_COLOR}; font-family: {_FONT_STACK};">
            {_e(alert.description)}</p>
          <p style="margin: 0; font-size: 13px; font-weight: 500;
            color: {_TEXT_COLOR}; font-family: {_FONT_STACK};">
            Action: {_e(alert.suggested_action)}</p>
        </td>
      </tr>
    </table>
  </td>
</tr>""")
    return "\n".join(parts)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Fixed population thresholds | Personal rolling baselines (SWC) | Widely adopted by 2020 | Individual variation makes population norms unreliable for daily monitoring |
| Single-metric alerts | Multi-metric convergence | Sports science consensus ~2022 | Single bad nights are noise; converging signals across systems are real |
| 7-day rolling avg baseline | 28-30 day rolling avg baseline | HRV research consensus 2024-2025 | 7 days too volatile for baseline; 28-30 days captures a full training cycle |
| ML-based anomaly detection | Deterministic z-score thresholds | Practical choice for personal tools | ML needs training data volume; z-scores are transparent, testable, debuggable |

**Sports science validation:**
- The Smallest Worthwhile Change (SWC) approach uses mean +/- 0.5 SD as the threshold for trivial vs. meaningful change. Using 1.0 SD for warnings and 2.0 SD for critical alerts is conservative and well-supported.
- A 30-day rolling average is the standard reference window in HRV-guided training research. The 28-day window aligns with this and captures a full training microcycle.
- Multi-metric convergence over 3+ days is the sports science standard for avoiding false positives from single-metric noise.

## Open Questions

1. **Exact single-metric extreme outlier threshold**
   - What we know: SWC literature suggests 0.5 SD for trivial boundary, 1.0 SD for meaningful. Extreme outliers should be well beyond "meaningful."
   - Recommendation: Use 2.5 SD for single-metric WARNING, 3.0 SD for CRITICAL. This is conservative -- only fires on genuine statistical outliers.

2. **Multi-metric convergence threshold**
   - What we know: Each individual metric in a convergence pattern needs a lower bar than single-metric outliers (since convergence IS the signal).
   - Recommendation: Use 1.0 SD per metric within a convergence pattern. When 3+ metrics all deviate by 1.0+ SD simultaneously for 3+ days, the combined probability of chance is extremely low.

3. **Body Battery drain acceleration metric**
   - What we know: CONTEXT.md says "Body Battery drain accelerating" for stress escalation pattern. No single column captures drain rate.
   - Recommendation: Compute as `body_battery_max - body_battery_min` as a proxy for daily drain. Higher drain = more stress. Add this as a derived metric to the extended trend window.

4. **Token budget increase**
   - What we know: Current budget is 6000 tokens. Adding 28-day trends (~150-200 tokens) + anomalies (~100-300 tokens) uses 250-500 additional tokens.
   - Recommendation: Increase DEFAULT_TOKEN_BUDGET to 7000. This provides headroom without risk -- Claude Haiku handles this easily.

5. **TREND_FIELDS expansion for convergence patterns**
   - What we know: Current TREND_FIELDS selects 8 columns. Convergence patterns need `deep_sleep_seconds`, `rest_stress_minutes`, `body_battery_max`, `body_battery_min`.
   - Recommendation: Add these 4 columns to TREND_FIELDS. They already exist in the `daily_metrics` table from Phase 1 ingestion.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (via uv) |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/ -x -q` |
| Full suite command | `uv run pytest tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TRND-02a | Extended trend computation produces 28-day stats with stddev | unit | `uv run pytest tests/test_trends.py -x -q -k extended` | No -- Wave 0 |
| TRND-02b | Insufficient data (< 14 days) marked as INSUFFICIENT | unit | `uv run pytest tests/test_trends.py -x -q -k insufficient` | No -- Wave 0 |
| TRND-02c | 28-day trends formatted and included in prompt | unit | `uv run pytest tests/test_prompt.py -x -q -k trends_28d` | No -- Wave 0 |
| TRND-03a | Z-score computation against personal baselines | unit | `uv run pytest tests/test_anomaly.py -x -q -k z_score` | No -- Wave 0 |
| TRND-03b | Single-metric extreme outlier detection | unit | `uv run pytest tests/test_anomaly.py -x -q -k outlier` | No -- Wave 0 |
| TRND-03c | 5 convergence patterns detect correctly | unit | `uv run pytest tests/test_anomaly.py -x -q -k convergence` | No -- Wave 0 |
| TRND-03d | Consecutive-day check with 3+ day threshold | unit | `uv run pytest tests/test_anomaly.py -x -q -k consecutive` | No -- Wave 0 |
| TRND-03e | Alert model serialization in DailyProtocol | unit | `uv run pytest tests/test_prompt.py -x -q -k alert` | No -- Wave 0 |
| TRND-03f | Alert banner rendering in HTML and plaintext | unit | `uv run pytest tests/test_renderer.py -x -q -k alert` | No -- Wave 0 |
| TRND-03g | Anomaly detection wired into analyze_daily pipeline | unit | `uv run pytest tests/test_analysis.py -x -q -k anomaly` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/ -x -q`
- **Per wave merge:** `uv run pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_anomaly.py` -- covers TRND-03a through TRND-03d (z-scores, outliers, convergence, consecutive days)
- [ ] Extend `tests/test_trends.py` -- covers TRND-02a, TRND-02b (extended trends, insufficient data)
- [ ] Extend `tests/test_prompt.py` -- covers TRND-02c, TRND-03e (28-day section, alert model)
- [ ] Extend `tests/test_renderer.py` -- covers TRND-03f (alert banners)
- [ ] Extend `tests/test_analysis.py` -- covers TRND-03g (anomaly in pipeline)

## Sources

### Primary (HIGH confidence)
- Project codebase: `src/biointelligence/trends/compute.py`, `trends/models.py` -- existing trend infrastructure
- Project codebase: `src/biointelligence/prompt/assembler.py`, `prompt/models.py` -- existing prompt/schema patterns
- Project codebase: `src/biointelligence/delivery/renderer.py` -- existing banner/rendering patterns
- Project codebase: `src/biointelligence/analysis/engine.py` -- existing pipeline orchestration
- [Python statistics module documentation](https://docs.python.org/3/library/statistics.html) -- stdev, mean, pstdev API reference

### Secondary (MEDIUM confidence)
- [MDPI Sensors: Monitoring Training Adaptation via HRV](https://www.mdpi.com/1424-8220/26/1/3) -- SWC methodology: mean +/- 0.5 SD threshold
- [Frontiers in Sports: HRV-based exercise prescription](https://www.frontiersin.org/journals/sports-and-active-living/articles/10.3389/fspor.2025.1578478/full) -- 30-day rolling avg as baseline reference
- [German Journal of Sports Medicine: HRV Methods](https://www.germanjournalsportsmedicine.com/archive/archive-2024/issue-3/heart-rate-variability-methods-and-analysis-in-sports-medicine-and-exercise-science/) -- Individual baseline tracking consensus
- [Science for Sport: HRV](https://www.scienceforsport.com/heart-rate-variability-hrv/) -- Practical HRV interpretation frameworks

### Tertiary (LOW confidence)
- None -- all findings verified against primary or secondary sources

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- zero new dependencies, all computation uses Python stdlib + existing project patterns
- Architecture: HIGH -- new anomaly/ module follows established patterns (trends/, analysis/), extension points clearly identified in existing code
- Pitfalls: HIGH -- all pitfalls identified from direct codebase inspection (TREND_FIELDS gaps, stddev edge cases, token budget)
- Statistical approach: HIGH -- z-score/SWC methodology verified against sports science literature and is widely adopted

**Research date:** 2026-03-04
**Valid until:** 2026-04-04 (stable domain, no fast-moving dependencies)
