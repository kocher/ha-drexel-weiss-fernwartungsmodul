"""Sensors for the Drexel integration."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import convert_value
from .const import DOMAIN, SENSORS, SensorDef
from .coordinator import DrexelCoordinator
from .entity import DrexelEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: DrexelCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(DrexelSensor(coordinator, desc) for desc in SENSORS)


class DrexelSensor(DrexelEntity, SensorEntity):
    """One parameter of the heat pump."""

    def __init__(self, coordinator: DrexelCoordinator, description: SensorDef) -> None:
        super().__init__(coordinator, description.parameter_id, description.name)
        self._description = description
        self._attr_device_class = description.device_class
        self._attr_native_unit_of_measurement = description.unit
        self._attr_suggested_display_precision = description.precision

    @property
    def native_value(self):
        return convert_value(
            self._raw_value,
            scale=self._description.scale,
            states=self._description.states,
        )
