import argparse
import os
import sys
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

from app.core.config import PROJECT_ROOT, load_env_file
from app.core.database_url import contains_placeholder_database_url
from app.ingestion.local import IngestionResult, ingest_local_documents


DEFAULT_FIXTURE_PATH = PROJECT_ROOT / "data/fixtures/ingestion"


def main(argv: list[str] | None = None, env_path: Path = PROJECT_ROOT / ".env") -> int:
    args = parse_args(argv)
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
            "your Neon connection string before running ingestion.",
            file=sys.stderr,
        )
        return 1

    try:
        with psycopg.connect(database_url, row_factory=dict_row) as conn:
            result = ingest_local_documents(
                conn,
                args.path,
                source_name=args.source_name,
                source_type=args.source_type,
            )
    except FileNotFoundError as error:
        print(str(error), file=sys.stderr)
        return 1
    except psycopg.OperationalError:
        print(
            "Could not connect to the database configured by DATABASE_URL. "
            "Verify the Neon connection string, network access, and sslmode=require.",
            file=sys.stderr,
        )
        return 1
    except psycopg.Error as error:
        print(
            "Local ingestion failed while writing to PostgreSQL. Verify database "
            f"migrations and privileges. Error type: {error.__class__.__name__}.",
            file=sys.stderr,
        )
        return 1

    print_result(result)
    return 0


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest local Drivewise fixtures.")
    parser.add_argument(
        "--path",
        type=Path,
        default=DEFAULT_FIXTURE_PATH,
        help="Directory or file containing .md, .txt, or .json documents.",
    )
    parser.add_argument(
        "--source-name",
        default="Drivewise Local Fixture Ingestion",
        help="Name of the source row used for imported documents.",
    )
    parser.add_argument(
        "--source-type",
        choices=["curated_internal", "public_dataset"],
        default="curated_internal",
        help="Source type for imported local fixture documents.",
    )
    return parser.parse_args(argv)


def print_result(result: IngestionResult) -> None:
    print(f"Inserted: {result.inserted}")
    print(f"Skipped: {result.skipped}")
    print(f"Updated: {result.updated}")


if __name__ == "__main__":
    raise SystemExit(main())
