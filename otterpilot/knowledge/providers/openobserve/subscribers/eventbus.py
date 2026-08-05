from __future__ import annotations

from otterpilot.core.eventbus import EventEnvelope
from otterpilot.core.serialization import make_json_safe
from otterpilot.knowledge.providers.openobserve.ingest import emit


class OpenObserveEventSubscriber:
    subscriber_id = "openobserve"

    def handle(
        self,
        event: EventEnvelope,
    ) -> None:
        payload = make_json_safe(event.payload)
        metadata = make_json_safe(event.metadata)

        emit(
            connector=event.connector,
            capability=event.capability,
            stream=event.capability,
            service=event.connector,
            component=event.capability,
            event_type=event.event_type,
            severity=event.severity,
            status=event.status,
            message=event.message,
            timestamp=event.timestamp.isoformat(),
            event_id=event.event_id,
            resource_id=event.resource_id,
            metadata=metadata,
            **payload,
        )
