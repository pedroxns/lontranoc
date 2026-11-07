"""Catálogo de configurações exposto pela API de gerenciamento."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from otterpilot.core.config import connector_enabled, get_env, update_env_file
from otterpilot.core.registry import ConnectorDefinition, SettingDefinition
from otterpilot.core.registry.bootstrap import build_default_registry
from otterpilot.core.secrets import has_credential


class SettingsValidationError(ValueError):
    """Valor inválido enviado para uma configuração."""


@dataclass(frozen=True)
class SettingsGroup:
    group_id: str
    name: str
    description: str
    settings: tuple[SettingDefinition, ...]
    connector: ConnectorDefinition | None = None


PLATFORM_GROUPS = (
    SettingsGroup(
        group_id="mqtt",
        name="Broker MQTT",
        description=(
            "Usado pelo Zigbee2MQTT, pelas detecções do Frigate e pelo Copilot "
            "via Home Assistant."
        ),
        settings=(
            SettingDefinition(key="MQTT_HOST", label="Host", required=True),
            SettingDefinition(key="MQTT_PORT", label="Porta", kind="int", default="1883"),
            SettingDefinition(key="MQTT_USERNAME", label="Usuário"),
            SettingDefinition(key="MQTT_PASSWORD", label="Senha", kind="secret"),
        ),
    ),
    SettingsGroup(
        group_id="openobserve",
        name="OpenObserve",
        description=(
            "Histórico de eventos. Opcional: sem ele o estado atual continua "
            "funcionando, mas o Copilot e a Atividade ficam sem histórico."
        ),
        settings=(
            SettingDefinition(key="OPENOBSERVE_URL", label="URL", kind="url", required=True),
            SettingDefinition(key="OPENOBSERVE_ORG", label="Organização", default="default"),
            SettingDefinition(
                key="OPENOBSERVE_INGEST_USER", label="Usuário de ingestão", required=True,
            ),
            SettingDefinition(
                key="OPENOBSERVE_INGEST_TOKEN", label="Token de ingestão", kind="secret",
                required=True,
            ),
            SettingDefinition(
                key="OPENOBSERVE_READ_USER", label="Usuário de leitura",
                help="Opcional. Vazio usa o usuário de ingestão.",
            ),
            SettingDefinition(
                key="OPENOBSERVE_READ_TOKEN", label="Token de leitura", kind="secret",
            ),
        ),
    ),
)


def connector_groups() -> tuple[SettingsGroup, ...]:
    return tuple(
        SettingsGroup(
            group_id=connector.connector_id,
            name=connector.display_name,
            description=connector.description,
            settings=connector.settings,
            connector=connector,
        )
        for connector in build_default_registry().list_connectors()
        if connector.settings
    )


def all_groups() -> tuple[SettingsGroup, ...]:
    return PLATFORM_GROUPS + connector_groups()


def find_group(group_id: str) -> SettingsGroup:
    for group in all_groups():
        if group.group_id == group_id:
            return group

    raise KeyError(group_id)


def _setting_state(setting: SettingDefinition) -> dict[str, Any]:
    raw = get_env(setting.key)
    from_credential = bool(setting.credential and has_credential(setting.credential))

    if from_credential:
        source = "credential"
    elif raw is not None:
        source = "env"
    elif setting.default is not None:
        source = "default"
    else:
        source = "unset"

    state: dict[str, Any] = {
        "key": setting.key,
        "label": setting.label,
        "kind": setting.kind,
        "required": setting.required,
        "default": setting.default,
        "help": setting.help,
        "group": setting.group,
        "source": source,
        "is_set": source in ("env", "credential"),
    }

    if setting.kind != "secret":
        state["value"] = raw

    return state


def is_satisfied(setting: SettingDefinition) -> bool:
    if setting.credential and has_credential(setting.credential):
        return True

    return get_env(setting.key) is not None or setting.default is not None


def missing_required(group: SettingsGroup) -> list[str]:
    return [
        setting.key
        for setting in group.settings
        if setting.required and not is_satisfied(setting)
    ]


def describe_group(group: SettingsGroup) -> dict[str, Any]:
    missing = missing_required(group)

    return {
        "id": group.group_id,
        "name": group.name,
        "description": group.description,
        "kind": "connector" if group.connector else "platform",
        "enabled": connector_enabled(group.group_id) if group.connector else True,
        "configured": not missing,
        "missing": missing,
        "settings": [_setting_state(setting) for setting in group.settings],
    }


def _normalize(setting: SettingDefinition, value: Any) -> str | None:
    if value is None:
        return None

    text = str(value).strip()

    if text == "":
        return None

    if setting.kind == "int":
        try:
            number = int(text)
        except ValueError as error:
            raise SettingsValidationError(f"{setting.label}: informe um número inteiro") from error

        if number < 0:
            raise SettingsValidationError(f"{setting.label}: valor não pode ser negativo")

        return str(number)

    if setting.kind == "bool":
        if text.lower() in ("true", "1", "sim", "yes", "on"):
            return "true"

        if text.lower() in ("false", "0", "não", "nao", "no", "off"):
            return "false"

        raise SettingsValidationError(f"{setting.label}: valor booleano inválido")

    if setting.kind == "url" and not text.startswith(("http://", "https://")):
        raise SettingsValidationError(f"{setting.label}: a URL precisa começar com http:// ou https://")

    if setting.kind == "list":
        return ",".join(item.strip() for item in text.split(",") if item.strip())

    if "\n" in text:
        raise SettingsValidationError(f"{setting.label}: quebras de linha não são permitidas")

    return text


def update_group(
    group: SettingsGroup,
    values: dict[str, Any],
    enabled: bool | None = None,
) -> dict[str, Any]:
    """Aplica alterações de um grupo no .env.

    Para segredos, string vazia mantém o valor atual e null remove.
    Para os demais campos, vazio ou null removem (volta ao padrão).
    """

    known = {setting.key: setting for setting in group.settings}
    unknown = sorted(set(values) - set(known))

    if unknown:
        raise SettingsValidationError(f"Campos desconhecidos: {', '.join(unknown)}")

    updates: dict[str, str | None] = {}

    for key, raw in values.items():
        setting = known[key]

        if setting.kind == "secret" and raw == "":
            continue

        updates[key] = _normalize(setting, raw)

    if enabled is not None and group.connector:
        updates[f"{group.group_id.upper()}_ENABLED"] = None if enabled else "false"

    if updates:
        update_env_file(updates)

    return describe_group(group)
