import os
import socket
from datetime import datetime, timezone

import requests
from otterpilot.core.config import get_env

OO_URL = get_env("OPENOBSERVE_URL", required=True)
OO_ORG = get_env("OPENOBSERVE_ORG", "default")
OO_USER = get_env("OPENOBSERVE_INGEST_USER", required=True)
OO_TOKEN = get_env("OPENOBSERVE_INGEST_TOKEN", required=True)

HOSTNAME = socket.gethostname()


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
    url = f"{OO_URL}/api/{OO_ORG}/{stream}/_json"

    response = requests.post(
        url,
        json=[event],
        auth=(OO_USER, OO_TOKEN),
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
