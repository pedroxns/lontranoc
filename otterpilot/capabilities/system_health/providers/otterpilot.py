from __future__ import annotations

from otterpilot.core.eventbus import EventEnvelope
from otterpilot.core.eventbus.bootstrap import build_default_event_bus
from otterpilot.overview.system import build_overview


def collect() -> EventEnvelope:
    overview = build_overview()

    payload = dict(overview)

    payload["overall_severity"] = payload.pop(
        "severity"
    )

    return EventEnvelope(
        capability="system_health",
        connector="otterpilot",
        event_type="system_snapshot",
        resource_id="homelab",
        severity=overview["severity"],
        status=overview["overall_status"],
        message=overview["summary"],
        payload=payload,
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
        "|",
        event.message,
        flush=True,
    )

    publish(event)


if __name__ == "__main__":
    main()
