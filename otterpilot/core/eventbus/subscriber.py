from __future__ import annotations

from typing import Protocol, runtime_checkable

from otterpilot.core.eventbus.models import EventEnvelope


@runtime_checkable
class EventSubscriber(Protocol):
    subscriber_id: str

    def handle(self, event: EventEnvelope) -> None:
        ...
