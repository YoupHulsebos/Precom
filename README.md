# PreCom for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

Home Assistant integration for the [PreCom](https://app.pre-com.nl) fire department alerting service. Monitors incoming P2000 alarms and lets you report your availability (inside or outside your response region) directly from Home Assistant.

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
4. Optionally set a **scan interval** (default: 60 s, range: 10–3600 s).

Credentials are validated against the PreCom API before the entry is saved.

## Entities

| Entity | Type | State |
|--------|------|-------|
| `sensor.precom_last_alarm` | Sensor | Alarm ID when active, `none` when idle |

### Sensor attributes

| Attribute | Description |
|-----------|-------------|
| `alarm_id` | Same as entity state — useful in templates |
| `functions` | List of `{label, users}` objects for the alarm |
| `last_updated` | ISO timestamp of the last successful poll |

## Services

### `precom.set_outside_region`

Mark yourself as **outside** your response region.

| Field | Required | Description |
|-------|----------|-------------|
| `hours` | Yes | Duration in hours (1–24) |
| `geofence` | Yes | Geofence identifier as used by the PreCom API |

### `precom.set_in_region`

Cancel the outside-region status and mark yourself as **back inside** your response region. No fields required.

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

- **Invalid credentials on setup** — verify your username and password at [app.pre-com.nl](https://app.pre-com.nl).
- **Sensor stuck on `none`** — check that your account has access to alarm messages and review the Home Assistant logs for API errors.
- **Rate limiting / connectivity** — increase the scan interval in the integration options.

## Contributing

Issues and pull requests are welcome. Please open an issue before submitting large changes.
