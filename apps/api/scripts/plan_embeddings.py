import argparse
import os
import sys
from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

import psycopg  # noqa: E402
from psycopg.rows import dict_row  # noqa: E402

from app.core.config import PROJECT_ROOT, load_env_file  # noqa: E402
from app.core.database_url import contains_placeholder_database_url  # noqa: E402
from app.embeddings.planner import (  # noqa: E402
    DEFAULT_EMBEDDING_BATCH_LIMIT,
    DEFAULT_EMBEDDING_MODEL,
    EmbeddingBatchPlan,
    EmbeddingPlanError,
    list_documents_missing_embeddings,
    mark_embedding_plan_dry_run,
    plan_embedding_batch,
    validate_document_type,
    validate_embedding_limit,
)


DATABASE_ENV_KEYS = frozenset({"DATABASE_URL"})


def main(argv: list[str] | None = None, env_path: Path = PROJECT_ROOT / ".env") -> int:
    args = parse_args(argv)

    try:
        validate_embedding_limit(args.limit)
        validate_document_type(args.document_type)
    except EmbeddingPlanError as error:
        print(str(error), file=sys.stderr)
        return 1

    load_env_file(env_path, allowed_keys=DATABASE_ENV_KEYS)
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
            "your Neon connection string before planning embeddings.",
            file=sys.stderr,
        )
        return 1

    try:
        with psycopg.connect(database_url, row_factory=dict_row) as conn:
            documents = list_documents_missing_embeddings(
                conn,
                limit=args.limit,
                document_type=args.document_type,
            )
            plan = plan_embedding_batch(
                documents,
                model=args.model,
                limit=args.limit,
                document_type=args.document_type,
            )
    except psycopg.OperationalError:
        print(
            "Could not connect to the database configured by DATABASE_URL. "
            "Verify the Neon connection string, network access, and sslmode=require.",
            file=sys.stderr,
        )
        return 1
    except psycopg.Error as error:
        print(
            "Embedding planning failed while reading PostgreSQL. Verify database "
            f"migrations and privileges. Error type: {error.__class__.__name__}.",
            file=sys.stderr,
        )
        return 1
    except EmbeddingPlanError as error:
        print(str(error), file=sys.stderr)
        return 1

    print_plan(plan)
    return 0


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plan document embedding generation without provider calls or DB writes."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_EMBEDDING_BATCH_LIMIT,
        help="Maximum documents to include in the dry-run plan. Must be 1-100.",
    )
    parser.add_argument(
        "--document-type",
        default=None,
        help="Optional exact documents.document_type filter.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_EMBEDDING_MODEL,
        help="Embedding model name to include in the plan only.",
    )
    return parser.parse_args(argv)


def print_plan(plan: EmbeddingBatchPlan) -> None:
    dry_run = mark_embedding_plan_dry_run(plan)

    print("Embedding dry-run plan")
    print(f"Model: {plan.model}")
    print(f"Limit: {plan.limit}")
    print(f"Document type filter: {plan.document_type or 'none'}")
    print(f"Documents selected: {plan.total_documents}")
    print(f"Total estimated chars: {plan.total_estimated_characters}")
    print(f"Total estimated tokens: {plan.total_estimated_tokens}")

    for document in plan.documents:
        print(f"- {document.id}")
        print(f"  Title: {document.title}")
        print(f"  Type: {document.document_type}")
        print(f"  Estimated chars: {document.estimated_characters}")
        print(f"  Estimated tokens: {document.estimated_tokens}")
        print(f"  Preview: {document.preview}")

    if dry_run["external_provider_calls"] == "disabled":
        print("No external provider calls were made.")
    if dry_run["database_writes"] == "disabled":
        print("No database writes were made.")


if __name__ == "__main__":
    raise SystemExit(main())
