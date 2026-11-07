from __future__ import annotations

from typing import Any

from otterpilot.core.eventbus import EventEnvelope
from otterpilot.core.eventbus.bootstrap import build_default_event_bus
from otterpilot.integrations.homeassistant.client import (
    HomeAssistantClient,
    required_entity,
)


def to_float(
    value: Any,
) -> float | None:
    if value in (
        None,
        "unknown",
        "unavailable",
    ):
        return None

    try:
        return float(
            str(value).replace(",", ".")
        )
    except Exception:
        return None


def normalize_status(
    value: Any,
) -> str:
    if value is None:
        return "unknown"

    return str(value).strip()


def classify_health(
    ups_status: str,
    battery_percent: float | None,
) -> tuple[str, str]:
    normalized = ups_status.lower()

    online_tokens = (
        "ol",
        "online",
        "on line",
    )

    is_online = any(
        token == normalized
        or token in normalized
        for token in online_tokens
    )

    if not is_online:
        return "warning", "warning"

    if (
        battery_percent is not None
        and battery_percent <= 20
    ):
        return "critical", "critical"

    if (
        battery_percent is not None
        and battery_percent <= 40
    ):
        return "warning", "warning"

    return "healthy", "info"


def collect() -> EventEnvelope:
    client = HomeAssistantClient()

    status_entity = required_entity("UPS_STATUS_ENTITY")
    battery_entity = required_entity("UPS_BATTERY_ENTITY")

    status_state = client.get_state(status_entity)
    battery_state = client.get_state(battery_entity)

    ups_status = normalize_status(
        status_state.get("state")
        if status_state
        else None
    )

    battery_percent = to_float(
        battery_state.get("state")
        if battery_state
        else None
    )

    health, severity = classify_health(
        ups_status,
        battery_percent,
    )

    return EventEnvelope(
        capability="ups",
        connector="homeassistant",
        event_type="status_snapshot",
        resource_id="primary_ups",
        severity=severity,
        status=health,
        message="UPS status snapshot",
        payload={
            "ups_status": ups_status,
            "battery_percent": battery_percent,
            "status_entity": status_entity,
            "battery_entity": battery_entity,
        },
    )


def publish(
    event: EventEnvelope,
) -> None:
    bus = build_default_event_bus()
    bus.publish(event)


def main() -> None:
    event = collect()

    print(
        "UPS:",
        event.resource_id,
        "=>",
        event.status,
        "| status:",
        event.payload.get("ups_status"),
        "| battery:",
        event.payload.get("battery_percent"),
        flush=True,
    )

    publish(event)


if __name__ == "__main__":
    main()
