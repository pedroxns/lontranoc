# OtterPilot Migration Map

## Phase 1 — Package skeleton

Create the `otterpilot` package without moving runtime modules.

New files:

- `otterpilot/__init__.py`
- `otterpilot/version.py`
- package subdirectories with `__init__.py`

Risk: Low

## Phase 2 — Routing package

Current:

- `core/context_router.py`
- `core/query_context.py`
- `core/time_parser.py`
- `core/entity_parser.py`
- `core/search_engine.py`

Target:

- `otterpilot/routing/context_router.py`
- `otterpilot/routing/query_context.py`
- `otterpilot/routing/time_parser.py`
- `otterpilot/routing/entity_parser.py`
- `otterpilot/knowledge/search.py`

Compatibility:

- old `core` modules temporarily re-export the new implementations.

Risk: Medium

## Phase 3 — OpenObserve provider

Current:

- `openobserve_ingest.py`
- `openobserve_search.py`

Target:

- `otterpilot/knowledge/providers/openobserve/ingest.py`
- `otterpilot/knowledge/providers/openobserve/search.py`

Compatibility:

- root modules temporarily re-export provider functions.

Risk: High, because most modules depend on OpenObserve.

## Phase 4 — Analysis package

Current:

- `analysis_engine.py`
- `analysis_vehicle.py`

Target:

- `otterpilot/analysis/engine.py`
- `otterpilot/analysis/capabilities/vehicle.py`

Compatibility:

- root modules temporarily re-export the new functions.

Risk: Medium

## Phase 5 — Product integrations

### Home Assistant / Vehicle

Current:

- `collectors/vehicle.py`
- `config/vehicle.yaml`

Target:

- Home Assistant adapter in `otterpilot/integrations/homeassistant`
- vehicle capability mapping in `otterpilot/capabilities/vehicle`
- analysis in `otterpilot/analysis/capabilities/vehicle.py`

Risk: Medium

### AdGuard

Current:

- `adguard_status.py`

Target:

- `otterpilot/integrations/adguard`

Capability:

- `dns`

Risk: Medium

### Frigate

Current:

- `frigate_mqtt_collector.py`

Target:

- `otterpilot/integrations/frigate`

Capabilities:

- `object_detection`
- `camera_health`

Risk: Medium

### Ollama

Current:

- `ollama_status.py`
- direct assistant calls

Target:

- `otterpilot/integrations/ollama`

Capability:

- inference provider and internal health.

Risk: High

### MQTT

Current:

- MQTT code spread across multiple modules.

Target:

- `otterpilot/integrations/mqtt`

Risk: High

## Phase 6 — Copilot orchestrator

Current:

- `lontranoc_assistant.py`

Target:

- `otterpilot/copilot/assistant.py`

Compatibility:

- legacy entrypoint imports and calls the new assistant.

Risk: Very high

## Phase 7 — Configuration

Current:

- `.env`
- absolute paths
- `config/routes.yaml`
- `config/vehicle.yaml`

Target:

- central configuration loader;
- environment overrides;
- schema validation;
- relative/default paths;
- future database-backed configuration.

Risk: High

## Phase 8 — Runtime naming migration

Migrate:

- prompt identity;
- telemetry service name;
- OpenObserve stream;
- MQTT topics;
- systemd units;
- installation path.

Compatibility period:

- read old and new MQTT topics;
- publish responses to the matching namespace;
- keep legacy telemetry alias;
- maintain old systemd service until the new service is validated.

Risk: Very high

## Phase 9 — API and persistent storage

Create:

- SQLite application database;
- credential encryption;
- FastAPI server;
- integration lifecycle API.

Risk: High

## Phase 10 — Discovery MVP

Initial providers:

- Home Assistant;
- Proxmox;
- Docker/Portainer;
- AdGuard Home;
- Nginx Proxy Manager.

Risk: Medium

## Phase 11 — OtterPilot Console

Create:

- onboarding;
- integration catalog;
- connection tests;
- capability dashboards;
- alerts;
- diagnostics.

Risk: High
