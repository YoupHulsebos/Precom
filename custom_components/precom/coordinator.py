"""DataUpdateCoordinator for PreCom - handles polling and token refresh."""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
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
        is_available: bool,
        not_available_timestamp: str,
        not_available_scheduled: bool,
    ) -> None:
        self.alarm_id = alarm_id      # alarm ID string, or STATE_NO_ALARM
        self.functions = functions    # list of {label: str, users: list[str]}
        self.text = text              # alarm message text
        self.timestamp = timestamp    # alarm date/time string from API
        self.is_available = is_available              # True when user is available
        self.not_available_timestamp = not_available_timestamp  # ISO ts of unavailability
        self.not_available_scheduled = not_available_scheduled  # scheduled absence


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
        entry: ConfigEntry,
        client: PreComApiClient,
        scan_interval: int | None,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval) if scan_interval else None,
        )
        self._entry = entry
        self.client = client
        self._unavailable = False

    async def _fetch_alarms(self) -> list[dict]:
        """Fetch alarms, re-authenticating once on token rejection."""
        try:
            return await self.client.get_alarm_messages()
        except PreComAuthError:
            pass

        # Token was rejected — re-authenticate and retry once.
        _LOGGER.debug("PreCom token rejected, re-authenticating")
        await self.client.authenticate()
        return await self.client.get_alarm_messages()

    async def _fetch_user_info(self) -> dict:
        """Fetch user info, re-authenticating once on token rejection."""
        try:
            return await self.client.get_user_info()
        except PreComAuthError:
            pass

        await self.client.authenticate()
        return await self.client.get_user_info()

    def _mark_unavailable(self, reason: str) -> None:
        """Log a warning the first time the service becomes unavailable."""
        if not self._unavailable:
            _LOGGER.warning("PreCom unavailable: %s", reason)
            self._unavailable = True

    def _mark_available(self) -> None:
        """Log recovery once when the service becomes reachable again."""
        if self._unavailable:
            _LOGGER.info("PreCom API connection restored")
            self._unavailable = False

    async def _async_update_data(self) -> PreComCoordinatorData:
        """Fetch latest alarm data and user info. Called automatically by HA on each interval."""
        try:
            alarms = await self._fetch_alarms()
            user_info = await self._fetch_user_info()
        except PreComAuthError as err:
            self._mark_unavailable(f"authentication failed after token refresh: {err}")
            self._entry.async_start_reauth(self.hass)
            raise UpdateFailed(f"PreCom auth failed: {err}") from err
        except PreComApiError as err:
            self._mark_unavailable(f"API error: {err}")
            raise UpdateFailed(f"PreCom API error: {err}") from err

        self._mark_available()

        # Parse user availability info
        # NOTE: The API uses "NotAvailalbeScheduled" (missing 'i') — intentional typo.
        is_available = not bool(user_info.get("NotAvailable", False))
        not_available_timestamp = ""
        raw_na_ts = user_info.get("NotAvailableTimestamp", "")
        if raw_na_ts:
            try:
                dt = datetime.fromisoformat(str(raw_na_ts))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                not_available_timestamp = dt.isoformat()
            except ValueError:
                not_available_timestamp = str(raw_na_ts)
        not_available_scheduled = bool(user_info.get("NotAvailalbeScheduled", False))

        if not alarms:
            return PreComCoordinatorData(
                alarm_id=STATE_NO_ALARM,
                functions=[],
                text="",
                timestamp="",
                is_available=is_available,
                not_available_timestamp=not_available_timestamp,
                not_available_scheduled=not_available_scheduled,
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
            alarm_id=alarm_id,
            functions=functions,
            text=text,
            timestamp=timestamp,
            is_available=is_available,
            not_available_timestamp=not_available_timestamp,
            not_available_scheduled=not_available_scheduled,
        )

    async def async_set_unavailable(self, hours: int) -> None:
        """Call set_unavailable on the API client with token-refresh retry."""
        try:
            await self.client.set_unavailable(hours)
        except PreComAuthError:
            await self.client.authenticate()
            await self.client.set_unavailable(hours)

    async def async_set_available(self) -> None:
        """Call set_available on the API client with token-refresh retry."""
        try:
            await self.client.set_available()
        except PreComAuthError:
            await self.client.authenticate()
            await self.client.set_available()
