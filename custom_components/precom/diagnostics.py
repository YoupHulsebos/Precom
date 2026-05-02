"""Diagnostics support for PreCom."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_PASSWORD
from homeassistant.core import HomeAssistant

if TYPE_CHECKING:
    from . import PreComConfigEntry

TO_REDACT = [CONF_PASSWORD]


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: PreComConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a PreCom config entry."""
    coordinator = entry.runtime_data

    data = coordinator.data
    alarm_data: dict[str, Any] = {}
    availability_data: dict[str, Any] = {}
    if data is not None:
        alarm_data = {
            "alarm_id": data.alarm_id,
            "text": data.text,
            "timestamp": data.timestamp,
            "functions_count": len(data.functions),
            "response_data_count": len(data.response_data),
            "benodigd_count": len(data.benodigd),
            "voorgestelde_functies_count": len(data.voorgestelde_functies),
        }
        availability_data = {
            "is_available": data.is_available,
            "not_available_timestamp": data.not_available_timestamp,
            "not_available_scheduled": data.not_available_scheduled,
        }

    return {
        "entry_data": async_redact_data(dict(entry.data), TO_REDACT),
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "update_interval_seconds": (
                coordinator.update_interval.total_seconds()
                if coordinator.update_interval
                else None
            ),
            "last_alarm": alarm_data,
            "availability": availability_data,
        },
    }
