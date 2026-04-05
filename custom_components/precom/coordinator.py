"""DataUpdateCoordinator for PreCom - handles polling and token refresh."""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import PreComApiClient, PreComAuthError, PreComApiError
from .const import DOMAIN, STATE_NO_ALARM

_LOGGER = logging.getLogger(__name__)


class PreComCoordinatorData:
    """Typed container for the data fetched on each polling cycle."""

    def __init__(
        self,
        alarm_id: str,
        functions: list[dict[str, Any]],
        text: str,
        timestamp: str,
    ) -> None:
        self.alarm_id = alarm_id      # alarm ID string, or STATE_NO_ALARM
        self.functions = functions    # list of {label: str, users: list[str]}
        self.text = text              # alarm message text
        self.timestamp = timestamp    # alarm date/time string from API


class PreComCoordinator(DataUpdateCoordinator[PreComCoordinatorData]):
    """Polls PreCom every scan_interval seconds.

    On PreComAuthError the coordinator re-authenticates once and retries before
    raising UpdateFailed. This mirrors the original YAML pattern of always
    fetching a fresh token before each alarm check, but avoids a full
    authenticate() call on every successful poll cycle.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        client: PreComApiClient,
        scan_interval: int,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.client = client

    async def _async_update_data(self) -> PreComCoordinatorData:
        """Fetch latest alarm data. Called automatically by HA on each interval."""
        try:
            alarms = await self.client.get_alarm_messages()
        except PreComAuthError:
            _LOGGER.debug("PreCom token rejected, re-authenticating")
            try:
                await self.client.authenticate()
                alarms = await self.client.get_alarm_messages()
            except PreComAuthError as err:
                raise UpdateFailed(
                    f"PreCom authentication failed after token refresh: {err}"
                ) from err
            except PreComApiError as err:
                raise UpdateFailed(
                    f"PreCom API error after token refresh: {err}"
                ) from err
        except PreComApiError as err:
            raise UpdateFailed(f"PreCom API error: {err}") from err

        if not alarms:
            return PreComCoordinatorData(
                alarm_id=STATE_NO_ALARM, functions=[], text="", timestamp=""
            )

        latest = alarms[0]
        alarm_id = str(latest.get("MsgInID", STATE_NO_ALARM))
        text = str(latest.get("Text", ""))

        # The API returns Timestamp as an ISO 8601 date-time string.
        # Parse it and attach UTC if no timezone is present.
        raw_ts = latest.get("Timestamp", "")
        timestamp = ""
        if raw_ts:
            try:
                dt = datetime.fromisoformat(str(raw_ts))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                timestamp = dt.isoformat()
            except ValueError:
                timestamp = str(raw_ts)

        # NOTE: The API uses "ServiceFuntions" (missing 'c') — this is an
        # intentional typo in the PreCom API response. Do not correct it.
        raw_functions = latest.get("Group", {}).get("ServiceFuntions", [])
        functions = [
            {
                "label": func.get("Label", ""),
                "users": [u.get("FullName", "") for u in func.get("Users", [])],
            }
            for func in raw_functions
        ]

        return PreComCoordinatorData(
            alarm_id=alarm_id, functions=functions, text=text, timestamp=timestamp
        )

    async def async_set_outside_region(self, hours: int) -> None:
        """Call set_outside_region on the API client with token-refresh retry."""
        try:
            await self.client.set_outside_region(hours)
        except PreComAuthError:
            await self.client.authenticate()
            await self.client.set_outside_region(hours)

    async def async_set_in_region(self) -> None:
        """Call set_in_region on the API client with token-refresh retry."""
        try:
            await self.client.set_in_region()
        except PreComAuthError:
            await self.client.authenticate()
            await self.client.set_in_region()
