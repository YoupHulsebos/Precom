"""Tests for PreCom integration setup (__init__.py)."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.precom.api import PreComApiError, PreComAuthError
from custom_components.precom.const import (
    ATTR_HOURS,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    SERVICE_SET_IN_REGION,
    SERVICE_SET_OUTSIDE_REGION,
    SERVICE_UPDATE_ALARM,
)

from .conftest import make_client_mock

_PATCH_CLIENT = "custom_components.precom.PreComApiClient"


async def _setup(hass: HomeAssistant, entry: MockConfigEntry, client=None) -> AsyncMock:
    """Set up the PreCom integration with a mock client. Returns the client."""
    mock_client = client or make_client_mock()
    with patch(_PATCH_CLIENT, return_value=mock_client):
        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return mock_client


# ---------------------------------------------------------------------------
# async_setup_entry
# ---------------------------------------------------------------------------


async def test_setup_entry_loads_successfully(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """async_setup_entry returns True and state is LOADED."""
    await _setup(hass, mock_config_entry)

    assert mock_config_entry.state == ConfigEntryState.LOADED


async def test_setup_entry_stores_coordinator_in_runtime_data(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Coordinator is stored in entry.runtime_data after setup."""
    from custom_components.precom.coordinator import PreComCoordinator

    await _setup(hass, mock_config_entry)

    assert isinstance(mock_config_entry.runtime_data, PreComCoordinator)


async def test_setup_entry_registers_services(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """All three domain services are registered after setup."""
    await _setup(hass, mock_config_entry)

    assert hass.services.has_service(DOMAIN, SERVICE_SET_OUTSIDE_REGION)
    assert hass.services.has_service(DOMAIN, SERVICE_SET_IN_REGION)
    assert hass.services.has_service(DOMAIN, SERVICE_UPDATE_ALARM)


async def test_setup_entry_uses_options_scan_interval(
    hass: HomeAssistant,
) -> None:
    """scan_interval from options takes precedence over entry data."""
    from custom_components.precom.coordinator import PreComCoordinator
    from datetime import timedelta

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="opt_user@test.com",
        data={"username": "opt_user@test.com", "password": "pass", CONF_SCAN_INTERVAL: 60},
        options={CONF_SCAN_INTERVAL: 180},
    )
    await _setup(hass, entry)

    coordinator: PreComCoordinator = entry.runtime_data
    assert coordinator.update_interval == timedelta(seconds=180)


async def test_setup_entry_uses_default_scan_interval(
    hass: HomeAssistant,
) -> None:
    """DEFAULT_SCAN_INTERVAL is used when none is configured."""
    from custom_components.precom.coordinator import PreComCoordinator
    from datetime import timedelta

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="def_user@test.com",
        data={"username": "def_user@test.com", "password": "pass"},
        options={},
    )
    await _setup(hass, entry)

    coordinator: PreComCoordinator = entry.runtime_data
    assert coordinator.update_interval == timedelta(seconds=DEFAULT_SCAN_INTERVAL)


async def test_setup_entry_raises_not_ready_on_api_error(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """API error during first refresh sets state to SETUP_RETRY."""
    failing_client = make_client_mock()
    failing_client.get_alarm_messages = AsyncMock(side_effect=PreComApiError("down"))

    with patch(_PATCH_CLIENT, return_value=failing_client):
        mock_config_entry.add_to_hass(hass)
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert mock_config_entry.state == ConfigEntryState.SETUP_RETRY


async def test_register_services_is_idempotent(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Calling _register_services twice does not duplicate registrations."""
    from custom_components.precom import _register_services

    await _setup(hass, mock_config_entry)

    # Call again — should be a no-op
    _register_services(hass)

    assert hass.services.has_service(DOMAIN, SERVICE_SET_OUTSIDE_REGION)


# ---------------------------------------------------------------------------
# async_unload_entry
# ---------------------------------------------------------------------------


async def test_unload_entry_removes_services_when_last_entry(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Services are removed when the last entry is unloaded."""
    await _setup(hass, mock_config_entry)

    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state == ConfigEntryState.NOT_LOADED
    assert not hass.services.has_service(DOMAIN, SERVICE_SET_OUTSIDE_REGION)
    assert not hass.services.has_service(DOMAIN, SERVICE_SET_IN_REGION)
    assert not hass.services.has_service(DOMAIN, SERVICE_UPDATE_ALARM)


async def test_unload_entry_keeps_services_when_another_entry_remains(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Services are kept when a second entry is still loaded."""
    second_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="second@test.com",
        data={"username": "second@test.com", "password": "pass2"},
        options={},
    )

    await _setup(hass, mock_config_entry)
    await _setup(hass, second_entry)

    # Unload only the first entry
    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Services should still be registered (second entry is live)
    assert hass.services.has_service(DOMAIN, SERVICE_SET_OUTSIDE_REGION)


# ---------------------------------------------------------------------------
# Options update listener
# ---------------------------------------------------------------------------


async def test_options_update_triggers_reload(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Updating options triggers a reload of the config entry."""
    with patch(_PATCH_CLIENT, return_value=make_client_mock()):
        mock_config_entry.add_to_hass(hass)
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        assert mock_config_entry.state == ConfigEntryState.LOADED

        # Change the scan interval — the update listener should trigger reload
        hass.config_entries.async_update_entry(
            mock_config_entry, options={CONF_SCAN_INTERVAL: 120}
        )
        await hass.async_block_till_done()

    assert mock_config_entry.state == ConfigEntryState.LOADED


# ---------------------------------------------------------------------------
# Service handlers
# ---------------------------------------------------------------------------


async def test_service_set_outside_region_calls_coordinator(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """set_outside_region service calls coordinator.async_set_outside_region."""
    mock_client = await _setup(hass, mock_config_entry)

    await hass.services.async_call(
        DOMAIN, SERVICE_SET_OUTSIDE_REGION, {ATTR_HOURS: 6}, blocking=True
    )

    mock_client.set_outside_region.assert_called_once_with(6)


async def test_service_set_in_region_calls_coordinator(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """set_in_region service calls coordinator.async_set_in_region."""
    mock_client = await _setup(hass, mock_config_entry)

    await hass.services.async_call(
        DOMAIN, SERVICE_SET_IN_REGION, {}, blocking=True
    )

    mock_client.set_in_region.assert_called_once()


async def test_service_update_alarm_triggers_refresh(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """update_alarm service triggers async_request_refresh on coordinator."""
    await _setup(hass, mock_config_entry)
    coordinator = mock_config_entry.runtime_data
    coordinator.async_request_refresh = AsyncMock()

    await hass.services.async_call(
        DOMAIN, SERVICE_UPDATE_ALARM, {}, blocking=True
    )

    coordinator.async_request_refresh.assert_called_once()


async def test_service_set_outside_region_raises_on_api_error(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """PreComApiError from coordinator raises HomeAssistantError."""
    await _setup(hass, mock_config_entry)
    coordinator = mock_config_entry.runtime_data
    coordinator.async_set_outside_region = AsyncMock(
        side_effect=PreComApiError("API down")
    )

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            DOMAIN, SERVICE_SET_OUTSIDE_REGION, {ATTR_HOURS: 4}, blocking=True
        )


async def test_service_set_outside_region_raises_on_auth_error(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """PreComAuthError from coordinator raises HomeAssistantError."""
    await _setup(hass, mock_config_entry)
    coordinator = mock_config_entry.runtime_data
    coordinator.async_set_outside_region = AsyncMock(
        side_effect=PreComAuthError("unauthorized")
    )

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            DOMAIN, SERVICE_SET_OUTSIDE_REGION, {ATTR_HOURS: 4}, blocking=True
        )


async def test_service_set_in_region_raises_on_api_error(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """PreComApiError from coordinator raises HomeAssistantError."""
    await _setup(hass, mock_config_entry)
    coordinator = mock_config_entry.runtime_data
    coordinator.async_set_in_region = AsyncMock(
        side_effect=PreComApiError("API down")
    )

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            DOMAIN, SERVICE_SET_IN_REGION, {}, blocking=True
        )


async def test_service_set_in_region_raises_on_auth_error(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """PreComAuthError from coordinator raises HomeAssistantError."""
    await _setup(hass, mock_config_entry)
    coordinator = mock_config_entry.runtime_data
    coordinator.async_set_in_region = AsyncMock(
        side_effect=PreComAuthError("unauthorized")
    )

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            DOMAIN, SERVICE_SET_IN_REGION, {}, blocking=True
        )


# ---------------------------------------------------------------------------
# _get_coordinator
# ---------------------------------------------------------------------------


async def test_get_coordinator_raises_when_no_entries(hass: HomeAssistant) -> None:
    """_get_coordinator raises HomeAssistantError when no domain entries exist."""
    from custom_components.precom import _get_coordinator

    with pytest.raises(HomeAssistantError):
        _get_coordinator(hass)
