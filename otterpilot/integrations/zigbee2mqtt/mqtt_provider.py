from __future__ import annotations

import json
from typing import Any

import paho.mqtt.client as mqtt

from otterpilot.core.config import get_env
from otterpilot.core.eventbus import EventEnvelope
from otterpilot.core.eventbus.bootstrap import build_default_event_bus


MQTT_HOST = get_env("MQTT_HOST", required=True)
MQTT_PORT = int(
    get_env("MQTT_PORT", "1883") or "1883"
)

INSTANCES = (
    "z2m1",
    "z2m2",
)

TOPICS = tuple(
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


def _instance_from_topic(
    topic: str,
) -> str:
    return topic.split("/", 1)[0]


def _subtopic_from_topic(
    topic: str,
) -> str:
    parts = topic.split("/")
    return parts[2] if len(parts) >= 3 else ""


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


def on_connect(
    client,
    userdata,
    flags,
    reason_code,
    properties,
):
    for topic, qos in TOPICS:
        client.subscribe(
            topic,
            qos=qos,
        )

    print(
        "OtterPilot Zigbee2MQTT "
        "subscriber conectado.",
        flush=True,
    )


def on_message(
    client,
    userdata,
    msg,
):
    instance = _instance_from_topic(
        msg.topic
    )

    subtopic = _subtopic_from_topic(
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
    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2
    )

    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(
        MQTT_HOST,
        MQTT_PORT,
        60,
    )

    client.loop_forever()


if __name__ == "__main__":
    main()
