"""Option settings (operating mode, functions) of the Drexel integration."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import Parameter
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
        DrexelSelect(coordinator, parameter)
        for parameter in coordinator.parameters
        if parameter.writable and parameter.options and not parameter.is_binary
    )


class DrexelSelect(DrexelParameterEntity, SelectEntity):
    """A writable parameter with named options; index = raw value."""

    def __init__(self, coordinator: DrexelCoordinator, parameter: Parameter) -> None:
        super().__init__(coordinator, parameter)
        self._update_options()

    def _update_options(self) -> None:
        # A value that can't be chosen (e.g. Ferien) is listed while active.
        choices = self.parameter.choices(self.raw_value)
        self._indexes = {text: index for index, text in choices.items()}
        self._attr_options = list(self._indexes)

    @callback
    def _handle_coordinator_update(self) -> None:
        self._update_options()
        super()._handle_coordinator_update()

    @property
    def current_option(self) -> str | None:
        return self.parameter.option_text(self.raw_value)

    async def async_select_option(self, option: str) -> None:
        if option not in self._indexes:
            raise HomeAssistantError(f"Unbekannte Option: {option}")
        await self.async_write_raw(self._indexes[option])
