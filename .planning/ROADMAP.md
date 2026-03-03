# Roadmap: BioIntelligence

## Overview

BioIntelligence transforms raw Garmin biometric data into a personalized Daily Protocol delivered by email each morning. The build follows data flow dependencies: first establish reliable data ingestion and storage, then build the health profile and prompt assembly layer, then the Claude analysis engine, then protocol rendering and email delivery, then pipeline automation, and finally intelligence hardening with extended trends and anomaly detection. Each phase delivers a verifiable capability that unblocks the next.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Data Ingestion and Storage** - Pull Garmin biometrics daily, validate completeness, and persist to Supabase with idempotent upserts
- [x] **Phase 2: Health Profile and Prompt Assembly** - Load personal health profile, compute rolling trends, and assemble structured Claude prompts
- [x] **Phase 3: Analysis Engine** - Claude API integration producing validated Daily Protocol JSON across all 5 domains with safety guardrails
- [ ] **Phase 4: Protocol Rendering and Email Delivery** - Render Daily Protocol as email and deliver each morning via Resend
- [ ] **Phase 5: Pipeline Automation** - End-to-end automated daily pipeline with scheduling, failure handling, and monitoring
- [ ] **Phase 6: Intelligence Hardening** - Extended 28-day trend windows, multi-metric anomaly detection, and proactive alerts

## Phase Details

### Phase 1: Data Ingestion and Storage
**Goal**: Reliable daily Garmin data flows into Supabase with validation, completeness checks, and idempotent persistence
**Depends on**: Nothing (first phase)
**Requirements**: DATA-01, DATA-02, DATA-03, DATA-04, DATA-05, DATA-06, DATA-07, DATA-08
**Success Criteria** (what must be TRUE):
  1. Running the ingestion script for yesterday's date pulls training, recovery, sleep, stress, and general metrics from Garmin and stores them in Supabase
  2. Running the script twice for the same date produces no duplicate rows (upsert idempotency works)
  3. When Garmin returns empty or incomplete data, the system detects it and logs a warning rather than storing null records
  4. Garmin authentication persists across runs without manual re-login (token refresh works)
  5. Querying Supabase for a stored date returns all expected metric categories with correct values
**Plans**: 3 plans

Plans:
- [x] 01-01-PLAN.md — Project scaffold, Garmin auth client, metric extractors, Pydantic models, completeness scoring
- [x] 01-02-PLAN.md — Supabase storage layer, pipeline orchestrator, CLI entry point, end-to-end verification
- [x] 01-03-PLAN.md — Gap closure: fix Settings test isolation from .env file (2 failing tests)

### Phase 2: Health Profile and Prompt Assembly
**Goal**: Personal health profile is loaded from config, rolling trend statistics are computed from stored data, and a structured prompt is assembled ready for Claude
**Depends on**: Phase 1
**Requirements**: PROF-01, PROF-02, TRND-01, TRND-04
**Success Criteria** (what must be TRUE):
  1. A YAML health profile config file exists with all required sections (biometrics, goals, medical, labs, diet, supplements, sleep context) and loads without errors
  2. Given 7+ days of stored data, the system computes rolling 7-day trend statistics (HRV avg, sleep avg, resting HR trend direction) correctly
  3. The assembled prompt contains today's metrics, 7-day rolling context, health profile, and sports science grounding in structured XML-tagged sections
  4. The prompt stays within a defined token budget and uses pre-computed statistics rather than raw data arrays
**Plans**: 2 plans

Plans:
- [x] 02-01-PLAN.md — Health profile Pydantic models, YAML loader, reference config, and 7-day rolling trend computation
- [x] 02-02-PLAN.md — Prompt assembler with XML-tagged sections, sports science grounding, DailyProtocol schema, and token budget

### Phase 3: Analysis Engine
**Goal**: Claude API produces a validated, structured Daily Protocol covering training, recovery, sleep, nutrition, and supplementation with safety guardrails
**Depends on**: Phase 2
**Requirements**: TRNG-01, TRNG-02, TRNG-03, TRNG-04, SLEP-01, SLEP-02, NUTR-01, NUTR-02, SUPP-01, SUPP-02, SAFE-02, SAFE-03
**Success Criteria** (what must be TRUE):
  1. Given a fully assembled prompt, the system returns a validated DailyProtocol JSON object with all 5 domains (training, recovery, sleep, nutrition, supplementation) populated
  2. The training section includes a readiness assessment, recommended intensity/type/duration, and training load interpretation
  3. The sleep section analyzes architecture quality and provides actionable optimization advice tied to prior-day data
  4. Nutrition and supplementation recommendations reference the health profile (dietary preferences, current supplements, lab values) rather than inventing generic advice
  5. When data is ambiguous or concerning patterns emerge, the protocol explicitly states assumptions and recommends consulting a healthcare professional
**Plans**: 2 plans

Plans:
- [x] 03-01-PLAN.md — Anthropic client factory, structured output API call with retry, analysis engine orchestration, Settings extension, and tests
- [x] 03-02-PLAN.md — Protocol storage in Supabase, pipeline run_analysis function, and CLI --analyze flag

### Phase 4: Protocol Rendering and Email Delivery
**Goal**: The Daily Protocol is rendered into a readable email format and delivered reliably each morning
**Depends on**: Phase 3
**Requirements**: PROT-01, PROT-02, PROT-03, PROT-04, SAFE-01
**Success Criteria** (what must be TRUE):
  1. The Daily Protocol email synthesizes all 5 domains into a single coherent output with a clear structure
  2. Each recommendation includes explanatory reasoning (why the data looks this way, what cross-domain interactions exist)
  3. The email includes a "Why this matters" section explaining broader context
  4. The email reports data freshness and alerts when any data source is missing or stale
  5. A test email arrives in the inbox (not spam) with correct formatting
**Plans**: 2 plans

Plans:
- [x] 04-01-PLAN.md — HTML/plain-text email renderers, delivery package scaffold, Settings extension with Resend config
- [ ] 04-02-PLAN.md — Resend sender with retry, run_delivery pipeline function, CLI --deliver flag

### Phase 5: Pipeline Automation
**Goal**: The entire pull-analyze-deliver pipeline runs automatically each morning without manual intervention
**Depends on**: Phase 4
**Requirements**: AUTO-01, AUTO-02
**Success Criteria** (what must be TRUE):
  1. The daily pipeline executes automatically via cron or scheduled task at the configured time each morning
  2. When any pipeline stage fails, the system retries with backoff and sends a failure notification if the protocol cannot be generated
  3. The pipeline can be triggered manually for testing or re-runs without side effects (idempotent)
**Plans**: TBD

Plans:
- [ ] 05-01: TBD

### Phase 6: Intelligence Hardening
**Goal**: The analysis engine evolves from day-zero reactive analysis to longitudinal pattern detection with proactive alerts
**Depends on**: Phase 5 (requires 2+ weeks of accumulated data)
**Requirements**: TRND-02, TRND-03
**Success Criteria** (what must be TRUE):
  1. The system computes 28-day extended trend windows and feeds summary statistics into the analysis prompt
  2. When multiple concerning metrics converge simultaneously (e.g., HRV decline + elevated resting HR + poor sleep efficiency), the system generates a proactive alert in the Daily Protocol
  3. Alert thresholds are based on personal baselines (relative deviations), not absolute population values
**Plans**: TBD

Plans:
- [ ] 06-01: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Data Ingestion and Storage | 3/3 | Complete | 2026-03-03 |
| 2. Health Profile and Prompt Assembly | 2/2 | Complete | 2026-03-03 |
| 3. Analysis Engine | 2/2 | Complete | 2026-03-03 |
| 4. Protocol Rendering and Email Delivery | 1/2 | In progress | - |
| 5. Pipeline Automation | 0/1 | Not started | - |
| 6. Intelligence Hardening | 0/1 | Not started | - |
