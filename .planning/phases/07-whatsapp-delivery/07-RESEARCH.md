# Phase 7: WhatsApp Delivery - Research

**Researched:** 2026-03-04
**Domain:** WhatsApp Cloud API integration, message rendering, delivery pipeline modification
**Confidence:** HIGH

## Summary

Phase 7 replaces email as the primary Daily Protocol delivery channel with WhatsApp messages via Meta's WhatsApp Cloud API. The implementation requires four new components: a WhatsApp-specific renderer that transforms the DailyProtocol into mobile-friendly formatted text with emoji headers and WhatsApp formatting markers, a WhatsApp sender that POSTs to the Meta Cloud API endpoint, pipeline modifications to try WhatsApp first with email fallback, and Settings extensions for three new environment variables.

The architecture is straightforward: direct HTTP calls via httpx (already a transitive dependency) to `https://graph.facebook.com/v21.0/{phone_number_id}/messages`, using a pre-approved template message with a single body variable containing the formatted protocol text. The critical constraint is the template body character limit -- template bodies are capped at 1,024 characters when headers/footers are included, but up to 32,768 characters when the body is the only component. The template should be created as body-only to maximize available space. A condensed Daily Protocol will likely be 800-1,500 characters, so body-only templates provide ample room.

**Primary recommendation:** Create a body-only template named "daily_protocol" with a single `{{1}}` variable, render the full protocol into WhatsApp-formatted text using emoji headers and `*bold*` formatting, send via httpx POST with tenacity retry matching the existing Resend sender pattern, and modify `run_delivery()` to try WhatsApp first then fall back to email on failure.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- WhatsApp via Meta's WhatsApp Cloud API (direct HTTP, not Twilio or third-party wrapper)
- Meta Business account needed -- starting from scratch, verification done separately
- Build and test with Meta's test phone number first; production requires Meta Business Verification
- Full protocol condensed for mobile -- all 5 domains included, not just TL;DR
- Same domain order as email: Sleep -> Recovery -> Training -> Nutrition -> Supplementation
- Emoji headers + bold keys for visual structure (e.g., "sleeping *Sleep*\nQuality: Good\n...")
- WhatsApp formatting: *bold* for section names and key labels, plain text for values
- Include 1-2 sentence trimmed reasoning per domain
- Alert banners (from Phase 6) rendered as prominent text blocks at message top
- "Why This Matters" synthesis section included at the end
- Readiness score prominent at the top of the message
- WhatsApp replaces email as the primary delivery channel (not alongside)
- Email is the automatic fallback: if WhatsApp send fails after retries, fall back to email delivery via Resend
- Same timing as current pipeline -- message sent during the existing 7 AM CET GitHub Actions run
- No separate scheduling or delivery time configuration in this phase
- Fire-and-forget: log API response (message ID + success/fail), no webhook callbacks
- Direct HTTP calls using httpx (already a project dependency) -- no third-party WhatsApp library
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

### Deferred Ideas (OUT OF SCOPE)
- Interactive WhatsApp bot for follow-up questions about the protocol -- separate phase
- Telegram as alternative channel (DLVR-03 in v2 requirements) -- consider if WhatsApp verification proves blocking
- Rich media attachments (charts, trend graphs) in WhatsApp messages -- future enhancement
- WhatsApp delivery status tracking via webhooks -- adds complexity for minimal value in single-user tool
- Delivery time configuration from onboarding (Phase 8) -- scheduling stays at pipeline run time for now
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| WHTS-01 | Daily Protocol delivered via WhatsApp message formatted for mobile readability (concise sections, WhatsApp-native formatting) | WhatsApp supports *bold*, _italic_, ~strikethrough~, and list formatting. Emoji headers + bold keys pattern maps directly to these. Template body-only mode allows up to 32,768 chars. |
| WHTS-02 | WhatsApp delivery operates alongside email -- user selects preferred channel | CONTEXT.md overrides this: WhatsApp replaces email as primary, email becomes automatic fallback on failure. Pipeline `run_delivery()` modified for try/fallback pattern. |
| WHTS-03 | Message delivery confirmed via API status callbacks; failure triggers fallback to email | CONTEXT.md simplifies this: fire-and-forget with API response logging (message_id + success/fail). No webhook callbacks. Email fallback triggered by API send failure, not delivery status. |
| WHTS-04 | Delivery timing configurable based on user preference | CONTEXT.md defers this: same timing as current pipeline (7 AM CET GitHub Actions run). No delivery time configuration in this phase. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| httpx | 0.28.1 | HTTP POST to WhatsApp Cloud API | Already a transitive dependency (via supabase, anthropic). Modern async-capable HTTP client. |
| tenacity | (existing) | Retry logic for API calls | Already used for Resend sender -- same pattern for WhatsApp sender |
| pydantic | (existing) | DeliveryResult model extension | Already used throughout for all data structures |
| pydantic-settings | (existing) | Settings extension with WhatsApp env vars | Already used for all configuration |
| structlog | (existing) | Structured logging for send success/failure | Already used throughout for all logging |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| N/A | - | - | No new dependencies needed |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| httpx direct | python-whatsapp-cloud (pywa) | Adds dependency for a single POST call -- overkill for this use case |
| httpx direct | requests | httpx already available as transitive dep, requests would add a new dep |

**Installation:**
```bash
# httpx is already available as transitive dependency -- add as explicit if needed
uv add httpx
```

Note: httpx is currently a transitive dependency via supabase and anthropic (version 0.28.1 in uv.lock). If adding it as an explicit dependency is desired for clarity, do so. Otherwise, it is already importable.

## Architecture Patterns

### Recommended Project Structure
```
src/biointelligence/
├── delivery/
│   ├── __init__.py           # Extend lazy imports with whatsapp exports
│   ├── renderer.py           # Existing HTML + text renderers (unchanged)
│   ├── sender.py             # Existing Resend email sender (unchanged)
│   ├── whatsapp_renderer.py  # NEW: WhatsApp-formatted text renderer
│   └── whatsapp_sender.py    # NEW: WhatsApp Cloud API sender
├── config.py                 # Extend Settings with 3 WhatsApp fields
└── pipeline.py               # Modify run_delivery() for WhatsApp-first + email fallback
```

### Pattern 1: WhatsApp Sender (mirrors existing email sender)
**What:** A `send_whatsapp()` function that mirrors `send_email()` -- accepts rendered content, calls the API with tenacity retry, returns a `DeliveryResult`.
**When to use:** Every WhatsApp delivery attempt.
**Example:**
```python
# Pattern modeled after existing sender.py
import httpx
import structlog
from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from biointelligence.config import Settings
from biointelligence.delivery.sender import DeliveryResult

log = structlog.get_logger()

WHATSAPP_API_URL = "https://graph.facebook.com/v21.0/{phone_number_id}/messages"


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=4, max=60),
    retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TransportError)),
)
def _send_via_whatsapp(url: str, headers: dict, payload: dict) -> dict:
    """POST to WhatsApp Cloud API with tenacity retry on transient errors."""
    response = httpx.post(url, headers=headers, json=payload, timeout=30.0)
    response.raise_for_status()
    return response.json()


def send_whatsapp(
    body_text: str,
    target_date: date,
    settings: Settings,
) -> DeliveryResult:
    """Send a WhatsApp template message via Meta Cloud API."""
    url = WHATSAPP_API_URL.format(phone_number_id=settings.whatsapp_phone_number_id)
    headers = {
        "Authorization": f"Bearer {settings.whatsapp_access_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": settings.whatsapp_recipient_phone,
        "type": "template",
        "template": {
            "name": "daily_protocol",
            "language": {"code": "en"},
            "components": [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": body_text},
                    ],
                },
            ],
        },
    }
    try:
        response = _send_via_whatsapp(url, headers, payload)
        message_id = response.get("messages", [{}])[0].get("id", "unknown")
        log.info("whatsapp_sent", date=target_date.isoformat(), message_id=message_id)
        return DeliveryResult(date=target_date, email_id=message_id, success=True)
    except RetryError as e:
        cause = e.last_attempt.exception() if e.last_attempt else e
        error_msg = str(cause) if cause else str(e)
        log.error("whatsapp_send_failed", date=target_date.isoformat(), error=error_msg)
        return DeliveryResult(date=target_date, success=False, error=error_msg)
    except Exception as e:
        log.error("whatsapp_send_failed", date=target_date.isoformat(), error=str(e))
        return DeliveryResult(date=target_date, success=False, error=str(e))
```

### Pattern 2: WhatsApp Renderer (adapts existing render_text pattern)
**What:** A `render_whatsapp()` function that produces WhatsApp-formatted text from DailyProtocol. Uses emoji headers, `*bold*` for section names and key labels, condensed reasoning.
**When to use:** Before every WhatsApp send.
**Example:**
```python
def render_whatsapp(protocol: DailyProtocol, target_date: date) -> str:
    """Render DailyProtocol as WhatsApp-formatted text.

    Uses emoji headers, *bold* keys, condensed reasoning for mobile readability.
    """
    lines: list[str] = []

    # Readiness score at top
    score = protocol.training.readiness_score
    lines.append(f"*Daily Protocol* -- {target_date:%B %-d, %Y}")
    lines.append(f"Readiness: *{score}/10*")
    lines.append("")

    # Alert banners at top (if any)
    if protocol.alerts:
        for alert in protocol.alerts:
            severity = alert.severity.value.upper()
            lines.append(f"*[{severity}] {alert.title}*")
            lines.append(f"{alert.description}")
            lines.append(f"Action: {alert.suggested_action}")
            lines.append("")

    # Domain sections with emoji headers
    # Sleep
    lines.append("sleeping *Sleep*")
    lines.append(f"*Quality:* {protocol.sleep.quality_assessment}")
    lines.append(f"*Architecture:* {protocol.sleep.architecture_notes}")
    lines.append(f"{_trim_reasoning(protocol.sleep.reasoning)}")
    lines.append("")

    # ... (Recovery, Training, Nutrition, Supplementation follow same pattern)

    # Why This Matters
    lines.append("*Why This Matters*")
    lines.append(protocol.overall_summary)

    return "\n".join(lines)
```

### Pattern 3: Try/Fallback Pipeline Delivery
**What:** Modify `run_delivery()` to try WhatsApp first, then fall back to email if WhatsApp fails.
**When to use:** Always -- this replaces the current email-only delivery.
**Example:**
```python
def run_delivery(
    analysis_result: AnalysisResult, settings: Settings | None = None
) -> DeliveryResult:
    # ... existing guard checks ...

    # Try WhatsApp first (if configured)
    if settings.whatsapp_access_token:
        whatsapp_text = render_whatsapp(protocol, target_date)
        result = send_whatsapp(whatsapp_text, target_date, settings)
        if result.success:
            return result
        log.warning("whatsapp_failed_falling_back_to_email",
                    date=target_date.isoformat(), error=result.error)

    # Fallback to email
    html_content = render_html(protocol, target_date)
    text_content = render_text(protocol, target_date)
    subject = build_subject(protocol, target_date)
    return send_email(html=html_content, text=text_content, subject=subject,
                      target_date=target_date, settings=settings)
```

### Anti-Patterns to Avoid
- **Sending free-form text messages instead of templates:** Business-initiated messages outside the 24-hour customer window MUST use pre-approved templates. A template with a single body variable is the correct approach.
- **Hardcoding the access token:** The WhatsApp access token must come from Settings/environment variables, not be hardcoded. It also expires (temporary tokens last 24 hours; permanent system user tokens should be used for production).
- **Importing httpx at module level without guarding:** Since WhatsApp is optional (email fallback exists), the import is fine at module level in the whatsapp_sender module, but Settings fields should default to empty strings so the app works without WhatsApp configured.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP retry logic | Custom retry/backoff loop | tenacity (already in project) | Consistent with existing Resend sender pattern |
| JSON serialization for API call | Manual string building | httpx `json=` parameter | Handles Content-Type header and encoding automatically |
| Environment variable loading | os.environ lookups | pydantic-settings (already in project) | Consistent with existing Settings pattern, type validation |
| WhatsApp message formatting | HTML-to-text conversion | Purpose-built WhatsApp renderer | WhatsApp uses its own formatting syntax (*bold*, _italic_), not HTML |

**Key insight:** The entire WhatsApp integration is essentially two small modules (renderer + sender) that follow patterns already established in the codebase. The sender mirrors `sender.py`, the renderer adapts `render_text()`, and the pipeline modification is a small try/fallback wrapper.

## Common Pitfalls

### Pitfall 1: Template Body Character Limit
**What goes wrong:** Template body exceeds 1,024 characters, API rejects the message.
**Why it happens:** The 1,024 character limit applies when the template includes header, footer, or button components. A body-only template allows up to 32,768 characters.
**How to avoid:** Create the "daily_protocol" template with ONLY a body component (no header, footer, or buttons). Guard in code with a character count check and truncation/warning if approaching the limit. A condensed protocol with trimmed reasoning should fit within 2,000-3,000 characters comfortably.
**Warning signs:** API error 132001 (template parameter format mismatch) or message truncation.

### Pitfall 2: Token Expiration
**What goes wrong:** The WhatsApp access token expires, all sends fail.
**Why it happens:** Temporary tokens from the Meta developer dashboard expire after 24 hours. Production requires a System User Token which does not expire (unless revoked).
**How to avoid:** For development, use the temporary token and re-generate as needed. For production (GitHub Actions), create a System User in Meta Business Manager and generate a permanent access token. Document this setup step clearly.
**Warning signs:** HTTP 401 responses from the API. The tenacity retry will waste time retrying auth errors.

### Pitfall 3: Retrying Non-Retryable Errors
**What goes wrong:** Tenacity retries on errors that will never succeed (auth errors, invalid template, etc.), wasting time and delaying the email fallback.
**Why it happens:** Blanket `retry_if_exception_type(Exception)` catches everything.
**How to avoid:** Classify Meta API errors:
- **Retryable (transient):** HTTP 429 (rate limit), HTTP 500/503 (server error), network timeout, error code 130429 (throughput limit)
- **Non-retryable (permanent):** HTTP 401 (auth), HTTP 400 (bad request), error code 132001 (template not found), error code 131026 (recipient not opted in)
**Implementation:** Retry only on `httpx.TransportError` and check HTTP status codes -- retry on 429/5xx, fail immediately on 4xx (except 429).

### Pitfall 4: WhatsApp Formatting in Template Variables
**What goes wrong:** WhatsApp formatting markers (*bold*, _italic_) don't render in template variable content.
**Why it happens:** Some template implementations strip formatting from variable values.
**How to avoid:** Test with the actual template. If formatting in variables is stripped, the template body itself should contain the static structure with formatting, and variables should contain only the dynamic data values. Alternatively, use a template where the body text IS the variable (single `{{1}}`), which preserves formatting in the injected text.
**Warning signs:** Messages appear as plain text without any formatting.

### Pitfall 5: Phone Number Format
**What goes wrong:** API rejects the recipient phone number.
**Why it happens:** WhatsApp requires international format without + or leading zeros (e.g., "4915123456789" not "+49 151 23456789").
**How to avoid:** Store WHATSAPP_RECIPIENT_PHONE in the correct format. Add a validation/normalization step that strips +, spaces, and leading zeros from country code.
**Warning signs:** API error about invalid phone number format.

### Pitfall 6: DeliveryResult Model Reuse
**What goes wrong:** The `email_id` field name is semantically wrong for WhatsApp message IDs.
**Why it happens:** DeliveryResult was designed for email delivery only.
**How to avoid:** Reuse DeliveryResult as-is (the field stores a string identifier regardless of channel). The `email_id` field name is slightly misleading but functionally correct. Renaming would require updating all existing email tests and callers -- not worth the churn for a single-user tool. If desired, add an optional `channel` field to distinguish "whatsapp" vs "email" in logs.

## Code Examples

Verified patterns from official sources and existing codebase:

### WhatsApp Cloud API POST Request
```python
# Source: Meta WhatsApp Cloud API documentation
# POST https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages

import httpx

url = f"https://graph.facebook.com/v21.0/{phone_number_id}/messages"
headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json",
}
payload = {
    "messaging_product": "whatsapp",
    "to": "4915123456789",  # International format, no + prefix
    "type": "template",
    "template": {
        "name": "daily_protocol",
        "language": {"code": "en"},
        "components": [
            {
                "type": "body",
                "parameters": [
                    {"type": "text", "text": "Your formatted protocol text here..."},
                ],
            },
        ],
    },
}

response = httpx.post(url, headers=headers, json=payload, timeout=30.0)
response.raise_for_status()
result = response.json()
# result = {"messaging_product": "whatsapp", "contacts": [...], "messages": [{"id": "wamid.xxx"}]}
message_id = result["messages"][0]["id"]
```

### WhatsApp API Success Response
```json
{
  "messaging_product": "whatsapp",
  "contacts": [
    {"input": "4915123456789", "wa_id": "4915123456789"}
  ],
  "messages": [
    {"id": "wamid.HBgLMTU1NTU1NTU1NTUFBgIYFBgJQjFBRTI3MjYxOQA="}
  ]
}
```

### WhatsApp Text Formatting Syntax
```
# Bold: wrap in asterisks
*Bold text*

# Italic: wrap in underscores
_Italic text_

# Strikethrough: wrap in tildes
~Strikethrough~

# Bulleted list: dash prefix
- Item one
- Item two

# Combining: bold + italic
*_Bold italic_*
```

### WhatsApp Renderer Output Example
```
*Daily Protocol* -- March 4, 2026
Readiness: *7/10*

*[WARNING] HRV Declining Trend*
HRV has been declining for 3 consecutive days.
Action: Consider reducing training intensity today.

sleeping *Sleep*
*Quality:* Good sleep quality with adequate deep sleep.
*Architecture:* Deep 1h42m (22%), REM 1h28m (19%).
Sleep score 82 supports training today.

green_heart *Recovery*
*Status:* Well recovered
*HRV:* 48ms, above 7-day average of 44ms.
*Body Battery:* Morning 72, good energy reserves.
Multi-metric convergence shows solid recovery.

fire *Training*
*Intensity:* Zone 2
*Type:* Cycling
*Duration:* 75 min
*Load:* Acute load within optimal range.
HRV above baseline, body battery 72.

plate_with_cutlery *Nutrition*
*Calories:* 2,800 kcal
*Macros:* Higher carb pre-ride, moderate protein.
*Hydration:* 3.2L including 500ml electrolyte.
Zone 2 cycling requires moderate fueling.

pill *Supplementation*
- Creatine 5g with breakfast
- Vitamin D 4000IU with lunch
*Timing:* Magnesium glycinate 400mg 1h before bed.

*Why This Matters*
Good day for a moderate Zone 2 ride. Recovery metrics look solid.
```

### Settings Extension
```python
# Source: Existing config.py pattern
class Settings(BaseSettings):
    # ... existing fields ...

    # WhatsApp (delivery)
    whatsapp_access_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_recipient_phone: str = ""
```

### httpx Error Handling with Retry Classification
```python
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential
import httpx

def _is_retryable(exc: BaseException) -> bool:
    """Classify whether an httpx error is retryable."""
    if isinstance(exc, httpx.TransportError):
        return True  # Network errors are always retryable
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in (429, 500, 502, 503, 504)
    return False

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=4, max=60),
    retry=retry_if_exception(_is_retryable),
)
def _send_via_whatsapp(url: str, headers: dict, payload: dict) -> dict:
    response = httpx.post(url, headers=headers, json=payload, timeout=30.0)
    response.raise_for_status()
    return response.json()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| WhatsApp Business API (on-premise) | WhatsApp Cloud API (Meta-hosted) | 2022 | No server infrastructure needed, direct HTTP calls |
| Separate auth per request | System User permanent tokens | 2023 | No token refresh needed for production |
| Twilio/third-party wrappers | Direct Meta API calls | Current | Lower cost, fewer dependencies, full control |
| Free-form messages | Template messages (required for business-initiated) | Always | Must pre-approve templates, but supports variables |

**Deprecated/outdated:**
- WhatsApp Business API (self-hosted): Still works but Cloud API is the recommended path for new integrations
- Temporary access tokens for production: Use System User tokens instead (no expiry)

## Open Questions

1. **Template Body Character Limit -- Body-Only vs With Components**
   - What we know: 1,024 chars with header/footer, some sources suggest up to 32,768 for body-only templates
   - What's unclear: The exact limit for body-only templates (sources conflict between 1,024 and 32,768)
   - Recommendation: Create body-only template (no header/footer/buttons). Test with actual content length. Implement a character count guard at 1,024 as a safe minimum, with a configurable ceiling. If 1,024 is the actual hard limit, the renderer must aggressively trim reasoning text to fit.

2. **WhatsApp Formatting in Template Variable Content**
   - What we know: WhatsApp supports *bold*, _italic_, ~strikethrough~ in regular messages
   - What's unclear: Whether formatting markers in template variable values are preserved when rendered
   - Recommendation: Test with the actual template during development. If formatting is stripped, restructure to use a plain-text variable and rely on the template body itself for structure.

3. **System User Token for Production**
   - What we know: Temporary tokens expire after 24 hours. System User tokens are permanent.
   - What's unclear: Exact steps to create a System User token without full Meta Business Verification
   - Recommendation: Start with temporary token for development/testing. Document the System User token creation process. This is an operational concern, not a code concern -- the code just reads WHATSAPP_ACCESS_TOKEN from env.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-mock |
| Config file | pyproject.toml [tool.pytest.ini_options] |
| Quick run command | `uv run pytest tests/ -x -q` |
| Full suite command | `uv run pytest tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| WHTS-01 | WhatsApp renderer produces formatted text with emoji headers, bold keys, all 5 domains | unit | `uv run pytest tests/test_whatsapp_renderer.py -x` | No -- Wave 0 |
| WHTS-01 | Alerts rendered at message top | unit | `uv run pytest tests/test_whatsapp_renderer.py::TestRenderWhatsappAlerts -x` | No -- Wave 0 |
| WHTS-02 | Pipeline tries WhatsApp first, falls back to email on failure | unit | `uv run pytest tests/test_pipeline.py::TestRunDeliveryWhatsApp -x` | No -- Wave 0 |
| WHTS-03 | WhatsApp sender calls Meta API with correct payload, returns DeliveryResult | unit | `uv run pytest tests/test_whatsapp_sender.py -x` | No -- Wave 0 |
| WHTS-03 | WhatsApp sender retries on transient errors, fails on permanent errors | unit | `uv run pytest tests/test_whatsapp_sender.py::TestRetryClassification -x` | No -- Wave 0 |
| WHTS-04 | Settings loads WHATSAPP_* env vars with empty string defaults | unit | `uv run pytest tests/test_whatsapp_sender.py::TestSettingsWhatsApp -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/ -x -q`
- **Per wave merge:** `uv run pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_whatsapp_renderer.py` -- covers WHTS-01 (WhatsApp formatting, emoji headers, domain order, alerts, character length)
- [ ] `tests/test_whatsapp_sender.py` -- covers WHTS-03 (API call, retry logic, error handling, Settings fields)
- [ ] `tests/test_pipeline.py` additions -- covers WHTS-02 (WhatsApp-first delivery with email fallback)

## Sources

### Primary (HIGH confidence)
- Existing codebase: `delivery/sender.py`, `delivery/renderer.py`, `pipeline.py`, `config.py` -- established patterns for sender/renderer/pipeline/settings
- Existing codebase: `pyproject.toml`, `uv.lock` -- httpx 0.28.1 available as transitive dependency
- WhatsApp Cloud API endpoint format: `POST https://graph.facebook.com/v21.0/{phone_number_id}/messages` -- confirmed across multiple sources

### Secondary (MEDIUM confidence)
- [Chatarmin - WhatsApp API Send Message Guide 2026](https://chatarmin.com/en/blog/whats-app-api-send-messages) -- Python code examples, JSON payload structure, character limits
- [GuruSup - WhatsApp API Message Templates Guide 2026](https://gurusup.com/blog/whatsapp-api-message-templates) -- Template structure, variable formats, character limits
- [Heltar - Meta WhatsApp Cloud API Error Codes 2025](https://www.heltar.com/blogs/all-meta-error-codes-explained-along-with-complete-troubleshooting-guide-2025-cm69x5e0k000710xtwup66500) -- Error classification (retryable vs permanent)
- [WhatsApp Help Center - Text Formatting](https://faq.whatsapp.com/539178204879377/) -- Official formatting syntax (*bold*, _italic_, etc.)
- [SleekFlow - Supported Message Types](https://help.sleekflow.io/en_US/supported-message-types-on-whatsapp-business-api-cloud-a) -- Character limits, formatting support

### Tertiary (LOW confidence)
- 32,768 character limit for body-only templates -- mentioned in one source, contradicted by others citing 1,024 universal limit. Needs validation with actual template creation.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, all patterns established in codebase
- Architecture: HIGH -- direct mirror of existing sender/renderer pattern
- WhatsApp API format: HIGH -- confirmed across multiple sources
- Character limits: MEDIUM -- template body limit has conflicting information (1,024 vs 32,768 for body-only)
- Error classification: MEDIUM -- based on community sources, not official docs (developers.facebook.com was unreachable)
- Formatting in variables: LOW -- needs actual testing to confirm

**Research date:** 2026-03-04
**Valid until:** 2026-04-04 (stable API, unlikely to change within 30 days)
