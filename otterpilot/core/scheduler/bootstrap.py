from __future__ import annotations

from otterpilot.core.registry.executor_bootstrap import (
    build_default_executor,
)
from otterpilot.core.scheduler.models import PollingJob
from otterpilot.core.scheduler.scheduler import PollingScheduler


DEFAULT_JOBS = (
    PollingJob(
        job_id="frigate-camera-health",
        connector_id="frigate",
        capability_id="camera_health",
        interval_seconds=60,
    ),
    PollingJob(
        job_id="adguard-dns",
        connector_id="adguard",
        capability_id="dns",
        interval_seconds=60,
    ),
    PollingJob(
        job_id="homeassistant-vehicle",
        connector_id="homeassistant",
        capability_id="vehicle",
        interval_seconds=180,
    ),
    PollingJob(
        job_id="ollama-llm-runtime",
        connector_id="ollama",
        capability_id="llm_runtime",
        interval_seconds=120,
    ),
    PollingJob(
        job_id="homeassistant-ups",
        connector_id="homeassistant",
        capability_id="ups",
        interval_seconds=30,
    ),
    PollingJob(
        job_id="proxmox-host-health",
        connector_id="proxmox",
        capability_id="host_health",
        interval_seconds=60,
    ),
    PollingJob(
        job_id="homeassistant-environment-health",
        connector_id="homeassistant",
        capability_id="environment_health",
        interval_seconds=60,
    ),
    PollingJob(
        job_id="otterpilot-system-health",
        connector_id="otterpilot",
        capability_id="system_health",
        interval_seconds=60,
    ),
    PollingJob(
        job_id="proxmox-virtualization",
        connector_id="proxmox",
        capability_id="virtualization",
        interval_seconds=60,
    ),
)

def build_default_scheduler() -> PollingScheduler:
    return PollingScheduler(
        executor=build_default_executor(),
        jobs=DEFAULT_JOBS,
    )
