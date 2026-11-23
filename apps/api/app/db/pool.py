from collections.abc import Iterator
from contextlib import contextmanager
from queue import Empty, LifoQueue
from threading import Lock
from time import monotonic

import psycopg
from psycopg.rows import dict_row

from app.core.config import DEFAULT_DATABASE_URL, Settings
from app.core.database_url import contains_placeholder_database_url


class DatabaseConfigurationError(RuntimeError):
    pass


class DatabaseConnectionPool:
    def __init__(
        self,
        settings: Settings,
        max_size: int = 5,
        max_idle_seconds: float = 60.0,
    ) -> None:
        self.settings = settings
        self.max_size = max_size
        # Serverless instances freeze and Neon suspends idle computes, so a
        # connection left idle can be dead without psycopg noticing.
        self.max_idle_seconds = max_idle_seconds
        self._available: LifoQueue[tuple[psycopg.Connection, float]] = LifoQueue(
            maxsize=max_size
        )
        self._created = 0
        self._closed = False
        self._lock = Lock()

    @contextmanager
    def connection(self) -> Iterator[psycopg.Connection]:
        self._ensure_configured()
        conn = self._acquire()
        try:
            yield conn
        except Exception:
            conn.rollback()
            raise
        else:
            conn.commit()
        finally:
            self._release(conn)

    def close(self) -> None:
        self._closed = True
        while True:
            try:
                conn, _ = self._available.get_nowait()
            except Empty:
                break
            conn.close()

        with self._lock:
            self._created = 0

    def _acquire(self) -> psycopg.Connection:
        self._closed = False
        while True:
            try:
                conn, released_at = self._available.get_nowait()
            except Empty:
                break
            if monotonic() - released_at <= self.max_idle_seconds:
                return conn
            self._discard(conn)

        with self._lock:
            if self._created < self.max_size:
                self._created += 1
                should_create = True
            else:
                should_create = False

        if should_create:
            try:
                return psycopg.connect(
                    self.settings.database_url,
                    row_factory=dict_row,
                )
            except Exception:
                with self._lock:
                    self._created -= 1
                raise

        conn, _ = self._available.get()
        return conn

    def _release(self, conn: psycopg.Connection) -> None:
        if conn.closed or self._closed:
            self._discard(conn)
            return

        try:
            self._available.put_nowait((conn, monotonic()))
        except Exception:
            self._discard(conn)

    def _discard(self, conn: psycopg.Connection) -> None:
        conn.close()
        with self._lock:
            self._created -= 1

    def _ensure_configured(self) -> None:
        if contains_placeholder_database_url(self.settings.database_url):
            raise DatabaseConfigurationError(
                "DATABASE_URL contains placeholder values. Configure a real "
                "database URL before using database-backed endpoints."
            )

        if (
            self.settings.app_env != "local"
            and self.settings.database_url == DEFAULT_DATABASE_URL
        ):
            raise DatabaseConfigurationError(
                "DATABASE_URL is required outside local development."
            )
