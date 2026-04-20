"""Shared fixtures and helpers for PreCom tests."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.precom.const import (
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

pytest_plugins = "pytest_homeassistant_custom_component"

# ---------------------------------------------------------------------------
# Test constants
# ---------------------------------------------------------------------------
MOCK_USERNAME = "test@example.com"
MOCK_PASSWORD = "test_password"
MOCK_TOKEN = "eyJhbGciOiJSUzI1NiJ9.testtoken"

MOCK_ALARM = {
    "MsgInID": "12345",
    "Text": "Test alarm message",
    "Timestamp": "2024-01-15T10:30:00",
    "Group": {
        "ServiceFuntions": [
            {
                "Label": "Brandweer",
                "Users": [
                    {"FullName": "Jan Jansen"},
                    {"FullName": "Piet Pietersen"},
                ],
            }
        ]
    },
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom components for all tests."""
    yield


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a mock PreCom config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id=MOCK_USERNAME,
        data={
            "username": MOCK_USERNAME,
            "password": MOCK_PASSWORD,
            CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
        },
        options={},
    )


def make_client_mock(alarms: list | None = None) -> AsyncMock:
    """Return a pre-configured mock PreComApiClient."""
    client = AsyncMock()
    client.authenticate = AsyncMock()
    client.get_alarm_messages = AsyncMock(
        return_value=alarms if alarms is not None else [MOCK_ALARM]
    )
    client.set_outside_region = AsyncMock()
    client.set_in_region = AsyncMock()
    return client


def make_mock_response(
    status: int,
    text: str = "",
    json_data: object = None,
) -> MagicMock:
    """Create a mock aiohttp response context manager."""
    response = MagicMock()
    response.status = status
    response.text = AsyncMock(return_value=text)
    response.json = AsyncMock(return_value=json_data)
    response.__aenter__ = AsyncMock(return_value=response)
    response.__aexit__ = AsyncMock(return_value=None)
    return response
