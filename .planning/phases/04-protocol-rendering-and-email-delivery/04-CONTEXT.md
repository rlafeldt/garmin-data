# Phase 4: Protocol Rendering and Email Delivery - Context

**Gathered:** 2026-03-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Render the validated DailyProtocol JSON into a styled HTML email and deliver it reliably via Resend. Covers email template design, rendering logic, Resend integration, and data freshness display. Pipeline automation, scheduling, and failure notifications are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Email structure
- Open with a readiness dashboard: readiness score (1-10), key numbers (HRV, sleep score, body battery), then action summary from overall_summary
- Narrative flow section order: Sleep -> Recovery -> Training -> Nutrition -> Supplementation (tells the story: how you slept -> how recovered -> what to do -> how to fuel)
- Show recommendation + reasoning per domain (~2 min read), skip intermediate fields (e.g., hrv_interpretation standalone) since reasoning folds them in
- "Why this matters" section after all 5 domains as a closing synthesis — ties cross-domain patterns together, explains broader context (PROT-04)

### Visual style
- Full HTML email with styled sections, proper headings, bold key numbers
- Traffic light color coding for readiness: green (8-10), yellow (5-7), red (1-4)
- Clean and functional template — think "Stripe receipt" style: well-structured, clear typography, responsive for mobile. No images, logos, or fancy graphics
- Multipart email (HTML + plain-text fallback) for universal inbox compatibility including Apple Watch and smart displays

### Resend integration
- Custom domain for sender identity (user will configure DNS: DKIM, SPF)
- Sender name: "BioIntelligence"
- Subject line format: "Daily Protocol — {date} — Readiness: {score}/10" (readiness visible without opening)
- Configuration in .env file: RESEND_API_KEY, SENDER_EMAIL, RECIPIENT_EMAIL — extends existing Settings class
- Resend Python SDK for sending

### Data freshness (SAFE-01)
- Top banner below readiness dashboard for data quality warnings — colored warning when metrics are missing or stale
- Hide banner entirely when all data is clean (no noise on good days)
- Last Garmin sync timestamp always displayed in email footer (e.g., "Data from: Mar 2, 2026 06:42 CET")
- Failure notifications (pipeline errors, no protocol generated) deferred to Phase 5 Pipeline Automation — Phase 4 only renders and sends when a valid protocol exists

### Claude's Discretion
- HTML template implementation approach (inline CSS vs embedded styles for email client compatibility)
- Plain-text rendering logic from DailyProtocol fields
- Exact color hex values for traffic light indicators
- Footer content and layout
- Resend SDK error handling and retry strategy
- How to extract last sync timestamp from stored data

</decisions>

<specifics>
## Specific Ideas

- Phase 3 decided protocol tone is "balanced — data-grounded but readable, action-first, brief reasoning, always cite specific numbers" — the email template should present this tone faithfully, not add its own editorial layer
- Readiness score in the subject line enables inbox triage without opening — critical for the daily habit to stick
- Narrative flow (sleep -> ... -> supplementation) was chosen over priority-based ordering because it tells the story of the day from waking up
- Multipart email ensures Apple Watch notification previews are readable (plain-text part)

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `DailyProtocol` model (prompt/models.py): complete output schema with 5 domain sub-models — each has specific fields + reasoning. Template renders directly from these fields
- `AnalysisResult` model (analysis/engine.py): wraps DailyProtocol with metadata (date, model, token counts, success) — rendering function receives this
- `Settings` class (config.py): pydantic-settings with .env — extend with RESEND_API_KEY, SENDER_EMAIL, RECIPIENT_EMAIL
- `data_quality_notes` field on DailyProtocol: already captures data freshness info from the analysis — renders into the top banner
- `readiness_score` field on TrainingRecommendation: integer 1-10 — drives subject line and color coding
- structlog configured throughout — email module should log send success/failure

### Established Patterns
- Pydantic models for all data structures — email rendering models follow this
- pydantic-settings with .env for configuration — new Resend settings follow same pattern
- tenacity for retry logic on external API calls — reuse for Resend API
- Pipeline functions (run_ingestion, run_analysis) return Pydantic result models — run_delivery follows this pattern
- Lazy imports in __init__.py via __getattr__ pattern

### Integration Points
- `run_analysis()` in pipeline.py returns AnalysisResult — Phase 4 adds `run_delivery()` that takes AnalysisResult and sends email
- `DailyProtocol` is the input to the renderer — all email content derives from this model
- Settings class needs new fields: RESEND_API_KEY, SENDER_EMAIL, RECIPIENT_EMAIL
- CLI (main.py) needs new --deliver flag or Phase 5 handles orchestration
- New module: likely `delivery/` package with renderer.py, sender.py, templates

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 04-protocol-rendering-and-email-delivery*
*Context gathered: 2026-03-03*
