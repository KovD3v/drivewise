"""Stage an artifact-backed bundle, or explicitly publish a staged batch."""

import argparse
import os
import sys
from pathlib import Path
from uuid import UUID

import psycopg
from psycopg.rows import dict_row
from pydantic import ValidationError

from app.core.config import PROJECT_ROOT, load_env_file
from app.core.database_url import contains_placeholder_database_url
from app.ingestion.catalog import CatalogValidationError
from app.ingestion.catalog_v2 import load_catalog_v2
from app.ingestion.catalog_v2_writer import (
    publish_catalog_v2,
    stage_catalog_v2,
    verify_artifacts,
)


def main(argv=None, env_path=PROJECT_ROOT / ".env") -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", type=Path, metavar="BUNDLE")
    mode.add_argument("--stage", type=Path, metavar="BUNDLE")
    mode.add_argument("--publish", type=UUID, metavar="BATCH_ID")
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--adopt-legacy", action="store_true")
    args = parser.parse_args(argv)
    if args.adopt_legacy and not args.publish:
        parser.error("--adopt-legacy requires --publish")
    try:
        payload = (
            load_catalog_v2(args.check or args.stage) if not args.publish else None
        )
        if args.check:
            verify_artifacts(payload, args.artifact_root)
            print("Catalog v2 and artifact hashes are valid.")
            return 0
        load_env_file(env_path)
        database_url = os.getenv("DATABASE_URL", "").strip()
        if not database_url or contains_placeholder_database_url(database_url):
            print(
                "Configure DATABASE_URL before staging or publishing.", file=sys.stderr
            )
            return 1
        with psycopg.connect(
            database_url, row_factory=dict_row, autocommit=True
        ) as conn:
            if args.stage:
                batch_id = stage_catalog_v2(
                    conn, payload, artifact_root=args.artifact_root
                )
                print(f"Staged batch: {batch_id}")
            else:
                result = publish_catalog_v2(
                    conn,
                    args.publish,
                    artifact_root=args.artifact_root,
                    adopt_legacy=args.adopt_legacy,
                )
                print(f"Batch {args.publish}: {result}")
        return 0
    except (CatalogValidationError, ValidationError, psycopg.Error, OSError) as error:
        # SQL errors and validation input can contain credentials or scraped content.
        print(
            f"Catalog v2 operation failed ({type(error).__name__}); no partial publication.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
