# OtterPilot Project Inventory

OtterPilot is produced by Lontra Labs.

This document describes the current implementation, architectural destination,
technical debt and product readiness of each OtterPilot module.

## Status legend

- Stable: currently operational and reasonably isolated.
- Functional: operational, but requires architectural restructuring.
- Experimental: operational only for limited use cases.
- Planned: architecturally defined, but not yet implemented.
- Legacy: maintained temporarily for compatibility.

---

# 1. Core Platform

## Context Router

Status: Functional

Current implementation:

- `core/context_router.py`
- `config/routes.yaml`

Current responsibility:

- scores product-oriented keywords;
- selects an OpenObserve stream;
- selects a named query;
- returns SQL and route score.

Dependencies:

- PyYAML;
- `config/routes.yaml`.

Architectural destination:

- Intent and capability routing within the Core Platform.

Technical debt:

- still routes primarily by product/stream;
- contains legacy fallback to the `lontranoc` stream;
- uses an absolute configuration path;
- query definitions are coupled to OpenObserve SQL.

Product readiness: 60%

---

## Query Context

Status: Functional

Current implementation:

- `core/query_context.py`

Current responsibility:

- combines routing;
- temporal parsing;
- entity extraction;
- filters;
- query metadata.

Dependencies:

- Context Router;
- Time Parser;
- Entity Parser.

Architectural destination:

- normalized request context shared by Knowledge and Analysis engines.

Technical debt:

- still exposes raw SQL;
- context schema is not yet represented by typed models.

Product readiness: 65%

---

## Time Parser

Status: Stable

Current implementation:

- `core/time_parser.py`

Current responsibility:

- interprets relative and explicit time windows;
- converts local time to OpenObserve timestamps;
- provides display and query boundaries;
- handles the `America/Sao_Paulo` timezone.

Architectural destination:

- shared Temporal Engine.

Technical debt:

- timezone is currently fixed;
- output should eventually use typed models;
- user and deployment timezones must become configurable.

Product readiness: 75%

---

## Entity Parser

Status: Functional

Current implementation:

- `core/entity_parser.py`

Current responsibility:

- extracts known entities and filters from user questions;
- maps natural-language aliases to structured fields.

Architectural destination:

- shared entity extraction engine;
- capability-aware entity registry.

Technical debt:

- aliases are currently static;
- product and capability entities are not yet registered dynamically.

Product readiness: 55%

---

## Search Engine

Status: Functional

Current implementation:

- `core/search_engine.py`

Current responsibility:

- obtains query context;
- applies filters;
- executes OpenObserve searches;
- builds search summaries.

Dependencies:

- Query Context;
- `openobserve_search.py`.

Architectural destination:

- Knowledge Retrieval Engine.

Technical debt:

- directly depends on OpenObserve;
- SQL mutation is string-based;
- provider-independent query abstraction does not exist;
- imports an integration module located in the project root.

Product readiness: 55%

---

# 2. Copilot Engine

## Assistant Orchestrator

Status: Functional / Legacy-branded

Current implementation:

- `lontranoc_assistant.py`

Current responsibility:

- receives MQTT requests;
- performs context routing;
- executes historical searches;
- calls the Analysis Engine;
- builds the LLM prompt;
- calls Ollama;
- publishes responses;
- emits telemetry to OpenObserve.

Dependencies:

- MQTT;
- Ollama;
- OpenObserve;
- Core Platform;
- Analysis Engine.

Architectural destination:

- `otterpilot/copilot/assistant.py`
- separated request, inference, transport and telemetry modules.

Technical debt:

- concentrates too many responsibilities;
- contains product name and technical identifiers from LontraNOC;
- MQTT topics are hard-coded;
- prompt text is embedded in the module;
- environment path is absolute;
- emits directly to OpenObserve;
- contains compatibility imports that may be redundant.

Product readiness: 45%

---

# 3. Analysis Engine

## Analysis Dispatcher

Status: Functional

Current implementation:

- `analysis_engine.py`

Current responsibility:

- normalizes events;
- calculates basic statistics;
- groups events;
- builds incidents;
- dispatches vehicle analysis.

Dependencies:

- `analysis_vehicle.py`.

Architectural destination:

- `analysis/engine.py`
- capability-based plugin dispatcher.

Technical debt:

- product-generic and capability-specific logic are mixed;
- plugin registry does not exist;
- event schemas are untyped;
- file remains in the project root.

Product readiness: 50%

---

## Vehicle Analysis

Status: Experimental

Current implementation:

- `analysis_vehicle.py`

Current responsibility:

- interprets vehicle range;
- interprets fuel level;
- analyses tire pressure;
- interprets lock and door states;
- distinguishes auxiliary and hybrid batteries.

Capability:

- `vehicle`

Current provider:

- Home Assistant entities representing Renault Koleos telemetry.

Architectural destination:

- `analysis/capabilities/vehicle.py`

Technical debt:

- thresholds are hard-coded;
- vehicle profile is not configurable;
- consumption baseline is not historical;
- output schema is untyped;
- file remains in the project root.

Product readiness: 60%

---

## Generic Incident Analysis

Status: Experimental

Current implementation:

- logic inside `analysis_engine.py`.

Current capabilities:

- camera and RTSP failures;
- network events;
- Zigbee instability;
- infrastructure events.

Architectural destination:

- separate capability analyzers:
  - `object_detection`
  - `network`
  - `zigbee`
  - `virtualization`

Technical debt:

- classifications are embedded in a shared file;
- confidence and causes are rule-based but not configurable;
- knowledge signatures are not registered externally.

Product readiness: 40%

---

# 4. Capability Platform

## Vehicle

Status: Experimental

Provider:

- Home Assistant.

Configuration:

- `config/vehicle.yaml`

Current data:

- location;
- range;
- fuel level;
- average consumption;
- engine state and temperature;
- 12 V battery;
- hybrid battery;
- tire pressure;
- doors and locks;
- odometer;
- maintenance interval;
- data freshness.

Current implementation:

- `collectors/vehicle.py`
- `analysis_vehicle.py`
- vehicle routes in `config/routes.yaml`

Product readiness: 65%

---

## DNS

Status: Experimental

Provider:

- AdGuard Home.

Current data:

- service status;
- protection status;
- query volume;
- blocking volume;
- blocking percentage;
- recent query-log errors;
- health score.

Current implementation:

- `adguard_status.py`
- AdGuard routes in `config/routes.yaml`
- OpenObserve `adguard` stream and pipeline.

Architectural destination:

- generic `dns` capability;
- AdGuard Home as one provider;
- future Pi-hole and Technitium providers.

Product readiness: 55%

---

## Object Detection and Camera Health

Status: Experimental

Provider:

- Frigate.

Current data:

- object events;
- labels;
- camera;
- confidence scores;
- RTSP errors;
- FFmpeg failures;
- camera availability.

Current implementation:

- `frigate_mqtt_collector.py`
- Frigate routes in `config/routes.yaml`
- generic camera analysis in `analysis_engine.py`.

Architectural destination:

- capabilities:
  - `object_detection`
  - `camera_health`
  - `video_surveillance`

Product readiness: 60%

---

## Virtualization

Status: Experimental

Provider:

- Proxmox VE logs through OpenObserve.

Current data:

- cluster;
- quorum;
- nodes;
- VM/LXC lifecycle;
- backups;
- storage;
- ZFS and disk events.

Current implementation:

- Proxmox queries in `config/routes.yaml`.

Missing:

- direct Proxmox API integration;
- inventory;
- metrics;
- authentication workflow;
- discovery.

Product readiness: 35%

---

## Home Automation

Status: Experimental

Provider:

- Home Assistant logs and API.

Current implementation:

- Home Assistant routes;
- Home Assistant vehicle-state provider.

Missing:

- generic integration adapter;
- entity inventory;
- capability mapping;
- automation health;
- persons, zones, energy and notification capabilities.

Product readiness: 35%

---

## AI Inference

Status: Functional

Provider:

- Ollama.

Current data:

- model;
- model load status;
- latency;
- GPU temperature;
- GPU utilization;
- VRAM usage.

Current implementation:

- `ollama_status.py`
- `ollama_latency.sh`
- Ollama routes;
- direct calls in the assistant.

Architectural destination:

- inference provider integration;
- local and remote model-provider abstraction.

Product readiness: 55%

---

# 5. Collection and Connector Modules

## Vehicle State Connector

Status: Functional

Current implementation:

- `collectors/vehicle.py`

Source:

- Home Assistant REST API.

Destination:

- OpenObserve `vehicle` stream.

Technical debt:

- inserts `/opt/lontranoc` into `sys.path`;
- uses absolute configuration and environment paths;
- sends directly through `openobserve_ingest`;
- configuration schema is not validated.

Future destination:

- Home Assistant integration providing the `vehicle` capability.

---

## AdGuard Status Connector

Status: Functional

Current implementation:

- `adguard_status.py`

Source:

- AdGuard Home control API.

Destination:

- OpenObserve `adguard` stream.

Technical debt:

- located in the project root;
- credentials and instances come directly from `.env`;
- direct dependency on OpenObserve;
- integration and capability logic are mixed.

Future destination:

- AdGuard Home integration providing the `dns` capability.

---

## Frigate MQTT Connector

Status: Functional

Current implementation:

- `frigate_mqtt_collector.py`

Source:

- MQTT `frigate/#`.

Destination:

- OpenObserve `frigate` stream.

Technical debt:

- located in the project root;
- direct OpenObserve dependency;
- MQTT and normalization logic are mixed;
- topics and environment loading are not centrally configured.

Future destination:

- Frigate integration providing object-detection and camera capabilities.

---

## Homelab Status Aggregator

Status: Functional / Legacy

Current implementation:

- `homelab_status.py`

Current responsibility:

- aggregates state from multiple sources;
- publishes MQTT status;
- emits OpenObserve telemetry.

Technical debt:

- unclear long-term ownership;
- overlaps with Knowledge and Health engines;
- product-specific assumptions;
- direct dependencies on MQTT and OpenObserve.

Future destination:

- Health Engine or Knowledge Engine.

---

## Ollama Status Connector

Status: Functional

Current implementation:

- `ollama_status.py`
- `ollama_latency.sh`

Source:

- Ollama API;
- NVIDIA utilities;
- local process state.

Destinations:

- MQTT;
- OpenObserve.

Future destination:

- inference-provider integration and internal observability.

---

# 6. External Integrations

## OpenObserve

Status: Stable

Current implementation:

- `openobserve_ingest.py`
- `openobserve_search.py`

Responsibilities:

- structured event ingestion;
- historical SQL search.

Used by:

- Core Search Engine;
- Assistant;
- all current connectors.

Architectural destination:

- `integrations/openobserve/ingest.py`
- `integrations/openobserve/search.py`

Technical debt:

- global environment configuration;
- absolute `.env` path;
- no abstract knowledge-store interface;
- tightly coupled throughout the project.

Product readiness: 65%

---

## Graylog

Status: Legacy / Partially used

Current implementation:

- `graylog_client.py`

Responsibilities:

- historical Graylog searches;
- predefined query routing.

Technical debt:

- uses legacy LontraNOC terminology;
- overlaps with OpenObserve;
- unclear whether Graylog remains a supported provider.

Decision required:

- retain as optional knowledge provider;
- or deprecate after OpenObserve migration.

Product readiness: 25%

---

## MQTT

Status: Functional

Used by:

- Assistant request and response transport;
- Frigate events;
- homelab status;
- Ollama status.

Architectural destination:

- messaging transport integration.

Technical debt:

- topics are distributed across modules;
- no shared MQTT client;
- no typed message schema;
- legacy `homelab/lontranoc/*` topics remain active.

Product readiness: 50%

---

## Home Assistant

Status: Functional but not represented as a formal integration

Used by:

- vehicle connector;
- MQTT request and response workflow;
- alerts and user interaction.

Architectural destination:

- formal Home Assistant integration adapter;
- provider of multiple capabilities.

Product readiness: 40%

---

## Ollama

Status: Functional

Used by:

- Copilot inference;
- system telemetry.

Architectural destination:

- inference provider adapter.

Product readiness: 55%

---

# 7. Configuration

## Environment File

Status: Functional / Development-oriented

Current implementation:

- `/opt/lontranoc/.env`

Contains:

- OpenObserve credentials;
- MQTT connection;
- Home Assistant tokens;
- AdGuard credentials;
- service URLs.

Technical debt:

- absolute path;
- no secret encryption;
- no configuration validation;
- unsuitable as the primary configuration system for SaaS or UI.

Future destination:

- bootstrap configuration only;
- encrypted persistent integration secrets.

---

## Routes Configuration

Status: Functional

Current implementation:

- `config/routes.yaml`

Responsibilities:

- stream keywords;
- query keywords;
- SQL templates.

Technical debt:

- still product-oriented;
- includes provider-specific SQL;
- no schema validation;
- no capability registry.

Future destination:

- capability intents and retrieval templates.

---

## Vehicle Configuration

Status: Functional

Current implementation:

- `config/vehicle.yaml`

Responsibility:

- maps Home Assistant entities to the generic vehicle model.

Architectural significance:

- first practical example of separating provider-specific identifiers from capability logic.

Technical debt:

- single-vehicle assumption;
- no schema validation;
- no UI-based entity selection.

---

# 8. Documentation

Existing documents:

- `VISION.md`
- `BRANDING.md`
- `CONVENTIONS.md`
- `architecture/ARCHITECTURE.md`

Status:

- product vision defined;
- branding defined;
- technical conventions defined;
- capability-first architecture defined.

Missing:

- public `README.md`;
- installation guide;
- developer guide;
- integration SDK guide;
- security model;
- threat model;
- roadmap;
- changelog;
- API documentation.

Product readiness: 35%

---

# 9. Infrastructure and Runtime

Current runtime:

- Python virtual environment;
- systemd services and timers;
- MQTT broker;
- OpenObserve;
- Ollama;
- Home Assistant.

Technical debt:

- absolute `/opt/lontranoc` paths;
- systemd unit files are external to the repository;
- no Docker image;
- no Compose stack;
- no health endpoint;
- no migrations;
- no persistent application database;
- no unified scheduler;
- no API server;
- no web console.

Product readiness: 25%

---

# 10. Legacy OtterPilot Migration Inventory

Current legacy identifiers include:

- installation directory `/opt/lontranoc`;
- `lontranoc_assistant.py`;
- OpenObserve stream `lontranoc`;
- service value `lontranoc`;
- MQTT topics `homelab/lontranoc/request` and `homelab/lontranoc/response`;
- prompt identity `LontraNOC`;
- systemd service names;
- OpenObserve credentials using the old name;
- Graylog queries;
- messages and telemetry text.

Migration policy:

1. introduce OtterPilot aliases;
2. support old and new MQTT topics temporarily;
3. create the new OpenObserve stream;
4. update Home Assistant consumers;
5. migrate systemd units;
6. rename the installation directory last;
7. remove legacy identifiers only after validation.

---

# 11. Missing Product Components

## Critical

- Capability Registry
- Integration Registry
- Plugin Loader
- Typed common models
- Persistent application database
- Credential vault
- REST API
- Integration lifecycle manager
- Capability-aware routing
- Inventory Engine
- Health Engine

## High priority

- Discovery Engine
- Fingerprint Engine
- Scheduler
- Alert Engine
- Notification providers
- Diagnostics endpoint
- Configuration validation
- Integration connection tests
- Local agent model

## Product-facing

- Web Console
- Onboarding wizard
- Integration catalog
- Entity and resource selector
- Alert editor
- Capability dashboards
- Backup and restore
- Upgrade system

## Commercial and SaaS

- User accounts
- Organization and site model
- Licensing
- Billing
- Cloud gateway
- Agent registration
- Secure secret boundaries
- Audit log
- Multi-tenant authorization
- Terms and privacy controls

---

# 12. Strategic Priorities

## Priority 1 — Package and module structure

- remove root-level business modules;
- introduce the `otterpilot` Python package;
- eliminate absolute paths;
- centralize configuration.

## Priority 2 — Common models and registries

- define integration contracts;
- define capability contracts;
- create typed resource, event, state and analysis models;
- implement registries and plugin loading.

## Priority 3 — Migrate existing functionality

- Vehicle → Home Assistant integration + Vehicle capability;
- AdGuard → AdGuard integration + DNS capability;
- Frigate → Frigate integration + Object Detection capability;
- Ollama → Inference provider;
- OpenObserve → Knowledge provider.

## Priority 4 — Discovery MVP

Initial discovery targets:

- Home Assistant;
- Proxmox;
- Docker/Portainer;
- AdGuard Home;
- Nginx Proxy Manager.

## Priority 5 — API and Console

- expose integrations, inventory, health, alerts and diagnostics;
- build the first OtterPilot Console.

---

# 13. Overall Readiness

Current strengths:

- functional end-to-end assistant;
- historical search;
- temporal understanding;
- entity filtering;
- deterministic analysis;
- multiple real integrations;
- capability-first architecture now documented.

Current weaknesses:

- strong coupling to local environment;
- no formal plugin system;
- no persistent application state;
- no UI or API;
- configuration and secrets are scattered;
- legacy branding remains in runtime identifiers.

Overall engineering maturity: Experimental

Overall product readiness: approximately 35%

The current system is a strong functional prototype and a suitable foundation for
the OtterPilot product architecture.
