from __future__ import annotations

from otterpilot.core.eventbus import EventEnvelope
from otterpilot.core.registry.executor import build_inventory_event
from otterpilot.state.subscriber import StateStoreSubscriber


def snapshot(resource_id: str, status: str = "healthy") -> EventEnvelope:
    return EventEnvelope(
        capability="virtualization",
        connector="proxmox",
        event_type="guest_snapshot",
        resource_id=resource_id,
        status=status,
        payload={"name": resource_id},
    )


def test_upsert_and_get(store):
    store.upsert(snapshot("lxc/100"))
    store.upsert(snapshot("lxc/100", "warning"))

    state = store.get(connector="proxmox", capability="virtualization", resource_id="lxc/100")
    assert state["status"] == "warning"
    assert state["payload"] == {"name": "lxc/100"}


def test_inventory_event_prunes_missing_resources(tmp_path):
    subscriber = StateStoreSubscriber(tmp_path / "state.db")

    for resource_id in ("lxc/100", "lxc/900", "qemu/210"):
        subscriber.handle(snapshot(resource_id))

    current = [snapshot("lxc/100"), snapshot("qemu/210")]
    subscriber.handle(build_inventory_event("proxmox", "virtualization", current))

    remaining = [state["resource_id"] for state in subscriber.store.list_all()]
    assert remaining == ["lxc/100", "qemu/210"]


def test_inventory_only_touches_its_capability(tmp_path):
    subscriber = StateStoreSubscriber(tmp_path / "state.db")
    subscriber.handle(snapshot("lxc/100"))
    subscriber.handle(
        EventEnvelope(
            capability="host_health",
            connector="proxmox",
            event_type="host_snapshot",
            resource_id="pve",
        )
    )

    subscriber.handle(build_inventory_event("proxmox", "virtualization", []))

    assert [state["resource_id"] for state in subscriber.store.list_all()] == ["pve"]


def test_job_status_tracks_failures(store):
    common = dict(job_id="j", connector_id="c", capability_id="x", interval_seconds=60)

    store.record_job_run(**common, outcome="error", error="boom")
    store.record_job_run(**common, outcome="error", error="boom 2")
    [row] = store.list_job_status()
    assert row["consecutive_failures"] == 2
    assert row["last_error"] == "boom 2"
    assert row["last_success_at"] is None

    store.record_job_run(**common, outcome="ok", resource_count=3)
    [row] = store.list_job_status()
    assert row["consecutive_failures"] == 0
    assert row["last_error"] is None
    assert row["last_success_at"] is not None
    assert row["last_error_at"] is not None
    assert row["resource_count"] == 3


def test_component_status_keeps_last_message(store):
    store.report_component("zigbee2mqtt", "connected", message_seen=True)
    store.report_component("zigbee2mqtt", "disconnected")

    [row] = store.list_component_status()
    assert row["status"] == "disconnected"
    assert row["last_message_at"] is not None


def test_delete(store):
    store.upsert(snapshot("lxc/100"))
    assert store.delete(connector="proxmox", capability="virtualization", resource_id="lxc/100")
    assert not store.delete(connector="proxmox", capability="virtualization", resource_id="lxc/100")
