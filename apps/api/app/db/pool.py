import time
from collections.abc import Iterator
from contextlib import contextmanager
from threading import Condition
from time import monotonic

import psycopg
from psycopg.rows import dict_row

from app.core.config import DEFAULT_DATABASE_URL, Settings
from app.core.database_url import contains_placeholder_database_url


CONNECT_TIMEOUT_SECONDS = 5
# Server-side limits so one slow query or abandoned transaction cannot hold a
# pooled connection (and a serverless instance) indefinitely. They are set per
# transaction, not as libpq startup `options`: Neon's pooled endpoint rejects
# startup options ("unsupported startup parameter in options"), and with
# transaction pooling only SET LOCAL reliably applies to our own transaction.
TRANSACTION_TIMEOUTS_SQL = (
    "SET LOCAL statement_timeout = 5000; "
    "SET LOCAL lock_timeout = 2000; "
    "SET LOCAL idle_in_transaction_session_timeout = 10000"
)


class DatabaseConfigurationError(RuntimeError):
    pass


class DatabasePoolTimeoutError(RuntimeError):
    """No connection became available within the acquire timeout."""


class DatabasePoolClosedError(RuntimeError):
    """The pool was closed explicitly and no longer hands out connections."""


def _is_unusable(conn: psycopg.Connection) -> bool:
    return bool(conn.closed or getattr(conn, "broken", False))


class DatabaseConnectionPool:
    def __init__(
        self,
        settings: Settings,
        max_size: int = 5,
        max_idle_seconds: float = 60.0,
        acquire_timeout: float = 5.0,
    ) -> None:
        self.settings = settings
        self.max_size = max_size
        # Serverless instances freeze and Neon suspends idle computes, so a
        # connection left idle can be dead without psycopg noticing.
        self.max_idle_seconds = max_idle_seconds
        self.acquire_timeout = acquire_timeout
        # LIFO stack of (connection, released_at); guarded by _condition.
        self._idle: list[tuple[psycopg.Connection, float]] = []
        # Connections that exist: idle plus checked out plus being created.
        self._created = 0
        self._closed = False
        self._condition = Condition()

    @property
    def closed(self) -> bool:
        return self._closed

    @contextmanager
    def connection(self) -> Iterator[psycopg.Connection]:
        self._ensure_configured()
        conn = self._acquire_prepared()
        reusable = True
        try:
            yield conn
        except BaseException:
            if _is_unusable(conn):
                reusable = False
            else:
                try:
                    conn.rollback()
                except Exception:
                    # Keep the original error; just never reuse this connection.
                    reusable = False
            raise
        else:
            try:
                conn.commit()
            except BaseException:
                reusable = False
                raise
        finally:
            if reusable:
                self._release(conn)
            else:
                self._discard(conn)

    def close(self) -> None:
        with self._condition:
            self._closed = True
            idle, self._idle = self._idle, []
            # Checked-out connections give their slot back on release.
            self._created -= len(idle)
            self._condition.notify_all()
        for conn, _ in idle:
            self._close_quietly(conn)

    def _acquire_prepared(self) -> psycopg.Connection:
        """Acquire a connection and open its transaction with the timeouts.

        The preamble is the first round trip, so it also finds a pooled
        connection the server dropped while idle. No request work has run
        yet, so one retry on a fresh connection is safe.
        """
        for attempt in range(2):
            conn = self._acquire()
            try:
                conn.execute(TRANSACTION_TIMEOUTS_SQL)
            except psycopg.OperationalError:
                self._discard(conn)
                if attempt == 1:
                    raise
            except BaseException:
                self._discard(conn)
                raise
            else:
                return conn
        raise AssertionError("unreachable")

    def _acquire(self) -> psycopg.Connection:
        # Idle age uses the patchable `monotonic`; the wait deadline uses the
        # real clock so a frozen test clock cannot make a waiter spin forever.
        deadline = time.monotonic() + self.acquire_timeout
        stale: list[psycopg.Connection] = []
        try:
            with self._condition:
                while True:
                    if self._closed:
                        raise DatabasePoolClosedError(
                            "The database connection pool is closed."
                        )
                    while self._idle:
                        conn, released_at = self._idle.pop()
                        fresh = monotonic() - released_at <= self.max_idle_seconds
                        if fresh and not _is_unusable(conn):
                            return conn
                        stale.append(conn)
                        self._created -= 1
                    if self._created < self.max_size:
                        self._created += 1
                        break
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise DatabasePoolTimeoutError(
                            "Timed out waiting for a database connection."
                        )
                    self._condition.wait(remaining)
                if stale:
                    # Dropping stale connections may have freed extra slots.
                    self._condition.notify_all()
        finally:
            for conn in stale:
                self._close_quietly(conn)

        try:
            return psycopg.connect(
                self.settings.database_url,
                row_factory=dict_row,
                connect_timeout=CONNECT_TIMEOUT_SECONDS,
            )
        except BaseException:
            self._free_slot()
            raise

    def _release(self, conn: psycopg.Connection) -> None:
        if not _is_unusable(conn):
            with self._condition:
                if not self._closed and len(self._idle) < self.max_size:
                    self._idle.append((conn, monotonic()))
                    self._condition.notify()
                    return
        self._discard(conn)

    def _discard(self, conn: psycopg.Connection) -> None:
        try:
            self._close_quietly(conn)
        finally:
            self._free_slot()

    def _free_slot(self) -> None:
        with self._condition:
            self._created -= 1
            self._condition.notify()

    @staticmethod
    def _close_quietly(conn: psycopg.Connection) -> None:
        try:
            conn.close()
        except Exception:
            pass

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
