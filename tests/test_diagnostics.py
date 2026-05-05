"""Tests for PreCom diagnostics (diagnostics.py)."""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from homeassistant.const import CONF_PASSWORD
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.precom.const import DOMAIN
from custom_components.precom.coordinator import PreComCoordinator, PreComCoordinatorData
from custom_components.precom.diagnostics import async_get_config_entry_diagnostics

from .conftest import MOCK_PASSWORD, MOCK_USERNAME


def _make_entry_with_coordinator(
    hass: HomeAssistant,
    alarm_data: PreComCoordinatorData | None = None,
) -> MockConfigEntry:
    """Helper: create a config entry with a coordinator attached."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=MOCK_USERNAME,
        data={
            "username": MOCK_USERNAME,
            "password": MOCK_PASSWORD,
        },
        options={},
    )
    entry.add_to_hass(hass)

    coordinator = PreComCoordinator(hass, entry, AsyncMock(), 60)
    coordinator.data = alarm_data
    entry.runtime_data = coordinator
    return entry


# ---------------------------------------------------------------------------
# async_get_config_entry_diagnostics
# ---------------------------------------------------------------------------


async def test_diagnostics_redacts_password(hass: HomeAssistant) -> None:
    """Password is redacted in diagnostics output."""
    entry = _make_entry_with_coordinator(hass)

    result = await async_get_config_entry_diagnostics(hass, entry)

    assert result["entry_data"][CONF_PASSWORD] == "**REDACTED**"


async def test_diagnostics_includes_username(hass: HomeAssistant) -> None:
    """Username (non-sensitive) is present in entry_data."""
    entry = _make_entry_with_coordinator(hass)

    result = await async_get_config_entry_diagnostics(hass, entry)

    assert result["entry_data"]["username"] == MOCK_USERNAME


async def test_diagnostics_includes_coordinator_state(hass: HomeAssistant) -> None:
    """Coordinator last_update_success and update_interval are included."""
    entry = _make_entry_with_coordinator(hass)

    result = await async_get_config_entry_diagnostics(hass, entry)

    assert "coordinator" in result
    assert "last_update_success" in result["coordinator"]
    assert "update_interval_seconds" in result["coordinator"]
    assert result["coordinator"]["update_interval_seconds"] == 60.0


async def test_diagnostics_includes_alarm_data_when_present(
    hass: HomeAssistant,
) -> None:
    """last_alarm block is populated when coordinator has data."""
    alarm_data = PreComCoordinatorData(
        alarm_id="55555",
        functions=[{"label": "BW", "users": ["User A"]}],
        text="Big fire",
        timestamp="2024-01-15T10:30:00+00:00",
    )
    entry = _make_entry_with_coordinator(hass, alarm_data)

    result = await async_get_config_entry_diagnostics(hass, entry)

    last_alarm = result["coordinator"]["last_alarm"]
    assert last_alarm["alarm_id"] == "55555"
    assert last_alarm["text"] == "Big fire"
    assert last_alarm["timestamp"] == "2024-01-15T10:30:00+00:00"
    assert last_alarm["functions_count"] == 1


async def test_diagnostics_empty_alarm_when_no_data(hass: HomeAssistant) -> None:
    """last_alarm is an empty dict when coordinator.data is None."""
    entry = _make_entry_with_coordinator(hass, alarm_data=None)

    result = await async_get_config_entry_diagnostics(hass, entry)

    assert result["coordinator"]["last_alarm"] == {}


async def test_diagnostics_none_update_interval(hass: HomeAssistant) -> None:
    """update_interval_seconds is None when polling is disabled."""
    entry = _make_entry_with_coordinator(hass)
    entry.runtime_data.update_interval = None

    result = await async_get_config_entry_diagnostics(hass, entry)

    assert result["coordinator"]["update_interval_seconds"] is None
