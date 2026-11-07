"""Sensors for the Drexel integration."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
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
        DrexelParameterSensor(coordinator, parameter)
        for parameter in coordinator.parameters
        if not parameter.writable and not parameter.is_binary
    )


class DrexelParameterSensor(DrexelParameterEntity, SensorEntity):
    """Read-only parameter of a device: a measurement or a status text."""

    def __init__(self, coordinator: DrexelCoordinator, parameter: Parameter) -> None:
        super().__init__(coordinator, parameter)
        if parameter.options:
            self._attr_device_class = SensorDeviceClass.ENUM
            self._attr_options = list(dict.fromkeys(parameter.options.values()))
            return
        unit = UNITS.get(parameter.unit)
        self._attr_native_unit_of_measurement = (
            unit.unit if unit else parameter.unit or None
        )
        self._attr_device_class = unit.sensor_class if unit else None
        self._attr_suggested_display_precision = parameter.komma
        if parameter.key.startswith("H_"):
            # Betriebsstunden and filter counters; they reset on maintenance.
            self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        elif parameter.unit and self._attr_device_class != SensorDeviceClass.VOLUME:
            self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        if self.parameter.options:
            return self.parameter.option_text(self.raw_value)
        return self.numeric_value
