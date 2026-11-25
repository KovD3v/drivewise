import os

from app.core.config import get_settings, load_env_file
from app.core.database_url import contains_placeholder_database_url


def test_settings_come_from_environment(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://drivewise:secret@localhost:5432/drivewise_test",
    )
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv(
        "API_CORS_ORIGINS",
        "http://localhost:3000, http://127.0.0.1:3000",
    )
    monkeypatch.setenv("FIRECRAWL_API_KEY", "fc-test-key")

    settings = get_settings()

    assert settings.app_env == "test"
    assert settings.database_url == (
        "postgresql://drivewise:secret@localhost:5432/drivewise_test"
    )
    assert settings.api_cors_origins == (
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    )
    assert settings.firecrawl_api_key == "fc-test-key"


def test_placeholder_database_url_detects_masked_password():
    assert contains_placeholder_database_url(
        "postgresql://postgres:***@localhost:5432/drivewise_test"
    )


def test_cors_origins_default_to_local_frontend(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("API_CORS_ORIGINS", "")

    settings = get_settings()

    assert settings.api_cors_origins == (
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    )


def test_firecrawl_api_key_is_optional(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)

    settings = get_settings()

    assert settings.firecrawl_api_key is None


def test_api_root_path_defaults_to_none_and_drops_a_trailing_slash(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.delenv("API_ROOT_PATH", raising=False)
    assert get_settings().api_root_path == ""

    get_settings.cache_clear()
    monkeypatch.setenv("API_ROOT_PATH", "/api/")
    assert get_settings().api_root_path == "/api"
    get_settings.cache_clear()


def test_api_root_path_is_read_from_the_env_file(monkeypatch, tmp_path):
    monkeypatch.delenv("API_ROOT_PATH", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text("API_ROOT_PATH=/api\n")

    load_env_file(env_file)
    get_settings.cache_clear()
    try:
        assert get_settings().api_root_path == "/api"
    finally:
        # load_env_file wrote to os.environ directly, so remove it the same way.
        os.environ.pop("API_ROOT_PATH", None)
        get_settings.cache_clear()
