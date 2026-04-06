"""Async API client for the PreCom fire department alerting service."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp

from .const import (
    API_ALARMS_URL,
    API_GROUPS_URL,
    API_SET_OUTSIDE_REGION_URL,
    API_TOKEN_URL,
    API_GROUP_FUNCTIONS_URL,
    API_USER_GROUPS_URL,
    API_USER_INFO_URL,
)

_LOGGER = logging.getLogger(__name__)


class PreComAuthError(Exception):
    """Raised when authentication fails (bad credentials or 401)."""


class PreComApiError(Exception):
    """Raised for non-auth API errors (network, 5xx, unexpected response)."""


class PreComApiClient:
    """All HTTP communication with app.pre-com.nl.

    Token lifecycle:
      - _token is None on first use; authenticate() is called automatically.
      - On any 401, the caller (coordinator) should call authenticate() then retry.
      - authenticate() raises PreComAuthError on bad credentials.
    """

    def __init__(
        self,
        username: str,
        password: str,
        session: aiohttp.ClientSession,
    ) -> None:
        self._username = username
        self._password = password
        self._session = session
        self._token: str | None = None

    async def authenticate(self) -> None:
        """Fetch a fresh JWT token and store it internally.

        The PreCom API returns the token as a quoted JSON string (e.g. '"eyJ..."').
        We strip the surrounding quotes to get the raw token, mirroring the
        Jinja2 '| trim | trim('"')' logic in the original precom_token.yaml script.

        Raises:
            PreComAuthError: credentials rejected or unexpected response format.
            PreComApiError: network-level failure.
        """
        payload = (
            f"grant_type=password"
            f"&username={self._username}"
            f"&password={self._password}"
        )
        try:
            async with self._session.post(
                API_TOKEN_URL,
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=aiohttp.ClientTimeout(total=15),
            ) as response:
                if response.status == 400:
                    raise PreComAuthError(
                        f"Authentication failed (HTTP {response.status})"
                    )
                if response.status != 200:
                    raise PreComApiError(
                        f"Token endpoint returned HTTP {response.status}"
                    )
                raw = await response.text()
                self._token = raw.strip().strip('"')
        except aiohttp.ClientError as err:
            raise PreComApiError(f"Network error during authentication: {err}") from err

    def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token}"}

    async def get_alarm_messages(self) -> list[dict[str, Any]]:
        """Fetch the list of active alarm messages.

        Returns an empty list when there are no active alarms.

        Raises:
            PreComAuthError: token was rejected (401).
            PreComApiError: any other HTTP or network failure.
        """
        if self._token is None:
            await self.authenticate()

        try:
            async with self._session.get(
                API_ALARMS_URL,
                headers=self._auth_headers(),
                timeout=aiohttp.ClientTimeout(total=15),
            ) as response:
                if response.status == 401:
                    raise PreComAuthError("Token rejected by alarms endpoint (401)")
                if response.status != 200:
                    raise PreComApiError(
                        f"GetAlarmMessages returned HTTP {response.status}"
                    )
                data = await response.json(content_type=None)
                if not isinstance(data, list):
                    raise PreComApiError(
                        f"Expected list from GetAlarmMessages, got {type(data)}"
                    )
                return data
        except aiohttp.ClientError as err:
            raise PreComApiError(
                f"Network error fetching alarm messages: {err}"
            ) from err

    async def get_user_info(self) -> dict:
        """Fetch user information including availability status.

        Returns a dict with at minimum 'NotAvailable' (bool),
        'NotAvailableTimestamp' (str|None), and 'NotAvailalbeScheduled' (bool).

        Raises:
            PreComAuthError: token rejected.
            PreComApiError: other failure.
        """
        if self._token is None:
            await self.authenticate()

        try:
            async with self._session.get(
                API_USER_INFO_URL,
                headers=self._auth_headers(),
                timeout=aiohttp.ClientTimeout(total=15),
            ) as response:
                if response.status == 401:
                    raise PreComAuthError("Token rejected by GetUserInfo (401)")
                if response.status != 200:
                    raise PreComApiError(
                        f"GetUserInfo returned HTTP {response.status}"
                    )
                data = await response.json(content_type=None)
                if not isinstance(data, dict):
                    raise PreComApiError(
                        f"Expected dict from GetUserInfo, got {type(data)}"
                    )
                return data
        except aiohttp.ClientError as err:
            raise PreComApiError(
                f"Network error fetching user info: {err}"
            ) from err

    async def get_all_groups(self) -> list[dict[str, Any]]:
        """Fetch all groups the user belongs to.

        Returns a list of group dicts from the PreCom API.

        Raises:
            PreComAuthError: token rejected.
            PreComApiError: other failure.
        """
        if self._token is None:
            await self.authenticate()

        try:
            async with self._session.get(
                API_GROUPS_URL,
                headers=self._auth_headers(),
                timeout=aiohttp.ClientTimeout(total=15),
            ) as response:
                if response.status == 401:
                    raise PreComAuthError("Token rejected by GetAllGroups (401)")
                if response.status != 200:
                    raise PreComApiError(
                        f"GetAllGroups returned HTTP {response.status}"
                    )
                data = await response.json(content_type=None)
                if not isinstance(data, list):
                    raise PreComApiError(
                        f"Expected list from GetAllGroups, got {type(data)}"
                    )
                return data
        except aiohttp.ClientError as err:
            raise PreComApiError(
                f"Network error fetching groups: {err}"
            ) from err

    async def get_all_user_groups(self) -> list[dict[str, Any]]:
        """Fetch the groups to which the current user belongs today.

        Note: The returned group dicts have empty ServiceFuntions arrays.
        Use get_group_functions() per group to obtain staffing details.

        Raises:
            PreComAuthError: token rejected.
            PreComApiError: other failure.
        """
        if self._token is None:
            await self.authenticate()

        try:
            async with self._session.get(
                API_USER_GROUPS_URL,
                headers=self._auth_headers(),
                timeout=aiohttp.ClientTimeout(total=15),
            ) as response:
                if response.status == 401:
                    raise PreComAuthError("Token rejected by GetAllUserGroups (401)")
                if response.status != 200:
                    raise PreComApiError(
                        f"GetAllUserGroups returned HTTP {response.status}"
                    )
                data = await response.json(content_type=None)
                if not isinstance(data, list):
                    raise PreComApiError(
                        f"Expected list from GetAllUserGroups, got {type(data)}"
                    )
                return data
        except aiohttp.ClientError as err:
            raise PreComApiError(
                f"Network error fetching user groups: {err}"
            ) from err

    async def get_group_functions(self, group_id: int, date: str) -> dict[str, Any]:
        """Fetch full group details including populated ServiceFuntions for a given date.

        Args:
            group_id: The GroupID of the group.
            date: ISO 8601 date-time string (e.g. '2026-04-06T00:00:00').

        Returns a group dict with 'ServiceFuntions' populated with NumberNeeded and Users.

        Raises:
            PreComAuthError: token rejected.
            PreComApiError: other failure.
        """
        if self._token is None:
            await self.authenticate()

        try:
            async with self._session.get(
                API_GROUP_FUNCTIONS_URL,
                params={"groupID": group_id, "date": date},
                headers=self._auth_headers(),
                timeout=aiohttp.ClientTimeout(total=15),
            ) as response:
                if response.status == 401:
                    raise PreComAuthError("Token rejected by GetAllFunctions (401)")
                if response.status != 200:
                    raise PreComApiError(
                        f"GetAllFunctions returned HTTP {response.status}"
                    )
                data = await response.json(content_type=None)
                if not isinstance(data, dict):
                    raise PreComApiError(
                        f"Expected dict from GetAllFunctions, got {type(data)}"
                    )
                return data
        except aiohttp.ClientError as err:
            raise PreComApiError(
                f"Network error fetching group functions: {err}"
            ) from err

    async def set_unavailable(self, hours: int) -> None:
        """Mark the user as unavailable/outside region for the given number of hours.

        Args:
            hours: Number of hours to stay outside region (passed as query param).

        Raises:
            PreComAuthError: token rejected.
            PreComApiError: other failure.
        """
        if self._token is None:
            await self.authenticate()

        url = f"{API_SET_OUTSIDE_REGION_URL}?hours={hours}"
        body = {"Location": {"Geofence": "EXIT"}}

        try:
            async with self._session.post(
                url,
                headers=self._auth_headers(),
                json=body,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as response:
                if response.status == 401:
                    raise PreComAuthError("Token rejected by SetOutsideRegion (401)")
                if response.status not in (200, 204):
                    raise PreComApiError(
                        f"SetOutsideRegion returned HTTP {response.status}"
                    )
        except aiohttp.ClientError as err:
            raise PreComApiError(
                f"Network error setting unavailable: {err}"
            ) from err

    async def set_available(self) -> None:
        """Mark the user as available/back inside region.

        Cancels the outside-region status by posting to SetOutsideRegion with
        Geofence set to "ENTER", which signals the user has re-entered their
        response region.

        Raises:
            PreComAuthError: token rejected.
            PreComApiError: other failure.
        """
        if self._token is None:
            await self.authenticate()

        url = f"{API_SET_OUTSIDE_REGION_URL}?hours=0"
        body = {"Location": {"Geofence": "ENTER"}}

        try:
            async with self._session.post(
                url,
                headers=self._auth_headers(),
                json=body,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as response:
                if response.status == 401:
                    raise PreComAuthError("Token rejected by SetOutsideRegion (401)")
                if response.status not in (200, 204):
                    raise PreComApiError(
                        f"SetOutsideRegion returned HTTP {response.status}"
                    )
        except aiohttp.ClientError as err:
            raise PreComApiError(
                f"Network error setting available: {err}"
            ) from err
