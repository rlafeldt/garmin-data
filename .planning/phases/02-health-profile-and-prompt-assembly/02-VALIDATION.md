---
phase: 2
slug: health-profile-and-prompt-assembly
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-03
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 + pytest-mock 3.15.1 |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/ -x -q` |
| **Full suite command** | `uv run pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | PROF-01 | unit | `uv run pytest tests/test_profile.py -x` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | PROF-01 | unit | `uv run pytest tests/test_profile.py::TestProfileValidation -x` | ❌ W0 | ⬜ pending |
| 02-01-03 | 01 | 1 | TRND-01 | unit | `uv run pytest tests/test_trends.py::TestTrendComputation -x` | ❌ W0 | ⬜ pending |
| 02-01-04 | 01 | 1 | TRND-01 | unit | `uv run pytest tests/test_trends.py::TestTrendDirection -x` | ❌ W0 | ⬜ pending |
| 02-01-05 | 01 | 1 | TRND-01 | unit | `uv run pytest tests/test_trends.py::TestNoWearExclusion -x` | ❌ W0 | ⬜ pending |
| 02-01-06 | 01 | 1 | TRND-01 | unit | `uv run pytest tests/test_trends.py::TestInsufficientData -x` | ❌ W0 | ⬜ pending |
| 02-01-07 | 01 | 1 | TRND-01 | unit | `uv run pytest tests/test_trends.py::TestLowerIsBetter -x` | ❌ W0 | ⬜ pending |
| 02-02-01 | 02 | 2 | PROF-02 | unit | `uv run pytest tests/test_prompt.py::TestPromptAssembly -x` | ❌ W0 | ⬜ pending |
| 02-02-02 | 02 | 2 | TRND-04 | unit | `uv run pytest tests/test_prompt.py::TestSportsScienceGrounding -x` | ❌ W0 | ⬜ pending |
| 02-02-03 | 02 | 2 | ALL | unit | `uv run pytest tests/test_prompt.py::TestTokenBudget -x` | ❌ W0 | ⬜ pending |
| 02-02-04 | 02 | 2 | ALL | unit | `uv run pytest tests/test_prompt.py::TestPromptStructure -x` | ❌ W0 | ⬜ pending |
| 02-02-05 | 02 | 2 | ALL | unit | `uv run pytest tests/test_trends.py::TestDataFetching -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_profile.py` — health profile loading and validation tests
- [ ] `tests/test_trends.py` — trend computation, direction, data fetching tests
- [ ] `tests/test_prompt.py` — prompt assembly, token budget, structure tests
- [ ] `tests/fixtures/health_profile.yaml` — sample YAML fixture for tests
- [ ] `tests/fixtures/trend_data.json` — mock Supabase response fixtures for trend tests
- [ ] `health_profile.yaml` — reference health profile config (also serves as documentation)

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
