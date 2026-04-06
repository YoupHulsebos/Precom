"""PreCom binary sensor platform — user availability status."""
from __future__ import annotations

import logging
import voluptuous as vol
from typing import TYPE_CHECKING, Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import (
    AddEntitiesCallback,
    async_get_current_platform,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import PreComApiError, PreComAuthError
from .const import (
    ATTR_HOURS,
    ATTR_NOT_AVAILABLE_SCHEDULED,
    ATTR_NOT_AVAILABLE_TIMESTAMP,
    DOMAIN,
    SERVICE_SET_AVAILABLE,
    SERVICE_SET_UNAVAILABLE,
)
from .coordinator import PreComCoordinator

if TYPE_CHECKING:
    from . import PreComConfigEntry

_LOGGER = logging.getLogger(__name__)

# Coordinator centralises all data updates; no per-entity polling needed.
PARALLEL_UPDATES = 0

SET_UNAVAILABLE_SCHEMA = {
    vol.Required(ATTR_HOURS): vol.All(int, vol.Range(min=1, max=72)),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PreComConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the PreCom availability binary sensor from a config entry."""
    async_add_entities([PreComAvailabilitySensor(entry.runtime_data, entry)])

    platform = async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_SET_UNAVAILABLE,
        SET_UNAVAILABLE_SCHEMA,
        "async_set_unavailable",
    )
    platform.async_register_entity_service(
        SERVICE_SET_AVAILABLE,
        {},
        "async_set_available",
    )


class PreComAvailabilitySensor(CoordinatorEntity[PreComCoordinator], BinarySensorEntity):
    """Represents the current availability status of the PreCom user.

    State:    on  = user is available for alarm call-out
              off = user is marked unavailable (outside region or scheduled)
    Attributes:
        not_available_timestamp  — ISO timestamp when unavailability was set
        not_available_scheduled  — True when the absence is scheduler-driven
    """

    _attr_has_entity_name = True
    _attr_translation_key = "availability"

    def __init__(
        self,
        coordinator: PreComCoordinator,
        entry: PreComConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_availability"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="PreCom",
            manufacturer="PreCom",
            model="Cloud Alerting Service",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://portal.pre-com.nl",
        )

    @property
    def is_on(self) -> bool | None:
        """Return True when the user is available for alarm call-out."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.is_available

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return availability details as entity attributes."""
        if self.coordinator.data is None:
            return {}
        return {
            ATTR_NOT_AVAILABLE_TIMESTAMP: self.coordinator.data.not_available_timestamp,
            ATTR_NOT_AVAILABLE_SCHEDULED: self.coordinator.data.not_available_scheduled,
        }

    async def async_set_unavailable(self, hours: int) -> None:
        """Mark the user as unavailable/outside region for the given number of hours."""
        try:
            await self.coordinator.async_set_unavailable(hours)
        except PreComAuthError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="auth_failed",
            ) from err
        except PreComApiError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="action_failed",
            ) from err
        await self.coordinator.async_request_refresh()

    async def async_set_available(self) -> None:
        """Mark the user as available/back inside region."""
        try:
            await self.coordinator.async_set_available()
        except PreComAuthError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="auth_failed",
            ) from err
        except PreComApiError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="action_failed",
            ) from err
        await self.coordinator.async_request_refresh()
