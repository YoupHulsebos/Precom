"""The PreCom integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import PreComApiClient
from .const import (
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
)
from .coordinator import PreComCoordinator
from .htmlscraper import PreComHtmlScraper

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]

type PreComConfigEntry = ConfigEntry[PreComCoordinator]


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
    htmlscraper = PreComHtmlScraper(
        username=username, password=password, session=session
    )
    coordinator = PreComCoordinator(
        hass, entry, client, htmlscraper, scan_interval
    )

    # Raises ConfigEntryNotReady on failure; HA will retry with backoff.
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Reload the entry when options (e.g. scan_interval) are changed.
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def _async_update_listener(
    hass: HomeAssistant, entry: PreComConfigEntry
) -> None:
    """Reload the entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: PreComConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
