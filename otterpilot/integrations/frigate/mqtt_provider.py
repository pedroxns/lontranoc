from __future__ import annotations

import json

from otterpilot.core.config import get_env
from otterpilot.core.eventbus import EventEnvelope
from otterpilot.core.eventbus.bootstrap import build_default_event_bus
from otterpilot.integrations.mqtt.client import run_subscriber

PROVIDER_ID = "frigate"
PROVIDER_NAME = "Frigate"

PROVIDES_CAPABILITIES = (
    "object_detection",
    "camera_health",
)

EVENT_BUS = build_default_event_bus()


def topic_prefix() -> str:
    return (get_env("FRIGATE_MQTT_PREFIX", "frigate") or "frigate").strip("/")


def topics() -> list[tuple[str, int]]:
    prefix = topic_prefix()

    return [
        (f"{prefix}/events", 0),
        (f"{prefix}/+/motion", 0),
        (f"{prefix}/+/person", 0),
        (f"{prefix}/+/dog", 0),
    ]


def build_object_detection_event(
    topic: str,
    data: dict,
) -> EventEnvelope:
    parts = topic.split("/")

    camera = (
        parts[1]
        if len(parts) >= 3
        else data.get("camera", "unknown")
    )

    event_type = "mqtt_event"

    if topic == f"{topic_prefix()}/events":
        event_type = "object_event"
    elif topic.endswith("/motion"):
        event_type = "motion"
    elif topic.endswith("/person"):
        event_type = "person_state"
    elif topic.endswith("/dog"):
        event_type = "dog_state"

    fields = {
        "mqtt_topic": topic,
        "camera": camera,
        "raw": data,
    }

    if isinstance(data, dict):
        after = data.get("after", {})
        before = data.get("before", {})

        fields.update(
            {
                "frigate_type": data.get("type"),
                "id": after.get("id") or before.get("id"),
                "label": after.get("label") or before.get("label"),
                "score": after.get("score"),
                "top_score": after.get("top_score"),
                "false_positive": after.get("false_positive"),
                "stationary": after.get("stationary"),
                "start_time": after.get("start_time"),
                "end_time": after.get("end_time"),
                "has_clip": after.get("has_clip"),
                "has_snapshot": after.get("has_snapshot"),
            }
        )

        if after.get("camera"):
            fields["camera"] = after.get("camera")

    resource_id = fields.get("id") or fields.get("camera")

    return EventEnvelope(
        capability="object_detection",
        connector="frigate",
        event_type=event_type,
        resource_id=resource_id,
        severity="info",
        status="ok",
        message=f"Frigate MQTT event: {event_type}",
        payload=fields,
    )

def on_message(client, msg):
    payload_text = msg.payload.decode(
        errors="replace"
    )

    try:
        data = json.loads(payload_text)
    except Exception:
        data = {
            "raw_payload": payload_text
        }

    event = build_object_detection_event(
        msg.topic,
        data,
    )

    EVENT_BUS.publish(event)


def main():
    run_subscriber("frigate-mqtt", topics, on_message)


if __name__ == "__main__":
    main()