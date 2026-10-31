from __future__ import annotations

import time

from otterpilot.core.eventbus.models import EventEnvelope
from otterpilot.core.eventbus.subscriber import EventSubscriber


class EventBusError(RuntimeError):
    pass


class DuplicateSubscriberError(EventBusError):
    pass


# Falhas repetidas de um subscriber são relatadas no máximo uma vez
# por intervalo, para não inundar o journal quando um destino cai.
FAILURE_REPORT_INTERVAL_SECONDS = 300

# Compartilhado entre instâncias: providers criam um bus por publicação.
_last_failure_report: dict[str, float] = {}
_suppressed_failures: dict[str, int] = {}


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
        """Entrega o evento a todos os subscribers.

        A falha de um destino (ex.: OpenObserve fora do ar) não impede
        a entrega aos demais (ex.: State Store).
        """

        for subscriber_id, subscriber in self._subscribers.items():
            try:
                subscriber.handle(event)
            except Exception as error:
                self._report_failure(subscriber_id, event, error)

    def _report_failure(
        self,
        subscriber_id: str,
        event: EventEnvelope,
        error: Exception,
    ) -> None:
        now = time.monotonic()
        last = _last_failure_report.get(subscriber_id)

        if last is not None and now - last < FAILURE_REPORT_INTERVAL_SECONDS:
            _suppressed_failures[subscriber_id] = (
                _suppressed_failures.get(subscriber_id, 0) + 1
            )
            return

        suppressed = _suppressed_failures.pop(subscriber_id, 0)
        _last_failure_report[subscriber_id] = now

        extra = f" (+{suppressed} falhas suprimidas)" if suppressed else ""

        print(
            f"[eventbus] Falha no subscriber {subscriber_id} ao entregar "
            f"{event.connector}/{event.capability}/{event.event_type}: "
            f"{error}{extra}",
            flush=True,
        )

    def list_subscribers(self) -> tuple[str, ...]:
        return tuple(sorted(self._subscribers))


event_bus = EventBus()
