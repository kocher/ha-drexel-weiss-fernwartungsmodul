"""Config flow for the Drexel integration."""

from __future__ import annotations

import asyncio
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, OptionsFlow
from homeassistant.data_entry_flow import section
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import TextSelector
from homeassistant.helpers import config_validation as cv

from .api import DEFAULT_PATH, build_url, normalize_host, parse_values
from .const import (
    CONF_HOST,
    CONF_PATH,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    DEFAULT_PORT,
    DOMAIN,
    SCAN_INTERVAL_SECONDS,
)

CONF_ADVANCED = "advanced"

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): TextSelector(),
        vol.Required(CONF_SCAN_INTERVAL, default=SCAN_INTERVAL_SECONDS): vol.All(
            vol.Coerce(int), vol.Range(min=10, max=3600)
        ),
        # The web UI always uses port 334 and /dw; only needed behind a
        # port forwarding or reverse proxy.
        vol.Required(CONF_ADVANCED): section(
            vol.Schema(
                {
                    vol.Required(CONF_PORT, default=DEFAULT_PORT): cv.port,
                    vol.Required(CONF_PATH, default=DEFAULT_PATH): TextSelector(),
                }
            ),
            {"collapsed": True},
        ),
    }
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
            advanced = user_input.get(CONF_ADVANCED, {})
            data = {
                CONF_HOST: normalize_host(user_input[CONF_HOST]),
                CONF_PORT: advanced.get(CONF_PORT, DEFAULT_PORT),
                CONF_PATH: advanced.get(CONF_PATH, DEFAULT_PATH),
                CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL],
            }
            if not data[CONF_HOST]:
                errors[CONF_HOST] = "invalid_host"
            else:
                url = build_url(data[CONF_HOST], data[CONF_PORT], data[CONF_PATH])
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
                    host = data[CONF_HOST].split("://", 1)[1]
                    return self.async_create_entry(
                        title=f"Drexel und Weiss Aerosmart {host}", data=data
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(USER_SCHEMA, user_input),
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
