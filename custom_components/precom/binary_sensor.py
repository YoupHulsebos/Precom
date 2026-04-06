"""PreCom binary sensor platform — user availability status."""
from __future__ import annotations

import logging
import voluptuous as vol
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
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
    ATTR_CURRENT_AVAILABLE,
    ATTR_CURRENT_UNAVAILABLE,
    ATTR_HOURS,
    ATTR_NOT_AVAILABLE_SCHEDULED,
    ATTR_NOT_AVAILABLE_TIMESTAMP,
    ATTR_NUMBER_NEEDED,
    ATTR_SHORTAGE,
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
    """Set up the PreCom binary sensors from a config entry."""
    coordinator = entry.runtime_data
    async_add_entities([PreComAvailabilitySensor(coordinator, entry)])

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

    # Dynamically add one binary sensor per unique function label.
    # A function may appear across multiple groups; sensors are merged by label.
    # Skip functions where NumberNeeded is 0 in all groups.
    # Use a seen-set to avoid adding duplicates on subsequent coordinator updates.
    _seen_labels: set[str] = set()

    def _add_understaffed_sensors() -> None:
        if coordinator.data is None:
            return

        # Collect all function labels regardless of NumberNeeded.
        all_labels: set[str] = set()
        for group in coordinator.data.user_groups:
            for func in group.get("ServiceFuntions", []):
                label = func.get("Label", "")
                if label:
                    all_labels.add(label)

        new_entities: list[BinarySensorEntity] = []
        for label in all_labels:
            if label not in _seen_labels:
                _seen_labels.add(label)
                new_entities.append(
                    PreComFunctionUnderstaffedSensor(coordinator, entry, label)
                )
        if new_entities:
            async_add_entities(new_entities)

    _add_understaffed_sensors()
    entry.async_on_unload(coordinator.async_add_listener(lambda: _add_understaffed_sensors()))


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


class PreComFunctionUnderstaffedSensor(CoordinatorEntity[PreComCoordinator], BinarySensorEntity):
    """Binary sensor that is 'on' (problem) when a function is understaffed.

    One sensor per unique function label, merged across all user groups.
    Only created when NumberNeeded > 0 in at least one group.

    State:    on  = any group has a shortfall in the next 24 hours (per DayTotals)
              off = all groups are sufficiently staffed for the next 24 hours
    Attributes:
        function_label  — name of the function (e.g. "Chauffeur")
        groups          — per-group breakdown: group_label, number_needed, current_count, shortage
    """

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(
        self,
        coordinator: PreComCoordinator,
        entry: PreComConfigEntry,
        func_label: str,
    ) -> None:
        super().__init__(coordinator)
        self._func_label = func_label
        self._attr_translation_key = "function_understaffed"
        self._attr_translation_placeholders = {"function": func_label}
        self._attr_unique_id = f"{entry.entry_id}_understaffed_{func_label}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="PreCom",
            manufacturer="PreCom",
            model="Cloud Alerting Service",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://portal.pre-com.nl",
        )

    def _matching_functions(self) -> list[tuple[dict, dict]]:
        """Return (group, func) pairs matching this label."""
        if self.coordinator.data is None:
            return []
        result = []
        for group in self.coordinator.data.user_groups:
            for func in group.get("ServiceFuntions", []):
                if func.get("Label", "") == self._func_label:
                    result.append((group, func))
        return result

    @staticmethod
    def _check_day_totals(day_totals: dict, number_needed: int) -> bool:
        """Return True if any 15-min slot in the next 24h has count < number_needed."""
        now = datetime.now()
        for quarter_offset in range(96):  # 24 hours × 4 quarter-slots
            check_dt = now + timedelta(minutes=15 * quarter_offset)
            date_key = check_dt.strftime("%Y-%m-%dT00:00:00")
            suffix = ("", "_15", "_30", "_45")[check_dt.minute // 15]
            slot_key = f"Hour{check_dt.hour}{suffix}"
            day_data = day_totals.get(date_key)
            if day_data is not None and day_data.get(slot_key, 0) < number_needed:
                return True
        return False

    @property
    def is_on(self) -> bool | None:
        """Return True when any group has a staffing shortfall in the next 24 hours."""
        matches = self._matching_functions()
        if not matches:
            return None
        for _group, func in matches:
            number_needed: int = func.get("NumberNeeded", 0)
            day_totals: dict = func.get("DayTotals", {})
            if day_totals:
                if self._check_day_totals(day_totals, number_needed):
                    return True
            else:
                # Fallback when DayTotals is absent: compare current Users count.
                if len(func.get("Users", [])) < number_needed:
                    return True
        return False

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return current staffing figures for the current 15-min slot."""
        matches = self._matching_functions()
        if not matches:
            return {}
        # Use the first matching function for scalar attribute values.
        _group, func = matches[0]
        number_needed: int = func.get("NumberNeeded", 0)
        now = datetime.now()
        date_key = now.strftime("%Y-%m-%dT00:00:00")
        suffix = ("", "_15", "_30", "_45")[now.minute // 15]
        slot_key = f"Hour{now.hour}{suffix}"
        day_totals: dict = func.get("DayTotals", {})
        current_available = day_totals.get(date_key, {}).get(slot_key, len(func.get("Users", [])))
        current_unavailable = sum(
            1 for u in func.get("Users", []) if u.get("NotAvailable", False)
        )
        shortage = max(0, number_needed - current_available)
        return {
            ATTR_NUMBER_NEEDED: number_needed,
            ATTR_CURRENT_AVAILABLE: current_available,
            ATTR_CURRENT_UNAVAILABLE: current_unavailable,
            ATTR_SHORTAGE: shortage,
        }
