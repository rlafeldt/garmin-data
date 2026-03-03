# Project Research Summary

**Project:** BioIntelligence — Personal Health AI Agent
**Domain:** Biometric data pipeline with LLM analysis (Garmin + Claude + email delivery)
**Researched:** 2026-03-03
**Confidence:** HIGH

## Executive Summary

BioIntelligence is a personal ETL+AI pipeline that pulls daily biometric data from Garmin Connect, stores it in Supabase, analyzes it with Claude, and delivers a personalized "Daily Protocol" via email. The domain is well-understood: this is a batch data pipeline with a single user, running once per day, with no real-time requirements and no concurrent users. Research confirms that the correct architectural pattern is a sequential Python script triggered by a system scheduler — not microservices, not event-driven, not an LLM agent framework. Simplicity is correct here.

The core product differentiation is clear and genuinely novel: no existing competitor (Whoop, Oura, Garmin, HRV4Training) synthesizes training, recovery, sleep, nutrition, and supplementation into a single coherent daily protocol. Each competitor owns 2-3 domains and siloes them. BioIntelligence's cross-domain synthesis via LLM, grounded in a rich static health profile, creates recommendation quality that wearable companies cannot match without building complex onboarding flows. The email-first delivery model is contrarian but strategically sound — it eliminates app-open friction and validates the intelligence layer without competing on UI/UX.

The principal risks are concentrated in the data ingestion layer. Garmin's unofficial API has no stability guarantees, breaks without notice, and requires careful token management to avoid rate limiting. The LLM analysis layer carries hallucination risk that must be mitigated through constrained output schemas, pre-computed trend statistics, and explicit safety guardrails. Both risks are well-documented and have proven mitigation strategies — they do not threaten the project's feasibility but must be designed for from day one.

## Key Findings

### Recommended Stack

The stack is lean and mature. Python 3.12 with uv for package management is the clear choice — uv is 10-100x faster than pip and replaces venv, pip-tools, and pyenv in one tool. The garminconnect library (0.2.38) is the only maintained unofficial Garmin Python client with 105+ endpoints. Anthropic SDK (0.84.0) with structured outputs beta provides Pydantic-validated JSON directly from Claude, eliminating free-text parsing failures. Supabase via REST client (not direct psycopg2) avoids connection pooling complexity at single-user scale. Resend handles email delivery at 3,000 emails/month free, replacing SendGrid which retired its free tier in May 2025.

See [STACK.md](.planning/research/STACK.md) for full version table, alternatives considered, and what not to use.

**Core technologies:**
- Python 3.12 + uv: runtime and package management — the 2025/2026 standard for new Python projects
- garminconnect 0.2.38: Garmin data access — the only maintained unofficial client with 105+ endpoints
- anthropic 0.84.0: LLM analysis — structured output beta gives Pydantic-validated JSON responses
- supabase 2.28.0 (REST): time-series storage — avoids IPv6/connection-pooling issues of direct psycopg2
- resend 2.23.0: email delivery — free tier covers daily use, SendGrid free tier is dead
- pydantic-settings 2.13.1: configuration — type-safe .env loading with startup validation
- structlog 24.x: logging — JSON-structured pipeline logs for debugging failures
- tenacity 9.x: retry logic — exponential backoff on all external API calls
- Jinja2 3.1.x: email templating — separation of data (JSON) from presentation (HTML)

**Critical version note:** Structured outputs require `betas=["structured-outputs-2025-11-13"]` header. pydantic-settings requires pydantic v2, not v1.

### Expected Features

Research confirms competitors (Whoop, Oura, Garmin, HRV4Training) are definitively siloed by domain. The cross-domain gap is real and wide. Nutrition and supplementation tied to daily biometric data is genuinely uncharted territory — no wearable product goes there. The health profile config is an underappreciated competitive moat: competitors know age, weight, and activity level; BioIntelligence can know medical conditions, current supplement stack, recent lab values, dietary framework, and training goals.

See [FEATURES.md](.planning/research/FEATURES.md) for the full competitor analysis matrix and feature dependency graph.

**Must have (table stakes) — v1 launch:**
- Automated Garmin data pull (all metrics) — foundation; without data there is no product
- Static health profile config — enables the personalization that makes all other recommendations meaningful
- Supabase time-series storage — unlocks trend analysis; simple schema from day one
- Claude single-prompt analysis across 5 domains — the intelligence layer; the reason the product exists
- 7-day rolling trend context in prompt — minimum longitudinal awareness for non-trivial analysis
- Email delivery of Daily Protocol — the delivery mechanism; validates whether users act on recommendations
- Cron scheduler for daily pipeline — automation; the product must run without manual intervention

**Should have (competitive differentiation) — v1.x:**
- Proactive anomaly alerts (multi-metric convergence detection) — an emerging battleground; Whoop just announced this
- Extended 28-day trend windows — richer longitudinal patterns once baseline is established
- Sports science-grounded system prompt (Seiler's polarized training model, Banister fitness-fatigue model)
- HTML email template with structured sections — plain text validates intelligence, HTML improves scannability
- Data staleness detection and alerts — prevents silent failures from polluting the trend database

**Defer (v2+):**
- Web dashboard — validates UI hypothesis, not intelligence hypothesis; don't conflate them
- Conversational Q&A — fundamentally different interaction model; only build after protocol format is validated
- Lab result integration via manual entry or PDF OCR — static health profile config handles key values for v1
- Multi-wearable support — data normalization nightmare; Garmin provides the richest training+recovery dataset

**Anti-features to avoid completely:**
- Specific workout plan generation (liability, competes with Garmin Coach)
- Medical diagnosis or health condition detection (consumer wearables are not medical-grade)
- Food logging / calorie tracking (notoriously poor adherence; distracts from biometric intelligence)
- Social features or leaderboards (orthogonal to the core value; single-user product)

### Architecture Approach

The correct architecture is a classic ETL+A (Extract, Transform, Load, Act) pipeline with four sequential stages, implemented as a single Python package with one entry point. The pipeline orchestrator calls stages in sequence: Garmin Extract → Normalize + Store → Claude Analysis → Email Delivery. No message queues, no worker pools, no microservices. A single user running a 30-second daily batch job does not need distributed systems.

The key architectural insight for the analysis stage is treating the LLM context window as a database: all trend computation happens in Python before the prompt is assembled, and the prompt packs pre-computed statistics (HRV 7-day avg, sleep debt hours, trend direction) rather than raw data arrays. This prevents arithmetic hallucination and controls token costs.

See [ARCHITECTURE.md](.planning/research/ARCHITECTURE.md) for full component diagram, data flow, SQL schema, structured output JSON schema, and suggested build order.

**Major components:**
1. Garmin Extractor — authenticates via garth OAuth, pulls 11+ metric categories per date, returns raw dicts
2. Data Normalizer — Pydantic validation models convert raw dicts to typed models; upsert to Supabase by date
3. Supabase Storage — wide denormalized `daily_metrics` table (one row per date); `activities` table (1:many); raw JSONB column for schema evolution safety
4. Health Profile Loader — static YAML/TOML config file; loaded once at pipeline start; injected into every prompt
5. Prompt Assembler — builds Claude prompt from today's data + rolling history + pre-computed trends + health profile; XML-tagged sections
6. Analysis Engine — Claude API call with structured output schema; returns validated DailyProtocol JSON
7. Email Renderer + Delivery — Jinja2 template → HTML email → Resend API

**Deployment:** GitHub Actions scheduled workflow is the recommended path for automation. Token persistence challenge: store Garmin OAuth tokens in Supabase (encrypted) rather than filesystem, since GitHub Actions runners are ephemeral. Alternative: VPS or local cron with persistent filesystem if GitHub Actions token approach proves complex.

### Critical Pitfalls

Research identified 12 pitfalls across 3 severity levels. The top 5 require design-level decisions, not just implementation-level fixes.

See [PITFALLS.md](.planning/research/PITFALLS.md) for full detail, detection signals, and phase-specific warning table.

1. **Garmin auth breaks without warning** — Garmin changes SSO without notice; unofficial library reverse-engineers it. Always persist OAuth tokens (never re-authenticate per-run), pin library versions, disable MFA on the automation account, build a health check that alerts on 403 rather than retrying (which triggers rate limits).

2. **Garmin API returns 200 OK with silent empty/null data** — Watch sync lag, server processing delay, and endpoint migrations all produce empty 200 responses. Implement a data completeness check before storage: define minimum required fields (HRV, sleep duration, Body Battery, stress) and reject/retry if null. Schedule pipeline for 7-8 AM, not 5 AM. Store raw JSONB for schema evolution safety.

3. **LLM hallucinating health recommendations** — Structured prompts reduce hallucination but don't eliminate it (GPT-4o: 53% → 23% with structured prompts; still 23%). Constrain output to options from the health profile — never let the model invent supplement dosages. Add confidence fields. Include disclaimer in every email. Review protocols manually the first few weeks.

4. **Timezone and date boundary confusion** — Garmin returns UTC, local time, and Unix timestamps inconsistently. Sleep from Monday night is Tuesday's sleep. Normalize all timestamps to UTC immediately at ingestion. Define "health day" from wake time, not midnight. Use explicit tzinfo everywhere; treat naive timestamps as suspect.

5. **Unbounded context window in trend analysis** — Feeding 30 days of raw data to Claude wastes tokens and degrades attention quality. Fixed rolling window: 7 days of detailed data + pre-computed 30-day summary statistics + 90-day trend indicators. Pre-compute all statistics in Python; send summaries, not raw arrays.

## Implications for Roadmap

Architecture research explicitly prescribes the build order based on data flow dependencies. Pipeline stages have strict upstream dependencies (you cannot analyze without data; you cannot alert without trend history). This maps cleanly to roadmap phases.

### Phase 1: Data Ingestion Foundation

**Rationale:** Everything downstream depends on reliable Garmin data flow. This must be the first phase, and it must be hardened — not just working, but robust to auth failures, empty responses, and endpoint changes. The pipeline cannot be "done" in later phases if the data foundation is brittle.

**Delivers:** garminconnect authentication with token persistence, all 11+ metric categories pulled per date, Pydantic validation models for each metric type, data completeness checks, retry logic via tenacity, structured logging with structlog. Raw JSONB stored alongside normalized columns.

**Addresses features:** Automated Garmin data pull, data freshness and reliability, data staleness detection

**Avoids pitfalls:** Garmin auth breakage (Pitfall 1), silent empty responses (Pitfall 2), endpoint deprecation (Pitfall 9), timezone confusion (Pitfall 4), granularity mismatch (Pitfall 12)

**Research flag:** Needs phase-level research — garminconnect library has known breakage patterns; validate all target endpoints work with the specific Garmin account before building downstream stages.

### Phase 2: Storage and Schema

**Rationale:** Once data flows, persist it before iterating on analysis. The schema design is a one-time decision with long-term consequences — getting UTC normalization, the upsert pattern, and the wide denormalized table design right here prevents painful migrations later.

**Delivers:** Supabase project setup, `daily_metrics` and `activities` tables with SQL schema (see ARCHITECTURE.md), upsert-by-date writes, UTC timestamp normalization, raw_data JSONB column, date index for rolling window queries.

**Addresses features:** Supabase time-series storage, 7-day rolling trend context (storage prerequisite)

**Avoids pitfalls:** Duplicate records from non-idempotent pipeline (Pitfall 8), timezone confusion (Pitfall 4), proprietary scores as ground truth (Pitfall 5 — label metrics correctly in schema comments)

**Research flag:** Standard patterns — Supabase REST client, PostgreSQL schema design. No research needed.

### Phase 3: Health Profile and Prompt Assembly

**Rationale:** The health profile is the personalization foundation for all Claude analysis. It must exist before the analysis engine can be built or tested meaningfully. Prompt assembly depends on both stored history (Phase 2) and the health profile config.

**Delivers:** YAML health profile config (personal data, goals, medical, labs, diet, supplements), profile loader, trend computation Python functions (rolling averages, deltas, trend direction), prompt assembler with XML-tagged sections, prompt versioning system (prompts as versioned template files in repo).

**Addresses features:** Static health profile config, 7-day trend context, sports science grounding in system prompt

**Avoids pitfalls:** LLM hallucination (Pitfall 3 — constrain outputs to health profile bounds), over-engineered config (Pitfall 10 — flat YAML, match prompt needs exactly), prompt drift (Pitfall 11 — version-controlled templates), unbounded context (Pitfall 6 — pre-compute trends in Python)

**Research flag:** No research needed for health profile config structure. Prompt engineering patterns are well-documented in Anthropic's guides (data-first, XML tags, role anchoring).

### Phase 4: Claude Analysis Engine

**Rationale:** With all inputs ready (stored data, rolling history, health profile, computed trends), the analysis engine is a focused integration task: call the API, validate the DailyProtocol schema, handle errors and retries.

**Delivers:** Claude API integration with structured output schema (full JSON schema in ARCHITECTURE.md), Pydantic DailyProtocol model matching the 5-domain output (training, recovery, sleep, nutrition, supplementation + alerts), error handling for API failures, confidence fields per recommendation, system prompt with safety guardrails and sports science grounding.

**Addresses features:** Cross-domain unified Daily Protocol, explanatory reasoning, readiness/recovery assessment, sleep analysis with advice, training load interpretation, nutrition recommendations, supplement timing guidance

**Avoids pitfalls:** LLM hallucination (Pitfall 3 — constrained schema, confidence fields, no free-form dosage invention), unbounded context (Pitfall 6 — fixed token budget enforced before API call), proprietary scores as ground truth (Pitfall 5 — system prompt labels Garmin scores correctly)

**Research flag:** Standard patterns — Anthropic structured outputs beta is well-documented. Model choice (Sonnet vs Opus) may need a brief validation run comparing output quality at launch.

### Phase 5: Email Rendering and Delivery

**Rationale:** Once a validated DailyProtocol JSON exists, rendering and delivering it is straightforward. This is the final stage that closes the end-to-end pipeline loop.

**Delivers:** Jinja2 HTML email templates (base template + per-domain section templates + alert banner), responsive email CSS, subject line format ("Daily Protocol — [date] [STATUS]"), Resend API integration, domain DNS setup (SPF/DKIM/DMARC via Resend), test email to verify inbox delivery (not spam).

**Addresses features:** Email delivery of Daily Protocol, email-first passive delivery differentiator

**Avoids pitfalls:** Email landing in spam (Pitfall 7 — Resend handles deliverability, verify day one)

**Research flag:** Standard patterns — Resend Python SDK is simple. Jinja2 email templating is well-documented. No research needed.

### Phase 6: Pipeline Orchestration and Automation

**Rationale:** Automation wraps a working pipeline. Scheduling a broken pipeline just automates failures. All five prior stages must be working end-to-end manually before adding scheduling.

**Delivers:** Pipeline orchestrator (main.py with sequential stage calls), GitHub Actions scheduled workflow or local cron/launchd, Garmin token persistence to Supabase (for ephemeral CI runners), pipeline run status tracking (pulled/analyzed/emailed per day), monitoring and alert emails on pipeline failure, manual trigger capability for testing.

**Addresses features:** Cron scheduler for daily pipeline, data freshness and reliability

**Avoids pitfalls:** Non-idempotent pipeline (Pitfall 8 — all writes idempotent; pipeline tracks per-stage completion), Garmin auth breakage (Pitfall 1 — health check before main pipeline; alert on failure rather than retry loop)

**Research flag:** GitHub Actions token persistence approach needs validation — storing Garmin tokens in Supabase is the recommended pattern but the encryption/retrieval flow should be designed carefully.

### Phase 7: Intelligence Hardening and Anomaly Detection

**Rationale:** After the pipeline is running reliably for 2+ weeks, sufficient historical data exists to establish baselines. This phase upgrades the analysis engine from day-zero analysis to longitudinal pattern detection.

**Delivers:** Extended 28-day trend windows, proactive anomaly alerts (multi-metric convergence: HRV decline + elevated RHR + poor sleep efficiency), configurable alert thresholds relative to personal baselines (not absolute values), sports science prompt refinements based on observed output quality.

**Addresses features:** Proactive anomaly alerts, extended trend analysis, sports science prompt grounding improvements

**Avoids pitfalls:** Proprietary scores as ground truth (Pitfall 5 — thresholds based on relative deltas, not absolute values), unbounded context (Pitfall 6 — 28-day summaries, not 28 days of raw data)

**Research flag:** May need light research on multi-metric anomaly detection thresholds (HRV+RHR convergence signals). Otherwise standard patterns.

### Phase Ordering Rationale

- **Data before analysis:** You cannot test analysis quality with synthetic data; real Garmin data must flow first (Phases 1-2 before Phases 3-4)
- **Inputs before integration:** Health profile and prompt assembly must exist before the Claude API is integrated in a meaningful way (Phase 3 before Phase 4)
- **End-to-end before automation:** The complete pipeline must work manually before scheduling is added (Phases 1-5 before Phase 6)
- **Baseline before anomaly detection:** Proactive alerts require established personal baselines; impossible without 2+ weeks of stored data (Phase 6 running before Phase 7)
- **Intelligence before dashboard:** The email format validates whether recommendations are valuable; a dashboard would test whether the UI is good — a different hypothesis that should wait for v2+

### Research Flags

Phases needing deeper research during planning:
- **Phase 1:** Validate all target garminconnect endpoints with the specific Garmin account before building downstream. Known breakage patterns and endpoint migrations mean hands-on verification is required.
- **Phase 6:** GitHub Actions Garmin token persistence approach (storing tokens in Supabase, encrypting/retrieving in CI) should be designed carefully before implementation.

Phases with standard patterns (skip research-phase):
- **Phase 2:** Supabase REST client and PostgreSQL schema design are well-documented. ARCHITECTURE.md has the complete SQL schema ready to use.
- **Phase 3:** Health profile config and prompt engineering patterns are well-documented. Anthropic's guidelines are clear.
- **Phase 4:** Anthropic structured outputs beta is well-documented. The JSON schema is already designed in ARCHITECTURE.md.
- **Phase 5:** Resend Python SDK and Jinja2 email templating are standard. Deliverability handled by Resend.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All packages verified on PyPI with current versions. Version compatibility matrix complete. Known garminconnect MFA issue documented with workaround. One medium-confidence source on SendGrid free tier retirement (single source, May 2025). |
| Features | HIGH | Competitor analysis based on official product documentation (Whoop, Oura, Garmin). Nature Medicine paper confirms LLM-based personal health analysis is viable. Cross-domain gap validated across all competitors. |
| Architecture | HIGH | ETL+A sequential pipeline pattern is industry-standard for single-user batch jobs. Data flow, SQL schema, and structured output JSON schema are fully specified. Build order is deterministically derived from data flow dependencies. |
| Pitfalls | HIGH | Garmin auth pitfalls sourced from 6+ GitHub issues with documented failure modes. LLM hallucination data from PubMed/arXiv peer-reviewed sources. Email deliverability sourced from specialist email infrastructure documentation. |

**Overall confidence:** HIGH

### Gaps to Address

- **Garmin endpoint validation:** The garminconnect library lists 105+ endpoints but not all are reliably populated for all device models. Validate that the specific Garmin device and account return expected data for all target metrics (HRV, SpO2, Body Battery, sleep stages) before building the normalization layer.

- **SendGrid free tier retirement:** Confirmed by one source (May 2025). If already holding a SendGrid account, verify current tier status before migrating to Resend. For new setups, Resend is unambiguously correct.

- **GitHub Actions token persistence:** The recommended approach (store Garmin OAuth tokens in Supabase) has not been validated in a real CI environment. An alternative (local cron with filesystem persistence) is simpler and may be preferable for early phases.

- **Claude model selection:** ARCHITECTURE.md recommends claude-sonnet-4-5 for daily runs at ~$2/year cost. The model version should be confirmed as current at implementation time; Claude model naming evolves and the latest Sonnet may differ.

- **MFA handling decision:** The research documents a known MFA failure (Issue #312, Dec 2025). The decision to use a dedicated non-MFA Garmin account vs. attempting MFA workarounds should be made at Phase 1 start, not discovered mid-implementation.

## Sources

### Primary (HIGH confidence)

- [garminconnect on PyPI](https://pypi.org/project/garminconnect/) — version 0.2.38, Python requirements, release date
- [python-garminconnect GitHub](https://github.com/cyberjunky/python-garminconnect) — API methods, auth flow, token persistence, endpoint list
- [garminconnect MFA issue #312](https://github.com/cyberjunky/python-garminconnect/issues/312) — documented failure Dec 2025
- [garminconnect rate limit issues #127, #213](https://github.com/cyberjunky/python-garminconnect/issues) — auth retry pitfalls
- [garth GitHub](https://github.com/matin/garth) — OAuth1/OAuth2 token lifecycle
- [anthropic on PyPI](https://pypi.org/project/anthropic/) — version 0.84.0
- [Claude structured outputs docs](https://docs.claude.com/en/docs/build-with-claude/structured-outputs) — beta feature with Pydantic support
- [Claude prompting best practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices) — data-first prompting, XML tags
- [supabase on PyPI](https://pypi.org/project/supabase/) — version 2.28.0
- [Supabase connecting to Postgres docs](https://supabase.com/docs/guides/database/connecting-to-postgres) — REST vs direct connection
- [resend on PyPI](https://pypi.org/project/resend/) — version 2.23.0, free tier
- [Resend pricing](https://resend.com/pricing) — 3,000 emails/month free
- [pydantic-settings on PyPI](https://pypi.org/project/pydantic-settings/) — version 2.13.1
- [GitHub Actions scheduled workflows](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#schedule)
- [Whoop AI Guidance](https://www.whoop.com/us/en/thelocker/new-ai-guidance-from-whoop/) — competitor feature analysis
- [Oura Readiness Score](https://ouraring.com/blog/readiness-score/) — competitor feature analysis
- [Garmin Daily Suggested Workouts](https://www.garmin.com/en-US/garmin-technology/running-science/) — competitor feature analysis
- [Personal Health LLM for sleep and fitness (Nature Medicine)](https://www.nature.com/articles/s41591-025-03888-0) — LLM health agent viability
- [Medical Hallucination in Foundation Models (arXiv 2025)](https://arxiv.org/html/2503.05777v2) — hallucination rates in clinical tasks
- [Clinicians' Guide to LLMs and Hallucinations (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC11815294/) — structured prompt hallucination reduction data

### Secondary (MEDIUM confidence)

- [uv vs pip comparison (Real Python)](https://realpython.com/uv-vs-pip/) — performance and feature comparison
- [Garmin timezone approach](https://thomasclowes.com/garmins-approach-to-time-zones/) — UTC vs local time inconsistency documentation
- [ETL Best Practices 2026](https://oneuptime.com/blog/post/2026-02-13-etl-best-practices/view) — idempotency and pipeline design

### Tertiary (MEDIUM-LOW confidence)

- [SendGrid free tier retirement (Medium, May 2025)](https://medium.com/@nermeennasim/email-apis-in-2025-sendgrid-vs-resend-vs-aws-ses-a-developers-journey-8db7b5545233) — single source; verify if already holding a SendGrid account

---
*Research completed: 2026-03-03*
*Ready for roadmap: yes*
