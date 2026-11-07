from __future__ import annotations

from typing import Any

import requests
import urllib3
import yaml

from otterpilot.core.config import NotConfiguredError, config_path, get_bool, get_env
from otterpilot.core.secrets import get_secret


class ProxmoxAPIError(RuntimeError):
    """Erro ao consultar a API do Proxmox VE."""


def load_proxmox_file() -> dict[str, Any]:
    """Seção `proxmox` do proxmox.yaml (opcional)."""

    path = config_path("proxmox.yaml", must_exist=False)

    if not path.is_file():
        return {}

    with path.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}

    return config.get("proxmox", {}) or {}


class ProxmoxClient:
    def __init__(self) -> None:
        file_config = load_proxmox_file()

        self.base_url = str(
            get_env("PROXMOX_URL")
            or file_config.get("url", "")
        ).rstrip("/")

        if not self.base_url:
            raise NotConfiguredError("Proxmox não configurado (PROXMOX_URL)")

        self.verify_ssl = get_bool(
            "PROXMOX_VERIFY_SSL",
            bool(file_config.get("verify_ssl", True)),
        )

        self.token_id = get_secret(
            "proxmox_token_id",
            env_name="PROXMOX_TOKEN_ID",
            required=True,
        )

        self.token_secret = get_secret(
            "proxmox_token_secret",
            env_name="PROXMOX_TOKEN_SECRET",
            required=True,
        )

        if not self.verify_ssl:
            urllib3.disable_warnings(
                urllib3.exceptions.InsecureRequestWarning
            )

        self.session = requests.Session()

        self.session.headers.update({
            "Authorization": (
                f"PVEAPIToken={self.token_id}="
                f"{self.token_secret}"
            ),
        })

    def get(
        self,
        path: str,
    ) -> Any:
        url = (
            f"{self.base_url}/api2/json/"
            f"{path.lstrip('/')}"
        )

        try:
            response = self.session.get(
                url,
                timeout=10,
                verify=self.verify_ssl,
            )

            response.raise_for_status()

        except requests.RequestException as error:
            raise ProxmoxAPIError(
                f"Erro ao consultar Proxmox: {path}: "
                f"{error}"
            ) from error

        body = response.json()

        if "data" not in body:
            raise ProxmoxAPIError(
                f"Resposta inválida do Proxmox: {path}"
            )

        return body["data"]

    def cluster_status(self) -> Any:
        return self.get("cluster/status")

    def nodes(self) -> Any:
        return self.get("nodes")

    def cluster_resources(self) -> Any:
        return self.get(
            "cluster/resources"
        )
