from __future__ import annotations

from datetime import date, datetime, time
from pathlib import Path
from typing import Any


def make_json_safe(value: Any) -> Any:
    """Converte recursivamente valores Python para tipos serializáveis em JSON."""

    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, (datetime, date, time)):
        return value.isoformat()

    if isinstance(value, Path):
        return str(value)

    if isinstance(value, dict):
        return {
            str(key): make_json_safe(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple, set)):
        return [make_json_safe(item) for item in value]

    if hasattr(value, "model_dump"):
        return make_json_safe(value.model_dump())

    return str(value)
