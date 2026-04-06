"""The PreCom integration."""
from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import PreComApiClient, PreComApiError, PreComAuthError
from .const import (
    ATTR_HOURS,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    SERVICE_SET_IN_REGION,
    SERVICE_SET_OUTSIDE_REGION,
    SERVICE_UPDATE_ALARM,
)
from .coordinator import PreComCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

type PreComConfigEntry = ConfigEntry[PreComCoordinator]

SET_OUTSIDE_REGION_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_HOURS): vol.All(int, vol.Range(min=1, max=72)),
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: PreComConfigEntry) -> bool:
    """Set up PreCom from a config entry."""
    username: str = entry.data[CONF_USERNAME]
    password: str = entry.data[CONF_PASSWORD]
    scan_interval: int = (
        entry.options.get(CONF_SCAN_INTERVAL)
        or entry.data.get(CONF_SCAN_INTERVAL)
        or DEFAULT_SCAN_INTERVAL
    )

    session = async_get_clientsession(hass)
    client = PreComApiClient(username=username, password=password, session=session)
    coordinator = PreComCoordinator(hass, entry, client, scan_interval)

    # Raises ConfigEntryNotReady on failure; HA will retry with backoff.
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Reload the entry when options (e.g. scan_interval) are changed.
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    _register_services(hass)

    return True


async def _async_update_listener(
    hass: HomeAssistant, entry: PreComConfigEntry
) -> None:
    """Reload the entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: PreComConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        # Remove domain-level services only when the last entry is removed.
        remaining = hass.config_entries.async_entries(DOMAIN)
        if len(remaining) <= 1:
            hass.services.async_remove(DOMAIN, SERVICE_SET_OUTSIDE_REGION)
            hass.services.async_remove(DOMAIN, SERVICE_SET_IN_REGION)
            hass.services.async_remove(DOMAIN, SERVICE_UPDATE_ALARM)
    return unload_ok


def _get_coordinator(hass: HomeAssistant) -> PreComCoordinator:
    """Return the coordinator from the first active config entry."""
    for entry in hass.config_entries.async_entries(DOMAIN):
        if hasattr(entry, "runtime_data") and entry.runtime_data is not None:
            return entry.runtime_data
    raise HomeAssistantError(
        translation_domain=DOMAIN,
        translation_key="no_entry_loaded",
    )


def _register_services(hass: HomeAssistant) -> None:
    """Register PreCom services (idempotent — no-op if already registered)."""
    if hass.services.has_service(DOMAIN, SERVICE_SET_OUTSIDE_REGION):
        return

    async def handle_set_outside_region(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass)
        try:
            await coordinator.async_set_outside_region(call.data[ATTR_HOURS])
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

    async def handle_set_in_region(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass)
        try:
            await coordinator.async_set_in_region()
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

    async def handle_update_alarm(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass)
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
        schema=vol.Schema({}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_UPDATE_ALARM,
        handle_update_alarm,
        schema=vol.Schema({}),
    )
