import argparse
import os
import sys
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

from app.core.config import PROJECT_ROOT, load_env_file
from app.core.database_url import contains_placeholder_database_url
from app.ingestion.catalog import (
    CatalogValidationError,
    import_catalog,
    load_catalog,
    validate_catalog,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate or import a reviewed Drivewise catalog snapshot."
    )
    parser.add_argument("--path", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--check",
        action="store_true",
        help="Validate the complete JSON file without connecting to PostgreSQL.",
    )
    mode.add_argument(
        "--write",
        action="store_true",
        help="Validate and transactionally upsert the JSON file.",
    )
    return parser.parse_args(argv)


def main(
    argv: list[str] | None = None,
    env_path: Path = PROJECT_ROOT / ".env",
) -> int:
    args = parse_args(argv)
    try:
        payload = load_catalog(args.path)
    except CatalogValidationError as error:
        print(str(error), file=sys.stderr)
        return 1

    summary = validate_catalog(payload)
    if args.check:
        _print_valid(summary)
        return 0

    load_env_file(env_path)
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        print(
            "DATABASE_URL is not set. Validation passed, but --write requires "
            "a configured PostgreSQL database.",
            file=sys.stderr,
        )
        return 1
    if contains_placeholder_database_url(database_url):
        print(
            "DATABASE_URL still contains placeholders. Replace them before "
            "running --write.",
            file=sys.stderr,
        )
        return 1

    try:
        with psycopg.connect(
            database_url,
            row_factory=dict_row,
            autocommit=True,
        ) as conn:
            result = import_catalog(conn, payload, file_name=args.path.name)
    except psycopg.OperationalError:
        print(
            "Could not connect to the database configured by DATABASE_URL.",
            file=sys.stderr,
        )
        return 1
    except CatalogValidationError as error:
        print(
            f"Catalog import rejected: {error}",
            file=sys.stderr,
        )
        return 1
    except psycopg.Error as error:
        print(
            "Catalog import failed and catalog writes were rolled back. "
            f"Error type: {error.__class__.__name__}.",
            file=sys.stderr,
        )
        return 1

    print(f"Import status: {result.status}")
    print(f"Run ID: {result.run_id}")
    print(f"Dataset hash: {result.dataset_hash}")
    print(f"Inserted: {result.counts.inserted}")
    print(f"Updated: {result.counts.updated}")
    print(f"Unchanged: {result.counts.unchanged}")
    print(f"Deactivated: {result.counts.deactivated}")
    return 0


def _print_valid(summary) -> None:
    print("Catalog is valid.")
    print(f"Sources: {summary.sources}")
    print(f"Vehicles: {summary.vehicles}")
    print(f"Variants: {summary.variants}")
    print(f"Listings: {summary.listings}")


if __name__ == "__main__":
    raise SystemExit(main())
