import hashlib
from dataclasses import dataclass
from pathlib import Path

import psycopg

from app.core.config import get_settings


MIGRATIONS_PATH = Path(__file__).resolve().parents[2] / "migrations"
RENAMED_MIGRATIONS = {
    "0006_catalog_publication.sql": "0009_catalog_publication.sql",
    "0005_catalog_evidence.sql": "0008_catalog_evidence.sql",
}
# Serialises concurrent runners (two deploys at once). Any fixed bigint works, as
# long as nothing else in the database takes the same advisory lock.
MIGRATION_LOCK_KEY = 0x44726976_65576973  # "DriveWis"


@dataclass(frozen=True)
class Migration:
    version: str
    name: str
    sql: str

    @property
    def checksum(self) -> str:
        """SHA-256 of the SQL text, recorded when the migration is applied."""
        return hashlib.sha256(self.sql.encode("utf-8")).hexdigest()


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
        # The whole run is one transaction (each migration is a savepoint inside it),
        # so this lock holds until the final commit. A second runner waits here and
        # then reads the ledger the first one committed: no migration runs twice.
        conn.execute("SELECT pg_advisory_xact_lock(%s)", (MIGRATION_LOCK_KEY,))
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS drivewise_schema_migrations (
              version text PRIMARY KEY,
              name text NOT NULL,
              applied_at timestamptz NOT NULL DEFAULT now()
            )
            """
        )
        # Rows applied before checksums existed keep NULL and are not verified.
        conn.execute(
            "ALTER TABLE drivewise_schema_migrations "
            "ADD COLUMN IF NOT EXISTS checksum text"
        )

        # These unreleased migrations only changed names, not SQL. Preserve data.
        for old, new in RENAMED_MIGRATIONS.items():
            conn.execute(
                """UPDATE drivewise_schema_migrations SET version = %s, name = %s
                   WHERE version = %s AND name = %s""",
                (new.split("_", 1)[0], new, old.split("_", 1)[0], old),
            )
        applied_versions = {
            version: (name, checksum)
            for version, name, checksum in conn.execute(
                "SELECT version, name, checksum FROM drivewise_schema_migrations"
            ).fetchall()
        }

        for migration in migrations:
            if migration.version in applied_versions:
                applied_name, applied_checksum = applied_versions[migration.version]
                if applied_name != migration.name:
                    raise ValueError(
                        f"Migration version {migration.version} already belongs to "
                        f"{applied_name}, not {migration.name}"
                    )
                if (
                    applied_checksum is not None
                    and applied_checksum != migration.checksum
                ):
                    raise ValueError(
                        f"Migration {migration.name} changed after it was applied "
                        f"(checksum {applied_checksum[:12]}, file "
                        f"{migration.checksum[:12]}); add a new migration instead "
                        "of editing an applied one"
                    )
                already_applied.append(migration.name)
                continue

            try:
                with conn.transaction():
                    conn.execute(migration.sql)
                    conn.execute(
                        """
                        INSERT INTO drivewise_schema_migrations
                          (version, name, checksum)
                        VALUES (%s, %s, %s)
                        """,
                        (migration.version, migration.name, migration.checksum),
                    )
            except psycopg.Error as error:
                error.migration_name = migration.name
                raise
            applied_now.append(migration.name)

    return MigrationRun(applied=applied_now, already_applied=already_applied)


def apply_migrations(database_url: str | None = None) -> list[str]:
    return run_migrations(database_url).applied
