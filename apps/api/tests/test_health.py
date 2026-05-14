from fastapi.testclient import TestClient

from app.api.dependencies import get_connection
from app.main import app


def test_health_returns_ok_status():
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "drivewise-api"}


def test_preflight_allows_configured_local_frontend_origin():
    client = TestClient(app)

    response = client.options(
        "/advisor/recommendations",
        headers={
            "Origin": "http://127.0.0.1:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == (
        "http://127.0.0.1:3000"
    )


def test_health_response_includes_cors_header_for_allowed_origin():
    client = TestClient(app)

    response = client.get(
        "/health",
        headers={"Origin": "http://localhost:3000"},
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == (
        "http://localhost:3000"
    )


def test_ready_checks_database_connection():
    fake_connection = FakeConnection()

    def override_connection():
        yield fake_connection

    app.dependency_overrides[get_connection] = override_connection
    client = TestClient(app)

    response = client.get("/ready")

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "service": "drivewise-api",
        "database": "ok",
    }
    assert fake_connection.queries == ["SELECT 1"]


class FakeConnection:
    def __init__(self) -> None:
        self.queries: list[str] = []

    def execute(self, query: str):
        self.queries.append(query)
        return self

    def fetchone(self):
        return (1,)
