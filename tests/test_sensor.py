"""Tests for PreCom sensor entity (sensor.py)."""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.precom.const import (
    ATTR_ALARM_ID,
    ATTR_FUNCTIONS,
    ATTR_FUNCTIONS_FORMATTED,
    ATTR_LAST_UPDATED,
    ATTR_TEXT,
    ATTR_TIMESTAMP,
    DOMAIN,
    STATE_NO_ALARM,
)
from custom_components.precom.coordinator import PreComCoordinator, PreComCoordinatorData
from custom_components.precom.sensor import PreComLastAlarmSensor

from .conftest import MOCK_USERNAME, MOCK_PASSWORD


def _make_entry(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=MOCK_USERNAME,
        data={"username": MOCK_USERNAME, "password": MOCK_PASSWORD},
        options={},
    )
    entry.add_to_hass(hass)
    return entry


def _make_sensor(
    hass: HomeAssistant,
    data: PreComCoordinatorData | None = None,
) -> tuple[PreComLastAlarmSensor, MockConfigEntry]:
    entry = _make_entry(hass)
    coordinator = PreComCoordinator(hass, entry, AsyncMock(), 60)
    coordinator.data = data
    sensor = PreComLastAlarmSensor(coordinator, entry)
    return sensor, entry


# ---------------------------------------------------------------------------
# native_value
# ---------------------------------------------------------------------------


async def test_native_value_returns_alarm_id_when_data_present(
    hass: HomeAssistant,
) -> None:
    """native_value returns the alarm_id from coordinator data."""
    data = PreComCoordinatorData(
        alarm_id="99999", functions=[], text="Test", timestamp=""
    )
    sensor, _ = _make_sensor(hass, data)

    assert sensor.native_value == "99999"


async def test_native_value_returns_none_when_no_data(hass: HomeAssistant) -> None:
    """native_value returns STATE_NO_ALARM when coordinator.data is None."""
    sensor, _ = _make_sensor(hass, data=None)

    assert sensor.native_value == STATE_NO_ALARM


async def test_native_value_returns_state_no_alarm_constant(
    hass: HomeAssistant,
) -> None:
    """native_value returns exactly STATE_NO_ALARM, not an arbitrary string."""
    sensor, _ = _make_sensor(hass, data=None)

    assert sensor.native_value == "none"


# ---------------------------------------------------------------------------
# extra_state_attributes
# ---------------------------------------------------------------------------


async def test_extra_state_attributes_returns_empty_when_no_data(
    hass: HomeAssistant,
) -> None:
    """extra_state_attributes is empty dict when coordinator.data is None."""
    sensor, _ = _make_sensor(hass, data=None)

    assert sensor.extra_state_attributes == {}


async def test_extra_state_attributes_contains_all_keys(
    hass: HomeAssistant,
) -> None:
    """extra_state_attributes contains all expected attribute keys."""
    data = PreComCoordinatorData(
        alarm_id="123",
        functions=[{"label": "BW", "users": ["Jan"]}],
        text="Fire!",
        timestamp="2024-01-15T10:30:00+00:00",
    )
    sensor, _ = _make_sensor(hass, data)

    attrs = sensor.extra_state_attributes

    assert attrs[ATTR_ALARM_ID] == "123"
    assert attrs[ATTR_TEXT] == "Fire!"
    assert attrs[ATTR_TIMESTAMP] == "2024-01-15T10:30:00+00:00"
    assert attrs[ATTR_FUNCTIONS] == [{"label": "BW", "users": ["Jan"]}]
    assert ATTR_FUNCTIONS_FORMATTED in attrs
    assert ATTR_LAST_UPDATED in attrs


# ---------------------------------------------------------------------------
# _format_functions
# ---------------------------------------------------------------------------


def test_format_functions_with_users() -> None:
    """_format_functions produces a readable block per function."""
    functions = [
        {"label": "Brandweer", "users": ["Jan Jansen", "Piet Pietersen"]},
    ]
    result = PreComLastAlarmSensor._format_functions(functions)

    assert "Brandweer (2):" in result
    assert "- Jan Jansen" in result
    assert "- Piet Pietersen" in result


def test_format_functions_empty_list() -> None:
    """_format_functions returns empty string for empty list."""
    result = PreComLastAlarmSensor._format_functions([])

    assert result == ""


def test_format_functions_multiple_groups_separated_by_blank_line() -> None:
    """Multiple functions are separated by double newline."""
    functions = [
        {"label": "Group A", "users": ["User 1"]},
        {"label": "Group B", "users": ["User 2"]},
    ]
    result = PreComLastAlarmSensor._format_functions(functions)

    assert "Group A (1):" in result
    assert "Group B (1):" in result
    assert "\n\n" in result


def test_format_functions_no_users() -> None:
    """Function with empty users list renders with count 0."""
    functions = [{"label": "Leeg", "users": []}]
    result = PreComLastAlarmSensor._format_functions(functions)

    assert "Leeg (0):" in result


# ---------------------------------------------------------------------------
# Entity properties
# ---------------------------------------------------------------------------


async def test_unique_id_uses_entry_id(hass: HomeAssistant) -> None:
    """unique_id is constructed from entry_id."""
    sensor, entry = _make_sensor(hass)

    assert sensor.unique_id == f"{entry.entry_id}_last_alarm"


async def test_has_entity_name_is_true(hass: HomeAssistant) -> None:
    """has_entity_name is True for proper entity naming."""
    sensor, _ = _make_sensor(hass)

    assert sensor.has_entity_name is True


async def test_translation_key_is_set(hass: HomeAssistant) -> None:
    """translation_key is 'last_alarm' for entity translation."""
    sensor, _ = _make_sensor(hass)

    assert sensor.translation_key == "last_alarm"


async def test_device_info_uses_service_entry_type(hass: HomeAssistant) -> None:
    """device_info uses DeviceEntryType.SERVICE."""
    from homeassistant.helpers.device_registry import DeviceEntryType

    sensor, _ = _make_sensor(hass)

    assert sensor.device_info["entry_type"] == DeviceEntryType.SERVICE


async def test_parallel_updates_is_zero() -> None:
    """PARALLEL_UPDATES is 0 as coordinator handles all updates."""
    from custom_components.precom import sensor as sensor_module

    assert sensor_module.PARALLEL_UPDATES == 0
