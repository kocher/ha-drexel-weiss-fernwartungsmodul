"""Binary sensors for the Drexel integration."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import BINARY_SENSORS, DOMAIN, BinarySensorDef
from .coordinator import DrexelCoordinator
from .entity import DrexelEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: DrexelCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(DrexelBinarySensor(coordinator, desc) for desc in BINARY_SENSORS)


class DrexelBinarySensor(DrexelEntity, BinarySensorEntity):
    """On/off requirement signal of the heat pump."""

    def __init__(
        self, coordinator: DrexelCoordinator, description: BinarySensorDef
    ) -> None:
        super().__init__(coordinator, description.parameter_id, description.name)
        self._attr_device_class = description.device_class

    @property
    def is_on(self) -> bool | None:
        value = self._raw_value
        return None if value is None else bool(value)
