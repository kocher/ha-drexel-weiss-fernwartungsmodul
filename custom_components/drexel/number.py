"""Numeric settings (setpoints, times, limits) of the Drexel integration."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import Parameter
from .const import DOMAIN, UNITS
from .coordinator import DrexelCoordinator
from .entity import DrexelParameterEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: DrexelCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        DrexelNumber(coordinator, parameter)
        for parameter in coordinator.parameters
        if parameter.writable and not parameter.options
    )


class DrexelNumber(DrexelParameterEntity, NumberEntity):
    """A writable numeric parameter; range and step come from the module."""

    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: DrexelCoordinator, parameter: Parameter) -> None:
        super().__init__(coordinator, parameter)
        unit = UNITS.get(parameter.unit)
        self._attr_native_unit_of_measurement = (
            unit.unit if unit else parameter.unit or None
        )
        self._attr_device_class = unit.number_class if unit else None
        self._attr_native_min_value = parameter.to_native(parameter.minimum)
        self._attr_native_max_value = parameter.to_native(parameter.maximum)
        self._attr_native_step = parameter.to_native(parameter.step)

    @property
    def native_value(self) -> float | None:
        return self.parameter.to_native(self.raw_value)

    async def async_set_native_value(self, value: float) -> None:
        await self.async_write_raw(self.parameter.to_raw(value))
