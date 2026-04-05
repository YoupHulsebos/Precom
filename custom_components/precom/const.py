"""Constants for the PreCom integration."""

DOMAIN = "precom"

# Config entry keys
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_SCAN_INTERVAL = "scan_interval"

# Defaults
DEFAULT_SCAN_INTERVAL = 60  # seconds

# API endpoints
API_BASE_URL = "https://app.pre-com.nl"
API_TOKEN_URL = f"{API_BASE_URL}/Token"
API_ALARMS_URL = f"{API_BASE_URL}/api/v2/Message/GetAlarmMessages"
API_SET_OUTSIDE_REGION_URL = f"{API_BASE_URL}/api/v2/Available/SetOutsideRegion"

# Service names
SERVICE_SET_OUTSIDE_REGION = "set_outside_region"
SERVICE_SET_IN_REGION = "set_in_region"
SERVICE_UPDATE_ALARM = "update_alarm"

# Service field names
ATTR_HOURS = "hours"

# Sensor state when no alarm is active
STATE_NO_ALARM = "none"

# Sensor extra attribute keys
ATTR_ALARM_ID = "alarm_id"
ATTR_FUNCTIONS = "functions"
ATTR_FUNCTIONS_FORMATTED = "functions_formatted"
ATTR_LAST_UPDATED = "last_updated"
ATTR_TEXT = "text"
ATTR_TIMESTAMP = "timestamp"
