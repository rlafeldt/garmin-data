---
phase: 8
slug: user-onboarding
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-05
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing Python) + Vitest (new for Next.js frontend) |
| **Config file** | `pyproject.toml` [tool.pytest.ini_options] (Python) / `vitest.config.ts` (frontend — Wave 0) |
| **Quick run command** | `source .venv/bin/activate && python -m pytest tests/ -x -q` |
| **Full suite command** | `source .venv/bin/activate && python -m pytest tests/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `source .venv/bin/activate && python -m pytest tests/ -x -q`
- **After every plan wave:** Run `source .venv/bin/activate && python -m pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 08-01-01 | 01 | 1 | ONBD-01 | smoke/manual | Manual browser test | -- Wave 0 | ⬜ pending |
| 08-02-01 | 02 | 1 | ONBD-02 | unit | `pytest tests/test_onboarding.py::test_essential_fields -x` | -- Wave 0 | ⬜ pending |
| 08-03-01 | 03 | 1 | ONBD-03 | unit | `pytest tests/test_profile.py::test_load_from_supabase -x` | -- Wave 0 | ⬜ pending |
| 08-04-01 | 04 | 1 | ONBD-04 | unit | `pytest tests/test_onboarding.py::test_consent_required -x` | -- Wave 0 | ⬜ pending |
| 08-05-01 | 05 | 1 | ONBD-05 | unit | `pytest tests/test_onboarding.py::test_profile_update -x` | -- Wave 0 | ⬜ pending |
| 08-06-01 | 06 | 1 | ONBD-06 | unit | `pytest tests/test_profile.py::test_yaml_fallback -x` | -- Wave 0 | ⬜ pending |
| 08-07-01 | 07 | 1 | ONBD-07 | unit | `pytest tests/test_lab_extractor.py::test_extraction -x` | -- Wave 0 | ⬜ pending |
| 08-08-01 | 08 | 1 | ONBD-08 | unit | `pytest tests/test_profile.py::test_hormonal_context -x` | -- Wave 0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_onboarding.py` — stubs for ONBD-02 through ONBD-06 (onboarding data mapping, completeness, consent)
- [ ] `tests/test_lab_extractor.py` — stubs for ONBD-07 (lab extraction with mocked Claude API)
- [ ] `tests/test_profile.py` additions — stubs for ONBD-03/ONBD-06/ONBD-08 (Supabase load, YAML fallback, hormonal fields)
- [ ] `onboarding/vitest.config.ts` — frontend test setup
- [ ] `cd onboarding && npm install` — new Next.js project setup

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 6-step wizard renders and navigates | ONBD-01 | UI rendering, multi-step navigation | Open browser, step through all 6 wizard steps, verify back/forward navigation |
| Onboarding completes under 3 minutes | ONBD-01 | Timing/UX concern | Time a complete onboarding flow with essential fields only |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
