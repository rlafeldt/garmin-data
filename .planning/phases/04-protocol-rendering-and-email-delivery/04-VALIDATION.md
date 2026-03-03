---
phase: 4
slug: protocol-rendering-and-email-delivery
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-03
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest with pytest-mock |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/ -x -q` |
| **Full suite command** | `uv run pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

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
| 04-01-01 | 01 | 0 | PROT-01 | unit stub | `uv run pytest tests/test_renderer.py -x` | ❌ W0 | ⬜ pending |
| 04-01-02 | 01 | 0 | PROT-03 | unit stub | `uv run pytest tests/test_sender.py -x` | ❌ W0 | ⬜ pending |
| 04-01-03 | 01 | 0 | PROT-03 | unit stub | `uv run pytest tests/test_pipeline.py::TestRunDelivery -x` | ❌ W0 | ⬜ pending |
| 04-01-04 | 01 | 1 | PROT-01 | unit | `uv run pytest tests/test_renderer.py::TestRenderHtml -x` | ❌ W0 | ⬜ pending |
| 04-01-05 | 01 | 1 | PROT-02 | unit | `uv run pytest tests/test_renderer.py::TestRenderHtml::test_includes_reasoning -x` | ❌ W0 | ⬜ pending |
| 04-01-06 | 01 | 1 | PROT-04 | unit | `uv run pytest tests/test_renderer.py::TestRenderHtml::test_why_this_matters -x` | ❌ W0 | ⬜ pending |
| 04-01-07 | 01 | 1 | SAFE-01 | unit | `uv run pytest tests/test_renderer.py::TestDataQualityBanner -x` | ❌ W0 | ⬜ pending |
| 04-01-08 | 01 | 1 | SAFE-01 | unit | `uv run pytest tests/test_renderer.py::TestDataQualityBanner::test_hidden_when_clean -x` | ❌ W0 | ⬜ pending |
| 04-01-09 | 01 | 1 | SAFE-01 | unit | `uv run pytest tests/test_renderer.py::TestRenderHtml::test_footer_timestamp -x` | ❌ W0 | ⬜ pending |
| 04-02-01 | 02 | 2 | PROT-03 | unit | `uv run pytest tests/test_sender.py::TestSendEmail -x` | ❌ W0 | ⬜ pending |
| 04-02-02 | 02 | 2 | PROT-03 | unit | `uv run pytest tests/test_pipeline.py::TestRunDelivery -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_renderer.py` — stubs for PROT-01, PROT-02, PROT-04, SAFE-01 (HTML + text rendering)
- [ ] `tests/test_sender.py` — stubs for PROT-03 (Resend SDK integration, mocked)
- [ ] New test cases in `tests/test_pipeline.py` — stubs for run_delivery pipeline function
- [ ] `resend` package install: `uv add resend`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Email arrives in inbox (not spam) | PROT-03 | Requires real Resend API + DNS config | Send test email via CLI, verify inbox delivery and formatting |
| Email renders correctly on mobile | PROT-01 | Visual verification needed | Open test email on phone/tablet, check responsive layout |
| Apple Watch plain-text preview | PROT-01 | Requires Apple Watch device | Send email, check notification preview on Apple Watch |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
