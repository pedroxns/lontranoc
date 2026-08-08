from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from otterpilot.core.eventbus import EventEnvelope


class StateStoreError(RuntimeError):
    """Erro relacionado ao armazenamento de estado atual."""


class StateStore:
    def __init__(
        self,
        database_path: str | Path,
    ) -> None:
        self.database_path = Path(database_path)

        self.database_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.database_path,
            timeout=10,
        )

        connection.row_factory = sqlite3.Row

        connection.execute(
            "PRAGMA journal_mode=WAL"
        )

        connection.execute(
            "PRAGMA busy_timeout=5000"
        )

        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS current_state (
                    connector TEXT NOT NULL,
                    capability TEXT NOT NULL,
                    resource_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    event_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    status TEXT NOT NULL,
                    message TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,

                    PRIMARY KEY (
                        connector,
                        capability,
                        resource_id
                    )
                )
                """
            )

    def upsert(
        self,
        event: EventEnvelope,
    ) -> None:
        if not event.resource_id:
            raise StateStoreError(
                "Evento stateful sem resource_id"
            )

        payload_json = json.dumps(
            event.payload,
            ensure_ascii=False,
            separators=(",", ":"),
        )

        metadata_json = json.dumps(
            event.metadata,
            ensure_ascii=False,
            separators=(",", ":"),
        )

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO current_state (
                    connector,
                    capability,
                    resource_id,
                    event_type,
                    event_id,
                    timestamp,
                    severity,
                    status,
                    message,
                    payload_json,
                    metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

                ON CONFLICT (
                    connector,
                    capability,
                    resource_id
                )
                DO UPDATE SET
                    event_type = excluded.event_type,
                    event_id = excluded.event_id,
                    timestamp = excluded.timestamp,
                    severity = excluded.severity,
                    status = excluded.status,
                    message = excluded.message,
                    payload_json = excluded.payload_json,
                    metadata_json = excluded.metadata_json
                """,
                (
                    event.connector,
                    event.capability,
                    event.resource_id,
                    event.event_type,
                    event.event_id,
                    event.timestamp.isoformat(),
                    event.severity,
                    event.status,
                    event.message,
                    payload_json,
                    metadata_json,
                ),
            )

    def get(
        self,
        *,
        connector: str,
        capability: str,
        resource_id: str,
    ) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM current_state
                WHERE connector = ?
                  AND capability = ?
                  AND resource_id = ?
                """,
                (
                    connector,
                    capability,
                    resource_id,
                ),
            ).fetchone()

        if row is None:
            return None

        return self._row_to_dict(row)

    def list_all(
        self,
    ) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM current_state
                ORDER BY connector, capability, resource_id
                """
            ).fetchall()

        return [
            self._row_to_dict(row)
            for row in rows
        ]

    @staticmethod
    def _row_to_dict(
        row: sqlite3.Row,
    ) -> dict[str, Any]:
        return {
            "connector": row["connector"],
            "capability": row["capability"],
            "resource_id": row["resource_id"],
            "event_type": row["event_type"],
            "event_id": row["event_id"],
            "timestamp": row["timestamp"],
            "severity": row["severity"],
            "status": row["status"],
            "message": row["message"],
            "payload": json.loads(
                row["payload_json"]
            ),
            "metadata": json.loads(
                row["metadata_json"]
            ),
        }
