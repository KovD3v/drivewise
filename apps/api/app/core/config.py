import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


DEFAULT_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/drivewise"
DEFAULT_API_CORS_ORIGINS = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
)
PROJECT_ROOT = Path(__file__).resolve().parents[4]
# Environments where docs, OpenAPI and internal/debug routes are on by default.
INTERNAL_ROUTE_ENVS = frozenset({"local", "test"})
ENV_FILE_KEYS = frozenset(
    {
        "APP_ENV",
        "DATABASE_URL",
        "API_CORS_ORIGINS",
        "API_ROOT_PATH",
        "FIRECRAWL_API_KEY",
        "ENABLE_INTERNAL_ROUTES",
    }
)


@dataclass(frozen=True)
class Settings:
    app_env: str = "local"
    database_url: str = DEFAULT_DATABASE_URL
    api_cors_origins: tuple[str, ...] = DEFAULT_API_CORS_ORIGINS
    firecrawl_api_key: str | None = None
    # Path prefix the API is served under when it shares a domain with the
    # frontend (for example "/api"). Requests without the prefix still match.
    api_root_path: str = ""
    # Docs, OpenAPI and the listings/documents/search/resolve/recommendations
    # routes. Off by default outside local and test; ENABLE_INTERNAL_ROUTES
    # overrides it either way.
    enable_internal_routes: bool = True


def load_env_file(
    env_path: Path = PROJECT_ROOT / ".env",
    allowed_keys: frozenset[str] = ENV_FILE_KEYS,
) -> None:
    if not env_path.exists():
        return

    for raw_line in env_path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", maxsplit=1)
        key = key.removeprefix("export ").strip()
        value = value.strip().strip('"').strip("'")
        if key not in allowed_keys:
            continue
        if key:
            os.environ.setdefault(key, value)


def parse_csv_list(value: str | None) -> tuple[str, ...]:
    if value is None:
        return ()

    return tuple(item.strip() for item in value.split(",") if item.strip())


def parse_bool(value: str | None, default: bool) -> bool:
    if value is None or not value.strip():
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"Invalid boolean value: {value!r}")


@lru_cache
def get_settings() -> Settings:
    load_env_file()
    app_env = os.getenv("APP_ENV", "local")
    configured_cors_origins = parse_csv_list(os.getenv("API_CORS_ORIGINS"))

    if app_env == "local":
        api_cors_origins = tuple(
            dict.fromkeys((*DEFAULT_API_CORS_ORIGINS, *configured_cors_origins))
        )
    else:
        # Fail closed: a deployed API with no configured origins allows none.
        api_cors_origins = configured_cors_origins

    return Settings(
        app_env=app_env,
        database_url=os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL),
        api_cors_origins=api_cors_origins,
        firecrawl_api_key=os.getenv("FIRECRAWL_API_KEY") or None,
        api_root_path=os.getenv("API_ROOT_PATH", "").rstrip("/"),
        enable_internal_routes=parse_bool(
            os.getenv("ENABLE_INTERNAL_ROUTES"),
            default=app_env in INTERNAL_ROUTE_ENVS,
        ),
    )
