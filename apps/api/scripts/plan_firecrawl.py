import argparse
import os
import re
import sys
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.core.config import PROJECT_ROOT, load_env_file  # noqa: E402
from app.ingestion.firecrawl import (  # noqa: E402
    FirecrawlConfigError,
    FirecrawlIngestionPlan,
    load_sources_config,
    plan_firecrawl_ingestion,
)


DEFAULT_SOURCES_PATH = PROJECT_ROOT / "data/sources.example.json"
FIRECRAWL_ENV_KEYS = frozenset({"FIRECRAWL_API_KEY"})
SENSITIVE_QUERY_KEY = re.compile(
    r"key|token|secret|pass|auth|sig|session|credential|code", re.IGNORECASE
)


def redact_url(url: str) -> str:
    """Hide values of query parameters that look like credentials."""
    parts = urlsplit(url)
    if not parts.query:
        return url
    query = [
        (key, "REDACTED" if SENSITIVE_QUERY_KEY.search(key) else value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
    ]
    return urlunsplit(parts._replace(query=urlencode(query, safe="/:,")))


def main(argv: list[str] | None = None, env_path: Path = PROJECT_ROOT / ".env") -> int:
    args = parse_args(argv)
    load_env_file(env_path, allowed_keys=FIRECRAWL_ENV_KEYS)
    api_key = os.getenv("FIRECRAWL_API_KEY") or None

    try:
        config = load_sources_config(args.sources)
        plan = plan_firecrawl_ingestion(config, firecrawl_api_key=api_key)
    except FirecrawlConfigError as error:
        print(f"Invalid Firecrawl source config: {error}", file=sys.stderr)
        return 1

    print_plan(plan)
    return 0


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plan future Firecrawl ingestion without crawling or DB writes."
    )
    parser.add_argument(
        "--sources",
        type=Path,
        default=DEFAULT_SOURCES_PATH,
        help="JSON source config to validate and plan.",
    )
    return parser.parse_args(argv)


def print_plan(plan: FirecrawlIngestionPlan) -> None:
    print("Firecrawl ingestion plan")
    print(f"API key configured: {'yes' if plan.api_key_present else 'no'}")
    print(f"Firecrawl sources: {len(plan.firecrawl_sources)}")

    for source in plan.firecrawl_sources:
        print(f"- {source.name}")
        print(f"  Type: {source.source_type}")
        print(f"  URL: {redact_url(source.url)}")
        print(f"  Limit: {source.limit}")
        print(f"  Document type: {source.document_type}")
        print(f"  Crawl depth: {source.crawl_depth}")

    if plan.local_sources:
        print(f"Local fixture sources: {len(plan.local_sources)}")
        for source in plan.local_sources:
            print(f"- {source.name}")
            print(f"  Type: {source.source_type}")
            print(f"  Path: {source.path}")
            print(f"  Limit: {source.limit}")

    for warning in plan.warnings:
        print(f"Warning: {warning}")

    if not plan.http_requests_enabled:
        print("No HTTP requests were made.")
    if not plan.database_writes_enabled:
        print("No database writes were made.")


if __name__ == "__main__":
    raise SystemExit(main())
