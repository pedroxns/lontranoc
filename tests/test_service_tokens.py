from __future__ import annotations

import json

import pytest

from otterpilot.api import auth
from otterpilot.cli import main as cli

VOICE = auth.SCOPE_COPILOT_VOICE


@pytest.fixture
def auth_file(tmp_path):
    return tmp_path / "auth.json"


def test_created_token_verifies_and_is_not_stored_in_clear(auth_file):
    token = auth.create_service_token("aparelho", [VOICE], auth_file)

    assert token.startswith(auth.SERVICE_TOKEN_PREFIX)
    assert auth.verify_service_token(token, VOICE, auth_file) == "aparelho"
    assert token not in auth_file.read_text(encoding="utf-8")
    assert "hash" in json.loads(auth_file.read_text(encoding="utf-8"))["service_tokens"]["aparelho"]


def test_token_needs_the_right_scope_and_a_known_value(auth_file):
    token = auth.create_service_token("aparelho", [VOICE], auth_file)

    assert auth.verify_service_token(token, "copilot:outro", auth_file) is None
    assert auth.verify_service_token(token + "x", VOICE, auth_file) is None
    assert auth.verify_service_token("otp_inventado", VOICE, auth_file) is None
    assert auth.verify_service_token(None, VOICE, auth_file) is None
    assert auth.verify_service_token("sem-prefixo", VOICE, auth_file) is None


def test_revoked_token_stops_working_and_others_survive(auth_file):
    first = auth.create_service_token("um", [VOICE], auth_file)
    second = auth.create_service_token("dois", [VOICE], auth_file)

    assert auth.revoke_service_token("um", auth_file) is True
    assert auth.verify_service_token(first, VOICE, auth_file) is None
    assert auth.verify_service_token(second, VOICE, auth_file) == "dois"
    assert auth.revoke_service_token("um", auth_file) is False


@pytest.mark.parametrize(
    "name, scopes",
    [("Nome Ruim", [VOICE]), ("", [VOICE]), ("ok", []), ("ok", ["copilot:inexistente"])],
)
def test_invalid_token_requests_are_rejected(auth_file, name, scopes):
    with pytest.raises(ValueError):
        auth.create_service_token(name, scopes, auth_file)


def test_duplicate_names_are_rejected(auth_file):
    auth.create_service_token("aparelho", [VOICE], auth_file)

    with pytest.raises(ValueError):
        auth.create_service_token("aparelho", [VOICE], auth_file)


def test_list_never_exposes_hash_or_token(auth_file):
    token = auth.create_service_token("aparelho", [VOICE], auth_file)

    listed = auth.list_service_tokens(auth_file)

    assert [item["name"] for item in listed] == ["aparelho"]
    assert listed[0]["scopes"] == [VOICE]
    assert token not in json.dumps(listed) and "hash" not in listed[0]


def test_tokens_do_not_disturb_the_password(auth_file):
    auth.set_password("senha-de-teste", auth_file)
    auth.create_service_token("aparelho", [VOICE], auth_file)

    assert auth.password_configured(auth_file)
    assert auth.validate_session(auth.create_session(auth_file), auth_file)


# --------------------------------------------------------------------- CLI


def test_cli_token_lifecycle(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(auth, "AUTH_FILE", tmp_path / "auth.json")

    assert cli.main(["token", "create", "gateway"]) == 0
    created = capsys.readouterr().out
    token = created.strip().splitlines()[-1]
    assert token.startswith(auth.SERVICE_TOKEN_PREFIX)
    assert auth.verify_service_token(token, VOICE) == "gateway"

    assert cli.main(["token", "list"]) == 0
    listing = capsys.readouterr().out
    assert "gateway" in listing and token not in listing

    assert cli.main(["token", "create", "gateway"]) == 1  # duplicado
    capsys.readouterr()

    assert cli.main(["token", "revoke", "gateway"]) == 0
    assert cli.main(["token", "revoke", "gateway"]) == 1
    assert auth.verify_service_token(token, VOICE) is None


def test_cli_hands_auth_file_back_to_service_user(monkeypatch, tmp_path, capsys):
    # Rodando com sudo, a gravação atômica deixaria o auth.json do root e
    # ilegível para a API: todo comando que o regrava precisa devolvê-lo.
    auth_path = tmp_path / "auth.json"
    monkeypatch.setattr(auth, "AUTH_FILE", auth_path)
    chowned = []
    monkeypatch.setattr(cli, "_chown_to_service_user", chowned.append)

    assert cli.main(["token", "create", "gateway"]) == 0
    assert cli.main(["token", "revoke", "gateway"]) == 0
    assert chowned == [auth_path, auth_path]

    assert cli.main(["token", "revoke", "gateway"]) == 1  # nada gravado
    assert len(chowned) == 2
    capsys.readouterr()
