import os
import sqlite3
from datetime import datetime, timezone
from threading import Lock


_EXECUTION_REPLAY_DB_PATH_ENV = "NIGHTLEDGER_EXECUTION_REPLAY_DB_PATH"
_DEFAULT_EXECUTION_REPLAY_DB_PATH = "/tmp/nightledger_execution_replay.db"


class SQLiteExecutionReplayStore:
    def __init__(self, path: str | None = None) -> None:
        self._path = path if path is not None else configured_execution_replay_db_path()
        self._lock = Lock()
        self._initialize()

    def consume_once(self, *, jti: str, exp_unix: int) -> bool:
        self._purge_expired()
        now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        with self._lock:
            with sqlite3.connect(self._path) as conn:
                cursor = conn.execute(
                    "INSERT OR IGNORE INTO used_execution_tokens (jti, exp_unix, used_at) VALUES (?, ?, ?)",
                    (jti, exp_unix, now_iso),
                )
                conn.commit()
                return cursor.rowcount == 1

    def _initialize(self) -> None:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with self._lock:
            with sqlite3.connect(self._path) as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS used_execution_tokens (
                        jti TEXT PRIMARY KEY,
                        exp_unix INTEGER NOT NULL,
                        used_at TEXT NOT NULL
                    )
                    """
                )
                conn.commit()

    def _purge_expired(self) -> None:
        now_unix = int(datetime.now(timezone.utc).timestamp())
        with self._lock:
            with sqlite3.connect(self._path) as conn:
                conn.execute("DELETE FROM used_execution_tokens WHERE exp_unix < ?", (now_unix,))
                conn.commit()


def configured_execution_replay_db_path() -> str:
    configured = os.getenv(_EXECUTION_REPLAY_DB_PATH_ENV)
    if configured is None:
        return _DEFAULT_EXECUTION_REPLAY_DB_PATH
    value = configured.strip()
    if value == "":
        return _DEFAULT_EXECUTION_REPLAY_DB_PATH
    return value
