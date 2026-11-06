"""Shared base entities for Drexel."""

from __future__ import annotations

from typing import Any

from homeassistant.const import EntityCategory
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import Parameter
from .const import DEVICE_LABELS, DOMAIN, ENVIRONMENT_NAMES, LEGACY_PARAMETER_IDS
from .coordinator import DrexelCoordinator


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
        via_device=(DOMAIN, coordinator.entry.entry_id),
    )


class DrexelEntity(CoordinatorEntity[DrexelCoordinator]):
    """Common name, unique id and device grouping."""

    def __init__(
        self, coordinator: DrexelCoordinator, parameter_id: int | str, name: str
    ) -> None:
        super().__init__(coordinator)
        self._parameter_id = parameter_id
        self._attr_name = name
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{parameter_id}"
        self._attr_device_info = hub_device_info(coordinator)

    @property
    def _raw_value(self):
        return self.coordinator.data.values.get(self._parameter_id)


class DrexelParameterEntity(CoordinatorEntity[DrexelCoordinator]):
    """An entity built from the module's own parameter metadata."""

    def __init__(self, coordinator: DrexelCoordinator, parameter: Parameter) -> None:
        super().__init__(coordinator)
        self.parameter = parameter
        entry_id = coordinator.entry.entry_id
        if parameter.environment:
            # Environment-wide controls live on the module, named like the
            # existing entities.
            self._attr_name = ENVIRONMENT_NAMES.get(
                parameter.parameter_id, f"Aerosmart {parameter.name}"
            )
            self._attr_unique_id = (
                f"{entry_id}_env{parameter.hardware_id}_{parameter.parameter_id}"
            )
            self._attr_device_info = hub_device_info(coordinator)
        else:
            self._attr_has_entity_name = True
            self._attr_name = parameter.name
            self._attr_unique_id = (
                f"{entry_id}_{parameter.hardware_id}_{parameter.parameter_id}"
            )
            self._attr_device_info = hardware_device_info(
                coordinator, parameter.hardware_id
            )
            if parameter.writable:
                # Settings that restart the device stay off until enabled.
                self._attr_entity_category = EntityCategory.CONFIG
                self._attr_entity_registry_enabled_default = not parameter.restart
            else:
                if parameter.key.startswith("E_") or parameter.key == "VERSION":
                    self._attr_entity_category = EntityCategory.DIAGNOSTIC
                self._attr_entity_registry_enabled_default = (
                    parameter.parameter_id not in LEGACY_PARAMETER_IDS
                )
        self._attr_extra_state_attributes = {
            "parameter": parameter.key,
            "parameter_id": parameter.parameter_id,
        }

    @property
    def raw_value(self) -> Any:
        data = self.coordinator.data
        if self.parameter.environment:
            return data.values.get(self.parameter.parameter_id)
        return data.devices.get(self.parameter.hardware_id, {}).get(
            self.parameter.parameter_id
        )

    async def async_write_raw(self, raw: int) -> None:
        await self.coordinator.async_write(self.parameter, raw)
