# Garmin Data Access: Open-Source Libraries & Tools Research

*Researched: 2026-03-03*

---

## Table of Contents

1. [garminconnect (Python) - cyberjunky](#1-garminconnect-python---cyberjunky)
2. [garth (Python) - matin](#2-garth-python---matin)
3. [garmin-connect (Node.js) - gooin](#3-garmin-connect-nodejs---gooin)
4. [Garmin FIT SDK](#4-garmin-fit-sdk)
5. [Bulk Export Tools (gcexport, garminexport, GarminDB)](#5-bulk-export-tools)
6. [Home Assistant Garmin Integration](#6-home-assistant-garmin-integration)
7. [Gadgetbridge](#7-gadgetbridge)
8. [Garmin API Blocking Status](#8-garmin-api-blocking-status)
9. [Comparison Matrix](#9-comparison-matrix)
10. [Recommendations](#10-recommendations)

---

## 1. garminconnect (Python) - cyberjunky

**The most comprehensive and actively maintained Python wrapper for Garmin Connect.**

| Detail | Value |
|--------|-------|
| GitHub | https://github.com/cyberjunky/python-garminconnect |
| Stars | ~1,000+ (actively growing; 16+ contributors) |
| Last Updated | Actively maintained through 2025-2026 |
| Latest Release | v0.2.26 (bumped garth to 0.5.3, refactored MFA) |
| PyPI | `pip install garminconnect` |
| License | MIT |
| Language | Python 3 |

### Authentication

- Uses **garth** library under the hood for OAuth1/OAuth2 authentication
- Mimics the official Garmin Connect mobile app's SSO flow
- First login requires email/password; tokens saved to `~/.garminconnect`
- Tokens valid up to **1 year** without re-login
- Supports MFA (multi-factor authentication)
- Optional custom OAuth consumer keys via environment variables

```python
from garminconnect import Garmin

client = Garmin("email@example.com", "password")
client.login()  # Tokens saved automatically

# Subsequent logins reuse tokens
client = Garmin()
client.login(tokenstore="~/.garminconnect")
```

### Data Available (100+ Endpoints in 11 Categories)

| Category | Methods | Examples |
|----------|---------|----------|
| User/Profile | 4 | User info, settings |
| Daily Health/Activity | 8 | Steps, calories, distance, floors |
| Advanced Metrics | 10 | HRV, VO2 max, fitness age, body battery |
| Activities/Workouts | 20 | Get/create/delete activities, splits, manual entries |
| Body/Weight | 8 | Weigh-ins, timestamps, body composition |
| Goals/Achievements | 15 | Badges, challenges, progress |
| Devices/Gear | 13 | Device info, alarms, solar tracking |
| Hydration/Wellness | 9 | Blood pressure, menstrual cycle, hydration |
| Historical/Trends | 6 | Date range queries, historical data |
| Sleep | multiple | Sleep stages, duration, score, SpO2 during sleep |
| System/Export | 4 | GraphQL, reports, logout |

Key methods:
- `get_stats(date)` - Daily summary (steps, calories, HR, etc.)
- `get_heart_rates(date)` - Heart rate time series
- `get_sleep_data(date)` - Sleep stages and metrics
- `get_stress_data(date)` - Stress level time series
- `get_body_battery(date)` - Body battery levels
- `get_hrv_data(date)` - Heart rate variability
- `get_spo2_data(date)` - Blood oxygen levels
- `get_activities_by_date(start, end)` - Activity list
- `get_respiration_data(date)` - Respiration rate
- `get_intensity_minutes_data(date)` - Intensity minutes

### Known Issues / Limitations

- Unofficial/reverse-engineered API -- could break if Garmin changes endpoints
- Rate limiting (~5 min recommended between calls)
- Not all Garmin features/fields are mapped
- MFA can require re-login via `client.login(tokenstore)` after initial MFA challenge
- Returns JSON data; no built-in export to CSV/DB (DIY)

### Reliability

- Highly reliable; used as the foundation for Home Assistant integration
- 57+ releases showing active maintenance
- Community actively reports and fixes endpoint changes
- Tokens rarely expire prematurely

---

## 2. garth (Python) - matin

**The authentication backbone for Garmin Connect Python tools.**

| Detail | Value |
|--------|-------|
| GitHub | https://github.com/matin/garth |
| Stars | ~500+ |
| Last Updated | Active through 2025-2026 |
| Latest Version | 0.5.3 (referenced Dec 2024) |
| PyPI | `pip install garth` |
| Language | Python |

### How It Works

- **Focused solely on authentication** -- not a full API wrapper
- Implements Garmin Connect SSO via OAuth1/OAuth2 token flow
- Mimics the official Garmin mobile app authentication
- Generates long-lived tokens (up to 1 year)
- Saves tokens locally (e.g., `~/.garminconnect`)
- Browser-based MFA support
- CLI: `uvx garth login`

### Comparison to garminconnect

| Aspect | garth | garminconnect |
|--------|-------|---------------|
| Purpose | Auth only | Full API wrapper |
| Auth | OAuth1/OAuth2, MFA, browser | Uses garth internally |
| Data access | Raw HTTP via garth client | 100+ typed methods |
| Standalone | Yes | Depends on garth |
| Use case | Custom API calls, other libs | General Garmin data access |

### When to Use garth Directly

- Building custom API integrations
- Need fine-grained control over HTTP requests
- Want to use Garmin API endpoints not yet wrapped by garminconnect
- Building an MCP server or custom tool

```python
import garth

garth.login("email@example.com", "password")
garth.save("~/.garminconnect")

# Direct API access
response = garth.connectapi("/wellness-service/wellness/dailySummary", params={"calendarDate": "2026-03-03"})
```

### Known Issues

- Token files should be secured (`chmod 600`) -- they are equivalent to passwords
- Some MFA edge cases in fully automated (headless) flows
- Not a standalone data tool; usually paired with garminconnect or custom code

---

## 3. garmin-connect (Node.js) - gooin

**The primary Node.js library for Garmin Connect.**

| Detail | Value |
|--------|-------|
| npm | `@gooin/garmin-connect` |
| GitHub | https://github.com/gooin/garmin-connect (inferred from npm) |
| Also | `@flow-js/garmin-connect` (fork) |
| Last Updated | Active; used in 2025-2026 projects |
| Language | JavaScript/TypeScript |

### Authentication

- Username/password login generating OAuth1/OAuth2 tokens
- Tokens are serializable JSON, can be saved/loaded from files or DB
- Auto-refresh support
- `sessionChange` event for token persistence
- `restoreOrLogin()` fallback if tokens expire

```javascript
const { GarminConnect } = require('@gooin/garmin-connect');
const GCClient = new GarminConnect({ username: 'user', password: 'pass' });

await GCClient.login();

// Save tokens for reuse
GCClient.saveTokenToFile('/path/to/tokens.json');

// Later: restore tokens
GCClient.loadTokenByFile('/path/to/tokens.json');
// or
await GCClient.restoreOrLogin();
```

### Data Available

| Endpoint | Method |
|----------|--------|
| Activities | `getActivities(start, limit, type, subType)` |
| Single Activity | `getActivity({activityId})` |
| Activity Count | `countActivities()` |
| Profile | `getUserProfile()` |
| Settings | `getUserSettings()` |
| Steps | `getSteps(date)` |
| Sleep | `getSleepData(date)` |
| Golf | `getGolfSummary()`, `getGolfScorecard(id)` |
| Upload/Delete | Activity upload and deletion |
| Custom | `get('/wellness/dailyHeartRate/...')` proxy |

### Limitations

- Fewer endpoints than Python garminconnect (no HRV, body battery, stress, SpO2 methods built in)
- Some features marked "planned" (badges, workouts, gear)
- Heart rate requires manual URL construction via `get()` proxy
- May face issues if Garmin enforces OAuth2 PKCE (currently uses legacy credentials)

### Used In

- MagicMirror modules (MMM-GConnect)
- MCP servers (garmin-mcp-ts)
- AI coaching apps
- ioBroker Garmin adapter

---

## 4. Garmin FIT SDK

**Official Garmin toolkit for parsing FIT (Flexible and Interoperable Data Transfer) files.**

| Detail | Value |
|--------|-------|
| Official Site | https://developer.garmin.com/fit |
| Python SDK | https://github.com/garmin/fit-python-sdk |
| npm Package | `@garmin/fitsdk` |
| Languages | C/C++, Java, C#, Python, JavaScript |
| License | Garmin FIT SDK License |

### What is in a FIT File?

FIT files are compact binary files stored on Garmin devices containing:

| Message Type | Data Fields |
|-------------|-------------|
| **Record** (time-series) | timestamp, lat/long, altitude, speed, heart_rate, cadence, power, distance, calories, temperature, vertical_oscillation, pedal_smoothness |
| **Session** | Activity summary, total distance, avg/max HR, avg/max power, total calories, sport type |
| **Lap** | Split data, lap distance, lap time, avg HR per lap |
| **Event** | Start/stop timestamps, timer events |
| **Device Info** | Hardware details, firmware, battery, sensor info |
| **Heart Rate** | HR zones, resting HR |
| **Sleep** | Sleep levels, timestamps (newer devices) |
| **Stress** | Stress scores (newer devices) |
| **HRV** | Beat-to-beat intervals |

### Python Parsing

```python
# Official SDK
from garmin_fit_sdk import Decoder, Stream

stream = Stream.from_file("activity.fit")
decoder = Decoder(stream)
messages, errors = decoder.read()

for record in messages.get("record_mesgs", []):
    print(record)  # {'timestamp': ..., 'heart_rate': 115, 'altitude': 1587, ...}

# Alternative: fitparse (community library)
from fitparse import FitFile

fitfile = FitFile('activity.fit')
for record in fitfile.get_messages('record'):
    print(record.get_values())
```

### JavaScript Parsing

```javascript
import { Decoder, Stream } from '@garmin/fitsdk';

const stream = Stream.fromByteArray(new Uint8Array(buffer));
const decoder = new Decoder(stream);
const { messages, errors } = decoder.read({
    applyScaleAndOffset: true,
    expandSubFields: true,
    includeUnknownData: true,
    mergeHeartRates: true
});

console.log(messages.recordMesgs);
```

### Key Considerations

- **Granularity**: FIT files contain the rawest, most granular data (per-second time series)
- **Offline**: No API calls needed -- parse files locally
- **Undocumented fields**: Some fields are not in the official profile; use `includeUnknownData: true`
- **Profile spreadsheet**: `profile.xlsx` in the SDK documents all known messages/fields
- **FIT File Viewer**: https://fitfileviewer.com for manual inspection
- **Activity types**: Different activities produce different fields (running has cadence/vertical oscillation; cycling has power/pedal smoothness)

### Why FIT Files Matter for This Project

- They are the **most complete** data source from a Garmin device
- Can be downloaded via garminconnect library (`download_activity()`)
- Can be exported from Garmin Connect web UI
- Contain data not available through the Connect API (e.g., per-second GPS, undocumented sensors)

---

## 5. Bulk Export Tools

### 5a. pe-st/garmin-connect-export (gcexport)

| Detail | Value |
|--------|-------|
| GitHub | https://github.com/pe-st/garmin-connect-export |
| Stars | ~800+ |
| Version | 4.6.0 (preparing) |
| Language | Python |

- Bulk downloads all activities as CSV summaries + track files (GPX, TCX, FIT, JSON)
- Output to dated directories like `YYYY-MM-DD_garmin_connect_export/`
- OAuth session persistence (`-ss` flag)
- Customizable: `-c all -f gpx` for all GPX files
- Docker support via included Dockerfile

```bash
python gcexport.py -c all -f original  # Download all activities as original FIT files
python gcexport.py -c 100 -f gpx -d ./exports  # Last 100 as GPX
```

### 5b. petergardfjall/garminexport

| Detail | Value |
|--------|-------|
| GitHub | https://github.com/petergardfjall/garminexport |
| Language | Python |
| Install | `pip install garminexport` |

- CLI tool for **incremental backups** via `garmin-backup`
- Downloads only new activities on subsequent runs
- Supports GPX, TCX, FIT, JSON formats
- Handles Cloudflare bot protection

```bash
garmin-backup --backup-dir ./backups --format original --format gpx
```

### 5c. tcgoetz/GarminDB

| Detail | Value |
|--------|-------|
| GitHub | https://github.com/tcgoetz/GarminDB |
| Language | Python |

- Downloads activities, sleep, weight, heart rate data
- Parses and stores as JSON
- Imports into a **local database** (SQLite)
- Good for long-term data warehousing
- Includes analysis tools

### 5d. Other Notable Tools

| Tool | URL | Purpose |
|------|-----|---------|
| jo-m/garmin-disconnect | https://github.com/jo-m/garmin-disconnect | Local Garmin Connect alternative, offline data viewing |
| arpanghosh8453/garmin-grafana | https://github.com/arpanghosh8453/garmin-grafana | Docker: Garmin -> InfluxDB -> Grafana dashboards |
| labsansis/garmin-workout-downloader | https://github.com/labsansis/garmin-workout-downloader | Browser extension for strength training workout details |
| RobertWojtowicz/export2garmin | https://github.com/RobertWojtowicz/export2garmin | Sync TO Garmin from Xiaomi/Omron |

---

## 6. Home Assistant Garmin Integration

| Detail | Value |
|--------|-------|
| GitHub | https://github.com/cyberjunky/home-assistant-garmin_connect |
| Stars | ~368 |
| Forks | ~46 |
| Install | Via HACS (Home Assistant Community Store) |
| Last Updated | Active through 2025-2026 |

### How It Works

- Custom integration installed via HACS
- Uses **python-garminconnect** library under the hood
- Configured via HA UI with Garmin email/password
- Polls Garmin Connect API every ~5 minutes
- Creates HA sensor entities for all available data

### Available Sensors

| Category | Sensors |
|----------|---------|
| Steps | Total Steps, Daily Step Goal, Total Distance |
| Calories | Total Kilocalories, Active, BMR, Burned |
| Time | Active Time, Sedentary Time, Sleeping Time, Awake Duration |
| Floors | Ascended, Descended, Ascended Goal |
| Heart Rate | Min HR, Max HR, Resting HR |
| Stress | Avg/Max Stress Level, stress durations by category (Rest/Activity/Low/Medium/High) |
| Body Battery | Charged, Drained, Highest, Lowest, Most Recent |
| SpO2 | Average, Lowest, Latest |
| Body Composition | Weight, BMI, Body Fat%, Body Water%, Bone Mass, Muscle Mass, Visceral Fat, Metabolic Age |
| Respiration | Highest, Lowest, Latest respiration rate |
| Sleep | Sleep Duration, Total Sleep, Awake Duration |
| Other | Next Alarm, HRV Status, Intensity Minutes, Gear Sensors |

### Services (Push Data Back)

- `garmin_connect.add_body_composition` - Push weight/BMI from other scales
- `garmin_connect.add_blood_pressure` - Push BP data
- `garmin_connect.set_active_gear` - Set active gear

### Known Issues

- **No 2FA/MFA support** -- endless login loops if 2FA enabled; must disable 2FA
- Rate limited to ~5 minute update intervals
- Not all sensors populate for every user (depends on device)
- Garmin API is closed/unofficial; any changes could break it
- Debug logging available via `configuration.yaml`

### Relevance to This Project

The HA integration demonstrates what data is reliably available through the unofficial API and provides a proven polling architecture. Its sensor list is essentially a catalog of what garminconnect can deliver in near-real-time.

---

## 7. Gadgetbridge

| Detail | Value |
|--------|-------|
| Website | https://gadgetbridge.org |
| GitHub | https://codeberg.org/Freeyourgadget/Gadgetbridge (primary) |
| Latest Release | 0.89.0 (early 2026) |
| Platform | Android (F-Droid, IzzyOnDroid) |

### What It Is

Gadgetbridge is an open-source Android app that connects directly to wearable devices via Bluetooth, bypassing vendor cloud services entirely. It is **privacy-focused** -- all data stays local on the phone.

### Garmin Device Support (Partial)

| Category | Supported Models |
|----------|-----------------|
| Bike Computers | Edge 130 Plus, Edge 540, Edge 840, Edge 1040, Edge Explore/Explore 2 |
| Handhelds | eTrex SE, GPSMAP 66s |
| Smartwatches | Instinct 3, Descent Mk3, Fenix 3/6X Pro, Forerunner 165/945, Venu X1, Vivoactive 6, Vivomove Sport, Vivosmart 3 |
| HR Monitors | HRM-Pro Plus, HRM 200 |
| Other | inReach Mini 2 |

Support is often **partial** -- some features work, others do not. Newer models tend to have better support.

### Data Available

- Activity files (.fit/.gpx) downloaded directly from device
- Heart rate (real-time and historical)
- Sleep tracking
- HRV data
- Steps, calories
- SpO2, VO2 Max
- Stress data
- Respiration rate
- Temperature
- Diving depth (newer versions)

### As a Data Source

- **Direct device sync** via Bluetooth -- no cloud dependency
- Exports to **Health Connect** (Android) for interop
- Local data storage with export capabilities
- Does NOT pull from Garmin Connect servers
- Firmware updates and AGPS supported via manual file upload

### Limitations for This Project

- **Android only** -- no iOS, no desktop
- Garmin support is partial and device-dependent
- Cannot access historical data from Garmin Connect servers
- Not suitable as a primary data pipeline; better as a complementary/fallback source
- Requires the physical Garmin device to be nearby for sync

---

## 8. Garmin API Blocking Status

### Has Garmin Been Blocking Unofficial Access?

**As of March 2026: No evidence of active blocking, rate limiting changes, or legal action against unofficial API libraries.**

Key findings:
- python-garminconnect has been continuously functional with regular releases through 2025-2026
- garth's OAuth approach (mimicking the mobile app) has remained stable
- No reports of tokens being invalidated or accounts being banned
- No legal threats or cease-and-desist letters reported
- The libraries have adapted to auth changes (e.g., MFA support) proactively

### Risk Factors

| Risk | Level | Notes |
|------|-------|-------|
| API endpoint changes | Medium | Garmin occasionally changes URLs/responses; libraries adapt within days/weeks |
| Auth flow changes | Low-Medium | OAuth flow has been stable; garth mimics official app |
| Rate limiting | Low | Already exists (~5 min recommended); no tightening observed |
| Account bans | Very Low | No reports of accounts being banned for API use |
| Legal action | Very Low | No known cases; Garmin has not sent C&D letters to library maintainers |
| Cloudflare/bot protection | Low | Some tools (garminexport) handle this; not a major barrier |

### Garmin's Official APIs

Garmin does offer official APIs but they are restrictive:
- **Garmin Health API** (wellness-api): For commercial/partner use only; requires business agreement
- **Connect IQ SDK**: For building watch apps, not for data extraction
- **OAuth2 PKCE**: Official auth flow for registered apps; requires Consumer Key/Secret from Garmin

The unofficial libraries exist because Garmin does not offer a personal/developer API for accessing your own data.

---

## 9. Comparison Matrix

| Feature | garminconnect (Python) | garth (Python) | garmin-connect (Node.js) | FIT SDK | gcexport |
|---------|----------------------|----------------|------------------------|---------|----------|
| **Language** | Python 3 | Python 3 | Node.js | Multi | Python |
| **Purpose** | Full API wrapper | Auth only | API wrapper | File parser | Bulk export |
| **Auth** | Via garth (OAuth) | OAuth1/OAuth2 | Username/password OAuth | N/A | OAuth session |
| **Endpoints** | 100+ | Direct HTTP | ~15-20 | N/A | Activities |
| **Real-time data** | Yes | Yes (manual) | Yes | No | No |
| **Historical data** | Yes (date ranges) | Yes (manual) | Limited | Yes (from files) | Yes (bulk) |
| **HRV** | Yes | Yes (manual) | No built-in | Yes | No |
| **Body Battery** | Yes | Yes (manual) | No built-in | Yes | No |
| **Sleep** | Yes | Yes (manual) | Yes | Yes | No |
| **Stress** | Yes | Yes (manual) | No built-in | Yes | No |
| **SpO2** | Yes | Yes (manual) | No built-in | Yes | No |
| **Activity download** | Yes (FIT/TCX/GPX) | Yes (manual) | Yes | Parses FIT | Yes |
| **Maintenance** | Very active | Active | Active | Official | Active |
| **Community** | Large | Medium | Medium | Official | Medium |
| **Risk of breaking** | Medium | Low-Medium | Medium | None | Medium |

---

## 10. Recommendations

### Primary Data Access Strategy

**Use `garminconnect` (Python) as the primary library** because:
- Most comprehensive endpoint coverage (100+)
- Actively maintained with a responsive community
- Stable authentication via garth
- Used by Home Assistant (proves reliability at scale)
- Supports all the health metrics we need (HR, HRV, sleep, stress, body battery, SpO2, etc.)

### Complementary: FIT File Parsing

**Use `@garmin/fitsdk` or `garmin_fit_sdk` for detailed activity data** because:
- FIT files contain per-second time series data not available via API
- GPS coordinates, power data, cadence at full resolution
- Can be downloaded via garminconnect, then parsed locally
- No API dependency for parsing -- purely offline

### Backup / Bulk Export

**Use `pe-st/garmin-connect-export` or `tcgoetz/GarminDB` for initial data seeding** to:
- Backfill historical data
- Create a local archive of all activities
- Feed into a database for analysis

### Architecture Implications

```
[Garmin Device] --> [Garmin Connect Cloud]
                         |
                    [garminconnect library]
                         |
              +----------+----------+
              |                     |
    [Daily Summary API]    [Activity Download]
    (JSON: steps, HR,      (FIT files)
     sleep, stress,              |
     body battery,          [FIT SDK Parser]
     SpO2, HRV)            (per-second data)
              |                     |
              +----------+----------+
                         |
                   [Our Database]
                         |
                   [AI Analysis]
```

### Key Technical Notes

1. **Token management**: Save garth tokens, refresh only when needed. Tokens last ~1 year.
2. **Rate limiting**: Space API calls by at least 5 minutes. Batch daily data pulls.
3. **Data freshness**: Garmin Connect data updates after device sync (typically when user opens Garmin Connect app).
4. **MFA consideration**: If the user has MFA enabled, initial setup requires interactive login. Consider disabling MFA on a dedicated Garmin account or handling the MFA flow.
5. **No official API**: This is all reverse-engineered. Keep library versions pinned and test regularly.
6. **FIT files are king**: For detailed analysis (training load, HR zones, GPS), always prefer FIT file parsing over API summaries.
