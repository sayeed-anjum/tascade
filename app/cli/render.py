"""Human-readable rendering of API responses, used when ``--json`` is absent."""

from __future__ import annotations

import json
from typing import Any

_SUMMARY_FIELDS = ("short_id", "id", "name", "title", "state", "status")


def render(obj: Any) -> str:
    if isinstance(obj, dict) and isinstance(obj.get("items"), list):
        items = obj["items"]
        if not items:
            return "(no items)"
        return "\n".join(_summarise(item) for item in items)
    if isinstance(obj, list):
        return "\n".join(_summarise(item) for item in obj) if obj else "(no items)"
    if isinstance(obj, dict):
        return _key_values(obj)
    if obj is None:
        return "(no content)"
    return str(obj)


def _summarise(item: Any) -> str:
    if not isinstance(item, dict):
        return str(item)
    parts = [str(item[field]) for field in _SUMMARY_FIELDS if item.get(field) is not None]
    return "  ".join(parts) if parts else _compact(item)


def _key_values(obj: dict[str, Any]) -> str:
    width = max((len(key) for key in obj), default=0)
    return "\n".join(f"{key + ':':<{width + 1}} {_scalar(value)}" for key, value in obj.items())


def _scalar(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return _compact(value)
    return "" if value is None else str(value)


def _compact(value: Any) -> str:
    return json.dumps(value, default=str)
