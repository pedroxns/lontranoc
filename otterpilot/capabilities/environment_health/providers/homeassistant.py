from __future__ import annotations

import requests

from otterpilot.core.config import get_env
from otterpilot.core.eventbus import EventEnvelope
from otterpilot.core.eventbus.bootstrap import build_default_event_bus


HA_URL = (get_env("HA_URL", required=True) or "").rstrip("/")
HA_TOKEN = get_env("HA_TOKEN", required=True)

RACK_TEMP_ENTITY = get_env(
    "RACK_TEMP_ENTITY",
    "sensor.clima_servidor_temperature",
)


def get_state(
    entity_id: str,
) -> dict:
    response = requests.get(
        f"{HA_URL}/api/states/{entity_id}",
        headers={
            "Authorization": f"Bearer {HA_TOKEN}",
            "Content-Type": "application/json",
        },
        timeout=10,
    )

    response.raise_for_status()

    return response.json()


def classify_temperature(
    temperature_c: float,
) -> tuple[str, str]:
    if temperature_c >= 50:
        return "critical", "critical"

    if temperature_c >= 45:
        return "warning", "warning"

    return "healthy", "info"


def collect() -> EventEnvelope:
    state = get_state(RACK_TEMP_ENTITY)

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
                "entity_id": RACK_TEMP_ENTITY,
            },
        )

    temperature_c = float(raw_value)

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
            "entity_id": RACK_TEMP_ENTITY,
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
