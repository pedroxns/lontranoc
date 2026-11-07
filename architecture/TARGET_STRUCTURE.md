# OtterPilot Target Package Structure

This document defines the target Python package layout for OtterPilot.

The current installation directory may remain `/opt/lontranoc` during migration.
The Python package itself will use the `otterpilot` namespace.

## Target tree

```text
/opt/lontranoc/
├── otterpilot/
│   ├── __init__.py
│   ├── version.py
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── models.py
│   │   ├── registry.py
│   │   ├── scheduler.py
│   │   ├── events.py
│   │   └── exceptions.py
│   │
│   ├── copilot/
│   │   ├── __init__.py
│   │   ├── assistant.py
│   │   ├── intents.py
│   │   ├── prompts.py
│   │   └── inference.py
│   │
│   ├── routing/
│   │   ├── __init__.py
│   │   ├── context_router.py
│   │   ├── query_context.py
│   │   ├── time_parser.py
│   │   └── entity_parser.py
│   │
│   ├── knowledge/
│   │   ├── __init__.py
│   │   ├── search.py
│   │   ├── models.py
│   │   ├── relationships.py
│   │   └── providers/
│   │       └── openobserve/
│   │           ├── __init__.py
│   │           ├── client.py
│   │           ├── ingest.py
│   │           └── search.py
│   │
│   ├── analysis/
│   │   ├── __init__.py
│   │   ├── engine.py
│   │   ├── registry.py
│   │   └── capabilities/
│   │       ├── __init__.py
│   │       ├── vehicle.py
│   │       ├── dns.py
│   │       ├── object_detection.py
│   │       ├── camera_health.py
│   │       └── virtualization.py
│   │
│   ├── capabilities/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── registry.py
│   │   ├── vehicle/
│   │   ├── dns/
│   │   ├── reverse_proxy/
│   │   ├── containers/
│   │   ├── virtualization/
│   │   ├── object_detection/
│   │   ├── camera_health/
│   │   ├── storage/
│   │   └── ups/
│   │
│   ├── integrations/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── registry.py
│   │   ├── homeassistant/
│   │   ├── adguard/
│   │   ├── frigate/
│   │   ├── proxmox/
│   │   ├── ollama/
│   │   ├── mqtt/
│   │   ├── graylog/
│   │   └── reverse_proxy/
│   │       ├── nginx_proxy_manager/
│   │       ├── caddy/
│   │       └── traefik/
│   │
│   ├── discovery/
│   │   ├── __init__.py
│   │   ├── scanner.py
│   │   ├── http_probe.py
│   │   ├── fingerprint.py
│   │   └── models.py
│   │
│   ├── inventory/
│   │   ├── __init__.py
│   │   ├── engine.py
│   │   ├── models.py
│   │   └── relationships.py
│   │
│   ├── alerts/
│   │   ├── __init__.py
│   │   ├── engine.py
│   │   ├── models.py
│   │   └── providers/
│   │       ├── mqtt.py
│   │       ├── homeassistant.py
│   │       └── email.py
│   │
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── database.py
│   │   ├── models.py
│   │   ├── migrations/
│   │   └── secrets.py
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── app.py
│   │   ├── dependencies.py
│   │   └── routes/
│   │       ├── integrations.py
│   │       ├── capabilities.py
│   │       ├── inventory.py
│   │       ├── health.py
│   │       └── alerts.py
│   │
│   └── cli/
│       ├── __init__.py
│       ├── main.py
│       ├── discover.py
│       └── integrations.py
│
├── config/
│   ├── routes.yaml
│   ├── capabilities/
│   ├── integrations/
│   └── examples/
│
├── docs/
├── tests/
├── scripts/
├── deploy/
│   ├── systemd/
│   ├── docker/
│   └── compose/
│
├── pyproject.toml
├── README.md
├── VISION.md
├── BRANDING.md
├── CONVENTIONS.md
├── PROJECT_INVENTORY.md
└── ARCHITECTURE.md
