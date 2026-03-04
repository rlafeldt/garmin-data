# Phase 7: WhatsApp Delivery - Context

**Gathered:** 2026-03-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Add WhatsApp as a delivery channel for the Daily Protocol alongside email. The protocol is reformatted for mobile/WhatsApp readability (concise sections, no heavy HTML) and sent via WhatsApp Business API. Delivery timing can be informed by the user's preferred insight delivery time from onboarding (Step 04: Morning / Post-workout / Evening / Flexible).

Note: WhatsApp was initially listed as out-of-scope due to Meta Business Verification requirements and template pre-approval. This phase re-evaluates feasibility and implements if viable, or pivots to an alternative messaging channel.

</domain>

<decisions>
## Implementation Decisions

### Delivery channel strategy
- WhatsApp delivery operates alongside email (not replacing it) — user chooses preferred channel
- The onboarding questionnaire (Phase 8, Step 04) captures "Preferred insight delivery time" which feeds scheduling
- WhatsApp messages must be concise — protocol sections summarised for mobile readability

### WhatsApp Business API requirements
- Meta Business Verification required for production
- Message templates must be pre-approved by Meta
- 24-hour messaging window rules apply for non-template messages
- Consider alternatives if verification proves blocking: Telegram (free, immediate, rich Markdown) or SMS

### Message formatting
- No HTML — WhatsApp supports limited formatting (*bold*, _italic_, ~strikethrough~, ```monospace```)
- Protocol must be condensed: TL;DR + key metrics + top 3 actions per domain
- Alert banners (from Phase 6) rendered as prominent text blocks at message top
- Consider splitting into multiple messages if single message exceeds WhatsApp limits (65,536 chars)

### Delivery confirmation
- WhatsApp API provides message status callbacks (sent / delivered / read)
- Pipeline logs delivery status — failure triggers fallback to email
- Retry logic consistent with existing email delivery (tenacity pattern)

</decisions>

<specifics>
## Specific Ideas

- The "Preferred insight delivery time" from onboarding Step 04 directly maps to delivery scheduling:
  - Morning: send with overnight recovery data first thing
  - Post-workout: send after detecting activity completion via Garmin data
  - Evening: end-of-day full summary
  - Flexible: send on pipeline completion (current behavior)
- WhatsApp template messages could include quick-reply buttons (e.g., "Show full protocol" / "Training details" / "Skip today")
- If WhatsApp Business verification is prohibitive, Telegram remains the pragmatic alternative (already noted in v2 requirements as DLVR-03)

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `delivery/` package: email renderer and Resend sender — extend with WhatsApp renderer and sender
- `render_plaintext()` (delivery/renderer.py): Plain-text rendering is closer to WhatsApp format than HTML
- `run_delivery()` pipeline function: Add channel selection logic
- `Settings` model: Extend with WhatsApp API credentials and channel preference

### Integration Points
- `run_delivery()`: Branch on delivery channel (email / whatsapp / both)
- `render_whatsapp()`: New renderer producing WhatsApp-formatted text (based on plaintext renderer)
- `WhatsAppSender`: New sender class using WhatsApp Business API (or Twilio WhatsApp API)
- Pipeline orchestrator: Delivery time scheduling based on onboarding preference
- `DailyProtocol` alerts: Render as WhatsApp-formatted alert blocks

</code_context>

<deferred>
## Deferred Ideas

- Interactive WhatsApp bot for follow-up questions about the protocol
- Telegram as alternative channel (DLVR-03)
- Rich media attachments (charts, trend graphs) in WhatsApp messages

</deferred>

---

*Phase: 07-whatsapp-delivery*
*Context gathered: 2026-03-04*
