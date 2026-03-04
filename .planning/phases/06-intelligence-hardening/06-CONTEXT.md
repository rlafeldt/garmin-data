# Phase 6: Intelligence Hardening - Context

**Gathered:** 2026-03-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Evolve the analysis engine from reactive day-zero analysis to longitudinal pattern detection with proactive alerts. Add 28-day extended trend windows fed into the analysis prompt, server-side multi-metric anomaly detection, and proactive alert banners in the Daily Protocol email. The existing 7-day trend computation, Claude analysis pipeline, and email delivery infrastructure are already built — this phase extends them.

</domain>

<decisions>
## Implementation Decisions

### Alert presentation
- Top banner at the very top of the email, before the overall summary — alerts are the first thing seen
- Two severity levels: Warning (yellow #eab308) and Critical (red #ef4444) — matches existing traffic light color scheme
- No banner when nothing is flagged — most days should be alert-free, clean email
- Each alert includes both detection description AND suggested action — consistent with the protocol's action-first philosophy (e.g., "HRV declining 3 consecutive days — consider a rest day or light zone 1 session")

### Alert sensitivity
- Personal baselines defined as rolling 28-day mean + standard deviation — adapts as fitness changes over time
- Multi-metric convergence over 3+ consecutive days triggers standard alerts — consistent with Phase 3's "don't cry wolf on single bad nights"
- Single-metric extreme outliers also get flagged as standalone alerts — catches acute events even without multi-metric convergence
- Anomaly detection happens server-side in Python, deterministically — feed detected anomalies into Claude prompt so Claude focuses on interpretation and recommendations. Reliable, testable, consistent across runs.

### 28-day trend visibility
- 28-day trends feed Claude silently — do NOT show in email unless anomalous
- 7-day trends also stay hidden from email (current behavior preserved) — only anomalies surface
- Summary stats only in prompt: 28-day mean, stddev, direction, and any detected anomalies — no raw daily values. Stay within existing ~4-6K token budget.
- Minimum 14 of 28 days of data required for 28-day trend computation — below that, mark as "insufficient data" and skip anomaly detection. Consistent with Phase 2's ~57% coverage ratio (4 of 7).

### Metric convergence patterns
- 5 hardcoded convergence patterns in Python code (personal tool — edit source to change):
  1. **HRV + HR + Sleep** (from roadmap): HRV decline + elevated resting HR + poor sleep efficiency
  2. **Overtraining signals**: Training load rising + HRV declining + Body Battery not recovering
  3. **Sleep debt accumulation**: Sleep score declining + total sleep dropping + deep sleep shrinking
  4. **Stress escalation**: Avg stress rising + relaxation time dropping + Body Battery drain accelerating
  5. **Recovery stall**: Body Battery morning charge plateauing low + resting HR creeping up + HRV flat/declining
- No alert history tracking — stateless, each day's analysis is independent. If a pattern persists, the alert fires again. The 28-day window inherently captures persistence.

### Claude's Discretion
- Exact statistical threshold for single-metric extreme outliers (implementation decides appropriate stddev cutoff)
- Specific stddev thresholds for multi-metric convergence pattern detection
- Enhanced trend statistics beyond avg/min/max (stddev, percentiles, z-scores — whatever anomaly detection needs)
- Token budget adjustments to accommodate 28-day trend data alongside existing sections
- Anomaly detection module architecture and code organization
- DailyProtocol schema extension for alert fields (top-level alerts list, Alert sub-model structure)
- Prompt template updates for anomaly detection directives
- SQL query design for 28-day window fetching

</decisions>

<specifics>
## Specific Ideas

- Server-side anomaly detection feeds INTO the prompt — Claude interprets and recommends, Python detects. This keeps alerts deterministic and testable while letting Claude add clinical context.
- Alert format should feel like the existing data_quality_notes banner pattern but with severity coloring and action text.
- The 5 convergence patterns are sports-science-grounded: overtraining, sleep debt, stress, and recovery stall are the four classic failure modes for endurance athletes beyond the obvious HRV+HR+sleep cluster.
- "Don't cry wolf" philosophy from Phase 3 is preserved: multi-metric over 3+ days is the bar, with single-metric only for true statistical outliers.

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `compute_trends()` (trends/compute.py): Already accepts `window_days` parameter — call twice for 7-day and 28-day windows
- `fetch_trend_window()` (trends/compute.py): Supabase query with date range filter and tenacity retry — reuse for 28-day fetch
- `TrendResult` / `MetricTrend` models (trends/models.py): Current stats are avg/min/max/direction — extend with stddev for anomaly baselines
- `data_quality_notes` field on DailyProtocol: Proves the alert banner pattern works in the renderer — extend to formal alerts
- Traffic light colors in renderer.py: GREEN (#22c55e), YELLOW (#eab308), RED (#ef4444) — reuse for alert severity
- `render_html()` / `render_plaintext()` (delivery/renderer.py): Already has data quality banner rendering — add alert banner above it

### Established Patterns
- Pydantic models for all data structures — new Alert and anomaly models follow this
- structlog for logging — anomaly detection should log detected patterns
- tenacity for retry on Supabase calls — reuse for 28-day data fetching
- Split-half direction computation (trends/compute.py) — 28-day trends use same approach
- Pipeline functions return Pydantic result models — anomaly detection follows this

### Integration Points
- `analyze_daily()` (analysis/engine.py): Add 28-day trend computation and anomaly detection between existing trend computation and prompt assembly
- `PromptContext` (prompt/models.py): Extend to include 28-day trends and detected anomalies
- `assemble_prompt()` (prompt/assembler.py): Add `<trends_28d>` and `<anomalies>` sections with appropriate budget priority
- `DailyProtocol` (prompt/models.py): Add `alerts: list[Alert]` field for structured alert output
- `render_html()` / `render_plaintext()` (delivery/renderer.py): Add alert banner rendering at top of email
- `ANALYSIS_DIRECTIVES` in prompt assembler: Update to instruct Claude on anomaly interpretation

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 06-intelligence-hardening*
*Context gathered: 2026-03-04*
