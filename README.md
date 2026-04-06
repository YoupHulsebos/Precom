# PreCom for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

Home Assistant integration for the [PreCom](https://portal.pre-com.nl) fire department alerting service. Monitors incoming P2000 alarms and lets you report your availability (inside or outside your response region) directly from Home Assistant.

## Requirements

- Home Assistant 2024.1.0 or newer
- A PreCom account (username + password)
- [HACS](https://hacs.xyz) installed

## Installation

### HACS (recommended)

1. Open HACS → **Integrations**.
2. Click the three-dot menu → **Custom repositories**.
3. Add this repository URL and select category **Integration**.
4. Search for **PreCom** and click **Download**.
5. Restart Home Assistant.

### Manual

1. Copy the `custom_components/precom` folder into your `<config>/custom_components/` directory.
2. Restart Home Assistant.

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**.
2. Search for **PreCom**.
3. Enter your PreCom **username** and **password**.
4. Optionally set a **scan interval** (range: 10–3600 s). Leave blank to disable automatic polling — use `precom.update_alarm` to refresh on demand instead.

Credentials are validated against the PreCom API before the entry is saved.

## Entities

| Entity | Type | State |
|--------|------|-------|
| `sensor.precom_last_alarm` | Sensor | Alarm ID when active, `none` when idle |

### Sensor attributes

| Attribute | Description |
|-----------|-------------|
| `alarm_id` | Same as entity state — useful in templates |
| `text` | Alarm message text |
| `timestamp` | Date/time of the alarm as returned by the API |
| `functions` | List of `{label, users}` objects for the alarm |
| `last_updated` | ISO timestamp of the last successful poll |

## Services

### `precom.set_outside_region`

Mark yourself as **outside** your response region.

| Field | Required | Description |
|-------|----------|-------------|
| `hours` | Yes | Duration in hours (1–72) |

### `precom.set_in_region`

Cancel the outside-region status and mark yourself as **back inside** your response region. No fields required.

### `precom.update_alarm`

Force an immediate refresh of the latest alarm data from PreCom, without waiting for the next scheduled poll interval. No fields required.

## Automation example

```yaml
automation:
  - alias: "Notify on new PreCom alarm"
    trigger:
      - platform: state
        entity_id: sensor.precom_last_alarm
    condition:
      - condition: template
        value_template: "{{ trigger.to_state.state != 'none' }}"
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "PreCom Alarm"
          message: "Alarm ID: {{ states('sensor.precom_last_alarm') }}"
```

## Troubleshooting

- **Invalid credentials on setup** — verify your username and password at [app.pre-com.nl](https://portal.pre-com.nl).
- **Sensor stuck on `none`** — check that your account has access to alarm messages and review the Home Assistant logs for API errors.
- **Rate limiting / connectivity** — increase the scan interval in the integration options.
- **"Authentication failed" after working correctly** — Home Assistant will automatically prompt you to re-enter your password via a re-authentication notification. Go to **Settings → Integrations → PreCom** and follow the notification.
- **Reconfiguring after an email/password change** — click the three-dot menu on the integration card → **Reconfigure**, enter new credentials.

## How data is updated

The integration uses a polling model (`iot_class: cloud_polling`). Every `scan_interval` seconds (default 60 s, configurable 10–3600 s) the coordinator calls `GET /api/v2/Message/GetAlarmMessages` on the PreCom API. The JWT token is cached in memory; if it is rejected (HTTP 401) the coordinator re-authenticates once and retries before marking the sensor unavailable.

No webhooks or push mechanisms are used.

## Use cases

- **Alarm notifications** — trigger a mobile notification, flash a light, or start a siren whenever `sensor.precom_last_alarm` changes to a non-`none` value.
- **Automatic availability reporting** — use a device tracker or input boolean to automatically call `precom.set_outside_region` when you leave home.
- **Dashboard card** — display the latest alarm text (`alarm_id`, `text`, `timestamp` attributes) on a Lovelace dashboard.
- **Response tracking** — combined with `precom.set_in_region` / `precom.set_outside_region`, build automations that keep PreCom in sync with your physical location.

## Supported functionality

| Platform | Entity | State | Notes |
|----------|--------|-------|-------|
| Sensor | `sensor.precom_last_alarm` | Alarm ID or `none` | Attributes: `alarm_id`, `text`, `timestamp`, `functions`, `last_updated` |

| Service | Description |
|---------|-------------|
| `precom.set_outside_region` | Mark user outside response region (1–72 h) |
| `precom.set_in_region` | Cancel outside-region status |
| `precom.update_alarm` | Force immediate alarm data refresh |

## Known limitations

- **Polling only** — no push support; minimum latency equals the configured scan interval.
- **No P2000 raw messages** — alarm data is what PreCom exposes via its own API; raw P2000 data is not available.
- **Single device per entry** — each config entry covers one PreCom account. Multiple accounts require multiple entries, but the domain-level services will only target the first loaded entry.
- **No alarm history** — only the latest alarm is exposed. Historical alarms are not stored or surfaced.
- **No availability status entity** — the user's in/out-of-region status is write-only (no entity reflecting the current status).

## Removing the integration

1. Go to **Settings → Devices & Services**.
2. Find the **PreCom** integration and click the three-dot menu → **Delete**.
3. Confirm deletion. Home Assistant will unload the integration and remove all associated entities and devices.
4. No files are left behind after removal.

## Contributing

Issues and pull requests are welcome. Please open an issue before submitting large changes.
