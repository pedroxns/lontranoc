# OtterPilot — Runtime de produção

Atualizado em 2026-10-30 (versão 0.5.0, branch `refactor/otterpilot`).

## Host

| Item | Valor |
|---|---|
| Host | `Jambroba-tech` — 192.168.70.10, LXC 1001 (Debian 13, Python 3.13) |
| Código | checkout git em `/opt/otterpilot` |
| Instalação | `/opt/otterpilot/venv` (pacote não editável, via `deploy/install.sh`) |
| Usuário | `otterpilot` (sistema, sem login) |
| Interface | `http://192.168.70.10:8470/` |

Migrado do `openwebui-ollama` (192.168.10.20, LXC 910) em 2026-10-30. O .20
continua com o Ollama (GPU) e o cron `ollama_latency.sh`
(`/usr/local/bin/ollama_latency.sh`, publica `homelab/ollama/latency`).
Backup do runtime antigo: `/root/lontranoc-archive-2026-10-30.tar.gz` no .20.

## Serviços

Fonte: `deploy/systemd/`. Todos com `Restart=always`, `ProtectSystem=strict`,
`OTTERPILOT_ROOT=/etc/otterpilot`.

| Unit | Processo | Função |
|---|---|---|
| `otterpilot-scheduler` | `python -m otterpilot.core.scheduler` | 9 coletas periódicas |
| `otterpilot-zigbee2mqtt` | `python -m otterpilot.integrations.zigbee2mqtt.mqtt_provider` | bridges `z2m1`, `z2m2` |
| `otterpilot-frigate` | `python -m otterpilot.integrations.frigate.mqtt_provider` | detecções do Frigate |
| `otterpilot-copilot` | `python -m otterpilot.copilot.assistant` | Copilot via MQTT |
| `otterpilot-api` | `python -m otterpilot.api` | API e interface (0.0.0.0:8470) |

Os quatro primeiros reiniciam sozinhos quando `.env` ou `config/*.yaml`
mudam (`core.config.watch_config`). A API relê a configuração a cada
requisição e não reinicia.

## Configuração e estado

| Caminho | Dono / modo | Conteúdo |
|---|---|---|
| `/etc/otterpilot/` | `root:otterpilot` 0770 | raiz da configuração |
| `/etc/otterpilot/.env` | `otterpilot` 0600 | conexões e secrets (editável pela interface) |
| `/etc/otterpilot/config/proxmox.yaml` | `otterpilot` 0640 | política de workloads |
| `/etc/otterpilot/config/vehicle.yaml` | `otterpilot` 0640 | entidades do veículo |
| `/etc/otterpilot/config/copilot/` | `otterpilot` | personas editadas/próprias (`personas/`), avatares enviados (`avatars/`) e persona por canal (`settings.yaml`); fora do `watch_config`, lidos a cada pergunta |
| `/etc/otterpilot/auth.json` | `otterpilot` 0600 | hash da senha e chave de sessão |
| `/etc/otterpilot/credentials/` | `root` 0700 | tokens Proxmox (`LoadCredential`, precedência sobre o `.env`) |
| `/var/lib/otterpilot/state.db` | `otterpilot` | State Store: `current_state`, `job_status`, `component_status` |

Backup da configuração anterior ao 0.5.0: `/root/otterpilot-etc-backup-2026-10-30.tar.gz`.

## Dependências externas

| Serviço | Endereço | Uso |
|---|---|---|
| MQTT (EMQX) | 192.168.20.10:1883 | Zigbee2MQTT, Frigate, Copilot |
| OpenObserve | 192.168.10.40:5080 | histórico, Atividade, Copilot |
| Home Assistant | 192.168.68.11:8123 | UPS, rack, veículo |
| Proxmox VE | 192.168.10.2:8006 | hosts e virtualização |
| AdGuard | 192.168.10.10, 192.168.10.11 | DNS |
| Frigate | 192.168.10.30:5000 | saúde das câmeras |
| Ollama | 192.168.10.20:11434 | `llm_runtime` e Copilot (`qwen3.5:9b`) |

## MQTT

| Direção | Tópico | Componente |
|---|---|---|
| sub | `z2m1/bridge/{state,health,info,logging}`, idem `z2m2` | zigbee2mqtt |
| sub | `frigate/events`, `frigate/+/{motion,person,dog}` | frigate |
| sub | `homelab/lontranoc/request`, `otterpilot/request` | copilot |
| pub | `homelab/lontranoc/response`, `otterpilot/response` | copilot (payload inclui `persona`, o nome de quem respondeu) |

## Operação

```bash
systemctl status 'otterpilot-*'
journalctl -u otterpilot-scheduler -f
otterpilot status
sudo otterpilot set-password
cd /opt/otterpilot && git pull && sudo deploy/install.sh   # atualização
```
