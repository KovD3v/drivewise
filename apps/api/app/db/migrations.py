from dataclasses import dataclass
from pathlib import Path

import psycopg

from app.core.config import get_settings


MIGRATIONS_PATH = Path(__file__).resolve().parents[2] / "migrations"


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

    for path in iter_migration_files(migrations_path):
        version = path.name.split("_", maxsplit=1)[0]
        migrations.append(
            Migration(
                version=version,
                name=path.name,
                sql=path.read_text(),
            )
        )

    return migrations


def run_migrations(database_url: str | None = None) -> MigrationRun:
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

        applied_versions = {
            row[0]
            for row in conn.execute(
                "SELECT version FROM drivewise_schema_migrations"
            ).fetchall()
        }

        for migration in load_migrations():
            if migration.version in applied_versions:
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
