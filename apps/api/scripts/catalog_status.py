from __future__ import annotations

import argparse
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row

from app.core.config import PROJECT_ROOT, load_env_file
from app.core.database_url import contains_placeholder_database_url
from app.repositories.advisor import AdvisorRepository


BODY_STYLES = (
    "city_car",
    "crossover",
    "hatchback",
    "mpv",
    "sedan",
    "small_hatchback",
    "suv",
    "van",
    "wagon",
)
FUEL_TYPES = (
    "diesel",
    "electric",
    "full_hybrid_petrol",
    "hybrid_petrol",
    "mild_hybrid_petrol",
    "petrol",
    "petrol_lpg",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Report the readiness of catalog listings for Advisor rankings."
    )
    parser.add_argument(
        "--as-of",
        type=_parse_as_of,
        default=None,
        help="Evaluate freshness at this ISO 8601 time (defaults to now).",
    )
    return parser.parse_args(argv)


def _parse_as_of(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "--as-of must be an ISO 8601 date-time"
        ) from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise argparse.ArgumentTypeError("--as-of must include a timezone")
    return parsed.astimezone(timezone.utc)


def format_report(
    candidates: list[dict[str, Any]],
    excluded_counts: dict[str, int],
    *,
    as_of: datetime,
) -> str:
    body_styles = Counter(
        str(candidate["spec"]["body_style"]) for candidate in candidates
    )
    fuel_types = Counter(
        str(candidate["spec"]["fuel_type"]) for candidate in candidates
    )
    conditions = Counter(
        "new" if candidate["offer"]["condition"] == "new" else "used"
        for candidate in candidates
    )
    prices = [float(candidate["offer"]["price_eur"]) for candidate in candidates]
    total = len(candidates) + sum(excluded_counts.values())

    lines = [
        f"Catalog readiness as of: {as_of.isoformat()}",
        f"Listings: total={total}, rankable={len(candidates)}",
        "Exclusions:",
    ]
    if excluded_counts:
        lines.extend(
            f"  {reason}: {count}"
            for reason, count in sorted(
                excluded_counts.items(),
                key=lambda item: (-item[1], item[0]),
            )
        )
    else:
        lines.append("  none")

    lines.extend(
        [
            "Rankable body styles:",
            *[f"  {value}: {body_styles[value]}" for value in BODY_STYLES],
            "Rankable fuel types:",
            *[f"  {value}: {fuel_types[value]}" for value in FUEL_TYPES],
            "Rankable conditions:",
            f"  new: {conditions['new']}",
            f"  used: {conditions['used']}",
        ]
    )
    if prices:
        lines.append(
            f"Rankable price range (EUR): min={min(prices):.2f}, "
            f"max={max(prices):.2f}"
        )
    else:
        lines.append("Rankable price range (EUR): unavailable")

    missing_body_styles = [value for value in BODY_STYLES if not body_styles[value]]
    missing_fuel_types = [value for value in FUEL_TYPES if not fuel_types[value]]
    lines.append(
        "Zero-coverage body styles: "
        + (", ".join(missing_body_styles) if missing_body_styles else "none")
    )
    lines.append(
        "Zero-coverage fuel types: "
        + (", ".join(missing_fuel_types) if missing_fuel_types else "none")
    )
    return "\n".join(lines)


def main(
    argv: list[str] | None = None,
    env_path: Path = PROJECT_ROOT / ".env",
) -> int:
    args = parse_args(argv)
    as_of = args.as_of or datetime.now(timezone.utc)

    load_env_file(env_path)
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        print(
            "DATABASE_URL is not set. Catalog status requires a configured "
            "PostgreSQL database.",
            file=sys.stderr,
        )
        return 1
    if contains_placeholder_database_url(database_url):
        print(
            "DATABASE_URL still contains placeholders. Replace them before "
            "checking catalog status.",
            file=sys.stderr,
        )
        return 1

    try:
        with psycopg.connect(database_url, row_factory=dict_row) as conn:
            conn.execute("SET TRANSACTION READ ONLY")
            repository = AdvisorRepository(conn)
            candidates = repository.list_candidates(as_of=as_of)
            excluded_counts = repository.count_excluded_candidates(as_of=as_of)
    except psycopg.OperationalError:
        print(
            "Could not connect to the database configured by DATABASE_URL.",
            file=sys.stderr,
        )
        return 1
    except psycopg.Error as error:
        print(
            f"Catalog status query failed. Error type: {error.__class__.__name__}.",
            file=sys.stderr,
        )
        return 1

    print(format_report(candidates, excluded_counts, as_of=as_of))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
