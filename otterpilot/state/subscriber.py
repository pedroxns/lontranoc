from __future__ import annotations

from pathlib import Path

from otterpilot.core.eventbus import EventEnvelope
from otterpilot.state.store import StateStore


STATEFUL_EVENT_TYPES = frozenset({
    "snapshot",
    "host_snapshot",
    "status_snapshot",
    "environment_snapshot",
    "bridge_snapshot",
    "camera_health",
    "system_snapshot",
})


class StateStoreSubscriber:
    subscriber_id = "state_store"

    def __init__(
        self,
        database_path: str | Path | None = None,
    ) -> None:
        if database_path is None:
            from otterpilot.state import DEFAULT_STATE_DB

            database_path = DEFAULT_STATE_DB

        self.store = StateStore(database_path)

    def handle(
        self,
        event: EventEnvelope,
    ) -> None:
        if event.event_type not in STATEFUL_EVENT_TYPES:
            return

        if not event.resource_id:
            return

        self.store.upsert(event)
