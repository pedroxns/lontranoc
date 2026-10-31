from __future__ import annotations

from pathlib import Path

from otterpilot.core.eventbus import INVENTORY_EVENT_TYPE, EventEnvelope
from otterpilot.state.store import StateStore


STATEFUL_EVENT_TYPES = frozenset({
    "snapshot",
    "host_snapshot",
    "status_snapshot",
    "environment_snapshot",
    "bridge_snapshot",
    "camera_health",
    "system_snapshot",
    "guest_snapshot",
    # Falha de coleta de um recurso conhecido também é o estado atual dele.
    "status_error",
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
        if event.event_type == INVENTORY_EVENT_TYPE:
            self.store.retain(
                connector=event.connector,
                capability=event.capability,
                resource_ids=list(event.payload.get("resource_ids", [])),
            )
            return

        if event.event_type not in STATEFUL_EVENT_TYPES:
            return

        if not event.resource_id:
            return

        self.store.upsert(event)
