from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from collections import defaultdict, deque
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
