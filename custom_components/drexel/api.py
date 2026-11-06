"""Pure helpers for the Aerosmart Fernwartungsmodul values endpoint."""

from __future__ import annotations

from typing import Any

DEFAULT_PATH = "/dw"
QUERY = "area=values"


def build_url(host: str, port: int, path: str = DEFAULT_PATH) -> str:
    """Build the values URL from the user config."""
    host = host.strip().rstrip("/")
    if not host.startswith(("http://", "https://")):
        host = f"http://{host}"
    path = (path.strip() or DEFAULT_PATH)
    if not path.startswith("/"):
        path = f"/{path}"
    return f"{host}:{port}{path}?{QUERY}"


def parse_values(payload: Any) -> dict[int, Any]:
    """Flatten ``[{"value": [{"values": [...]}]}]`` into {parameterId: currentValue}."""
    try:
        groups = payload[0]["value"]
        values = {
            item["parameterId"]: item.get("currentValue")
            for group in groups
            for item in group.get("values") or []
            if item.get("parameterId") is not None
        }
    except (KeyError, IndexError, TypeError, AttributeError) as err:
        raise ValueError("Unerwartete Antwort vom Aerosmart-Fernwartungsmodul") from err
    return values


def convert_value(
    value: Any, *, scale: float = 1, states: dict[int, str] | None = None
) -> Any:
    """Turn a raw currentValue into a sensor state."""
    if value is None:
        return None
    if states is not None:
        return states.get(value, "Unbekannt")
    return value / scale if scale != 1 else value
