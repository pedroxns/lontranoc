from __future__ import annotations

import time

import requests

from otterpilot.core.config import NotConfiguredError, get_env


def _settings() -> tuple[str, str, tuple[str, str]]:
    url = get_env("OPENOBSERVE_URL")
    user = get_env("OPENOBSERVE_READ_USER") or get_env("OPENOBSERVE_INGEST_USER")
    token = get_env("OPENOBSERVE_READ_TOKEN") or get_env("OPENOBSERVE_INGEST_TOKEN")

    if not (url and user and token):
        raise NotConfiguredError("OpenObserve (consulta) não configurado")

    org = get_env("OPENOBSERVE_ORG", "default") or "default"

    return url.rstrip("/"), org, (user, token)


def is_configured() -> bool:
    try:
        _settings()
    except NotConfiguredError:
        return False

    return True


def search_logs(
    sql: str,
    hours: int = 24,
    size: int = 100,
    start_time: int | None = None,
    end_time: int | None = None,
) -> list[dict]:
    url, org, auth = _settings()

    if end_time is None:
        end_time = int(time.time() * 1_000_000)

    if start_time is None:
        start_time = end_time - (hours * 60 * 60 * 1_000_000)

    payload = {
        "query": {
            "sql": sql,
            "from": 0,
            "size": size,
            "start_time": start_time,
            "end_time": end_time,
        }
    }

    response = requests.post(
        f"{url}/api/{org}/_search",
        json=payload,
        auth=auth,
        headers={"Content-Type": "application/json"},
        timeout=20,
    )

    if not response.ok:
        raise RuntimeError(
            f"OpenObserve respondeu {response.status_code}: {response.text[:300]}"
        )

    return response.json().get("hits", [])


def list_streams() -> list[str]:
    url, org, auth = _settings()

    response = requests.get(
        f"{url}/api/{org}/streams",
        params={"type": "logs"},
        auth=auth,
        timeout=10,
    )
    response.raise_for_status()

    return [
        item.get("name")
        for item in response.json().get("list", [])
        if item.get("name")
    ]
