from collections.abc import Iterator
from contextlib import contextmanager
from queue import Empty, LifoQueue
from threading import Lock

import psycopg
from psycopg.rows import dict_row

from app.core.config import DEFAULT_DATABASE_URL, Settings
from app.core.database_url import contains_placeholder_database_url


class DatabaseConfigurationError(RuntimeError):
    pass


class DatabaseConnectionPool:
    def __init__(self, settings: Settings, max_size: int = 5) -> None:
        self.settings = settings
        self.max_size = max_size
        self._available: LifoQueue[psycopg.Connection] = LifoQueue(maxsize=max_size)
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
                conn = self._available.get_nowait()
            except Empty:
                break
            conn.close()

        with self._lock:
            self._created = 0

    def _acquire(self) -> psycopg.Connection:
        self._closed = False
        try:
            return self._available.get_nowait()
        except Empty:
            pass

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

        return self._available.get()

    def _release(self, conn: psycopg.Connection) -> None:
        if conn.closed or self._closed:
            conn.close()
            with self._lock:
                self._created -= 1
            return

        try:
            self._available.put_nowait(conn)
        except Exception:
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
