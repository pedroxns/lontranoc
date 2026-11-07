from __future__ import annotations

from otterpilot.core.eventbus import EventBus, EventEnvelope


class Failing:
    subscriber_id = "failing"

    def handle(self, event):
        raise RuntimeError("destino fora do ar")


class Recording:
    subscriber_id = "recording"

    def __init__(self):
        self.events = []

    def handle(self, event):
        self.events.append(event)


def test_failing_subscriber_does_not_block_others(capsys):
    bus = EventBus()
    recorder = Recording()
    bus.subscribe(Failing())
    bus.subscribe(recorder)

    event = EventEnvelope(capability="dns", connector="adguard", event_type="snapshot")
    bus.publish(event)
    bus.publish(event)

    assert recorder.events == [event, event]
    assert capsys.readouterr().out.count("destino fora do ar") == 1
