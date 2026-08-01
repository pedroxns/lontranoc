from __future__ import annotations

from otterpilot.core.registry.bootstrap import build_default_registry
from otterpilot.core.registry.executor import ConnectorExecutor
from otterpilot.core.registry.runtime_bootstrap import (
    build_default_runtime_registry,
)


def build_default_executor() -> ConnectorExecutor:
    return ConnectorExecutor(
        metadata_registry=build_default_registry(),
        runtime_registry=build_default_runtime_registry(),
    )
