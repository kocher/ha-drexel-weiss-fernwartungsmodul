"""Room climate of the Drexel integration (thermostat card, voice assistants)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import Parameter, room_action
from .const import DOMAIN
from .coordinator import DrexelCoordinator
from .entity import parameter_device_info

# Parameters behind the climate entity.
RAUM_SOLL = 5016  # E_RAUM_SOLL, target temperature
BETRIEBSART = 5002  # E_MODUS_WLG, preset
T_RAUM = 200  # current temperature
WP_BETRIEBSSTATUS = 1346  # heating / cooling / idle


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: DrexelCoordinator = hass.data[DOMAIN][entry.entry_id]
    target = coordinator.environment_parameter(RAUM_SOLL)
    if target is not None:
        async_add_entities([DrexelClimate(coordinator, target)])


class DrexelClimate(CoordinatorEntity[DrexelCoordinator], ClimateEntity):
    """Raum-Soll, Raum and Betriebsart as one thermostat.

    The unit has no heating on/off switch, so the only HVAC mode is heat.
    """

    _attr_has_entity_name = True
    _attr_name = "Raum"
    _attr_hvac_modes = [HVACMode.HEAT]
    _attr_hvac_mode = HVACMode.HEAT
    _attr_temperature_unit = UnitOfTemperature.CELSIUS

    def __init__(self, coordinator: DrexelCoordinator, target: Parameter) -> None:
        super().__init__(coordinator)
        self._target = target
        self._current = coordinator.device_parameter(T_RAUM)
        self._action = coordinator.device_parameter(WP_BETRIEBSSTATUS)
        self._preset = coordinator.environment_parameter(BETRIEBSART)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_climate"
        self._attr_device_info = parameter_device_info(coordinator, target)
        self._attr_min_temp = target.to_native(target.minimum)
        self._attr_max_temp = target.to_native(target.maximum)
        self._attr_target_temperature_step = target.to_native(target.step)
        self._attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
        self._presets: dict[str, int] = {}
        if self._preset is not None and self._preset.options:
            self._attr_supported_features |= ClimateEntityFeature.PRESET_MODE
            self._update_presets()

    def _update_presets(self) -> None:
        # A mode that can't be chosen (e.g. Ferien) is listed while active.
        if self._preset is None or not self._preset.options:
            return
        choices = self._preset.choices(self._value(self._preset))
        self._presets = {text: index for index, text in choices.items()}
        self._attr_preset_modes = list(self._presets)

    @callback
    def _handle_coordinator_update(self) -> None:
        self._update_presets()
        super()._handle_coordinator_update()

    def _value(self, parameter: Parameter | None) -> Any:
        return None if parameter is None else self.coordinator.raw_value(parameter)

    @property
    def current_temperature(self) -> float | None:
        if self._current is None:
            return None
        return self._current.to_native(self._value(self._current))

    @property
    def target_temperature(self) -> float | None:
        return self._target.to_native(self._value(self._target))

    @property
    def hvac_action(self) -> HVACAction | None:
        action = room_action(self._value(self._action))
        return None if action is None else HVACAction(action)

    @property
    def preset_mode(self) -> str | None:
        if self._preset is None:
            return None
        return self._preset.option_text(self._value(self._preset))

    async def async_set_temperature(self, **kwargs: Any) -> None:
        if (temperature := kwargs.get(ATTR_TEMPERATURE)) is not None:
            await self.coordinator.async_write(
                self._target, self._target.to_raw(temperature)
            )

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        if self._preset is None or preset_mode not in self._presets:
            raise HomeAssistantError(f"Unbekannte Betriebsart: {preset_mode}")
        await self.coordinator.async_write(self._preset, self._presets[preset_mode])

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        # Heat is the only mode; nothing to switch.
        if hvac_mode != HVACMode.HEAT:
            raise HomeAssistantError(f"Nicht unterstützt: {hvac_mode}")
