"""Shared base entities for Drexel."""

from __future__ import annotations

import inspect
from typing import Any

from homeassistant.const import EntityCategory
from homeassistant.helpers.device_registry import DeviceInfo, DeviceRegistry
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import Parameter
from .const import DEVICE_LABELS, DOMAIN
from .coordinator import DrexelCoordinator

# HA 2026.11 references the parent device by registry id (via_device_id).
_VIA_DEVICE_ID = "via_device_id" in inspect.signature(
    DeviceRegistry.async_get_or_create
).parameters


def hub_device_info(coordinator: DrexelCoordinator) -> DeviceInfo:
    """The Fernwartungsmodul itself."""
    return DeviceInfo(
        identifiers={(DOMAIN, coordinator.entry.entry_id)},
        name=coordinator.entry.title,
        manufacturer="Drexel und Weiss",
        model="Aerosmart Fernwartungsmodul",
    )


def hardware_device_info(coordinator: DrexelCoordinator, hardware_id: int) -> DeviceInfo:
    """One device behind the module (Wärmepumpe, Lüftung, Raumbediengerät)."""
    hardware = coordinator.hardware.get(hardware_id)
    name = hardware.name if hardware else str(hardware_id)
    return DeviceInfo(
        identifiers={(DOMAIN, f"{coordinator.entry.entry_id}_{hardware_id}")},
        name=f"Aerosmart {DEVICE_LABELS.get(name, name)}",
        manufacturer="Drexel und Weiss",
        model=hardware.model if hardware else None,
        serial_number=hardware.serial_number if hardware else None,
        sw_version=hardware.software_version if hardware else None,
        **(
            {"via_device_id": coordinator.hub_device_id}
            if _VIA_DEVICE_ID
            else {"via_device": (DOMAIN, coordinator.entry.entry_id)}
        ),
    )


def parameter_device_info(
    coordinator: DrexelCoordinator, parameter: Parameter
) -> DeviceInfo:
    """Device a parameter is shown on; environment controls have one too."""
    if parameter.device_id is None:
        return hub_device_info(coordinator)
    return hardware_device_info(coordinator, parameter.device_id)


def parameter_unique_id(entry_id: str, parameter: Parameter) -> str:
    if parameter.environment:
        return f"{entry_id}_env{parameter.hardware_id}_{parameter.parameter_id}"
    return f"{entry_id}_{parameter.hardware_id}_{parameter.parameter_id}"


class DrexelEntity(CoordinatorEntity[DrexelCoordinator]):
    """An entity of the module itself (messages)."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: DrexelCoordinator, key: str, name: str) -> None:
        super().__init__(coordinator)
        self._attr_name = name
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{key}"
        self._attr_device_info = hub_device_info(coordinator)


class DrexelParameterEntity(CoordinatorEntity[DrexelCoordinator]):
    """An entity built from the module's own parameter metadata."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: DrexelCoordinator, parameter: Parameter) -> None:
        super().__init__(coordinator)
        self.parameter = parameter
        self._attr_name = parameter.name
        self._attr_unique_id = parameter_unique_id(coordinator.entry.entry_id, parameter)
        # Environment controls are shown on the device that reports them.
        self._attr_device_info = parameter_device_info(coordinator, parameter)
        if parameter.writable and not parameter.environment:
            # Settings that restart the device stay off until enabled.
            self._attr_entity_category = EntityCategory.CONFIG
            self._attr_entity_registry_enabled_default = not parameter.restart
        elif not parameter.writable and (
            parameter.key.startswith("E_") or parameter.key == "VERSION"
        ):
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_extra_state_attributes = {
            "parameter": parameter.key,
            "parameter_id": parameter.parameter_id,
        }

    @property
    def raw_value(self) -> Any:
        return self.coordinator.raw_value(self.parameter)

    @property
    def numeric_value(self) -> float | int:
        """Display value; 0 when the module doesn't report it, like the web UI."""
        raw = self.raw_value
        return self.parameter.to_native(0 if raw is None else raw)

    async def async_write_raw(self, raw: int) -> None:
        await self.coordinator.async_write(self.parameter, raw)
