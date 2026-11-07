from __future__ import annotations

import os
from pathlib import Path

from otterpilot.core.config import NotConfiguredError


class SecretError(NotConfiguredError):
    """Secret obrigatório ausente."""


def _systemd_credential_path(
    name: str,
) -> Path | None:
    credentials_directory = os.getenv(
        "CREDENTIALS_DIRECTORY"
    )

    if not credentials_directory:
        return None

    return Path(credentials_directory) / name


def get_secret(
    name: str,
    *,
    env_name: str | None = None,
    required: bool = False,
) -> str | None:
    """
    Retorna um secret sem depender de .env.

    Ordem de resolução:

    1. systemd credential
    2. variável de ambiente
    3. None ou erro, conforme required
    """

    credential_path = _systemd_credential_path(name)

    if (
        credential_path is not None
        and credential_path.is_file()
    ):
        value = credential_path.read_text(
            encoding="utf-8"
        ).strip()

        if value:
            return value

    environment_name = (
        env_name
        if env_name is not None
        else name.upper()
    )

    value = os.getenv(environment_name)

    if value:
        return value

    if required:
        raise SecretError(
            f"Secret obrigatório não configurado: {name}"
        )

    return None


def has_credential(
    name: str,
) -> bool:
    """Indica se o secret vem de uma credencial systemd não vazia."""

    path = _systemd_credential_path(name)

    if path is None or not path.is_file():
        return False

    return bool(path.read_text(encoding="utf-8").strip())
