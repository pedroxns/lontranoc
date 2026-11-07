from __future__ import annotations

from otterpilot.core.eventbus import EventEnvelope
from otterpilot.core.eventbus.bootstrap import build_default_event_bus
from otterpilot.integrations.homeassistant.client import (
    HomeAssistantClient,
    required_entity,
)


def classify_temperature(
    temperature_c: float,
) -> tuple[str, str]:
    if temperature_c >= 50:
        return "critical", "critical"

    if temperature_c >= 45:
        return "warning", "warning"

    return "healthy", "info"


def collect() -> EventEnvelope:
    client = HomeAssistantClient()
    entity_id = required_entity("RACK_TEMP_ENTITY")

    state = client.get_state(entity_id) or {}

    raw_value = state.get("state")

    if raw_value in (
        None,
        "unknown",
        "unavailable",
    ):
        return EventEnvelope(
            capability="environment_health",
            connector="homeassistant",
            event_type="environment_snapshot",
            resource_id="rack",
            severity="warning",
            status="unknown",
            message="Rack temperature unavailable",
            payload={
                "temperature_c": None,
                "entity_id": entity_id,
            },
        )

    try:
        temperature_c = float(str(raw_value).replace(",", "."))
    except ValueError:
        return EventEnvelope(
            capability="environment_health",
            connector="homeassistant",
            event_type="environment_snapshot",
            resource_id="rack",
            severity="warning",
            status="unknown",
            message=f"Rack temperature inválida: {raw_value}",
            payload={
                "temperature_c": None,
                "entity_id": entity_id,
            },
        )

    health, severity = classify_temperature(
        temperature_c
    )

    return EventEnvelope(
        capability="environment_health",
        connector="homeassistant",
        event_type="environment_snapshot",
        resource_id="rack",
        severity=severity,
        status=health,
        message="Rack environment health",
        payload={
            "temperature_c": temperature_c,
            "entity_id": entity_id,
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
        event.resource_id,
        "=>",
        event.status,
        "|",
        event.severity,
        "| Temperature:",
        event.payload.get("temperature_c"),
        "°C",
        flush=True,
    )

    publish(event)


if __name__ == "__main__":
    main()
