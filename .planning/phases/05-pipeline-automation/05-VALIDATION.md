---
phase: 5
slug: pipeline-automation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-03
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest with pytest-mock |
| **Config file** | `pyproject.toml` [tool.pytest.ini_options] |
| **Quick run command** | `uv run pytest tests/ -x -q` |
| **Full suite command** | `uv run pytest tests/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 1 | AUTO-01 | unit | `uv run pytest tests/test_automation.py::TestTokenPersistence -x` | ❌ W0 | ⬜ pending |
| 05-01-02 | 01 | 1 | AUTO-01 | unit | `uv run pytest tests/test_automation.py::TestTokenPersistence -x` | ❌ W0 | ⬜ pending |
| 05-01-03 | 01 | 1 | AUTO-01 | unit | `uv run pytest tests/test_client.py::TestSupabaseTokenAuth -x` | ❌ W0 | ⬜ pending |
| 05-01-04 | 01 | 1 | AUTO-01 | unit | `uv run pytest tests/test_pipeline.py -x` | ✅ partial | ⬜ pending |
| 05-01-05 | 01 | 1 | AUTO-02 | unit | `uv run pytest tests/test_automation.py::TestFailureNotification -x` | ❌ W0 | ⬜ pending |
| 05-01-06 | 01 | 1 | AUTO-02 | unit | `uv run pytest tests/test_automation.py::TestRunLog -x` | ❌ W0 | ⬜ pending |
| 05-01-07 | 01 | 1 | AUTO-02 | unit | `uv run pytest tests/test_automation.py::TestFailureNotification -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_automation.py` — stubs for token persistence, run logging, failure notification (AUTO-01, AUTO-02)
- [ ] Extend `tests/test_client.py` — stubs for Supabase token auth path (AUTO-01)
- [ ] Extend `tests/test_pipeline.py` — stubs for run logging integration (AUTO-02)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| GitHub Actions cron triggers at correct time | AUTO-01 | Real cron scheduling requires actual GitHub infrastructure | After deploy: verify first scheduled run triggers within expected window |
| Garmin token bootstrap from local to Supabase | AUTO-01 | Requires real Garmin credentials and interactive auth | Run locally, extract tokens with garth.dumps(), seed into Supabase |
| Email arrives in inbox on pipeline failure | AUTO-02 | End-to-end email delivery through Resend | Trigger manual workflow_dispatch with invalid date or mock a failure |
| workflow_dispatch manual trigger works | AUTO-01 | Requires actual GitHub Actions UI or API | Trigger from GitHub Actions tab with optional --date parameter |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
