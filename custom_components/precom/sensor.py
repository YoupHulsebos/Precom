"""PreCom sensor platform — sensor.precom_last_alarm."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_ALARM_ID,
    ATTR_FUNCTIONS,
    ATTR_FUNCTIONS_FORMATTED,
    ATTR_LAST_UPDATED,
    ATTR_TEXT,
    ATTR_TIMESTAMP,
    DOMAIN,
    STATE_NO_ALARM,
)
from .coordinator import PreComCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the PreCom sensor from a config entry."""
    coordinator: PreComCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([PreComLastAlarmSensor(coordinator, entry)])


class PreComLastAlarmSensor(CoordinatorEntity[PreComCoordinator], SensorEntity):
    """Represents the most recent PreCom alarm.

    State:    alarm ID (str) when an alarm is active, "none" when idle.
    Attributes:
        alarm_id     — same as state, for template convenience
        functions    — list of {label: str, users: list[str]}
        last_updated — ISO timestamp of the last successful poll
    """

    _attr_has_entity_name = True
    _attr_name = "Last Alarm"
    _attr_icon = "mdi:fire-truck"

    def __init__(
        self,
        coordinator: PreComCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_last_alarm"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "PreCom",
            "manufacturer": "PreCom",
            "model": "Cloud Alerting Service",
            "entry_type": "service",
        }

    @property
    def native_value(self) -> str:
        """Return the alarm ID, or 'none' when no alarm is active."""
        if self.coordinator.data is None:
            return STATE_NO_ALARM
        return self.coordinator.data.alarm_id

    @staticmethod
    def _format_functions(functions: list[dict]) -> str:
        """Return a human-readable string listing each function and its users."""
        lines: list[str] = []
        for func in functions:
            users: list[str] = func.get("users", [])
            lines.append(f"{func.get('label', '')} ({len(users)}):")
            for user in users:
                lines.append(f"- {user}")
        return "\n".join(lines)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return alarm details as entity attributes."""
        if self.coordinator.data is None:
            return {}
        return {
            ATTR_ALARM_ID: self.coordinator.data.alarm_id,
            ATTR_TEXT: self.coordinator.data.text,
            ATTR_TIMESTAMP: self.coordinator.data.timestamp,
            ATTR_FUNCTIONS: self.coordinator.data.functions,
            ATTR_FUNCTIONS_FORMATTED: self._format_functions(
                self.coordinator.data.functions
            ),
            ATTR_LAST_UPDATED: datetime.now(timezone.utc).isoformat(),
        }
