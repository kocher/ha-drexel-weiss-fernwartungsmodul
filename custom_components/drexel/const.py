"""Constants for the Drexel integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import NumberDeviceClass
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import (
    PERCENTAGE,
    REVOLUTIONS_PER_MINUTE,
    UnitOfTemperature,
    UnitOfTime,
    UnitOfVolume,
    UnitOfVolumeFlowRate,
)

try:  # HA 2026.11+
    from homeassistant.const import UnitOfRatio

    PARTS_PER_MILLION: str = UnitOfRatio.PARTS_PER_MILLION
except ImportError:
    from homeassistant.const import CONCENTRATION_PARTS_PER_MILLION as PARTS_PER_MILLION

DOMAIN = "drexel"

CONF_HOST = "host"
CONF_PORT = "port"
CONF_PATH = "path"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_PORT = 334
DEFAULT_PATH = "/dw"
SCAN_INTERVAL_SECONDS = 60

# The web UI polls lastchanges once per second, ten times, to confirm a write.
WRITE_CONFIRM_ATTEMPTS = 10
WRITE_CONFIRM_INTERVAL = 1

# Device names by hardware name from area=hardware.
DEVICE_LABELS = {
    "WP": "Wärmepumpe",
    "LU": "Lüftung",
    "RBG-TP": "Raumbediengerät",
    "RBG-V/H": "Raumbediengerät",
    "VB": "Verteilerbox",
}


@dataclass(frozen=True)
class UnitDef:
    unit: str
    sensor_class: SensorDeviceClass | None = None
    number_class: NumberDeviceClass | None = None


# Units (einheit) of the module mapped to Home Assistant.
UNITS = {
    "°C": UnitDef(
        UnitOfTemperature.CELSIUS,
        SensorDeviceClass.TEMPERATURE,
        NumberDeviceClass.TEMPERATURE,
    ),
    "K": UnitDef(UnitOfTemperature.KELVIN),
    "ppm": UnitDef(
        PARTS_PER_MILLION, SensorDeviceClass.CO2, NumberDeviceClass.CO2
    ),
    "1/min": UnitDef(REVOLUTIONS_PER_MINUTE),
    "h": UnitDef(UnitOfTime.HOURS, SensorDeviceClass.DURATION, NumberDeviceClass.DURATION),
    "min": UnitDef(
        UnitOfTime.MINUTES, SensorDeviceClass.DURATION, NumberDeviceClass.DURATION
    ),
    "sec": UnitDef(
        UnitOfTime.SECONDS, SensorDeviceClass.DURATION, NumberDeviceClass.DURATION
    ),
    "%": UnitDef(PERCENTAGE),
    "m³": UnitDef(UnitOfVolume.CUBIC_METERS, SensorDeviceClass.VOLUME),
    "m³/h": UnitDef(
        UnitOfVolumeFlowRate.CUBIC_METERS_PER_HOUR,
        SensorDeviceClass.VOLUME_FLOW_RATE,
        NumberDeviceClass.VOLUME_FLOW_RATE,
    ),
}

