from __future__ import annotations

from datetime import datetime, timedelta, timezone

from otterpilot.core.eventbus import EventEnvelope
from otterpilot.overview.system import build_overview


def add(store, resource_id, status="healthy", capability="virtualization", age_seconds=0):
    store.upsert(
        EventEnvelope(
            capability=capability,
            connector="proxmox",
            event_type="guest_snapshot",
            resource_id=resource_id,
            status=status,
            timestamp=datetime.now(timezone.utc) - timedelta(seconds=age_seconds),
        )
    )


def test_empty(store):
    assert build_overview(store)["summary"] == "Nenhum recurso monitorado disponível."


def test_healthy_and_neutral(store):
    add(store, "lxc/100")
    add(store, "lxc/101", status="stopped")

    overview = build_overview(store)
    assert overview["overall_status"] == "healthy"
    assert overview["problem_count"] == 0


def test_summary_is_bounded_and_separates_stale(store):
    for n in range(8):
        add(store, f"lxc/{n}", status="warning")

    add(store, "lxc/old", age_seconds=3600)

    overview = build_overview(store)
    assert overview["overall_status"] == "degraded"
    assert overview["stale_count"] == 1
    assert "8 alerta(s)" in overview["summary"]
    assert "e mais 3" in overview["summary"]
    assert "1 sem atualização recente: lxc/old" in overview["summary"]


def test_critical_impact_by_capability(store):
    add(store, "pve", status="offline", capability="host_health")
    assert build_overview(store)["overall_status"] == "critical"
