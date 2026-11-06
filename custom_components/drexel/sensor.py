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

from .api import Parameter, convert_value
from .const import DOMAIN, SENSORS, UNITS, SensorDef
from .coordinator import DrexelCoordinator
from .entity import DrexelEntity, DrexelParameterEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: DrexelCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [DrexelSensor(coordinator, desc) for desc in SENSORS]
        + [
            DrexelParameterSensor(coordinator, parameter)
            for parameter in coordinator.parameters
            if not parameter.writable and not parameter.is_binary
        ]
    )


class DrexelSensor(DrexelEntity, SensorEntity):
    """One parameter of the heat pump."""

    def __init__(self, coordinator: DrexelCoordinator, description: SensorDef) -> None:
        super().__init__(coordinator, description.parameter_id, description.name)
        self._description = description
        if description.states is None:
            self._attr_device_class = description.device_class
            self._attr_state_class = SensorStateClass.MEASUREMENT
        else:
            self._attr_device_class = SensorDeviceClass.ENUM
            self._attr_options = [*description.states.values(), "Unbekannt"]
        self._attr_native_unit_of_measurement = description.unit
        self._attr_suggested_display_precision = description.precision

    @property
    def native_value(self):
        return convert_value(
            self._raw_value,
            scale=self._description.scale,
            states=self._description.states,
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
        return self.parameter.to_native(self.raw_value)
