from __future__ import annotations

from pathlib import Path

from otterpilot.core.config import get_env
from otterpilot.state.store import StateStore


DEFAULT_STATE_DB = Path(
    get_env(
        "OTTERPILOT_STATE_DB",
        "/var/lib/otterpilot/state.db",
    )
    or "/var/lib/otterpilot/state.db"
)


def build_default_state_store() -> StateStore:
    return StateStore(DEFAULT_STATE_DB)
