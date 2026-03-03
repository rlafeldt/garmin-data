# Integration Paths: AI Health Agent to Garmin Data

Last updated: 2026-03-03

---

## Prerequisite: Getting the Garmin Data

Before evaluating delivery channels, every path requires a data source. The data ingestion layer is **independent** of the delivery mechanism. The primary options are:

| Method | Data Richness | Reliability | Setup |
|--------|--------------|-------------|-------|
| **python-garminconnect** (unofficial) | Full (sleep, HRV, stress, Body Battery, SpO2, training load, VO2 max, activities) | Medium (can break on Garmin changes) | Simple (pip install, username/password + token persistence) |
| **Garmin Health API** (official) | Full | High | Hard (enterprise approval required, OAuth 2.0, must serve 2+ users) |
| **Garmin bulk export** | Full (but FIT files need parsing) | High (official) | Manual trigger, no automation |
| **Strava API** (intermediary) | Activities only (no sleep, stress, Body Battery) | High | Moderate (OAuth 2.0, well-documented) |
| **Terra API / Vital API** (aggregators) | Good subset | High | Moderate (OAuth, paid tiers) |
| **Google Health Connect** | Good subset (steps, HR, sleep, activities) | High | Android-only, limited vs direct Garmin |

**For BioIntelligence v1**: `python-garminconnect` is the clear choice. It provides the richest data set with the simplest setup for a single-user personal tool. All delivery paths below assume data is already extracted via this library and stored in Supabase.

---

## Path 1: Email Delivery

### How It Works
A daily automated pipeline pulls Garmin data, runs Claude API analysis, generates a Daily Protocol, and sends it as a formatted email each morning.

### Garmin's Native Email Features
- Garmin Connect sends **weekly and monthly Wellness/Fitness Reports** via email (toggle in app: Settings > Notifications > Email Notifications)
- Reports cover activity summaries, sleep, heart rate, progress toward goals
- **No daily email reports** exist natively
- The native reports are too generic for AI analysis — they summarize, they do not advise
- Parsing native Garmin emails is possible but yields limited, pre-aggregated data

### Implementation Approach
1. **Cron job / scheduler** triggers daily at configured time (e.g., 6 AM)
2. Python script pulls yesterday's data via `python-garminconnect`
3. Data stored in Supabase, rolling trends computed
4. Claude API call with data + health profile generates Daily Protocol
5. Transactional email service sends formatted HTML email

### Email Service Options

| Service | Free Tier | Paid Starting | Best For |
|---------|-----------|---------------|----------|
| **Resend** | 3,000/month | $20/mo for 50K | Developer experience, React Email templates |
| **Amazon SES** | 62K/month (first year on EC2) | $0.10 per 1,000 | Cost at scale |
| **Postmark** | None | $15/mo for 10K | Deliverability (99%+) |
| **SendGrid** | 100/day trial | $19.95/mo for 50K | Advanced analytics |

For a single-user daily email, **Resend** (3,000 free emails/month = ~100 emails/day capacity) or **Amazon SES** (effectively free for 1 email/day) are optimal.

### Assessment

| Dimension | Rating | Notes |
|-----------|--------|-------|
| **Technical Complexity** | 2/5 | Straightforward: cron + API call + email send |
| **Cost** | ~$0/month | Free tiers cover single-user daily emails easily |
| **User Friction** | 1/5 (lowest) | User does nothing — email arrives in inbox |
| **Data Timing** | Delayed (daily) | Previous day's data analyzed each morning |
| **Data Richness** | 5/5 | Full Garmin data set via python-garminconnect |
| **Reliability** | High | Email delivery is mature, well-understood |

### Verdict
**RECOMMENDED for v1.** Email is the simplest delivery channel with the lowest user friction. The user's existing email workflow requires zero new apps or habits. Aligns perfectly with the Daily Protocol concept — a morning briefing consumed passively.

---

## Path 2: WhatsApp Integration

### How It Works
An AI agent sends daily health insights as WhatsApp messages to the user. Could support interactive queries ("How was my sleep this week?").

### Technical Implementation
- **WhatsApp Cloud API** (Meta-hosted): Fastest setup, no servers needed
- **WhatsApp Business API** (self-hosted): More control, higher setup cost
- Both require **Meta Business Verification** (submit business docs, days to weeks for approval)
- Messages outside the 24-hour customer-initiated window require **pre-approved template messages**
- Health summaries classify as **utility messages**

### Pricing (Post-July 2025 per-template model)

| Message Type | US Price | Notes |
|-------------|----------|-------|
| Utility template | $0.004/msg | Health summaries, reminders |
| Marketing template | $0.025/msg | Promotional content |
| Service (user-initiated) | Free | Responses within 24hr window |

For 1 daily message: ~$0.12/month (utility) — negligible cost.

### Requirements
1. Meta Business Account (verified)
2. WhatsApp Business phone number (cannot be personal number)
3. Template message approval (1-2 days per template)
4. Webhook endpoint for receiving user messages (if interactive)
5. SSL certificate on webhook domain

### Assessment

| Dimension | Rating | Notes |
|-----------|--------|-------|
| **Technical Complexity** | 3/5 | Business verification, template approval, webhook setup |
| **Cost** | ~$0.12/month | Negligible per-message cost |
| **User Friction** | 2/5 | User must add bot number to WhatsApp, but no new app |
| **Data Timing** | Delayed (daily) or on-demand if interactive |
| **Data Richness** | 5/5 | Same data, different delivery |
| **Interactivity** | High | User can ask follow-up questions |

### Pros
- WhatsApp is already on most phones (2B+ users globally)
- Rich formatting: bold, italic, lists, emojis
- Two-way: user can ask questions, request specific metrics
- Push notifications ensure visibility
- Message history preserved in chat

### Cons
- Business verification is bureaucratic and designed for companies, not personal projects
- Template messages must be pre-approved — cannot dynamically change format without re-approval
- 24-hour session window limits free-form interaction
- Character limits on template messages (1024 chars for body)
- Meta can revoke API access
- Cannot send truly rich HTML (no tables, charts, or embedded images in templates)

### Verdict
**VIABLE for v2 as an interactive layer.** The business verification overhead makes this a poor v1 choice, but the two-way interaction capability is compelling for a conversational health agent. Consider after email delivery proves the core value.

---

## Path 3: Web Dashboard

### How It Works
A custom web application that visualizes Garmin health data with trends, charts, and AI-generated insights. The user visits a URL to see their health data and Daily Protocol.

### Existing Open-Source Projects

| Project | Stack | Features |
|---------|-------|----------|
| **garmin-grafana** (arpanghosh8453) | Docker/Python/InfluxDB/Grafana | 2800+ GitHub stars. Sleep stages, HRV, SpO2, Body Battery, stress, steps, GPS tracks. Heatmaps, histograms, long-term trends. Pre-built Grafana dashboards. |
| **Garmin-dashboard** (haydentbs) | Python/PostgreSQL/Flask/Next.js/Chart.js | Daily steps, distance, goals with time filters (7/14/30 days). Containerized. |
| **garmin-report** (paigevogie) | Python/React/Next.js | Garmin data visualization with modern frontend. |
| **Strapi + Next.js** (mxd.codes tutorial) | Next.js/React-Leaflet/Strapi CMS | Activity maps, routes, elevation, metrics. |

### Build-Your-Own Approach

**Grafana stack** (recommended for visualization-first):
- Docker Compose: Python data puller + InfluxDB + Grafana
- Pre-built dashboard templates available (IDs 24786, 23245)
- Powerful time-series visualization out of the box
- Self-hosted for privacy

**Next.js stack** (recommended for custom UX):
- Next.js frontend with Chart.js or Recharts
- Supabase as backend (already in BioIntelligence stack)
- API routes for data fetching
- Full control over UI/UX

### Assessment

| Dimension | Rating | Notes |
|-----------|--------|-------|
| **Technical Complexity** | 4/5 | Full web app: frontend, backend, hosting, auth, data viz |
| **Cost** | $0-20/month | Vercel free tier + Supabase free tier; or VPS for self-hosting |
| **User Friction** | 3/5 | User must visit URL; no push mechanism |
| **Data Timing** | Near real-time | Can refresh on page load or poll |
| **Data Richness** | 5/5 | Full data with visual trends, charts, historical views |
| **Development Time** | High | Weeks to months for polished dashboard |

### Pros
- Richest visual experience (charts, trends, maps)
- Full historical data exploration
- Can embed AI insights alongside raw data
- Existing open-source projects accelerate development
- Serves as portfolio/demo piece

### Cons
- Pull-based: user must remember to visit
- Significant frontend development effort
- Hosting and maintenance burden
- Does not solve the "morning briefing" problem — it is a reference tool, not a delivery mechanism
- Explicitly listed as **Out of Scope** for v1 in project requirements

### Verdict
**DEFERRED to v2 (PLAT-01 in requirements).** A dashboard complements but does not replace the Daily Protocol. Build this after email delivery validates the core intelligence layer. The Grafana stack is the fastest path if visualization is the primary goal; Next.js + Supabase is better for a custom product experience.

---

## Path 4: Telegram Bot

### How It Works
A Telegram bot sends daily health summaries and supports interactive queries. User adds the bot on Telegram and receives messages.

### Technical Implementation
1. Create bot via @BotFather (instant, free)
2. Receive API token
3. Implement bot using Python libraries (`python-telegram-bot`, `aiogram`)
4. Send messages via HTTP POST to `api.telegram.org/bot{token}/sendMessage`
5. Schedule daily sends via cron
6. Handle incoming commands for interactive queries

### Key Features
- **Formatting**: Full Markdown and HTML support in messages (bold, italic, code blocks, links)
- **Message length**: Up to 4,096 characters per message
- **Rate limits**: 30 messages/second per chat; 1 message/second globally
- **Inline keyboards**: Interactive buttons for "Show sleep details", "Compare to last week"
- **File sending**: Can send charts as images, PDFs as documents
- **No template approval**: Send any content, any time

### Assessment

| Dimension | Rating | Notes |
|-----------|--------|-------|
| **Technical Complexity** | 1/5 | Easiest of all paths. Create bot in 2 minutes, send messages via HTTP. |
| **Cost** | $0/month | Telegram Bot API is completely free. Server costs only. |
| **User Friction** | 2/5 | User must install Telegram (if not already) and start bot |
| **Data Timing** | Delayed (daily) or real-time on-demand |
| **Data Richness** | 5/5 | Same data; can send images (charts) and files (PDFs) |
| **Interactivity** | Very High | Commands, inline keyboards, free-form conversation |

### Pros
- **Zero cost** for messaging (Telegram's biggest advantage over WhatsApp)
- **No business verification** needed — anyone can create a bot instantly
- **No template approval** — send any message format at any time
- Rich formatting with Markdown/HTML
- Inline keyboards for interactive navigation
- Can send images (chart screenshots), documents (PDF reports)
- Bot creation takes 2 minutes via @BotFather
- Excellent Python libraries (`python-telegram-bot` is mature, well-documented)
- Webhook or long-polling for receiving user messages

### Cons
- Telegram has smaller user base than WhatsApp (900M vs 2B)
- User must install Telegram if they do not already use it
- No end-to-end encryption for bot messages (unlike Signal or WhatsApp E2E)
- Bot messages can feel less "personal" than email
- No native scheduling — requires external cron

### Telegram vs WhatsApp Comparison

| Feature | Telegram Bot | WhatsApp Cloud API |
|---------|-------------|-------------------|
| Setup time | 2 minutes | Days to weeks (verification) |
| Cost per message | Free | $0.004+ per template |
| Template approval | Not needed | Required for proactive messages |
| Business verification | Not needed | Required |
| Message formatting | Markdown + HTML + inline keyboards | Limited formatting in templates |
| File sharing | Images, PDFs, any file type | Images, PDFs (with restrictions) |
| Interactive buttons | Inline keyboards (unlimited) | Quick reply buttons (max 3) |
| User base | ~900M | ~2B |

### Verdict
**EXCELLENT alternative or complement to email.** Telegram is objectively the easiest and cheapest messaging integration. For a personal project, it is strictly superior to WhatsApp in every technical dimension. The only drawback is requiring the user to use Telegram. Consider as a v1.1 addition alongside email — adds interactivity without WhatsApp's bureaucratic overhead.

---

## Path 5: SMS (Twilio)

### How It Works
Send daily health summaries via SMS using Twilio or similar programmable SMS APIs.

### Twilio Pricing (2025-2026)

| Component | Cost |
|-----------|------|
| US phone number | ~$1/month |
| Outbound SMS (US) | $0.0083/segment (160 chars) |
| Carrier passthrough fees | ~$0.003/segment |
| 10DLC registration | $15 one-time + $4/month |
| Failed message fee | $0.001/attempt |

For 1 daily SMS: ~$5.30/month (number + registration + ~30 messages).

### Alternatives to Twilio

| Provider | Per SMS (US) | Notes |
|----------|-------------|-------|
| **Plivo** | ~$0.008 | Competitive pricing, good API |
| **Sinch** | ~$0.008-0.01 | High uptime SLA |
| **Vonage (Nexmo)** | ~$0.007 | Good international coverage |
| **Amazon SNS** | ~$0.00645 | Cheapest, AWS integration |

### Assessment

| Dimension | Rating | Notes |
|-----------|--------|-------|
| **Technical Complexity** | 2/5 | Simple API call; 10DLC registration adds friction |
| **Cost** | ~$5-6/month | Not free; phone number + per-message + registration fees |
| **User Friction** | 1/5 | User does nothing — SMS arrives on their phone |
| **Data Timing** | Delayed (daily) |
| **Data Richness** | 1/5 | 160 chars per segment; no formatting, no charts, no links |
| **Interactivity** | Low | Two-way SMS possible but clunky |

### Pros
- Universal reach — every phone receives SMS
- No app installation required
- Highest visibility (SMS open rates are ~98%)
- User does nothing beyond providing phone number

### Cons
- **Severely limited formatting**: 160 characters per segment, plain text only
- No bold, italic, lists, tables, or charts
- A Daily Protocol would span 10-20+ SMS segments (~$0.10-0.20 per daily send)
- Multi-segment SMS may arrive out of order
- Monthly cost adds up vs free alternatives (email, Telegram)
- 10DLC registration required for US A2P messaging (bureaucratic)
- Cannot embed images or links in a rich way
- Health data in plain-text SMS raises privacy concerns (no encryption)

### Verdict
**NOT RECOMMENDED.** SMS is the worst fit for health data delivery. The 160-character limit makes it impossible to deliver a meaningful Daily Protocol. The cost is non-trivial for what is fundamentally a degraded experience. Use email or Telegram instead. SMS could work only for brief alerts ("HRV dropped 20% — check your Daily Protocol email") but not as a primary delivery channel.

---

## Path 6: Push Notifications (Mobile App / PWA)

### How It Works
Build a mobile app or Progressive Web App (PWA) that receives push notifications with health insight summaries. User taps notification to see full Daily Protocol.

### Push Notification Services

| Service | Platforms | Cost | Setup Complexity |
|---------|-----------|------|-----------------|
| **Firebase Cloud Messaging (FCM)** | Android, iOS, Web/PWA | Free (unlimited) | Medium (Firebase project, SDK integration) |
| **Apple Push Notification service (APNs)** | iOS, macOS, watchOS | Free (requires $99/year Apple Developer account) | High (certificates, HTTP/2, Apple-only) |
| **Web Push API** | Chrome, Firefox, Safari (via service workers) | Free | Low (VAPID keys, service worker) |
| **OneSignal** | Cross-platform | Free up to 10K subscribers | Low (managed service) |

### PWA Approach (Lowest Barrier)
1. Build Next.js or static web app
2. Register service worker for push notifications
3. Use Web Push API with VAPID keys
4. Backend sends push via FCM for cross-browser support
5. User "installs" PWA from browser (no App Store needed)
6. Notification links to full Daily Protocol page

### Native App Approach
1. Build with React Native, Flutter, or Swift/Kotlin
2. Integrate FCM (Android) and APNs (iOS)
3. Submit to App Store / Play Store
4. Push notification triggers data fetch and display
5. Significant development and maintenance effort

### Assessment

| Dimension | Rating | Notes |
|-----------|--------|-------|
| **Technical Complexity** | 4/5 (PWA) to 5/5 (native) | Service workers, push subscription, app development |
| **Cost** | $0-99/year | FCM free; Apple Developer $99/year for iOS |
| **User Friction** | 3/5 (PWA) to 4/5 (native) | PWA: visit site + allow notifications. Native: download app. |
| **Data Timing** | Near real-time | Push whenever data is ready |
| **Data Richness** | 3/5 (notification) to 5/5 (in-app) | Notification is brief; full data in app |
| **Interactivity** | Medium to High | In-app experience can be rich |

### Pros
- Push notifications are highly visible (like SMS but richer)
- PWA avoids App Store gatekeeping
- FCM is free for unlimited notifications
- Can link to full web dashboard for details
- Near real-time data delivery possible

### Cons
- **Requires building an app** (PWA or native) — substantial development effort
- Push notification content is brief (title + body, ~100 chars visible)
- iOS Safari PWA push support is relatively new (iOS 16.4+) and inconsistent
- User must explicitly grant notification permission
- Notification fatigue — users may disable after novelty wears off
- For a single user, the development cost is extremely high relative to value
- Does not work if app/browser is force-closed on some platforms

### Verdict
**DEFERRED — pairs with web dashboard in v2.** Building a mobile app or PWA for push notifications is massive overkill for v1. The development effort to build an app just to send a daily notification is not justified when email and Telegram deliver the same content with near-zero development. Push notifications make sense as a complement to a web dashboard (Path 3) — the notification says "Your Daily Protocol is ready" and links to the dashboard.

---

## Path 7: Automated Daily/Weekly Reports

### How It Works
This is not a delivery channel but a **scheduling and generation layer** that sits behind any delivery mechanism. The system automatically pulls data, generates reports, and dispatches them on a schedule.

### Scheduling Options

| Approach | Pros | Cons | Cost |
|----------|------|------|------|
| **Cron on VPS** | Full control, reliable, simple | Must maintain server | $5-10/month (DigitalOcean, Hetzner) |
| **Vercel Cron Jobs** | Serverless, no infrastructure | Vercel free tier limits (hobby plan limitations, max 60s execution) | $0-20/month |
| **AWS Lambda + EventBridge** | Highly scalable, reliable, pay-per-use | AWS complexity, cold starts | ~$0/month at low volume |
| **GitHub Actions (scheduled)** | Free for public repos, no infra | 6-hour cron granularity, unreliable timing | Free |
| **Railway / Render cron** | Simple deployment, managed | May sleep on free tiers | $0-7/month |
| **Supabase Edge Functions + pg_cron** | In-stack if already using Supabase | Deno runtime, Edge Function time limits | Included in Supabase plan |

### Report Types

**Daily Protocol** (core v1 product):
- Previous day's biometric summary
- AI analysis across 5 domains
- Actionable recommendations
- Trend context (7-day rolling)

**Weekly Summary** (v2 - PLAT-03):
- Week-over-week trends
- Training load progression
- Sleep quality patterns
- Cumulative stress/recovery balance

**Monthly Report** (v2 - PLAT-03):
- Long-term trend analysis
- Goal progress tracking
- Pattern identification across 28-day windows

### Assessment

| Dimension | Rating | Notes |
|-----------|--------|-------|
| **Technical Complexity** | 2/5 | Cron scheduling is well-understood |
| **Cost** | $0-10/month | Depends on hosting choice |
| **User Friction** | 1/5 | Fully automated — user does nothing after initial setup |
| **Data Timing** | Scheduled (daily/weekly) |
| **Data Richness** | 5/5 | Full analysis possible in generated reports |

### Recommended Stack for BioIntelligence v1
- **Option A**: Cron on a $5/month VPS (DigitalOcean, Hetzner) — simple, reliable, full control
- **Option B**: Supabase pg_cron triggers a Supabase Edge Function — keeps everything in-stack
- **Option C**: GitHub Actions scheduled workflow — free, but timing is approximate

### Verdict
**CORE INFRASTRUCTURE for v1.** This is not an "alternative path" but a required component. Every delivery channel needs a scheduler. For v1, a simple cron job on a VPS or Supabase pg_cron is the pragmatic choice. The pipeline is: `cron trigger -> Python data pull -> Supabase store -> Claude API analysis -> email send`.

---

## Path 8: Voice Assistants (Alexa / Google Home)

### How It Works
Build a custom Alexa Skill or Google Home Action that reads out the Daily Protocol or answers health questions by voice.

### Alexa Skill Approach
1. Create skill in Alexa Developer Console
2. Define intents ("Alexa, ask BioIntelligence for my daily protocol")
3. Backend (AWS Lambda) fetches pre-generated protocol from Supabase
4. Skill responds with SSML-formatted speech
5. User must enable skill and link account

### Google Home / Assistant Approach
1. Build Action in Actions Console (note: Google deprecated many conversational Actions in 2023)
2. **Google Health Connect integration**: Garmin syncs to Health Connect; Action reads via API
3. Fulfillment webhooks serve protocol content
4. Google Assistant Routines can trigger custom actions (e.g., "Good morning" routine includes health summary)

### Key Technical Considerations
- Voice output must be concise — a full Daily Protocol read aloud takes 5-10 minutes
- Need to distill protocol into a 30-60 second TL;DR for voice
- "Tell me more about training" follow-up intents add complexity
- Account linking (OAuth) required for personalized data
- Alexa Skills Kit and Actions SDK have learning curves
- Google deprecated most third-party conversational Actions (2023) — limited path forward
- Voice is stateless — multi-turn conversations are harder than text

### Assessment

| Dimension | Rating | Notes |
|-----------|--------|-------|
| **Technical Complexity** | 4/5 | Alexa Skills Kit, SSML, intent mapping, account linking |
| **Cost** | $0/month | AWS Lambda free tier; Alexa/Google hosting is free |
| **User Friction** | 3/5 | Must own smart speaker, enable skill, link account |
| **Data Timing** | On-demand | User asks when they want it |
| **Data Richness** | 2/5 | Voice cannot convey charts, trends, or detailed numbers well |
| **Interactivity** | Medium | Multi-turn voice is possible but awkward for health data |

### Pros
- Hands-free morning briefing (ask while making coffee)
- Novel and impressive experience
- Can integrate into existing morning routines ("Alexa, good morning" includes health summary)
- Free hosting (Lambda for Alexa, Cloud Functions for Google)

### Cons
- **Voice is a poor medium for data-rich content** — numbers, trends, and percentages are hard to absorb auditorily
- Full Daily Protocol cannot be read aloud without being tedious
- Requires heavy content distillation for voice format
- Google deprecated most conversational Actions (2023) — uncertain platform future
- Alexa Skill development has a significant learning curve
- User must own a smart speaker or use phone-based assistant
- No visual component (unless using Echo Show — then it is basically a dashboard)
- Cannot reference back to specific data points (unlike email you can re-read)

### Verdict
**NICE-TO-HAVE for v3+.** Voice assistants are compelling for a TL;DR morning briefing ("Your readiness is 72, take it easy today, prioritize sleep tonight") but cannot replace the full Daily Protocol. Build only after the core product is proven and there is demand for a voice interface. If pursued, Alexa is the more viable platform (Google has deprecated most conversational Actions).

---

## Path 9: Existing Aggregation Platforms

### How It Works
Instead of pulling Garmin data directly, leverage platforms that already aggregate wearable data and provide APIs.

### Platform Comparison

#### Apple Health / HealthKit
- **Garmin sync**: One-way (Garmin -> Apple Health) via Garmin Connect iOS app
- **Data available**: Energy, body fat, BMI, blood pressure, steps, distance, HR, sleep, weight, workouts
- **Missing**: Body Battery, stress score, training load, HRV detail, VO2 max trend, respiration rate
- **API**: HealthKit (iOS/watchOS only, on-device, no server API)
- **Limitation**: Cannot access from a server-side Python script — HealthKit is device-local only
- **Verdict**: Not useful for a server-side AI agent

#### Google Health Connect
- **Garmin sync**: One-way (Garmin -> Health Connect) since June 2025 on Android
- **Data available**: Steps, HR, sleep, distance, calories, activities
- **Missing**: Body Battery, stress, HRV detail, training status, VO2 max
- **API**: Android API only (on-device, like HealthKit)
- **Limitation**: Same as Apple Health — no server-side access
- **Verdict**: Not useful for a server-side AI agent

#### Strava API
- **Garmin sync**: Auto-sync activities via Garmin Connect
- **Data available**: Activities (distance, pace, HR, power, GPS routes, laps)
- **Missing**: All health data (sleep, stress, Body Battery, HRV, SpO2, training readiness)
- **API**: Well-documented REST API with OAuth 2.0
- **Rate limits**: 1,000 requests per 15 minutes, 100K per month
- **Cost**: Free for developers
- **Verdict**: Useful only for activity data; misses all health/recovery metrics critical to BioIntelligence

#### Terra API (Health Data Aggregator)
- **Garmin support**: Direct Garmin Connect integration
- **Data available**: 30+ wearable sources; steps, HR, sleep, weight, blood pressure, activities
- **API**: REST with webhooks for real-time data
- **Cost**: Free tier (limited); paid starts ~$0.10 per 1,000 API calls
- **Verdict**: Viable alternative to python-garminconnect. Adds cost and a middleman but provides a stable, maintained API. Consider if python-garminconnect breaks.

#### Vital API (Health Data Aggregator)
- **Garmin support**: OAuth-based Garmin Connect integration
- **Data available**: Steps, HR, sleep, VO2 max, stress, activities, biometrics
- **API**: REST with webhooks
- **Cost**: Free dev tier; production $99+/month + ~$0.50/user/month
- **Verdict**: Enterprise pricing makes this overkill for a single-user personal tool. Consider only if building a multi-user product.

#### Open Wearables API
- **Overview**: Open-source API for unifying wearable data across devices
- **Status**: Early-stage project
- **Verdict**: Worth watching but not production-ready for v1

### Assessment

| Dimension | Rating | Notes |
|-----------|--------|-------|
| **Technical Complexity** | 2-3/5 | Varies by platform; aggregators simplify auth |
| **Cost** | $0-100+/month | Free (Strava, Apple) to expensive (Vital) |
| **User Friction** | 2/5 | User must authorize data sharing via OAuth |
| **Data Timing** | Near real-time with webhooks | Better than polling Garmin directly |
| **Data Richness** | 2-4/5 | Aggregators lose Garmin-specific metrics (Body Battery, training load) |

### Verdict
**FALLBACK OPTION.** For BioIntelligence, direct access via python-garminconnect provides richer data than any aggregator. Aggregators like Terra serve as a safety net if the unofficial library breaks. Apple Health and Google Health Connect are not viable because they lack server-side APIs. Strava is useful only for activity enrichment, not health data.

---

## Comparative Summary

| Path | Complexity | Monthly Cost | User Friction | Data Richness | Interactivity | v1 Ready? |
|------|-----------|-------------|---------------|---------------|---------------|-----------|
| **Email** | 2/5 | $0 | 1/5 (lowest) | 5/5 | None | **YES** |
| **Telegram Bot** | 1/5 | $0 | 2/5 | 5/5 | Very High | Yes (v1.1) |
| **WhatsApp** | 3/5 | ~$0.12 | 2/5 | 5/5 | High | No (v2) |
| **Web Dashboard** | 4/5 | $0-20 | 3/5 | 5/5 | High | No (v2) |
| **SMS** | 2/5 | ~$5-6 | 1/5 | 1/5 | Low | **No** |
| **Push Notifications** | 4-5/5 | $0-99/yr | 3-4/5 | 3-5/5 | Medium-High | No (v2) |
| **Automated Reports** | 2/5 | $0-10 | 1/5 | 5/5 | None | **YES** (infrastructure) |
| **Voice Assistants** | 4/5 | $0 | 3/5 | 2/5 | Medium | No (v3+) |
| **Aggregation Platforms** | 2-3/5 | $0-100+ | 2/5 | 2-4/5 | N/A (data source) | Fallback only |

---

## Recommended Phased Approach

### Phase 1 (v1): Email + Cron Automation
- **Delivery**: Email via Resend or Amazon SES
- **Scheduling**: Cron on VPS or Supabase pg_cron
- **Data source**: python-garminconnect
- **Rationale**: Lowest complexity, zero cost, zero user friction, validates core intelligence
- **Timeline**: Days to implement delivery layer

### Phase 1.1 (optional): Add Telegram Bot
- **Why**: Adds interactivity ("How was my sleep this week?") with zero cost
- **Effort**: 1-2 days additional development
- **Risk**: Requires user to use Telegram

### Phase 2: Web Dashboard + Push Notifications
- **Why**: Visual trends, historical exploration, protocol archive
- **Effort**: Weeks of frontend development
- **Prerequisite**: v1 email delivery proven valuable

### Phase 3: WhatsApp Integration
- **Why**: Broader reach, professional feel, interactive health agent
- **Effort**: Business verification + template approval + webhook setup
- **Prerequisite**: Multi-user demand justifies business verification

### Phase 4+: Voice Assistants, SMS alerts
- **Why**: Niche use cases, accessibility
- **Prerequisite**: Core product is mature, clear user demand

---

## Key Insight

The delivery channel is the **least risky and least important** part of the system. The hard problems are:
1. Reliable Garmin data extraction (python-garminconnect stability)
2. Intelligent analysis (Claude API prompt engineering across 5 domains)
3. Trend detection (rolling windows, anomaly convergence)
4. Health profile integration (personalized recommendations)

Email solves delivery with near-zero effort. Every other channel can be added later without changing the core intelligence pipeline. **Build the brain first, then choose where it speaks.**

---
*Research conducted: 2026-03-03*
*Sources: Garmin developer documentation, Meta WhatsApp API docs, Telegram Bot API docs, Twilio pricing, Firebase documentation, Perplexity AI research synthesis*
