"""Polling coordinator for the Aerosmart Fernwartungsmodul."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
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

from .api import (
    Hardware,
    Message,
    Parameter,
    Text,
    build_parameters,
    has_informations,
    index_languages,
    language_code,
    newest_owners,
    newest_row,
    parse_device_values,
    parse_hardware,
    parse_messages,
    parse_values,
    write_body,
)
from .const import DOMAIN, WRITE_CONFIRM_ATTEMPTS, WRITE_CONFIRM_INTERVAL

_LOGGER = logging.getLogger(__name__)


@dataclass
class DrexelData:
    """Result of one polling cycle."""

    values: dict[int, Any]
    devices: dict[int, dict[int, Any]]
    errors_active: bool = False
    errors: list[Message] = field(default_factory=list)
    informations_active: bool = False
    informations: list[Message] = field(default_factory=list)


class DrexelCoordinator(DataUpdateCoordinator[DrexelData]):
    """Load the parameter metadata once, then poll values and messages."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        base_url: str,
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
        self.base_url = base_url
        self.texts: dict[int, Text] = {}
        self.hardware: dict[int, Hardware] = {}
        self.parameters: list[Parameter] = []
        self.owners: dict[int, int] = {}
        self._write_lock = asyncio.Lock()

    def _area_url(self, area: str) -> str:
        return f"{self.base_url}?area={area}"

    async def _async_setup(self) -> None:
        """Fetch texts, devices and parameter metadata (changes only on updates)."""
        languages = await self._async_get_json(self._area_url("languages"))
        self.texts = index_languages(languages, language_code(self.hass.config.language))
        hardware = await self._async_get_json(self._area_url("hardware"))
        self.hardware = {
            device.hardware_id: device for device in parse_hardware(hardware, self.texts)
        }
        options = await self._async_get_json(self._area_url("options"))
        betriebsart = await self._async_get_json(self._area_url("betriebsart"))
        tempconfig = await self._async_get_json(self._area_url("tempconfig"))
        values = await self._async_get_json(self._area_url("values"))
        self.owners = newest_owners(values)
        self.parameters = build_parameters(
            options, [betriebsart, tempconfig], self.texts, self.owners
        )

    async def _async_update_data(self) -> DrexelData:
        values_payload = await self._async_get_json(self._area_url("values"))
        errors = await self._async_get_json(self._area_url("errors"))
        informations = await self._async_get_json(self._area_url("informations"))

        try:
            values = parse_values(values_payload)
        except ValueError as err:
            raise UpdateFailed(str(err)) from err

        # An empty payload means "no messages", anything else is a problem.
        return DrexelData(
            values=values,
            devices=parse_device_values(values_payload),
            errors_active=has_informations(errors),
            errors=parse_messages(errors, self.texts),
            informations_active=has_informations(informations),
            informations=parse_messages(informations, self.texts),
        )

    async def async_write(self, parameter: Parameter, raw: int) -> None:
        """Write a raw value and wait until the module reports the change."""
        owner = None if parameter.environment else parameter.hardware_id
        lastchanges = self._area_url("lastchanges")
        async with self._write_lock:
            before = newest_row(
                await self._async_get_json(lastchanges), parameter.parameter_id, owner
            )
            _LOGGER.debug(
                "Schreibe %s (%s) = %s auf %s",
                parameter.key,
                parameter.parameter_id,
                raw,
                parameter.hardware_id,
            )
            await self._async_post_json(
                write_body(parameter.parameter_id, parameter.hardware_id, raw)
            )
            for _ in range(WRITE_CONFIRM_ATTEMPTS):
                await asyncio.sleep(WRITE_CONFIRM_INTERVAL)
                payload = await self._async_get_json(lastchanges)
                if newest_row(payload, parameter.parameter_id, owner) > before:
                    break
            else:
                _LOGGER.warning(
                    "Änderung von %s wurde vom Fernwartungsmodul nicht bestätigt",
                    parameter.key,
                )
        await self.async_request_refresh()

    async def _async_get_json(self, url: str) -> Any:
        try:
            async with asyncio.timeout(30):
                response = await async_get_clientsession(self.hass).get(url)
                response.raise_for_status()
                return await response.json(content_type=None)
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise UpdateFailed(f"Fehler beim Abrufen von {url}: {err}") from err

    async def _async_post_json(self, body: Any) -> None:
        try:
            async with asyncio.timeout(10):
                response = await async_get_clientsession(self.hass).post(
                    self.base_url, json=body, headers={"Accept": "application/json"}
                )
                response.raise_for_status()
        except (aiohttp.ClientError, TimeoutError) as err:
            raise UpdateFailed(f"Fehler beim Schreiben nach {self.base_url}: {err}") from err
