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
ENV_FILE_KEYS = frozenset(
    {"APP_ENV", "DATABASE_URL", "API_CORS_ORIGINS", "FIRECRAWL_API_KEY"}
)


@dataclass(frozen=True)
class Settings:
    app_env: str = "local"
    database_url: str = DEFAULT_DATABASE_URL
    api_cors_origins: tuple[str, ...] = DEFAULT_API_CORS_ORIGINS
    firecrawl_api_key: str | None = None


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
        api_cors_origins = configured_cors_origins or DEFAULT_API_CORS_ORIGINS

    return Settings(
        app_env=app_env,
        database_url=os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL),
        api_cors_origins=api_cors_origins,
        firecrawl_api_key=os.getenv("FIRECRAWL_API_KEY") or None,
    )
