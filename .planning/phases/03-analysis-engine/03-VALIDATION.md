---
phase: 3
slug: analysis-engine
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-03
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-mock (existing) |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/test_analysis.py -x` |
| **Full suite command** | `uv run pytest tests/ -x` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_analysis.py -x`
- **After every plan wave:** Run `uv run pytest tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | TRNG-01 | unit | `uv run pytest tests/test_analysis.py::TestAnalyzePrompt::test_protocol_has_training_readiness -x` | ❌ W0 | ⬜ pending |
| 03-01-02 | 01 | 1 | TRNG-02 | unit | `uv run pytest tests/test_analysis.py::TestAnalyzePrompt::test_protocol_has_training_load -x` | ❌ W0 | ⬜ pending |
| 03-01-03 | 01 | 1 | TRNG-03 | unit | `uv run pytest tests/test_analysis.py::TestAnalyzePrompt::test_protocol_has_training_recommendation -x` | ❌ W0 | ⬜ pending |
| 03-01-04 | 01 | 1 | TRNG-04 | unit | `uv run pytest tests/test_analysis.py::TestAnalyzePrompt::test_protocol_has_stress_impact -x` | ❌ W0 | ⬜ pending |
| 03-01-05 | 01 | 1 | SLEP-01 | unit | `uv run pytest tests/test_analysis.py::TestAnalyzePrompt::test_protocol_has_sleep_analysis -x` | ❌ W0 | ⬜ pending |
| 03-01-06 | 01 | 1 | SLEP-02 | unit | `uv run pytest tests/test_analysis.py::TestAnalyzePrompt::test_protocol_has_sleep_tips -x` | ❌ W0 | ⬜ pending |
| 03-01-07 | 01 | 1 | NUTR-01 | unit | `uv run pytest tests/test_analysis.py::TestAnalyzePrompt::test_protocol_has_nutrition -x` | ❌ W0 | ⬜ pending |
| 03-01-08 | 01 | 1 | NUTR-02 | unit | `uv run pytest tests/test_analysis.py::TestAnalyzePrompt::test_protocol_has_hydration -x` | ❌ W0 | ⬜ pending |
| 03-01-09 | 01 | 1 | SUPP-01 | unit | `uv run pytest tests/test_analysis.py::TestAnalyzePrompt::test_protocol_has_supplements -x` | ❌ W0 | ⬜ pending |
| 03-01-10 | 01 | 1 | SUPP-02 | unit | `uv run pytest tests/test_analysis.py::TestAnalyzePrompt::test_protocol_has_supplement_reasoning -x` | ❌ W0 | ⬜ pending |
| 03-02-01 | 02 | 1 | SAFE-02 | unit | `uv run pytest tests/test_analysis.py::TestDegradedData::test_partial_data_includes_caveats -x` | ❌ W0 | ⬜ pending |
| 03-02-02 | 02 | 1 | SAFE-03 | unit | `uv run pytest tests/test_analysis.py::TestDegradedData::test_no_wear_uses_trends -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_analysis.py` — stubs for all analysis engine tests (TRNG-01 through SAFE-03)
- [ ] Mock fixtures: fake `DailyProtocol` response, mock `anthropic.Anthropic` client
- [ ] `uv add anthropic` — new dependency

*Existing pytest + pytest-mock infrastructure covers framework needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Protocol tone is balanced/readable | CONTEXT decision | Subjective quality | Review sample protocol output for tone |

*All functional behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
