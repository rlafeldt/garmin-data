# Stack Research

**Domain:** Personal health AI agent -- biometric data pipeline with LLM analysis
**Researched:** 2026-03-03
**Confidence:** HIGH

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.12+ | Runtime | garminconnect requires >=3.10; 3.12 is the current stable sweet spot balancing ecosystem compatibility and performance. 3.13 works but some deps may lag behind. |
| uv | latest | Package manager, venv, project tooling | 10-100x faster than pip, handles venv creation, lockfiles, and dependency resolution in one tool. Replaces pip + pip-tools + venv + pyenv. The standard for new Python projects in 2025/2026. |
| garminconnect | 0.2.38 | Garmin Connect API wrapper | The only maintained unofficial Python client for Garmin Connect. 105+ endpoints covering HRV, Body Battery, sleep, stress, VO2 max, SpO2, respiration, training status. Uses garth for OAuth. Actively maintained (last release Jan 2026). |
| anthropic | 0.84.0 | Claude API SDK | Official Anthropic Python SDK. Type-safe, streaming support, retries, structured outputs (beta). Required for Claude API integration. |
| supabase | 2.28.0 | Hosted PostgreSQL client (REST) | Official Python client for Supabase. REST API for reads/writes, no connection pooling headaches. Aligns with project constraint for hosted Postgres with future web dashboard path. |
| resend | 2.23.0 | Transactional email delivery | Modern developer-focused email API. Free tier: 3,000 emails/month (100/day) -- more than sufficient for a single-user daily email. Clean Python SDK, excellent DX, no legacy baggage like SendGrid. |
| pydantic-settings | 2.13.1 | Configuration management | Type-safe settings loaded from .env files and environment variables. Validates config at startup. Pairs naturally with Pydantic models used for data schemas. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| garth | 0.5.x (transitive) | Garmin OAuth authentication | Installed as garminconnect dependency. Handles OAuth1/OAuth2 token persistence, auto-refresh. Tokens saved to ~/.garminconnect by default. |
| pydantic | 2.x (transitive) | Data validation and schemas | Installed as pydantic-settings dependency. Use for Garmin data models, Claude prompt/response schemas, health profile validation. |
| Jinja2 | 3.1.x | HTML email templating | Render the Daily Protocol into a styled HTML email. Standard Python templating -- mature, fast, well-documented. |
| python-dotenv | 1.x (transitive) | .env file loading | Loaded by pydantic-settings. No direct dependency needed but .env file is the config interface. |
| structlog | 24.x+ | Structured logging | JSON-structured logs for the pipeline. Better than loguru for this use case because pipeline runs need machine-parseable logs for debugging failures. Colored console output in dev, JSON in production. |
| tenacity | 9.x | Retry logic | Retry decorator for Garmin API calls and email sends. Handles transient failures with exponential backoff. Cleaner than hand-rolled retry loops. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| uv | Project management | `uv init`, `uv add`, `uv run` -- replaces pip, venv, pip-tools. Use `uv.lock` for reproducible installs. |
| ruff | Linting + formatting | Replaces flake8, black, isort in one tool. Fast (Rust-based). Configure in `pyproject.toml`. |
| pytest | Testing | Standard Python testing. Use `pytest-mock` for mocking Garmin API responses. |
| mypy | Type checking | Enforce type safety on data models and pipeline functions. Pydantic plugin available. |

## Installation

```bash
# Initialize project
uv init biointelligence
cd biointelligence

# Core dependencies
uv add garminconnect anthropic supabase resend pydantic-settings jinja2 structlog tenacity

# Dev dependencies
uv add --dev ruff pytest pytest-mock mypy
```

## Key Architecture Decisions

### Supabase: REST API client, NOT direct Postgres

Use the `supabase` Python client (REST API) rather than `psycopg2` or `SQLAlchemy` for direct Postgres connections.

**Why:**
- No connection pooling configuration needed
- REST API is fast enough for a single-user daily pipeline (not high-throughput)
- Matches the Supabase ecosystem -- schema migrations via Supabase dashboard/CLI
- Future web dashboard can share the same Supabase project seamlessly
- Avoids IPv6 connection issues that plague direct psycopg2 connections to Supabase

**When to reconsider:** If you need complex SQL queries, bulk inserts of thousands of rows, or sub-millisecond latency. None of these apply here.

### Scheduling: System crontab, NOT APScheduler

Use macOS `launchd` (or Linux `cron`) to trigger the pipeline script, not an in-process scheduler like APScheduler.

**Why:**
- The pipeline is a run-once-daily batch job, not a long-running daemon
- System cron/launchd handles restarts, logging, and reliability natively
- APScheduler adds complexity (process management, job stores, graceful shutdown) for no benefit in a single-user daily-run scenario
- The Python script should be a simple entry point: pull data, analyze, email, exit
- For cloud deployment later: use cloud scheduler (Railway cron, Render cron, GitHub Actions schedule)

**When to reconsider:** If the pipeline evolves into a multi-job system with different schedules or needs to run inside a web framework.

### Email: Resend, NOT SendGrid or SMTP

Use Resend over SendGrid or raw SMTP.

**Why:**
- SendGrid retired its free tier (May 2025). New accounts get a 60-day trial then $19.95/month minimum
- Resend free tier: 3,000 emails/month -- a daily email to one person needs ~30/month
- Resend SDK is clean and modern: 5 lines to send an email
- Raw SMTP (smtplib) works but requires managing SMTP credentials, TLS config, and deliverability is poor from personal IPs

**When to reconsider:** If you already have a SendGrid account with a grandfathered free tier, or if you need email analytics/tracking (SendGrid is richer here).

### Claude API: Single structured prompt with Pydantic response model

Use a single Claude API call with a structured system prompt, not multi-agent or chain-of-thought architectures.

**Why:**
- PROJECT.md explicitly scopes this as single-prompt approach
- Claude structured outputs (beta) can return Pydantic-validated JSON directly
- One API call per day keeps costs minimal (~$0.01-0.05 per analysis with Sonnet)
- The prompt includes: health profile, today's data, rolling history window, and output schema

**Model recommendation:** Claude Sonnet 4 for daily analysis (fast, cheap, good enough). Reserve Opus for complex trend analysis if Sonnet quality proves insufficient.

### Authentication: Token persistence with garth

garminconnect uses garth under the hood for Garmin SSO authentication.

**Critical detail:**
- First login requires username/password (interactive)
- Tokens are saved to `~/.garminconnect/` (or `GARMINTOKENS` env var)
- Subsequent runs auto-refresh tokens without re-authentication
- **Known issue:** MFA-enabled accounts have intermittent OAuth1 refresh failures (Issue #312, Dec 2025). Workaround: disable MFA on the Garmin account used for API access, or use a dedicated non-MFA account
- Set permissions: `chmod 700 ~/.garminconnect && chmod 600 ~/.garminconnect/*`

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| garminconnect | garmy | garmy is newer (2024) with a cleaner API but has far less community usage and fewer endpoints. Stick with garminconnect for its 105+ endpoints and proven track record. |
| supabase (REST) | psycopg2 + SQLAlchemy | If you need complex joins, stored procedures, or bulk operations. Overkill for this project's simple CRUD + time-series reads. |
| supabase (REST) | SQLite (local) | If you want zero infrastructure and never plan a web dashboard. PROJECT.md chose Supabase intentionally for future expansion. |
| resend | Amazon SES | If you're already on AWS and want the cheapest option at scale ($0.10/1000 emails). Resend is simpler for a single-user project. |
| resend | SendGrid | If you need advanced email analytics, A/B testing, or marketing features. Not needed for a single daily protocol email. |
| structlog | loguru | If you prefer simpler setup over structured JSON logging. Loguru is easier to start with but structlog's processor chains are better for pipeline debugging. |
| uv | pip + venv | If team members are unfamiliar with uv. But for a personal project, uv is strictly better. |
| system cron | APScheduler 3.11 | If the pipeline needs to run inside a web framework or needs multiple schedule types. Not the case here. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Poetry | Slower than uv, more complex config, losing momentum in 2025/2026 | uv |
| pipenv | Abandoned development pace, poor lockfile performance | uv |
| raw smtplib | Poor deliverability from personal IPs, complex TLS setup, no tracking | resend |
| Flask/FastAPI | No web server needed -- this is a batch pipeline, not an API | Plain Python script with entry point |
| Celery | Massive overkill for a single daily cron job | System crontab / cloud scheduler |
| LangChain | Adds abstraction without value for a single API call. Extra dependency, harder to debug | Direct anthropic SDK |
| pandas | Tempting for data manipulation but heavy dependency for simple time-series aggregation | Plain Python dicts/lists + Pydantic models |
| SQLAlchemy ORM | Adds ORM complexity when Supabase REST client handles CRUD directly | supabase Python client |

## Stack Patterns

**For local development:**
- Use `.env` file with pydantic-settings for all secrets (Garmin creds, Supabase keys, Anthropic key, Resend key)
- Run with `uv run python -m biointelligence.main`
- Schedule with macOS launchd plist or manual trigger

**For cloud deployment (future):**
- Environment variables via hosting platform (Railway, Render, Fly.io)
- Cron trigger via platform scheduler or GitHub Actions `schedule`
- Same codebase, no changes needed -- pydantic-settings reads env vars automatically

**For testing:**
- Mock garminconnect responses with saved JSON fixtures
- Use Supabase local development (Docker) or a test project
- Mock Claude API with recorded responses
- Resend has a test mode (no actual email sent)

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| garminconnect 0.2.38 | Python 3.10-3.13 | Requires garth >=0.5.x for OAuth |
| anthropic 0.84.0 | Python >=3.9 | Structured outputs beta requires `betas=["structured-outputs-2025-11-13"]` header |
| supabase 2.28.0 | Python >=3.9 | Uses httpx internally |
| resend 2.23.0 | Python >=3.7 | Minimal dependencies |
| pydantic-settings 2.13.1 | Python >=3.10, pydantic >=2.7 | Requires pydantic v2, NOT v1 |
| structlog 24.x | Python >=3.8 | Works with stdlib logging |
| Jinja2 3.1.x | Python >=3.8 | No conflicts expected |

**Python 3.12 is the target** -- all dependencies support it, and it avoids any 3.13 edge cases.

## Sources

- [garminconnect on PyPI](https://pypi.org/project/garminconnect/) -- version 0.2.38, release date, Python requirements (HIGH confidence)
- [python-garminconnect GitHub](https://github.com/cyberjunky/python-garminconnect) -- API methods, auth flow, token persistence (HIGH confidence)
- [garminconnect OAuth1 MFA issue #312](https://github.com/cyberjunky/python-garminconnect/issues/312) -- MFA auth failure documented Dec 2025 (HIGH confidence)
- [garth GitHub](https://github.com/matin/garth) -- OAuth token persistence details (HIGH confidence)
- [anthropic on PyPI](https://pypi.org/project/anthropic/) -- version 0.84.0 (HIGH confidence)
- [Claude structured outputs docs](https://docs.claude.com/en/docs/build-with-claude/structured-outputs) -- beta feature with Pydantic support (HIGH confidence)
- [supabase on PyPI](https://pypi.org/project/supabase/) -- version 2.28.0 (HIGH confidence)
- [Supabase connecting to Postgres docs](https://supabase.com/docs/guides/database/connecting-to-postgres) -- REST vs direct connection guidance (HIGH confidence)
- [resend on PyPI](https://pypi.org/project/resend/) -- version 2.23.0, free tier details (HIGH confidence)
- [Resend pricing](https://resend.com/pricing) -- free tier: 3,000 emails/month (HIGH confidence)
- [SendGrid free tier retirement](https://medium.com/@nermeennasim/email-apis-in-2025-sendgrid-vs-resend-vs-aws-ses-a-developers-journey-8db7b5545233) -- retired May 2025 (MEDIUM confidence, single source)
- [pydantic-settings on PyPI](https://pypi.org/project/pydantic-settings/) -- version 2.13.1 (HIGH confidence)
- [APScheduler on PyPI](https://pypi.org/project/APScheduler/) -- version 3.11.2, considered but not recommended for this use case (HIGH confidence)
- [uv vs pip comparison](https://realpython.com/uv-vs-pip/) -- performance and feature comparison (MEDIUM confidence)

---
*Stack research for: BioIntelligence -- Personal Health AI Agent*
*Researched: 2026-03-03*
