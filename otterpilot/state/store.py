from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from otterpilot.core.eventbus import EventEnvelope


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS job_status (
                    job_id TEXT PRIMARY KEY,
                    connector_id TEXT NOT NULL,
                    capability_id TEXT NOT NULL,
                    interval_seconds INTEGER NOT NULL,
                    outcome TEXT NOT NULL,
                    last_run_at TEXT,
                    last_success_at TEXT,
                    last_error_at TEXT,
                    last_error TEXT,
                    consecutive_failures INTEGER NOT NULL DEFAULT 0,
                    duration_ms INTEGER,
                    resource_count INTEGER
                )
                """
            )

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS component_status (
                    component TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    detail TEXT,
                    updated_at TEXT NOT NULL,
                    last_message_at TEXT
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

    def delete(
        self,
        *,
        connector: str,
        capability: str,
        resource_id: str,
    ) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                DELETE FROM current_state
                WHERE connector = ?
                  AND capability = ?
                  AND resource_id = ?
                """,
                (connector, capability, resource_id),
            )

        return cursor.rowcount > 0

    def retain(
        self,
        *,
        connector: str,
        capability: str,
        resource_ids: list[str],
    ) -> int:
        """Remove recursos da capability que não estão no inventário atual."""

        keep = set(resource_ids)

        with self._connect() as connection:
            existing = [
                row["resource_id"]
                for row in connection.execute(
                    """
                    SELECT resource_id
                    FROM current_state
                    WHERE connector = ? AND capability = ?
                    """,
                    (connector, capability),
                )
            ]

            removed = [
                resource_id
                for resource_id in existing
                if resource_id not in keep
            ]

            connection.executemany(
                """
                DELETE FROM current_state
                WHERE connector = ? AND capability = ? AND resource_id = ?
                """,
                [
                    (connector, capability, resource_id)
                    for resource_id in removed
                ],
            )

        return len(removed)

    def record_job_run(
        self,
        *,
        job_id: str,
        connector_id: str,
        capability_id: str,
        interval_seconds: int,
        outcome: str,
        error: str | None = None,
        duration_ms: int | None = None,
        resource_count: int | None = None,
    ) -> None:
        now = _now_iso()
        success = outcome == "ok"
        failure = outcome == "error"

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO job_status (
                    job_id, connector_id, capability_id, interval_seconds,
                    outcome, last_run_at, last_success_at, last_error_at,
                    last_error, consecutive_failures, duration_ms,
                    resource_count
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

                ON CONFLICT (job_id) DO UPDATE SET
                    connector_id = excluded.connector_id,
                    capability_id = excluded.capability_id,
                    interval_seconds = excluded.interval_seconds,
                    outcome = excluded.outcome,
                    last_run_at = excluded.last_run_at,
                    last_success_at = COALESCE(
                        excluded.last_success_at,
                        job_status.last_success_at
                    ),
                    last_error_at = COALESCE(
                        excluded.last_error_at,
                        job_status.last_error_at
                    ),
                    last_error = CASE
                        WHEN excluded.outcome = 'ok' THEN NULL
                        ELSE COALESCE(excluded.last_error, job_status.last_error)
                    END,
                    consecutive_failures = CASE
                        WHEN excluded.outcome = 'error'
                            THEN job_status.consecutive_failures + 1
                        ELSE 0
                    END,
                    duration_ms = excluded.duration_ms,
                    resource_count = COALESCE(
                        excluded.resource_count,
                        job_status.resource_count
                    )
                """,
                (
                    job_id,
                    connector_id,
                    capability_id,
                    interval_seconds,
                    outcome,
                    now,
                    now if success else None,
                    now if failure else None,
                    error,
                    1 if failure else 0,
                    duration_ms,
                    resource_count,
                ),
            )

    def list_job_status(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM job_status ORDER BY job_id"
            ).fetchall()

        return [dict(row) for row in rows]

    def report_component(
        self,
        component: str,
        status: str,
        *,
        detail: str | None = None,
        message_seen: bool = False,
    ) -> None:
        now = _now_iso()

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO component_status (
                    component, status, detail, updated_at, last_message_at
                )
                VALUES (?, ?, ?, ?, ?)

                ON CONFLICT (component) DO UPDATE SET
                    status = excluded.status,
                    detail = excluded.detail,
                    updated_at = excluded.updated_at,
                    last_message_at = COALESCE(
                        excluded.last_message_at,
                        component_status.last_message_at
                    )
                """,
                (
                    component,
                    status,
                    detail,
                    now,
                    now if message_seen else None,
                ),
            )

    def list_component_status(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM component_status ORDER BY component"
            ).fetchall()

        return [dict(row) for row in rows]

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
