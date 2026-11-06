"""On/off settings of the Drexel integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import DrexelCoordinator
from .entity import DrexelParameterEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: DrexelCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        DrexelSwitch(coordinator, parameter)
        for parameter in coordinator.parameters
        if parameter.writable and parameter.is_binary
    )


class DrexelSwitch(DrexelParameterEntity, SwitchEntity):
    """A writable two-option parameter (0 = aus/nein, 1 = ein/ja)."""

    @property
    def is_on(self) -> bool | None:
        value = self.raw_value
        return None if value is None else value == 1

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.async_write_raw(1)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.async_write_raw(0)
