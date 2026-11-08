"""Drexel und Weiss Aerosmart integration (Fernwartungsmodul)."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .api import Parameter, build_base_url
from .const import (
    CONF_HOST,
    CONF_PATH,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    DOMAIN,
    SCAN_INTERVAL_SECONDS,
)
from .coordinator import DrexelCoordinator
from .entity import hub_device_info, parameter_unique_id

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SWITCH,
    Platform.CLIMATE,
    Platform.WATER_HEATER,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = DrexelCoordinator(
        hass,
        entry,
        build_base_url(
            entry.data[CONF_HOST], entry.data[CONF_PORT], entry.data[CONF_PATH]
        ),
        entry.options.get(
            CONF_SCAN_INTERVAL,
            entry.data.get(CONF_SCAN_INTERVAL, SCAN_INTERVAL_SECONDS),
        ),
    )
    await coordinator.async_config_entry_first_refresh()
    # The devices behind the module reference it via via_device(_id).
    coordinator.hub_device_id = (
        dr.async_get(hass)
        .async_get_or_create(config_entry_id=entry.entry_id, **hub_device_info(coordinator))
        .id
    )
    _async_migrate_legacy_entities(hass, entry, coordinator)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    return True


def _successor(
    coordinator: DrexelCoordinator, parameter_id: int, domain: str
) -> Parameter | None:
    """Read-only per-device parameter that replaces a hand-written entity.

    Several devices report e.g. T_RAUM; the old entity showed the newest.
    """
    parameter = coordinator.device_parameter(parameter_id)
    if parameter is None:
        return None
    if domain != ("binary_sensor" if parameter.is_binary else "sensor"):
        return None
    return parameter


def _async_migrate_legacy_entities(
    hass: HomeAssistant, entry: ConfigEntry, coordinator: DrexelCoordinator
) -> None:
    """Hand the hand-written "Aerosmart …" entities over to per-device ones.

    Their unique id was "<entry_id>_<parameterId>". The registry entry gets the
    unique id of its successor, so entity_id, history and statistics stay.
    """
    registry = er.async_get(hass)
    prefix = f"{entry.entry_id}_"
    for legacy in er.async_entries_for_config_entry(registry, entry.entry_id):
        suffix = legacy.unique_id.removeprefix(prefix)
        if not suffix.isdigit():
            continue
        successor = _successor(coordinator, int(suffix), legacy.domain)
        if successor is None:
            _LOGGER.warning(
                "Kein Nachfolger für %s, Entität bleibt ohne Daten stehen",
                legacy.entity_id,
            )
            continue
        unique_id = parameter_unique_id(entry.entry_id, successor)
        duplicate = registry.async_get_entity_id(legacy.domain, DOMAIN, unique_id)
        if duplicate:
            # Created next to the old entity (disabled by default before);
            # the old one carries the history.
            _LOGGER.info("Entferne %s zugunsten von %s", duplicate, legacy.entity_id)
            registry.async_remove(duplicate)
        _LOGGER.info("Übernehme %s für %s", legacy.entity_id, unique_id)
        registry.async_update_entity(legacy.entity_id, new_unique_id=unique_id)


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded
