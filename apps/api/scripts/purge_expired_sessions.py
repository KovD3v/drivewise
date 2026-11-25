"""Delete anonymous sessions older than the retention period (GDPR, F-13).

Dry run by default: it only counts what it would delete. Pass --execute to delete.

    uv run --project apps/api python apps/api/scripts/purge_expired_sessions.py --days 30
    uv run --project apps/api python apps/api/scripts/purge_expired_sessions.py --days 30 --execute

A guided decision expires when its last activity (updated_at) is older than the
cutoff; its turns go with it through ON DELETE CASCADE. A recommendation run
expires by created_at; its items go with it the same way. No table here has an
owner column: every session is anonymous.
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

from app.core.config import PROJECT_ROOT, load_env_file
from app.core.database_url import contains_placeholder_database_url


DEFAULT_RETENTION_DAYS = 30

# One predicate per table, shared by the count and the delete.
_EXPIRED_DECISIONS = "guided_decisions.updated_at < %(cutoff)s"
_EXPIRED_RUNS = "recommendation_runs.created_at < %(cutoff)s"

COUNT_SQL = f"""
SELECT
  (SELECT count(*) FROM guided_decisions
   WHERE {_EXPIRED_DECISIONS}) AS guided_decisions,
  (SELECT count(*) FROM guided_decision_turns
   JOIN guided_decisions ON guided_decisions.id = guided_decision_turns.decision_id
   WHERE {_EXPIRED_DECISIONS}) AS guided_decision_turns,
  (SELECT count(*) FROM recommendation_runs
   WHERE {_EXPIRED_RUNS}) AS recommendation_runs,
  (SELECT count(*) FROM recommendation_items
   JOIN recommendation_runs ON recommendation_runs.id = recommendation_items.run_id
   WHERE {_EXPIRED_RUNS}) AS recommendation_items
"""
DELETE_DECISIONS_SQL = f"DELETE FROM guided_decisions WHERE {_EXPIRED_DECISIONS}"
DELETE_RUNS_SQL = f"DELETE FROM recommendation_runs WHERE {_EXPIRED_RUNS}"


@dataclass(frozen=True)
class PurgeReport:
    cutoff: datetime
    executed: bool
    counts: dict[str, int]


def _positive_days(value: str) -> int:
    try:
        days = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("--days must be a whole number") from error
    if days < 1:
        raise argparse.ArgumentTypeError("--days must be at least 1")
    return days


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Count, or with --execute delete, anonymous guided decisions and "
            "recommendation runs older than the retention period."
        )
    )
    parser.add_argument(
        "--days",
        type=_positive_days,
        default=DEFAULT_RETENTION_DAYS,
        help=f"Retention period in days (default {DEFAULT_RETENTION_DAYS}).",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Delete the expired rows. Without it the script only counts them.",
    )
    return parser.parse_args(argv)


def purge_expired_sessions(
    conn,
    *,
    days: int,
    execute: bool,
    now: datetime | None = None,
) -> PurgeReport:
    """Count the expired rows and, when execute is true, delete them in one
    transaction. The caller owns the connection and its commit."""
    if days < 1:
        raise ValueError("days must be at least 1")
    cutoff = (now or datetime.now(timezone.utc)) - timedelta(days=days)
    params = {"cutoff": cutoff}
    row = conn.execute(COUNT_SQL, params).fetchone()
    counts = {key: int(value) for key, value in dict(row).items()}
    if execute:
        conn.execute(DELETE_DECISIONS_SQL, params)
        conn.execute(DELETE_RUNS_SQL, params)
    return PurgeReport(cutoff=cutoff, executed=execute, counts=counts)


def format_report(report: PurgeReport) -> str:
    verb = "Deleted" if report.executed else "Would delete"
    lines = [f"Cutoff: {report.cutoff.isoformat()}"]
    lines.extend(f"{verb} {count} {table}" for table, count in report.counts.items())
    if not report.executed:
        lines.append("Dry run: nothing was deleted. Pass --execute to delete.")
    return "\n".join(lines)


def main(
    argv: list[str] | None = None,
    env_path: Path = PROJECT_ROOT / ".env",
    now: datetime | None = None,
) -> int:
    args = parse_args(argv)
    load_env_file(env_path)
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        print(
            "DATABASE_URL is not set. The retention purge requires a configured "
            "PostgreSQL database.",
            file=sys.stderr,
        )
        return 1
    if contains_placeholder_database_url(database_url):
        print(
            "DATABASE_URL still contains placeholders. Replace them before "
            "running the retention purge.",
            file=sys.stderr,
        )
        return 1

    try:
        with psycopg.connect(database_url, row_factory=dict_row) as conn:
            if not args.execute:
                conn.execute("SET TRANSACTION READ ONLY")
            report = purge_expired_sessions(
                conn, days=args.days, execute=args.execute, now=now
            )
    except psycopg.OperationalError:
        print(
            "Could not connect to the database configured by DATABASE_URL.",
            file=sys.stderr,
        )
        return 1
    except psycopg.Error as error:
        print(
            f"Retention purge failed. Error type: {error.__class__.__name__}.",
            file=sys.stderr,
        )
        return 1

    print(format_report(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
