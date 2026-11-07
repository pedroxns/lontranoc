from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from otterpilot.api import auth
from otterpilot.api.app import create_app
from otterpilot.copilot import language, personas, service

PASSWORD = "senha-de-teste"
SWEARS = ("droga", "merda", "porra", "caralho", "bosta", "cacete", "puta", "foda", "inferno", "diabos", "saco")


# ------------------------------------------------------------------ filtro


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Droga, o disco encheu.", "Poxa, o disco encheu."),
        ("O ambiente tá na merda.", "O ambiente tá na bagunça."),
        ("PORRA!", "POXA!"),
        ("Que saco, de novo?", "Que chato, de novo?"),
        ("Puta merda, caiu tudo", "Nossa, caiu tudo"),
        ("Bom dia, tudo certo.", "Bom dia, tudo certo."),
    ],
)
def test_soften_replaces_swearing_and_keeps_the_rest(text, expected):
    assert language.soften(text) == expected


@pytest.mark.parametrize("text", ["Levou uma porrada", "Trouxe uma sacola", "Uma computação cara", "Tem diabetes"])
def test_soften_does_not_touch_words_that_merely_contain_one(text):
    assert language.soften(text) == text


def test_soften_is_idempotent():
    once = language.soften("Droga, que merda, porra!")

    assert language.soften(once) == once


# ----------------------------------------------------------------- persona


def test_unicorn_costume_persona_is_builtin_and_family_friendly():
    entry = personas.get_persona("lontra-unicornio")

    assert entry is not None and entry.builtin
    assert entry.persona.device_avatar == "unicorn"
    assert entry.persona.family_friendly is True
    assert entry.persona.voice == "lontra_unicornio"  # arquivo próprio, clonado da voz da lontra: trocar é só substituir o .wav
    text = entry.persona.personality.lower()
    assert "crianças" in text and "rabugenta" in text and "fantasia" in text


def test_default_persona_keeps_the_otter_avatar_and_swearing():
    persona = personas.get_persona("lontraz").persona

    assert persona.device_avatar == "otter" and persona.family_friendly is False


def test_new_persona_fields_are_validated():
    base = {"name": "Teste", "personality": "x"}

    assert personas._build("teste", {**base, "voice": "outra_voz", "device_avatar": "unicorn"}).voice == "outra_voz"

    for bad in ({"voice": "Voz Ruim"}, {"voice": "../etc"}, {"device_avatar": "dragao"}):
        with pytest.raises(personas.PersonaError):
            personas._build("teste", {**base, **bad})


def test_the_family_filter_applies_to_web_and_voice_answers(monkeypatch):
    monkeypatch.setattr(service, "ask_ollama", lambda prompt, *, temperature=None: ("Droga, que merda.", "m"))

    def fake_stream(prompt, *, temperature=None, num_predict=None, on_text=None, stop=None):
        on_text("Droga, que merda.")
        return "Droga, que merda.", "m"

    monkeypatch.setattr(service, "stream_ollama", fake_stream)
    partials: list[str] = []

    web = service.answer_question("oi", source="web", persona_id="lontra-unicornio")
    spoken = service.answer_question("oi", source="voice", persona_id="lontra-unicornio", on_text=partials.append)
    grumpy = service.answer_question("oi", source="web", persona_id="lontraz")

    assert web["answer"] == "Poxa, que bagunça."
    assert spoken["answer"] == "Poxa, que bagunça." and partials == ["Poxa, que bagunça."]
    assert grumpy["answer"] == "Droga, que merda."  # a lontra de sempre continua xingando
    assert not any(word in web["answer"].lower() for word in SWEARS)


# ---------------------------------------------------------------------- API


@pytest.fixture
def client(project_root):
    auth.set_password(PASSWORD)
    auth._failures.clear()
    data = auth.load_auth()
    data.pop("service_tokens", None)
    auth.save_auth(data)
    personas.set_channels({"voice": None})

    with TestClient(create_app()) as test_client:
        yield test_client

    personas.set_channels({"voice": None})
    data = auth.load_auth()
    data.pop("service_tokens", None)
    auth.save_auth(data)


def _bearer(token):
    return {"Authorization": f"Bearer {token}"}


def test_config_lists_device_avatars_and_the_new_fields(client):
    assert client.post("/api/auth/login", json={"password": PASSWORD}).status_code == 200

    data = client.get("/api/copilot/config").json()

    assert {item["id"] for item in data["device_avatars"]} == {"otter", "unicorn"}
    unicorn = next(item for item in data["personas"] if item["id"] == "lontra-unicornio")
    assert unicorn["device_avatar"] == "unicorn" and unicorn["family_friendly"] is True and unicorn["voice"] == "lontra_unicornio"


def test_device_endpoint_follows_the_persona_chosen_for_the_voice_channel(client):
    token = auth.create_service_token("aparelho", [auth.SCOPE_COPILOT_VOICE])
    assert client.post("/api/auth/login", json={"password": PASSWORD}).status_code == 200

    before = client.get("/api/copilot/voice/persona", headers=_bearer(token)).json()
    assert before["id"] == "lontraz" and before["device_avatar"] == "otter" and before["family_friendly"] is False

    # "Avatar: unicórnio" na página = a persona do canal de voz passa a ser a de fantasia.
    assert client.put("/api/copilot/channels", json={"channels": {"voice": "lontra-unicornio"}}).status_code == 200

    after = client.get("/api/copilot/voice/persona", headers=_bearer(token)).json()
    assert after["id"] == "lontra-unicornio" and after["device_avatar"] == "unicorn"
    assert after["family_friendly"] is True and "fantasia" in after["personality"]
    assert set(after) == {"id", "name", "personality", "temperature", "greeting", "voice", "device_avatar", "family_friendly"}


def test_device_endpoint_requires_a_valid_token(client):
    assert client.get("/api/copilot/voice/persona").status_code == 401
    assert client.get("/api/copilot/voice/persona", headers=_bearer("otp_errado")).status_code == 401


def test_a_persona_can_be_saved_with_the_new_fields(client):
    assert client.post("/api/auth/login", json={"password": PASSWORD}).status_code == 200
    body = {"id": "robo", "name": "Robô", "personality": "Fala como robô.", "voice": "voz_robo",
            "device_avatar": "unicorn", "family_friendly": True}

    created = client.post("/api/copilot/personas", json=body)
    assert created.status_code == 200 or created.status_code == 201
    view = created.json()
    assert view["voice"] == "voz_robo" and view["device_avatar"] == "unicorn" and view["family_friendly"] is True

    bad = client.post("/api/copilot/personas", json={**body, "id": "robo2", "device_avatar": "dragao"})
    assert bad.status_code == 422

    client.delete("/api/copilot/personas/robo")
