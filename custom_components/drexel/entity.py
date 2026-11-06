"""Shared base entity for Drexel."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import DrexelCoordinator


class DrexelEntity(CoordinatorEntity[DrexelCoordinator]):
    """Common name, unique id and device grouping."""

    def __init__(
        self, coordinator: DrexelCoordinator, parameter_id: int, name: str
    ) -> None:
        super().__init__(coordinator)
        self._parameter_id = parameter_id
        self._attr_name = name
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{parameter_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.entry.entry_id)},
            name=coordinator.entry.title,
            manufacturer="Drexel und Weiss",
            model="Aerosmart Fernwartungsmodul",
        )

    @property
    def _raw_value(self):
        return (self.coordinator.data or {}).get(self._parameter_id)
