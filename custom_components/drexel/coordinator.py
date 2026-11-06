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

from .api import parse_values
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class DrexelCoordinator(DataUpdateCoordinator[dict[int, Any]]):
    """Fetch all parameter values in one request."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, url: str, scan_interval: int
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

    async def _async_update_data(self) -> dict[int, Any]:
        try:
            async with asyncio.timeout(10):
                response = await async_get_clientsession(self.hass).get(self.url)
                response.raise_for_status()
                payload = await response.json(content_type=None)
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise UpdateFailed(f"Fehler beim Abrufen von {self.url}: {err}") from err

        try:
            return parse_values(payload)
        except ValueError as err:
            raise UpdateFailed(str(err)) from err
