from __future__ import annotations

import json
from typing import Any

from otterpilot.core.config import get_env
from otterpilot.core.eventbus import EventEnvelope
from otterpilot.core.eventbus.bootstrap import build_default_event_bus
from otterpilot.integrations.mqtt.client import run_subscriber


def configured_instances() -> tuple[str, ...]:
    """Base topics das instâncias (`ZIGBEE2MQTT_BASE_TOPICS`, separados por vírgula)."""

    raw = get_env("ZIGBEE2MQTT_BASE_TOPICS", "zigbee2mqtt") or "zigbee2mqtt"

    return tuple(
        item.strip().strip("/")
        for item in raw.split(",")
        if item.strip().strip("/")
    )


INSTANCES = configured_instances()


def topics() -> tuple[tuple[str, int], ...]:
    return tuple(
        (f"{instance}/bridge/{topic}", 0)
        for instance in INSTANCES
        for topic in (
            "state",
            "health",
            "info",
            "logging",
        )
    )


_state: dict[str, dict[str, Any]] = {
    instance: {}
    for instance in INSTANCES
}


def _split_topic(
    topic: str,
) -> tuple[str, str]:
    """Separa `<base>/bridge/<subtopic>`; base topics podem conter barras."""

    base, separator, subtopic = topic.rpartition("/bridge/")

    if not separator:
        return "", ""

    return base, subtopic


def _parse_json(
    payload: bytes,
) -> Any:
    text = payload.decode(
        "utf-8",
        errors="replace",
    )

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def _build_snapshot(
    instance: str,
) -> EventEnvelope:
    data = _state[instance]

    state = data.get("state", {})
    health = data.get("health", {})
    info = data.get("info", {})

    online = (
        state.get("state") == "online"
        if isinstance(state, dict)
        else False
    )

    mqtt_health = health.get(
        "mqtt",
        {},
    )

    mqtt_connected = mqtt_health.get(
        "connected"
    )

    restart_required = info.get(
        "restart_required"
    )

    status = "healthy"
    severity = "info"

    if not online:
        status = "offline"
        severity = "critical"

    elif mqtt_connected is False:
        status = "degraded"
        severity = "warning"

    elif restart_required is True:
        status = "degraded"
        severity = "warning"

    devices = health.get(
        "devices",
        {},
    )

    coordinator = info.get(
        "coordinator",
        {},
    )

    network = info.get(
        "network",
        {},
    )

    process = health.get(
        "process",
        {},
    )

    os_health = health.get(
        "os",
        {},
    )

    return EventEnvelope(
        capability="zigbee_health",
        connector="zigbee2mqtt",
        event_type="bridge_snapshot",
        resource_id=instance,
        severity=severity,
        status=status,
        message=(
            f"Zigbee2MQTT bridge health: "
            f"{instance}"
        ),
        payload={
            "instance": instance,
            "online": online,

            "version": info.get(
                "version"
            ),
            "restart_required": (
                restart_required
            ),
            "permit_join": info.get(
                "permit_join"
            ),

            "coordinator_type": (
                coordinator.get("type")
            ),
            "coordinator_ieee": (
                coordinator.get(
                    "ieee_address"
                )
            ),

            "channel": network.get(
                "channel"
            ),
            "pan_id": network.get(
                "pan_id"
            ),

            "mqtt_connected": (
                mqtt_connected
            ),
            "mqtt_queued": (
                mqtt_health.get("queued")
            ),
            "mqtt_published": (
                mqtt_health.get(
                    "published"
                )
            ),
            "mqtt_received": (
                mqtt_health.get(
                    "received"
                )
            ),

            "process_uptime_seconds": (
                process.get("uptime_sec")
            ),
            "process_memory_mb": (
                process.get(
                    "memory_used_mb"
                )
            ),

            "os_memory_percent": (
                os_health.get(
                    "memory_percent"
                )
            ),

            "device_count": len(
                devices
            ),
        },
    )


def _build_log_event(
    instance: str,
    payload: dict[str, Any],
) -> EventEnvelope:
    level = str(
        payload.get(
            "level",
            "info",
        )
    ).lower()

    message = str(
        payload.get(
            "message",
            "",
        )
    )

    severity = "info"
    status = "healthy"
    error_type = None

    if level == "error":
        severity = "error"
        status = "degraded"

    elif level == "warning":
        severity = "warning"
        status = "degraded"

    if "ASH_NCP_FATAL_ERROR" in message:
        error_type = "ash_ncp_fatal_error"
        severity = "critical"
        status = "critical"

    elif "HOST_FATAL_ERROR" in message:
        error_type = "host_fatal_error"
        severity = "critical"
        status = "critical"

    return EventEnvelope(
        capability="zigbee_health",
        connector="zigbee2mqtt",
        event_type="coordinator_error",
        resource_id=instance,
        severity=severity,
        status=status,
        message=message,
        payload={
            "instance": instance,
            "level": level,
            "error_type": error_type,
        },
    )


def on_message(
    client,
    msg,
):
    instance, subtopic = _split_topic(
        msg.topic
    )

    payload = _parse_json(
        msg.payload
    )

    if instance not in _state:
        return

    bus = build_default_event_bus()

    if subtopic == "logging":
        if not isinstance(
            payload,
            dict,
        ):
            return

        level = str(
            payload.get(
                "level",
                "info",
            )
        ).lower()

        if level not in (
            "warning",
            "error",
        ):
            return

        event = _build_log_event(
            instance,
            payload,
        )

        bus.publish(event)
        return

    if isinstance(
        payload,
        dict,
    ):
        _state[instance][
            subtopic
        ] = payload

    if all(
        key in _state[instance]
        for key in (
            "state",
            "health",
            "info",
        )
    ):
        event = _build_snapshot(
            instance
        )

        bus.publish(event)


def main() -> None:
    run_subscriber("zigbee2mqtt", topics, on_message)


if __name__ == "__main__":
    main()
