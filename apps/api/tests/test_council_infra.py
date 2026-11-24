import json
import threading
import time
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import (
    get_database_pool,
    get_guided_decisions_repository,
    get_vehicles_repository,
)
from app.core.config import Settings, get_settings
from app.db import pool as pool_module
from app.db.pool import (
    TRANSACTION_TIMEOUTS_SQL,
    DatabaseConnectionPool,
    DatabasePoolClosedError,
    DatabasePoolTimeoutError,
)
from app.ingestion.catalog import _upsert_sources, load_catalog
from app.main import (
    PRIVATE_NO_STORE,
    PUBLIC_CATALOG_CACHE,
    app,
    create_app,
)


ROOT = Path(__file__).resolve().parents[3]
CATALOG_FIXTURE = ROOT / "data/fixtures/catalog/catalog-v1.synthetic.json"
DB_URL = "postgresql://user:pw@db.example/drivewise"


class FakeConnection:
    def __init__(self, *, fail_commit: bool = False) -> None:
        self.closed = False
        self.broken = False
        self.fail_commit = fail_commit
        self.rollbacks = 0
        self.commits = 0
        self.queries: list[str] = []
        self.fail_execute = False

    def execute(self, query: str, params=None):
        if self.fail_execute:
            raise pool_module.psycopg.OperationalError("server closed the connection")
        self.queries.append(query)
        return self

    def fetchone(self):
        return (1,)

    def commit(self) -> None:
        if self.fail_commit:
            # Not an OperationalError: get_connection maps those to 503.
            raise RuntimeError("commit failed")
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1

    def close(self) -> None:
        self.closed = True


def make_pool(monkeypatch, *, max_size=2, acquire_timeout=5.0, factory=None):
    created: list[FakeConnection] = []
    calls: list[dict] = []

    def connect(*args, **kwargs):
        calls.append(kwargs)
        conn = factory() if factory else FakeConnection()
        created.append(conn)
        return conn

    monkeypatch.setattr(pool_module.psycopg, "connect", connect)
    pool = DatabaseConnectionPool(
        Settings(app_env="test", database_url=DB_URL),
        max_size=max_size,
        acquire_timeout=acquire_timeout,
    )
    return pool, created, calls


def prod_settings(**overrides) -> Settings:
    values = dict(
        app_env="production",
        database_url=DB_URL,
        api_cors_origins=("https://drivewise.example",),
        enable_internal_routes=False,
    )
    values.update(overrides)
    return Settings(**values)


@pytest.fixture
def clean_settings():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


# --- Commit before 2xx ------------------------------------------------------


def test_commit_failure_returns_500_not_200(monkeypatch):
    pool, created, _ = make_pool(
        monkeypatch, factory=lambda: FakeConnection(fail_commit=True)
    )
    app.dependency_overrides[get_database_pool] = lambda: pool
    try:
        response = TestClient(app, raise_server_exceptions=False).get("/ready")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 500
    # A connection whose commit failed is never handed out again.
    assert created[0].closed
    assert pool._created == 0


class EmptyAdvisorRepository:
    def list_candidates(self, *, as_of):
        return []

    def count_excluded_candidates(self, *, as_of):
        return {}


class RecordingDecisionsRepository:
    def __init__(self) -> None:
        self.created = 0

    def create(self, **_kwargs):
        self.created += 1


def post_guided_decision(monkeypatch, *, fail_commit: bool):
    from app.api.dependencies import ConnectionDep, get_advisor_repository

    pool, created, _ = make_pool(
        monkeypatch, factory=lambda: FakeConnection(fail_commit=fail_commit)
    )
    decisions = RecordingDecisionsRepository()

    # Keep the real connection dependency (and its scope) in the request while
    # replacing only the repository logic.
    def decisions_with_connection(conn: ConnectionDep):
        return decisions

    app.dependency_overrides[get_database_pool] = lambda: pool
    app.dependency_overrides[get_guided_decisions_repository] = (
        decisions_with_connection
    )
    app.dependency_overrides[get_advisor_repository] = EmptyAdvisorRepository
    try:
        response = TestClient(app, raise_server_exceptions=False).post(
            "/guided-decisions",
            json={"message": "Cerco un SUV, budget 30.000 euro", "market": "IT"},
        )
    finally:
        app.dependency_overrides.clear()
    return response, decisions, created


def test_commit_failure_on_a_write_endpoint_returns_500(monkeypatch):
    response, decisions, created = post_guided_decision(monkeypatch, fail_commit=True)

    assert decisions.created == 1
    assert response.status_code == 500
    assert created[0].closed


def test_write_endpoint_commits_before_returning_200(monkeypatch):
    response, decisions, created = post_guided_decision(
        monkeypatch, fail_commit=False
    )

    assert response.status_code == 200
    assert decisions.created == 1
    assert created[0].commits == 1


def test_connection_dependency_uses_function_scope():
    from app.api.dependencies import ConnectionDep

    depends = ConnectionDep.__metadata__[0]
    assert depends.scope == "function"


# --- Pool hardening ---------------------------------------------------------


def test_pool_sets_timeouts_per_transaction(monkeypatch):
    pool, created, calls = make_pool(monkeypatch)
    with pool.connection():
        pass
    with pool.connection():
        pass
    assert calls[0]["connect_timeout"] == 5
    # Neon's pooled endpoint rejects libpq startup options.
    assert "options" not in calls[0]
    # Every transaction, including one on a reused connection, gets the limits.
    assert created[0].queries == [TRANSACTION_TIMEOUTS_SQL] * 2
    for setting in (
        "statement_timeout = 5000",
        "lock_timeout = 2000",
        "idle_in_transaction_session_timeout = 10000",
    ):
        assert f"SET LOCAL {setting}" in TRANSACTION_TIMEOUTS_SQL


def test_pool_retries_once_when_a_pooled_connection_is_dead(monkeypatch):
    pool, created, _ = make_pool(monkeypatch)
    with pool.connection():
        pass
    created[0].fail_execute = True  # the server dropped it while idle

    with pool.connection() as conn:
        assert conn is created[1]
    assert created[0].closed
    assert pool._created == 1


def test_pool_skips_every_dead_idle_connection(monkeypatch):
    pool, created, _ = make_pool(monkeypatch, max_size=2)
    with pool.connection(), pool.connection():
        pass
    for conn in created:
        conn.fail_execute = True  # a suspended compute dropped them all

    with pool.connection() as conn:
        assert conn is created[2]
    assert created[0].closed and created[1].closed
    assert pool._created == 1


def test_pool_gives_up_when_new_connections_are_dead_too(monkeypatch):
    def dead():
        conn = FakeConnection()
        conn.fail_execute = True
        return conn

    pool, created, _ = make_pool(monkeypatch, max_size=2, factory=dead)
    with pytest.raises(pool_module.psycopg.OperationalError):
        with pool.connection():
            pass
    assert len(created) == 3  # bounded: max_size + 1 attempts
    assert pool._created == 0


def test_pool_acquire_times_out_when_exhausted(monkeypatch):
    pool, _, _ = make_pool(monkeypatch, max_size=1, acquire_timeout=0.05)
    with pool.connection():
        started = time.monotonic()
        with pytest.raises(DatabasePoolTimeoutError):
            with pool.connection():
                pass
        assert time.monotonic() - started < 2


def test_pool_waiter_gets_slot_after_failed_creation(monkeypatch):
    attempts = {"n": 0}

    def flaky():
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise OSError("connect failed")
        return FakeConnection()

    pool, _, _ = make_pool(monkeypatch, max_size=1, factory=flaky)
    with pytest.raises(OSError):
        with pool.connection():
            pass
    assert pool._created == 0
    with pool.connection() as conn:
        assert isinstance(conn, FakeConnection)


def test_pool_discard_wakes_a_blocked_waiter(monkeypatch):
    pool, created, _ = make_pool(monkeypatch, max_size=1, acquire_timeout=5.0)
    result: dict = {}
    holder_ready = threading.Event()
    release = threading.Event()

    def holder():
        with pool.connection() as conn:
            holder_ready.set()
            release.wait(5)
            conn.broken = True  # released broken: must be discarded

    def waiter():
        try:
            with pool.connection() as conn:
                result["conn"] = conn
        except Exception as error:  # pragma: no cover - surfaced by assert
            result["error"] = error

    t1 = threading.Thread(target=holder)
    t1.start()
    assert holder_ready.wait(5)
    t2 = threading.Thread(target=waiter)
    t2.start()
    time.sleep(0.05)
    release.set()
    t1.join(5)
    t2.join(5)
    assert not t1.is_alive() and not t2.is_alive()
    assert "error" not in result
    assert result["conn"] is not created[0]
    assert created[0].closed
    assert pool._created == 1


def test_pool_does_not_rollback_a_broken_connection(monkeypatch):
    pool, created, _ = make_pool(monkeypatch)
    with pytest.raises(ValueError):
        with pool.connection() as conn:
            conn.broken = True
            raise ValueError("boom")
    assert created[0].rollbacks == 0
    assert created[0].closed
    assert pool._created == 0


def test_pool_rolls_back_and_reuses_a_healthy_connection(monkeypatch):
    pool, created, _ = make_pool(monkeypatch)
    with pytest.raises(ValueError):
        with pool.connection():
            raise ValueError("boom")
    assert created[0].rollbacks == 1
    with pool.connection() as again:
        assert again is created[0]


def test_closed_pool_rejects_acquisition_and_wakes_waiters(monkeypatch):
    pool, _, _ = make_pool(monkeypatch, max_size=1)
    outcome: dict = {}
    holding = threading.Event()

    def waiter():
        try:
            with pool.connection():
                pass
        except Exception as error:
            outcome["error"] = error

    with pool.connection():
        holding.set()
        thread = threading.Thread(target=waiter)
        thread.start()
        time.sleep(0.05)
        pool.close()
        thread.join(5)
        assert not thread.is_alive()
    assert isinstance(outcome["error"], DatabasePoolClosedError)
    assert pool.closed
    with pytest.raises(DatabasePoolClosedError):
        with pool.connection():
            pass
    # The checked-out connection gave its slot back on release.
    assert pool._created == 0


def test_closed_pool_on_app_state_is_replaced(monkeypatch):
    pool, _, _ = make_pool(monkeypatch)
    pool.close()

    class State:
        database_pool = pool

    class FakeApp:
        state = State()

    class FakeRequest:
        app = FakeApp()

    replacement = get_database_pool(FakeRequest())
    assert replacement is not pool
    assert not replacement.closed


def test_pool_timeout_maps_to_503(monkeypatch):
    pool, _, _ = make_pool(monkeypatch, max_size=1, acquire_timeout=0.01)
    app.dependency_overrides[get_database_pool] = lambda: pool
    try:
        with pool.connection():
            response = TestClient(app, raise_server_exceptions=False).get("/ready")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 503


# --- Settings ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("app_env", "expected"),
    [("local", True), ("test", True), ("production", False), ("preview", False)],
)
def test_internal_routes_default_by_environment(
    monkeypatch, clean_settings, app_env, expected
):
    monkeypatch.setenv("APP_ENV", app_env)
    monkeypatch.delenv("ENABLE_INTERNAL_ROUTES", raising=False)
    assert get_settings().enable_internal_routes is expected


def test_internal_routes_env_override(monkeypatch, clean_settings):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ENABLE_INTERNAL_ROUTES", "true")
    assert get_settings().enable_internal_routes is True
    get_settings.cache_clear()
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("ENABLE_INTERNAL_ROUTES", "0")
    assert get_settings().enable_internal_routes is False


def test_cors_fails_closed_outside_local(monkeypatch, clean_settings):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("API_CORS_ORIGINS", "")
    assert get_settings().api_cors_origins == ()


def test_enable_internal_routes_is_read_from_env_file():
    from app.core.config import ENV_FILE_KEYS

    assert "ENABLE_INTERNAL_ROUTES" in ENV_FILE_KEYS


# --- Route gating and headers -----------------------------------------------


def test_production_app_hides_docs_and_internal_routers():
    client = TestClient(create_app(prod_settings()))
    for path in ("/docs", "/redoc", "/openapi.json", "/listings", "/documents"):
        assert client.get(path).status_code == 404, path
    assert client.post("/search/documents", json={}).status_code in {404, 405}
    assert client.get("/health").status_code == 200


def test_production_gates_resolve_and_recommendations_before_validation(
    monkeypatch,
):
    production = create_app(prod_settings())

    def must_not_connect():
        raise AssertionError("gated route acquired a database connection")

    production.dependency_overrides[get_database_pool] = must_not_connect
    client = TestClient(production)
    # Empty bodies: a 404 (not 422) proves the gate runs before validation.
    assert client.post("/vehicles/resolve", json={}).status_code == 404
    assert client.post("/advisor/recommendations", json={}).status_code == 404


def test_production_keeps_public_routes(monkeypatch):
    from app.api.dependencies import get_advisor_repository

    production = create_app(prod_settings())

    class Vehicles:
        def list_vehicles(self, filters):
            return []

    production.dependency_overrides[get_vehicles_repository] = lambda: Vehicles()
    production.dependency_overrides[get_advisor_repository] = EmptyAdvisorRepository
    client = TestClient(production)
    response = client.get("/vehicles")
    assert response.status_code == 200
    # model-analysis stays routed: validation error, not 404.
    assert client.post("/advisor/model-analysis", json=None).status_code != 404


def test_local_app_keeps_docs_and_internal_routes():
    local = create_app(Settings(app_env="local"))
    paths = {route.path for route in local.routes}
    assert {"/docs", "/openapi.json", "/listings", "/documents"} <= paths


def test_cors_restricts_methods_and_headers():
    client = TestClient(create_app(prod_settings()))
    preflight = client.options(
        "/vehicles",
        headers={
            "Origin": "https://drivewise.example",
            "Access-Control-Request-Method": "DELETE",
        },
    )
    assert preflight.status_code == 400
    allowed = client.options(
        "/vehicles",
        headers={
            "Origin": "https://drivewise.example",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization",
        },
    )
    assert allowed.status_code == 400


def test_vehicle_filters_reject_long_strings():
    class Vehicles:
        def list_vehicles(self, filters):
            return []

    app.dependency_overrides[get_vehicles_repository] = lambda: Vehicles()
    try:
        client = TestClient(app)
        assert client.get("/vehicles", params={"make": "x" * 121}).status_code == 422
        assert client.get("/vehicles", params={"make": "x" * 120}).status_code == 200
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize("root_path", ["", "/api"])
def test_cache_headers(root_path):
    instance = create_app(Settings(app_env="local", api_root_path=root_path))
    vehicle_id = uuid4()

    class Vehicles:
        def list_vehicles(self, filters):
            return []

        def get_vehicle(self, _id):
            return None

    class Decisions:
        def get(self, decision_id, **_kwargs):
            from app.repositories.guided_decisions import (
                GuidedDecisionNotFoundError,
            )

            raise GuidedDecisionNotFoundError(str(decision_id))

    instance.dependency_overrides[get_vehicles_repository] = lambda: Vehicles()
    instance.dependency_overrides[get_guided_decisions_repository] = (
        lambda: Decisions()
    )
    from app.api.dependencies import get_advisor_repository

    instance.dependency_overrides[get_advisor_repository] = EmptyAdvisorRepository
    client = TestClient(instance, raise_server_exceptions=False)

    listing = client.get(f"{root_path}/vehicles")
    assert listing.status_code == 200
    assert listing.headers["cache-control"] == PUBLIC_CATALOG_CACHE

    missing = client.get(f"{root_path}/vehicles/{vehicle_id}")
    assert missing.status_code == 404
    assert "cache-control" not in missing.headers

    decision = client.get(f"{root_path}/guided-decisions/{uuid4()}")
    assert decision.status_code == 404
    assert decision.headers["cache-control"] == PRIVATE_NO_STORE

    health = client.get(f"{root_path}/health")
    assert "cache-control" not in health.headers


# --- Catalog v1 guard -------------------------------------------------------


class RecordingConnection:
    def __init__(self) -> None:
        self.queries: list[str] = []
        self.existing_id = uuid4()

    def execute(self, query, params=None):
        self.queries.append(query)
        return self

    def fetchone(self):
        return {"id": self.existing_id}


def test_v1_source_upsert_never_overwrites_existing_sources():
    payload = load_catalog(CATALOG_FIXTURE)
    conn = RecordingConnection()

    source_ids = _upsert_sources(conn, payload.sources[:1])

    insert = conn.queries[0]
    assert "ON CONFLICT (source_key) DO NOTHING" in insert
    assert "DO UPDATE" not in insert
    assert "SELECT id FROM sources WHERE source_key" in conn.queries[1]
    assert source_ids == {payload.sources[0].source_key: conn.existing_id}


def _load_import_script():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "council_import_catalog_script", ROOT / "apps/api/scripts/import_catalog.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("app_env", ["production", "preview"])
def test_import_catalog_v1_refuses_write_outside_local(
    monkeypatch, capsys, tmp_path, app_env
):
    module = _load_import_script()
    monkeypatch.setenv("APP_ENV", app_env)
    monkeypatch.setenv("DATABASE_URL", DB_URL)
    monkeypatch.setattr(module, "load_env_file", lambda _path: None)

    def must_not_connect(*_a, **_k):
        raise AssertionError("connected despite the write freeze")

    monkeypatch.setattr(module.psycopg, "connect", must_not_connect)

    exit_code = module.main(
        ["--path", str(CATALOG_FIXTURE), "--write"], env_path=tmp_path / ".env"
    )

    err = capsys.readouterr().err
    assert exit_code == 1
    assert "import_catalog_v2.py" in err
    assert f"APP_ENV={app_env}" in err


def test_import_catalog_v1_check_still_works_in_production(monkeypatch, capsys):
    module = _load_import_script()
    monkeypatch.setenv("APP_ENV", "production")
    assert module.main(["--path", str(CATALOG_FIXTURE), "--check"]) == 0
    assert "Catalog is valid." in capsys.readouterr().out


# --- vercel.json ------------------------------------------------------------


def test_vercel_sets_security_headers():
    config = json.loads((ROOT / "vercel.json").read_text())
    headers = {
        item["key"]: item["value"]
        for rule in config["headers"]
        if rule["source"] == "/(.*)"
        for item in rule["headers"]
    }
    assert headers == {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    }


def test_app_pool_uses_the_app_settings_not_global_ones():
    settings = prod_settings(database_url="postgresql://u:p@factory.example/dw")
    instance = create_app(settings)
    with TestClient(instance):
        assert instance.state.database_pool.settings is settings

    class FakeRequest:
        app = create_app(settings)

    assert get_database_pool(FakeRequest()).settings is settings
