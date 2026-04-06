"""Constants for the PreCom integration."""

DOMAIN = "precom"

# Config entry keys
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_SCAN_INTERVAL = "scan_interval"
DEFAULT_SCAN_INTERVAL = 60

# API endpoints
API_BASE_URL = "https://app.pre-com.nl"
API_TOKEN_URL = f"{API_BASE_URL}/Token"
API_ALARMS_URL = f"{API_BASE_URL}/api/v2/Message/GetAlarmMessages"
API_SET_OUTSIDE_REGION_URL = f"{API_BASE_URL}/api/v2/Available/SetOutsideRegion"
API_USER_INFO_URL = f"{API_BASE_URL}/api/v2/User/GetUserInfo"
API_GROUPS_URL = f"{API_BASE_URL}/api/v2/Group/GetAllGroups"

# Service names
SERVICE_SET_UNAVAILABLE = "set_unavailable"
SERVICE_SET_AVAILABLE = "set_available"
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

# Availability sensor attribute keys
ATTR_NOT_AVAILABLE_TIMESTAMP = "not_available_timestamp"
ATTR_NOT_AVAILABLE_SCHEDULED = "not_available_scheduled"

# Groups sensor attribute keys
ATTR_GROUPS = "groups"
