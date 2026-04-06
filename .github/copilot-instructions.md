# PreCom HACS Integration — Copilot Instructions

## Project Overview
Home Assistant HACS custom integration for the **PreCom** fire department alerting service (https://portal.pre-com.nl). Allows HA users to view the latest P2000-style alarm and report themselves in or outside of their response region.

## Architecture

```
custom_components/precom/
├── __init__.py       # Entry setup, HA service registration (set_outside_region, set_in_region)
├── api.py            # PreComApiClient — all HTTP; raises PreComAuthError / PreComApiError
├── coordinator.py    # PreComCoordinator — polling + token-refresh retry logic
├── sensor.py         # PreComLastAlarmSensor (state = alarm ID or "none")
├── config_flow.py    # UI config + options flow (credentials + scan_interval)
├── const.py          # All constants; single source of truth for URLs, keys, service names
├── services.yaml     # Service descriptions for HA UI
└── strings.json      # Translatable UI strings
```

**Data flow:** `api.py` → `coordinator.py` → `sensor.py` (via `CoordinatorEntity`)  
**Services:** registered in `__init__.py`, forwarded through `coordinator.py` to `api.py`

## API Details

- **Base URL:** `https://app.pre-com.nl` (≠ `pre-com.nl/Mobile` in the Swagger UI)
- **Swagger spec:** https://pre-com.nl/Mobile/swagger/docs/v2
- **Auth:** OAuth2 password grant — POST `/Token` with `application/x-www-form-urlencoded`
- Token is returned as a **quoted JSON string** — strip surrounding `"` characters before use
- Auth failure returns **HTTP 400** (not 401); 401 means the token was rejected on a subsequent call

## Critical API Quirks (Do Not "Fix" These)

- `"ServiceFuntions"` — missing the letter 'c' — is an **intentional typo in the PreCom API response**. Never rename this key.
- `GetAlarmMessages` — the Swagger shows `msgInID` + `previousOrNext` params; the integration calls it without params to get the default latest list; this is intentional.
- `SetOutsideRegion` body must be `{"Location": {"Geofence": "EXIT"}}` or `"ENTER"` — the `region` param is a `Region` model, not a plain string.

## Token Refresh Pattern

`PreComCoordinator` re-authenticates once on `PreComAuthError`, then retries the failed call. **Do not move the token refresh logic into `api.py`** — the coordinator owns retry policy.

## HA Integration Conventions

- Use `async_get_clientsession(hass)` — never create a standalone `aiohttp.ClientSession`
- Raise `ConfigEntryNotReady` (via `async_config_entry_first_refresh`) on startup failure; HA will back off and retry
- Unload services only when the **last** config entry is removed (see `async_unload_entry`)
- `SensorEntity` state is either the alarm `id` string or the constant `STATE_NO_ALARM = "none"`
- Sensor attributes: `alarm_id`, `functions` (list of `{label, users}`), `last_updated`

## Available API Endpoints (for future features)

| Endpoint | Purpose |
|---|---|
| `POST /Token` | Get JWT |
| `GET /api/v2/Message/GetAlarmMessages` | Latest alarm(s) |
| `POST /api/v2/Available/SetOutsideRegion` | Report outside region |
| `POST /api/v2/Available/SetAvailable` | Report available/in region |
| `POST /api/v2/Available/SetGeofencePosition` | Set GPS/address position |
| `GET /api/v2/User/GetUserInfo` | User + availability status (`NotAvailable` flag) |
| `GET /api/v2/Message/GetMessages` | Active messages (filter by `controlID`) |
| `POST /api/v2/Message/SetAvailabilityForAlarmMessage` | Respond to alarm |

## Key Constants (`const.py`)

- `API_BASE_URL = "https://app.pre-com.nl"`
- `DEFAULT_SCAN_INTERVAL = 60` seconds (configurable 10–3600)
- `STATE_NO_ALARM = "none"` — sensor state when no alarm is active
- `SERVICE_SET_OUTSIDE_REGION`, `SERVICE_SET_IN_REGION` — HA service names

## Development Notes

- No automated tests yet; test manually via HA dev tools → Services
- No external `requirements` — relies only on `aiohttp` (bundled with HA)
- `hacs.json` is present; follow HACS validation rules (manifest fields, versioning)
- `manifest.json` placeholder URLs (`yourusername`) should be updated before publishing
- Goal is a Gold integration. We should follow rules on: https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/