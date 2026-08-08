# OtterPilot Domains

OtterPilot is produced by Lontra Labs.

Domains organize capabilities for product navigation, onboarding, dashboards
and documentation.

Domains do not own provider-specific logic.

The primary technical abstraction remains the capability.

## Hierarchy

The OtterPilot conceptual hierarchy is:

Domain
→ Capability
→ Provider
→ Resource
→ State and events
→ Analysis
→ Knowledge
→ Copilot response

Example:

Infrastructure
→ DNS
→ AdGuard Home
→ DNS server instance
→ query and health data
→ DNS analysis
→ operational knowledge
→ user response

## Architectural rule

Domains are organizational and product-facing.

Capabilities are operational and technical.

Providers supply data to capabilities.

A capability may belong to one primary domain and may be referenced by
additional domains when necessary.

A provider may supply multiple capabilities across different domains.

---

# Initial Domains

## Infrastructure

Operational foundation of the environment.

Initial capabilities:

- `dns`
- `reverse_proxy`
- `containers`
- `virtualization`
- `storage`
- `ups`
- `network`
- `backup`
- `service_health`

Example providers:

- AdGuard Home
- Pi-hole
- Technitium
- Nginx Proxy Manager
- Caddy
- Traefik
- Docker
- Portainer
- Proxmox VE
- TrueNAS
- Synology
- NUT

---

## Automation

Automation, orchestration and messaging systems.

Initial capabilities:

- `home_automation`
- `messaging`
- `device_control`
- `presence`
- `zones`
- `notifications`
- `voice_assistant`
- `iot`

Example providers:

- Home Assistant
- MQTT
- Zigbee2MQTT
- ESPHome
- Tasmota
- Node-RED

---

## Security

Video surveillance, detection and access control.

Initial capabilities:

- `object_detection`
- `camera_health`
- `video_surveillance`
- `access_control`
- `alarm`
- `doorbell`
- `recording`

Example providers:

- Frigate
- Blue Iris
- Shinobi
- Scrypted
- ONVIF devices
- Home Assistant

---

## Mobility

Vehicles and mobile assets.

Initial capabilities:

- `vehicle`
- `vehicle_location`
- `vehicle_energy`
- `vehicle_maintenance`
- `charging`
- `trip`

Example providers:

- Home Assistant
- Renault
- Tesla
- FordPass
- BMW
- OBD integrations

The initial implementation uses Home Assistant as the provider for the generic
`vehicle` capability.

---

## AI

Inference, models and AI-assisted analysis.

Initial capabilities:

- `inference`
- `model_health`
- `vision_analysis`
- `embedding`
- `agent_runtime`
- `ai_acceleration`

Example providers:

- Ollama
- OpenAI-compatible APIs
- local vision models
- NVIDIA runtime

---

## Fabrication

Digital fabrication and maker equipment.

Initial capabilities:

- `three_d_printing`
- `print_job`
- `print_failure_detection`
- `filament`
- `printer_camera`
- `machine_health`

Example providers:

- Klipper
- Moonraker
- OctoPrint
- manufacturer APIs
- Home Assistant
- camera vision providers

---

## Energy

Power, consumption and resilience.

Initial capabilities:

- `energy`
- `power_metering`
- `ups`
- `battery`
- `solar`
- `generator`
- `outage`

Example providers:

- Home Assistant
- NUT
- smart meters
- solar inverters
- MQTT devices

The `ups` capability may appear in both Infrastructure and Energy views, but it
must have only one canonical capability definition.

---

## Environment

Physical environmental conditions.

Initial capabilities:

- `temperature`
- `humidity`
- `air_quality`
- `water`
- `weather`
- `leak_detection`

Example providers:

- Home Assistant
- MQTT
- ESPHome
- weather services

---

# Domain and Capability Rules

## Canonical ownership

Each capability must define one canonical domain.

Example:

- `dns` → Infrastructure
- `vehicle` → Mobility
- `object_detection` → Security
- `three_d_printing` → Fabrication
- `inference` → AI

## Cross-domain presentation

A capability may be displayed in more than one product view.

Example:

- `ups` may appear in Infrastructure and Energy.
- `battery` may appear in Energy and Mobility.
- `camera_health` may appear in Security and Fabrication.

Cross-domain display must not duplicate capability implementations.

## Provider independence

Domains and capabilities must not depend on specific providers.

Incorrect:

- `adguard_health`
- `frigate_camera`
- `renault_vehicle`

Preferred:

- `dns`
- `camera_health`
- `vehicle`

Provider-specific identifiers belong in integration or provider modules.

## UI behavior

The OtterPilot Console should present:

Domain
→ Capability
→ Resources
→ Provider information

Example:

Infrastructure
→ DNS
→ DNS Principal
→ provided by AdGuard Home

The provider name remains visible, but it is not the primary navigation model.

---

# Current Mapping

## Infrastructure

- DNS
  - provider: AdGuard Home
  - status: experimental

- Virtualization
  - provider: Proxmox logs
  - status: experimental

- Service health
  - providers: OpenObserve, MQTT and internal collectors
  - status: experimental

## Security

- Object detection
  - provider: Frigate
  - status: experimental

- Camera health
  - provider: Frigate
  - status: experimental

## Mobility

- Vehicle
  - provider: Home Assistant
  - status: experimental

## AI

- Inference
  - provider: Ollama
  - status: functional

- Model health
  - provider: Ollama
  - status: functional

## Automation

- Messaging
  - provider: MQTT
  - status: functional

- Home automation
  - provider: Home Assistant
  - status: experimental

---

# Product Navigation Proposal

The future OtterPilot Console may use:

- Overview
- Infrastructure
- Automation
- Security
- Mobility
- AI
- Fabrication
- Energy
- Environment
- Integrations
- Alerts
- Diagnostics

The Integrations page shows products and authentication.

The Domain pages show operational capabilities and resources.

---

# Implementation Guidance

Domain metadata should eventually be represented by a registry.

Possible fields:

- identifier
- display name
- description
- icon
- order
- capabilities
- enabled state

Capabilities must remain independently registered.

Providers declare which capabilities they supply.

The initial implementation should remain declarative and simple.
No dynamic plugin system is required solely to introduce domains.
