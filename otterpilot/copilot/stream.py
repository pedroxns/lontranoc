"""Eventos NDJSON da resposta falada, para o canal de voz da API.

`answer_question` bloqueia e avisa o texto parcial por callback; aqui ele roda
numa thread e os avisos viram uma sequência de eventos que o endpoint repassa
ao cliente (o aparelho começa a sintetizar a 1ª frase antes de a resposta
terminar):

    {"type": "text", "text": "Ah, o disco..."}      texto parcial (já cortado)
    {"type": "done", "answer": "...", "ok": true, ...}
    {"type": "error", "error": "..."}                  falha inesperada
"""

from __future__ import annotations

import json
import queue
import threading
from collections.abc import Iterator
from typing import Any

from otterpilot.copilot.service import answer_question
from otterpilot.core.serialization import make_json_safe


def _line(event: dict[str, Any]) -> bytes:
    return json.dumps(make_json_safe(event), ensure_ascii=False).encode() + b"\n"


def voice_events(question: str, *, persona_id: str | None = None) -> Iterator[bytes]:
    events: queue.Queue[dict[str, Any] | None] = queue.Queue()
    cancel = threading.Event()
    last_text = ""

    def on_text(partial: str) -> None:
        nonlocal last_text

        # O corte pode repetir o mesmo texto enquanto o LLM escreve além do limite.
        if partial != last_text:
            last_text = partial
            events.put({"type": "text", "text": partial})

    def work() -> None:
        try:
            result = answer_question(
                question,
                source="voice",
                persona_id=persona_id,
                on_text=on_text,
                cancel=cancel,
            )
            events.put({"type": "done", **result})
        except Exception as error:  # nunca deixar o cliente esperando sem resposta
            events.put({"type": "error", "error": str(error)})
        finally:
            events.put(None)

    threading.Thread(target=work, daemon=True, name="copilot-voice").start()

    try:
        while (event := events.get()) is not None:
            yield _line(event)
    finally:
        cancel.set()  # o cliente foi embora (ou terminou): aborta a geração se ainda houver
