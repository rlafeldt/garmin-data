# BioIntelligence

## What This Is

A personal AI health agent that reads daily Garmin biometric data — HRV, Body Battery, training load, sleep stages, stress, VO2 max, respiration rate, SpO2 — interprets it through the lens of sports science and a personal health profile, and delivers a Daily Protocol via email with actionable recommendations across training, recovery, sleep, nutrition, and supplementation.

## Core Value

Every morning, receive a single coherent Daily Protocol that tells you exactly what to do today based on your Garmin data, health profile, and recent trends — bridging the gap between raw biometric numbers and actionable decisions.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Automated daily Garmin data pull (training, recovery, sleep, stress, general metrics)
- [ ] Static health profile via config file (biometrics, goals, medical context, labs, diet, supplements, sleep context)
- [ ] Time-series data storage in Supabase for historical tracking
- [ ] Single-prompt Claude API analysis across 5 domains (training, recovery, sleep, nutrition, supplementation)
- [ ] Trend analysis — feed rolling history window into prompt for longitudinal pattern detection
- [ ] Daily Protocol generation with structured recommendations and explanations
- [ ] Email delivery of Daily Protocol each morning
- [ ] Proactive alerts when concerning trends emerge (HRV decline, sleep debt, overtraining signals)
- [ ] Cron/scheduler for automated daily pipeline (pull → analyze → deliver)

### Out of Scope

- Multi-user support — personal tool first, expand later
- Web dashboard — email delivery validates the core value faster
- Mobile app — interface layer comes after intelligence layer is proven
- Lab result PDF upload/OCR — static config captures lab values manually for v1
- Interactive onboarding questionnaire — static config file replaces this
- Multi-agent architecture — single structured prompt is simpler and sufficient for v1
- Other wearable integrations (Apple Watch, Whoop, Oura) — Garmin first
- CGM integration — future expansion
- Marketplace/ecosystem features — Phase 4 vision, not v1
- Connect IQ watch apps — no networking capability, cannot send data to external servers
- Apple Health / Google Health Connect — device-local APIs only, no server-side access
- WhatsApp delivery — requires Meta Business Verification, template pre-approval; Telegram is superior for personal tool

## Context

- The garminconnect Python library (unofficial API) is already familiar — de-risks data ingestion
- Garmin provides the richest data set among wearables for training and recovery analysis
- The Garmin Connect app presents data but not decisions — this is the core gap to fill
- Supabase provides hosted PostgreSQL with easy setup and a path to web dashboard later
- Claude API single-prompt approach is validated as sufficient for this type of structured analysis
- The Daily Protocol format (as described in the README) is the north star output format
- **Garmin health data has no public weblinks** — sleep, stress, body battery, HRV, etc. cannot be shared via URL. Only activity links exist. All health data requires authenticated API access.
- **Official Garmin Health API is enterprise-only** — requires business approval, commercial license, 2+ users minimum. Personal projects are explicitly excluded.
- **Rate limits on unofficial API** — ~1 request/5 min on some endpoints; batch daily pulls recommended. Re-authenticating per run triggers rate limits.
- **garth library handles OAuth** — tokens persist ~1 year; token refresh is the critical reliability concern
- **Connect IQ apps cannot send data externally** — no networking capability, not a viable extraction path
- **Bulk export available for historical backfill** — garmin.com/account/datamanagement/ provides FIT/GPX/TCX files, parseable with garmin_fit_sdk or fitparse
- **Aggregator APIs (Terra ~$0.10/1K calls, Vital $99+/mo) exist as fallback** — if garminconnect breaks, Terra covers 30+ wearables but loses Garmin-specific metrics (Body Battery, training load)
- **Telegram is the best interactive delivery channel** — free, 2-min bot setup, rich Markdown, no business verification (unlike WhatsApp which requires Meta Business Verification)

## Constraints

- **Tech stack**: Python 3.11+ — aligns with garminconnect library and data pipeline tooling
- **AI provider**: Claude API (Anthropic) — single structured prompt approach
- **Database**: Supabase (hosted PostgreSQL) — time-series biometric data + health profile
- **Garmin API**: Unofficial garminconnect Python library — official Health API is enterprise-only, explicitly rejects personal projects
- **Garmin rate limits**: ~1 req/5 min on some endpoints; must batch daily pulls, never re-authenticate per run
- **Delivery**: Email — simplest channel, no app infrastructure needed
- **Audience**: Single user (personal tool) — no auth, no multi-tenancy

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Static config file over onboarding flow | Personal tool — hardcoded profile is faster and simpler than building intake UI | — Pending |
| Supabase over local SQLite | Hosted Postgres ready for future web dashboard; easy setup | — Pending |
| All 5 domains in v1 | Core value is the holistic Daily Protocol — partial domains weaken the value proposition | — Pending |
| Include trend analysis in v1 | Trends are what make the protocol intelligent over time, not just reactive | — Pending |
| Email delivery over web dashboard | Validates core intelligence without building UI; daily email is natural consumption pattern | — Pending |
| Unofficial garminconnect over official Health API | Official API is enterprise-only (business approval, commercial license, 2+ users). Unofficial library has 105+ endpoints, actively maintained, used by Home Assistant. | — Pending |
| Dedicated non-MFA Garmin account for automation | MFA-enabled accounts have known OAuth refresh failures (Issue #312, Dec 2025). Non-MFA account eliminates this risk. | — Pending |
| Telegram as v1.1 delivery channel | Free, 2-min bot setup, rich Markdown, interactive keyboards. WhatsApp requires Meta Business Verification — wrong for personal tool. | — Pending |

---
*Last updated: 2026-03-03 after Garmin research synthesis incorporation*
