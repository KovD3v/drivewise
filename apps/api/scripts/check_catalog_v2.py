"""Validate evidence bundles without reading .env or connecting to a database."""

import argparse
import sys
from pathlib import Path

from app.ingestion.catalog import CatalogValidationError
from app.ingestion.catalog_v2 import load_catalog_v2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        payload = load_catalog_v2(args.path)
    except CatalogValidationError as error:
        print(f"Catalog v2 rejected: {error}", file=sys.stderr)
        return 1
    print(
        f"Catalog v2 valid: {len(payload.vehicles)} vehicles, "
        f"{len(payload.variants)} variants, {len(payload.snapshots)} snapshots, "
        f"{len(payload.observations)} observations, {len(payload.decisions)} decisions."
    )
    print(
        "Validation checks structure and references, not factual truth or publication."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
