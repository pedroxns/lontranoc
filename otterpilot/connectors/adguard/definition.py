from otterpilot.core.registry import (
    ComponentStatus,
    ConnectorDefinition,
    SettingDefinition,
)


ADGUARD_CONNECTOR = ConnectorDefinition(
    connector_id="adguard",
    display_name="AdGuard Home",
    description=(
        "Saúde e filtragem de DNS do AdGuard Home."
    ),
    capabilities=("dns",),
    status=ComponentStatus.ENABLED,
    read_only_default=True,
    supports_discovery=True,
    settings=tuple(
        setting
        for n in (1, 2, 3)
        for setting in (
            SettingDefinition(key=f"ADGUARD{n}_NAME", label="Nome", group=f"Instância {n}"),
            SettingDefinition(key=f"ADGUARD{n}_HOST", label="Host", group=f"Instância {n}"),
            SettingDefinition(
                key=f"ADGUARD{n}_PORT", label="Porta", kind="int", default="80",
                group=f"Instância {n}",
            ),
            SettingDefinition(
                key=f"ADGUARD{n}_HTTPS", label="HTTPS", kind="bool", default="false",
                group=f"Instância {n}",
            ),
            SettingDefinition(key=f"ADGUARD{n}_USER", label="Usuário", group=f"Instância {n}"),
            SettingDefinition(
                key=f"ADGUARD{n}_PASS", label="Senha", kind="secret", group=f"Instância {n}",
            ),
        )
    ),
)
