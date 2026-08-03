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
)


def build_default_scheduler() -> PollingScheduler:
    return PollingScheduler(
        executor=build_default_executor(),
        jobs=DEFAULT_JOBS,
    )
