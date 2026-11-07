from __future__ import annotations

from otterpilot.core.config import NotConfiguredError
from otterpilot.core.scheduler.models import PollingJob
from otterpilot.core.scheduler.scheduler import PollingScheduler, effective_interval


class FakeExecutor:
    def __init__(self, behavior):
        self.behavior = behavior
        self.calls = 0

    def collect_and_publish(self, connector_id, capability_id):
        self.calls += 1
        return self.behavior()


def boom():
    raise RuntimeError("No route to host")


def not_configured():
    raise NotConfiguredError("PROXMOX_URL")


JOB = PollingJob(job_id="proxmox-host-health", connector_id="proxmox",
                 capability_id="host_health", interval_seconds=60)


def test_failed_job_waits_for_next_interval(store):
    executor = FakeExecutor(boom)
    scheduler = PollingScheduler(executor, (JOB,), status_recorder=store)

    for _ in range(5):
        scheduler.run_pending()

    assert executor.calls == 1
    [row] = store.list_job_status()
    assert row["outcome"] == "error"
    assert "No route to host" in row["last_error"]


def test_not_configured_is_not_an_error(store):
    scheduler = PollingScheduler(FakeExecutor(not_configured), (JOB,), status_recorder=store)
    assert scheduler.run_job(JOB) == "not_configured"
    assert store.list_job_status()[0]["consecutive_failures"] == 0


def test_disabled_connector_is_skipped(store, monkeypatch):
    monkeypatch.setenv("PROXMOX_ENABLED", "false")
    executor = FakeExecutor(lambda: [])
    scheduler = PollingScheduler(executor, (JOB,), status_recorder=store)

    assert scheduler.run_job(JOB) == "disabled"
    assert executor.calls == 0


def test_interval_override(monkeypatch):
    assert effective_interval(JOB) == 60
    monkeypatch.setenv("POLL_INTERVAL_PROXMOX_HOST_HEALTH", "120")
    assert effective_interval(JOB) == 120
    monkeypatch.setenv("POLL_INTERVAL_PROXMOX_HOST_HEALTH", "1")
    assert effective_interval(JOB) == 10
