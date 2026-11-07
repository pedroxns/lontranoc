from __future__ import annotations

import os

from dotenv import dotenv_values

from otterpilot.core import config


def test_get_env_treats_blank_as_missing(monkeypatch):
    monkeypatch.setenv("OTTERPILOT_TEST_BLANK", "  ")
    assert config.get_env("OTTERPILOT_TEST_BLANK", "fallback") == "fallback"


def test_update_env_file_preserves_comments_and_quotes(tmp_path):
    env = tmp_path / ".env"
    env.write_text("## MQTT ##\nMQTT_HOST=old\n\n# comentário\nKEEP=1\nREMOVE=x\n")

    config.update_env_file(
        {
            "MQTT_HOST": "192.168.20.10",
            "REMOVE": None,
            "TOKEN": "a b#c$d'e\"f",
            "PLAIN": "abc-123",
        },
        path=env,
    )

    text = env.read_text()
    assert text.startswith("## MQTT ##\nMQTT_HOST=192.168.20.10\n\n# comentário\nKEEP=1\n")
    assert "REMOVE" not in text

    values = dotenv_values(env)
    assert values["TOKEN"] == "a b#c$d'e\"f"
    assert values["PLAIN"] == "abc-123"
    assert values["KEEP"] == "1"


def test_update_env_file_keeps_file_mode(tmp_path):
    env = tmp_path / ".env"
    env.write_text("A=1\n")
    env.chmod(0o640)

    config.update_env_file({"A": "2"}, path=env)

    assert env.stat().st_mode & 0o777 == 0o640


def test_reload_env_applies_and_removes_file_keys(project_root, monkeypatch):
    env = project_root / ".env"
    env.write_text("OTTERPILOT_TEST_RELOAD=1\n")
    config.reload_env()
    assert os.environ["OTTERPILOT_TEST_RELOAD"] == "1"

    config.update_env_file({"OTTERPILOT_TEST_RELOAD": None})
    assert "OTTERPILOT_TEST_RELOAD" not in os.environ

    env.unlink()
    config.reload_env()


def test_connector_enabled_flag(monkeypatch):
    assert config.connector_enabled("proxmox")
    monkeypatch.setenv("PROXMOX_ENABLED", "false")
    assert not config.connector_enabled("proxmox")
