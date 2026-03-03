# Garmin Data & Integration Research Synthesis

*Date: 2026-03-03*

---

## TL;DR

- **Activity weblinks work; health data weblinks do NOT exist.** Garmin lets you share activities via `https://connect.garmin.com/activity/{id}` but there is no equivalent for sleep, stress, body battery, HRV, or any other health metric. Health data is locked behind authentication.
- **The official Garmin Health API is enterprise-only** — requires business approval, commercial license, and serving 2+ users. Personal projects get rejected.
- **`python-garminconnect` is the best path** for a personal project — 100+ endpoints, all health data, actively maintained, free, tokens last ~1 year.
- **Email is the easiest delivery channel** (zero cost, zero user friction). Telegram is the best interactive option (free, instant bot setup, no business verification). WhatsApp requires Meta Business Verification — wrong for v1.
- **The delivery channel is the least important part.** The hard problem is reliable data extraction + intelligent analysis. Email validates the core product; everything else layers on top.

---

## 1. How the Garmin App & API Works

### The Data Flow

```
[Garmin Watch] --Bluetooth--> [Garmin Connect App (phone)]
                                        |
                                   [Garmin Cloud]
                                   (connect.garmin.com)
                                        |
                    +-------------------+-------------------+
                    |                   |                   |
            [Official Health API]  [Unofficial API]  [Third-party sync]
            (enterprise only)     (garminconnect)    (Strava, Apple Health)
```

Garmin devices sync to the phone app via Bluetooth, which uploads to Garmin's cloud. From there, data can be accessed through official APIs (restricted), unofficial APIs (reverse-engineered), or third-party integrations.

### What Garmin Tracks

| Category | Metrics |
|----------|---------|
| **Heart** | Resting HR, all-day HR (2-15s intervals), HR zones, HRV (nightly RMSSD + 7-day baseline) |
| **Sleep** | Duration, stages (deep/light/REM/awake), sleep score, SpO2 during sleep, respiration, stress, HRV status |
| **Stress & Recovery** | Stress level (0-100, every ~3 min), Body Battery (charge/drain curve), training readiness |
| **Activity** | Type, duration, distance, pace, HR, cadence, power, elevation, GPS, training effect, training load |
| **Body** | Weight, BMI, body fat %, muscle mass, bone mass, body water % |
| **Respiratory** | Breathing rate (all-day, sleep, activity) |
| **Blood Oxygen** | SpO2 (overnight, spot checks, continuous on some devices) |
| **Fitness** | VO2 max, fitness age, training status, intensity minutes |

---

## 2. Sharing: What Works and What Doesn't

### Activities: Public Weblinks Exist

- URL format: `https://connect.garmin.com/activity/{activityID}`
- Shared from: Garmin Connect app → Activity → Share → Web Link
- Requires privacy set to "Everyone"
- Shows: distance, time, map, pace, HR, elevation, calories
- Does NOT show: full lap splits, interval details
- No API to generate links — you need the activity ID (obtainable via unofficial API)

### Health Data: NO Public Weblinks

**This is a hard limitation.** Sleep, stress, body battery, steps, HR summaries, HRV — none of these can be shared via a public URL. Garmin only offers:

- **Connections** — other Garmin users you add as friends (requires their Garmin login)
- **Authorized Viewers** — specific people granted access (requires Garmin login)
- **Third-party sync** — one-way push to Apple Health, Google Health Connect (no public links)

**Bottom line:** You cannot get health data by having a user share a link. You need either API access or credential-based extraction.

---

## 3. All Paths to Garmin Health Data

### Path A: `python-garminconnect` Library (RECOMMENDED)

| Aspect | Detail |
|--------|--------|
| **What** | Reverse-engineered Python wrapper for Garmin Connect's internal API |
| **GitHub** | https://github.com/cyberjunky/python-garminconnect (~1,800 stars) |
| **Data** | ALL health metrics + activities + write operations (100+ endpoints) |
| **Auth** | Username/password → OAuth tokens cached ~1 year via `garth` library |
| **Rate limits** | ~1 request/5 min for some endpoints; batch daily pulls recommended |
| **Risk** | Unofficial — could break if Garmin changes APIs (historically fixed within days) |
| **Cost** | Free |
| **Status** | Actively maintained (v0.2.26, 57+ releases, used by Home Assistant) |

```python
from garminconnect import Garmin

client = Garmin("email", "password")
client.login()

today = "2026-03-03"
stats = client.get_stats(today)              # Steps, calories, HR, body battery
sleep = client.get_sleep_data(today)         # Sleep stages, scores
stress = client.get_stress_data(today)       # Stress time series
hrv = client.get_hrv_data(today)             # HRV status + values
spo2 = client.get_spo2_data(today)           # Blood oxygen
readiness = client.get_training_readiness(today)  # Training readiness
```

### Path B: Garmin Health API (Official — Enterprise Only)

| Aspect | Detail |
|--------|--------|
| **What** | Official REST API with webhook push notifications |
| **Auth** | OAuth 1.0a with consumer key/secret (issued to approved partners) |
| **Data** | Daily summaries, epochs (15-min), sleep, stress, body comp, activities, SpO2, HRV |
| **Push model** | Webhook pings on device sync → your server pulls full data |
| **Access** | Business application required, evaluation then production keys, commercial license fee |
| **Verdict** | **Not viable for personal projects** — explicitly excludes hobbyists |

### Path C: Strava API as Intermediary (Activities Only)

| Aspect | Detail |
|--------|--------|
| **What** | Garmin auto-syncs activities to Strava; Strava has a public OAuth2 API |
| **Data** | Activities only (distance, pace, HR, power, GPS, laps) |
| **Missing** | ALL health data (sleep, stress, body battery, HRV, SpO2, training readiness) |
| **Verdict** | Useful for activity enrichment but **cannot replace direct Garmin access** for health data |

### Path D: Garmin Bulk Export + FIT Parsing

| Aspect | Detail |
|--------|--------|
| **What** | Official data export at garmin.com/account/datamanagement/ |
| **Data** | Everything — activities as FIT/GPX/TCX, health stats |
| **Parsing** | FIT files contain per-second sensor data; parse with `garmin_fit_sdk` or `fitparse` |
| **Limitation** | Manual trigger, no automation, good for initial historical backfill only |

### Path E: Aggregator APIs (Terra, Vital)

| Aspect | Detail |
|--------|--------|
| **Terra API** | ~$0.10/1K calls, covers 30+ wearables including Garmin, REST + webhooks |
| **Vital API** | $99+/month production, enterprise-focused |
| **Trade-off** | Adds cost + middleman; loses Garmin-specific metrics (Body Battery, training load) |
| **Verdict** | Safety net if `python-garminconnect` breaks, not primary path |

### Path F: Connect IQ (Watch Apps) — NOT VIABLE

Connect IQ apps **cannot send data to external servers**. No networking capability, no filesystem access. Data stays on the device. Not a viable extraction path.

### Path G: Apple Health / Google Health Connect — NOT VIABLE (Server-Side)

Both are device-local APIs only (HealthKit on iOS, Health Connect on Android). No server-side access. Cannot be used by a backend AI agent.

---

## 4. All Delivery Channels Compared

| Channel | Complexity | Cost/mo | User Friction | Richness | Interactive | When |
|---------|-----------|---------|---------------|----------|-------------|------|
| **Email** | 2/5 | $0 | Lowest (1/5) | Full | No | **v1** |
| **Telegram Bot** | 1/5 | $0 | Low (2/5) | Full | Yes (keyboards, commands) | **v1.1** |
| **WhatsApp** | 3/5 | ~$0.12 | Low-Med (2/5) | Full | Yes (templates) | v2 |
| **Web Dashboard** | 4/5 | $0-20 | Medium (3/5) | Full + charts | Yes (exploration) | v2 |
| **Push Notifications** | 4-5/5 | $0-99/yr | Med-High (3-4/5) | Brief → full | Medium | v2 (with dashboard) |
| **SMS** | 2/5 | ~$5-6 | Lowest (1/5) | **Terrible** (160 chars) | Low | **Never** |
| **Voice (Alexa)** | 4/5 | $0 | Medium (3/5) | Poor (audio only) | Medium | v3+ |

### Email (RECOMMENDED for v1)

- Cron job pulls data daily → Claude API generates protocol → Resend/SES sends email
- **Resend**: 3,000 free emails/month (more than enough for daily sends)
- **Amazon SES**: $0.10 per 1,000 emails
- User does nothing — briefing arrives in inbox every morning
- Zero new apps, zero new habits

### Telegram Bot (Best Interactive Option)

- Create bot via @BotFather in 2 minutes, completely free
- Rich Markdown formatting, inline keyboards, 4,096 char messages
- Can send chart images, PDF reports
- No business verification, no template approval (unlike WhatsApp)
- Strictly superior to WhatsApp for personal projects on every technical dimension
- Only downside: user must use Telegram

### WhatsApp (Viable for v2+)

- Requires **Meta Business Verification** (days-weeks of bureaucratic process)
- Pre-approved message templates required for proactive messages
- $0.004/message (utility), negligible cost
- Two-way interaction within 24-hour session windows
- Right for multi-user product, wrong for personal v1

### Web Dashboard (v2)

- Best for visual exploration, trends, historical data
- **garmin-grafana** (2,800 stars): Docker + InfluxDB + Grafana, pre-built dashboards
- Pull-based (user must visit), doesn't replace daily push delivery
- Significant frontend development effort

---

## 5. Key Open-Source Tools

| Tool | Type | Stars | Status | Use Case |
|------|------|-------|--------|----------|
| **python-garminconnect** | Python API wrapper | ~1,800 | Active (2026) | Primary data extraction |
| **garth** | Python auth library | ~500 | Active | Auth engine (used by garminconnect) |
| **garmin-connect (npm)** | Node.js wrapper | — | Active | JS alternative (fewer endpoints) |
| **garmin_fit_sdk** | FIT parser (Python) | Official | Active | Per-second activity data |
| **pe-st/garmin-connect-export** | Bulk export tool | ~800 | Active | Historical data backfill |
| **tcgoetz/GarminDB** | SQLite data warehouse | — | Active | Long-term data storage |
| **garmin-grafana** | Grafana dashboards | ~2,800 | Active | Visual dashboard |
| **garmy** | AI-oriented wrapper | — | Active | MCP server for AI agents |

---

## 6. Recommended Architecture

```
Phase 1 (v1): Email Daily Protocol
─────────────────────────────────────────

[Garmin Watch] → [Garmin Connect Cloud]
                         │
                  [python-garminconnect]
                  (cron: daily 6 AM)
                         │
                    [Supabase DB]
                    (store metrics + trends)
                         │
                    [Claude API]
                    (analyze + generate protocol)
                         │
                    [Resend / SES]
                    (send email)
                         │
                    [User's Inbox]


Phase 1.1: Add Telegram Bot
─────────────────────────────────────────

                    [Claude API]
                         │
                    ┌────┴────┐
                [Email]   [Telegram Bot]
                          (interactive queries)


Phase 2: Web Dashboard + Push
─────────────────────────────────────────

                    [Supabase DB]
                         │
                    ┌────┴────┐
                [API]      [Dashboard]
                 │         (Next.js + charts)
            [Push notif]
```

---

## 7. Answers to Your Specific Questions

**Q: Can you share health data via weblinks like you can with training activities?**
**A: No.** Activity sharing via weblinks works. Health data (sleep, stress, body battery, etc.) has no public URL sharing mechanism. Health data requires authenticated access — either the official enterprise API or the unofficial `python-garminconnect` library.

**Q: Which delivery path is easiest?**
**A: Email.** Zero cost, zero user friction, zero new apps. Cron + garminconnect + Claude API + Resend = done. Telegram is the easiest *interactive* option (free, 2-minute bot setup).

**Q: What about WhatsApp?**
**A: Wrong for v1.** Requires Meta Business Verification, template pre-approval, a dedicated business phone number. All overhead, no benefit over Telegram for a personal project. Revisit for multi-user v2+.

**Q: Can Connect IQ apps send data out?**
**A: No.** Connect IQ has no networking capability. Data stays on the watch. Not a viable path.

**Q: What's the risk of using the unofficial API?**
**A: Low in practice.** No accounts banned, no legal action, no active blocking as of March 2026. The library adapts to Garmin's changes within days. Main risk is temporary breakage during API changes.

---

## Detailed Research Files

For deep-dives, see the companion documents in this directory:

- **GARMIN_DATA_ACCESS.md** — Full API documentation, endpoints, auth flows, data fields, rate limits
- **GARMIN_DATA_TOOLS.md** — Open-source libraries, FIT SDK, export tools, comparison matrix
- **INTEGRATION_PATHS.md** — All 9 delivery channels with detailed analysis, pricing, code examples

---

*Research conducted with web search across Garmin developer docs, GitHub repositories, Meta/WhatsApp API docs, Telegram Bot API, Twilio pricing, Firebase docs, and developer community forums.*
