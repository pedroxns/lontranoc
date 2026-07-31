from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


def find_project_root() -> Path:
    env_root = os.getenv("OTTERPILOT_ROOT")

    if env_root:
        return Path(env_root).expanduser().resolve()

    return Path(__file__).resolve().parents[2]


PROJECT_ROOT = find_project_root()
CONFIG_DIR = PROJECT_ROOT / "config"
ENV_FILE = PROJECT_ROOT / ".env"

load_dotenv(ENV_FILE)


def get_env(
    name: str,
    default: str | None = None,
    *,
    required: bool = False,
) -> str | None:
    value = os.getenv(name, default)

    if required and not value:
        raise RuntimeError(f"Variável obrigatória não configurada: {name}")

    return value


def get_path(
    relative_path: str | Path,
    *,
    must_exist: bool = False,
) -> Path:
    path = PROJECT_ROOT / relative_path

    if must_exist and not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")

    return path


def config_path(
    filename: str,
    *,
    must_exist: bool = True,
) -> Path:
    path = CONFIG_DIR / filename

    if must_exist and not path.exists():
        raise FileNotFoundError(f"Configuração não encontrada: {path}")

    return path
