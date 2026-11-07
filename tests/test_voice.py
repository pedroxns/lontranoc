from __future__ import annotations

import json

import pytest

from otterpilot.copilot import personas, service, voice
from otterpilot.core.eventbus import EventEnvelope

LONG = (
    "Ah, o disco do servidor está com noventa e cinco por cento de uso, droga. "
    "Isso é sério e vai parar tudo se ninguém limpar alguma coisa logo. "
    "Aliás, eu avisei três vezes, mas ninguém me escuta nessa casa."
)


# ------------------------------------------------------------------ corte


def test_trim_voice_keeps_two_complete_sentences():
    trimmed = voice.trim_voice(LONG)

    assert trimmed.endswith("logo.")
    assert "Aliás" not in trimmed
    assert len(trimmed) <= voice.MAX_CHARS


def test_trim_voice_limits_the_number_of_sentences_on_its_own():
    # Frases curtas: aqui só o limite de frases pode agir, não o de caracteres.
    assert voice.trim_voice("Um. Dois. Três. Quatro.") == "Um. Dois."


def test_trim_voice_leaves_short_answers_alone():
    assert voice.trim_voice("Sim. Sem erros.") == "Sim. Sem erros."
    assert voice.trim_voice("  Hmm.  ") == "Hmm."


def test_trim_voice_cuts_a_huge_first_sentence_at_a_pause():
    text = (
        "Uma frase gigantesca que não termina nunca e vai se arrastando com vírgulas, "
        "e mais vírgulas, e ainda mais palavras sem fim, só para testar o corte em uma "
        "pausa natural da fala porque senão fica estranho demais mesmo assim"
    )
    trimmed = voice.trim_voice(text)

    assert len(trimmed) <= voice.MAX_CHARS
    assert trimmed.endswith(".")
    assert text.startswith(trimmed[:-1])


def test_trim_voice_never_returns_empty():
    assert voice.trim_voice("") == ""
    assert voice.trim_voice("...") != ""


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Oi.", False),
        ("Primeira frase. Segunda frase.", False),
        ("Primeira frase. Segunda frase. Terceira começou", True),
        ("x" * (voice.MAX_CHARS + 40), True),
    ],
)
def test_voice_enough(text, expected):
    assert voice.voice_enough(text) is expected


def test_relevant_capabilities_ignores_accents_and_case():
    assert voice.relevant_capabilities("Como está o NOBREAK e a bateria?") == {"ups"}
    assert {"camera_health", "dns"} <= voice.relevant_capabilities("câmeras e DNS")
    assert voice.relevant_capabilities("bom dia") == set()


# ---------------------------------------------------------------- contexto


def _put(store, capability, resource_id, status="ok", **payload):
    store.upsert(
        EventEnvelope(
            capability=capability,
            connector="teste",
            event_type="snapshot",
            resource_id=resource_id,
            status=status,
            payload=payload,
        )
    )


def test_voice_context_only_lists_what_the_question_mentions(store):
    _put(store, "ups", "ups1", ups_status="ONLINE", battery_percent=100)
    _put(store, "dns", "adguard1", running=True)

    text = service.build_voice_context("como está o nobreak?", store)

    assert "Status geral:" in text
    assert "teste/ups ups1" in text
    assert "teste/dns" not in text


def test_voice_context_is_smaller_than_the_web_context(store):
    for index in range(30):
        _put(store, "virtualization", f"lxc/{index}", name=f"ct{index}", cpu_percent=1.0)

    assert len(service.build_voice_context("bom dia", store)) < len(service.build_current_context(store)) / 3


def test_voice_context_caps_the_problem_list(store):
    for index in range(voice.MAX_PROBLEMS + 4):
        _put(store, "virtualization", f"lxc/{index}", status="critical", name=f"ct{index}")

    text = service.build_voice_context("bom dia", store)

    assert text.count("- [") <= voice.MAX_PROBLEMS
    assert "... e mais" in text


# ------------------------------------------------------------------ prompt


def test_prompt_only_asks_for_short_answers_in_voice_mode():
    persona = personas.get_persona("lontraz").persona
    web = service.build_prompt("oi", "ctx", {}, persona)
    spoken = service.build_prompt("oi", "ctx", {}, persona, voice_mode=True)

    assert voice.VOICE_RULES not in web
    assert voice.VOICE_RULES in spoken
    assert persona.personality in spoken  # a rabugice continua


def test_the_voice_channel_uses_the_grumpy_persona_by_default():
    assert personas.resolve_persona(channel="voice").id == "lontraz"
    assert "rabugenta" in personas.resolve_persona(channel="voice").personality


# --------------------------------------------------------------- streaming


class FakeResponse:
    def __init__(self, lines):
        self.lines = lines
        self.consumed = 0
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.closed = True

    def raise_for_status(self):
        pass

    def iter_lines(self):
        for line in self.lines:
            self.consumed += 1
            yield line


def _ndjson(text, size=6):
    pieces = [text[i : i + size] for i in range(0, len(text), size)]
    lines = [json.dumps({"response": piece, "done": False}).encode() for piece in pieces]
    lines.append(json.dumps({"response": "", "done": True}).encode())
    return lines


def test_stream_ollama_stops_early_and_closes_the_connection(monkeypatch):
    monkeypatch.setenv("OLLAMA_URL", "http://ollama.test")
    fake = FakeResponse(_ndjson(LONG * 3))
    sent = {}

    def fake_post(url, json=None, timeout=None, stream=None):
        sent["body"] = json
        return fake

    monkeypatch.setattr(service.requests, "post", fake_post)

    text, _model = service.stream_ollama("p", num_predict=voice.NUM_PREDICT, stop=voice.voice_enough)

    assert sent["body"]["stream"] is True
    assert sent["body"]["options"]["num_predict"] == voice.NUM_PREDICT
    assert fake.closed
    assert fake.consumed < len(fake.lines) / 2  # parou no meio do texto
    assert voice.trim_voice(text).endswith("logo.")


# ----------------------------------------------------------------- resposta


def test_answer_question_by_voice_is_short_and_streams_trimmed_text(monkeypatch):
    seen = {}

    def fake_stream(prompt, *, temperature=None, num_predict=None, on_text=None, stop=None):
        seen["prompt"] = prompt
        seen["num_predict"] = num_predict
        for end in range(10, len(LONG) + 1, 10):
            on_text(LONG[:end])
        return LONG, "modelo-teste"

    monkeypatch.setattr(service, "stream_ollama", fake_stream)
    partials = []

    result = service.answer_question("como está o disco?", source="voice", on_text=partials.append)

    assert result["ok"] is True
    assert result["persona"]["id"] == "lontraz"
    assert result["answer"].endswith("logo.") and "Aliás" not in result["answer"]
    assert seen["num_predict"] == voice.NUM_PREDICT
    assert voice.VOICE_RULES in seen["prompt"]
    assert partials and all(len(item) <= voice.MAX_CHARS for item in partials)


def test_answer_question_by_voice_without_ollama_is_a_friendly_error():
    result = service.answer_question("oi", source="voice")

    assert result["ok"] is False
    assert "não está configurado" in result["answer"]


def test_web_answers_are_not_shortened(monkeypatch):
    monkeypatch.setattr(service, "ask_ollama", lambda prompt, *, temperature=None: (LONG, "m"))

    result = service.answer_question("como está o disco?", source="web")

    assert result["answer"] == LONG
