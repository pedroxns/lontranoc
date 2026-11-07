from __future__ import annotations

from otterpilot.core.eventbus import EventBus
from otterpilot.knowledge.providers.openobserve.ingest import (
    is_configured as openobserve_configured,
)
from otterpilot.knowledge.providers.openobserve.subscribers.eventbus import (
    OpenObserveEventSubscriber,
)
from otterpilot.state.subscriber import StateStoreSubscriber


def build_default_event_bus() -> EventBus:
    bus = EventBus()

    # O estado atual vem primeiro: ele não pode depender do histórico.
    bus.subscribe(
        StateStoreSubscriber()
    )

    if openobserve_configured():
        bus.subscribe(
            OpenObserveEventSubscriber()
        )

    return bus
