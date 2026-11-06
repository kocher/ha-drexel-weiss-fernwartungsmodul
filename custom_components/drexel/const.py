"""Constants and entity descriptions for the Drexel integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.sensor import SensorDeviceClass

DOMAIN = "drexel"

CONF_HOST = "host"
CONF_PORT = "port"
CONF_PATH = "path"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_PORT = 334
DEFAULT_PATH = "/dw"
SCAN_INTERVAL_SECONDS = 60

STATUS_WP = {
    0: "Wiedereinschaltsperre",
    1: "Wärmepumpe aus",
    2: "Vorlaufzeit Solepumpe",
    3: "Vorlaufzeit Ventilatoren",
    4: "Öffnen Heissgasventil",
    5: "Öffnen Flüssiggasventil",
    6: "Start Kompressor",
    7: "Mindestlaufzeit Wärmepumpe",
    8: "Wärmepumpe ein",
    9: "Kältemittel absaugen",
    10: "Beim Abtauen absaugen",
    11: "Abtauen ein",
    12: "Nach Abtauen abtropfen",
    13: "Pufferentladung",
    14: "Abtaumodus definieren",
}

BETRIEBSSTATUS = {
    0: "Aus",
    1: "Badheizung",
    2: "Boilerladung",
    3: "Boilerladung/Frischluftheizung",
    4: "Boilerladung/Niedertemperaturheizung",
    5: "Frostschutz",
    6: "Frischluftheizung",
    7: "Niedertemperaturheizung",
    8: "Frischluft-/Niedertemperaturheizung",
    9: "solare Heizungsunterstützung",
    10: "Passive Kühlung",
    11: "Aktive Kühlung",
    12: "Funktionsheizen",
}


@dataclass(frozen=True, kw_only=True)
class SensorDef:
    parameter_id: int
    name: str
    device_class: SensorDeviceClass | None = None
    unit: str | None = None
    scale: float = 1
    precision: int | None = None
    states: dict[int, str] | None = None


@dataclass(frozen=True, kw_only=True)
class BinarySensorDef:
    parameter_id: int
    name: str
    device_class: BinarySensorDeviceClass | None = None


SENSORS: tuple[SensorDef, ...] = (
    SensorDef(
        parameter_id=210,
        name="Aerosmart Verdampferregister",
        device_class=SensorDeviceClass.TEMPERATURE,
        unit="°C",
        scale=1000,
        precision=1,
    ),
    SensorDef(
        parameter_id=212,
        name="Aerosmart Warmwasserspeicher oben",
        device_class=SensorDeviceClass.TEMPERATURE,
        unit="°C",
        scale=1000,
        precision=1,
    ),
    SensorDef(
        parameter_id=214,
        name="Aerosmart Warmwasserspeicher WP",
        device_class=SensorDeviceClass.TEMPERATURE,
        unit="°C",
        scale=1000,
        precision=1,
    ),
    SensorDef(
        parameter_id=1184,
        name="Aerosmart Ist-Drehzahl Zuluftventilator",
        unit="rpm",
    ),
    SensorDef(
        parameter_id=1186,
        name="Aerosmart Ist-Drehzahl Abluftventilator",
        unit="rpm",
    ),
    SensorDef(
        parameter_id=1314,
        name="Aerosmart Status WP",
        states=STATUS_WP,
    ),
    SensorDef(
        parameter_id=1346,
        name="Aerosmart WP Betriebsstatus",
        states=BETRIEBSSTATUS,
    ),
    SensorDef(
        parameter_id=200,
        name="Aerosmart Raum",
        device_class=SensorDeviceClass.TEMPERATURE,
        unit="°C",
        scale=1000,
        precision=1,
    ),
    SensorDef(
        parameter_id=5016,
        name="Aerosmart Raum Soll",
        device_class=SensorDeviceClass.TEMPERATURE,
        unit="°C",
        scale=1000,
        precision=1,
    ),
    SensorDef(
        parameter_id=1054,
        name="Aerosmart Boiler",
        device_class=SensorDeviceClass.TEMPERATURE,
        unit="°C",
        scale=1000,
        precision=1,
    ),
    SensorDef(
        parameter_id=5064,
        name="Aerosmart Brauchwasser Soll",
        device_class=SensorDeviceClass.TEMPERATURE,
        unit="°C",
        scale=1000,
        precision=1,
    ),
    SensorDef(
        parameter_id=230,
        name="Aerosmart CO₂",
        device_class=SensorDeviceClass.CO2,
        unit="ppm",
    ),
)

BINARY_SENSORS: tuple[BinarySensorDef, ...] = (
    BinarySensorDef(
        parameter_id=1032,
        name="Aerosmart Anforderung: Raum-Heizstufe 1",
        device_class=BinarySensorDeviceClass.HEAT,
    ),
    BinarySensorDef(
        parameter_id=1034,
        name="Aerosmart Anforderung: Raum-Heizstufe 2",
        device_class=BinarySensorDeviceClass.HEAT,
    ),
    BinarySensorDef(
        parameter_id=1036,
        name="Aerosmart Anforderung: Brauchwasserheizung Wärmepumpe",
        device_class=BinarySensorDeviceClass.HEAT,
    ),
    BinarySensorDef(
        parameter_id=1038,
        name="Aerosmart Anforderung: Brauchwasserheizung Elektroheizstab",
        device_class=BinarySensorDeviceClass.POWER,
    ),
)
