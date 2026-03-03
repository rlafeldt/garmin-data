# Domain Pitfalls

**Domain:** Personal health AI agent with Garmin biometric data pipeline
**Researched:** 2026-03-03

---

## Critical Pitfalls

Mistakes that cause rewrites, data corruption, or complete pipeline failures.

---

### Pitfall 1: Garmin Authentication Breaks Without Warning

**What goes wrong:** The unofficial `garminconnect` library relies on reverse-engineered authentication against Garmin's SSO. Garmin changes server-side auth requirements (headers, cookie formats, endpoint signatures) without notice, breaking all automated pipelines overnight. Recent example: Dec 2025, MFA-enabled accounts broke with "OAuth1 token is required for OAuth2 refresh" after Garmin changed their auth flow.

**Why it happens:** There is no official consumer API. The library (and its dependency `garth`) reverse-engineers Garmin's web authentication, which Garmin can and does change at any time. You are building on someone else's reverse engineering of a third party's internal API.

**Consequences:**
- Pipeline silently stops pulling data (returns 403 or empty responses)
- MFA-enabled accounts may become entirely incompatible with automated login
- Rate limiting kicks in after repeated failed auth attempts (429 errors), with 1-hour lockout periods
- If you log in fresh each run instead of persisting tokens, you hit rate limits within a few runs

**Prevention:**
- Always persist OAuth tokens to disk (`~/.garminconnect` or `GARMINTOKENS` env var). Tokens are valid for ~1 year. Never re-authenticate from credentials on every run.
- Pin `garminconnect` and `garth` versions. Only upgrade deliberately after checking the changelog and GitHub issues.
- Consider disabling MFA on the Garmin account used for automation (use a dedicated automation account, not your personal one).
- Build a health check that runs before the main pipeline: if auth fails, alert immediately and skip the run rather than retrying in a loop (which triggers rate limits).
- Monitor the [python-garminconnect GitHub issues](https://github.com/cyberjunky/python-garminconnect/issues) -- breakages are reported there first.

**Detection:**
- HTTP 403 responses after previously successful auth
- "OAuth1 token is required" errors in logs
- 429 Too Many Requests from Garmin SSO
- Empty JSON responses with HTTP 200 (stealth failure)

**Phase relevance:** Phase 1 (data ingestion). This must be robust before anything downstream matters.

---

### Pitfall 2: Garmin API Returns 200 OK with Empty/Null Data

**What goes wrong:** The Garmin Connect API returns HTTP 200 with empty body, null values, or missing fields -- not an error code. Your pipeline processes this as "no data" and either stores empty records or crashes on null access. This is a silent data integrity failure.

**Why it happens:** Multiple causes converge:
- The watch has not synced to Garmin Connect yet when the pipeline runs (Bluetooth sync happens when phone is nearby; WiFi sync is inconsistent)
- Garmin server-side processing lag: sync completes but data takes minutes to hours to appear in the API
- Certain metrics (SpO2, HRV, Body Battery) require overnight computation and may not be available until mid-morning
- Garmin changes which fields are included in endpoint responses (the "modern dashboard" migration broke several endpoints in 2025)

**Consequences:**
- Historical database gets polluted with null/zero records that corrupt trend analysis
- LLM receives incomplete data and generates recommendations based on missing context
- Trend detection breaks when null days create artificial "drops" in metrics

**Prevention:**
- Never run the pipeline at the earliest possible time. Schedule for 7-8 AM (not 5 AM) to allow watch sync + server processing. Better yet: verify data completeness before proceeding.
- Implement a data completeness check before storing: define minimum required fields (HRV, sleep duration, Body Battery, stress) and reject/retry if any are null.
- Use an idempotent "upsert" pattern: if today's data is incomplete, allow the pipeline to re-run and update (not append) the record. Partition by date, overwrite the partition.
- Store the raw API response alongside the normalized data so you can detect and fix silent schema changes.

**Detection:**
- Monitoring: track the number of non-null fields per daily record. Alert if below threshold.
- Compare today's field count against the 7-day average field count.
- Log the raw JSON response size -- a response under 100 bytes for a daily summary is suspicious.

**Phase relevance:** Phase 1 (data ingestion) and Phase 2 (storage). The validation layer sits between ingestion and storage.

---

### Pitfall 3: LLM Hallucinating Health Recommendations

**What goes wrong:** The LLM generates plausible-sounding but fabricated health advice. It may invent supplement dosages, misinterpret HRV trends, recommend training intensities that are dangerous for the user's context, or cite non-existent studies. Research shows hallucination rates of 15-40% on clinical tasks even with state-of-the-art models.

**Why it happens:**
- LLMs are autoregressive text generators, not health experts. They pattern-match from training data.
- Biometric data interpretation requires context that the model doesn't inherently understand (e.g., HRV trends are individual-specific, not absolute)
- The model has no grounding mechanism -- it cannot verify its claims against medical literature in real-time
- Structured prompts reduce but do not eliminate hallucination (from ~66% to ~44% in one study; GPT-4o from 53% to 23%)

**Consequences:**
- Following fabricated supplement recommendations could cause harm (drug interactions, excessive dosages)
- Incorrect training recommendations could lead to injury or overtraining
- User develops false confidence in AI-generated protocols
- Liability exposure if recommendations cause harm, even for a personal tool

**Prevention:**
- Constrain the output space: provide explicit ranges and options in the prompt rather than letting the model generate freely. Example: "Recommend training intensity from [Rest, Easy, Moderate, Hard] based on these thresholds" rather than "What training should I do?"
- Include a health profile with known supplements, medications, and conditions so the model reasons within bounds.
- Add a "confidence" field to each recommendation in the output schema. Instruct the model to output LOW confidence when data is ambiguous or insufficient.
- Never let the LLM recommend specific dosages it wasn't given in the prompt context. Provide supplement options and dosage ranges in the health profile; the model selects, it does not invent.
- Include a prominent disclaimer in every email: "AI-generated analysis. Not medical advice. Consult a healthcare professional."
- Periodically review generated protocols manually for the first few weeks to calibrate prompt quality.

**Detection:**
- Recommendations that reference supplements or medications not in the health profile
- Dosage numbers that don't match the ranges in the health profile config
- Recommendations that contradict the data (e.g., "push hard today" when HRV is at a 30-day low)
- Any cited studies or specific statistics (LLMs fabricate these)

**Phase relevance:** Phase 3 (AI analysis). This is the core risk of the entire project.

---

### Pitfall 4: Timezone and Date Boundary Confusion

**What goes wrong:** Sleep data spans two calendar dates. HRV data uses overnight windows. Garmin timestamps may be in UTC, local time, or Unix timestamps with inconsistent timezone offsets. The pipeline assigns data to the wrong day, creating phantom trends, missing days, and double-counted metrics.

**Why it happens:**
- Garmin's API is inconsistent: some endpoints return UTC, some return local time, some return Unix timestamps. The timezone offset in activity data is not a timezone identifier (UTC-5 could be EST or CDT).
- Sleep from Monday night is really Tuesday's sleep. If you query "Monday's data" you might get Sunday night's sleep or miss Monday night's sleep entirely.
- Daylight saving time transitions cause one day to be 23 hours and another 25 hours.
- The watch may report in the timezone where the activity occurred, but the API may convert to the account's home timezone.

**Consequences:**
- Trend analysis shows false dips/spikes at timezone boundaries
- Sleep metrics are attributed to the wrong day, making daily protocols inaccurate
- DST transitions create duplicate or missing records twice a year
- Travel across timezones creates data that looks anomalous but is just misaligned

**Prevention:**
- Normalize all timestamps to UTC immediately upon ingestion. Store UTC. Convert to local only at display/email time.
- Define "health day" as the 24-hour window from the user's wake time, not midnight. Garmin's sleep data already uses a "calendar date" concept that attributes overnight sleep to the date you woke up -- follow this convention consistently.
- Use `datetime` with explicit `tzinfo` everywhere. Never use naive datetimes. Treat any naive timestamp from the API as suspect and log a warning.
- Test the pipeline explicitly across DST transitions with synthetic data.
- Store the raw Garmin timestamp alongside the normalized UTC timestamp so you can debug misalignment.

**Detection:**
- Days with zero sleep data adjacent to days with double sleep data
- Sudden 1-hour shifts in sleep timing twice a year (DST)
- Negative sleep durations or durations exceeding 24 hours

**Phase relevance:** Phase 1 (data ingestion) and Phase 2 (storage schema). Get this wrong and everything downstream is silently wrong.

---

## Moderate Pitfalls

Mistakes that cause significant rework, degraded quality, or reliability issues.

---

### Pitfall 5: Treating Garmin's Proprietary Scores as Ground Truth

**What goes wrong:** Body Battery, Training Load, Training Status, and Stress Level are proprietary Garmin algorithms, not raw physiological measurements. Building analysis that interprets these scores as if they were clinical measurements leads to incorrect conclusions and fragile logic.

**Why it happens:** Garmin presents these as authoritative metrics in their UI, and the numbers feel precise (e.g., Body Battery: 73). But the algorithms are opaque, change between firmware updates, and may not correlate with actual physiological state for all individuals.

**Prevention:**
- Use Garmin's proprietary scores as supplementary context, not primary inputs. Prioritize raw-ish metrics: resting heart rate, HRV (rMSSD), sleep stages/duration, SpO2.
- In the LLM prompt, explicitly label metrics as "Garmin's proprietary estimate" vs. "measured physiological data" so the model can weight them appropriately.
- Do not build hard-coded thresholds on proprietary scores (e.g., "if Body Battery < 30, recommend rest"). These thresholds are individual-specific and algorithm-version-specific.
- Instead, use relative trends: "Body Battery is 20% below your 7-day average" is more meaningful than "Body Battery is 45."

**Detection:**
- Recommendations that change dramatically after a Garmin firmware update (the algorithm changed, not the user's physiology)
- Hard-coded threshold values for Body Battery, Stress Level, or Training Load in the codebase

**Phase relevance:** Phase 3 (AI analysis prompt design). Affects how you instruct the LLM to interpret data.

---

### Pitfall 6: Unbounded Context Window in Trend Analysis

**What goes wrong:** Feeding "all historical data" into the Claude prompt for trend analysis. The context window fills up, costs skyrocket, and the model's attention degrades on long contexts -- it may focus on recent data and ignore patterns in the middle of the window.

**Why it happens:** It feels natural to send more data for better analysis. But Claude's 200K context window is not infinite, and even within it, attention quality varies. Each daily record with all biometric fields could be 2-4K tokens. Thirty days = 60-120K tokens of data alone, leaving less room for the health profile, prompt instructions, and output.

**Prevention:**
- Define a fixed rolling window: 7 days of detailed data + 30 days of daily summaries (key metrics only) + 90-day trend statistics (averages, min, max, standard deviation).
- Pre-compute trend statistics in Python, not in the LLM prompt. The LLM should receive "HRV 7-day avg: 45ms, 30-day avg: 52ms, trend: declining" rather than 30 raw daily HRV values.
- Use Claude's token counting API to estimate prompt size before sending. Set a hard ceiling (e.g., 50K tokens for the data portion).
- Structure the prompt so the most important data (today's metrics, recent trend summaries) appears first, and older context appears last.

**Detection:**
- API costs increasing linearly over time as the history window grows
- Prompt token counts exceeding 100K
- Recommendations that seem to ignore recent data in favor of older patterns

**Phase relevance:** Phase 3 (AI analysis) and Phase 4 (trend analysis). Design the data windowing strategy before building the prompt.

---

### Pitfall 7: Email Delivery Landing in Spam

**What goes wrong:** The Daily Protocol email lands in the spam folder. You don't notice for days because the pipeline reports success (email was sent), but it was never read.

**Why it happens:**
- Gmail and Yahoo enforce SPF, DKIM, and DMARC requirements as of 2024. Emails without proper authentication are aggressively filtered.
- Sending from a personal domain without proper DNS records (SPF, DKIM, DMARC) flags the email as suspicious.
- Using raw Python `smtplib` with Gmail App Passwords works initially but degrades over time as Google's heuristics classify the sending pattern.
- HTML-heavy emails with poor text-to-image ratios trigger spam filters.
- A new sending domain has zero reputation.

**Prevention:**
- Use a transactional email service (Resend, Postmark, or Amazon SES) instead of raw SMTP. These services handle SPF/DKIM/DMARC and maintain sender reputation.
- For a personal tool, the simplest path: use Resend with a verified domain. Setup takes 10 minutes, costs nothing at this volume (1 email/day), and deliverability is near-perfect.
- If using Gmail SMTP: set up an App Password, and send from and to the same Gmail address. Same-account delivery is reliable.
- Keep the email content clean: primarily text, minimal HTML formatting, no images, no link-heavy content.
- Send a test email on day one and verify it arrives in the inbox, not spam.

**Detection:**
- Check the spam folder manually the first week
- Add a read receipt or tracking pixel (though this adds complexity and may itself trigger spam filters)
- Log email send status and periodically verify inbox delivery

**Phase relevance:** Phase 5 (email delivery). Not technically complex but easy to overlook until the pipeline is "done" and nothing arrives.

---

### Pitfall 8: Non-Idempotent Pipeline Causes Duplicate Data

**What goes wrong:** The pipeline runs, partially fails (e.g., data pulled but email not sent), and on retry inserts duplicate records into the database. Trend analysis now sees doubled values for that day.

**Why it happens:**
- Using INSERT instead of UPSERT for daily records
- No deduplication key (e.g., user_id + date)
- The pipeline has no concept of "already processed this day"
- Cron retries on failure without checking what already succeeded

**Prevention:**
- Use UPSERT (INSERT ON CONFLICT UPDATE) with a unique constraint on the date column. Running the pipeline twice for the same day overwrites, never duplicates.
- Make each pipeline stage independently idempotent:
  - Data pull: always fetches today's data (idempotent by nature)
  - Storage: upsert, not insert
  - Analysis: regenerate, not append
  - Email: deduplicate by checking if today's email was already sent (or accept that a re-send is harmless for a personal tool)
- Store pipeline run status (pulled/analyzed/emailed) so partial failures can resume from the failed step.

**Detection:**
- Multiple records for the same date in the database
- Trend charts showing sudden spikes (doubled values)
- Email received twice for the same day

**Phase relevance:** Phase 1 (data ingestion) and Phase 2 (storage). Build idempotency into the schema from day one.

---

### Pitfall 9: Garmin Endpoint Deprecation Breaks Silently

**What goes wrong:** Garmin migrates to a "modern dashboard" and changes API endpoint paths. Some endpoints (sleep, stress, SpO2, respiration) stop returning data or return different JSON structures. The library wraps these endpoints, so you don't notice until your data goes stale or schema validation fails.

**Why it happens:** Garmin's web frontend evolves independently of the unofficial API. When Garmin redesigns their dashboard, the backend endpoints change. The `python-garminconnect` library tracks these changes but there's always a lag between Garmin's change and the library update.

**Prevention:**
- Validate the shape of API responses against an expected schema before storing. If the schema changes, fail loudly rather than storing malformed data.
- Store the raw JSON response in a `raw_response` column alongside normalized data. This lets you re-process historical data when the schema changes.
- Subscribe to the [python-garminconnect releases](https://github.com/cyberjunky/python-garminconnect/releases) for breaking change notifications.
- Build a simple data freshness check: if any metric hasn't been updated in 48 hours, trigger an alert.

**Detection:**
- Fields that were previously populated are now null or missing from the JSON
- JSON response structure changes (new nesting, renamed keys)
- Library changelog mentions endpoint migrations

**Phase relevance:** Phase 1 (data ingestion). Build response validation early.

---

## Minor Pitfalls

Mistakes that cause annoyance, minor bugs, or suboptimal results.

---

### Pitfall 10: Over-Engineering the Health Profile Config

**What goes wrong:** The static health profile config file grows into a complex schema with nested objects, validation rules, and version management. It becomes harder to maintain than a simple database table and slows down iteration on prompt design.

**Prevention:**
- Start with a flat YAML or TOML file. No nesting deeper than 2 levels.
- Include only what the LLM prompt actually uses: age, weight, resting HR baseline, known conditions, current medications, current supplements with dosages, training goals, sleep context.
- Resist adding fields "for later." The config should match the current prompt template 1:1.

**Phase relevance:** Phase 2 (health profile). Keep it simple; expand only when the prompt needs it.

---

### Pitfall 11: Prompt Drift Without Version Control

**What goes wrong:** The LLM prompt evolves through manual tweaking. Previous versions that worked well are lost. A "small improvement" degrades output quality in a way that's not noticed for days.

**Prevention:**
- Store prompts as versioned template files in the repo, not inline strings.
- Log which prompt version generated each daily protocol in the database.
- When changing prompts, keep the previous version and A/B test by reviewing outputs side-by-side before committing.

**Phase relevance:** Phase 3 (AI analysis). Treat prompts as code artifacts.

---

### Pitfall 12: Ignoring Garmin Data Granularity Differences

**What goes wrong:** Treating all metrics as if they have the same sampling frequency. HRV might be a single overnight average, while stress has per-minute readings. Comparing or combining metrics at different granularities leads to misleading analysis.

**Prevention:**
- Document the granularity of each metric at ingestion time: HRV (overnight average), stress (per-minute or daily summary), sleep (per-stage breakdown), Body Battery (per-minute or daily range).
- For the LLM prompt, present all metrics at the daily summary level. Per-minute data should be pre-aggregated (daily min, max, average, time-in-zone).
- Do not send raw per-minute data to the LLM -- it wastes tokens and the model cannot meaningfully process hundreds of minute-level readings.

**Phase relevance:** Phase 1 (data ingestion) and Phase 2 (storage schema design).

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|---|---|---|
| Garmin data ingestion | Auth breakage (Pitfall 1), silent empty responses (Pitfall 2), endpoint deprecation (Pitfall 9) | Token persistence, data completeness validation, response schema checks |
| Data storage (Supabase) | Timezone confusion (Pitfall 4), duplicate records (Pitfall 8) | UTC normalization, upsert with date constraint, raw JSON archival |
| AI analysis (Claude) | Hallucinated recommendations (Pitfall 3), unbounded context (Pitfall 6), prompt drift (Pitfall 11) | Constrained output schema, pre-computed trends, versioned prompts |
| Health profile | Over-engineering config (Pitfall 10) | Flat YAML, match prompt needs exactly |
| Email delivery | Spam folder (Pitfall 7) | Use transactional email service or same-account Gmail |
| Trend analysis | Proprietary scores as truth (Pitfall 5), granularity mismatch (Pitfall 12) | Raw metrics first, daily-level aggregation |
| Pipeline orchestration | Non-idempotency (Pitfall 8), stale data timing (Pitfall 2) | Upsert pattern, late-morning schedule, pipeline stage tracking |

---

## Sources

### Garmin Authentication and API
- [Login rate limit (Part II) - python-garminconnect #213](https://github.com/cyberjunky/python-garminconnect/issues/213)
- [Login rate limit - python-garminconnect #127](https://github.com/cyberjunky/python-garminconnect/issues/127)
- [MFA OAuth1 token error - python-garminconnect #312](https://github.com/cyberjunky/python-garminconnect/issues/312)
- [403 Forbidden after Garth auth - python-garminconnect #303](https://github.com/cyberjunky/python-garminconnect/issues/303)
- [Modern dashboard endpoints - python-garminconnect #207](https://github.com/cyberjunky/python-garminconnect/issues/207)
- [Garmin Unofficial API notes](https://wiki.brianturchyn.net/programming/apis/garmin/)
- [garth library - Garmin SSO auth](https://github.com/matin/garth)

### Garmin Data and Timezone
- [Garmin Connect data recording in UTC timezone](https://forums.garmin.com/apps-software/mobile-apps-web/f/garmin-connect-web/153446/connect-data-recording-in-utc-timezone-six-hours-off)
- [Garmin's approach to time zones](https://thomasclowes.com/garmins-approach-to-time-zones/)
- [Garmin API empty response issues](https://forums.garmin.com/apps-software/mobile-apps-web/f/garmin-connect-mobile-andriod/364977/seeking-help-garmin-connect-api-integration-issues-with-empty-responses)
- [Fitness tracker data granularity](https://www.thryve.health/blog/fitness-tracker-data-granularity-unified-api)

### LLM Health Risks
- [Clinicians' Guide to LLMs and Hallucinations](https://pmc.ncbi.nlm.nih.gov/articles/PMC11815294/)
- [Medical Hallucination in Foundation Models](https://arxiv.org/html/2503.05777v2)
- [LLM vulnerability to adversarial hallucination in clinical decision support](https://pmc.ncbi.nlm.nih.gov/articles/PMC12318031/)
- [Hidden Risk of AI Hallucinations in Medical Practice](https://www.annfammed.org/content/hidden-risk-ai-hallucinations-medical-practice)
- [Medical malpractice liability in LLM AI](https://pubmed.ncbi.nlm.nih.gov/38295300/)

### Email Deliverability
- [Transactional email deliverability - MailChannels](https://blog.mailchannels.com/how-to-improve-transactional-email-deliverability-and-stay-out-of-the-spam-folder/)
- [Email deliverability guide 2026](https://www.emailvendorselection.com/email-deliverability-guide/)
- [Email deliverability issues - Mailtrap](https://mailtrap.io/blog/email-deliverability-issues/)

### Data Pipeline Best Practices
- [ETL Best Practices 2026](https://oneuptime.com/blog/post/2026-02-13-etl-best-practices/view)
- [Mastering Idempotency in Data Analytics](https://python-bloggers.com/2024/12/mastering-idempotency-in-data-analytics-ensuring-reliable-pipelines/)
- [Supabase TimescaleDB extension docs](https://supabase.com/docs/guides/database/extensions/timescaledb)

### HRV and Biometric Interpretation
- [Garmin HRV Status](https://www.garmin.com/en-US/garmin-technology/health-science/hrv-status/)
- [HRV - everything you need to know](https://the5krunner.com/2025/05/20/hrv-everything-you-need-to-know-garmin-whoop-oura-hrv-hrv4training-training-readiness/)
- [Composite health scores in consumer wearables](https://www.degruyterbrill.com/document/doi/10.1515/teb-2025-0001/html?lang=en)
