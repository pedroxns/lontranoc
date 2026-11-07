# OtterPilot Vision

## What is OtterPilot?

OtterPilot is an AI copilot for homelabs, self-hosted services and small infrastructure environments.

It discovers services, connects to supported platforms, collects operational data, correlates events and explains problems in natural language.

OtterPilot is produced by Lontra Labs.

## The problem

Homelabs commonly contain many independent systems:

- hypervisors;
- containers;
- home automation;
- network controllers;
- DNS servers;
- reverse proxies;
- monitoring platforms;
- cameras;
- storage;
- vehicles;
- 3D printers;
- UPS systems.

Each system exposes its own logs, APIs, dashboards and alert formats.

Understanding an incident often requires manually correlating information from several tools.

## The solution

OtterPilot provides a unified operational layer.

Its core workflow is:

1. Discover services.
2. Identify products.
3. Request the appropriate credentials.
4. Import inventory and capabilities.
5. Collect telemetry and events.
6. Normalize the data.
7. Correlate related incidents.
8. Explain the result in natural language.
9. Recommend safe actions.
10. Notify the user through configured channels.

## Product principles

### Local-first

Sensitive credentials and local-network access should remain in the local OtterPilot Agent whenever possible.

### Read-only by default

New integrations must start with read-only permissions.

Write operations and automation must require explicit enablement.

### Deterministic before generative

Time parsing, filtering, calculations, thresholds and known technical signatures should be handled by deterministic code.

The language model explains and communicates results; it should not invent measurable facts.

### Explainable conclusions

Operational conclusions should include:

- supporting evidence;
- affected services;
- confidence;
- probable cause;
- recommended next action.

### Modular integrations

Each supported product must be implemented as an independent adapter or plugin.

### Self-hosted and cloud-capable

OtterPilot should support:

- a completely self-hosted edition;
- a local agent connected to OtterPilot Cloud;
- optional bundled infrastructure through Docker Compose.

## Initial audience

- homelab enthusiasts;
- self-hosting users;
- makers;
- home-automation enthusiasts;
- small technical teams;
- small businesses without a dedicated operations team.

## Core differentiator

OtterPilot is not just an otter monitoring dashboard.

Its differentiator is:

> Discovering, correlating and explaining infrastructure behavior with minimal manual configuration.

## Long-term vision

OtterPilot should become a trusted operational companion capable of understanding an environment as a connected system rather than as isolated applications.
