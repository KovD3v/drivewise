import os
import sys
from pathlib import Path
from urllib.parse import urlsplit

import psycopg

from app.core.config import PROJECT_ROOT, load_env_file
from app.core.database_url import contains_placeholder_database_url
from app.db.migrations import MigrationRun, run_migrations


def main(env_path: Path = PROJECT_ROOT / ".env") -> int:
    load_env_file(env_path)
    database_url = os.getenv("DATABASE_URL", "").strip()

    if not database_url:
        print(
            "DATABASE_URL is not set. Create .env from .env.example and set "
            "DATABASE_URL, or export DATABASE_URL in your shell.",
            file=sys.stderr,
        )
        return 1

    if contains_placeholder_database_url(database_url):
        print(
            "DATABASE_URL still contains placeholders. Replace .env values with "
            "your Neon connection string before running migrations.",
            file=sys.stderr,
        )
        return 1

    try:
        report = run_migrations(database_url)
    except psycopg.OperationalError:
        print(
            "Could not connect to the database configured by DATABASE_URL. "
            "Verify the Neon connection string, network access, and sslmode=require.",
            file=sys.stderr,
        )
        return 1
    except psycopg.Error as error:
        _print_migration_error(error, database_url)
        return 1

    _print_report(report)
    return 0


def _print_migration_error(error: psycopg.Error, database_url: str) -> None:
    lines = [
        "Database migration failed. Verify database privileges, pgvector "
        "support, and migration SQL.",
    ]
    migration_name = getattr(error, "migration_name", None)
    if migration_name:
        lines.append(
            f"Migration file: {_redact_sensitive(str(migration_name), database_url)}"
        )

    lines.append(f"Exception type: {error.__class__.__name__}")
    lines.append(
        f"Exception message: {_redact_sensitive(str(error), database_url)}"
    )

    sqlstate = _get_error_attr(error, "sqlstate")
    if sqlstate:
        lines.append(f"SQLSTATE: {_redact_sensitive(str(sqlstate), database_url)}")

    pgerror = _get_error_attr(error, "pgerror")
    if pgerror:
        lines.append(f"pgerror: {_redact_sensitive(str(pgerror), database_url)}")

    diag = _get_error_attr(error, "diag")
    if diag:
        for field_name in (
            "message_primary",
            "message_detail",
            "message_hint",
            "statement_position",
            "context",
        ):
            value = _get_error_attr(diag, field_name)
            if value:
                lines.append(
                    f"{field_name}: {_redact_sensitive(str(value), database_url)}"
                )

    print("\n".join(lines), file=sys.stderr)


def _get_error_attr(error: object, attribute: str) -> object | None:
    try:
        return getattr(error, attribute)
    except Exception:
        return None


def _redact_sensitive(text: str, database_url: str) -> str:
    if not database_url:
        return text

    redacted = text.replace(database_url, "[redacted DATABASE_URL]")

    parsed = urlsplit(database_url)
    if parsed.netloc:
        redacted = redacted.replace(parsed.netloc, "[redacted DATABASE_URL]")

    if parsed.password:
        redacted = redacted.replace(parsed.password, "[redacted]")

    if parsed.username:
        redacted = redacted.replace(
            f"user={parsed.username}",
            "user=[redacted]",
        )
        redacted = redacted.replace(
            f"username={parsed.username}",
            "username=[redacted]",
        )

    return redacted


def _print_report(report: MigrationRun) -> None:
    if report.already_applied:
        for migration_name in report.already_applied:
            print(f"Already applied {migration_name}")

    if not report.applied:
        print("No pending migrations.")
        return

    for migration_name in report.applied:
        print(f"Applied {migration_name}")


if __name__ == "__main__":
    raise SystemExit(main())
