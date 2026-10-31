from __future__ import annotations

import socket
from dataclasses import dataclass
from datetime import datetime, timezone

import requests

from otterpilot.core.config import NotConfiguredError, get_env

HOSTNAME = socket.gethostname()


@dataclass(frozen=True, slots=True)
class IngestSettings:
    url: str
    org: str
    user: str
    token: str


def load_settings() -> IngestSettings:
    url = get_env("OPENOBSERVE_URL")
    user = get_env("OPENOBSERVE_INGEST_USER")
    token = get_env("OPENOBSERVE_INGEST_TOKEN")

    if not (url and user and token):
        raise NotConfiguredError("OpenObserve (ingestão) não configurado")

    return IngestSettings(
        url=url.rstrip("/"),
        org=get_env("OPENOBSERVE_ORG", "default") or "default",
        user=user,
        token=token,
    )


def is_configured() -> bool:
    try:
        load_settings()
    except NotConfiguredError:
        return False

    return True


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def build_event(
    service: str,
    component: str,
    event_type: str,
    message: str,
    severity: str = "info",
    status: str = "ok",
    **fields,
):
    event = {
        "timestamp": now_iso(),
        "service": service,
        "component": component,
        "event_type": event_type,
        "severity": severity,
        "status": status,
        "message": message,
        "source": HOSTNAME,
    }

    event.update(fields)
    return event


def send_log(stream: str, event: dict):
    settings = load_settings()

    response = requests.post(
        f"{settings.url}/api/{settings.org}/{stream}/_json",
        json=[event],
        auth=(settings.user, settings.token),
        headers={"Content-Type": "application/json"},
        timeout=10,
    )

    response.raise_for_status()
    return response.json()


def emit(
    stream: str,
    service: str,
    component: str,
    event_type: str,
    message: str,
    severity: str = "info",
    status: str = "ok",
    **fields,
):
    event = build_event(
        service=service,
        component=component,
        event_type=event_type,
        message=message,
        severity=severity,
        status=status,
        **fields,
    )

    return send_log(stream, event)


def record(
    stream: str,
    **fields,
) -> bool:
    """Registra um evento histórico sem nunca propagar falhas.

    Usado por componentes cuja função principal não pode parar quando o
    histórico está indisponível ou não configurado (ex.: Copilot).
    """

    if not is_configured():
        return False

    try:
        emit(stream=stream, **fields)
    except Exception as error:
        print(f"[openobserve] Falha ao registrar evento: {error}", flush=True)
        return False

    return True
