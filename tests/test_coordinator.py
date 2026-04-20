"""Tests for PreComCoordinator (coordinator.py)."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.precom.api import PreComApiError, PreComAuthError
from custom_components.precom.const import DEFAULT_SCAN_INTERVAL, DOMAIN, STATE_NO_ALARM
from custom_components.precom.coordinator import PreComCoordinator, PreComCoordinatorData

from .conftest import MOCK_ALARM, MOCK_USERNAME, MOCK_PASSWORD, make_client_mock


def _make_coordinator(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    client: AsyncMock | None = None,
    scan_interval: int = DEFAULT_SCAN_INTERVAL,
) -> PreComCoordinator:
    if client is None:
        client = make_client_mock()
    return PreComCoordinator(hass, entry, client, scan_interval)


# ---------------------------------------------------------------------------
# Normal update path
# ---------------------------------------------------------------------------


async def test_update_returns_alarm_data(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """_async_update_data parses alarm correctly from API response."""
    mock_config_entry.add_to_hass(hass)
    coordinator = _make_coordinator(hass, mock_config_entry)

    data = await coordinator._async_update_data()

    assert data.alarm_id == "12345"
    assert data.text == "Test alarm message"
    assert len(data.functions) == 1
    assert data.functions[0]["label"] == "Brandweer"
    assert data.functions[0]["users"] == ["Jan Jansen", "Piet Pietersen"]


async def test_update_returns_no_alarm_on_empty_list(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Empty alarm list yields STATE_NO_ALARM data."""
    mock_config_entry.add_to_hass(hass)
    client = make_client_mock(alarms=[])
    coordinator = _make_coordinator(hass, mock_config_entry, client)

    data = await coordinator._async_update_data()

    assert data.alarm_id == STATE_NO_ALARM
    assert data.functions == []
    assert data.text == ""


async def test_update_marks_available_on_recovery(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """After an unavailable period, _mark_available is called on success."""
    mock_config_entry.add_to_hass(hass)
    client = make_client_mock(alarms=[])
    coordinator = _make_coordinator(hass, mock_config_entry, client)
    coordinator._unavailable = True  # Simulate prior failure

    await coordinator._async_update_data()

    assert coordinator._unavailable is False


async def test_mark_available_no_op_when_already_available(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """_mark_available does not log when already available."""
    mock_config_entry.add_to_hass(hass)
    coordinator = _make_coordinator(hass, mock_config_entry)
    coordinator._unavailable = False

    coordinator._mark_available()  # Must not raise or log

    assert coordinator._unavailable is False


async def test_mark_unavailable_only_logs_first_time(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """_mark_unavailable only sets the flag (and would log) on first call."""
    mock_config_entry.add_to_hass(hass)
    coordinator = _make_coordinator(hass, mock_config_entry)

    coordinator._mark_unavailable("reason one")
    assert coordinator._unavailable is True

    # Second call must not change state or raise
    coordinator._mark_unavailable("reason two")
    assert coordinator._unavailable is True


# ---------------------------------------------------------------------------
# Timestamp parsing
# ---------------------------------------------------------------------------


async def test_timestamp_with_no_timezone_gets_utc(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """ISO timestamp without tz info is assumed UTC."""
    mock_config_entry.add_to_hass(hass)
    alarm = {**MOCK_ALARM, "Timestamp": "2024-01-15T10:30:00"}
    client = make_client_mock(alarms=[alarm])
    coordinator = _make_coordinator(hass, mock_config_entry, client)

    data = await coordinator._async_update_data()

    assert "+00:00" in data.timestamp


async def test_timestamp_with_timezone_preserved(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """ISO timestamp with timezone info is preserved as-is."""
    mock_config_entry.add_to_hass(hass)
    alarm = {**MOCK_ALARM, "Timestamp": "2024-01-15T10:30:00+01:00"}
    client = make_client_mock(alarms=[alarm])
    coordinator = _make_coordinator(hass, mock_config_entry, client)

    data = await coordinator._async_update_data()

    assert "+01:00" in data.timestamp


async def test_invalid_timestamp_stored_as_string(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Unparseable timestamp is stored as the raw string."""
    mock_config_entry.add_to_hass(hass)
    alarm = {**MOCK_ALARM, "Timestamp": "not-a-date"}
    client = make_client_mock(alarms=[alarm])
    coordinator = _make_coordinator(hass, mock_config_entry, client)

    data = await coordinator._async_update_data()

    assert data.timestamp == "not-a-date"


async def test_empty_timestamp_stored_as_empty_string(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Missing Timestamp field results in empty string."""
    mock_config_entry.add_to_hass(hass)
    alarm = {**MOCK_ALARM, "Timestamp": ""}
    client = make_client_mock(alarms=[alarm])
    coordinator = _make_coordinator(hass, mock_config_entry, client)

    data = await coordinator._async_update_data()

    assert data.timestamp == ""


# ---------------------------------------------------------------------------
# Token-refresh retry in _fetch_alarms
# ---------------------------------------------------------------------------


async def test_fetch_alarms_refreshes_token_on_first_auth_error(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """On first PreComAuthError the coordinator re-authenticates and retries."""
    mock_config_entry.add_to_hass(hass)
    client = AsyncMock()
    client.get_alarm_messages = AsyncMock(
        side_effect=[PreComAuthError("rejected"), [MOCK_ALARM]]
    )
    client.authenticate = AsyncMock()
    coordinator = _make_coordinator(hass, mock_config_entry, client)

    data = await coordinator._async_update_data()

    client.authenticate.assert_called_once()
    assert data.alarm_id == "12345"


# ---------------------------------------------------------------------------
# Persistent failure paths
# ---------------------------------------------------------------------------


async def test_persistent_auth_error_raises_update_failed(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Persistent PreComAuthError raises UpdateFailed and triggers reauth."""
    mock_config_entry.add_to_hass(hass)
    client = AsyncMock()
    # Both calls raise auth error
    client.get_alarm_messages = AsyncMock(side_effect=PreComAuthError("bad creds"))
    client.authenticate = AsyncMock()
    coordinator = _make_coordinator(hass, mock_config_entry, client)

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()

    assert coordinator._unavailable is True


async def test_api_error_raises_update_failed(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """PreComApiError from get_alarm_messages raises UpdateFailed."""
    mock_config_entry.add_to_hass(hass)
    client = make_client_mock()
    client.get_alarm_messages = AsyncMock(side_effect=PreComApiError("server down"))
    coordinator = _make_coordinator(hass, mock_config_entry, client)

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()

    assert coordinator._unavailable is True


async def test_api_error_after_reauth_raises_update_failed(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """PreComApiError on retry after re-auth raises UpdateFailed."""
    mock_config_entry.add_to_hass(hass)
    client = AsyncMock()
    client.get_alarm_messages = AsyncMock(
        side_effect=[PreComAuthError("token"), PreComApiError("api down")]
    )
    client.authenticate = AsyncMock()
    coordinator = _make_coordinator(hass, mock_config_entry, client)

    # _fetch_alarms raises PreComApiError which propagates to _async_update_data
    # which catches it as PreComApiError
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


# ---------------------------------------------------------------------------
# async_set_outside_region / async_set_in_region
# ---------------------------------------------------------------------------


async def test_async_set_outside_region_success(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """async_set_outside_region calls client method with hours."""
    mock_config_entry.add_to_hass(hass)
    client = make_client_mock()
    coordinator = _make_coordinator(hass, mock_config_entry, client)

    await coordinator.async_set_outside_region(8)

    client.set_outside_region.assert_called_once_with(8)


async def test_async_set_outside_region_retries_on_auth_error(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """async_set_outside_region re-authenticates once on PreComAuthError."""
    mock_config_entry.add_to_hass(hass)
    client = AsyncMock()
    client.set_outside_region = AsyncMock(
        side_effect=[PreComAuthError("expired"), None]
    )
    client.authenticate = AsyncMock()
    coordinator = _make_coordinator(hass, mock_config_entry, client)

    await coordinator.async_set_outside_region(4)

    client.authenticate.assert_called_once()
    assert client.set_outside_region.call_count == 2


async def test_async_set_in_region_success(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """async_set_in_region calls client method."""
    mock_config_entry.add_to_hass(hass)
    client = make_client_mock()
    coordinator = _make_coordinator(hass, mock_config_entry, client)

    await coordinator.async_set_in_region()

    client.set_in_region.assert_called_once()


async def test_async_set_in_region_retries_on_auth_error(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """async_set_in_region re-authenticates once on PreComAuthError."""
    mock_config_entry.add_to_hass(hass)
    client = AsyncMock()
    client.set_in_region = AsyncMock(side_effect=[PreComAuthError("expired"), None])
    client.authenticate = AsyncMock()
    coordinator = _make_coordinator(hass, mock_config_entry, client)

    await coordinator.async_set_in_region()

    client.authenticate.assert_called_once()
    assert client.set_in_region.call_count == 2


# ---------------------------------------------------------------------------
# scan_interval=None disables polling
# ---------------------------------------------------------------------------


async def test_no_scan_interval_disables_polling(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """When scan_interval is None the coordinator has no update_interval."""
    mock_config_entry.add_to_hass(hass)
    coordinator = _make_coordinator(hass, mock_config_entry, scan_interval=None)  # type: ignore[arg-type]

    assert coordinator.update_interval is None
