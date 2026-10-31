from __future__ import annotations

import os
import re
import signal
import tempfile
import threading
import time
from collections.abc import Callable
from importlib import resources
from pathlib import Path

from dotenv import dotenv_values


class ConfigError(RuntimeError):
    """Erro relacionado à configuração do OtterPilot."""


class NotConfiguredError(ConfigError):
    """Uma integração ou recurso necessário não está configurado."""


def find_project_root() -> Path:
    env_root = os.getenv("OTTERPILOT_ROOT")

    if env_root:
        return Path(env_root).expanduser().resolve()

    return Path(__file__).resolve().parents[2]


PROJECT_ROOT = find_project_root()
CONFIG_DIR = PROJECT_ROOT / "config"
ENV_FILE = PROJECT_ROOT / ".env"

_ENV_KEY = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=")

# Chaves que vieram do .env, para que um reload consiga removê-las.
_file_keys: set[str] = set()


def reload_env() -> None:
    """Carrega o .env no ambiente do processo.

    Variáveis definidas fora do arquivo (ex.: Environment= do systemd)
    têm precedência e nunca são sobrescritas.
    """

    global _file_keys

    values = dotenv_values(ENV_FILE) if ENV_FILE.is_file() else {}

    for key in _file_keys - values.keys():
        os.environ.pop(key, None)

    loaded: set[str] = set()

    for key, value in values.items():
        if key in _file_keys or key not in os.environ:
            os.environ[key] = value or ""
            loaded.add(key)

    _file_keys = loaded


reload_env()


def get_env(
    name: str,
    default: str | None = None,
    *,
    required: bool = False,
) -> str | None:
    value = os.getenv(name)

    if value is None or value.strip() == "":
        value = default

    if required and not value:
        raise NotConfiguredError(f"Variável obrigatória não configurada: {name}")

    return value


def get_bool(name: str, default: bool = False) -> bool:
    value = get_env(name)

    if value is None:
        return default

    return value.strip().lower() in ("1", "true", "yes", "on", "sim")


def get_int(name: str, default: int) -> int:
    value = get_env(name)

    if value is None:
        return default

    try:
        return int(value)
    except ValueError:
        return default


def connector_enabled(connector_id: str) -> bool:
    """Connectors ficam habilitados salvo `<CONNECTOR>_ENABLED=false`."""

    return get_bool(f"{connector_id.upper()}_ENABLED", True)


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
        raise NotConfiguredError(f"Configuração não encontrada: {path}")

    return path


def resource_text(package: str, filename: str) -> str:
    """Lê um arquivo da configuração local ou, se ausente, o padrão do pacote."""

    override = CONFIG_DIR / filename

    if override.is_file():
        return override.read_text(encoding="utf-8")

    return resources.files(package).joinpath(filename).read_text(encoding="utf-8")


def _quote_env_value(value: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9_./:@,+=-]*", value):
        return value

    if "'" not in value:
        return f"'{value}'"

    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = path.stat().st_mode & 0o777 if path.exists() else 0o600

    fd, temp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)

        os.chmod(temp_name, mode)
        os.replace(temp_name, path)
    except BaseException:
        Path(temp_name).unlink(missing_ok=True)
        raise


def update_env_file(
    updates: dict[str, str | None],
    path: Path | None = None,
) -> None:
    """Altera chaves do .env preservando comentários e ordem.

    Valor None remove a chave. Chaves novas são acrescentadas ao final.
    """

    path = path or ENV_FILE
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    pending = dict(updates)
    output: list[str] = []

    for line in lines:
        match = _ENV_KEY.match(line)

        if match and match.group(1) in pending:
            key = match.group(1)
            value = pending.pop(key)

            if value is not None:
                output.append(f"{key}={_quote_env_value(value)}")

            continue

        output.append(line)

    for key, value in pending.items():
        if value is not None:
            output.append(f"{key}={_quote_env_value(value)}")

    _atomic_write(path, "\n".join(output) + "\n")

    if path == ENV_FILE:
        reload_env()


def write_config_file(filename: str, text: str) -> Path:
    path = CONFIG_DIR / filename
    _atomic_write(path, text if text.endswith("\n") else text + "\n")
    return path


def _config_snapshot() -> dict[str, int | None]:
    files = [ENV_FILE]

    if CONFIG_DIR.is_dir():
        files.extend(sorted(CONFIG_DIR.glob("*.yaml")))

    snapshot: dict[str, int | None] = {}

    for file in files:
        try:
            snapshot[str(file)] = file.stat().st_mtime_ns
        except FileNotFoundError:
            snapshot[str(file)] = None

    return snapshot


def _terminate_self() -> None:
    os.kill(os.getpid(), signal.SIGTERM)


def watch_config(
    interval_seconds: float = 5.0,
    on_change: Callable[[], None] | None = None,
) -> threading.Thread:
    """Encerra o processo quando a configuração muda.

    Os serviços rodam com Restart=always, então o systemd os reinicia
    já com a configuração nova.
    """

    baseline = _config_snapshot()

    def run() -> None:
        while True:
            time.sleep(interval_seconds)

            if _config_snapshot() != baseline:
                print(
                    "[config] Configuração alterada; reiniciando o processo.",
                    flush=True,
                )
                (on_change or _terminate_self)()
                return

    thread = threading.Thread(target=run, name="config-watcher", daemon=True)
    thread.start()
    return thread
