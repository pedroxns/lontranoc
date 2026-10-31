from __future__ import annotations

from otterpilot.copilot.assistant import parse_question
from otterpilot.copilot.service import answer_question, build_current_context
from otterpilot.core.eventbus import EventEnvelope


def test_parse_question():
    assert parse_question('{"question": " oi "}') == "oi"
    assert parse_question("texto puro") == "texto puro"


def test_context_is_compact(store):
    store.upsert(
        EventEnvelope(
            capability="virtualization",
            connector="proxmox",
            event_type="guest_snapshot",
            resource_id="lxc/510",
            status="warning",
            payload={"name": "frigate", "disk_percent": 86.04, "raw": {"big": "x" * 5000}},
        )
    )

    text = build_current_context(store)
    assert "proxmox/virtualization lxc/510: warning | name=frigate, disk_percent=86.0" in text
    assert "x" * 100 not in text


def test_answer_without_configuration():
    result = answer_question("tudo bem?")
    assert result["ok"] is False
    assert "não está configurado" in result["answer"]
