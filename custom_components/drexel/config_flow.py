"""Config flow for the Drexel integration."""

from __future__ import annotations

import asyncio
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, OptionsFlow
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import TextSelector
from homeassistant.helpers import config_validation as cv

from .api import DEFAULT_PATH, build_url, parse_values
from .const import (
    CONF_HOST,
    CONF_PATH,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    DEFAULT_PORT,
    DOMAIN,
    SCAN_INTERVAL_SECONDS,
)


class DrexelConfigFlow(ConfigFlow, domain=DOMAIN):
    """Ask for the address of the heat pump."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(config_entry) -> DrexelOptionsFlow:
        return DrexelOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        errors: dict[str, str] = {}

        if user_input is not None:
            url = build_url(
                user_input[CONF_HOST], user_input[CONF_PORT], user_input[CONF_PATH]
            )
            try:
                async with asyncio.timeout(10):
                    response = await async_get_clientsession(self.hass).get(url)
                    response.raise_for_status()
                    parse_values(await response.json(content_type=None))
            except (aiohttp.ClientError, TimeoutError, ValueError):
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(url)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Drexel und Weiss Aerosmart {user_input[CONF_HOST]}",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): TextSelector(),
                    vol.Required(CONF_PORT, default=DEFAULT_PORT): cv.port,
                    vol.Required(CONF_PATH, default=DEFAULT_PATH): TextSelector(),
                    vol.Required(
                        CONF_SCAN_INTERVAL, default=SCAN_INTERVAL_SECONDS
                    ): vol.All(vol.Coerce(int), vol.Range(min=10, max=3600)),
                }
            ),
            errors=errors,
        )


class DrexelOptionsFlow(OptionsFlow):
    """Change the polling interval."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_SCAN_INTERVAL,
                            self.config_entry.data.get(
                                CONF_SCAN_INTERVAL, SCAN_INTERVAL_SECONDS
                            ),
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=10, max=3600)),
                }
            ),
        )
