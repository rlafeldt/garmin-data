# Requirements: BioIntelligence

**Defined:** 2026-03-03
**Core Value:** Every morning, receive a single coherent Daily Protocol that tells you exactly what to do today based on your Garmin data, health profile, and recent trends.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Data Ingestion

- [x] **DATA-01**: System pulls previous day's Garmin data automatically covering training activities, heart rate zones, training effect, training load, training status, and VO2 max trend
- [x] **DATA-02**: System pulls recovery metrics including overnight HRV (average and trend), Body Battery (charge/drain curve), and resting heart rate
- [x] **DATA-03**: System pulls sleep data including total duration, sleep stages (deep, light, REM, awake), sleep score, SpO2, and respiration rate
- [x] **DATA-04**: System pulls stress data including all-day stress score, stress duration breakdown, and relaxation time
- [x] **DATA-05**: System pulls general metrics including steps, intensity minutes, and calories burned
- [x] **DATA-06**: System validates data completeness and detects silent empty responses from Garmin API
- [x] **DATA-07**: System stores daily biometric data in Supabase with wide denormalized schema and upsert-by-date idempotency
- [x] **DATA-08**: System handles Garmin auth token persistence and refresh without manual intervention

### Health Profile

- [x] **PROF-01**: User defines personal health profile in a static YAML config file including age, sex, weight, height, body composition, training goals, medical history, metabolic profile, diet preferences, current supplements with dosages, sleep context, and relevant lab values
- [x] **PROF-02**: Health profile is injected into every Claude API analysis call as structured context

### Analysis — Training & Recovery

- [x] **TRNG-01**: System assesses daily readiness by interpreting Body Battery, HRV status, resting heart rate trend, and sleep quality holistically
- [x] **TRNG-02**: System interprets training load with acute-to-chronic load ratio analysis and flags overreaching before it becomes overtraining
- [x] **TRNG-03**: System recommends today's training intensity zone, training type (e.g., easy aerobic, tempo, rest day), and duration range based on readiness and load state
- [x] **TRNG-04**: System surfaces stress patterns and connects elevated stress to training and sleep recommendations

### Analysis — Sleep

- [x] **SLEP-01**: System analyzes sleep architecture (deep sleep sufficiency, REM adequacy, awake time) and identifies sleep quality issues
- [x] **SLEP-02**: System provides specific actionable sleep optimization advice tied to prior-day variables (training intensity, stress levels, schedule consistency)

### Analysis — Nutrition

- [x] **NUTR-01**: System suggests daily caloric targets, macro ratios, and meal timing based on training volume, recovery demands, body composition goals, and dietary preferences from health profile
- [x] **NUTR-02**: System recommends daily hydration targets based on training load and recovery state

### Analysis — Supplementation

- [x] **SUPP-01**: System recommends specific supplement timing and dosing tied to current biometric state, health profile, and lab values (e.g., magnesium glycinate on high-stress days, vitamin D calibrated to blood levels)
- [x] **SUPP-02**: System provides conservative supplement advice with explicit reasoning and states assumptions when lab values are unavailable

### Protocol & Delivery

- [x] **PROT-01**: System produces a unified Daily Protocol synthesizing training, recovery, sleep, nutrition, and supplementation into a single coherent output each morning
- [x] **PROT-02**: Daily Protocol includes explanatory reasoning chains explaining why data looks the way it does and what cross-domain interactions exist
- [ ] **PROT-03**: Daily Protocol is delivered via email each morning using a transactional email service
- [x] **PROT-04**: Daily Protocol includes a "Why this matters" section explaining the broader context and what's at stake

### Trends & Intelligence

- [x] **TRND-01**: System feeds 7-day rolling trend context into the analysis prompt for longitudinal awareness
- [ ] **TRND-02**: System computes 28-day extended trend windows for deeper pattern detection (HRV trajectory, resting HR creep, sleep debt accumulation)
- [ ] **TRND-03**: System detects multi-metric anomaly convergence (e.g., simultaneous HRV decline + elevated resting HR + poor sleep efficiency) and generates proactive alerts
- [x] **TRND-04**: System prompt encodes sports science frameworks (periodization models, HRV interpretation, sleep architecture research) for grounded recommendations

### Safety & Quality

- [x] **SAFE-01**: Daily Protocol reports data freshness and alerts when data is missing or stale
- [x] **SAFE-02**: System flags concerning health patterns and recommends consulting a healthcare professional rather than diagnosing conditions
- [x] **SAFE-03**: System acknowledges uncertainty — when data is ambiguous or conflicting, it states assumptions explicitly rather than forcing confident recommendations

### Pipeline Automation

- [ ] **AUTO-01**: Daily pipeline runs automatically via cron or scheduled task (pull -> analyze -> deliver) without manual intervention
- [ ] **AUTO-02**: Pipeline handles failures gracefully with retry logic and sends notification if daily protocol cannot be generated

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Delivery Enhancements

- **DLVR-01**: HTML email template with structured scannable sections (TL;DR at top, detailed domains below)
- **DLVR-02**: Weekend vs weekday protocol differentiation accounting for schedule differences
- **DLVR-03**: Telegram bot delivery as interactive alternative to email (free, 2-min setup, rich Markdown, inline keyboards)

### Intelligence Improvements

- **INTL-01**: Adaptive learning from user feedback on recommendation usefulness
- **INTL-02**: Periodization awareness — incorporate training block context if user follows structured program

### Platform Expansion

- **PLAT-01**: Web dashboard with trend visualizations and protocol history
- **PLAT-02**: Lab result PDF upload with OCR parsing
- **PLAT-03**: Weekly and monthly summary reports

### Data Enrichment

- **ENRH-01**: Historical data backfill via Garmin bulk export (FIT/GPX/TCX parsing with garmin_fit_sdk or fitparse)

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Specific workout plan generation | Liability risk, can't verify form/technique, competes with Garmin Coach. Recommend intensity/type/duration ranges instead. |
| Medical diagnosis or condition detection | Consumer wearable data is not medical-grade. Flag patterns and recommend consulting professionals. |
| Food/calorie tracking and logging | Poor user adherence (most quit within weeks). Provide nutrition principles based on biometric state instead. |
| Real-time conversational AI chat | Scope creep into chatbot territory. Daily Protocol is the validated interaction model. |
| Multi-wearable data aggregation | Data normalization across devices is complex. Garmin provides sufficient data for all 5 domains. |
| Social features / leaderboards | Single-user personal tool. Social requires entirely different infrastructure. |
| Mobile application | Email delivery validates intelligence layer. App validates UI — different hypothesis. |
| Automated supplement ordering | Business complexity, conflict of interest risk, regulatory concerns. |
| Multi-user support | Personal tool first. Multi-user requires auth, profiles, billing — different product. |
| CGM integration | Future expansion. Static config captures relevant metabolic context for v1. |
| Official Garmin Health API | Enterprise-only: requires business approval, commercial license, 2+ users min. Personal projects rejected. |
| Connect IQ watch apps | No networking capability — cannot send data to external servers. |
| WhatsApp delivery | Requires Meta Business Verification, template pre-approval. Telegram is superior for personal tool. |
| Apple Health / Google Health Connect | Device-local APIs only, no server-side access for backend agent. |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| DATA-01 | Phase 1: Data Ingestion and Storage | Complete |
| DATA-02 | Phase 1: Data Ingestion and Storage | Complete |
| DATA-03 | Phase 1: Data Ingestion and Storage | Complete |
| DATA-04 | Phase 1: Data Ingestion and Storage | Complete |
| DATA-05 | Phase 1: Data Ingestion and Storage | Complete |
| DATA-06 | Phase 1: Data Ingestion and Storage | Complete |
| DATA-07 | Phase 1: Data Ingestion and Storage | Complete |
| DATA-08 | Phase 1: Data Ingestion and Storage | Complete |
| PROF-01 | Phase 2: Health Profile and Prompt Assembly | Complete |
| PROF-02 | Phase 2: Health Profile and Prompt Assembly | Complete |
| TRND-01 | Phase 2: Health Profile and Prompt Assembly | Complete |
| TRND-04 | Phase 2: Health Profile and Prompt Assembly | Complete |
| TRNG-01 | Phase 3: Analysis Engine | Complete |
| TRNG-02 | Phase 3: Analysis Engine | Complete |
| TRNG-03 | Phase 3: Analysis Engine | Complete |
| TRNG-04 | Phase 3: Analysis Engine | Complete |
| SLEP-01 | Phase 3: Analysis Engine | Complete |
| SLEP-02 | Phase 3: Analysis Engine | Complete |
| NUTR-01 | Phase 3: Analysis Engine | Complete |
| NUTR-02 | Phase 3: Analysis Engine | Complete |
| SUPP-01 | Phase 3: Analysis Engine | Complete |
| SUPP-02 | Phase 3: Analysis Engine | Complete |
| SAFE-02 | Phase 3: Analysis Engine | Complete |
| SAFE-03 | Phase 3: Analysis Engine | Complete |
| PROT-01 | Phase 4: Protocol Rendering and Email Delivery | Complete |
| PROT-02 | Phase 4: Protocol Rendering and Email Delivery | Complete |
| PROT-03 | Phase 4: Protocol Rendering and Email Delivery | Pending |
| PROT-04 | Phase 4: Protocol Rendering and Email Delivery | Complete |
| SAFE-01 | Phase 4: Protocol Rendering and Email Delivery | Complete |
| AUTO-01 | Phase 5: Pipeline Automation | Pending |
| AUTO-02 | Phase 5: Pipeline Automation | Pending |
| TRND-02 | Phase 6: Intelligence Hardening | Pending |
| TRND-03 | Phase 6: Intelligence Hardening | Pending |

**Coverage:**
- v1 requirements: 33 total
- Mapped to phases: 33
- Unmapped: 0

---
*Requirements defined: 2026-03-03*
*Last updated: 2026-03-03 after roadmap creation*
