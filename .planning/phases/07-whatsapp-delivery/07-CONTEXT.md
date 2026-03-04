# Phase 7: WhatsApp Delivery - Context

**Gathered:** 2026-03-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace email as the primary Daily Protocol delivery channel with WhatsApp messages via Meta's WhatsApp Cloud API. The protocol is reformatted for mobile/WhatsApp readability (emoji headers, bold keys, condensed reasoning) and sent as a pre-approved template message. Email delivery is retained as an automatic fallback when WhatsApp fails. Meta Business Verification is a prerequisite for production use but development/testing proceeds with Meta's test number.

</domain>

<decisions>
## Implementation Decisions

### Channel choice
- WhatsApp via Meta's WhatsApp Cloud API (direct HTTP, not Twilio or third-party wrapper)
- Meta Business account needed — starting from scratch, verification done separately
- Build and test with Meta's test phone number first; production requires Meta Business Verification
- If verification ultimately stalls, code is built and working — just needs the verification gate cleared

### Message format
- Full protocol condensed for mobile — all 5 domains included, not just TL;DR
- Same domain order as email: Sleep -> Recovery -> Training -> Nutrition -> Supplementation (Phase 4 decision carried forward)
- Emoji headers + bold keys for visual structure (e.g., "💤 *Sleep*\nQuality: Good\n...")
- WhatsApp formatting: *bold* for section names and key labels, plain text for values
- Include 1-2 sentence trimmed reasoning per domain — the "why" is what makes the protocol valuable
- Alert banners (from Phase 6) rendered as prominent text blocks at message top
- "Why This Matters" synthesis section included at the end
- Readiness score prominent at the top of the message

### Delivery strategy
- WhatsApp replaces email as the primary delivery channel (not alongside)
- Email is the automatic fallback: if WhatsApp send fails after retries, fall back to email delivery via Resend
- Same timing as current pipeline — message sent during the existing 7 AM CET GitHub Actions run
- No separate scheduling or delivery time configuration in this phase
- Fire-and-forget: log API response (message ID + success/fail), no webhook callbacks for delivered/read status

### API integration
- Direct HTTP calls using httpx (already a project dependency) — no third-party WhatsApp library
- Meta Cloud API POST to /v21.0/{phone_number_id}/messages endpoint
- Pre-approved message template with a single body variable containing the full formatted protocol text
- Template name: "daily_protocol" (simple, one body parameter)
- Three new .env settings: WHATSAPP_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_RECIPIENT_PHONE
- Tenacity retry pattern consistent with existing Resend sender

### Claude's Discretion
- Exact WhatsApp message character budgeting per domain section
- How to handle the 65,536 char limit (unlikely to hit with condensed format, but guard anyway)
- Template registration instructions/documentation
- httpx client configuration (timeouts, headers)
- Error classification (which Meta API errors are retryable vs permanent)

</decisions>

<specifics>
## Specific Ideas

- The existing `render_text()` function in delivery/renderer.py is conceptually close to WhatsApp format — use it as a starting point but add emoji headers and WhatsApp formatting
- Email fallback means the existing Resend sender stays in the codebase and is called on WhatsApp failure
- The `run_delivery()` pipeline function needs to try WhatsApp first, then fall back to email — not a channel selection flag, but a try/fallback pattern
- Meta Business Verification is an external process (not code) — document the steps needed but don't block development on it
- WhatsApp template approval can take 24-48 hours — factor this into the "get it working" timeline

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `render_text()` (delivery/renderer.py): Plain-text renderer is the starting point for WhatsApp format — adapt with emoji headers and WhatsApp formatting markers
- `send_email()` (delivery/sender.py): Resend sender with tenacity retry — reuse as email fallback, model WhatsApp sender after this pattern
- `DeliveryResult` model (delivery/sender.py): Reuse for WhatsApp delivery results (date, message_id, success, error)
- `Settings` class (config.py): Extend with WHATSAPP_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_RECIPIENT_PHONE
- `build_subject()` (delivery/renderer.py): Subject line concept maps to WhatsApp template header
- Alert rendering in `render_text()`: Already handles alert banners in plain text — adapt for WhatsApp

### Established Patterns
- tenacity for retry logic on external API calls — reuse for WhatsApp Cloud API
- Pydantic models for all data structures — WhatsApp sender follows DeliveryResult pattern
- pydantic-settings with .env for configuration — WhatsApp credentials follow same pattern
- Lazy imports in __init__.py via __getattr__ pattern
- structlog logging throughout — WhatsApp module logs send success/failure

### Integration Points
- `run_delivery()` in pipeline.py: Modify to try WhatsApp first, fall back to email on failure
- `run_full_pipeline()` in pipeline.py: No changes needed — calls run_delivery() which handles channel logic
- `Settings` class: Add three WhatsApp fields (access_token, phone_number_id, recipient_phone)
- `delivery/` package: Add whatsapp_renderer.py and whatsapp_sender.py alongside existing email files
- GitHub Actions workflow: Add WHATSAPP_* secrets to the environment

</code_context>

<deferred>
## Deferred Ideas

- Interactive WhatsApp bot for follow-up questions about the protocol — separate phase
- Telegram as alternative channel (DLVR-03 in v2 requirements) — consider if WhatsApp verification proves blocking
- Rich media attachments (charts, trend graphs) in WhatsApp messages — future enhancement
- WhatsApp delivery status tracking via webhooks — adds complexity for minimal value in single-user tool
- Delivery time configuration from onboarding (Phase 8) — scheduling stays at pipeline run time for now

</deferred>

---

*Phase: 07-whatsapp-delivery*
*Context gathered: 2026-03-04*
