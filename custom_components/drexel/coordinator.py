"""Polling coordinator for the Aerosmart Fernwartungsmodul."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import has_informations, parse_values
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class DrexelCoordinator(DataUpdateCoordinator[dict[int, Any]]):
    """Fetch all parameter values and the informations in one cycle."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        url: str,
        informations_url: str,
        scan_interval: int,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.entry = entry
        self.url = url
        self.informations_url = informations_url
        self.informations = False

    async def _async_update_data(self) -> dict[int, Any]:
        values_payload = await self._async_get_json(self.url)
        informations = await self._async_get_json(self.informations_url)

        try:
            values = parse_values(values_payload)
        except ValueError as err:
            raise UpdateFailed(str(err)) from err

        # An empty payload means "no informations", anything else is a problem.
        self.informations = has_informations(informations)
        return values

    async def _async_get_json(self, url: str) -> Any:
        try:
            async with asyncio.timeout(10):
                response = await async_get_clientsession(self.hass).get(url)
                response.raise_for_status()
                return await response.json(content_type=None)
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise UpdateFailed(f"Fehler beim Abrufen von {url}: {err}") from err
