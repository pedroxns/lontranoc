from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from otterpilot.api import auth
from otterpilot.api.app import create_app
from otterpilot.copilot import service, stream, voice

PASSWORD = "senha-de-teste"
LONG = (
    "Ah, o disco do servidor está com noventa e cinco por cento de uso, droga. "
    "Isso é sério e vai parar tudo se ninguém limpar alguma coisa logo. "
    "Aliás, eu avisei três vezes, mas ninguém me escuta nessa casa."
)


@pytest.fixture
def client(project_root):
    auth.set_password(PASSWORD)
    auth._failures.clear()
    data = auth.load_auth()
    data.pop("service_tokens", None)
    auth.save_auth(data)

    with TestClient(create_app()) as test_client:
        yield test_client

    data = auth.load_auth()
    data.pop("service_tokens", None)
    auth.save_auth(data)
    auth._failures.clear()


@pytest.fixture
def fake_llm(monkeypatch):
    def fake_stream(prompt, *, temperature=None, num_predict=None, on_text=None, stop=None):
        for end in range(12, len(LONG) + 1, 12):
            on_text(LONG[:end])
        on_text(LONG)
        return LONG, "modelo-teste"

    monkeypatch.setattr(service, "stream_ollama", fake_stream)


def _events(response):
    return [json.loads(line) for line in response.text.splitlines() if line.strip()]


def _bearer(token):
    return {"Authorization": f"Bearer {token}"}


def test_voice_endpoint_requires_credentials(client):
    assert client.post("/api/copilot/voice", json={"question": "oi"}).status_code == 401
    assert client.post("/api/copilot/voice", json={"question": "oi"}, headers=_bearer("otp_errado")).status_code == 401


def test_voice_endpoint_streams_short_answers_with_a_token(client, fake_llm):
    token = auth.create_service_token("aparelho", [auth.SCOPE_COPILOT_VOICE])

    response = client.post("/api/copilot/voice", json={"question": "como está o disco?"}, headers=_bearer(token))

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/x-ndjson")
    events = _events(response)
    kinds = [event["type"] for event in events]
    assert kinds[-1] == "done" and set(kinds[:-1]) == {"text"}
    assert len(events) > 3  # chegou aos pedaços, não de uma vez

    partials = [event["text"] for event in events if event["type"] == "text"]
    assert all(len(text) <= voice.MAX_CHARS for text in partials)
    assert len(set(partials)) == len(partials)  # sem repetir o mesmo texto

    done = events[-1]
    assert done["ok"] is True and done["persona"]["id"] == "lontraz"
    assert done["answer"].endswith("logo.") and "Aliás" not in done["answer"]


def test_voice_endpoint_also_accepts_the_web_session(client, fake_llm):
    assert client.post("/api/auth/login", json={"password": PASSWORD}).status_code == 200

    response = client.post("/api/copilot/voice", json={"question": "oi"})

    assert response.status_code == 200 and _events(response)[-1]["type"] == "done"


def test_revoked_token_is_refused(client, fake_llm):
    token = auth.create_service_token("aparelho", [auth.SCOPE_COPILOT_VOICE])
    auth.revoke_service_token("aparelho")

    assert client.post("/api/copilot/voice", json={"question": "oi"}, headers=_bearer(token)).status_code == 401


def test_repeated_bad_tokens_are_throttled(client):
    for _ in range(auth.LOGIN_MAX_FAILURES):
        client.post("/api/copilot/voice", json={"question": "oi"}, headers=_bearer("otp_errado"))

    assert client.post("/api/copilot/voice", json={"question": "oi"}, headers=_bearer("otp_errado")).status_code == 429


def test_voice_endpoint_validates_the_question(client):
    token = auth.create_service_token("aparelho", [auth.SCOPE_COPILOT_VOICE])

    assert client.post("/api/copilot/voice", json={"question": ""}, headers=_bearer(token)).status_code == 422
    assert client.post("/api/copilot/voice", json={"question": "x" * 501}, headers=_bearer(token)).status_code == 422


def test_llm_problems_still_end_with_a_done_event(client):
    token = auth.create_service_token("aparelho", [auth.SCOPE_COPILOT_VOICE])

    # Sem OLLAMA_URL: o Copilot responde que não está configurado (não é erro de HTTP).
    events = _events(client.post("/api/copilot/voice", json={"question": "oi"}, headers=_bearer(token)))

    assert events[-1]["type"] == "done" and events[-1]["ok"] is False


def test_unexpected_failure_becomes_an_error_event(monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("quebrou")

    monkeypatch.setattr(stream, "answer_question", boom)

    events = [json.loads(line) for line in stream.voice_events("oi")]

    assert events == [{"type": "error", "error": "quebrou"}]


def test_closing_the_stream_cancels_the_generation(monkeypatch):
    seen = {}

    def slow_answer(question, *, source, persona_id, on_text, cancel):
        on_text("Primeira.")
        seen["cancel"] = cancel
        cancel.wait(timeout=5)
        return {"ok": True, "answer": "x"}

    monkeypatch.setattr(stream, "answer_question", slow_answer)
    events = stream.voice_events("oi")

    assert json.loads(next(events))["type"] == "text"
    events.close()  # o cliente desconectou

    assert seen["cancel"].wait(timeout=2)
