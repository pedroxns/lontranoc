from __future__ import annotations

from typing import Any

import requests

from otterpilot.core.config import NotConfiguredError, get_env


class HomeAssistantClient:
    """Acesso de leitura à API REST do Home Assistant."""

    def __init__(
        self,
        token_env: str | None = None,
    ) -> None:
        url = get_env("HA_URL")
        token = (get_env(token_env) if token_env else None) or get_env("HA_TOKEN")

        if not (url and token):
            raise NotConfiguredError("Home Assistant não configurado (HA_URL/HA_TOKEN)")

        self.base_url = url.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    def get_state(
        self,
        entity_id: str,
    ) -> dict[str, Any] | None:
        response = requests.get(
            f"{self.base_url}/api/states/{entity_id}",
            headers=self._headers,
            timeout=10,
        )

        if response.status_code == 404:
            return None

        response.raise_for_status()

        return response.json()

    def get_states(self) -> dict[str, dict[str, Any]]:
        response = requests.get(
            f"{self.base_url}/api/states",
            headers=self._headers,
            timeout=20,
        )
        response.raise_for_status()

        return {item["entity_id"]: item for item in response.json()}


def required_entity(name: str) -> str:
    entity_id = get_env(name)

    if not entity_id:
        raise NotConfiguredError(f"Entidade do Home Assistant não configurada: {name}")

    return entity_id
