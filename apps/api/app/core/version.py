import os
import tomllib
from functools import lru_cache
from importlib import metadata
from pathlib import Path

from app.db.migrations import MIGRATIONS_PATH, iter_migration_files


SERVICE_NAME = "drivewise-api"
PYPROJECT_PATH = Path(__file__).resolve().parents[2] / "pyproject.toml"


@lru_cache
def get_api_version(pyproject_path: Path = PYPROJECT_PATH) -> str | None:
    """Return the package version from installed metadata, else pyproject.toml."""
    try:
        return metadata.version(SERVICE_NAME)
    except metadata.PackageNotFoundError:
        pass
    try:
        with pyproject_path.open("rb") as file:
            return tomllib.load(file)["project"]["version"]
    except (OSError, KeyError, tomllib.TOMLDecodeError):
        return None


def get_git_commit() -> str | None:
    return os.environ.get("VERCEL_GIT_COMMIT_SHA") or None


@lru_cache
def get_schema_version(migrations_path: Path = MIGRATIONS_PATH) -> str | None:
    """Return the newest migration file name shipped with this build."""
    files = iter_migration_files(migrations_path)
    return files[-1].name if files else None
