import tomllib
from importlib import metadata

from fastapi.testclient import TestClient

from app.core import version as version_module
from app.db.migrations import iter_migration_files
from app.main import app
from app.services.advisor.scoring import SCORING_VERSION


EXPECTED_KEYS = {
    "service",
    "api_version",
    "git_commit",
    "scoring_version",
    "schema_version",
}


def pyproject_version() -> str:
    with version_module.PYPROJECT_PATH.open("rb") as file:
        return tomllib.load(file)["project"]["version"]


def test_version_reports_build_and_logic_versions(monkeypatch):
    monkeypatch.setenv("VERCEL_GIT_COMMIT_SHA", "abc1234")
    client = TestClient(app)

    response = client.get("/version")

    assert response.status_code == 200
    body = response.json()
    assert set(body) == EXPECTED_KEYS
    assert body["service"] == "drivewise-api"
    assert body["api_version"] == pyproject_version()
    assert body["git_commit"] == "abc1234"
    assert body["scoring_version"] == SCORING_VERSION
    assert body["schema_version"] == iter_migration_files()[-1].name


def test_version_commit_is_null_without_platform_variable(monkeypatch):
    monkeypatch.delenv("VERCEL_GIT_COMMIT_SHA", raising=False)
    client = TestClient(app)

    response = client.get("/version")

    assert response.status_code == 200
    assert response.json()["git_commit"] is None


def test_version_does_not_need_database():
    # No dependency override for get_connection: the route must not ask for one.
    route = next(r for r in app.routes if getattr(r, "path", None) == "/version")
    assert route.dependant.dependencies == []


def test_api_version_falls_back_to_pyproject(monkeypatch):
    def missing(_name: str) -> str:
        raise metadata.PackageNotFoundError

    monkeypatch.setattr(version_module.metadata, "version", missing)
    version_module.get_api_version.cache_clear()
    try:
        assert version_module.get_api_version() == pyproject_version()
    finally:
        version_module.get_api_version.cache_clear()


def test_api_version_is_null_when_no_source_exists(monkeypatch, tmp_path):
    def missing(_name: str) -> str:
        raise metadata.PackageNotFoundError

    monkeypatch.setattr(version_module.metadata, "version", missing)
    get_api_version = version_module.get_api_version.__wrapped__

    assert get_api_version(tmp_path / "missing.toml") is None


def test_schema_version_is_newest_migration_file(tmp_path):
    for name in ("0002_b.sql", "0010_c.sql", "0001_a.sql", "notes.txt"):
        (tmp_path / name).write_text("")
    get_schema_version = version_module.get_schema_version.__wrapped__

    assert get_schema_version(tmp_path) == "0010_c.sql"
    assert get_schema_version(tmp_path / "empty") is None
