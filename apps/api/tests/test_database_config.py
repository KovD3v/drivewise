from app.core.config import get_settings
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
