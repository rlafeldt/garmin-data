---
phase: 7
slug: whatsapp-delivery
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-04
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-mock |
| **Config file** | pyproject.toml [tool.pytest.ini_options] |
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
| 07-01-01 | 01 | 1 | WHTS-01 | unit | `uv run pytest tests/test_whatsapp_renderer.py -x` | No -- Wave 0 | ⬜ pending |
| 07-01-02 | 01 | 1 | WHTS-01 | unit | `uv run pytest tests/test_whatsapp_renderer.py::TestRenderWhatsappAlerts -x` | No -- Wave 0 | ⬜ pending |
| 07-01-03 | 01 | 1 | WHTS-02 | unit | `uv run pytest tests/test_pipeline.py::TestRunDeliveryWhatsApp -x` | No -- Wave 0 | ⬜ pending |
| 07-01-04 | 01 | 1 | WHTS-03 | unit | `uv run pytest tests/test_whatsapp_sender.py -x` | No -- Wave 0 | ⬜ pending |
| 07-01-05 | 01 | 1 | WHTS-03 | unit | `uv run pytest tests/test_whatsapp_sender.py::TestRetryClassification -x` | No -- Wave 0 | ⬜ pending |
| 07-01-06 | 01 | 1 | WHTS-04 | unit | `uv run pytest tests/test_whatsapp_sender.py::TestSettingsWhatsApp -x` | No -- Wave 0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_whatsapp_renderer.py` — stubs for WHTS-01 (WhatsApp formatting, emoji headers, domain order, alerts, character length)
- [ ] `tests/test_whatsapp_sender.py` — stubs for WHTS-03, WHTS-04 (API call, retry logic, error handling, Settings fields)
- [ ] `tests/test_pipeline.py` additions — stubs for WHTS-02 (WhatsApp-first delivery with email fallback)

*Existing test infrastructure (pytest, conftest.py) covers framework needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| WhatsApp message renders correctly on mobile device | WHTS-01 | Visual rendering depends on WhatsApp client | Send test message to phone, verify emoji headers, bold formatting, section layout |
| Template approval succeeds in Meta Business Manager | WHTS-03 | External service dependency | Submit template via Meta dashboard, confirm approval status |
| Email fallback triggers on real WhatsApp failure | WHTS-02 | Requires actual API failure scenario | Revoke token temporarily, run pipeline, verify email arrives |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
