# OtterPilot Branding

## Company

**Lontra Labs**

## Product

**OtterPilot**

## Product description

OtterPilot is an AI copilot for homelabs and self-hosted infrastructure. Vibecoded to be uour homelabs other pilot.

## Tagline

**Your AI Copilot for Infrastructure**

Alternative homelab-focused tagline:

**AI Copilot for Homelabs**

## Naming conventions

| Previous name | New name |
|---|---|
| LontraNOC | OtterPilot |
| lontranoc | otterpilot |
| Lontra Labs project | Lontra Labs product |
| LontraNOC Assistant | OtterPilot Assistant |
| LontraNOC Agent | OtterPilot Agent |
| LontraNOC Cloud | OtterPilot Cloud |
| LontraNOC UI | OtterPilot Console |
| LontraNOC Analysis Engine | OtterPilot Analysis Engine |
| LontraNOC Integration Platform | OtterPilot Integration Platform |

## Technical identifiers

New code, services, streams, MQTT topics and configuration keys must use:

- Python package: `otterpilot`
- Service name: `otterpilot`
- OpenObserve stream: `otterpilot`
- MQTT base topic: `otterpilot`
- Container prefix: `otterpilot`
- Environment-variable prefix: `OTTERPILOT_`
- Repository name: `otterpilot`

## Compatibility policy

During the migration, existing identifiers using `lontranoc` may remain as compatibility aliases.

They must not be removed until:

1. the replacement is tested;
2. systemd services are migrated;
3. MQTT consumers are updated;
4. OpenObserve queries are updated;
5. Home Assistant automations are updated.

## Ownership

OtterPilot is produced by **Lontra Labs**.
