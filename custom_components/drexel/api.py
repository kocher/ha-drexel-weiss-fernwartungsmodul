"""Pure helpers for the Aerosmart Fernwartungsmodul API (see docs/API.md)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlsplit

DEFAULT_PATH = "/dw"
QUERY = "area=values"
INFORMATIONS_QUERY = "area=informations"

LANGUAGES = ("DE", "EN", "FR", "IT")
DEFAULT_LANGUAGE = "DE"

# Menu areas (bereichBit) of the web UI.
BEREICH_STATUS = 0
BEREICH_BETRIEB = 3

# Never offered as entities: factory reset and clearing the fault history.
DANGEROUS_PARAMETERS = frozenset({6000, 6002})

# Options the web UI never offers although the metadata allows them: for the
# operating mode it only shows indexes below 6, i.e. not Ferien (6) and
# Reinigung (7).
HIDDEN_OPTIONS = {5002: frozenset({6, 7})}

# Reported in area=values but in no menu of the web UI; added as read-only
# parameters of the device that reports them.
EXTRA_PARAMETERS = {
    1054: {"parameterName": "T_BOILER", "einheit": "°C", "divisor": 100, "komma": 1},
}


def normalize_host(text: str) -> str:
    """Reduce what the user typed to scheme and host.

    Accepts "192.168.1.2", "aerosmart.local" or the web UI address
    ("http://192.168.1.2/home"); the port and path of the web UI are dropped,
    the API has its own.
    """
    text = text.strip()
    if "://" not in text:
        if text.count(":") > 1 and not text.startswith("["):
            text = f"[{text}]"  # bare IPv6 address
        text = f"http://{text}"
    parts = urlsplit(text)
    host = parts.hostname or ""
    if ":" in host:  # IPv6
        host = f"[{host}]"
    return f"{parts.scheme}://{host}" if host else ""


def build_base_url(host: str, port: int, path: str = DEFAULT_PATH) -> str:
    """Build the API URL (without area) from the user config."""
    host = host.strip().rstrip("/")
    if not host.startswith(("http://", "https://")):
        host = f"http://{host}"
    path = (path.strip() or DEFAULT_PATH)
    if not path.startswith("/"):
        path = f"/{path}"
    return f"{host}:{port}{path}"


def build_url(
    host: str, port: int, path: str = DEFAULT_PATH, query: str = QUERY
) -> str:
    """Build an area URL from the user config."""
    return f"{build_base_url(host, port, path)}?{query}"


def _device_blocks(payload: Any) -> list[dict[str, Any]]:
    """Return the per-device objects of all environment blocks."""
    if not isinstance(payload, list):
        return []
    return [
        device
        for environment in payload
        if isinstance(environment, dict)
        for device in environment.get("value") or []
        if isinstance(device, dict)
    ]


def parse_values(payload: Any) -> dict[int, Any]:
    """Flatten ``[{"value": [{"values": [...]}]}]`` into {parameterId: currentValue}.

    Several devices report the same parameterId, often with stale values. Like
    the web UI, keep the entry with the highest ``rowId`` (the newest one).
    """
    try:
        newest: dict[int, tuple[int, Any]] = {}
        for group in payload[0]["value"]:
            for item in group.get("values") or []:
                parameter_id = item.get("parameterId")
                if parameter_id is None:
                    continue
                row_id = item.get("rowId") or 0
                if parameter_id not in newest or row_id >= newest[parameter_id][0]:
                    newest[parameter_id] = (row_id, item.get("currentValue"))
    except (KeyError, IndexError, TypeError, AttributeError) as err:
        raise ValueError("Unerwartete Antwort vom Aerosmart-Fernwartungsmodul") from err
    return {parameter_id: value for parameter_id, (_, value) in newest.items()}


def parse_device_values(payload: Any) -> dict[int, dict[int, Any]]:
    """Return {hardwareId: {parameterId: currentValue}} without merging devices."""
    devices: dict[int, dict[int, Any]] = {}
    for device in _device_blocks(payload):
        hardware_id = device.get("hardwareId")
        if hardware_id is None:
            continue
        values = devices.setdefault(hardware_id, {})
        for item in device.get("values") or []:
            if isinstance(item, dict) and item.get("parameterId") is not None:
                values[item["parameterId"]] = item.get("currentValue")
    return devices


def newest_row(payload: Any, parameter_id: int, hardware_id: int | None = None) -> int:
    """Highest rowId of a parameter (optionally of one device), -1 if absent.

    Used on ``area=lastchanges`` to confirm that a write was applied.
    """
    rows = [
        item.get("rowId") or 0
        for device in _device_blocks(payload)
        if hardware_id is None or device.get("hardwareId") == hardware_id
        for item in device.get("values") or []
        if isinstance(item, dict) and item.get("parameterId") == parameter_id
    ]
    return max(rows, default=-1)


def newest_owners(payload: Any) -> dict[int, int]:
    """Return {parameterId: hardwareId} of the device with the newest row."""
    newest: dict[int, tuple[int, int]] = {}
    for device in _device_blocks(payload):
        hardware_id = device.get("hardwareId")
        if hardware_id is None:
            continue
        for item in device.get("values") or []:
            if not isinstance(item, dict) or item.get("parameterId") is None:
                continue
            row_id = item.get("rowId") or 0
            parameter_id = item["parameterId"]
            if parameter_id not in newest or row_id >= newest[parameter_id][0]:
                newest[parameter_id] = (row_id, hardware_id)
    return {parameter_id: owner for parameter_id, (_, owner) in newest.items()}


def write_body(parameter_id: int, device_id: int, raw: int) -> list[dict[str, int]]:
    """Body for ``POST /dw``; deviceId is a hardwareId or an environment key."""
    return [{"parameterId": parameter_id, "deviceId": device_id, "value": raw}]


def has_informations(payload: Any) -> bool:
    """Return True if an informations answer carries anything.

    The module wraps reports the same way as the values area, so an empty
    ``{}``, ``[]`` or ``{"value": []}`` all mean "no information". In an
    envelope only ``value`` counts, not ``key``, ``identifier`` or ``ticks``.
    """
    if isinstance(payload, dict):
        if "value" in payload:
            return has_informations(payload["value"])
        return any(has_informations(value) for value in payload.values())
    if isinstance(payload, (list, tuple)):
        return any(has_informations(item) for item in payload)
    return bool(payload)


# --- Texts -----------------------------------------------------------------


@dataclass(frozen=True)
class Text:
    """Display name and option texts of one parameter in one language."""

    name: str
    options: dict[int, str]


def language_code(language: str | None) -> str:
    """Map a Home Assistant language ("de", "en-GB") to the module's codes."""
    code = (language or "")[:2].upper()
    return code if code in LANGUAGES else DEFAULT_LANGUAGE


def _clean(text: Any) -> str:
    return " ".join(str(text or "").replace("\\", " ").split())


def index_languages(payload: Any, language: str) -> dict[int, Text]:
    """Index ``area=languages`` by parameterId, falling back to German."""
    texts: dict[int, Text] = {}
    fallback: dict[int, Text] = {}
    for entry in payload if isinstance(payload, list) else []:
        if not isinstance(entry, dict) or entry.get("parameterId") is None:
            continue
        text = Text(
            name=_clean(entry.get("name")),
            options={
                unit["index"]: _clean(unit.get("text"))
                for unit in entry.get("units") or []
                if isinstance(unit, dict) and _clean(unit.get("text"))
            },
        )
        if entry.get("countryCode") == language:
            texts[entry["parameterId"]] = text
        elif entry.get("countryCode") == DEFAULT_LANGUAGE:
            fallback[entry["parameterId"]] = text
    for parameter_id, text in texts.items():
        german = fallback.get(parameter_id)
        if german is not None:
            fallback[parameter_id] = Text(
                text.name or german.name, text.options or german.options
            )
        else:
            fallback[parameter_id] = text
    return fallback


# --- Devices ---------------------------------------------------------------


@dataclass(frozen=True)
class Hardware:
    """One device behind the module (RBG-TP, LU, WP, ...)."""

    hardware_id: int
    name: str
    model: str
    serial_number: str | None
    software_version: str | None


def parse_hardware(payload: Any, texts: dict[int, Text]) -> list[Hardware]:
    """Parse ``area=hardware``; the model text comes from E_TYPE (5000)."""
    types = texts.get(5000, Text("", {})).options
    devices = []
    for device in _device_blocks(payload):
        if device.get("id") is None:
            continue
        name = str(device.get("name") or device["id"])
        e_type = device.get("eType")
        model = f"{types[e_type]} {name}" if e_type in types else name
        devices.append(
            Hardware(
                hardware_id=device["id"],
                name=name,
                model=model,
                serial_number=device.get("serialNumber") or None,
                software_version=device.get("softwareversion") or None,
            )
        )
    return devices


# Device a parameter reported by several devices is shown on, by hardware
# name. The device with the newest value changes over time, so it can't be
# used for this (for EXTRA_PARAMETERS it is even part of the unique id).
PLACEMENT = {
    5002: ("RBG-TP", "RBG-V/H"),  # Betriebsart
    5016: ("RBG-TP", "RBG-V/H"),  # Raum-Soll
    5064: ("WP",),  # Brauchwasser-Soll
    1054: ("WP",),  # T_BOILER
}


def parameter_owners(payload: Any, hardware: list[Hardware]) -> dict[int, int]:
    """Return {parameterId: hardwareId} of the device to show a parameter on.

    PLACEMENT where a matching device reports the parameter, otherwise the
    device with the newest value.
    """
    owners = newest_owners(payload)
    reported = {
        (device.get("hardwareId"), item.get("parameterId"))
        for device in _device_blocks(payload)
        for item in device.get("values") or []
        if isinstance(item, dict)
    }
    for parameter_id, names in PLACEMENT.items():
        owner = next(
            (
                device.hardware_id
                for name in names
                for device in sorted(hardware, key=lambda device: device.hardware_id)
                if device.name == name and (device.hardware_id, parameter_id) in reported
            ),
            None,
        )
        if owner is not None:
            owners[parameter_id] = owner
    return owners


# --- Parameters ------------------------------------------------------------


@dataclass(frozen=True)
class Parameter:
    """Metadata of one parameter, taken from a Feature object of the module.

    ``hardware_id`` is the owning device, or the environment key (e.g. 100)
    for environment-wide controls such as the operating mode. ``device_id``
    is the device the entity is shown on (None: the module itself).
    ``options`` are the values that can be chosen, ``labels`` the texts of
    all values (also those that can't be chosen).
    """

    hardware_id: int
    parameter_id: int
    key: str
    name: str
    unit: str
    divisor: int
    komma: int
    minimum: int
    maximum: int
    step: int
    options: dict[int, str] = field(default_factory=dict)
    writable: bool = False
    restart: bool = False
    environment: bool = False
    device_id: int | None = None
    labels: dict[int, str] = field(default_factory=dict)

    @property
    def scale(self) -> int:
        return self.divisor * 10**self.komma

    @property
    def is_binary(self) -> bool:
        return set(self.options) == {0, 1}

    def to_native(self, raw: Any) -> float | int | None:
        """Raw module value to display value (like ql.GetValue, untruncated)."""
        if raw is None:
            return None
        return raw / self.scale if self.scale != 1 else raw

    def to_raw(self, value: float) -> int:
        """Display value to raw value, snapped to the step and clamped."""
        raw = round(value * self.scale)
        if self.step > 0:
            raw = self.minimum + round((raw - self.minimum) / self.step) * self.step
        return max(self.minimum, min(self.maximum, raw))

    def option_text(self, raw: Any) -> str | None:
        if raw is None:
            return None
        return self.options.get(raw) or self.labels.get(raw)

    def choices(self, raw: Any) -> dict[int, str]:
        """Options to offer; includes the current value if it can't be chosen.

        E.g. Ferien set on the room panel stays visible as the current mode.
        """
        if raw in self.options or raw not in self.labels:
            return self.options
        return {**self.options, raw: self.labels[raw]}


def _parameter(
    feature: dict[str, Any],
    owner: int,
    texts: dict[int, Text],
    *,
    writable: bool,
    environment: bool = False,
    device_id: int | None = None,
) -> Parameter:
    parameter_id = feature["parameterId"]
    text = texts.get(parameter_id, Text("", {}))
    minimum = int(feature.get("minValue") or 0)
    maximum = int(feature.get("maxValue") or 0)
    options = text.options
    if writable and options:
        # The web UI only offers options in range that are not invalid.
        invalid = set(feature.get("invalidOptionsIndex") or [])
        invalid |= HIDDEN_OPTIONS.get(parameter_id, frozenset())
        allowed = {
            index: option
            for index, option in options.items()
            if minimum <= index <= maximum and index not in invalid
        }
        if allowed:
            options = allowed
        else:
            writable = False
    return Parameter(
        hardware_id=owner,
        parameter_id=parameter_id,
        key=str(feature.get("parameterName") or parameter_id),
        name=text.name or str(feature.get("parameterName") or parameter_id),
        unit=str(feature.get("einheit") or ""),
        divisor=max(int(feature.get("divisor") or 1), 1),
        komma=max(int(feature.get("komma") or 0), 0),
        minimum=minimum,
        maximum=maximum,
        step=max(int(feature.get("schritte") or 1), 1),
        options=options,
        labels=text.options,
        writable=writable,
        restart=bool(feature.get("restarOnChange")),
        environment=environment,
        device_id=device_id,
    )


def build_parameters(
    options_payload: Any,
    environment_payloads: list[Any],
    texts: dict[int, Text],
    owners: dict[int, int] | None = None,
) -> list[Parameter]:
    """Collect the parameters the web UI shows to a user.

    - ``environment_payloads`` (``betriebsart``, ``tempconfig``): environment
      wide controls, written with the environment key as deviceId and shown
      on the device that reports them (``owners``, see parameter_owners).
    - ``options``: per device, everything of the status area (read only) and
      everything editable in the operating area (Betrieb). Settings that are
      also environment controls stay read only here.
    - ``EXTRA_PARAMETERS``: read only, on the device that reports them.
    """
    owners = owners or {}
    parameters: list[Parameter] = []
    seen: set[tuple[int, int]] = set()
    environment_ids: set[int] = set()

    for payload in environment_payloads:
        for environment in payload if isinstance(payload, list) else []:
            for feature in environment.get("value") or []:
                parameter_id = feature.get("parameterId")
                owner = feature.get("hardwareEnvironment") or environment.get("key")
                if parameter_id is None or owner is None:
                    continue
                if parameter_id in DANGEROUS_PARAMETERS or parameter_id in environment_ids:
                    continue
                environment_ids.add(parameter_id)
                parameters.append(
                    _parameter(
                        feature,
                        owner,
                        texts,
                        writable=True,
                        environment=True,
                        device_id=owners.get(parameter_id),
                    )
                )

    for device in _device_blocks(options_payload):
        hardware_id = device.get("hardwareId")
        for feature in device.get("displays") or []:
            parameter_id = feature.get("parameterId")
            if parameter_id is None or parameter_id in DANGEROUS_PARAMETERS:
                continue
            if (hardware_id, parameter_id) in seen:
                continue
            areas = {
                area.get("bereichBit"): area
                for area in feature.get("bereiche") or []
                if area.get("isDisplayEnabled")
            }
            writable = bool(areas.get(BEREICH_BETRIEB, {}).get("isEditEnabled"))
            if not writable and BEREICH_STATUS not in areas:
                continue
            seen.add((hardware_id, parameter_id))
            parameters.append(
                _parameter(
                    feature,
                    hardware_id,
                    texts,
                    writable=writable and parameter_id not in environment_ids,
                    device_id=hardware_id,
                )
            )

    for parameter_id, feature in EXTRA_PARAMETERS.items():
        owner = owners.get(parameter_id)
        if owner is None or (owner, parameter_id) in seen:
            continue
        parameters.append(
            _parameter(
                {"parameterId": parameter_id, **feature},
                owner,
                texts,
                writable=False,
                device_id=owner,
            )
        )

    return parameters


# --- Climate ---------------------------------------------------------------

# WP_BETRIEBSSTATUS (1346) values that heat or cool the rooms.
ROOM_HEATING_STATES = frozenset({1, 3, 4, 6, 7, 8, 9, 12})
ROOM_COOLING_STATES = frozenset({10, 11})


def room_action(raw: Any) -> str | None:
    """Map WP_BETRIEBSSTATUS to "heating", "cooling" or "idle"."""
    if raw is None:
        return None
    if raw in ROOM_HEATING_STATES:
        return "heating"
    if raw in ROOM_COOLING_STATES:
        return "cooling"
    return "idle"


# --- Errors and informations -----------------------------------------------


@dataclass(frozen=True)
class Message:
    """An active fault or information message."""

    hardware_id: int | None
    parameter_id: int
    text: str


def parse_messages(payload: Any, texts: dict[int, Text]) -> list[Message]:
    """Parse ``area=errors`` / ``area=informations``.

    The text is the parameter name. The web UI also shows the option text
    with index 1 ("Ja", "vorhanden"), which adds nothing for an active message.
    """
    messages = []
    for item in _device_blocks(payload):
        parameter_id = item.get("parameterId")
        if parameter_id is None:
            continue
        text = texts.get(parameter_id)
        label = text.name if text is not None and text.name else str(parameter_id)
        messages.append(Message(item.get("hardwareId"), parameter_id, label))
    return messages
