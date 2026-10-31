from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from otterpilot.api import auth
from otterpilot.api.app import create_app
from otterpilot.core import config
from otterpilot.core.eventbus import EventEnvelope
from otterpilot.state import build_default_state_store

PASSWORD = "senha-de-teste"


@pytest.fixture
def client(project_root):
    auth.set_password(PASSWORD)
    (project_root / ".env").write_text("# teste\n")
    config.reload_env()
    auth._failures.clear()

    store = build_default_state_store()
    for state in store.list_all():
        store.delete(connector=state["connector"], capability=state["capability"], resource_id=state["resource_id"])

    store.upsert(
        EventEnvelope(
            capability="virtualization",
            connector="proxmox",
            event_type="guest_snapshot",
            resource_id="lxc/510",
            status="warning",
            payload={"name": "frigate", "node": "pve", "proxmox_status": "running"},
        )
    )

    with TestClient(create_app()) as test_client:
        yield test_client

    (project_root / ".env").unlink(missing_ok=True)
    (project_root / "config" / "proxmox.yaml").unlink(missing_ok=True)
    config.reload_env()


def login(client):
    response = client.post("/api/auth/login", json={"password": PASSWORD})
    assert response.status_code == 200


def test_health_is_public(client):
    assert client.get("/api/health").json()["status"] == "ok"


def test_api_requires_session(client):
    assert client.get("/api/system").status_code == 401
    assert client.get("/api/auth/session").json()["authenticated"] is False


def test_wrong_password(client, monkeypatch):
    monkeypatch.setattr("otterpilot.api.app.time.sleep", lambda _: None)
    assert client.post("/api/auth/login", json={"password": "errada"}).status_code == 401


def test_login_and_overview(client):
    login(client)
    system = client.get("/api/system").json()
    assert system["resource_count"] == 1
    assert system["overall_status"] == "degraded"

    resources = client.get("/api/resources?capability=virtualization").json()
    assert resources[0]["name"] == "frigate"

    detail = client.get("/api/resources/proxmox/virtualization/lxc/510").json()
    assert detail["resource_id"] == "lxc/510"


def test_forget_resource(client):
    login(client)
    assert client.delete("/api/resources/proxmox/virtualization/lxc/510").status_code == 200
    assert client.get("/api/resources/proxmox/virtualization/lxc/510").status_code == 404


def test_settings_roundtrip_masks_secrets(client, project_root):
    login(client)

    response = client.put(
        "/api/settings/homeassistant",
        json={"values": {"HA_URL": "http://ha.local:8123", "HA_TOKEN": "segredo"}},
    )
    assert response.status_code == 200, response.text
    group = response.json()
    assert group["configured"] is True

    token = next(s for s in group["settings"] if s["key"] == "HA_TOKEN")
    assert token["is_set"] is True
    assert "value" not in token

    env = (project_root / ".env").read_text()
    assert "HA_TOKEN=segredo" in env

    # Segredo vazio mantém o valor; null remove.
    client.put("/api/settings/homeassistant", json={"values": {"HA_TOKEN": ""}})
    assert "HA_TOKEN=segredo" in (project_root / ".env").read_text()

    client.put("/api/settings/homeassistant", json={"values": {"HA_TOKEN": None}})
    assert "HA_TOKEN" not in (project_root / ".env").read_text()


def test_settings_validation(client):
    login(client)
    response = client.put("/api/settings/homeassistant", json={"values": {"HA_URL": "ha.local"}})
    assert response.status_code == 422

    response = client.put("/api/settings/homeassistant", json={"values": {"NOPE": "x"}})
    assert response.status_code == 422


def test_disable_connector(client, project_root):
    login(client)
    client.put("/api/settings/proxmox", json={"values": {}, "enabled": False})
    assert "PROXMOX_ENABLED=false" in (project_root / ".env").read_text()

    connectors = {c["id"]: c for c in client.get("/api/connectors").json()}
    assert connectors["proxmox"]["enabled"] is False

    client.put("/api/settings/proxmox", json={"values": {}, "enabled": True})
    assert "PROXMOX_ENABLED" not in (project_root / ".env").read_text()


def test_job_interval_override(client, project_root):
    login(client)
    jobs = client.put("/api/jobs/proxmox-virtualization", json={"interval_seconds": 120}).json()
    job = next(j for j in jobs if j["job_id"] == "proxmox-virtualization")
    assert job["interval_seconds"] == 120 and job["interval_overridden"]

    client.put("/api/jobs/proxmox-virtualization", json={"interval_seconds": None})
    assert "POLL_INTERVAL_PROXMOX_VIRTUALIZATION" not in (project_root / ".env").read_text()


def test_policies(client, project_root):
    login(client)
    response = client.put(
        "/api/policies/virtualization",
        json={"workloads": {"lxc/510": {"name": "frigate", "expected_state": "running", "importance": "critical"}}},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["workloads"]["lxc/510"]["importance"] == "critical"
    assert data["guests"][0]["resource_id"] == "lxc/510"


def test_config_file_validation(client):
    login(client)
    bad = client.put("/api/config-files/vehicle.yaml", json={"content": "foo: [unclosed"})
    assert bad.status_code == 422

    wrong = client.put("/api/config-files/vehicle.yaml", json={"content": "outra: 1\n"})
    assert wrong.status_code == 422

    assert client.put("/api/config-files/../.env", json={"content": "x"}).status_code == 404


def test_copilot_without_ollama(client):
    login(client)
    result = client.post("/api/copilot/query", json={"question": "tudo bem?"}).json()
    assert result["ok"] is False


def test_activity_without_openobserve(client):
    login(client)
    assert client.get("/api/activity").json()["available"] is False


def test_password_change_invalidates_old_session(client):
    login(client)
    old_cookie = client.cookies.get(auth.SESSION_COOKIE)

    response = client.post("/api/auth/password", json={"current": PASSWORD, "new": "outra-senha-123"})
    assert response.status_code == 200
    assert client.get("/api/system").status_code == 200

    assert not auth.validate_session(old_cookie)
    auth.set_password(PASSWORD)


def test_web_ui_served(client):
    page = client.get("/")
    assert page.status_code == 200
    assert "app.js" in page.text
    assert client.get("/static/app.js").status_code == 200


def test_connection_test_reports_missing_configuration(client):
    login(client)

    proxmox = client.post("/api/settings/proxmox/test").json()["results"]
    assert {r["label"] for r in proxmox} == {"Coleta host_health", "Coleta virtualization"}
    assert all(r["not_configured"] and not r["ok"] for r in proxmox)

    mqtt = client.post("/api/settings/mqtt/test").json()["results"]
    assert mqtt[0]["not_configured"]

    assert client.post("/api/settings/nope/test").status_code == 404
