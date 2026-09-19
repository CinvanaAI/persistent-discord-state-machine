"""Durable, guild-scoped workflow sessions with optimistic concurrency."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


class SessionError(RuntimeError):
    """Base class for workflow-session errors."""


class SessionExistsError(SessionError):
    """Raised when a new workflow would overwrite an active session."""


class SessionNotFoundError(SessionError):
    """Raised when a requested workflow session does not exist."""


class SessionStateError(SessionError):
    """Raised when an event is applied to the wrong workflow state."""


class ConcurrentUpdateError(SessionError):
    """Raised when a stale revision attempts to update a session."""


@dataclass(frozen=True)
class WorkflowSession:
    guild_id: int
    user_id: int
    state: str
    payload: dict[str, Any]
    revision: int
    updated_at: str


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


class SqliteSessionStore:
    """Persist one active workflow per `(guild_id, user_id)` pair."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                connection.execute("PRAGMA busy_timeout = 5000")
                yield connection
        finally:
            connection.close()

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS workflow_sessions (
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    state TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    revision INTEGER NOT NULL DEFAULT 1,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (guild_id, user_id)
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_workflow_sessions_user ON workflow_sessions(user_id)"
            )

    def start(
        self,
        guild_id: int,
        user_id: int,
        state: str,
        payload: dict[str, Any] | None = None,
        *,
        replace: bool = False,
    ) -> WorkflowSession:
        state = self._validate_state(state)
        encoded = self._encode_payload(payload if payload is not None else {})
        now = _utc_now()
        with self._connect() as connection:
            if replace:
                connection.execute(
                    """
                    INSERT INTO workflow_sessions(guild_id, user_id, state, payload_json, revision, updated_at)
                    VALUES(?, ?, ?, ?, 1, ?)
                    ON CONFLICT(guild_id, user_id) DO UPDATE SET
                        state=excluded.state,
                        payload_json=excluded.payload_json,
                        revision=workflow_sessions.revision + 1,
                        updated_at=excluded.updated_at
                    """,
                    (guild_id, user_id, state, encoded, now),
                )
            else:
                try:
                    connection.execute(
                        """
                        INSERT INTO workflow_sessions(guild_id, user_id, state, payload_json, revision, updated_at)
                        VALUES(?, ?, ?, ?, 1, ?)
                        """,
                        (guild_id, user_id, state, encoded, now),
                    )
                except sqlite3.IntegrityError as exc:
                    raise SessionExistsError(f"active session already exists for guild={guild_id} user={user_id}") from exc
        return self.require(guild_id, user_id)

    def get(self, guild_id: int, user_id: int) -> WorkflowSession | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM workflow_sessions WHERE guild_id=? AND user_id=?",
                (guild_id, user_id),
            ).fetchone()
        return self._session(row) if row is not None else None

    def require(self, guild_id: int, user_id: int) -> WorkflowSession:
        session = self.get(guild_id, user_id)
        if session is None:
            raise SessionNotFoundError(f"no active session for guild={guild_id} user={user_id}")
        return session

    def list_for_user(self, user_id: int) -> list[WorkflowSession]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM workflow_sessions WHERE user_id=? ORDER BY updated_at DESC, guild_id",
                (user_id,),
            ).fetchall()
        return [self._session(row) for row in rows]

    def transition(
        self,
        guild_id: int,
        user_id: int,
        *,
        expected_state: str,
        next_state: str,
        payload: dict[str, Any],
        expected_revision: int | None = None,
    ) -> WorkflowSession:
        next_state = self._validate_state(next_state)
        encoded = self._encode_payload(payload)
        now = _utc_now()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT state, revision FROM workflow_sessions WHERE guild_id=? AND user_id=?",
                (guild_id, user_id),
            ).fetchone()
            if row is None:
                raise SessionNotFoundError(f"no active session for guild={guild_id} user={user_id}")
            if row["state"] != expected_state:
                raise SessionStateError(f"expected state {expected_state!r}, found {row['state']!r}")
            revision = int(row["revision"])
            if expected_revision is not None and revision != expected_revision:
                raise ConcurrentUpdateError(f"expected revision {expected_revision}, found {revision}")
            updated = connection.execute(
                """
                UPDATE workflow_sessions
                SET state=?, payload_json=?, revision=revision+1, updated_at=?
                WHERE guild_id=? AND user_id=? AND revision=?
                """,
                (next_state, encoded, now, guild_id, user_id, revision),
            )
            if updated.rowcount != 1:
                raise ConcurrentUpdateError("session changed during transition")
        return self.require(guild_id, user_id)

    def complete(self, guild_id: int, user_id: int, *, expected_state: str | None = None) -> None:
        with self._connect() as connection:
            if expected_state is None:
                result = connection.execute(
                    "DELETE FROM workflow_sessions WHERE guild_id=? AND user_id=?",
                    (guild_id, user_id),
                )
            else:
                result = connection.execute(
                    "DELETE FROM workflow_sessions WHERE guild_id=? AND user_id=? AND state=?",
                    (guild_id, user_id, expected_state),
                )
            if result.rowcount != 1:
                current = connection.execute(
                    "SELECT state FROM workflow_sessions WHERE guild_id=? AND user_id=?",
                    (guild_id, user_id),
                ).fetchone()
                if current is None:
                    raise SessionNotFoundError(f"no active session for guild={guild_id} user={user_id}")
                raise SessionStateError(
                    f"session is in state {current['state']!r}, not {expected_state!r}"
                )

    @staticmethod
    def _validate_state(state: str) -> str:
        state = str(state).strip()
        if not state:
            raise ValueError("state must not be empty")
        return state

    @staticmethod
    def _encode_payload(payload: dict[str, Any]) -> str:
        if not isinstance(payload, dict):
            raise TypeError("payload must be a dictionary")
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    @staticmethod
    def _session(row: sqlite3.Row) -> WorkflowSession:
        payload = json.loads(row["payload_json"])
        if not isinstance(payload, dict):
            payload = {}
        return WorkflowSession(
            guild_id=int(row["guild_id"]),
            user_id=int(row["user_id"]),
            state=str(row["state"]),
            payload=payload,
            revision=int(row["revision"]),
            updated_at=str(row["updated_at"]),
        )
