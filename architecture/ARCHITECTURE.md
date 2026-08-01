OtterPilot

                     UI
                      │
              REST / WebSocket
                      │
                 API Gateway
                      │
        ┌─────────────┴─────────────┐
        │                           │
 Integration Platform         Intelligence Engine
        │                           │
        │                    Knowledge Engine
        │                           │
        │                    Analysis Engine
        │                           │
        └─────────────┬─────────────┘
                      │
               Event Normalization
                      │
               OpenObserve Streams
                      │
                 Local Connectors
                      │
Home Automationt • Containersr • Hypervisorx • DNS • Vehicle • NVR/object detection


# OtterPilot Architecture

OtterPilot is an AI copilot for homelabs, self-hosted services and small infrastructure environments.

OtterPilot is produced by Lontra Labs.

## Core principle

Products provide capabilities.

Capabilities build knowledge.

Knowledge powers intelligence.

The user should not need to know which product provides a capability.

## How OtterPilot sees the environment

OtterPilot does not treat products as the primary abstraction.

Products are integration providers.

Capabilities are the primary abstraction.

Examples:

- AdGuard Home, Pi-hole and Technitium provide the `dns` capability.
- Nginx Proxy Manager, Caddy, Traefik and Nginx provide the `reverse_proxy` capability.
- Frigate, Blue Iris and Shinobi provide the `object_detection` capability.
- Proxmox, VMware and XCP-ng provide the `virtualization` capability.
- Docker, Portainer and Kubernetes provide the `containers` capability.
- Renault, Tesla and FordPass integrations provide the `vehicle` capability.
- Home Assistant may provide several capabilities, including automation, persons, energy, climate, vehicles and notifications.

## High-level flow

Discovery
→ Integration adapter
→ Capability mapping
→ Inventory
→ Normalization
→ Knowledge
→ Analysis
→ Copilot
→ User

## Product layers

### User Interface

Responsible for:

- onboarding;
- integration setup;
- capability views;
- alerts;
- health dashboards;
- diagnostics;
- configuration.

The UI should expose capabilities, not implementation details.

Example:

- `DNS`
- provided by `AdGuard Home`

### API

Responsible for:

- configuration;
- authentication;
- integration management;
- inventory;
- health;
- alerts;
- diagnostics;
- communication with the UI.

### Core

Responsible for:

- configuration;
- plugin lifecycle;
- scheduling;
- event routing;
- common models;
- internal APIs.

The core must not contain product-specific logic.

### Discovery Engine

Responsible for answering:

> What services exist in the authorized environment?

Discovery may use:

- mDNS;
- SSDP;
- controlled TCP probing;
- HTTP fingerprints;
- DNS;
- Docker or Portainer inventory;
- Home Assistant inventory.

Discovery must not attempt authentication without user authorization.

### Integration Platform

Responsible for answering:

> How does OtterPilot communicate with this product?

Each integration adapter may provide:

- discovery fingerprints;
- authentication;
- connection testing;
- inventory collection;
- health collection;
- event collection;
- suggested alerts;
- capability declarations.

Examples:

- Home Assistant adapter;
- Proxmox adapter;
- AdGuard Home adapter;
- Nginx Proxy Manager adapter.

### Capability Platform

Responsible for answering:

> What operational capabilities does this integration provide?

Examples:

- `dns`
- `reverse_proxy`
- `containers`
- `virtualization`
- `object_detection`
- `vehicle`
- `energy`
- `ups`
- `storage`
- `home_automation`

A single product may provide multiple capabilities.

### Inventory Engine

Responsible for representing discovered resources consistently.

Examples:

- DNS server;
- proxy host;
- certificate;
- virtual machine;
- container;
- camera;
- vehicle;
- printer;
- UPS.

Inventory items must use generic resource models whenever possible.

### Normalization Layer

Responsible for transforming product-specific data into normalized events and state.

Preferred event fields:

- `service`
- `integration`
- `capability`
- `component`
- `instance`
- `resource_id`
- `event_type`
- `severity`
- `status`
- `message`
- `timestamp`
- `schema_version`
- `source`

### Knowledge Engine

Responsible for combining:

- current state;
- historical events;
- inventory;
- relationships;
- known signatures;
- user configuration;
- previous incidents.

The Knowledge Engine should describe the environment as a connected system rather than isolated applications.

### Analysis Engine

Responsible for deterministic interpretation.

Analysis should be organized by capability, not by product.

Examples:

- `analysis/dns`
- `analysis/reverse_proxy`
- `analysis/vehicle`
- `analysis/containers`
- `analysis/object_detection`

Known facts, thresholds and calculations must be handled here before reaching the language model.

### Copilot Engine

Responsible for:

- understanding user intent;
- selecting capabilities;
- retrieving knowledge;
- explaining conclusions;
- presenting evidence;
- recommending safe actions.

The language model must not invent measurable facts.

## Integration contract

Each integration should implement, when applicable:

- `discover`
- `fingerprint`
- `test_connection`
- `get_inventory`
- `get_health`
- `collect_state`
- `collect_events`
- `get_capabilities`
- `suggest_alerts`
- `close`

## Capability contract

Each capability should define:

- resource types;
- normalized fields;
- supported intents;
- health rules;
- known signatures;
- relationships;
- recommended alerts;
- analysis output schema.

## Read-only by default

New integrations must start with read-only access.

Write operations require:

- explicit enablement;
- clear scope;
- audit logging;
- confirmation when appropriate.

## Local-first architecture

In a cloud deployment:

- the OtterPilot Agent runs locally;
- local credentials remain with the agent whenever possible;
- the agent initiates outbound connections;
- the cloud should not require inbound access to the local network.

## Compatibility

Legacy identifiers using `lontranoc` remain temporarily supported during migration.

New code must use:

- product name: `OtterPilot`
- company name: `Lontra Labs`
- technical identifier: `otterpilot`

## Initial capability targets

The first public MVP should prioritize:

- `home_automation`
- `virtualization`
- `containers`
- `dns`
- `reverse_proxy`
- `object_detection`
- `vehicle`

## Architectural rule

Before implementing a new feature, answer:

1. Which capability owns it?
2. Which integration provides it?
3. Is the logic generic or product-specific?
4. Does it belong in core, integration, capability, knowledge or analysis?
5. How will it be tested?

## Domain organization

OtterPilot groups capabilities into product-facing domains.

The conceptual hierarchy is:

Domain
→ Capability
→ Provider
→ Resource

Domains organize navigation, onboarding and dashboards.

Capabilities remain the primary technical abstraction.

Providers supply product-specific data to capabilities.

The canonical domain definitions are documented in `architecture/DOMAINS.md`.
