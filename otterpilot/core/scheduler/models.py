from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PollingJob:
    job_id: str
    connector_id: str
    capability_id: str
    interval_seconds: int
    enabled: bool = True
