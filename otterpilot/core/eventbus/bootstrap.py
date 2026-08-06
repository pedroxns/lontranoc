from __future__ import annotations

from otterpilot.core.eventbus import EventBus
from otterpilot.knowledge.providers.openobserve.subscribers.eventbus import (
    OpenObserveEventSubscriber,
)
from otterpilot.state.subscriber import StateStoreSubscriber


def build_default_event_bus() -> EventBus:
    bus = EventBus()

    bus.subscribe(
        OpenObserveEventSubscriber()
    )

    bus.subscribe(
        StateStoreSubscriber()
    )

    return bus
