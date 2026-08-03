from __future__ import annotations

import time

from otterpilot.core.registry.executor import ConnectorExecutor
from otterpilot.core.scheduler.models import PollingJob


class PollingScheduler:
    def __init__(
        self,
        executor: ConnectorExecutor,
        jobs: tuple[PollingJob, ...],
    ) -> None:
        self._executor = executor
        self._jobs = jobs
        self._last_run: dict[str, float] = {}

    def run_job(
        self,
        job: PollingJob,
    ) -> None:
        print(
            f"[scheduler] Executando "
            f"{job.connector_id}/{job.capability_id}",
            flush=True,
        )

        self._executor.collect_and_publish(
            connector_id=job.connector_id,
            capability_id=job.capability_id,
        )

        self._last_run[job.job_id] = time.monotonic()

    def run_pending(self) -> None:
        now = time.monotonic()

        for job in self._jobs:
            if not job.enabled:
                continue

            last_run = self._last_run.get(job.job_id)

            if (
                last_run is None
                or now - last_run >= job.interval_seconds
            ):
                try:
                    self.run_job(job)
                except Exception as error:
                    print(
                        f"[scheduler] ERRO em "
                        f"{job.job_id}: {error}",
                        flush=True,
                    )

    def run_forever(
        self,
        tick_seconds: int = 1,
    ) -> None:
        while True:
            self.run_pending()
            time.sleep(tick_seconds)
