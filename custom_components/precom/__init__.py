"""The PreCom integration."""
from __future__ import annotations

import logging

import voluptuous as vol
import homeassistant.helpers.config_validation as cv

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import PreComApiClient
from .const import (
    ATTR_HOURS,
    CONF_SCAN_INTERVAL,
    DOMAIN,
    SERVICE_SET_IN_REGION,
    SERVICE_SET_OUTSIDE_REGION,
    SERVICE_UPDATE_ALARM,
)
from .coordinator import PreComCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

SET_OUTSIDE_REGION_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_HOURS): vol.All(int, vol.Range(min=1, max=72)),
    }
)
SET_IN_REGION_SCHEMA = vol.Schema({})


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up PreCom from a config entry."""
    username: str = entry.data[CONF_USERNAME]
    password: str = entry.data[CONF_PASSWORD]
    scan_interval: int | None = entry.data.get(CONF_SCAN_INTERVAL)

    session = async_get_clientsession(hass)
    client = PreComApiClient(username=username, password=password, session=session)
    coordinator = PreComCoordinator(hass, client, scan_interval)

    # Raises ConfigEntryNotReady on failure; HA will retry with backoff
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _register_services(hass, coordinator)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        # Remove domain services only when the last entry is removed
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, SERVICE_SET_OUTSIDE_REGION)
            hass.services.async_remove(DOMAIN, SERVICE_SET_IN_REGION)
            hass.services.async_remove(DOMAIN, SERVICE_UPDATE_ALARM)
    return unload_ok


def _register_services(hass: HomeAssistant, coordinator: PreComCoordinator) -> None:
    """Register precom services."""

    async def handle_set_outside_region(call: ServiceCall) -> None:
        hours: int = call.data[ATTR_HOURS]
        await coordinator.async_set_outside_region(hours)

    async def handle_set_in_region(call: ServiceCall) -> None:
        await coordinator.async_set_in_region()

    async def handle_update_alarm(call: ServiceCall) -> None:
        await coordinator.async_request_refresh()

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_OUTSIDE_REGION,
        handle_set_outside_region,
        schema=SET_OUTSIDE_REGION_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_IN_REGION,
        handle_set_in_region,
        schema=SET_IN_REGION_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_UPDATE_ALARM,
        handle_update_alarm,
        schema=vol.Schema({}),
    )
