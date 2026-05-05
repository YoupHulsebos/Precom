"""Tests for PreCom API client (api.py)."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

from custom_components.precom.api import (
    PreComApiClient,
    PreComApiError,
    PreComAuthError,
)

from .conftest import make_mock_response


def _client(session: MagicMock, token: str | None = None) -> PreComApiClient:
    """Helper: create a client with an optional pre-set token."""
    c = PreComApiClient("user@test.com", "password", session)
    if token is not None:
        c._token = token
    return c


def _session(post=None, get=None) -> MagicMock:
    """Helper: create a mock session with optional method overrides."""
    s = MagicMock()
    if post is not None:
        s.post = MagicMock(return_value=post)
    if get is not None:
        s.get = MagicMock(return_value=get)
    return s


# ---------------------------------------------------------------------------
# authenticate()
# ---------------------------------------------------------------------------


class TestAuthenticate:
    """Tests for PreComApiClient.authenticate()."""

    async def test_success_strips_surrounding_quotes(self) -> None:
        """Token returned as quoted JSON string has its quotes stripped."""
        session = _session(post=make_mock_response(200, text='"eyJtoken"'))
        client = _client(session)

        await client.authenticate()

        assert client._token == "eyJtoken"

    async def test_success_sets_token_without_outer_whitespace(self) -> None:
        """Leading/trailing whitespace around the quoted token is stripped."""
        session = _session(post=make_mock_response(200, text='  "mytoken"  '))
        client = _client(session)

        await client.authenticate()

        assert client._token == "mytoken"

    async def test_http_400_raises_auth_error(self) -> None:
        """HTTP 400 from token endpoint raises PreComAuthError."""
        session = _session(post=make_mock_response(400))
        client = _client(session)

        with pytest.raises(PreComAuthError):
            await client.authenticate()

    async def test_http_500_raises_api_error(self) -> None:
        """HTTP 5xx from token endpoint raises PreComApiError."""
        session = _session(post=make_mock_response(500))
        client = _client(session)

        with pytest.raises(PreComApiError):
            await client.authenticate()

    async def test_network_error_raises_api_error(self) -> None:
        """ClientError during authentication raises PreComApiError."""
        s = MagicMock()
        s.post = MagicMock(side_effect=aiohttp.ClientError("timeout"))
        client = _client(s)

        with pytest.raises(PreComApiError):
            await client.authenticate()


# ---------------------------------------------------------------------------
# get_alarm_messages()
# ---------------------------------------------------------------------------


class TestGetAlarmMessages:
    """Tests for PreComApiClient.get_alarm_messages()."""

    async def test_returns_list_of_alarms(self) -> None:
        """HTTP 200 with list returns the list as-is."""
        alarm_data = [{"MsgInID": "123", "Text": "Fire"}]
        auth_resp = make_mock_response(200, text='"tok"')
        get_resp = make_mock_response(200, json_data=alarm_data)
        s = MagicMock()
        s.post = MagicMock(return_value=auth_resp)
        s.get = MagicMock(return_value=get_resp)

        result = await _client(s).get_alarm_messages()

        assert result == alarm_data

    async def test_skips_auth_when_token_already_set(self) -> None:
        """Does not call authenticate when token is already present."""
        get_resp = make_mock_response(200, json_data=[])
        s = _session(get=get_resp)

        await _client(s, token="existing").get_alarm_messages()

        s.post.assert_not_called()

    async def test_auto_authenticates_when_token_is_none(self) -> None:
        """Calls authenticate automatically when _token is None."""
        s = MagicMock()
        s.post = MagicMock(return_value=make_mock_response(200, text='"tok"'))
        s.get = MagicMock(return_value=make_mock_response(200, json_data=[]))
        client = _client(s)  # token is None

        await client.get_alarm_messages()

        s.post.assert_called_once()  # authenticate was called

    async def test_returns_empty_list(self) -> None:
        """Returns empty list when no active alarms."""
        s = _session(get=make_mock_response(200, json_data=[]))

        result = await _client(s, token="tok").get_alarm_messages()

        assert result == []

    async def test_http_401_raises_auth_error(self) -> None:
        """HTTP 401 raises PreComAuthError."""
        s = _session(get=make_mock_response(401))

        with pytest.raises(PreComAuthError):
            await _client(s, token="stale").get_alarm_messages()

    async def test_http_500_raises_api_error(self) -> None:
        """HTTP 500 raises PreComApiError."""
        s = _session(get=make_mock_response(500))

        with pytest.raises(PreComApiError):
            await _client(s, token="tok").get_alarm_messages()

    async def test_non_list_response_raises_api_error(self) -> None:
        """Non-list JSON body raises PreComApiError."""
        s = _session(get=make_mock_response(200, json_data={"error": "unexpected"}))

        with pytest.raises(PreComApiError, match="Expected list"):
            await _client(s, token="tok").get_alarm_messages()

    async def test_network_error_raises_api_error(self) -> None:
        """ClientError while fetching alarms raises PreComApiError."""
        s = MagicMock()
        s.get = MagicMock(side_effect=aiohttp.ClientError("conn refused"))
        client = _client(s, token="tok")

        with pytest.raises(PreComApiError):
            await client.get_alarm_messages()


# ---------------------------------------------------------------------------
# set_outside_region()
# ---------------------------------------------------------------------------


class TestSetOutsideRegion:
    """Tests for PreComApiClient.set_outside_region()."""

    async def test_success_200(self) -> None:
        """HTTP 200 does not raise."""
        s = _session(post=make_mock_response(200))
        await _client(s, token="tok").set_outside_region(4)

    async def test_success_204(self) -> None:
        """HTTP 204 does not raise."""
        s = _session(post=make_mock_response(204))
        await _client(s, token="tok").set_outside_region(4)

    async def test_http_401_raises_auth_error(self) -> None:
        """HTTP 401 raises PreComAuthError."""
        s = _session(post=make_mock_response(401))

        with pytest.raises(PreComAuthError):
            await _client(s, token="stale").set_outside_region(4)

    async def test_http_500_raises_api_error(self) -> None:
        """HTTP 500 raises PreComApiError."""
        s = _session(post=make_mock_response(500))

        with pytest.raises(PreComApiError):
            await _client(s, token="tok").set_outside_region(4)

    async def test_network_error_raises_api_error(self) -> None:
        """ClientError raises PreComApiError."""
        s = MagicMock()
        s.post = MagicMock(side_effect=aiohttp.ClientError("net err"))

        with pytest.raises(PreComApiError):
            await _client(s, token="tok").set_outside_region(4)

    async def test_auto_authenticates_when_token_is_none(self) -> None:
        """Calls authenticate then set_outside_region when token is None."""
        auth_resp = make_mock_response(200, text='"tok"')
        set_resp = make_mock_response(200)
        s = MagicMock()
        s.post = MagicMock(side_effect=[auth_resp, set_resp])

        await _client(s).set_outside_region(4)

        assert s.post.call_count == 2


# ---------------------------------------------------------------------------
# set_in_region()
# ---------------------------------------------------------------------------


class TestSetInRegion:
    """Tests for PreComApiClient.set_in_region()."""

    async def test_success_200(self) -> None:
        """HTTP 200 does not raise."""
        s = _session(post=make_mock_response(200))
        await _client(s, token="tok").set_in_region()

    async def test_success_204(self) -> None:
        """HTTP 204 does not raise."""
        s = _session(post=make_mock_response(204))
        await _client(s, token="tok").set_in_region()

    async def test_http_401_raises_auth_error(self) -> None:
        """HTTP 401 raises PreComAuthError."""
        s = _session(post=make_mock_response(401))

        with pytest.raises(PreComAuthError):
            await _client(s, token="stale").set_in_region()

    async def test_http_500_raises_api_error(self) -> None:
        """HTTP 500 raises PreComApiError."""
        s = _session(post=make_mock_response(500))

        with pytest.raises(PreComApiError):
            await _client(s, token="tok").set_in_region()

    async def test_network_error_raises_api_error(self) -> None:
        """ClientError raises PreComApiError."""
        s = MagicMock()
        s.post = MagicMock(side_effect=aiohttp.ClientError("net err"))

        with pytest.raises(PreComApiError):
            await _client(s, token="tok").set_in_region()

    async def test_auto_authenticates_when_token_is_none(self) -> None:
        """Calls authenticate then set_in_region when token is None."""
        auth_resp = make_mock_response(200, text='"tok"')
        set_resp = make_mock_response(200)
        s = MagicMock()
        s.post = MagicMock(side_effect=[auth_resp, set_resp])

        await _client(s).set_in_region()

        assert s.post.call_count == 2
