"""Binary sensors for the Drexel integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import Message, Parameter
from .const import DEVICE_LABELS, DOMAIN
from .coordinator import DrexelCoordinator
from .entity import DrexelEntity, DrexelParameterEntity

# Device classes by parameterName prefix.
PREFIX_CLASSES = {
    "K_": BinarySensorDeviceClass.RUNNING,  # Relaiskontakte
    "TUER_": BinarySensorDeviceClass.DOOR,
    "PSA_": BinarySensorDeviceClass.PROBLEM,  # Hoch-/Niederdruckschalter
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: DrexelCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [DrexelInformationSensor(coordinator), DrexelErrorSensor(coordinator)]
        + [
            DrexelParameterBinarySensor(coordinator, parameter)
            for parameter in coordinator.parameters
            if not parameter.writable and parameter.is_binary
        ]
    )


def _message_attributes(
    coordinator: DrexelCoordinator, messages: list[Message]
) -> dict[str, Any]:
    texts = []
    for message in messages:
        hardware = coordinator.hardware.get(message.hardware_id)
        if hardware is None:
            texts.append(message.text)
        else:
            label = DEVICE_LABELS.get(hardware.name, hardware.name)
            texts.append(f"{label}: {message.text}")
    return {"meldungen": texts}


class DrexelInformationSensor(DrexelEntity, BinarySensorEntity):
    """On when the module reports informations (problems)."""

    def __init__(self, coordinator: DrexelCoordinator) -> None:
        super().__init__(coordinator, "informations", "Informationen")
        self._attr_device_class = BinarySensorDeviceClass.PROBLEM

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.informations_active

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return _message_attributes(self.coordinator, self.coordinator.data.informations)


class DrexelErrorSensor(DrexelEntity, BinarySensorEntity):
    """On when the module reports active faults (area=errors)."""

    def __init__(self, coordinator: DrexelCoordinator) -> None:
        super().__init__(coordinator, "errors", "Störung")
        self._attr_device_class = BinarySensorDeviceClass.PROBLEM

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.errors_active

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return _message_attributes(self.coordinator, self.coordinator.data.errors)


class DrexelParameterBinarySensor(DrexelParameterEntity, BinarySensorEntity):
    """Read-only two-state parameter (relay contact, requirement, ...)."""

    def __init__(self, coordinator: DrexelCoordinator, parameter: Parameter) -> None:
        super().__init__(coordinator, parameter)
        self._attr_device_class = next(
            (
                device_class
                for prefix, device_class in PREFIX_CLASSES.items()
                if parameter.key.startswith(prefix)
            ),
            None,
        )

    @property
    def is_on(self) -> bool | None:
        value = self.raw_value
        return None if value is None else value == 1
