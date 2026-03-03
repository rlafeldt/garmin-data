# Garmin Connect Data Access Research

Last updated: 2026-03-03

---

## 1. Garmin Health API (Official)

### Overview

The Garmin Health API is an **enterprise-grade**, officially supported API provided through the **Garmin Connect Developer Program**. It is designed for corporate wellness platforms, population health initiatives, patient monitoring, clinical research, and insurance/wellness programs -- NOT for individual developers or personal projects.

- **Developer portal**: https://developer.garmin.com/gc-developer-program/
- **Health API docs**: https://developer.garmin.com/gc-developer-program/health-api/
- **Activity API docs**: https://developer.garmin.com/gc-developer-program/activity-api/

### Access Requirements

- **Must apply** through the Garmin Connect Developer Program
- **Business use only** -- personal/hobbyist projects are explicitly excluded
- Approval typically takes 1-2 business days for legitimate business applicants
- Initial access uses **evaluation keys** (must test with 2+ Garmin accounts)
- Production keys granted after evaluation period
- **Commercial license fee** required for production use
- Enterprise SLAs available for approved partners

### Authentication: OAuth 1.0a (with consumer key/secret)

The Health API uses **OAuth 1.0a** for authentication:

1. Garmin issues a **consumer key** and **consumer secret** to approved partners
2. Users authorize the partner app via Garmin's OAuth consent flow
3. Partner receives a **user access token** and **token secret**
4. All API requests are signed with OAuth 1.0a signatures
5. User can revoke access at any time through Garmin Connect settings

Note: Some sources mention OAuth 2.0 with PKCE for newer integrations, but the documented standard remains OAuth 1.0a for the Health API.

### Available Summary Types and Endpoints

The Health API is organized around **summary types** that Garmin pushes to registered webhook endpoints. Base URL pattern: `https://healthapi.garmin.com/wellness-api/rest/`

| Summary Type | Endpoint Path | Description |
|---|---|---|
| **Daily Summaries** | `/wellness-api/rest/dailies` | Full-day aggregated wellness data |
| **Epoch Summaries** | `/wellness-api/rest/epochs` | 15-minute interval wellness data |
| **Activity Summaries** | `/wellness-api/rest/activities` | Discrete fitness activities (runs, rides, etc.) |
| **Activity Details** | Via Activity API | Detailed FIT-file-level activity data |
| **Sleep Summaries** | `/wellness-api/rest/sleeps` | Sleep duration, stages, and quality |
| **Body Composition** | `/wellness-api/rest/bodyComps` | Weight, body fat, BMI, muscle mass |
| **Stress Details** | `/wellness-api/rest/stressDetails` | All-day stress level data |
| **User Metrics** | `/wellness-api/rest/userMetrics` | VO2 max, fitness age, etc. |
| **Move IQ** | `/wellness-api/rest/moveiq` | Auto-detected activity events |
| **Pulse Ox** | `/wellness-api/rest/pulseOx` | SpO2/blood oxygen readings |
| **Respiration** | `/wellness-api/rest/respiration` | Breathing rate data |
| **Third-Party Dailies** | Varies | Aggregated data from partner apps |
| **Women's Health** | Separate API | Menstrual cycle, pregnancy tracking |
| **Training API** | Separate API | Push workouts/plans to devices |
| **Courses API** | Separate API | Push GPS courses to devices |

### Data Fields by Summary Type

#### Daily Summaries
- `steps`, `distanceInMeters`, `activeTimeInSeconds`
- `floorsClimbed`, `floorsDescended`
- `caloriesTotal` (BMR + active), `activeCalories`, `bmrCalories`
- `averageHeartRateInBeatsPerMinute`, `minHeartRateInBeatsPerMinute`, `maxHeartRateInBeatsPerMinute`
- `restingHeartRateInBeatsPerMinute`
- `timeOffsetHeartRateSamples` (timestamped HR samples throughout the day)
- `averageStressLevel`, `maxStressLevel`, `stressDurationInSeconds`, `stressQualifier`
- `bodyBatteryChargedValue`, `bodyBatteryDrainedValue`
- `moderateIntensityDurationInSeconds`, `vigorousIntensityDurationInSeconds`
- `startTimeInSeconds`, `startTimeOffsetInSeconds`, `calendarDate`
- `durationInSeconds`, `userProfilePK`

#### Epoch Summaries (15-minute intervals)
- Same fields as daily summaries but per 15-minute window
- `startTimeInSeconds`, `durationInSeconds` (typically 900s = 15 min)
- `steps`, `distanceInMeters`, `activeTimeInSeconds`
- `met` (metabolic equivalent)
- `intensity` (0=sedentary, 1-6=active levels)
- `activityType`
- Enables intraday step/HR/calorie charts similar to Garmin Connect UI

#### Sleep Summaries
- `totalSleepTimeInSeconds`, `deepSleepDurationInSeconds`
- `lightSleepDurationInSeconds`, `remSleepDurationInSeconds`
- `awakeDurationInSeconds`, `unmeasurableSleepDurationInSeconds`
- `averageHeartRate`, `minHeartRate`, `maxHeartRate`, `restingHeartRate`
- `averageSpO2`, `lowestSpO2`, `highestSpO2`
- `averageRespiration`, `lowestRespiration`, `highestRespiration`
- `sleepScoreOverall`, `sleepScoreDuration`, `sleepScoreQuality`
- `hrvStatus` (BALANCED, UNBALANCED, LOW, POOR)
- `averageStressLevel`, `sleepStressScore`
- `sleepStages` array with timestamps for each stage transition
- `awakeCount`, `restlessMomentsCount`
- `startTimeInSeconds`, `endTimeInSeconds` (GMT and local)

#### Activity Summaries
- `activityId`, `activityType`, `activityName`
- `startTimeInSeconds`, `durationInSeconds`
- `distanceInMeters`, `averageSpeedInMetersPerSecond`
- `averageHeartRateInBeatsPerMinute`, `maxHeartRateInBeatsPerMinute`
- `averagePaceInMinutesPerKilometer`
- `totalElevationGainInMeters`, `totalElevationLossInMeters`
- `averageCadenceInStepsPerMinute`
- `startLatitude`, `startLongitude`

#### Activity Details (Activity API)
- Full FIT file data: GPS trackpoints, lap splits, interval data
- Running dynamics: ground contact time, vertical oscillation, stride length
- Cycling power data, swimming stroke data
- Second-by-second or per-record HR, pace, cadence, elevation
- Available as FIT file download or structured JSON

#### Body Composition
- `weight` (grams), `bmi`, `bodyFatPercentage`
- `muscleMassInGrams`, `boneMassInGrams`
- `bodyWaterPercentage`
- `measurementTimestamp`

#### Stress Details
- `stressLevelTimestampList` -- timestamped stress readings (0-100 scale)
- `bodyBatteryTimestampList` -- timestamped body battery values
- `averageStressLevel`, `maxStressLevel`
- Qualifiers: "calm", "low", "medium", "high", "stressful"

#### Heart Rate
- `timeOffsetHeartRateSamples` -- map of timestamp offsets to HR values
- Provides near-continuous HR throughout the day (typically every 2-15 seconds when wearing device)
- `restingHeartRateInBeatsPerMinute`

#### Respiration
- Average, min, max breaths per minute
- All-day, sleep, and activity respiration rates
- Timestamped samples available

#### Pulse Ox / SpO2
- `averageSpO2`, `lowestSpO2`, `highestSpO2`
- Timestamped overnight readings
- All-day spot checks (if device supports continuous Pulse Ox)

#### HRV (Heart Rate Variability)
- `hrvStatus`: BALANCED, UNBALANCED, LOW, POOR
- Average HRV value (weekly average RMSSD in milliseconds)
- Overnight HRV readings
- 7-day baseline comparison

### Push vs Pull Model

The Garmin Health API supports **both push (webhooks) and pull (polling)**:

#### Push Model (Recommended)
1. **Register webhook URLs** for each summary type during developer program setup
2. When a user syncs their Garmin device, Garmin sends a **ping notification** to your webhook
3. The ping contains: user access token, summary type, start/end timestamps
4. Your server then **pulls the full data** using the provided tokens and time range
5. This is a "ping-then-pull" model, not a full data push

#### How Webhook Pings Work
```
1. User syncs Garmin watch -> phone -> Garmin cloud
2. Garmin processes data and creates summaries
3. Garmin POSTs a ping to your registered webhook URL:
   POST https://your-server.com/garmin/webhook
   {
     "dailies": [{
       "userId": "...",
       "userAccessToken": "...",
       "summaryId": "...",
       "startTimeInSeconds": 1709424000,
       "durationInSeconds": 86400,
       "calendarDate": "2026-03-03"
     }]
   }
4. Your server uses the access token to GET full summary data
5. Garmin may send multiple pings as data is updated (tentative -> final)
```

#### Pull Model (Polling)
- You can also poll endpoints directly at any time
- Use date-range parameters to fetch summaries
- Subject to rate limits
- Useful for backfilling historical data

#### Historical Backfill
- **Health API**: Up to 2 years of historical data available via backfill request
- **Activity API**: Up to 5 years of historical activity data
- Backfill is requested through the developer portal after user authorization

### Rate Limits (Official API)
- Specific rate limits are documented in the developer program (not publicly disclosed)
- Generally more generous than unofficial API access
- Designed for production-scale applications with many users
- Garmin provides guidance during onboarding

---

## 2. Unofficial Garmin Connect API (Reverse-Engineered)

### Overview

Since Garmin does not offer a public API for personal/individual use, the developer community has reverse-engineered the internal REST APIs used by the Garmin Connect website and mobile apps. These are **not officially supported** and can break without notice.

### How It Works

The unofficial API mimics the same HTTP requests made by:
- The Garmin Connect web application (connect.garmin.com)
- The Garmin Connect mobile app

Developers discover endpoints by:
- Intercepting HTTPS traffic with tools like mitmproxy or Charles Proxy
- Inspecting browser network requests on connect.garmin.com
- Analyzing mobile app traffic

### Key Unofficial Endpoints (connect.garmin.com)

Base URL: `https://connect.garmin.com/`

| Category | Endpoint Pattern | Notes |
|---|---|---|
| Daily summary | `/usersummary-service/usersummary/daily/{guid}?calendarDate={date}` | Steps, HR, stress, body battery, etc. |
| Heart rate | `/usersummary-service/usersummary/daily/heartrate/{date}` | Full-day HR with timestamps |
| Sleep | `/wellness-service/wellness/dailySleepData/{date}` | Sleep stages, scores |
| Stress | `/usersummary-service/usersummary/daily/stressvalues/{date}` | Timestamped stress values |
| Body battery | Included in stress/daily data | Charge/drain values |
| Activities list | `/activitylist-service/activities/search/activities?start={n}&limit={n}` | Paginated |
| Activity detail | `/activity-service/activity/{activityId}` | Full activity JSON |
| Activity download | `/download-service/files/activity/{activityId}` | FIT file |
| Body composition | `/weight-service/weight/dateRange/{start}/{end}` | Weight, body fat |
| Steps | `/usersummary-service/stats/steps/daily/{start}/{end}` | Step counts |
| HRV | `/hrv-service/hrv/{date}` | HRV status and values |
| SpO2 | `/wellness-service/wellness/spo2/daily/{date}` | Blood oxygen data |
| Respiration | `/wellness-service/wellness/dailyRespiration/{date}` | Breathing rate |
| Training readiness | `/wellness-service/wellness/trainingReadiness/{date}` | Readiness score |
| VO2 max | `/fitness-stats-service/fitnessStats/{date}` | VO2 max, fitness age |
| Device info | `/device-service/deviceregistration/devices` | Connected devices |
| User profile | `/userprofile-service/usersettings` | Profile data |

### Authentication for Unofficial Access

The unofficial libraries use Garmin's SSO (Single Sign-On) authentication:

1. **Initial login**: Submit username/password to `sso.garmin.com`
2. **OAuth1 token exchange**: Receive long-lived OAuth1 tokens (~1 year validity)
3. **OAuth2 bearer tokens**: Exchange OAuth1 for short-lived OAuth2 tokens for API calls
4. **Critical detail**: API requests require both the JWT bearer token AND a `JWT_FGP` cookie
5. **DI-Backend header**: Some endpoints require `DI-Backend: connectapi.garmin.com`
6. **Token storage**: Tokens saved locally (default: `~/.garminconnect`) for session persistence
7. **MFA support**: Modern libraries support multi-factor authentication via custom handlers

---

## 3. Python Libraries

### python-garminconnect (Recommended)

- **GitHub**: https://github.com/cyberjunky/python-garminconnect
- **PyPI**: `pip install garminconnect`
- **Stars**: ~1,800+ on GitHub
- **Status**: Actively maintained (regular releases in 2024-2026)
- **Auth engine**: Uses `garth` library internally

#### Key Methods

```python
from garminconnect import Garmin
from datetime import date

client = Garmin("email@example.com", "password")
client.login()

today = date.today().strftime('%Y-%m-%d')

# Daily overview
client.get_stats(today)                    # Full daily summary (steps, HR, calories, etc.)
client.get_steps_data(today)               # Step count and distance
client.get_heart_rates(today)              # HR data: resting, avg, max, time-in-zones

# Health metrics
client.get_sleep_data(today)               # Sleep stages, duration, scores
client.get_stress_data(today)              # Stress levels throughout day
client.get_body_battery(today)             # Body battery charge/drain
client.get_hrv_data(today)                 # Heart rate variability
client.get_spo2_data(today)               # Blood oxygen saturation
client.get_respiration_data(today)         # Breathing rate
client.get_body_composition(today)         # Weight, body fat, BMI, muscle mass
client.get_hydration_data(today)           # Water intake logged
client.get_training_readiness(today)       # Training readiness score
client.get_training_status(today)          # Training status
client.get_max_metrics(today)              # VO2 max, fitness age

# Activities
client.get_activities(start=0, limit=20)   # Paginated activity list
client.get_activity(activity_id)           # Single activity detail
client.download_activity(activity_id)      # Download FIT file

# Write operations (unique to unofficial API)
client.add_body_composition(...)           # Log weight/body fat
client.add_hydration(...)                  # Log water intake
client.upload_activity(fit_file_path)      # Upload a FIT file
```

#### 100+ Methods Across 11 Categories
1. **User profile** -- profile info, settings, display name
2. **Daily health** -- stats, steps, HR, stress, body battery, sleep
3. **Advanced health** -- HRV, VO2 max, training readiness, training status
4. **Historical data** -- date-range queries for any metric
5. **Activities** -- list, detail, download (FIT/GPX/CSV), upload
6. **Body composition** -- weight, body fat, BMI trends
7. **Goals and achievements** -- badges, personal records, challenges
8. **Device management** -- connected devices, settings, alarms
9. **Gear tracking** -- shoes, bikes, activity assignment
10. **Hydration and wellness** -- water logging, blood pressure
11. **System** -- user settings, connected apps, permissions

#### Token Persistence

```python
from garminconnect import Garmin
import os

tokendir = os.path.expanduser("~/.garminconnect")
client = Garmin("email@example.com", "password")

# First login
client.login()
client.garth.dump(tokendir)  # Save tokens

# Subsequent logins (no password needed)
client = Garmin()
client.login(tokendir)       # Load from saved tokens
```

### garth (Authentication Layer)

- **GitHub**: https://github.com/matin/garth
- **PyPI**: `pip install garth`
- **Role**: Low-level SSO authentication + basic Connect API client
- **Used by**: python-garminconnect as its auth engine
- **Key features**:
  - OAuth1 tokens valid ~1 year (no frequent re-auth)
  - Automatic OAuth2 token refresh
  - MFA support via custom handlers
  - Direct API calls: `garth.connectapi("/endpoint")`
  - Pydantic-based data classes for type safety
  - ~50,000+ monthly PyPI downloads

```python
import garth

# Authenticate
garth.login("email@example.com", "password")
garth.save("~/.garth")

# Direct API calls
garth.connectapi("/usersummary-service/usersummary/daily/2026-03-03")

# Typed data access
from garth import DailyStress, SleepData
stress = DailyStress.list("2026-03-01", "2026-03-03")
sleep = SleepData.get("2026-03-03")
```

### garmy (AI-Oriented)

- **GitHub**: https://github.com/bes-dev/garmy
- **Focus**: Health data analysis with AI agent integration
- **Features**: CLI tools, MCP server for AI assistants, local SQLite storage
- **Use case**: Conversational health data analysis via Claude/ChatGPT

### GarminDB (Database Builder)

- **GitHub**: https://github.com/tcgoetz/GarminDB
- **Focus**: Download all Garmin data into a local SQLite database
- **Features**: Full historical data sync, FIT file parsing, trend analysis
- **Use case**: Long-term personal health data warehousing

---

## 4. JavaScript/Node.js Libraries

### garmin-connect (npm)

- **npm**: `npm install garmin-connect`
- **Latest version**: 1.6.2 (January 2024)
- **Status**: Less actively maintained than Python alternatives
- **No known security vulnerabilities** (per Snyk)

```javascript
const { GarminConnect } = require('garmin-connect');

const client = new GarminConnect({
  username: 'email@example.com',
  password: 'password'
});

await client.login();

// Activities
const activities = await client.getActivities(0, 10);
const activity = await client.getActivity(activityId);

// Health data
const steps = await client.getSteps(date);
const sleep = await client.getSleep(date);
const heartRate = await client.getHeartRate(date);

// Session persistence
const session = client.sessionJson;   // Export
client.sessionJson = savedSession;     // Restore

// OAuth token management
client.onSessionChange((session) => {
  saveToFile(session);  // Auto-save on token refresh
});
```

**Limitations compared to Python library**:
- Fewer endpoints covered
- Less active maintenance
- Smaller community
- Missing some advanced health metrics (HRV, training readiness, etc.)

---

## 5. Push vs Pull Model

### Official Health API: Ping-Then-Pull (Webhooks)

| Aspect | Detail |
|---|---|
| **Model** | Webhook ping notification + REST pull for data |
| **Trigger** | User syncs device to Garmin Connect (phone/web) |
| **Latency** | Minutes after device sync |
| **Reliability** | High -- Garmin guarantees delivery with retries |
| **Data completeness** | May receive "tentative" data first, then "final" update |
| **Configuration** | Register webhook URLs per summary type in developer portal |

### Unofficial API: Polling Only

| Aspect | Detail |
|---|---|
| **Model** | Poll/pull only -- no webhook support |
| **Trigger** | Your application initiates requests |
| **Latency** | Depends on polling frequency |
| **Challenge** | Must implement your own scheduling + rate limit awareness |
| **Typical pattern** | Cron job or scheduled task polls every 15-60 minutes |

### Practical Approach for Personal Projects

Since the official webhook API requires partner approval, personal projects using the unofficial API must:
1. Run a scheduled job (cron, systemd timer, cloud scheduler)
2. Authenticate and poll for new data
3. Compare against last-fetched data to detect changes
4. Respect rate limits to avoid IP/account blocks

---

## 6. Rate Limits and Restrictions

### Official Health API
- Rate limits documented privately during onboarding
- Generally generous for production-scale use
- Designed for apps with thousands of users

### Unofficial API (connect.garmin.com)
| Restriction | Detail |
|---|---|
| **Rate limit** | Approximately 1 request per 5 minutes for some endpoints |
| **Exceeded limit** | HTTP 429 "Too Many Requests" |
| **Block duration** | ~1 hour temporary IP-based block |
| **Repeated violation** | Longer blocks possible |
| **Account risk** | Theoretical risk of account suspension (rarely enforced in practice) |
| **Mitigation** | Cache aggressively, poll infrequently, implement exponential backoff |

### Practical Rate Limit Handling

```python
from garminconnect import (
    Garmin,
    GarminConnectTooManyRequestsError
)
import time

client = Garmin("email", "password")
client.login()

try:
    data = client.get_stats("2026-03-03")
except GarminConnectTooManyRequestsError:
    time.sleep(300)  # Wait 5 minutes
    data = client.get_stats("2026-03-03")
```

### Recommended Polling Strategy (Unofficial)
- Poll no more than once per 15-30 minutes for daily data
- Batch requests: fetch all metrics in one session rather than separate sessions
- Cache token/session to avoid re-authentication overhead
- Use exponential backoff on 429 errors
- Consider polling only 2-4 times per day for daily summaries

---

## 7. Data Granularity

### Raw Sensor Data vs Summaries

| Data Level | Source | Granularity | Access Method |
|---|---|---|---|
| **Raw sensor** | FIT files from device | Per-second or per-record | Download FIT files, parse with `fitparse` |
| **Epoch summaries** | Health API / unofficial | 15-minute intervals | API endpoints |
| **Hourly summaries** | Derived from epochs | Hourly aggregates | Compute from epoch data |
| **Daily summaries** | Health API / unofficial | One record per day | API endpoints |
| **Activity detail** | Activity API / FIT file | Per-second during activity | API or FIT download |

### Heart Rate Granularity
- **Daily summary**: avg, min, max, resting HR
- **Time-offset samples**: HR readings every ~2-15 seconds throughout the day (in `timeOffsetHeartRateSamples` map)
- **Activity**: Per-second or per-record HR from chest strap or wrist sensor
- **FIT file**: Full-resolution sensor data

### Sleep Granularity
- **Summary**: Total duration per stage, overall scores
- **Stage transitions**: Array of timestamped stage changes (deep/light/REM/awake)
- **Associated metrics**: Per-sleep HR, HRV status, SpO2, respiration, stress

### Stress / Body Battery Granularity
- **Daily summary**: Average, max stress; body battery charge/drain totals
- **Detail timestamps**: Stress readings every ~3 minutes (stress level 0-100)
- **Body battery**: Timestamped values showing charge/drain throughout day

### SpO2 Granularity
- **Summary**: Average, min, max SpO2 percentages
- **Timestamped readings**: Individual SpO2 measurements (frequency depends on device mode -- all-day vs sleep-only)

### HRV Granularity
- **Status**: Categorical classification (BALANCED, UNBALANCED, LOW, POOR)
- **Nightly average**: RMSSD value in milliseconds
- **7-day baseline**: Rolling average for trend comparison
- **Per-night readings**: Available in sleep detail data

### Steps Granularity
- **Daily total**: Single number
- **Epoch (15-min)**: Steps per 15-minute window
- **Move IQ**: Auto-detected activity type changes with timestamps

---

## 8. Activity Sharing via Weblinks

### URL Format
- Shared activity URLs: `https://connect.garmin.com/activity/{activityID}`
- `activityID` is a unique numeric identifier
- Accessible without login if activity privacy is set to "Everyone"

### How to Share
- Garmin Connect app: More > Activities > select activity > share icon > Web Link
- Activity privacy must be "Everyone", "Connections", or "Connections and Groups"

### Visible Data on Shared Page
- Distance, time, route map (if GPS)
- Average pace/speed, heart rate, elevation profile
- Calories burned, photos/stickers
- Full lap/interval details may NOT be visible

### Limitations
- Only activities can be shared via public links (NOT health summaries)
- No official API for generating share links programmatically
- Profile-level URL: `https://connect.garmin.com/explore?owner={username}`

---

## 9. Health Data Sharing

### Key Finding: Health data CANNOT be shared via public weblinks

Health metrics (sleep, stress, body battery, steps, heart rate) have NO public link sharing capability. Options:

- **Garmin Connections**: Friends with Garmin accounts see some public health data
- **Authorized Viewers**: Settings > Profile & Privacy > Authorized Viewers (requires Garmin login)
- **Third-party integrations**: One-way export to Google Health Connect, Apple Health
- **Research tools** (Fitrockr): Consent-based pull requiring Garmin login

---

## 10. Export Capabilities

### Manual Export Formats

| Format | Scope | Notes |
|---|---|---|
| **FIT** | Individual activities | Original upload format, full sensor data |
| **TCX** | Individual activities | May be empty for some activity types |
| **GPX** | Individual activities | Best for GPS track data |
| **CSV** | Bulk activity summaries | Select multiple on Activities page |

### Bulk Data Export (Official)
- **URL**: https://www.garmin.com/account/datamanagement/
- Request Data Export -> ZIP with ALL data emailed
- Includes activities in original FIT/GPX/TCX + health stats
- GDPR-compliant

### FIT File Parsing

```python
from fitparse import FitFile

fitfile = FitFile("activity.fit")
for record in fitfile.get_messages("record"):
    for field in record.fields:
        print(f"{field.name}: {field.value}")
# Outputs: timestamp, heart_rate, position_lat, position_long,
#          altitude, speed, cadence, power, etc.
```

---

## 11. Third-Party Integrations

### Native Sync Partners

| Service | Direction | Data Synced |
|---|---|---|
| **Strava** | Garmin -> Strava (one-way) | Activities with GPS, HR, power |
| **TrainingPeaks** | Bidirectional | Workouts + completed activities |
| **MyFitnessPal** | Limited | Body composition only |
| **Apple Health** | Garmin -> Apple (one-way) | Energy, body fat, BP, steps, HR, sleep, weight, workouts |
| **Google Health Connect** | Garmin -> Google (one-way) | Steps, HR, sleep, activities |

### Using Strava as Intermediary (Activities Only)
- Strava receives full Garmin activities automatically
- Strava API is public and well-documented (OAuth2)
- Limitation: No health summaries (sleep, stress, body battery, HRV, etc.)

### Garmin Health SDK (Separate from API)
- Direct Bluetooth access to paired Garmin watch from mobile app
- Fewer data types than Health API
- Avoids server round-trip (direct device -> phone)
- Separate application process from Health API

### Connect IQ SDK
- For building watch faces, widgets, data fields ON the device
- **Cannot directly send data to external servers**
- Data fields write to standard FIT format only
- Workaround: Mobile companion app relay via Bluetooth
- NOT a viable path for health data extraction to external servers

---

## 12. Comparison: Official vs Unofficial API

| Feature | Official Health API | Unofficial (python-garminconnect) |
|---|---|---|
| **Access** | Business approval required | Anyone with Garmin account |
| **Authentication** | OAuth 1.0a (consumer keys) | SSO username/password -> OAuth tokens |
| **Push notifications** | Yes (webhook pings) | No (polling only) |
| **Rate limits** | Generous (production-scale) | Strict (~1 req/5 min for some endpoints) |
| **Stability** | Guaranteed, versioned | Can break without notice |
| **Support** | Official Garmin support | Community only |
| **Data breadth** | Defined summary types | 100+ methods, broader data access |
| **Write operations** | Limited (Training/Courses API) | Full write access (log weight, upload activities, etc.) |
| **Historical backfill** | 2 years health, 5 years activities | Arbitrary date ranges |
| **Cost** | Commercial license fee | Free |
| **Risk** | None (official) | Account suspension possible (rare in practice) |
| **Best for** | Enterprise/commercial products | Personal projects, research, automation |

---

## 13. Summary: Best Approaches for This Project

### Recommended: python-garminconnect Library
- **Richest data access**: All health metrics (sleep, stress, body battery, HRV, SpO2, HR, steps, respiration, training readiness, VO2 max)
- **All activities**: Full activity details, GPS data, FIT file downloads
- **Authentication**: Username/password + MFA, with ~1-year token persistence
- **Risk**: Unofficial API, may break; potentially violates ToS
- **Mitigation**: Cache aggressively, handle 429 errors gracefully, store data locally

### Alternative: Garmin Bulk Export + FIT Parsing
- Official and ToS-compliant
- Full sensor-level data via FIT files
- Limitation: Manual trigger, no real-time/automated data
- Good for initial historical data load

### Alternative: Strava API as Intermediary (Activities Only)
- Public, well-documented OAuth2 API
- Garmin auto-syncs activities to Strava
- Limitation: No health summaries (sleep, stress, body battery)

### Not Recommended for Personal Use
- Garmin Health API (enterprise approval required, commercial license)
- Connect IQ apps (cannot send data externally)
- Direct web scraping (fragile, no advantage over python-garminconnect)
