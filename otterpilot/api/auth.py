from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import secrets
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from otterpilot.core.config import PROJECT_ROOT, _atomic_write

AUTH_FILE = PROJECT_ROOT / "auth.json"

SESSION_COOKIE = "otterpilot_session"
SESSION_TTL_SECONDS = 7 * 24 * 3600

MIN_PASSWORD_LENGTH = 8

# Proteção simples contra força bruta: tentativas falhas por IP.
LOGIN_WINDOW_SECONDS = 300
LOGIN_MAX_FAILURES = 10
_failures: dict[str, deque[float]] = defaultdict(deque)

_SCRYPT = {"n": 2**14, "r": 8, "p": 1}

# Tokens de serviço: credenciais de máquinas (o aparelho de mesa, por exemplo).
# O token só aparece uma vez, na criação; em disco fica o hash. Cada token tem
# escopos e pode ser revogado sem afetar a senha nem os outros tokens.
SERVICE_TOKEN_PREFIX = "otp_"
SCOPE_COPILOT_VOICE = "copilot:voice"
KNOWN_SCOPES = (SCOPE_COPILOT_VOICE,)
TOKEN_NAME = re.compile(r"^[a-z0-9][a-z0-9_-]{0,39}$")


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, dklen=32, **_SCRYPT)
    return f"scrypt${_SCRYPT['n']}${_SCRYPT['r']}${_SCRYPT['p']}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, n, r, p, salt, digest = encoded.split("$")
    except ValueError:
        return False

    if scheme != "scrypt":
        return False

    candidate = hashlib.scrypt(
        password.encode(),
        salt=_unb64(salt),
        n=int(n),
        r=int(r),
        p=int(p),
        dklen=len(_unb64(digest)),
    )

    return hmac.compare_digest(candidate, _unb64(digest))


def load_auth(path: Path | None = None) -> dict[str, Any]:
    path = path or AUTH_FILE

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}


def save_auth(data: dict[str, Any], path: Path | None = None) -> None:
    _atomic_write(path or AUTH_FILE, json.dumps(data, indent=2) + "\n")


def set_password(password: str, path: Path | None = None) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"A senha precisa ter ao menos {MIN_PASSWORD_LENGTH} caracteres")

    data = load_auth(path)
    data["password_hash"] = hash_password(password)
    data.setdefault("secret_key", secrets.token_urlsafe(32))
    save_auth(data, path)


def password_configured(path: Path | None = None) -> bool:
    return bool(load_auth(path).get("password_hash"))


def _signing_key(data: dict[str, Any]) -> bytes:
    # O hash da senha entra na chave: trocar a senha invalida as sessões.
    return (data["secret_key"] + data["password_hash"]).encode()


def create_session(path: Path | None = None) -> str:
    data = load_auth(path)
    body = _b64(json.dumps({"exp": int(time.time()) + SESSION_TTL_SECONDS}).encode())
    signature = _b64(hmac.new(_signing_key(data), body.encode(), hashlib.sha256).digest())
    return f"{body}.{signature}"


def validate_session(token: str | None, path: Path | None = None) -> bool:
    if not token or "." not in token:
        return False

    data = load_auth(path)

    if not data.get("password_hash") or not data.get("secret_key"):
        return False

    body, signature = token.rsplit(".", 1)
    expected = _b64(hmac.new(_signing_key(data), body.encode(), hashlib.sha256).digest())

    if not hmac.compare_digest(signature, expected):
        return False

    try:
        return json.loads(_unb64(body))["exp"] > time.time()
    except (ValueError, KeyError):
        return False


def login_allowed(client: str) -> bool:
    attempts = _failures[client]
    cutoff = time.monotonic() - LOGIN_WINDOW_SECONDS

    while attempts and attempts[0] < cutoff:
        attempts.popleft()

    return len(attempts) < LOGIN_MAX_FAILURES


def register_failure(client: str) -> None:
    _failures[client].append(time.monotonic())


def reset_failures(client: str) -> None:
    _failures.pop(client, None)


# ----------------------------------------------------------- tokens de serviço


def _token_digest(token: str) -> str:
    # O token tem 256 bits aleatórios: um hash rápido basta (scrypt é para senhas).
    return hashlib.sha256(token.encode()).hexdigest()


def create_service_token(name: str, scopes: list[str], path: Path | None = None) -> str:
    """Cria um token de serviço e o devolve (única vez em que ele existe em claro)."""

    if not TOKEN_NAME.match(name):
        raise ValueError("Nome inválido: use letras minúsculas, números, '-' ou '_' (até 40 caracteres)")

    if not scopes or any(scope not in KNOWN_SCOPES for scope in scopes):
        raise ValueError(f"Escopo inválido. Conhecidos: {', '.join(KNOWN_SCOPES)}")

    data = load_auth(path)
    tokens = data.setdefault("service_tokens", {})

    if name in tokens:
        raise ValueError(f"Já existe um token chamado {name}")

    token = SERVICE_TOKEN_PREFIX + secrets.token_urlsafe(32)
    tokens[name] = {
        "hash": _token_digest(token),
        "scopes": sorted(set(scopes)),
        "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    save_auth(data, path)

    return token


def revoke_service_token(name: str, path: Path | None = None) -> bool:
    data = load_auth(path)

    if name not in (data.get("service_tokens") or {}):
        return False

    del data["service_tokens"][name]
    save_auth(data, path)

    return True


def list_service_tokens(path: Path | None = None) -> list[dict[str, Any]]:
    """Nome, escopos e data de cada token (nunca o hash nem o token)."""

    tokens = load_auth(path).get("service_tokens") or {}

    return [
        {"name": name, "scopes": entry.get("scopes", []), "created": entry.get("created")}
        for name, entry in sorted(tokens.items())
    ]


def verify_service_token(token: str | None, scope: str, path: Path | None = None) -> str | None:
    """Nome do token se ele existe e tem o escopo pedido; senão None."""

    if not token or not token.startswith(SERVICE_TOKEN_PREFIX):
        return None

    digest = _token_digest(token)
    found: str | None = None

    # Percorre todos, sem parar no primeiro: o tempo não revela qual existe.
    for name, entry in (load_auth(path).get("service_tokens") or {}).items():
        if hmac.compare_digest(digest, str(entry.get("hash", ""))) and scope in entry.get("scopes", []):
            found = name

    return found
