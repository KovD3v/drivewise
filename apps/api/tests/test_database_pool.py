from app.core.config import Settings
from app.db import pool as pool_module
from app.db.pool import DatabaseConnectionPool


class FakeConnection:
    def __init__(self) -> None:
        self.closed = False

    def execute(self, query: str, params=None):
        return self

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass

    def close(self) -> None:
        self.closed = True


def make_pool(monkeypatch, clock):
    created = []

    def connect(*args, **kwargs):
        conn = FakeConnection()
        created.append(conn)
        return conn

    monkeypatch.setattr(pool_module.psycopg, "connect", connect)
    monkeypatch.setattr(pool_module, "monotonic", lambda: clock[0])
    settings = Settings(
        app_env="test", database_url="postgresql://user:pw@db.example/drivewise"
    )
    return DatabaseConnectionPool(settings, max_size=2, max_idle_seconds=60), created


def test_pool_reuses_a_recently_released_connection(monkeypatch):
    clock = [0.0]
    pool, created = make_pool(monkeypatch, clock)
    with pool.connection() as first:
        pass
    clock[0] = 59.0
    with pool.connection() as second:
        pass
    assert second is first
    assert len(created) == 1


def test_pool_replaces_a_connection_idle_past_the_limit(monkeypatch):
    clock = [0.0]
    pool, created = make_pool(monkeypatch, clock)
    with pool.connection() as stale:
        pass
    clock[0] = 61.0
    with pool.connection() as fresh:
        pass
    assert fresh is not stale
    assert stale.closed
    assert len(created) == 2
    # The discarded connection frees its slot, so the pool can still fill up.
    with pool.connection(), pool.connection():
        pass
    assert len(created) == 3
