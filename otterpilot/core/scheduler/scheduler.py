from __future__ import annotations

import time
from typing import Any, Protocol

from otterpilot.core.config import NotConfiguredError, connector_enabled, get_int
from otterpilot.core.registry.executor import ConnectorExecutor
from otterpilot.core.scheduler.models import PollingJob


class JobStatusRecorder(Protocol):
    def record_job_run(self, **fields: Any) -> None:
        ...


def interval_override_key(job: PollingJob) -> str:
    return "POLL_INTERVAL_" + job.job_id.upper().replace("-", "_")


def effective_interval(job: PollingJob) -> int:
    """Intervalo do job, ajustável por `POLL_INTERVAL_<JOB_ID>` (mínimo 10s)."""

    return max(10, get_int(interval_override_key(job), job.interval_seconds))


class PollingScheduler:
    def __init__(
        self,
        executor: ConnectorExecutor,
        jobs: tuple[PollingJob, ...],
        status_recorder: JobStatusRecorder | None = None,
    ) -> None:
        self._executor = executor
        self._jobs = jobs
        self._status_recorder = status_recorder
        self._last_run: dict[str, float] = {}
        self._last_outcome: dict[str, str] = {}

    @property
    def jobs(self) -> tuple[PollingJob, ...]:
        return self._jobs

    def run_job(
        self,
        job: PollingJob,
    ) -> str:
        started = time.monotonic()
        error: str | None = None
        resource_count: int | None = None

        try:
            if not connector_enabled(job.connector_id):
                outcome = "disabled"
            else:
                payload = self._executor.collect_and_publish(
                    connector_id=job.connector_id,
                    capability_id=job.capability_id,
                )
                outcome = "ok"
                resource_count = len(payload) if isinstance(payload, list) else 1

        except NotConfiguredError as exc:
            outcome = "not_configured"
            error = str(exc)

        except Exception as exc:
            outcome = "error"
            error = str(exc)

        finally:
            # Registrado também em falha: o próximo intervalo é respeitado
            # em vez de repetir a coleta a cada tick.
            self._last_run[job.job_id] = time.monotonic()

        duration_ms = round((time.monotonic() - started) * 1000)

        self._log(job, outcome, error)
        self._record(job, outcome, error, duration_ms, resource_count)

        return outcome

    def _log(
        self,
        job: PollingJob,
        outcome: str,
        error: str | None,
    ) -> None:
        previous = self._last_outcome.get(job.job_id)
        self._last_outcome[job.job_id] = outcome

        if outcome == "error":
            print(f"[scheduler] ERRO em {job.job_id}: {error}", flush=True)
        elif outcome != previous and outcome != "ok":
            detail = f": {error}" if error else ""
            print(f"[scheduler] {job.job_id} {outcome}{detail}", flush=True)
        elif outcome == "ok" and previous not in (None, "ok"):
            print(f"[scheduler] {job.job_id} recuperado", flush=True)

    def _record(
        self,
        job: PollingJob,
        outcome: str,
        error: str | None,
        duration_ms: int,
        resource_count: int | None,
    ) -> None:
        if self._status_recorder is None:
            return

        try:
            self._status_recorder.record_job_run(
                job_id=job.job_id,
                connector_id=job.connector_id,
                capability_id=job.capability_id,
                interval_seconds=effective_interval(job),
                outcome=outcome,
                error=error,
                duration_ms=duration_ms,
                resource_count=resource_count,
            )
        except Exception as exc:
            print(f"[scheduler] Falha ao registrar status de {job.job_id}: {exc}", flush=True)

    def run_pending(self) -> None:
        now = time.monotonic()

        for job in self._jobs:
            if not job.enabled:
                continue

            last_run = self._last_run.get(job.job_id)

            if last_run is None or now - last_run >= effective_interval(job):
                self.run_job(job)

    def run_forever(
        self,
        tick_seconds: int = 1,
    ) -> None:
        while True:
            self.run_pending()
            time.sleep(tick_seconds)
