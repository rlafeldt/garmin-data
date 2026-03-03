# Phase 4: Protocol Rendering and Email Delivery - Research

**Researched:** 2026-03-03
**Domain:** HTML email rendering, Resend transactional email API, Python email templating
**Confidence:** HIGH

## Summary

Phase 4 transforms the validated `DailyProtocol` JSON (produced by Phase 3's analysis engine) into a styled HTML email and delivers it via the Resend transactional email service. The core work divides into three areas: (1) rendering the DailyProtocol model into both HTML and plain-text formats, (2) integrating the Resend Python SDK for reliable delivery, and (3) extending the existing pipeline/CLI to support a `--deliver` step.

The Resend Python SDK (v2.23.0) natively supports sending both `html` and `text` parameters in a single API call, which automatically produces a multipart MIME email -- no manual MIME construction is needed. HTML email styling must use inline CSS for universal client compatibility (Gmail strips `<style>` tags). The project's existing patterns (pydantic-settings for config, tenacity for retry, structlog for logging, Pydantic result models for pipeline functions) apply directly to this phase.

**Primary recommendation:** Build a `delivery/` package with three modules: `renderer.py` (DailyProtocol to HTML/text conversion with inline CSS), `sender.py` (Resend SDK wrapper with tenacity retry), and integration into `pipeline.py` as `run_delivery()`. Use table-based HTML layout with inline styles for email client compatibility. Resend handles multipart automatically when both `html` and `text` params are provided.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Email structure:** Open with readiness dashboard (score 1-10, key numbers, action summary), then narrative flow: Sleep -> Recovery -> Training -> Nutrition -> Supplementation, then "Why this matters" closing synthesis (PROT-04)
- **Visual style:** Full HTML email, traffic light color coding (green 8-10, yellow 5-7, red 1-4), "Stripe receipt" style (well-structured, clear typography, responsive mobile), no images/logos/graphics
- **Multipart:** HTML + plain-text fallback for Apple Watch and smart display compatibility
- **Resend integration:** Custom domain sender, sender name "BioIntelligence", subject format "Daily Protocol -- {date} -- Readiness: {score}/10"
- **Configuration:** RESEND_API_KEY, SENDER_EMAIL, RECIPIENT_EMAIL in .env via Settings class
- **Data freshness (SAFE-01):** Top banner below readiness dashboard for warnings (hidden when clean), last Garmin sync timestamp in footer
- **Failure notifications:** Deferred to Phase 5 -- Phase 4 only renders/sends when valid protocol exists
- **Tone:** Balanced, data-grounded but readable, action-first (from Phase 3 decision) -- template presents faithfully, no editorial layer

### Claude's Discretion
- HTML template implementation approach (inline CSS vs embedded styles for email client compatibility)
- Plain-text rendering logic from DailyProtocol fields
- Exact color hex values for traffic light indicators
- Footer content and layout
- Resend SDK error handling and retry strategy
- How to extract last sync timestamp from stored data

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PROT-01 | System produces unified Daily Protocol synthesizing all 5 domains into single coherent output | HTML renderer maps all 5 DailyProtocol sub-models (training, recovery, sleep, nutrition, supplementation) plus overall_summary into structured email sections |
| PROT-02 | Daily Protocol includes explanatory reasoning chains | Each domain sub-model has a `reasoning` field -- renderer includes reasoning text below each domain's recommendations |
| PROT-03 | Daily Protocol delivered via email using transactional email service | Resend Python SDK v2.23.0 with `resend.Emails.send()` API, multipart html+text, custom domain sender |
| PROT-04 | Daily Protocol includes "Why this matters" section | Render `overall_summary` field as the "Why this matters" closing synthesis section |
| SAFE-01 | Daily Protocol reports data freshness and alerts on missing/stale data | Render `data_quality_notes` field as top warning banner (hidden when null), extract last sync timestamp for footer |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| resend | 2.23.0 | Transactional email delivery API | User decision. Simple API (send with html+text params), automatic multipart MIME, Python SDK with type hints |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pydantic-settings | (existing) | RESEND_API_KEY, SENDER_EMAIL, RECIPIENT_EMAIL config | Extends existing Settings class |
| tenacity | (existing) | Retry on Resend API transient errors (429, 500) | Wraps `resend.Emails.send()` call |
| structlog | (existing) | Log send success/failure with email ID | All delivery module functions |
| html (stdlib) | - | Escape user-generated text in HTML templates | Prevent XSS in any dynamic content |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Resend | SendGrid, Postmark, AWS SES | User chose Resend -- locked decision |
| Inline CSS by hand | premailer/css-inline library | Adds dependency for auto-inlining. For a single template, hand-inlining inline CSS is simpler and avoids dependency. Recommended: hand-inline since template is static |
| Jinja2 templates | Python f-strings / string.Template | Jinja2 adds dependency for what is a single static template. Recommended: use Python f-strings or a simple function-based approach since template structure is fixed and known |

**Installation:**
```bash
uv add resend
```

## Architecture Patterns

### Recommended Project Structure
```
src/biointelligence/
  delivery/
    __init__.py         # Lazy imports: render_html, render_text, send_email, DeliveryResult
    renderer.py         # render_html(protocol, date) -> str, render_text(protocol, date) -> str
    sender.py           # send_email(html, text, subject, settings) -> DeliveryResult
  config.py             # Extended Settings with resend_api_key, sender_email, recipient_email
  pipeline.py           # New run_delivery(analysis_result, settings) -> DeliveryResult
  main.py               # New --deliver CLI flag
```

### Pattern 1: Pipeline Function (run_delivery)
**What:** A `run_delivery()` function following the `run_ingestion()` and `run_analysis()` pattern -- takes an AnalysisResult, renders email, sends via Resend, returns a Pydantic result model.
**When to use:** Every time a protocol needs to be emailed.
**Example:**
```python
# Source: Established pattern from pipeline.py (run_ingestion, run_analysis)
class DeliveryResult(BaseModel):
    """Result of a protocol delivery attempt."""
    date: date
    email_id: str | None = None
    success: bool
    error: str | None = None

def run_delivery(
    analysis_result: AnalysisResult, settings: Settings | None = None
) -> DeliveryResult:
    """Render and deliver the Daily Protocol email."""
    if settings is None:
        settings = get_settings()

    protocol = analysis_result.protocol
    html = render_html(protocol, analysis_result.date)
    text = render_text(protocol, analysis_result.date)
    subject = f"Daily Protocol \u2014 {analysis_result.date:%b %-d, %Y} \u2014 Readiness: {protocol.training.readiness_score}/10"

    return send_email(html=html, text=text, subject=subject, settings=settings)
```

### Pattern 2: HTML Renderer with Inline CSS
**What:** A pure function that takes a DailyProtocol and returns an HTML string. All CSS is inline on elements. Table-based layout for email client compatibility.
**When to use:** Converting DailyProtocol to HTML email body.
**Example:**
```python
# Source: HTML email best practices (table-based, inline CSS, 600px max-width)
def render_html(protocol: DailyProtocol, target_date: date) -> str:
    """Render DailyProtocol into a styled HTML email string."""
    readiness = protocol.training.readiness_score
    color = _readiness_color(readiness)  # green/yellow/red hex

    # Build sections using helper functions
    sections = [
        _render_readiness_dashboard(protocol, color),
        _render_data_quality_banner(protocol.data_quality_notes),
        _render_domain_section("Sleep", _render_sleep(protocol.sleep)),
        _render_domain_section("Recovery", _render_recovery(protocol.recovery)),
        _render_domain_section("Training", _render_training(protocol.training)),
        _render_domain_section("Nutrition", _render_nutrition(protocol.nutrition)),
        _render_domain_section("Supplementation", _render_supplementation(protocol.supplementation)),
        _render_why_this_matters(protocol.overall_summary),
        _render_footer(target_date),
    ]
    body = "\n".join(s for s in sections if s)  # skip None/empty
    return _wrap_html(body)
```

### Pattern 3: Resend SDK Wrapper with Tenacity Retry
**What:** A thin wrapper around `resend.Emails.send()` with tenacity retry for transient errors.
**When to use:** Sending the actual email.
**Example:**
```python
# Source: Resend API docs + existing tenacity pattern from analysis/client.py
import resend
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=4, max=60),
    retry=retry_if_exception_type(Exception),  # Resend SDK raises generic exceptions
)
def _send_via_resend(params: dict, api_key: str) -> str:
    """Send email via Resend and return the email ID."""
    resend.api_key = api_key
    response = resend.Emails.send(params)
    return response["id"]
```

### Pattern 4: Lazy Imports in __init__.py
**What:** `__getattr__` pattern for delivery package public API.
**When to use:** Matches existing `analysis/__init__.py` and `prompt/__init__.py` patterns.
**Example:**
```python
# Source: Established pattern from analysis/__init__.py
__all__ = ["render_html", "render_text", "send_email", "DeliveryResult"]

def __getattr__(name: str) -> object:
    if name in ("render_html", "render_text"):
        from biointelligence.delivery.renderer import render_html, render_text
        return render_html if name == "render_html" else render_text
    if name == "send_email":
        from biointelligence.delivery.sender import send_email
        return send_email
    if name == "DeliveryResult":
        from biointelligence.delivery.sender import DeliveryResult
        return DeliveryResult
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
```

### Anti-Patterns to Avoid
- **External CSS or `<style>` blocks as sole styling:** Gmail strips `<style>` tags from `<head>`. All critical styles MUST be inline on elements. An embedded `<style>` block in `<head>` can be used as progressive enhancement for clients that support it (e.g., media queries for mobile), but never as the only styling mechanism.
- **Using `<div>` for layout:** Email clients (especially Outlook/Word renderer) do not reliably support CSS box model. Use `<table>` with explicit `width`, `cellpadding`, `cellspacing`, `align`, `valign` attributes.
- **CSS shorthand properties:** Write `padding-top: 10px; padding-bottom: 10px;` not `padding: 10px 0;`. Some email clients do not parse shorthand correctly.
- **Setting `resend.api_key` at module level:** The API key should be set per-call or lazily, not at import time, to allow test isolation and settings override.
- **Hand-building MIME messages:** Resend handles multipart automatically when both `html` and `text` params are provided. Do not use Python's `email.mime` modules.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Multipart MIME construction | Manual MIMEMultipart assembly | Resend `html` + `text` params together | Resend automatically creates multipart/alternative MIME when both provided |
| Email delivery with retries | Custom SMTP client with retry loop | Resend SDK + tenacity | SMTP is complex (TLS, auth, bounce handling). Resend abstracts it all |
| CSS inlining automation | Custom CSS parser/inliner | Hand-inline (template is static) | Only one template -- a CSS inlining library is overkill |
| Domain verification | Manual DNS record management | Resend dashboard + user DNS setup | DKIM/SPF/DMARC records managed through Resend dashboard; user adds DNS records per their provider |
| Plain text from HTML | HTML-to-text converter library | Write dedicated `render_text()` function | The text version should be purpose-built for readability (Apple Watch), not an automated strip of HTML |

**Key insight:** Resend eliminates the entire SMTP/delivery complexity. The code only needs to render content and call one API endpoint. The real work is in the HTML template, not in email infrastructure.

## Common Pitfalls

### Pitfall 1: Gmail Stripping `<style>` Tags
**What goes wrong:** Styles defined in `<head>` `<style>` block are stripped by Gmail, leaving unstyled content.
**Why it happens:** Gmail's security model removes all `<style>` and `<link>` elements. Other clients (Apple Mail, Outlook on Mac) support them, creating inconsistent rendering.
**How to avoid:** Inline ALL critical styles on every element. Use `<style>` only for progressive enhancement (e.g., `@media` queries for responsive behavior on clients that support it).
**Warning signs:** Email looks good in Apple Mail but unstyled in Gmail.

### Pitfall 2: Outlook Word Rendering Engine
**What goes wrong:** Outlook on Windows uses Microsoft Word as its rendering engine, which does not support modern CSS (no `flexbox`, `grid`, `border-radius`, `max-width` via CSS).
**Why it happens:** Microsoft has used Word's HTML renderer for Outlook since 2007.
**How to avoid:** Use `<table>` layout with `width` attributes (not CSS `max-width`). Use `align` and `valign` HTML attributes instead of CSS equivalents. Test with conditional comments (`<!--[if mso]>`) for Outlook-specific fixes if needed. For this project, the user's inbox is known -- but multipart plain-text fallback covers edge cases.
**Warning signs:** Broken layout specifically in Outlook desktop.

### Pitfall 3: Resend API Key Exposure in Tests
**What goes wrong:** Tests accidentally call the real Resend API or fail because no API key is set.
**Why it happens:** `resend.api_key` is a module-level global in the Resend SDK. If set at import time, tests may inherit it.
**How to avoid:** Set `resend.api_key` inside the send function, not at module level. Mock `resend.Emails.send` in tests (same pattern as Anthropic client mocking in test_analysis.py). Use monkeypatch for env vars in test fixtures.
**Warning signs:** Tests making real HTTP calls or failing on missing env vars.

### Pitfall 4: Subject Line Character Encoding
**What goes wrong:** The em-dash (\u2014) in "Daily Protocol \u2014 {date}" could appear as garbage characters in some email clients.
**Why it happens:** Email subject lines have specific encoding rules (RFC 2047). Most modern clients handle UTF-8, but some older systems don't.
**How to avoid:** Resend handles subject line encoding automatically. No manual RFC 2047 encoding needed. If issues arise, fall back to ASCII en-dash (--) instead of em-dash.
**Warning signs:** Garbled characters in subject line on specific email clients.

### Pitfall 5: Missing Protocol Guard
**What goes wrong:** `run_delivery()` is called with an AnalysisResult where `protocol is None` (failed analysis), causing AttributeError.
**Why it happens:** Pipeline orchestration may call delivery even when analysis failed.
**How to avoid:** Guard at the top of `run_delivery()`: if `analysis_result.protocol is None` or `not analysis_result.success`, return a failed DeliveryResult immediately. Log a warning.
**Warning signs:** AttributeError on `None.training.readiness_score`.

### Pitfall 6: Data Quality Banner Always Showing
**What goes wrong:** An empty or whitespace-only `data_quality_notes` renders a visible but empty warning banner.
**Why it happens:** Template checks for `is not None` but not for empty/whitespace strings.
**How to avoid:** Check `if protocol.data_quality_notes and protocol.data_quality_notes.strip()`. Only render the banner when there is meaningful content.
**Warning signs:** Empty yellow/orange box at the top of the email on clean data days.

## Code Examples

### Resend Send Email (Multipart HTML + Text)
```python
# Source: Resend API docs (https://resend.com/docs/api-reference/emails/send-email)
import resend

resend.api_key = "re_..."

params: resend.Emails.SendParams = {
    "from": "BioIntelligence <protocol@yourdomain.com>",
    "to": ["user@example.com"],
    "subject": "Daily Protocol \u2014 Mar 3, 2026 \u2014 Readiness: 7/10",
    "html": "<html>...<p>Your HTML email</p>...</html>",
    "text": "Your plain text fallback for Apple Watch / smart displays",
}

response = resend.Emails.send(params)
# response = {"id": "49a3999c-0ce1-4ea6-ab68-afcd6dc2e794"}
email_id = response["id"]
```

### Traffic Light Color Function
```python
# Source: User decision (green 8-10, yellow 5-7, red 1-4)
def _readiness_color(score: int) -> str:
    """Return hex color for readiness score traffic light."""
    if score >= 8:
        return "#22c55e"  # green-500
    if score >= 5:
        return "#eab308"  # yellow-500
    return "#ef4444"       # red-500

def _readiness_label(score: int) -> str:
    """Return text label for readiness score."""
    if score >= 8:
        return "High Readiness"
    if score >= 5:
        return "Moderate Readiness"
    return "Low Readiness"
```

### HTML Email Wrapper (Table-Based, 600px)
```python
# Source: HTML email best practices (table layout, inline styles, 600px width)
def _wrap_html(body_content: str) -> str:
    """Wrap email body in standard HTML email structure."""
    return f"""\
<!DOCTYPE html>
<html lang="en" xmlns="http://www.w3.org/1999/xhtml">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <title>Daily Protocol</title>
    <!--[if mso]>
    <noscript>
        <xml>
            <o:OfficeDocumentSettings>
                <o:PixelsPerInch>96</o:PixelsPerInch>
            </o:OfficeDocumentSettings>
        </xml>
    </noscript>
    <![endif]-->
</head>
<body style="margin: 0; padding: 0; background-color: #f4f4f5; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
    <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="background-color: #f4f4f5;">
        <tr>
            <td align="center" style="padding: 24px 16px;">
                <table role="presentation" cellpadding="0" cellspacing="0" width="600" style="background-color: #ffffff; border-radius: 8px; overflow: hidden;">
                    {body_content}
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""
```

### Plain Text Renderer (Purpose-Built for Apple Watch)
```python
# Source: Project requirement for multipart email with readable plain-text
def render_text(protocol: DailyProtocol, target_date: date) -> str:
    """Render DailyProtocol as plain text for Apple Watch and text-only clients."""
    lines = [
        f"DAILY PROTOCOL \u2014 {target_date:%B %-d, %Y}",
        f"Readiness: {protocol.training.readiness_score}/10",
        "",
    ]

    if protocol.data_quality_notes and protocol.data_quality_notes.strip():
        lines.extend(["DATA QUALITY", protocol.data_quality_notes, ""])

    lines.extend([
        "SLEEP", protocol.sleep.quality_assessment, protocol.sleep.reasoning, "",
        "RECOVERY", protocol.recovery.recovery_status, protocol.recovery.reasoning, "",
        "TRAINING", f"Intensity: {protocol.training.recommended_intensity}",
        f"Type: {protocol.training.recommended_type}",
        f"Duration: {protocol.training.recommended_duration_minutes}min",
        protocol.training.reasoning, "",
        "NUTRITION", f"Calories: {protocol.nutrition.caloric_target}",
        protocol.nutrition.reasoning, "",
        "SUPPLEMENTATION",
        *protocol.supplementation.adjustments,
        protocol.supplementation.reasoning, "",
        "WHY THIS MATTERS", protocol.overall_summary, "",
    ])

    return "\n".join(lines)
```

### Settings Extension
```python
# Source: Existing config.py pattern (pydantic-settings)
class Settings(BaseSettings):
    # ... existing fields ...

    # Resend (delivery)
    resend_api_key: str = ""
    sender_email: str = ""
    recipient_email: str = ""
```

### CLI --deliver Flag
```python
# Source: Existing --analyze pattern from main.py
parser.add_argument(
    "--deliver",
    action="store_true",
    default=False,
    help="Send protocol email after analysis (requires RESEND_API_KEY)",
)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| SMTP with smtplib | Transactional email APIs (Resend, SendGrid) | 2023+ | No SMTP server management, built-in deliverability, tracking |
| CSS in `<style>` block | Inline CSS on all elements | Always for email | Gmail compatibility -- unchanged requirement |
| Jinja2 templates for email | Function-based rendering | N/A (project choice) | For a single known template, functions are simpler than a template engine |
| Resend Python SDK 1.x | Resend Python SDK 2.x (2.23.0) | 2024 | Added type hints (`SendParams`, `SendResponse`), improved API |

**Deprecated/outdated:**
- Resend SDK 1.x: Replaced by 2.x with type hints and improved API. Use `resend.Emails.SendParams` for typed params.
- `from` parameter key: In Python dicts, use `"from"` as string key (not `from_` -- that is only needed in keyword arguments).

## Open Questions

1. **Last Garmin Sync Timestamp**
   - What we know: The `DailyMetrics.raw_data` dict contains the full Garmin API response, which likely includes timestamps. The `daily_metrics` table stores this in Supabase.
   - What's unclear: The exact field path for the "last sync" timestamp in Garmin's response varies by endpoint. It could be derived from the ingestion pipeline's execution time stored in Supabase, or from a timestamp within the raw_data.
   - Recommendation: Use the `updated_at` timestamp from the `daily_metrics` Supabase row (if the table has such a column), or derive it from the ingestion run time. If neither exists, use `{target_date} (ingested {today})` as a pragmatic approximation. This is a Claude's Discretion item.

2. **DailyProtocol "Why This Matters" Field Mapping**
   - What we know: The current `DailyProtocol` model has `overall_summary: str` and no dedicated `why_this_matters` field. The user wants a "Why this matters" section after all 5 domains.
   - What's unclear: Whether `overall_summary` is sufficient or if a new field is needed.
   - Recommendation: Render `overall_summary` as the "Why this matters" section. The prompt already asks Claude to provide an overall synthesis. No model change needed -- the renderer just labels it "Why This Matters" in the email.

3. **Resend Free Tier Daily Limit**
   - What we know: Resend has daily quotas for free plan users (exact number not documented publicly). Rate limit is 2 requests/second.
   - What's unclear: The exact daily email limit for the free tier.
   - Recommendation: For a single daily email use case, any Resend plan (including free) is more than sufficient. The user is configuring a custom domain, which may require a paid plan anyway.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest with pytest-mock |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/ -x -q` |
| Full suite command | `uv run pytest tests/ -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PROT-01 | render_html produces HTML with all 5 domain sections | unit | `uv run pytest tests/test_renderer.py::TestRenderHtml -x` | Wave 0 |
| PROT-02 | Each domain section includes reasoning text | unit | `uv run pytest tests/test_renderer.py::TestRenderHtml::test_includes_reasoning -x` | Wave 0 |
| PROT-03 | send_email calls Resend API with correct params | unit | `uv run pytest tests/test_sender.py::TestSendEmail -x` | Wave 0 |
| PROT-03 | run_delivery orchestrates render + send | unit | `uv run pytest tests/test_pipeline.py::TestRunDelivery -x` | Wave 0 |
| PROT-04 | HTML includes "Why this matters" from overall_summary | unit | `uv run pytest tests/test_renderer.py::TestRenderHtml::test_why_this_matters -x` | Wave 0 |
| SAFE-01 | Data quality banner shown when data_quality_notes present | unit | `uv run pytest tests/test_renderer.py::TestDataQualityBanner -x` | Wave 0 |
| SAFE-01 | Data quality banner hidden when notes are None/empty | unit | `uv run pytest tests/test_renderer.py::TestDataQualityBanner::test_hidden_when_clean -x` | Wave 0 |
| SAFE-01 | Footer includes data timestamp | unit | `uv run pytest tests/test_renderer.py::TestRenderHtml::test_footer_timestamp -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/ -x -q`
- **Per wave merge:** `uv run pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_renderer.py` -- covers PROT-01, PROT-02, PROT-04, SAFE-01 (HTML + text rendering)
- [ ] `tests/test_sender.py` -- covers PROT-03 (Resend SDK integration, mocked)
- [ ] New test cases in `tests/test_pipeline.py` -- covers run_delivery pipeline function
- [ ] `resend` package install: `uv add resend`

## Sources

### Primary (HIGH confidence)
- Resend API reference (https://resend.com/docs/api-reference/emails/send-email) -- send email parameters, multipart support, response format, idempotency
- Resend Python SDK docs (https://resend.com/docs/send-with-python) -- installation, basic usage, API key setup
- Resend rate limits (https://resend.com/docs/api-reference/rate-limit) -- 2 req/sec default, 429 handling, retry-after header
- Existing codebase: pipeline.py, config.py, analysis/client.py, prompt/models.py -- established patterns
- PyPI resend package (https://pypi.org/project/resend/) -- version 2.23.0, Python >=3.7

### Secondary (MEDIUM confidence)
- HTML email best practices (https://www.francescatabor.com/articles/2025/12/12/why-inline-css-is-still-essential-for-html-emails) -- inline CSS requirement verified across sources
- Email client compatibility guide (https://email-dev.com/the-complete-guide-to-email-client-compatibility-in-2025/) -- table layout, Outlook Word engine
- HTML and CSS in emails 2026 (https://designmodo.com/html-css-emails/) -- current state of email rendering

### Tertiary (LOW confidence)
- Resend free tier exact daily limit -- not documented publicly, assumed sufficient for 1 email/day

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- Resend SDK is well-documented, user chose it, version verified on PyPI
- Architecture: HIGH -- follows established project patterns exactly (pipeline functions, Settings, tenacity, structlog)
- Email rendering: HIGH -- inline CSS + table layout is universally accepted best practice, verified across multiple 2025/2026 sources
- Pitfalls: HIGH -- Gmail style stripping and Outlook Word engine are well-documented, long-standing issues
- Data freshness implementation: MEDIUM -- `data_quality_notes` field exists; sync timestamp extraction approach needs validation during implementation

**Research date:** 2026-03-03
**Valid until:** 2026-04-03 (Resend SDK stable, email rendering best practices change slowly)
