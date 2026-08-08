# OtterPilot Technical Conventions

## Python

- Package and module names use `snake_case`.
- Product identifiers use `otterpilot`.
- Public classes use `PascalCase`.
- Functions should have type hints.
- Collectors must not contain service-specific credentials directly.
- Absolute installation paths must not be introduced in new code.

## Integrations

Every integration should expose, when applicable:

- discovery;
- fingerprinting;
- connection testing;
- inventory collection;
- health collection;
- suggested alerts;
- graceful resource cleanup.

## Events

Every normalized event should preferably contain:

- `service`
- `component`
- `event_type`
- `severity`
- `status`
- `message`
- `timestamp`
- `schema_version`
- `source`
- `instance`

## Severity

Allowed normalized values:

- `debug`
- `info`
- `warning`
- `error`
- `critical`

## Status

Preferred normalized values:

- `ok`
- `warning`
- `degraded`
- `critical`
- `offline`
- `unknown`

## Streams

Stream names must be:

- lowercase;
- singular when practical;
- independent from product branding when they represent a generic resource.

Examples:

- `vehicle`
- `frigate`
- `adguard`
- `proxmox`
- `homeassistant`
- `otterpilot`

## Configuration

- Secrets stay outside versioned YAML files.
- `.env` is allowed only for bootstrap and development.
- Product configuration should migrate toward persistent storage.
- YAML files remain supported for declarative import/export.

## Compatibility

Legacy `lontranoc` identifiers must be migrated gradually.

No identifier should be removed before all known consumers are checked.
