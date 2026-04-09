# Impact Map: PreCom Home Assistant Integration

## 1. Goals

| # | Goal | Why | Success Criteria |
|---|------|-----|------------------|
| G1 | Volunteer firefighters receive P2000 alarm notifications through Home Assistant | PreCom's mobile app requires manual checking; HA enables push notifications, smart-home triggers (sirens, lights), and automation chains that reduce response time | Alarm state changes in HA within the configured polling interval; users can build automations that trigger on alarm state changes |
| G2 | Firefighters can report their availability from Home Assistant without opening the PreCom app | Manually opening the PreCom app to toggle availability is friction that leads to outdated status; HA automations (geofencing, routines) can keep it accurate automatically | Users can call `set_available` / `set_unavailable` services; availability binary sensor reflects current status within one poll cycle |
| G3 | Station officers can monitor staffing levels for all functions at their fire station | Understaffing is a safety risk; early visibility into gaps allows proactive call-outs before an alarm happens | Binary sensors per function show staffing shortfalls for the next 24 hours at 15-minute granularity |
| G4 | Achieve Home Assistant Gold-level integration quality | Gold quality signals reliability and earns trust from the HA community; required for potential core inclusion and HACS default listing | Pass all Gold-level quality scale rules as defined at developers.home-assistant.io |

---

## 2. Actors

| Actor | Description | Needs | Problems | Related Goals |
|-------|-------------|-------|----------|---------------|
| **Volunteer firefighter** | A PreCom user who responds to alarms and needs to stay informed about call-outs while at home | Instant awareness of new alarms; ability to control availability without switching apps; at-a-glance staffing overview | PreCom app requires manual checking; no smart-home integration; easy to forget to update availability when leaving/returning home | G1, G2, G3 |
| **Station officer / group leader** | Oversees staffing for a station or group; needs to know if upcoming shifts are covered | Visibility into staffing gaps across all functions; proactive alerts when understaffing is detected | Must log into PreCom portal to check staffing; no automated alerting for gaps; no way to see 24h ahead easily | G3 |
| **Home automation enthusiast** | A firefighter who uses HA extensively and wants deep integration | Clean entities, rich attributes, automation-friendly services, reliable polling, good error handling | Existing DIY solutions (REST sensors, shell commands) are fragile and hard to maintain | G1, G2, G4 |
| **HACS / HA reviewer** | Evaluates the integration for quality, security, and HA best practices | Standards compliance, proper config flow, diagnostics, translations, test coverage | Many community integrations lack polish, tests, and documentation | G4 |

---

## 3. Impacts (Desired Behavior Changes)

### Volunteer firefighter

| Impact | Deliverables that enable it | Goal |
|--------|----------------------------|------|
| Responds to alarms faster because HA triggers immediate notifications, lights, or sirens | Alarm sensor with state changes, rich attributes, automation examples | G1 |
| Keeps availability status accurate without effort because HA automates it via geofencing | Availability binary sensor + set_available / set_unavailable services | G2 |
| Checks staffing from the HA dashboard instead of opening the PreCom app | Staffing binary sensors per function with shortage attributes | G3 |

### Station officer / group leader

| Impact | Deliverables that enable it | Goal |
|--------|----------------------------|------|
| Gets notified of understaffing before an alarm happens and can proactively call people in | Staffing binary sensors with problem device class; automation-ready state changes | G3 |

### Home automation enthusiast

| Impact | Deliverables that enable it | Goal |
|--------|----------------------------|------|
| Replaces fragile DIY YAML with a maintained, installable integration | Full HACS-compatible integration with config flow, options, services | G1, G2 |
| Builds complex automations using structured entity attributes | Rich attributes on all sensors (functions list, formatted text, shortage numbers) | G1, G3 |

### HACS / HA reviewer

| Impact | Deliverables that enable it | Goal |
|--------|----------------------------|------|
| Approves the integration for Gold quality listing | Test coverage, diagnostics, translations, proper error handling, documentation | G4 |

---

## 4. Deliverables

### Epic 1: Alarm Monitoring

| # | Feature | Status | Actor | Impact | Goal |
|---|---------|--------|-------|--------|------|
| D1.1 | `sensor.precom_last_alarm` -- exposes latest alarm text, ID, timestamp, functions | BUILT | Firefighter, Enthusiast | Immediate alarm awareness via HA | G1 |
| D1.2 | Rich attributes: `alarm_id`, `text`, `timestamp`, `functions`, `functions_formatted`, `last_updated` | BUILT | Firefighter, Enthusiast | Enables detailed notification templates and automations | G1 |
| D1.3 | `precom.update_alarm` service -- force-refresh alarm data on demand | BUILT | Firefighter | Reduces latency when polling interval is long | G1 |
| D1.4 | Alarm history sensor -- expose last N alarms, not just the most recent | NOT BUILT | Firefighter, Officer | Review recent alarm activity without opening PreCom portal | G1 |
| D1.5 | Alarm response service -- call `SetAvailabilityForAlarmMessage` to respond to an alarm directly from HA | NOT BUILT | Firefighter | Respond to alarms without opening the app | G1, G2 |
| D1.6 | Event firing on alarm state change -- fire an HA event (not just state change) for richer automation triggers | NOT BUILT | Enthusiast | Enables event-based automations with full alarm payload | G1 |

### Epic 2: Availability Management

| # | Feature | Status | Actor | Impact | Goal |
|---|---------|--------|-------|--------|------|
| D2.1 | `binary_sensor.precom_availability` -- shows current availability status | BUILT | Firefighter | At-a-glance availability status | G2 |
| D2.2 | `precom.set_unavailable` service -- mark unavailable for 1-72 hours | BUILT | Firefighter | Control availability from HA | G2 |
| D2.3 | `precom.set_available` service -- cancel unavailable status | BUILT | Firefighter | Return to available from HA | G2 |
| D2.4 | Availability attributes: `not_available_timestamp`, `not_available_scheduled` | BUILT | Firefighter | Know when unavailability expires or if it is scheduled | G2 |
| D2.5 | Geofence position reporting -- call `SetGeofencePosition` to set GPS/address | NOT BUILT | Firefighter | Automatically report location-based availability | G2 |

### Epic 3: Staffing Monitoring

| # | Feature | Status | Actor | Impact | Goal |
|---|---------|--------|-------|--------|------|
| D3.1 | `binary_sensor.precom_staffing_<function>` -- one per function, problem class | BUILT | Firefighter, Officer | See understaffing at a glance | G3 |
| D3.2 | 24-hour look-ahead at 15-minute granularity via DayTotals | BUILT | Officer | Proactive staffing gap detection | G3 |
| D3.3 | Staffing attributes: `number_needed`, `current_available`, `current_unavailable`, `shortage` | BUILT | Officer, Enthusiast | Detailed staffing data for automations | G3 |
| D3.4 | Per-group staffing breakdown in attributes | BUILT (partial) | Officer | Compare staffing across groups | G3 |
| D3.5 | Staffing timeline sensor -- expose per-slot staffing for the next 24h as a list attribute | NOT BUILT | Officer, Enthusiast | Visualize staffing gaps on a timeline card | G3 |

### Epic 4: Integration Setup and Configuration

| # | Feature | Status | Actor | Impact | Goal |
|---|---------|--------|-------|--------|------|
| D4.1 | Config flow with credential validation | BUILT | All | Easy setup via HA UI | G4 |
| D4.2 | Reauthentication flow (handles password changes) | BUILT | All | Seamless recovery from auth failures | G4 |
| D4.3 | Reconfigure flow (change username/password without removing entry) | BUILT | All | Convenient credential updates | G4 |
| D4.4 | Options flow for scan interval | BUILT | All | Tune polling frequency without reconfiguring | G4 |
| D4.5 | Diagnostics support (redacted config dump) | BUILT | Reviewer | Easier troubleshooting and support | G4 |
| D4.6 | English and Dutch translations | BUILT | All | Localized UI for Dutch fire service users | G4 |
| D4.7 | HACS compatibility (`hacs.json`, manifest, icons) | BUILT | Reviewer | Installable via HACS | G4 |

### Epic 5: Quality and Reliability

| # | Feature | Status | Actor | Impact | Goal |
|---|---------|--------|-------|--------|------|
| D5.1 | Token refresh with single-retry on 401 | BUILT | All | Reliable operation without manual re-auth | G4 |
| D5.2 | `ConfigEntryNotReady` on startup failure with HA backoff | BUILT | All | Graceful handling of temporary API outages | G4 |
| D5.3 | Update listener -- reload on options change | BUILT | All | Options take effect without restart | G4 |
| D5.4 | Automated test suite (unit + integration tests) | NOT BUILT | Reviewer | Required for Gold quality; catches regressions | G4 |
| D5.5 | CI pipeline (linting, type checking, test execution) | NOT BUILT | Reviewer | Automated quality gate on every PR | G4 |
| D5.6 | Gold-level quality scale compliance audit | NOT BUILT | Reviewer | Systematic verification against HA quality rules | G4 |
| D5.7 | Fix manifest placeholder URLs (`yourusername`) | NOT BUILT | Reviewer | Correct repository links for issue tracking and docs | G4 |

### Epic 6: Groups and User Context

| # | Feature | Status | Actor | Impact | Goal |
|---|---------|--------|-------|--------|------|
| D6.1 | `sensor.precom_groups` -- number of groups with group list attribute | BUILT | Firefighter | Know which groups you belong to | G1, G3 |
| D6.2 | Active messages sensor -- expose `GetMessages` for non-alarm messages | NOT BUILT | Firefighter | See operational messages (not just alarms) | G1 |

---

## 5. Roadmap and Prioritization

### MVP (v1.0.0) -- SHIPPED

The current codebase already constitutes a functional MVP. All core use cases are addressed:

| Feature | Rationale |
|---------|-----------|
| D1.1 Alarm sensor | Core value proposition -- the reason the integration exists |
| D1.2 Rich alarm attributes | Enables useful automations (the "why" behind installing this) |
| D1.3 Force-refresh service | Compensates for polling-only architecture |
| D2.1 Availability sensor | Second pillar of the integration |
| D2.2 Set unavailable service | Enables availability automation |
| D2.3 Set available service | Completes the availability loop |
| D2.4 Availability attributes | Context for availability state |
| D3.1 Staffing sensors | Third pillar -- station-level awareness |
| D3.2 24h look-ahead | Makes staffing sensors actionable |
| D3.3 Staffing attributes | Enables staffing automations |
| D4.1-D4.7 All config/setup | Required for a usable, installable integration |
| D5.1-D5.3 Reliability features | Required for production use |
| D6.1 Groups sensor | Supporting context |

### v1.1 -- Quality and Polish

Focus: achieve Gold-level quality and close the most impactful gaps.

| Feature | Priority | Rationale |
|---------|----------|-----------|
| D5.4 Automated test suite | HIGH | Blocks Gold quality; required for confidence in future changes |
| D5.5 CI pipeline | HIGH | Automates quality enforcement; pairs with test suite |
| D5.7 Fix manifest URLs | HIGH | Low effort, blocks proper HACS listing |
| D5.6 Gold quality audit | HIGH | Systematic gap analysis against HA rules |
| D1.5 Alarm response service | MEDIUM | High-value feature that closes the "respond from HA" loop |
| D2.5 Geofence position reporting | MEDIUM | Unlocks fully automated availability via phone GPS |

### Beyond v1.1

Features that are valuable but not essential. Build only if there is clear user demand.

| Feature | Rationale for deferral |
|---------|----------------------|
| D1.4 Alarm history sensor | Nice-to-have; PreCom portal serves this need today |
| D1.6 Event firing on alarm change | State-change triggers already work; events add marginal value |
| D3.5 Staffing timeline sensor | Useful for dashboards but complex to implement and maintain |
| D6.2 Active messages sensor | Low demand; not all PreCom users receive non-alarm messages |

---

## 6. What Is Built vs. What Is Not

### Built (16 deliverables)

- Complete alarm monitoring with rich attributes and on-demand refresh
- Full availability management (read status + set available/unavailable)
- Dynamic staffing sensors per function with 24h look-ahead
- Full config flow suite (setup, reauth, reconfigure, options)
- Diagnostics, translations (EN + NL), HACS compatibility
- Token refresh retry logic, graceful startup failure handling

### Not Yet Built (8 deliverables)

- Automated tests and CI pipeline (highest priority gap)
- Alarm response from HA (`SetAvailabilityForAlarmMessage`)
- Geofence position reporting (`SetGeofencePosition`)
- Alarm history, event firing, staffing timeline
- Active (non-alarm) messages
- Manifest URL placeholders still reference `yourusername`

---

## 7. Key Decisions and Constraints

| Decision | Rationale |
|----------|-----------|
| Polling-only architecture | PreCom API offers no webhooks or push; minimum latency = scan interval |
| Single account per config entry | Matches HA convention; multiple accounts = multiple entries |
| Dynamic sensor creation for staffing | Functions vary per user/group; sensors are added as functions are discovered |
| Entity services (not global services) | HA best practice; services target specific entities |
| `ServiceFuntions` typo preserved | Intentional match to PreCom API response; do not "correct" |
| Token refresh at coordinator level | Coordinator owns retry policy; API client stays stateless regarding retries |
