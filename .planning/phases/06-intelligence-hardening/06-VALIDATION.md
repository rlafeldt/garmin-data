---
phase: 6
slug: intelligence-hardening
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-04
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (via uv) |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/ -x -q` |
| **Full suite command** | `uv run pytest tests/ -v` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 1 | TRND-02 | unit | `uv run pytest tests/test_trends.py -x -q -k extended` | ❌ W0 | ⬜ pending |
| 06-01-02 | 01 | 1 | TRND-02 | unit | `uv run pytest tests/test_trends.py -x -q -k insufficient` | ❌ W0 | ⬜ pending |
| 06-01-03 | 01 | 1 | TRND-02 | unit | `uv run pytest tests/test_prompt.py -x -q -k trends_28d` | ❌ W0 | ⬜ pending |
| 06-01-04 | 01 | 1 | TRND-03 | unit | `uv run pytest tests/test_anomaly.py -x -q -k z_score` | ❌ W0 | ⬜ pending |
| 06-01-05 | 01 | 1 | TRND-03 | unit | `uv run pytest tests/test_anomaly.py -x -q -k outlier` | ❌ W0 | ⬜ pending |
| 06-01-06 | 01 | 1 | TRND-03 | unit | `uv run pytest tests/test_anomaly.py -x -q -k convergence` | ❌ W0 | ⬜ pending |
| 06-01-07 | 01 | 1 | TRND-03 | unit | `uv run pytest tests/test_anomaly.py -x -q -k consecutive` | ❌ W0 | ⬜ pending |
| 06-01-08 | 01 | 1 | TRND-03 | unit | `uv run pytest tests/test_prompt.py -x -q -k alert` | ❌ W0 | ⬜ pending |
| 06-01-09 | 01 | 1 | TRND-03 | unit | `uv run pytest tests/test_renderer.py -x -q -k alert` | ❌ W0 | ⬜ pending |
| 06-01-10 | 01 | 1 | TRND-03 | unit | `uv run pytest tests/test_analysis.py -x -q -k anomaly` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_anomaly.py` — stubs for TRND-03 (z-scores, outliers, convergence, consecutive days)
- [ ] Extend `tests/test_trends.py` — stubs for TRND-02 (extended trends, insufficient data)
- [ ] Extend `tests/test_prompt.py` — stubs for TRND-02, TRND-03 (28-day section, alert model)
- [ ] Extend `tests/test_renderer.py` — stubs for TRND-03 (alert banners)
- [ ] Extend `tests/test_analysis.py` — stubs for TRND-03 (anomaly in pipeline)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Alert banner visual appearance in email | TRND-03 | CSS styling not testable in unit tests | Render HTML, open in browser, verify yellow/red banner colors and layout |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
