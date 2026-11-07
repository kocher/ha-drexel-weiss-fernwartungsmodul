"""Domestic hot water of the Drexel integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.water_heater import (
    STATE_HEAT_PUMP,
    WaterHeaterEntity,
    WaterHeaterEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import Parameter
from .const import DOMAIN
from .coordinator import DrexelCoordinator
from .entity import parameter_device_info

BRAUCHWASSER_SOLL = 5064  # E_T_BW_SOLL, target temperature
T_BOILER = 1054  # current temperature
T_BW_EHZ = 212  # fallback: Warmwasserspeicher oben


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: DrexelCoordinator = hass.data[DOMAIN][entry.entry_id]
    target = coordinator.environment_parameter(BRAUCHWASSER_SOLL)
    if target is not None:
        async_add_entities([DrexelWaterHeater(coordinator, target)])


class DrexelWaterHeater(CoordinatorEntity[DrexelCoordinator], WaterHeaterEntity):
    """Brauchwasser-Soll and boiler temperature as one water heater.

    The module has no hot water mode to switch; the state is always
    "heat_pump" (a water heater without operation mode would be "unknown").
    """

    _attr_has_entity_name = True
    _attr_name = "Brauchwasser"
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = WaterHeaterEntityFeature.TARGET_TEMPERATURE
    _attr_current_operation = STATE_HEAT_PUMP
    _attr_operation_list = [STATE_HEAT_PUMP]

    def __init__(self, coordinator: DrexelCoordinator, target: Parameter) -> None:
        super().__init__(coordinator)
        self._target = target
        self._current = coordinator.device_parameter(
            T_BOILER
        ) or coordinator.device_parameter(T_BW_EHZ)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_water_heater"
        self._attr_device_info = parameter_device_info(coordinator, target)
        self._attr_min_temp = target.to_native(target.minimum)
        self._attr_max_temp = target.to_native(target.maximum)
        self._attr_target_temperature_step = target.to_native(target.step)

    @property
    def current_temperature(self) -> float | None:
        if self._current is None:
            return None
        return self._current.to_native(self.coordinator.raw_value(self._current))

    @property
    def target_temperature(self) -> float | None:
        return self._target.to_native(self.coordinator.raw_value(self._target))

    async def async_set_temperature(self, **kwargs: Any) -> None:
        if (temperature := kwargs.get(ATTR_TEMPERATURE)) is not None:
            await self.coordinator.async_write(
                self._target, self._target.to_raw(temperature)
            )
