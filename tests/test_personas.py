from __future__ import annotations

import base64
import shutil

import pytest
from fastapi.testclient import TestClient

from otterpilot.api import auth
from otterpilot.api.app import create_app
from otterpilot.copilot import personas, service
from otterpilot.core import config

PASSWORD = "senha-de-teste"
PNG = "data:image/png;base64," + base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"\0" * 32).decode()
SVG = "data:image/svg+xml;base64," + base64.b64encode(b'<svg xmlns="http://www.w3.org/2000/svg"/>').decode()

ROBOT = {
    "name": "Robô",
    "description": "Fala como um robô.",
    "avatar": "otter",
    "color": "#123456",
    "greeting": "BIP.",
    "personality": "Responda como um robô educado.",
}


@pytest.fixture(autouse=True)
def clean_copilot_dir(project_root):
    shutil.rmtree(project_root / "config" / "copilot", ignore_errors=True)
    yield
    shutil.rmtree(project_root / "config" / "copilot", ignore_errors=True)


@pytest.fixture
def client(project_root):
    auth.set_password(PASSWORD)
    auth._failures.clear()
    (project_root / ".env").write_text("# teste\n")
    config.reload_env()

    with TestClient(create_app()) as test_client:
        assert test_client.post("/api/auth/login", json={"password": PASSWORD}).status_code == 200
        yield test_client

    (project_root / ".env").unlink(missing_ok=True)
    config.reload_env()


# ---------------------------------------------------------------- módulo


def test_builtins_are_listed_in_order():
    entries = personas.list_personas()
    assert [entry.id for entry in entries[:2]] == ["lontraz", "unicornio"]
    assert all(entry.builtin and not entry.customized for entry in entries[:2])
    assert entries[1].persona.avatar == "unicorn"


def test_channels_default_and_resolution():
    assert personas.channel_personas() == {"web": "lontraz", "mqtt": "lontraz", "voice": "lontraz"}

    personas.set_channels({"mqtt": "unicornio"})
    assert personas.channel_personas()["mqtt"] == "unicornio"
    assert personas.channel_personas()["voice"] == "lontraz"  # trocar um canal nao mexe nos outros
    assert personas.resolve_persona(channel="mqtt").id == "unicornio"
    assert personas.resolve_persona(channel="web").id == "lontraz"

    # Pedido explícito vence o canal; ID desconhecido cai no canal.
    assert personas.resolve_persona("lontraz", channel="mqtt").id == "lontraz"
    assert personas.resolve_persona("nao-existe", channel="mqtt").id == "unicornio"

    with pytest.raises(personas.PersonaError):
        personas.set_channels({"mqtt": "nao-existe"})

    with pytest.raises(personas.PersonaError):
        personas.set_channels({"telegram": "lontraz"})


def test_edit_and_reset_builtin(project_root):
    data = {**ROBOT, "name": "Lontra Brava"}
    entry = personas.save_persona("lontraz", data)
    assert entry.builtin and entry.customized
    assert entry.persona.name == "Lontra Brava"
    assert (project_root / "config" / "copilot" / "personas" / "lontraz.yaml").is_file()

    assert personas.delete_persona("lontraz") == "reset"
    assert personas.get_persona("lontraz").persona.name == "Lontraz"

    with pytest.raises(KeyError):
        personas.delete_persona("lontraz")


def test_custom_persona_lifecycle():
    entry = personas.save_persona("robo", ROBOT, create=True)
    assert not entry.builtin
    assert personas.list_personas()[-1].id == "robo"

    with pytest.raises(personas.PersonaError):
        personas.save_persona("robo", ROBOT, create=True)

    with pytest.raises(KeyError):
        personas.save_persona("outro", ROBOT)

    personas.set_channels({"web": "robo"})
    assert personas.delete_persona("robo") == "deleted"
    assert personas.get_persona("robo") is None
    assert personas.channel_personas()["web"] == "lontraz"


@pytest.mark.parametrize(
    ("persona_id", "changes"),
    [
        ("Com Espaço", {}),
        ("robo", {"personality": "   "}),
        ("robo", {"color": "vermelho"}),
        ("robo", {"temperature": 3}),
        ("robo", {"avatar": "dragao"}),
        ("robo", {"avatar": "custom"}),  # sem imagem
    ],
)
def test_validation(persona_id, changes):
    with pytest.raises(personas.PersonaError):
        personas.save_persona(persona_id, {**ROBOT, **changes}, create=True)


def test_avatar_upload_and_removal():
    entry = personas.save_persona("robo", ROBOT, avatar_image=PNG, create=True)
    assert entry.persona.avatar == "custom"
    assert personas.avatar_file("robo").suffix == ".png"

    # Mantém a imagem ao salvar de novo sem reenviar.
    personas.save_persona("robo", {**ROBOT, "avatar": "custom"})
    assert personas.avatar_file("robo") is not None

    personas.save_persona("robo", {**ROBOT, "avatar": "unicorn"})
    assert personas.avatar_file("robo") is None


def test_avatar_validation():
    with pytest.raises(personas.PersonaError, match="não corresponde"):
        personas.decode_avatar("data:image/png;base64," + base64.b64encode(b"<svg/>").decode())

    with pytest.raises(personas.PersonaError, match="não suportado"):
        personas.decode_avatar("data:image/gif;base64,R0lGODlh")

    payload = b"\x89PNG\r\n\x1a\n" + b"\0" * 300_000
    big = "data:image/png;base64," + base64.b64encode(payload).decode()
    with pytest.raises(personas.PersonaError, match="grande demais"):
        personas.decode_avatar(big)

    assert personas.decode_avatar(SVG)[0] == "svg"


def test_broken_user_file_is_ignored(project_root):
    directory = project_root / "config" / "copilot" / "personas"
    directory.mkdir(parents=True)
    (directory / "quebrada.yaml").write_text("name: [sem fechar")
    (directory / "incompleta.yaml").write_text("name: Sem personalidade\n")

    ids = {entry.id for entry in personas.list_personas()}
    assert {"lontraz", "unicornio"} <= ids
    assert not ids & {"quebrada", "incompleta"}


def test_prompt_keeps_fixed_rules_around_personality():
    persona = personas.get_persona("unicornio").persona
    prompt = service.build_prompt("O DNS está ok?", "Status geral: healthy", {}, persona)

    assert "Você é Unicórnio Bobão" in prompt
    rules = prompt.index("Você nunca inventa informações")
    personality = prompt.index("unicórnio bobão, animado")
    question = prompt.index("Pergunta:\nO DNS está ok?")
    reminder = prompt.index("a personalidade nunca muda os fatos")
    assert rules < personality < question < reminder


def test_ask_ollama_sends_persona_temperature(monkeypatch):
    sent = {}

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"response": " oi "}

    def fake_post(url, json, timeout):
        sent.update(url=url, body=json)
        return Response()

    monkeypatch.setenv("OLLAMA_URL", "http://ollama:11434/")
    monkeypatch.setattr(service.requests, "post", fake_post)

    assert service.ask_ollama("p", temperature=0.9) == ("oi", service.DEFAULT_MODEL)
    assert sent["url"] == "http://ollama:11434/api/generate"
    assert sent["body"]["options"] == {"temperature": 0.9}

    service.ask_ollama("p")
    assert "options" not in sent["body"]


# ---------------------------------------------------------------- API


def test_api_config(client):
    data = client.get("/api/copilot/config").json()
    assert data["channels"] == {"web": "lontraz", "mqtt": "lontraz", "voice": "lontraz"}
    lontraz = data["personas"][0]
    assert lontraz["id"] == "lontraz"
    assert lontraz["avatar_urls"]["crit"] == "/api/copilot/avatars/otter-crit.svg"
    assert lontraz["channels"] == ["web", "mqtt", "voice"]
    assert data["model"]["model"] is None


def test_api_builtin_avatars(client):
    for avatar in personas.BUILTIN_AVATARS:
        for mood in personas.MOODS:
            response = client.get(f"/api/copilot/avatars/{avatar}-{mood}.svg")
            assert response.status_code == 200, (avatar, mood)
            assert response.headers["content-type"].startswith("image/svg+xml")
            assert b"<svg" in response.content

    for bad in ("dragao-ok.svg", "otter-feliz.svg", "otter-ok.png", "..%2Fpersonas.py"):
        assert client.get(f"/api/copilot/avatars/{bad}").status_code == 404

    client.cookies.clear()
    assert client.get("/api/copilot/avatars/otter-ok.svg").status_code == 401


def test_api_persona_crud_and_avatar(client):
    created = client.post(
        "/api/copilot/personas", json={"id": "robo", **ROBOT, "avatar_image": SVG}
    )
    assert created.status_code == 200, created.text
    robot = created.json()
    assert robot["avatar"] == "custom" and not robot["builtin"]

    image = client.get(robot["avatar_urls"]["ok"])
    assert image.status_code == 200
    assert image.headers["content-type"].startswith("image/svg+xml")
    assert "sandbox" in image.headers["content-security-policy"]

    assert client.post("/api/copilot/personas", json={"id": "robo", **ROBOT}).status_code == 422

    updated = client.put(
        "/api/copilot/personas/robo", json={**ROBOT, "name": "Robô 2", "avatar": "custom"}
    )
    assert updated.json()["name"] == "Robô 2"

    assert client.put("/api/copilot/personas/nada", json=ROBOT).status_code == 404

    invalid = client.put(
        "/api/copilot/personas/robo",
        json={**ROBOT, "color": "x", "personality": " ", "temperature": 2},
    )
    assert invalid.status_code == 422
    assert invalid.json()["detail"] == (
        "Cor: use o formato #rrggbb; Temperatura: máximo 1,5; Personalidade: obrigatório"
    )

    channels = client.put("/api/copilot/channels", json={"channels": {"mqtt": "robo"}}).json()
    assert channels["channels"]["mqtt"] == "robo"

    deleted = client.delete("/api/copilot/personas/robo").json()
    assert deleted["result"] == "deleted"
    assert deleted["channels"]["mqtt"] == "lontraz"
    assert client.get("/api/copilot/personas/robo/avatar").status_code == 404
    assert client.delete("/api/copilot/personas/unicornio").status_code == 404


def test_api_requires_session_for_personas(client):
    client.post("/api/auth/logout")
    client.cookies.clear()
    assert client.get("/api/copilot/config").status_code == 401
    assert client.post("/api/copilot/personas", json={"id": "x", **ROBOT}).status_code == 401


def test_api_model_update_writes_env(client, project_root):
    response = client.put(
        "/api/copilot/model",
        json={
            "model": "llama3.2:3b",
            "num_ctx": 8192,
            "timeout_seconds": service.DEFAULT_TIMEOUT_SECONDS,
        },
    )
    assert response.status_code == 200, response.text
    env = (project_root / ".env").read_text()
    assert "OLLAMA_MODEL=llama3.2:3b" in env
    assert "OLLAMA_NUM_CTX=8192" in env
    assert "OLLAMA_TIMEOUT_SECONDS" not in env
    assert response.json()["model"]["model"] == "llama3.2:3b"

    client.put("/api/copilot/model", json={"model": service.DEFAULT_MODEL})
    env = (project_root / ".env").read_text()
    assert "OLLAMA_MODEL" not in env and "OLLAMA_NUM_CTX" not in env

    assert client.put("/api/copilot/model", json={"model": "rm -rf /"}).status_code == 422


def test_api_models_without_ollama(client):
    result = client.get("/api/copilot/models").json()
    assert result["available"] is False
    assert "OLLAMA_URL" in result["error"]


def test_api_query_reports_persona(client):
    question = {"question": "oi", "persona": "unicornio"}
    result = client.post("/api/copilot/query", json=question).json()
    assert result["ok"] is False
    assert result["persona"] == {"id": "unicornio", "name": "Unicórnio Bobão"}
