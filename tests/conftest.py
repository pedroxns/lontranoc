from __future__ import annotations

import os
import tempfile
from pathlib import Path

# Precisa acontecer antes de importar otterpilot: a raiz é resolvida no import.
_ROOT = Path(tempfile.mkdtemp(prefix="otterpilot-tests-"))
(_ROOT / "config").mkdir()
os.environ["OTTERPILOT_ROOT"] = str(_ROOT)
os.environ["OTTERPILOT_STATE_DB"] = str(_ROOT / "state.db")

for key in list(os.environ):
    if key.startswith(("MQTT_", "OPENOBSERVE_", "HA_", "PROXMOX_", "OLLAMA_", "ADGUARD")):
        del os.environ[key]

import pytest  # noqa: E402

from otterpilot.state.store import StateStore  # noqa: E402


@pytest.fixture
def project_root() -> Path:
    return _ROOT


@pytest.fixture
def store(tmp_path: Path) -> StateStore:
    return StateStore(tmp_path / "state.db")
