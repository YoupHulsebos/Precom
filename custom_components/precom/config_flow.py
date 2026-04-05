"""Config flow for the PreCom integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import PreComApiClient, PreComAuthError, PreComApiError
from .const import (
    CONF_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_SCAN_INTERVAL): vol.All(
            int, vol.Range(min=10, max=3600)
        ),
    }
)


async def _validate_credentials(
    hass: HomeAssistant, username: str, password: str
) -> None:
    """Attempt authentication to confirm the credentials are valid.

    Raises:
        PreComAuthError: credentials invalid.
        PreComApiError: network or server error.
    """
    session = async_get_clientsession(hass)
    client = PreComApiClient(username=username, password=password, session=session)
    await client.authenticate()


class PreComConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the user-facing configuration wizard."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Show the credentials form and validate on submit."""
        errors: dict[str, str] = {}

        if user_input is not None:
            username: str = user_input[CONF_USERNAME]
            password: str = user_input[CONF_PASSWORD]

            # Prevent duplicate entries for the same account
            await self.async_set_unique_id(username.lower())
            self._abort_if_unique_id_configured()

            try:
                await _validate_credentials(self.hass, username, password)
            except PreComAuthError:
                errors["base"] = "invalid_auth"
            except PreComApiError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error during PreCom config flow")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=f"PreCom ({username})",
                    data={
                        CONF_USERNAME: username,
                        CONF_PASSWORD: password,
                        CONF_SCAN_INTERVAL: user_input.get(CONF_SCAN_INTERVAL),
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_SCHEMA,
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> PreComOptionsFlow:
        """Return the options flow handler."""
        return PreComOptionsFlow(config_entry)


class PreComOptionsFlow(config_entries.OptionsFlow):
    """Allow updating the scan interval without re-entering credentials."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Show the options form."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_interval = self._config_entry.data.get(CONF_SCAN_INTERVAL)
        interval_schema: dict = {
            vol.Optional(CONF_SCAN_INTERVAL): vol.Any(
                None,
                vol.All(int, vol.Range(min=10, max=3600)),
            )
        }
        if current_interval is not None:
            interval_schema = {
                vol.Optional(
                    CONF_SCAN_INTERVAL, default=current_interval
                ): vol.All(int, vol.Range(min=10, max=3600))
            }
        schema = vol.Schema(interval_schema)
        return self.async_show_form(step_id="init", data_schema=schema)
