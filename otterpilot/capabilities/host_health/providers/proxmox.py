from __future__ import annotations

from otterpilot.core.eventbus import EventEnvelope
from otterpilot.core.eventbus.bootstrap import build_default_event_bus
from otterpilot.integrations.proxmox.client import ProxmoxClient


def percent(
    value: int | float | None,
    maximum: int | float | None,
) -> float | None:
    if value is None or not maximum:
        return None

    return round(
        float(value) / float(maximum) * 100,
        2,
    )


def classify_health(
    status: str,
    cpu_percent: float | None,
    memory_percent: float | None,
    disk_percent: float | None,
) -> tuple[str, str]:
    if status != "online":
        return "offline", "critical"

    if (
        cpu_percent is not None
        and cpu_percent >= 95
    ):
        return "critical", "critical"

    if (
        memory_percent is not None
        and memory_percent >= 95
    ):
        return "critical", "critical"

    if (
        disk_percent is not None
        and disk_percent >= 95
    ):
        return "critical", "critical"

    if (
        cpu_percent is not None
        and cpu_percent >= 85
    ):
        return "warning", "warning"

    if (
        memory_percent is not None
        and memory_percent >= 85
    ):
        return "warning", "warning"

    if (
        disk_percent is not None
        and disk_percent >= 85
    ):
        return "warning", "warning"

    return "healthy", "info"


def build_node_event(
    node: dict,
) -> EventEnvelope:
    cpu_percent = round(
        float(node.get("cpu") or 0) * 100,
        2,
    )

    memory_percent = percent(
        node.get("mem"),
        node.get("maxmem"),
    )

    disk_percent = percent(
        node.get("disk"),
        node.get("maxdisk"),
    )

    status = str(
        node.get("status") or "unknown"
    ).lower()

    health, severity = classify_health(
        status=status,
        cpu_percent=cpu_percent,
        memory_percent=memory_percent,
        disk_percent=disk_percent,
    )

    return EventEnvelope(
        capability="host_health",
        connector="proxmox",
        event_type="host_snapshot",
        resource_id=node.get("node"),
        severity=severity,
        status=health,
        message=(
            f"Proxmox host health: "
            f"{node.get('node')}"
        ),
        payload={
            "node": node.get("node"),
            "proxmox_status": status,

            "cpu_percent": cpu_percent,
            "cpu_threads": node.get("maxcpu"),

            "memory_used_bytes": node.get("mem"),
            "memory_total_bytes": node.get("maxmem"),
            "memory_percent": memory_percent,

            "disk_used_bytes": node.get("disk"),
            "disk_total_bytes": node.get("maxdisk"),
            "disk_percent": disk_percent,

            "uptime_seconds": node.get("uptime"),
        },
    )


def collect() -> list[EventEnvelope]:
    client = ProxmoxClient()

    nodes = client.nodes()

    return [
        build_node_event(node)
        for node in nodes
    ]


def publish(
    events: list[EventEnvelope],
) -> None:
    bus = build_default_event_bus()

    for event in events:
        bus.publish(event)


def main() -> None:
    events = collect()

    for event in events:
        print(
            event.resource_id,
            "=>",
            event.status,
            "| CPU:",
            event.payload.get("cpu_percent"),
            "| RAM:",
            event.payload.get("memory_percent"),
            "| Disk:",
            event.payload.get("disk_percent"),
            flush=True,
        )

    publish(events)


if __name__ == "__main__":
    main()
