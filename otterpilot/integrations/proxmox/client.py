from __future__ import annotations

from typing import Any

import requests
import urllib3
import yaml

from otterpilot.core.config import config_path
from otterpilot.core.secrets import get_secret


class ProxmoxAPIError(RuntimeError):
    """Erro ao consultar a API do Proxmox VE."""


class ProxmoxClient:
    def __init__(self) -> None:
        config_file = config_path("proxmox.yaml")

        with config_file.open(
            "r",
            encoding="utf-8",
        ) as f:
            config = yaml.safe_load(f) or {}

        proxmox_config = config.get("proxmox", {})

        self.base_url = str(
            proxmox_config.get("url", "")
        ).rstrip("/")

        if not self.base_url:
            raise ProxmoxAPIError(
                "URL do Proxmox não configurada em config/proxmox.yaml"
            )

        self.verify_ssl = bool(
            proxmox_config.get(
                "verify_ssl",
                True,
            )
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
