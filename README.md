# OtterPilot

Observabilidade e copiloto para homelabs e pequenos ambientes self-hosted,
por Lontra Labs.

O OtterPilot coleta o estado de Proxmox, Home Assistant, AdGuard, Frigate,
Zigbee2MQTT e Ollama, normaliza tudo em *capabilities* (hosts, virtualização,
DNS, UPS, câmeras…), mantém o estado atual num SQLite local, envia o histórico
para o OpenObserve (opcional) e responde perguntas sobre o ambiente com um LLM
local — pela interface web ou por MQTT (Home Assistant).

## Instalação

Requisitos: Debian/Ubuntu com systemd e Python 3.11+ (`apt install python3-venv git`).

```bash
sudo git clone https://github.com/pedroxns/lontranoc.git /opt/otterpilot
cd /opt/otterpilot && git checkout refactor/otterpilot
sudo deploy/install.sh
```

O instalador cria o usuário `otterpilot`, o venv em `/opt/otterpilot/venv`,
a configuração em `/etc/otterpilot`, o estado em `/var/lib/otterpilot`,
habilita os serviços e imprime o endereço da interface e a senha inicial.

## Configuração

Abra `http://<host>:8470/`, entre com a senha e vá em **Integrações**: cada
integração tem um formulário, um botão **Testar conexão** e pode ser
desativada. Os serviços reiniciam sozinhos quando a configuração muda.
Integrações sem configuração ficam inativas, sem erros.

| Onde | O quê |
|---|---|
| Integrações | Conexões (MQTT, OpenObserve, Proxmox, Home Assistant…) |
| Configurações › Coleta | Intervalo de cada coleta |
| Configurações › Políticas | Estado esperado e importância de cada VM/container |
| Configurações › Arquivos | `proxmox.yaml` e `vehicle.yaml` |
| Configurações › Sistema | Serviços, versão e senha |

Por baixo, a configuração fica em `/etc/otterpilot/.env` e
`/etc/otterpilot/config/*.yaml` (exemplos em `deploy/`). As personas ficam em
`/etc/otterpilot/config/copilot/` e mudam sem reiniciar nada. Os tokens do Proxmox
também podem vir de credenciais systemd em `/etc/otterpilot/credentials/`,
que têm precedência.

## Operação

```bash
systemctl status 'otterpilot-*'       # serviços
journalctl -u otterpilot-scheduler -f # logs da coleta
otterpilot status                     # resumo do estado atual
sudo otterpilot set-password          # redefine a senha da interface
sudo otterpilot token create <nome>    # token de serviço (ex.: aparelho de mesa); mostrado uma vez
sudo otterpilot token list|revoke      # lista ou revoga tokens
```

| Serviço | Função |
|---|---|
| `otterpilot-scheduler` | Coletas periódicas (polling) |
| `otterpilot-zigbee2mqtt` | Saúde das bridges Zigbee2MQTT via MQTT |
| `otterpilot-frigate` | Detecções do Frigate via MQTT |
| `otterpilot-copilot` | Perguntas/respostas via MQTT (`otterpilot/request` → `otterpilot/response`) |
| `otterpilot-api` | API e interface web (porta 8470) |

## Atualização

```bash
cd /opt/otterpilot && sudo git pull && sudo deploy/install.sh
```

## Desenvolvimento

```bash
python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'
.venv/bin/pytest -q
OTTERPILOT_ROOT=/tmp/op OTTERPILOT_STATE_DB=/tmp/op/state.db .venv/bin/python -m otterpilot.api
```

Arquitetura: [`architecture/ARCHITECTURE.md`](architecture/ARCHITECTURE.md).
Canal de voz (aparelho de mesa): [`architecture/VOICE_CHANNEL.md`](architecture/VOICE_CHANNEL.md).
Runtime de produção: [`architecture/RUNTIME_INVENTORY.md`](architecture/RUNTIME_INVENTORY.md).
