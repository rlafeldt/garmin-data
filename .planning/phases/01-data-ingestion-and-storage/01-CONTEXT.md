# Phase 1: Data Ingestion and Storage - Context

**Gathered:** 2026-03-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Pull previous day's Garmin biometrics daily, validate data completeness, and persist to Supabase with idempotent upserts. Covers authentication, all metric category extraction, normalization, storage, and completeness checks. Health profile, analysis, and delivery are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Garmin account & authentication
- Use personal Garmin account (not a dedicated automation account)
- MFA status unknown — check during setup; disable MFA if enabled (required for reliable OAuth token refresh per Issue #312)
- Device: Garmin Fenix 7 series — full sensor suite confirmed, all 11+ target metrics available (HRV, Body Battery, SpO2, sleep stages, stress, training load/status/effect, VO2 max, respiration rate, resting HR)

### Metric scope
- Pull all available metric categories from day one — training, recovery, sleep, stress, general metrics, everything the Fenix 7 reports
- Activity data: summary level only (type, duration, distance, avg/max HR, training effect, training load, calories) — no lap/split detail
- Typical activity volume: 1-2 activities per day
- Primary training types: cycling and strength training

### Data completeness
- Store whatever Garmin returns, flag gaps with nulls and log warnings — never reject a whole day for missing metrics
- No-wear days: store a record with a no-data flag; trend calculations in later phases skip these days
- Pipeline timing: run at ~7:00 AM CET to allow overnight sleep data sync (user wakes 5-6 AM)
- Timezone: Europe/Berlin (CET/CEST) — all timestamps normalized to UTC at ingestion, pipeline scheduling in local time

### Supabase setup
- Existing Supabase account — create a dedicated project for BioIntelligence (clean isolation)
- Region: eu-central-1 (Frankfurt) — closest to user
- Free tier — 500 MB database is more than sufficient for single-user daily biometric data

### Claude's Discretion
- Exact Supabase table schema design (wide denormalized vs normalized — research recommends wide with raw JSONB)
- Pydantic validation model structure for Garmin data normalization
- Retry strategy details (backoff timing, max retries)
- Logging format and levels
- Token persistence mechanism

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. Research already identified the recommended patterns (garminconnect library, garth OAuth, tenacity retries, structlog logging).

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- No existing code — greenfield project

### Established Patterns
- No established patterns yet — Phase 1 sets the foundation for all subsequent phases

### Integration Points
- Research documents (ARCHITECTURE.md, STACK.md) contain recommended SQL schema, package versions, and data flow diagrams
- garminconnect 0.2.38 library with 105+ endpoints is the primary external dependency
- supabase 2.28.0 REST client for database operations

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-data-ingestion-and-storage*
*Context gathered: 2026-03-03*
