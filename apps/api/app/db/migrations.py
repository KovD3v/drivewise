from dataclasses import dataclass
from pathlib import Path

import psycopg

from app.core.config import get_settings


MIGRATIONS_PATH = Path(__file__).resolve().parents[2] / "migrations"
RENAMED_MIGRATIONS = {
    "0005_catalog_evidence.sql": "0008_catalog_evidence.sql",
}


@dataclass(frozen=True)
class Migration:
    version: str
    name: str
    sql: str


@dataclass(frozen=True)
class MigrationRun:
    applied: list[str]
    already_applied: list[str]


def iter_migration_files(migrations_path: Path = MIGRATIONS_PATH) -> list[Path]:
    return sorted(migrations_path.glob("*.sql"))


def load_migrations(migrations_path: Path = MIGRATIONS_PATH) -> list[Migration]:
    migrations: list[Migration] = []
    versions: set[str] = set()

    for path in iter_migration_files(migrations_path):
        version = path.name.split("_", maxsplit=1)[0]
        if version in versions:
            raise ValueError(f"Duplicate migration version {version}: {path.name}")
        versions.add(version)
        migrations.append(
            Migration(
                version=version,
                name=path.name,
                sql=path.read_text(),
            )
        )

    return migrations


def run_migrations(database_url: str | None = None) -> MigrationRun:
    migrations = load_migrations()
    settings = get_settings()
    applied_now: list[str] = []
    already_applied: list[str] = []

    with psycopg.connect(database_url or settings.database_url) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS drivewise_schema_migrations (
              version text PRIMARY KEY,
              name text NOT NULL,
              applied_at timestamptz NOT NULL DEFAULT now()
            )
            """
        )

        # These unreleased migrations only changed names, not SQL. Preserve data.
        for old, new in RENAMED_MIGRATIONS.items():
            conn.execute(
                """UPDATE drivewise_schema_migrations SET version = %s, name = %s
                   WHERE version = %s AND name = %s""",
                (new.split("_", 1)[0], new, old.split("_", 1)[0], old),
            )
        applied_versions = dict(conn.execute(
            "SELECT version, name FROM drivewise_schema_migrations"
        ).fetchall())

        for migration in migrations:
            if migration.version in applied_versions:
                if applied_versions[migration.version] != migration.name:
                    raise ValueError(
                        f"Migration version {migration.version} already belongs to "
                        f"{applied_versions[migration.version]}, not {migration.name}"
                    )
                already_applied.append(migration.name)
                continue

            try:
                with conn.transaction():
                    conn.execute(migration.sql)
                    conn.execute(
                        """
                        INSERT INTO drivewise_schema_migrations (version, name)
                        VALUES (%s, %s)
                        """,
                        (migration.version, migration.name),
                    )
            except psycopg.Error as error:
                error.migration_name = migration.name
                raise
            applied_now.append(migration.name)

    return MigrationRun(applied=applied_now, already_applied=already_applied)


def apply_migrations(database_url: str | None = None) -> list[str]:
    return run_migrations(database_url).applied
