from __future__ import annotations
import yaml

from otterpilot.core.config import config_path

from otterpilot.core.eventbus import EventEnvelope
from otterpilot.core.eventbus.bootstrap import build_default_event_bus
from otterpilot.integrations.proxmox.client import ProxmoxClient

def load_workload_policy() -> dict:
    config_file = config_path("proxmox.yaml")

    with config_file.open(
        "r",
        encoding="utf-8",
    ) as f:
        config = yaml.safe_load(f) or {}

    proxmox_config = config.get(
        "proxmox",
        {},
    )

    workloads = proxmox_config.get(
        "workloads",
        {},
    )

    return workloads

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


def classify_guest(
    guest_type: str,
    proxmox_status: str,
    cpu_percent: float | None,
    memory_percent: float | None,
    disk_percent: float | None,
) -> tuple[str, str]:
    if proxmox_status == "stopped":
        return "stopped", "info"

    if proxmox_status != "running":
        return "unknown", "warning"

    #
    # CPU: útil tanto para QEMU quanto para LXC.
    #
    if (
        cpu_percent is not None
        and cpu_percent >= 95
    ):
        return "warning", "warning"

    #
    # LXC: memória e filesystem representam bem
    # a pressão real do container.
    #
    if guest_type == "lxc":
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

def apply_expectation(
    current_status: str,
    current_severity: str,
    proxmox_status: str,
    expected_state: str | None,
    importance: str,
) -> tuple[str, str]:
    if expected_state is None:
        return current_status, current_severity

    if proxmox_status == expected_state:
        return current_status, current_severity

    if (
        proxmox_status == "stopped"
        and expected_state == "running"
    ):
        severity = (
            "critical"
            if importance == "critical"
            else "warning"
        )

        return "unexpected_stopped", severity

    if (
        proxmox_status == "running"
        and expected_state == "stopped"
    ):
        return "unexpected_running", "warning"

    return "unexpected_state", "warning"

def build_guest_event(
    guest: dict,
    workloads: dict,
) -> EventEnvelope:
    guest_type = str(
        guest.get("type") or "unknown"
    ).lower()

    vmid = guest.get("vmid")

    resource_id = (
        f"{guest_type}/{vmid}"
        if vmid is not None
        else None
    )

    cpu_percent = round(
        float(guest.get("cpu") or 0) * 100,
        2,
    )

    memory_percent = percent(
        guest.get("mem"),
        guest.get("maxmem"),
    )

    disk_percent = percent(
        guest.get("disk"),
        guest.get("maxdisk"),
    )

    proxmox_status = str(
        guest.get("status") or "unknown"
    ).lower()

    workload_policy = (
        workloads.get(resource_id, {})
        if resource_id
        else {}
    )

    expected_state = workload_policy.get(
        "expected_state"
    )

    importance = normalize_importance(
    workload_policy.get("importance")
    )

    state_matches_expectation = (
        proxmox_status == expected_state
        if expected_state is not None
        else None
    )

    # 1. Classificação técnica do guest
    health, severity = classify_guest(
        guest_type=guest_type,
        proxmox_status=proxmox_status,
        cpu_percent=cpu_percent,
        memory_percent=memory_percent,
        disk_percent=disk_percent,
    )

    # 2. Aplica a política de estado esperado
    health, severity = apply_expectation(
        current_status=health,
        current_severity=severity,
        proxmox_status=proxmox_status,
        expected_state=expected_state,
        importance=importance,
    )
def normalize_importance(
    value: str | None,
) -> str:
    importance = str(
        value or "warning"
    ).lower()

    if importance not in (
        "critical",
        "warning",
    ):
        return "warning"

    return importance


def build_guest_event(
    guest: dict,
    workloads: dict,
) -> EventEnvelope:
    guest_type = str(
        guest.get("type") or "unknown"
    ).lower()

    vmid = guest.get("vmid")

    resource_id = (
        f"{guest_type}/{vmid}"
        if vmid is not None
        else None
    )

    cpu_percent = round(
        float(guest.get("cpu") or 0) * 100,
        2,
    )

    memory_percent = percent(
        guest.get("mem"),
        guest.get("maxmem"),
    )

    disk_percent = percent(
        guest.get("disk"),
        guest.get("maxdisk"),
    )

    proxmox_status = str(
        guest.get("status") or "unknown"
    ).lower()

    workload_policy = (
        workloads.get(resource_id, {})
        if resource_id
        else {}
    )

    expected_state = workload_policy.get(
        "expected_state"
    )

    importance = normalize_importance(
        workload_policy.get("importance")
    )

    state_matches_expectation = (
        proxmox_status == expected_state
        if expected_state is not None
        else None
    )

    # 1. Classificação técnica do guest
    health, severity = classify_guest(
        guest_type=guest_type,
        proxmox_status=proxmox_status,
        cpu_percent=cpu_percent,
        memory_percent=memory_percent,
        disk_percent=disk_percent,
    )

    # 2. Aplica a política de estado esperado
    health, severity = apply_expectation(
        current_status=health,
        current_severity=severity,
        proxmox_status=proxmox_status,
        expected_state=expected_state,
        importance=importance,
    )

    return EventEnvelope(
        capability="virtualization",
        connector="proxmox",
        event_type="guest_snapshot",
        resource_id=resource_id,
        severity=severity,
        status=health,
        message=(
            f"Proxmox guest health: "
            f"{guest.get('name') or resource_id}"
        ),
        payload={
            "vmid": vmid,
            "guest_type": guest_type,
            "name": guest.get("name"),
            "node": guest.get("node"),

            "proxmox_status": proxmox_status,
            "expected_state": expected_state,
            "state_matches_expectation": (
                state_matches_expectation
            ),
            "importance": importance,

            "cpu_percent": cpu_percent,
            "cpu_threads": guest.get("maxcpu"),

            "memory_used_bytes": guest.get("mem"),
            "memory_total_bytes": guest.get("maxmem"),
            "memory_percent": memory_percent,

            "disk_used_bytes": guest.get("disk"),
            "disk_total_bytes": guest.get("maxdisk"),
            "disk_percent": disk_percent,

            "uptime_seconds": guest.get("uptime"),

            "template": bool(
                guest.get("template", 0)
            ),
        },
    )

def collect() -> list[EventEnvelope]:
    client = ProxmoxClient()

    workloads = load_workload_policy()

    resources = client.cluster_resources()

    guests = [
        resource
        for resource in resources
        if resource.get("type") in (
            "qemu",
            "lxc",
        )
    ]

    return [
        build_guest_event(
            guest,
            workloads,
        )
        for guest in guests
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
            "|",
            event.payload.get("name"),
            "| node:",
            event.payload.get("node"),
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
