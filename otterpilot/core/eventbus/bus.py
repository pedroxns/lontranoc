from __future__ import annotations

from otterpilot.core.eventbus.models import EventEnvelope
from otterpilot.core.eventbus.subscriber import EventSubscriber


class EventBusError(RuntimeError):
    pass


class DuplicateSubscriberError(EventBusError):
    pass


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, EventSubscriber] = {}

    def subscribe(
        self,
        subscriber: EventSubscriber,
    ) -> None:
        subscriber_id = subscriber.subscriber_id

        if subscriber_id in self._subscribers:
            raise DuplicateSubscriberError(
                f"Subscriber já registrado: {subscriber_id}"
            )

        if not isinstance(subscriber, EventSubscriber):
            raise TypeError(
                f"Subscriber inválido: {subscriber_id}"
            )

        self._subscribers[subscriber_id] = subscriber

    def publish(
        self,
        event: EventEnvelope,
    ) -> None:
        for subscriber in self._subscribers.values():
            subscriber.handle(event)

    def list_subscribers(self) -> tuple[str, ...]:
        return tuple(sorted(self._subscribers))


event_bus = EventBus()
