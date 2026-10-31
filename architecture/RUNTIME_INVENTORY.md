# OtterPilot — Runtime Inventory (Fase B)

Levantado em 2026-10-30 no host de produção `openwebui-ollama` (192.168.10.20,
`lxc/910`) e no código de `refactor/otterpilot` (`f8e16f6`).

> **Atualização 2026-10-30 — migração concluída.** O runtime saiu do `openwebui-ollama`
> (192.168.10.20) e foi para `Jambroba-tech` (192.168.70.10, LXC 1001):
> código `/opt/otterpilot`, venv `/opt/otterpilot/venv` (instalação não-editável),
> config `/etc/otterpilot/{.env,config/}` via `OTTERPILOT_ROOT`, credenciais
> `/etc/otterpilot/credentials/`, estado `/var/lib/otterpilot/`, usuário `otterpilot`,
> units `otterpilot-{scheduler,zigbee2mqtt,frigate,copilot}` (fonte: `deploy/`).
> Ollama e o cron `ollama_latency.sh` continuam no .20; os units antigos lá estão
> parados e desabilitados (rollback). Proxmox corrigido para `192.168.10.2`.
> O restante deste documento descreve o runtime **antes** da migração.

---

## 0. Host

| Item | Valor |
|---|---|
| Host | `openwebui-ollama` — LXC 910, Debian 13, 12 vCPU, 14 GiB RAM, disco 100 G (67%) |
| Co-residentes | Ollama (`:11434`, GPU), whisper (`:8883`), chatterbox (`:8882`), wyoming-f5-tts (`:10220`) |
| Instalação | checkout git em `/opt/lontranoc` (dono `pedro`), branch `refactor/otterpilot` |
| Python | venv `/opt/lontranoc/venv`, Python 3.13.5, `pip install -e /opt/lontranoc` |
| Usuário de execução | `pedro:pedro` em todos os units |

> **Produção ≠ HEAD.** Há modificações não commitadas — ver seção 7.

## 1. Processos / systemd

Todos em `/etc/systemd/system/`, `enabled`, `active (running)`, `Restart=always`,
`WorkingDirectory=/opt/lontranoc`, `ExecStart=/opt/lontranoc/venv/bin/python ...`.
Nenhum define `EnvironmentFile` — o `.env` é lido pelo próprio código.

| Unit | Entrypoint | Extra |
|---|---|---|
| `otterpilot-scheduler.service` | `-m otterpilot.core.scheduler` | `LoadCredential=proxmox_token_{id,secret}`; **linha 1 corrompida** (ver 7) |
| `otterpilot-zigbee2mqtt.service` | `-m otterpilot.integrations.zigbee2mqtt.mqtt_provider` | — |
| `lontranoc-frigate-mqtt.service` | `-m otterpilot.integrations.frigate.mqtt_provider` | — |
| `lontranoc-assistant.service` | `/opt/lontranoc/lontranoc_assistant.py` | `After=ollama.service` |

Sem timers systemd. Cron do usuário `pedro`:

```
*/3 * * * * /opt/lontranoc/ollama_latency.sh
```

Nenhum processo OtterPilot escuta porta TCP — não existe API/HTTP server.

## 2. Jobs do scheduler

Hardcoded em `otterpilot/core/scheduler/bootstrap.py`:

| job_id | connector / capability | intervalo | estado em 2026-10-30 |
|---|---|---:|---|
| frigate-camera-health | frigate / camera_health | 60s | ok |
| adguard-dns | adguard / dns | 60s | ok |
| homeassistant-vehicle | homeassistant / vehicle | 180s | ok |
| ollama-llm-runtime | ollama / llm_runtime | 120s | ok |
| homeassistant-ups | homeassistant / ups | 30s | ok (entidade HA `unavailable`) |
| proxmox-host-health | proxmox / host_health | 60s | **falhando desde 2026-09-10** |
| homeassistant-environment-health | homeassistant / environment_health | 60s | ok (entidade HA `unavailable`) |
| otterpilot-system-health | otterpilot / system_health | 60s | ok |
| proxmox-virtualization | proxmox / virtualization | 60s | **falhando desde 2026-09-10** |

`zigbee_health` e `object_detection` chegam por MQTT (processos próprios).

## 3. Configuração

### Arquivos

| Caminho | Consumidor |
|---|---|
| `/opt/lontranoc/.env` | `core/config.py` (via `OTTERPILOT_ROOT` ou raiz do código) |
| `/opt/lontranoc/config/proxmox.yaml` | proxmox client + virtualization |
| `/opt/lontranoc/config/vehicle.yaml` | vehicle |
| `/opt/lontranoc/config/routes.yaml` | copilot (`routing/context_router.py`) |

### Variáveis — código × `.env` de produção

| Variável | Default no código | Em produção |
|---|---|---|
| `OTTERPILOT_ROOT` | raiz do código | ausente |
| `OTTERPILOT_STATE_DB` | `/var/lib/otterpilot/state.db` | ausente (usa default) |
| `MQTT_HOST` / `MQTT_PORT` | — / 1883 | `192.168.20.10` / 1883 (sem auth) |
| `OPENOBSERVE_URL` | obrigatório | `http://192.168.10.40:5080` |
| `OPENOBSERVE_ORG` | `default` | `default` |
| `OPENOBSERVE_INGEST_USER/TOKEN` | obrigatório | definido |
| `OPENOBSERVE_READ_USER/TOKEN` | — | definido |
| `HA_URL` / `HA_TOKEN` | obrigatório | `http://192.168.68.11:8123` / definido |
| `HA_TOKEN_VEHICLE` | — | **ausente** |
| `UPS_STATUS_ENTITY` / `UPS_BATTERY_ENTITY` | `sensor.dnb_status` / `sensor.dnb_carga_da_bateria` | ausente (usa default) |
| `RACK_TEMP_ENTITY` | `sensor.clima_servidor_temperature` | ausente (usa default) |
| `ADGUARD{1,2}_NAME/HOST/PORT/USER/PASS` | port 80 | `192.168.10.10`, `192.168.10.11` |
| `ADGUARD{n}_HTTPS` | `false` | `ADGUARD2_HTTPS`; **`ADGUARD_HTTPS` (sem número, ignorado)** |
| `FRIGATE_URL` | `http://192.168.10.30:5000` | igual |
| `OLLAMA_URL` / `OLLAMA_MODEL` | `localhost:11434` / `qwen2.5:7b-instruct` (HEAD) | `localhost:11434` / `qwen3.5:9b` |

### Secrets

| Secret | Origem em produção |
|---|---|
| `proxmox_token_id`, `proxmox_token_secret` | `/etc/otterpilot/credentials/` (root 0600) → `LoadCredential` |
| HA, OpenObserve, AdGuard | `.env` em texto plano (0664, `pedro`) |

## 4. Armazenamento persistente

| Caminho | Dono / modo | Conteúdo |
|---|---|---|
| `/var/lib/otterpilot/` | `pedro` 0750 | `state.db` (68 KB) + WAL (4 MB) + shm |
| `/etc/otterpilot/credentials/` | `root` 0700 | tokens Proxmox |
| `/opt/lontranoc/.env` | `pedro` 0664 | env + secrets |
| `/opt/lontranoc/config/` | `pedro` | YAML |
| journald | — | logs (journal total 281 MB; frigate-mqtt ~55 mil linhas/dia) |

State Store em 2026-10-30: 52 linhas em `current_state`
(`connector, capability, resource_id, event_type, event_id, timestamp, severity,
status, message, payload_json, metadata_json`).

## 5. Dependências externas

| Serviço | Endereço | Alcançável do host | Usado por |
|---|---|---|---|
| MQTT (EMQX) | `192.168.20.10:1883` | ok | z2m, frigate, copilot, `ollama_latency.sh` |
| OpenObserve | `192.168.10.40:5080` | ok | **todo processo que importa o EventBus** |
| Home Assistant | `192.168.68.11:8123` | ok | vehicle, ups, environment |
| Proxmox | `192.168.68.5:8006` | **FAIL — No route to host** | host_health, virtualization |
| AdGuard | `192.168.10.10`, `.11` | ok | dns |
| Frigate | `192.168.10.30:5000` | ok | camera_health |
| Ollama | `localhost:11434` | ok | llm_runtime, copilot, `ollama_latency.sh` |

Pacotes no venv: os do `pyproject.toml` + `graypy` (resíduo Graylog) + `build`.
Binários externos: `mosquitto_pub` (só `ollama_latency.sh`) e `nvidia-smi` (provider do Ollama lê a GPU via subprocess).

## 6. MQTT

| Direção | Tópico | Componente |
|---|---|---|
| sub | `z2m1/bridge/{state,health,info,logging}`, idem `z2m2` | zigbee2mqtt |
| sub | `frigate/events`, `frigate/+/{motion,person,dog}` | frigate |
| sub | `homelab/lontranoc/request`, `otterpilot/request` | copilot |
| pub | `homelab/lontranoc/response`, `otterpilot/response` | copilot |
| pub | `homelab/ollama/latency` (a cada 3 min, via cron) | `ollama_latency.sh` |

## 7. Problemas encontrados

### Operacionais (produção agora)

1. **Proxmox sem coleta há 7 semanas.** `192.168.68.5:8006` inacessível do LXC
   (rota default via `192.168.10.1`; HA em `192.168.68.11` responde, então é o
   endereço/host específico). `host_health` e `virtualization` estão congelados
   em 2026-09-10; 36 dos 51 recursos estão stale.
2. **Scheduler sem backoff.** `_last_run` só é gravado em sucesso
   (`core/scheduler/scheduler.py`), então um job falhando é reexecutado a cada tick:
   ~6.400 tentativas/dia por job Proxmox em vez de 1.440.
3. **Overview conta stale como problema "healthy".** `problems` lista recursos com
   status `healthy` porque estão stale; o `summary` vira uma lista de 40 nomes.
4. **`otterpilot-scheduler.service` tem um `1` antes de `[Unit]`.** `systemd-analyze
   verify` reporta "Assignment outside of section"; `Description`/`After`/`Wants`
   da seção `[Unit]` são ignorados.
5. `llm_runtime` fica `degraded`/warning permanente: latência de ~3,7 s com `qwen3.5:9b`
   passa do limiar de 3000 ms de `status_from_latency()`, que foi calibrado para o modelo anterior.
6. UPS e rack: entidades HA `unavailable` (problema do HA, não do OtterPilot).
7. `lontranoc-frigate-mqtt` loga cada mensagem MQTT (~55 mil linhas/dia no journal).

### Divergência produção × git

Modificado em produção e não commitado (backups `*.bak.20261020-143045` ao lado):

| Arquivo | Mudança |
|---|---|
| `otterpilot/copilot/assistant.py` | modelo `qwen3.5:9b`, `keep_alive: -1`, `think: false` |
| `otterpilot/integrations/ollama/status_provider.py` | idem |
| `ollama_latency.sh` | reescrito: `qwen3.5:9b`, `set -euo pipefail`, timeout |
| `otterpilot/capabilities/virtualization/providers/proxmox.py` | **protótipo de transição**: lê o estado anterior do State Store e publica `guest_transition` |

O último item é uma forma inicial do Transition Engine, que o handoff adia para pós-MVP.
Precisa de decisão: commitar, mover para branch ou descartar.

Também em produção, fora do git: `dist/`, `otterpilot.egg-info/`, `__pycache__/`
(ignorados), `core/` vazio na raiz, `.env.bak.2026-10-19-231603`, `ollama_latency.sh.bak`.

### Bloqueios de empacotamento (smoke test em venv limpo)

1. **Pacote instalado não encontra `config/`.** Sem `OTTERPILOT_ROOT`, `PROJECT_ROOT`
   vira `site-packages/`. Produção só funciona por ser editable install do checkout.
2. **OpenObserve obrigatório no import.** `ingest.py`/`search.py` exigem env no
   import; `core/eventbus/bootstrap.py` importa o subscriber, então 28 módulos
   (incl. scheduler) não importam sem OpenObserve configurado.
3. `ollama/status_provider.py`: `load_dotenv("/opt/lontranoc/.env")` hardcoded.
4. Defaults específicos do homelab no código: `FRIGATE_URL`, entidades HA,
   instâncias `z2m1`/`z2m2`.
5. CI: `.env` usa `OPENOBSERVE_*_PASS`, o código lê `*_TOKEN`; CI nunca importa o EventBus.
6. Units, `.env.example` e instalação não estão versionados.
7. Copilot: `from xmlrpc import client` sem uso; `search_logs` importado sem uso;
   `should_use_graylog()` nunca chamado.

## 8. Legado — consumidores confirmados

| Arquivo | Consumidor real | Pode remover? |
|---|---|---|
| `lontranoc_assistant.py` | `lontranoc-assistant.service` | só após trocar o `ExecStart` para `-m otterpilot.copilot.assistant` |
| `ollama_latency.sh` | cron do `pedro` (*/3) → `homelab/ollama/latency` | só após confirmar quem consome o tópico (HA?) |
| `analysis_engine.py`, `analysis_vehicle.py` | nenhum | sim |
| `openobserve_ingest.py`, `openobserve_search.py` | nenhum | sim |
| `graylog_client.py` (+ `graypy` no venv) | nenhum | sim |
| `analysis/`, `collectors/`, `core/` (raiz) | nenhum | sim |

Pacotes vazios em `otterpilot/`: `api`, `cli`, `alerts`, `discovery`, `inventory`,
`storage`, `integrations/{adguard,homeassistant,mqtt,graylog,reverse_proxy/*}`,
`capabilities/{containers,reverse_proxy,storage}`.

## 9. Mapa para empacotamento

```text
COMPONENT     PROCESS                                   CONFIG                  SECRET                 STORAGE             PORT  DEPENDENCY
scheduler     python -m otterpilot.core.scheduler       .env, proxmox.yaml,     LoadCredential (pve),  state.db (rw)       —     OpenObserve, HA, Proxmox,
                                                        vehicle.yaml            .env (HA, OO, AdGuard)                           AdGuard, Frigate, Ollama
zigbee2mqtt   python -m ...zigbee2mqtt.mqtt_provider    .env                    .env (OO)              state.db (rw)       —     MQTT, OpenObserve
frigate-mqtt  python -m ...frigate.mqtt_provider        .env                    .env (OO)              state.db (rw)*      —     MQTT, OpenObserve
copilot       lontranoc_assistant.py                    .env, routes.yaml       .env (OO)              state.db (ro)       —     MQTT, OpenObserve, Ollama
latency (cron) ollama_latency.sh                        hardcoded               —                      —                   —     Ollama, MQTT, mosquitto_pub
```

\* `object_detection` não é stateful; o processo abre o State Store via EventBus.
